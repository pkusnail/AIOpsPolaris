"""
Prometheus监控指标服务
收集和暴露系统运行指标
"""

import time
import logging
from typing import Dict, Any, Optional, List
from functools import wraps
from contextlib import contextmanager
from datetime import datetime

from prometheus_client import (
    Counter, Histogram, Gauge, Info, 
    CollectorRegistry, generate_latest, 
    CONTENT_TYPE_LATEST
)

logger = logging.getLogger(__name__)


class MetricsService:
    """Prometheus指标服务"""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 初始化指标
        self._init_metrics()
        self.logger.info("Metrics service initialized")
    
    def _init_metrics(self):
        """初始化Prometheus指标"""
        
        # HTTP请求指标
        self.http_requests_total = Counter(
            'aiops_http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.http_request_duration = Histogram(
            'aiops_http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        self.http_requests_in_progress = Gauge(
            'aiops_http_requests_in_progress',
            'Number of HTTP requests currently being processed',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # Agent执行指标
        self.agent_executions_total = Counter(
            'aiops_agent_executions_total',
            'Total agent executions',
            ['agent_type', 'status'],
            registry=self.registry
        )
        
        self.agent_execution_duration = Histogram(
            'aiops_agent_execution_duration_seconds',
            'Agent execution duration in seconds',
            ['agent_type'],
            registry=self.registry
        )
        
        self.agent_active = Gauge(
            'aiops_agent_active',
            'Number of active agents',
            ['agent_type'],
            registry=self.registry
        )
        
        # 搜索服务指标
        self.search_requests_total = Counter(
            'aiops_search_requests_total',
            'Total search requests',
            ['search_type', 'source'],
            registry=self.registry
        )
        
        self.search_duration = Histogram(
            'aiops_search_duration_seconds',
            'Search request duration in seconds',
            ['search_type'],
            registry=self.registry
        )
        
        self.search_results_count = Histogram(
            'aiops_search_results_count',
            'Number of search results returned',
            ['search_type'],
            registry=self.registry
        )
        
        # 数据库连接指标
        self.database_connections = Gauge(
            'aiops_database_connections',
            'Number of database connections',
            ['database_type', 'status'],
            registry=self.registry
        )
        
        self.database_operations_total = Counter(
            'aiops_database_operations_total',
            'Total database operations',
            ['database_type', 'operation', 'status'],
            registry=self.registry
        )
        
        self.database_operation_duration = Histogram(
            'aiops_database_operation_duration_seconds',
            'Database operation duration in seconds',
            ['database_type', 'operation'],
            registry=self.registry
        )
        
        # 会话和消息指标
        self.user_sessions_total = Counter(
            'aiops_user_sessions_total',
            'Total user sessions created',
            ['user_type'],
            registry=self.registry
        )
        
        self.active_sessions = Gauge(
            'aiops_active_sessions',
            'Number of active user sessions',
            registry=self.registry
        )
        
        self.messages_total = Counter(
            'aiops_messages_total',
            'Total messages processed',
            ['message_type', 'status'],
            registry=self.registry
        )
        
        self.message_tokens = Histogram(
            'aiops_message_tokens',
            'Number of tokens in messages',
            ['message_type'],
            registry=self.registry
        )
        
        # 系统资源指标
        self.system_info = Info(
            'aiops_system_info',
            'System information',
            registry=self.registry
        )
        
        self.memory_usage_bytes = Gauge(
            'aiops_memory_usage_bytes',
            'Memory usage in bytes',
            ['memory_type'],
            registry=self.registry
        )
        
        self.cpu_usage_percent = Gauge(
            'aiops_cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        # 缓存指标
        self.cache_operations_total = Counter(
            'aiops_cache_operations_total',
            'Total cache operations',
            ['cache_type', 'operation', 'result'],
            registry=self.registry
        )
        
        self.cache_hit_ratio = Gauge(
            'aiops_cache_hit_ratio',
            'Cache hit ratio',
            ['cache_type'],
            registry=self.registry
        )
        
        # 设置系统信息
        self.system_info.info({
            'version': '1.0.0',
            'python_version': '3.9+',
            'service_name': 'aiops-polaris'
        })
    
    # HTTP请求装饰器
    def track_http_request(self, endpoint: str):
        """装饰器：跟踪HTTP请求"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                method = kwargs.get('method', 'GET')
                start_time = time.time()
                
                # 增加进行中请求计数
                self.http_requests_in_progress.labels(
                    method=method, 
                    endpoint=endpoint
                ).inc()
                
                try:
                    result = await func(*args, **kwargs)
                    status_code = '200'
                    
                    # 记录成功请求
                    self.http_requests_total.labels(
                        method=method,
                        endpoint=endpoint,
                        status_code=status_code
                    ).inc()
                    
                    return result
                    
                except Exception as e:
                    status_code = '500'
                    # 记录失败请求
                    self.http_requests_total.labels(
                        method=method,
                        endpoint=endpoint,
                        status_code=status_code
                    ).inc()
                    raise
                finally:
                    # 记录请求时间
                    duration = time.time() - start_time
                    self.http_request_duration.labels(
                        method=method,
                        endpoint=endpoint
                    ).observe(duration)
                    
                    # 减少进行中请求计数
                    self.http_requests_in_progress.labels(
                        method=method,
                        endpoint=endpoint
                    ).dec()
                    
            return wrapper
        return decorator
    
    # Agent执行跟踪
    @contextmanager
    def track_agent_execution(self, agent_type: str):
        """上下文管理器：跟踪Agent执行"""
        start_time = time.time()
        
        # 增加活跃Agent计数
        self.agent_active.labels(agent_type=agent_type).inc()
        
        try:
            yield
            # 记录成功执行
            self.agent_executions_total.labels(
                agent_type=agent_type,
                status='success'
            ).inc()
        except Exception as e:
            # 记录失败执行
            self.agent_executions_total.labels(
                agent_type=agent_type,
                status='error'
            ).inc()
            raise
        finally:
            # 记录执行时间
            duration = time.time() - start_time
            self.agent_execution_duration.labels(
                agent_type=agent_type
            ).observe(duration)
            
            # 减少活跃Agent计数
            self.agent_active.labels(agent_type=agent_type).dec()
    
    # 搜索请求跟踪
    def record_search_request(self, search_type: str, source: str, 
                            duration: float, results_count: int):
        """记录搜索请求指标"""
        self.search_requests_total.labels(
            search_type=search_type,
            source=source or 'all'
        ).inc()
        
        self.search_duration.labels(
            search_type=search_type
        ).observe(duration)
        
        self.search_results_count.labels(
            search_type=search_type
        ).observe(results_count)
    
    # 数据库操作跟踪
    @contextmanager
    def track_database_operation(self, database_type: str, operation: str):
        """上下文管理器：跟踪数据库操作"""
        start_time = time.time()
        
        try:
            yield
            # 记录成功操作
            self.database_operations_total.labels(
                database_type=database_type,
                operation=operation,
                status='success'
            ).inc()
        except Exception as e:
            # 记录失败操作
            self.database_operations_total.labels(
                database_type=database_type,
                operation=operation,
                status='error'
            ).inc()
            raise
        finally:
            # 记录操作时间
            duration = time.time() - start_time
            self.database_operation_duration.labels(
                database_type=database_type,
                operation=operation
            ).observe(duration)
    
    def update_database_connections(self, database_type: str, 
                                  active_count: int, idle_count: int = 0):
        """更新数据库连接数"""
        self.database_connections.labels(
            database_type=database_type,
            status='active'
        ).set(active_count)
        
        if idle_count > 0:
            self.database_connections.labels(
                database_type=database_type,
                status='idle'
            ).set(idle_count)
    
    # 会话和消息跟踪
    def record_user_session(self, user_type: str = 'standard'):
        """记录新用户会话"""
        self.user_sessions_total.labels(user_type=user_type).inc()
    
    def update_active_sessions(self, count: int):
        """更新活跃会话数"""
        self.active_sessions.set(count)
    
    def record_message(self, message_type: str, status: str, token_count: int):
        """记录消息处理"""
        self.messages_total.labels(
            message_type=message_type,
            status=status
        ).inc()
        
        self.message_tokens.labels(
            message_type=message_type
        ).observe(token_count)
    
    # 系统资源监控
    def update_system_resources(self, memory_usage: Dict[str, int], 
                              cpu_usage: float):
        """更新系统资源使用情况"""
        for memory_type, usage in memory_usage.items():
            self.memory_usage_bytes.labels(
                memory_type=memory_type
            ).set(usage)
        
        self.cpu_usage_percent.set(cpu_usage)
    
    # 缓存操作跟踪
    def record_cache_operation(self, cache_type: str, operation: str, 
                             result: str):
        """记录缓存操作"""
        self.cache_operations_total.labels(
            cache_type=cache_type,
            operation=operation,
            result=result
        ).inc()
    
    def update_cache_hit_ratio(self, cache_type: str, ratio: float):
        """更新缓存命中率"""
        self.cache_hit_ratio.labels(cache_type=cache_type).set(ratio)
    
    # 指标导出
    def export_metrics(self) -> bytes:
        """导出Prometheus格式的指标"""
        return generate_latest(self.registry)
    
    def increment_counter(self, counter_name: str, labels: Dict[str, str] = None):
        """增加计数器"""
        if counter_name == "api_requests_total":
            endpoint = labels.get("endpoint", "") if labels else ""
            self.http_requests_total.labels(method="GET", endpoint=endpoint, status_code="200").inc()
    
    def get_prometheus_metrics(self) -> str:
        """获取Prometheus格式的指标"""
        return generate_latest(self.registry).decode('utf-8')
    
    def get_content_type(self) -> str:
        """获取指标内容类型"""
        return CONTENT_TYPE_LATEST
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要（用于健康检查）"""
        try:
            return {
                "metrics_enabled": True,
                "registry_collectors": len(self.registry._collector_to_names),
                "timestamp": datetime.utcnow().isoformat(),
                "export_format": "prometheus"
            }
        except Exception as e:
            self.logger.error(f"Failed to get metrics summary: {e}")
            return {
                "metrics_enabled": False,
                "error": str(e)
            }


# 全局实例
metrics_service = MetricsService()


def get_metrics_service() -> MetricsService:
    """获取指标服务实例"""
    return metrics_service