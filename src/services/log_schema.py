"""
Weaviate Collections Schema for Log Processing
两个collection的数据模式定义：LogEntry (全文搜索) 和 LogEmbedding (向量搜索)
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

# Collection 1: LogEntry - 全文搜索优化
LOG_ENTRY_SCHEMA = {
    "class": "LogEntry",
    "description": "Structured log entries optimized for full-text search and filtering",
    "properties": [
        {
            "name": "timestamp",
            "dataType": ["date"],
            "description": "Log timestamp in RFC3339 format",
            "indexFilterable": True,
            "indexSearchable": False
        },
        {
            "name": "service_name", 
            "dataType": ["text"],
            "description": "Name of the service generating the log",
            "indexFilterable": True,
            "indexSearchable": True,
            "tokenization": "keyword"  # 精确匹配
        },
        {
            "name": "host_ip",
            "dataType": ["text"], 
            "description": "IP address of the host machine",
            "indexFilterable": True,
            "indexSearchable": True,
            "tokenization": "keyword"
        },
        {
            "name": "host_name",
            "dataType": ["text"],
            "description": "Hostname or machine identifier", 
            "indexFilterable": True,
            "indexSearchable": True,
            "tokenization": "keyword"
        },
        {
            "name": "log_level",
            "dataType": ["text"],
            "description": "Log level (INFO, WARN, ERROR, CRITICAL)",
            "indexFilterable": True,
            "indexSearchable": False,
            "tokenization": "keyword"
        },
        {
            "name": "message",
            "dataType": ["text"],
            "description": "Raw log message content",
            "indexFilterable": False,
            "indexSearchable": True,
            "tokenization": "word"  # 全文搜索
        },
        {
            "name": "component",
            "dataType": ["text"],
            "description": "Component or module within the service",
            "indexFilterable": True,
            "indexSearchable": True,
            "tokenization": "keyword"
        },
        {
            "name": "thread_id",
            "dataType": ["text"],
            "description": "Thread or process identifier",
            "indexFilterable": True,
            "indexSearchable": False,
            "tokenization": "keyword"
        },
        {
            "name": "request_id", 
            "dataType": ["text"],
            "description": "Request correlation ID for tracing",
            "indexFilterable": True,
            "indexSearchable": False,
            "tokenization": "keyword"
        },
        {
            "name": "error_code",
            "dataType": ["text"],
            "description": "Error code if applicable",
            "indexFilterable": True,
            "indexSearchable": False,
            "tokenization": "keyword"
        },
        {
            "name": "duration_ms",
            "dataType": ["number"],
            "description": "Operation duration in milliseconds",
            "indexFilterable": True,
            "indexSearchable": False
        },
        {
            "name": "tags",
            "dataType": ["text[]"],
            "description": "Additional tags for categorization",
            "indexFilterable": True, 
            "indexSearchable": True,
            "tokenization": "keyword"
        },
        {
            "name": "metadata",
            "dataType": ["object"],
            "description": "Additional structured metadata as JSON",
            "indexFilterable": False,
            "indexSearchable": False
        }
    ],
    "vectorizer": "none",  # 不生成向量，纯全文搜索
}

# Collection 2: LogEmbedding - 向量搜索优化  
LOG_EMBEDDING_SCHEMA = {
    "class": "LogEmbedding",
    "description": "Log entries with semantic embeddings for vector similarity search",
    "properties": [
        {
            "name": "timestamp",
            "dataType": ["date"],
            "description": "Log timestamp",
            "indexFilterable": True,
            "indexSearchable": False
        },
        {
            "name": "service_name",
            "dataType": ["text"], 
            "description": "Service name for filtering",
            "indexFilterable": True,
            "indexSearchable": False,
            "tokenization": "keyword"
        },
        {
            "name": "host_ip",
            "dataType": ["text"],
            "description": "Host IP for filtering",
            "indexFilterable": True,
            "indexSearchable": False,
            "tokenization": "keyword"
        },
        {
            "name": "log_level",
            "dataType": ["text"],
            "description": "Log level for filtering",
            "indexFilterable": True,
            "indexSearchable": False,
            "tokenization": "keyword"
        },
        {
            "name": "content",
            "dataType": ["text"],
            "description": "Processed log content for embedding generation",
            "indexFilterable": False,
            "indexSearchable": True,
            "tokenization": "word"
        },
        {
            "name": "summary",
            "dataType": ["text"],
            "description": "AI-generated summary of the log entry",
            "indexFilterable": False,
            "indexSearchable": True,
            "tokenization": "word"
        },
        {
            "name": "category",
            "dataType": ["text"],
            "description": "AI-classified log category",
            "indexFilterable": True,
            "indexSearchable": True,
            "tokenization": "keyword"
        },
        {
            "name": "severity_score",
            "dataType": ["number"],
            "description": "AI-computed severity score (0-1)",
            "indexFilterable": True,
            "indexSearchable": False
        },
        {
            "name": "incident_id",
            "dataType": ["text"],
            "description": "Associated incident ID if applicable",
            "indexFilterable": True,
            "indexSearchable": False,
            "tokenization": "keyword"
        },
        {
            "name": "log_entry_id",
            "dataType": ["text"],
            "description": "Reference to original LogEntry UUID",
            "indexFilterable": True,
            "indexSearchable": False,
            "tokenization": "keyword"
        }
    ],
    "vectorizer": "text2vec-transformers",  # 使用transformer生成向量
    "moduleConfig": {
        "text2vec-transformers": {
            "vectorizeClassName": False,
            "vectorizePropertyName": False,
            "textFields": ["content", "summary"]  # 基于这些字段生成向量
        }
    }
}

@dataclass
class LogEntry:
    """LogEntry数据类"""
    timestamp: datetime
    service_name: str
    host_ip: str
    host_name: str
    log_level: str
    message: str
    component: Optional[str] = None
    thread_id: Optional[str] = None
    request_id: Optional[str] = None
    error_code: Optional[str] = None
    duration_ms: Optional[float] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_weaviate_object(self) -> Dict[str, Any]:
        """转换为Weaviate对象格式"""
        return {
            "timestamp": self.timestamp.isoformat() + "Z",
            "service_name": self.service_name,
            "host_ip": self.host_ip,
            "host_name": self.host_name,
            "log_level": self.log_level,
            "message": self.message,
            "component": self.component,
            "thread_id": self.thread_id,
            "request_id": self.request_id,
            "error_code": self.error_code,
            "duration_ms": self.duration_ms,
            "tags": self.tags or [],
            "metadata": self.metadata or {}
        }

@dataclass 
class LogEmbedding:
    """LogEmbedding数据类"""
    timestamp: datetime
    service_name: str
    host_ip: str
    log_level: str
    content: str
    summary: str
    category: str
    severity_score: float
    incident_id: Optional[str] = None
    log_entry_id: Optional[str] = None
    
    def to_weaviate_object(self) -> Dict[str, Any]:
        """转换为Weaviate对象格式"""
        return {
            "timestamp": self.timestamp.isoformat() + "Z",
            "service_name": self.service_name,
            "host_ip": self.host_ip,
            "log_level": self.log_level,
            "content": self.content,
            "summary": self.summary,
            "category": self.category,
            "severity_score": self.severity_score,
            "incident_id": self.incident_id,
            "log_entry_id": self.log_entry_id
        }

# 查询过滤器定义
class LogQueryFilters:
    """日志查询过滤器"""
    
    @staticmethod
    def time_range_filter(start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """时间窗口过滤器"""
        return {
            "path": "timestamp",
            "operator": "And",
            "operands": [
                {
                    "path": "timestamp", 
                    "operator": "GreaterThanEqual",
                    "valueDate": start_time.isoformat() + "Z"
                },
                {
                    "path": "timestamp",
                    "operator": "LessThanEqual", 
                    "valueDate": end_time.isoformat() + "Z"
                }
            ]
        }
    
    @staticmethod
    def service_filter(service_names: List[str]) -> Dict[str, Any]:
        """服务名称过滤器"""
        if len(service_names) == 1:
            return {
                "path": "service_name",
                "operator": "Equal",
                "valueText": service_names[0]
            }
        else:
            return {
                "operator": "Or",
                "operands": [
                    {
                        "path": "service_name",
                        "operator": "Equal",
                        "valueText": name
                    } for name in service_names
                ]
            }
    
    @staticmethod
    def host_filter(host_ips: List[str]) -> Dict[str, Any]:
        """主机IP过滤器"""
        if len(host_ips) == 1:
            return {
                "path": "host_ip",
                "operator": "Equal", 
                "valueText": host_ips[0]
            }
        else:
            return {
                "operator": "Or",
                "operands": [
                    {
                        "path": "host_ip",
                        "operator": "Equal",
                        "valueText": ip
                    } for ip in host_ips
                ]
            }
    
    @staticmethod
    def log_level_filter(levels: List[str]) -> Dict[str, Any]:
        """日志级别过滤器"""
        if len(levels) == 1:
            return {
                "path": "log_level",
                "operator": "Equal",
                "valueText": levels[0]
            }
        else:
            return {
                "operator": "Or", 
                "operands": [
                    {
                        "path": "log_level",
                        "operator": "Equal",
                        "valueText": level
                    } for level in levels
                ]
            }
            
    @staticmethod
    def combine_filters(*filters) -> Dict[str, Any]:
        """组合多个过滤器"""
        valid_filters = [f for f in filters if f is not None]
        if not valid_filters:
            return None
        elif len(valid_filters) == 1:
            return valid_filters[0]
        else:
            return {
                "operator": "And",
                "operands": valid_filters
            }