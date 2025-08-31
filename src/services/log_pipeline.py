"""
日志数据处理Pipeline
从./data/logs/读取日志文件并在Weaviate两个Collection中建立索引
"""

import os
import re
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

from .rag_vector_service import RAGVectorService
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class LogPipeline:
    """日志处理管道类"""
    
    def __init__(self):
        self.rag_service = RAGVectorService()
        self.embedding_service = EmbeddingService()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 日志解析正则模式
        self.log_patterns = {
            'standard': re.compile(
                r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\s+'
                r'\[(?P<level>\w+)\]\s+'
                r'(?P<service>[\w-]+):\s+'
                r'(?P<message>.*)'
            ),
            'simple': re.compile(
                r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\s+'
                r'\[(?P<level>\w+)\]\s+'
                r'(?P<message>.*)'
            )
        }
    
    def parse_log_line(self, line: str, line_number: int, log_file: str) -> Optional[Dict[str, Any]]:
        """解析单行日志"""
        try:
            line = line.strip()
            if not line or line.startswith('#'):
                return None
            
            # 尝试不同的解析模式
            for pattern_name, pattern in self.log_patterns.items():
                match = pattern.match(line)
                if match:
                    groups = match.groupdict()
                    
                    # 解析时间戳
                    timestamp_str = groups.get('timestamp', '')
                    try:
                        if timestamp_str.endswith('Z'):
                            timestamp = datetime.fromisoformat(timestamp_str[:-1])
                        else:
                            timestamp = datetime.fromisoformat(timestamp_str)
                    except:
                        timestamp = datetime.utcnow()
                    
                    # 从日志文件名提取服务名和主机名
                    service_name = groups.get('service', '')
                    hostname = 'unknown'
                    
                    # 尝试从文件名推断服务和主机信息
                    if 'service_b' in log_file.lower():
                        service_name = service_name or 'service-b'
                        hostname = 'd1-app-01'  # 根据incident信息推断
                    elif 'service_a' in log_file.lower():
                        service_name = service_name or 'service-a'
                        hostname = 'd1-app-02'
                    
                    return {
                        'timestamp': timestamp,
                        'level': groups.get('level', 'INFO'),
                        'service_name': service_name,
                        'hostname': hostname,
                        'message': groups.get('message', line),
                        'raw_line': line,
                        'line_number': line_number,
                        'log_file': log_file,
                        'pattern_used': pattern_name
                    }
            
            # 如果没有匹配到模式，创建基本记录
            return {
                'timestamp': datetime.utcnow(),
                'level': 'UNKNOWN',
                'service_name': 'unknown',
                'hostname': 'unknown',
                'message': line,
                'raw_line': line,
                'line_number': line_number,
                'log_file': log_file,
                'pattern_used': 'fallback'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to parse log line {line_number}: {e}")
            return None
    
    async def process_log_file(self, file_path: str) -> Tuple[int, int]:
        """处理单个日志文件"""
        try:
            processed_count = 0
            error_count = 0
            
            file_name = os.path.basename(file_path)
            self.logger.info(f"Processing log file: {file_name}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 批量处理日志行
            batch_size = 50
            for i in range(0, len(lines), batch_size):
                batch_lines = lines[i:i + batch_size]
                await self._process_log_batch(batch_lines, i, file_name)
                processed_count += len(batch_lines)
            
            self.logger.info(f"Processed {processed_count} lines from {file_name}")
            return processed_count, error_count
            
        except Exception as e:
            self.logger.error(f"Failed to process log file {file_path}: {e}")
            return 0, 1
    
    async def _process_log_batch(self, lines: List[str], start_line: int, log_file: str):
        """批量处理日志行"""
        try:
            tasks = []
            
            for idx, line in enumerate(lines):
                line_number = start_line + idx + 1
                parsed_log = self.parse_log_line(line, line_number, log_file)
                
                if parsed_log:
                    # 为每行日志创建处理任务
                    task = self._index_log_entry(parsed_log)
                    tasks.append(task)
            
            # 并行执行所有任务
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            self.logger.error(f"Failed to process log batch: {e}")
    
    async def _index_log_entry(self, log_data: Dict[str, Any]):
        """为单个日志条目建立索引"""
        try:
            content = log_data['message']
            title = f"[{log_data['level']}] {log_data['service_name']} - Line {log_data['line_number']}"
            
            # 生成向量表示
            embedding = None
            try:
                embedding = await self.embedding_service.encode_text(content)
            except Exception as e:
                self.logger.warning(f"Failed to generate embedding for log line {log_data['line_number']}: {e}")
            
            # 提取关键词和实体（简单版本）
            keywords = self._extract_keywords(content)
            entities = self._extract_entities(content)
            
            # 生成唯一的source_id
            source_id = f"log_{log_data['log_file']}_{log_data['line_number']}"
            
            # 索引到EmbeddingCollection
            if embedding:
                await self.rag_service.add_embedding_document(
                    content=content,
                    title=title,
                    source_type="logs",
                    source_id=source_id,
                    service_name=log_data['service_name'],
                    hostname=log_data['hostname'],
                    log_file=log_data['log_file'],
                    line_number=log_data['line_number'],
                    log_level=log_data['level'],
                    timestamp=log_data['timestamp'],
                    category="系统日志",
                    tags=keywords,
                    metadata={
                        'raw_line': log_data['raw_line'],
                        'pattern_used': log_data['pattern_used']
                    },
                    vector=embedding
                )
            
            # 索引到FullTextCollection
            await self.rag_service.add_fulltext_document(
                content=content,
                title=title,
                source_type="logs",
                source_id=source_id,
                service_name=log_data['service_name'],
                hostname=log_data['hostname'],
                log_file=log_data['log_file'],
                line_number=log_data['line_number'],
                log_level=log_data['level'],
                timestamp=log_data['timestamp'],
                category="系统日志",
                tags=keywords,
                metadata={
                    'raw_line': log_data['raw_line'],
                    'pattern_used': log_data['pattern_used']
                },
                keywords=keywords,
                entities=entities
            )
            
        except Exception as e:
            self.logger.error(f"Failed to index log entry: {e}")
    
    def _extract_keywords(self, content: str) -> List[str]:
        """提取关键词（简单实现）"""
        try:
            # 常见的运维关键词
            keywords = []
            content_lower = content.lower()
            
            # 系统指标关键词
            metric_keywords = [
                'cpu', 'memory', 'disk', 'network', 'io', 'latency', 'throughput',
                'error', 'exception', 'timeout', 'connection', 'gc', 'heap',
                'pool', 'queue', 'batch', 'request', 'response'
            ]
            
            # 日志级别和状态
            status_keywords = [
                'failed', 'success', 'warning', 'critical', 'started', 'stopped',
                'restart', 'killed', 'healthy', 'unhealthy'
            ]
            
            all_keywords = metric_keywords + status_keywords
            
            for keyword in all_keywords:
                if keyword in content_lower:
                    keywords.append(keyword)
            
            # 提取数字指标
            metric_patterns = [
                r'(\d+)%',  # 百分比
                r'(\d+)ms',  # 毫秒
                r'(\d+)mb',  # 内存
                r'(\d+)gb',  # 内存
                r'(\d+)/(\d+)',  # 比例
            ]
            
            for pattern in metric_patterns:
                matches = re.findall(pattern, content_lower)
                if matches:
                    keywords.extend([f'metric_{match}' if isinstance(match, str) else f'metric_{match[0]}' for match in matches])
            
            return list(set(keywords))  # 去重
            
        except Exception as e:
            self.logger.error(f"Failed to extract keywords: {e}")
            return []
    
    def _extract_entities(self, content: str) -> List[str]:
        """提取实体（简单实现）"""
        try:
            entities = []
            content_lower = content.lower()
            
            # 服务名实体
            service_patterns = [
                r'service-[a-z]',
                r'api-gateway',
                r'database',
                r'redis',
                r'nginx'
            ]
            
            for pattern in service_patterns:
                matches = re.findall(pattern, content_lower)
                entities.extend([f'service:{match}' for match in matches])
            
            # 技术栈实体
            tech_entities = [
                'mysql', 'redis', 'nginx', 'kubernetes', 'docker',
                'java', 'python', 'node', 'elasticsearch'
            ]
            
            for tech in tech_entities:
                if tech in content_lower:
                    entities.append(f'tech:{tech}')
            
            return list(set(entities))  # 去重
            
        except Exception as e:
            self.logger.error(f"Failed to extract entities: {e}")
            return []
    
    async def process_all_logs(self, logs_dir: str = "./data/logs/") -> Dict[str, Any]:
        """处理所有日志文件"""
        try:
            start_time = datetime.utcnow()
            
            # 首先创建schema
            await self.rag_service.create_rag_schema()
            
            stats = {
                'total_files': 0,
                'processed_files': 0,
                'total_lines': 0,
                'error_files': 0,
                'processing_time': 0.0
            }
            
            logs_path = Path(logs_dir)
            if not logs_path.exists():
                raise FileNotFoundError(f"Logs directory not found: {logs_dir}")
            
            # 获取所有日志文件
            log_files = list(logs_path.glob("*.log")) + list(logs_path.glob("*.txt"))
            stats['total_files'] = len(log_files)
            
            self.logger.info(f"Found {len(log_files)} log files to process")
            
            # 处理每个文件
            for log_file in log_files:
                try:
                    processed_lines, error_lines = await self.process_log_file(str(log_file))
                    stats['total_lines'] += processed_lines
                    stats['processed_files'] += 1
                    self.logger.info(f"Processed {log_file.name}: {processed_lines} lines")
                except Exception as e:
                    self.logger.error(f"Failed to process {log_file}: {e}")
                    stats['error_files'] += 1
            
            # 计算处理时间
            end_time = datetime.utcnow()
            stats['processing_time'] = (end_time - start_time).total_seconds()
            
            self.logger.info(f"Log processing completed: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to process all logs: {e}")
            raise
    
    async def process_structured_logs(self, logs_dir: str = "./data/logs/") -> Dict[str, Any]:
        """处理结构化日志数据（针对incident日志）"""
        try:
            start_time = datetime.utcnow()
            
            stats = {
                'incidents_processed': 0,
                'total_log_entries': 0,
                'error_count': 0
            }
            
            logs_path = Path(logs_dir)
            incident_files = list(logs_path.glob("incident_*.log"))
            
            for incident_file in incident_files:
                try:
                    # 从文件名提取incident信息
                    incident_info = self._extract_incident_info(incident_file.name)
                    
                    # 处理该incident的日志
                    entry_count = await self._process_incident_logs(
                        str(incident_file), 
                        incident_info
                    )
                    
                    stats['incidents_processed'] += 1
                    stats['total_log_entries'] += entry_count
                    
                    self.logger.info(f"Processed incident {incident_info['incident_id']}: {entry_count} entries")
                    
                except Exception as e:
                    self.logger.error(f"Failed to process incident file {incident_file}: {e}")
                    stats['error_count'] += 1
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            stats['processing_time'] = processing_time
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to process structured logs: {e}")
            raise
    
    def _extract_incident_info(self, filename: str) -> Dict[str, Any]:
        """从文件名提取incident信息"""
        try:
            # 解析文件名模式: incident_001_service_b_cpu_overload.log
            parts = filename.replace('.log', '').split('_')
            
            incident_id = f"INC-{parts[1]}" if len(parts) > 1 else "INC-UNKNOWN"
            
            # 推断问题类型
            problem_type = "unknown"
            if "cpu" in filename:
                problem_type = "cpu_overload"
            elif "disk" in filename:
                problem_type = "disk_io_bottleneck"
            elif "network" in filename:
                problem_type = "network_partition"
            elif "memory" in filename:
                problem_type = "memory_leak"
            
            # 推断服务名
            service_name = "unknown"
            if "service_a" in filename:
                service_name = "service-a"
            elif "service_b" in filename:
                service_name = "service-b"
            elif "service_c" in filename:
                service_name = "service-c"
            
            return {
                'incident_id': incident_id,
                'problem_type': problem_type,
                'primary_service': service_name,
                'filename': filename
            }
            
        except Exception as e:
            self.logger.error(f"Failed to extract incident info from {filename}: {e}")
            return {
                'incident_id': 'INC-UNKNOWN',
                'problem_type': 'unknown',
                'primary_service': 'unknown',
                'filename': filename
            }
    
    async def _process_incident_logs(self, file_path: str, incident_info: Dict[str, Any]) -> int:
        """处理特定incident的日志"""
        try:
            processed_count = 0
            
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 为这个incident添加特殊标签
            incident_tags = [
                incident_info['incident_id'],
                incident_info['problem_type'],
                f"service:{incident_info['primary_service']}"
            ]
            
            for line_num, line in enumerate(lines, 1):
                parsed_log = self.parse_log_line(line, line_num, incident_info['filename'])
                
                if parsed_log:
                    # 添加incident特定信息
                    parsed_log['incident_id'] = incident_info['incident_id']
                    parsed_log['problem_type'] = incident_info['problem_type']
                    
                    # 合并标签
                    log_keywords = self._extract_keywords(parsed_log['message'])
                    all_tags = incident_tags + log_keywords
                    
                    # 生成向量
                    embedding = None
                    try:
                        embedding = await self.embedding_service.encode_text(parsed_log['message'])
                    except Exception as e:
                        self.logger.warning(f"Failed to generate embedding: {e}")
                    
                    # 生成唯一ID
                    source_id = f"incident_{incident_info['incident_id']}_{line_num}"
                    
                    # 索引到两个Collection
                    await self._dual_index_log_entry(
                        parsed_log, 
                        source_id, 
                        all_tags, 
                        embedding
                    )
                    
                    processed_count += 1
            
            return processed_count
            
        except Exception as e:
            self.logger.error(f"Failed to process incident logs: {e}")
            return 0
    
    async def _dual_index_log_entry(
        self, 
        log_data: Dict[str, Any], 
        source_id: str, 
        tags: List[str], 
        embedding: Optional[List[float]]
    ):
        """同时索引到两个Collection"""
        try:
            content = log_data['message']
            title = f"[{log_data['level']}] {log_data['service_name']}"
            
            common_fields = {
                'content': content,
                'title': title,
                'source_type': 'logs',
                'source_id': source_id,
                'service_name': log_data['service_name'],
                'hostname': log_data['hostname'],
                'log_file': log_data['log_file'],
                'line_number': log_data['line_number'],
                'log_level': log_data['level'],
                'timestamp': log_data['timestamp'],
                'category': '系统日志',
                'tags': tags,
                'metadata': {
                    'raw_line': log_data['raw_line'],
                    'pattern_used': log_data['pattern_used'],
                    'incident_id': log_data.get('incident_id'),
                    'problem_type': log_data.get('problem_type')
                }
            }
            
            # 索引到EmbeddingCollection
            if embedding:
                await self.rag_service.add_embedding_document(
                    vector=embedding,
                    **common_fields
                )
            
            # 索引到FullTextCollection
            keywords = self._extract_keywords(content)
            entities = self._extract_entities(content)
            
            await self.rag_service.add_fulltext_document(
                keywords=keywords,
                entities=entities,
                **common_fields
            )
            
        except Exception as e:
            self.logger.error(f"Failed to dual index log entry: {e}")
    
    async def search_logs(
        self,
        query: str,
        search_type: str = "hybrid",
        service_name: Optional[str] = None,
        hostname: Optional[str] = None,
        log_file: Optional[str] = None,
        line_number_range: Optional[Tuple[int, int]] = None,
        timestamp_range: Optional[Tuple[datetime, datetime]] = None,
        log_level: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """搜索日志"""
        try:
            start_time = datetime.utcnow()
            
            if search_type == "vector" and hasattr(self.embedding_service, 'encode_query'):
                # 向量搜索
                query_vector = await self.embedding_service.encode_query(query)
                results = await self.rag_service.embedding_search(
                    query_vector=query_vector,
                    limit=limit,
                    service_name=service_name,
                    hostname=hostname,
                    log_file=log_file,
                    line_number_range=line_number_range,
                    timestamp_range=timestamp_range,
                    source_type="logs",
                    log_level=log_level
                )
                search_results = [{"collection": "embedding", **result} for result in results]
                
            elif search_type == "fulltext":
                # 全文搜索
                results = await self.rag_service.fulltext_search(
                    query=query,
                    limit=limit,
                    service_name=service_name,
                    hostname=hostname,
                    log_file=log_file,
                    line_number_range=line_number_range,
                    timestamp_range=timestamp_range,
                    source_type="logs",
                    log_level=log_level
                )
                search_results = [{"collection": "fulltext", **result} for result in results]
                
            else:  # hybrid
                # 混合搜索
                query_vector = await self.embedding_service.encode_query(query)
                hybrid_results = await self.rag_service.hybrid_search_with_rerank(
                    query=query,
                    query_vector=query_vector,
                    limit=limit,
                    service_name=service_name,
                    hostname=hostname,
                    log_file=log_file,
                    line_number_range=line_number_range,
                    timestamp_range=timestamp_range,
                    source_type="logs",
                    log_level=log_level
                )
                search_results = hybrid_results["merged_results"]
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                'results': search_results,
                'total': len(search_results),
                'query': query,
                'search_type': search_type,
                'filters': {
                    'service_name': service_name,
                    'hostname': hostname,
                    'log_file': log_file,
                    'line_number_range': line_number_range,
                    'timestamp_range': timestamp_range,
                    'log_level': log_level
                },
                'processing_time': processing_time
            }
            
        except Exception as e:
            self.logger.error(f"Log search failed: {e}")
            return {'results': [], 'total': 0, 'error': str(e)}


# 便利函数
async def run_log_pipeline():
    """运行日志处理管道"""
    pipeline = LogPipeline()
    try:
        # 处理结构化incident日志
        stats = await pipeline.process_structured_logs()
        print(f"Log pipeline completed: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Log pipeline failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_log_pipeline())