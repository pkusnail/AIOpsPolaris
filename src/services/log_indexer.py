"""
日志索引服务 - Log Ingestion and Indexing Pipeline
负责解析日志、处理数据并写入两个Weaviate collections
"""

import re
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor

import weaviate
from weaviate import Client
from sentence_transformers import SentenceTransformer

from .log_schema import (
    LOG_ENTRY_SCHEMA, LOG_EMBEDDING_SCHEMA,
    LogEntry, LogEmbedding, LogQueryFilters
)

logger = logging.getLogger(__name__)

class LogParser:
    """日志解析器 - 支持多种日志格式"""
    
    # 通用日志格式正则表达式
    PATTERNS = {
        # 标准格式: 2025-08-20T14:30:15.123Z [INFO] service-b: Application started
        'standard': re.compile(
            r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z?)\s+'
            r'\[(?P<level>\w+)\]\s+'
            r'(?P<service>[\w-]+):\s+'
            r'(?P<message>.*)'
        ),
        
        # 带主机信息: 2025-08-20T14:30:15.123Z [INFO] service-b@10.1.0.5: Application started
        'with_host': re.compile(
            r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z?)\s+'
            r'\[(?P<level>\w+)\]\s+'
            r'(?P<service>[\w-]+)@(?P<host_ip>\d+\.\d+\.\d+\.\d+):\s+'
            r'(?P<message>.*)'
        ),
        
        # 详细格式: 包含线程ID等信息
        'detailed': re.compile(
            r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z?)\s+'
            r'\[(?P<level>\w+)\]\s+'
            r'\[(?P<thread_id>[\w-]+)\]\s+'
            r'(?P<service>[\w-]+):\s+'
            r'(?:(?P<component>[\w\.]+):\s+)?'
            r'(?P<message>.*)'
        )
    }
    
    def parse_log_line(self, line: str) -> Optional[Dict[str, Any]]:
        """解析单行日志"""
        line = line.strip()
        if not line or line.startswith('#'):
            return None
            
        # 尝试各种格式
        for pattern_name, pattern in self.PATTERNS.items():
            match = pattern.match(line)
            if match:
                data = match.groupdict()
                return self._normalize_log_data(data, pattern_name)
        
        # 如果都不匹配，创建基本结构
        return self._create_fallback_entry(line)
    
    def _normalize_log_data(self, data: Dict[str, Any], pattern_name: str) -> Dict[str, Any]:
        """标准化日志数据"""
        # 解析时间戳
        timestamp_str = data.get('timestamp', '')
        try:
            if timestamp_str.endswith('Z'):
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc)
        except ValueError:
            timestamp = datetime.now(timezone.utc)
        
        # 提取服务信息
        service_name = data.get('service', 'unknown')
        
        # 提取主机信息
        host_ip = data.get('host_ip', self._extract_ip_from_message(data.get('message', '')))
        if not host_ip:
            host_ip = f"10.1.0.{hash(service_name) % 254 + 1}"  # 生成虚拟IP
        
        host_name = f"{service_name}-host"
        
        # 解析消息内容，提取结构化信息
        message = data.get('message', '')
        parsed_info = self._parse_message_content(message)
        
        return {
            'timestamp': timestamp,
            'service_name': service_name,
            'host_ip': host_ip,
            'host_name': host_name,
            'log_level': data.get('level', 'INFO').upper(),
            'message': message,
            'component': data.get('component', parsed_info.get('component')),
            'thread_id': data.get('thread_id', parsed_info.get('thread_id')),
            'request_id': parsed_info.get('request_id'),
            'error_code': parsed_info.get('error_code'),
            'duration_ms': parsed_info.get('duration_ms'),
            'tags': parsed_info.get('tags', []),
            'metadata': parsed_info.get('metadata', {})
        }
    
    def _parse_message_content(self, message: str) -> Dict[str, Any]:
        """从消息内容中提取结构化信息"""
        info = {'tags': [], 'metadata': {}}
        
        # 提取请求ID
        request_id_match = re.search(r'request[_-]?id[:\s=]+([a-zA-Z0-9-]+)', message, re.IGNORECASE)
        if request_id_match:
            info['request_id'] = request_id_match.group(1)
        
        # 提取错误码
        error_code_match = re.search(r'error[_\s]?code[:\s=]+([A-Z0-9_]+)', message, re.IGNORECASE)
        if error_code_match:
            info['error_code'] = error_code_match.group(1)
        
        # 提取执行时间
        duration_match = re.search(r'(\d+(?:\.\d+)?)\s*ms', message)
        if duration_match:
            info['duration_ms'] = float(duration_match.group(1))
        
        # 提取CPU、内存等指标
        cpu_match = re.search(r'CPU[:\s]*(\d+(?:\.\d+)?)%', message, re.IGNORECASE)
        if cpu_match:
            info['metadata']['cpu_percent'] = float(cpu_match.group(1))
            info['tags'].append('performance')
        
        memory_match = re.search(r'Memory[:\s]*(\d+(?:\.\d+)?)\s*(MB|GB)', message, re.IGNORECASE)
        if memory_match:
            memory_val = float(memory_match.group(1))
            memory_unit = memory_match.group(2).upper()
            if memory_unit == 'GB':
                memory_val *= 1024
            info['metadata']['memory_mb'] = memory_val
            info['tags'].append('performance')
        
        # 识别错误类型标签
        if any(keyword in message.lower() for keyword in ['timeout', 'connection', 'refused']):
            info['tags'].append('network')
        if any(keyword in message.lower() for keyword in ['memory', 'heap', 'oom']):
            info['tags'].append('memory')
        if any(keyword in message.lower() for keyword in ['disk', 'i/o', 'space']):
            info['tags'].append('disk')
        if any(keyword in message.lower() for keyword in ['database', 'sql', 'connection pool']):
            info['tags'].append('database')
        
        return info
    
    def _extract_ip_from_message(self, message: str) -> Optional[str]:
        """从消息中提取IP地址"""
        ip_pattern = re.compile(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b')
        match = ip_pattern.search(message)
        return match.group(1) if match else None
    
    def _create_fallback_entry(self, line: str) -> Dict[str, Any]:
        """创建fallback日志条目"""
        return {
            'timestamp': datetime.now(timezone.utc),
            'service_name': 'unknown',
            'host_ip': '10.1.0.1',
            'host_name': 'unknown-host',
            'log_level': 'INFO',
            'message': line,
            'component': None,
            'thread_id': None,
            'request_id': None,
            'error_code': None,
            'duration_ms': None,
            'tags': [],
            'metadata': {}
        }

class LogProcessor:
    """日志处理器 - AI增强处理"""
    
    def __init__(self):
        # 初始化sentence transformer用于生成embeddings
        self.embedding_model = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    async def _get_embedding_model(self):
        """懒加载embedding模型"""
        if self.embedding_model is None:
            loop = asyncio.get_event_loop()
            self.embedding_model = await loop.run_in_executor(
                self.executor,
                lambda: SentenceTransformer('all-MiniLM-L6-v2')  # 轻量级模型
            )
        return self.embedding_model
    
    async def process_for_embedding(self, log_entry: LogEntry) -> LogEmbedding:
        """处理日志条目生成embedding版本"""
        # 创建用于embedding的内容
        content = self._create_embedding_content(log_entry)
        
        # 生成摘要
        summary = self._generate_summary(log_entry)
        
        # 分类日志
        category = self._classify_log(log_entry)
        
        # 计算严重程度分数
        severity_score = self._calculate_severity(log_entry)
        
        return LogEmbedding(
            timestamp=log_entry.timestamp,
            service_name=log_entry.service_name,
            host_ip=log_entry.host_ip,
            log_level=log_entry.log_level,
            content=content,
            summary=summary,
            category=category,
            severity_score=severity_score,
            log_entry_id=None  # 将在索引后设置
        )
    
    def _create_embedding_content(self, log_entry: LogEntry) -> str:
        """创建用于embedding的规范化内容"""
        parts = []
        
        # 基本信息
        parts.append(f"Service: {log_entry.service_name}")
        parts.append(f"Level: {log_entry.log_level}")
        
        # 组件信息
        if log_entry.component:
            parts.append(f"Component: {log_entry.component}")
        
        # 主要消息（清理后）
        cleaned_message = self._clean_message(log_entry.message)
        parts.append(f"Message: {cleaned_message}")
        
        # 标签信息
        if log_entry.tags:
            parts.append(f"Tags: {', '.join(log_entry.tags)}")
        
        return " | ".join(parts)
    
    def _clean_message(self, message: str) -> str:
        """清理消息内容，移除噪音信息"""
        # 移除时间戳
        message = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z?', '', message)
        
        # 移除UUID和长ID
        message = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '[ID]', message)
        message = re.sub(r'[a-zA-Z0-9]{20,}', '[LONG_ID]', message)
        
        # 标准化数字
        message = re.sub(r'\d+\.\d+', '[NUMBER]', message)
        message = re.sub(r'\b\d+\b', '[NUM]', message)
        
        return message.strip()
    
    def _generate_summary(self, log_entry: LogEntry) -> str:
        """生成日志摘要"""
        # 简单的基于规则的摘要生成
        level = log_entry.log_level
        service = log_entry.service_name
        message = log_entry.message.lower()
        
        if level in ['ERROR', 'CRITICAL']:
            if 'cpu' in message:
                return f"{service} experiencing high CPU usage"
            elif 'memory' in message or 'heap' in message:
                return f"{service} has memory issues"
            elif 'disk' in message or 'i/o' in message:
                return f"{service} encountering disk I/O problems"
            elif 'timeout' in message or 'connection' in message:
                return f"{service} has connectivity issues"
            else:
                return f"{service} reported an error condition"
        elif level == 'WARN':
            return f"{service} has warning condition"
        else:
            return f"{service} normal operation log"
    
    def _classify_log(self, log_entry: LogEntry) -> str:
        """分类日志条目"""
        message = log_entry.message.lower()
        level = log_entry.log_level
        
        # 基于内容和级别分类
        if level in ['ERROR', 'CRITICAL']:
            if any(kw in message for kw in ['cpu', 'memory', 'heap', 'gc']):
                return 'performance_issue'
            elif any(kw in message for kw in ['timeout', 'connection', 'network']):
                return 'connectivity_issue' 
            elif any(kw in message for kw in ['disk', 'i/o', 'space']):
                return 'storage_issue'
            elif any(kw in message for kw in ['database', 'sql', 'query']):
                return 'database_issue'
            else:
                return 'application_error'
        elif level == 'WARN':
            return 'warning'
        elif 'start' in message or 'init' in message:
            return 'system_event'
        else:
            return 'normal_operation'
    
    def _calculate_severity(self, log_entry: LogEntry) -> float:
        """计算严重程度分数 (0-1)"""
        base_score = {
            'INFO': 0.1,
            'WARN': 0.4, 
            'ERROR': 0.7,
            'CRITICAL': 0.9
        }.get(log_entry.log_level, 0.1)
        
        message = log_entry.message.lower()
        
        # 根据关键词调整分数
        severity_keywords = {
            'critical': 0.2,
            'outofmemory': 0.25,
            'timeout': 0.15,
            'failed': 0.1,
            'exception': 0.1,
            'unable': 0.1,
            'denied': 0.1
        }
        
        for keyword, bonus in severity_keywords.items():
            if keyword in message:
                base_score = min(1.0, base_score + bonus)
        
        return round(base_score, 2)

class LogIndexer:
    """日志索引服务主类"""
    
    def __init__(self, weaviate_client: Client):
        self.client = weaviate_client
        self.parser = LogParser()
        self.processor = LogProcessor()
        
    async def initialize_collections(self):
        """初始化Weaviate collections"""
        try:
            # 创建LogEntry collection
            if not self.client.schema.exists("LogEntry"):
                self.client.schema.create_class(LOG_ENTRY_SCHEMA)
                logger.info("Created LogEntry collection")
            
            # 创建LogEmbedding collection  
            if not self.client.schema.exists("LogEmbedding"):
                self.client.schema.create_class(LOG_EMBEDDING_SCHEMA)
                logger.info("Created LogEmbedding collection")
                
        except Exception as e:
            logger.error(f"Failed to initialize collections: {e}")
            raise
    
    async def process_log_file(self, file_path: Path) -> Tuple[int, int]:
        """处理日志文件"""
        processed_count = 0
        error_count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 批量处理
            batch_size = 100
            for i in range(0, len(lines), batch_size):
                batch_lines = lines[i:i + batch_size]
                try:
                    await self._process_batch(batch_lines)
                    processed_count += len(batch_lines)
                except Exception as e:
                    logger.error(f"Batch processing error: {e}")
                    error_count += len(batch_lines)
                    
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            raise
        
        return processed_count, error_count
    
    async def _process_batch(self, lines: List[str]):
        """批量处理日志行"""
        # 解析日志
        log_entries = []
        for line in lines:
            parsed = self.parser.parse_log_line(line)
            if parsed:
                log_entry = LogEntry(**parsed)
                log_entries.append(log_entry)
        
        if not log_entries:
            return
        
        # 批量写入LogEntry collection
        with self.client.batch(
            batch_size=50,
            dynamic=True,
            timeout_retries=3,
            connection_error_retries=3
        ) as batch:
            for entry in log_entries:
                batch.add_data_object(
                    entry.to_weaviate_object(),
                    "LogEntry"
                )
        
        # 处理并写入LogEmbedding collection
        embedding_entries = []
        for entry in log_entries:
            embedding_entry = await self.processor.process_for_embedding(entry)
            embedding_entries.append(embedding_entry)
        
        with self.client.batch(
            batch_size=50,
            dynamic=True,
            timeout_retries=3,
            connection_error_retries=3
        ) as batch:
            for entry in embedding_entries:
                batch.add_data_object(
                    entry.to_weaviate_object(),
                    "LogEmbedding"
                )
    
    async def search_logs(
        self,
        query: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        services: List[str] = None,
        hosts: List[str] = None,
        log_levels: List[str] = None,
        limit: int = 100,
        use_vector_search: bool = False
    ) -> List[Dict[str, Any]]:
        """搜索日志"""
        
        collection = "LogEmbedding" if use_vector_search else "LogEntry"
        
        # 构建过滤器
        filters = []
        
        if start_time and end_time:
            filters.append(LogQueryFilters.time_range_filter(start_time, end_time))
        
        if services:
            filters.append(LogQueryFilters.service_filter(services))
        
        if hosts:
            filters.append(LogQueryFilters.host_filter(hosts))
            
        if log_levels:
            filters.append(LogQueryFilters.log_level_filter(log_levels))
        
        combined_filter = LogQueryFilters.combine_filters(*filters)
        
        # 构建查询
        query_builder = self.client.query.get(collection)
        
        # 添加字段
        if collection == "LogEntry":
            query_builder = query_builder.with_additional(["id"]).with_limit(limit)
        else:
            query_builder = query_builder.with_additional(["id", "distance"]).with_limit(limit)
        
        # 添加过滤器
        if combined_filter:
            query_builder = query_builder.with_where(combined_filter)
        
        # 添加搜索条件
        if query:
            if use_vector_search:
                query_builder = query_builder.with_near_text({"concepts": [query]})
            else:
                query_builder = query_builder.with_bm25(query=query)
        
        try:
            result = query_builder.do()
            return result.get("data", {}).get("Get", {}).get(collection, [])
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise