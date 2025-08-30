"""
系统配置相关模型
"""

from sqlalchemy import Column, String, Text, DateTime, JSON, Integer
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import ENUM
from .database import Base
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_config"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    config_key = Column(String(100), unique=True, nullable=False, index=True)
    config_value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class TaskQueue(Base):
    """任务队列表"""
    __tablename__ = "task_queue"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_type = Column(String(100), nullable=False, index=True)
    task_data = Column(JSON, nullable=False)
    status = Column(ENUM("pending", "running", "completed", "failed"), 
                   default="pending", index=True)
    priority = Column(Integer, default=0, index=True)
    max_retries = Column(Integer, default=3)
    retry_count = Column(Integer, default=0)
    scheduled_at = Column(DateTime, default=func.now(), index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# Pydantic模型用于API交互
class SystemConfigCreate(BaseModel):
    """创建系统配置请求模型"""
    config_key: str = Field(..., description="配置键")
    config_value: Any = Field(..., description="配置值")
    description: Optional[str] = Field(None, description="配置描述")


class SystemConfigUpdate(BaseModel):
    """更新系统配置请求模型"""
    config_value: Any = Field(..., description="配置值")
    description: Optional[str] = Field(None, description="配置描述")


class SystemConfigResponse(BaseModel):
    """系统配置响应模型"""
    id: str
    config_key: str
    config_value: Any
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    """创建任务请求模型"""
    task_type: str = Field(..., description="任务类型")
    task_data: Dict[str, Any] = Field(..., description="任务数据")
    priority: int = Field(default=0, description="任务优先级")
    max_retries: int = Field(default=3, ge=0, le=10, description="最大重试次数")
    scheduled_at: Optional[datetime] = Field(None, description="计划执行时间")


class TaskResponse(BaseModel):
    """任务响应模型"""
    id: str
    task_type: str
    task_data: Dict[str, Any]
    status: TaskStatus
    priority: int
    max_retries: int
    retry_count: int
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskUpdate(BaseModel):
    """任务更新模型"""
    status: Optional[TaskStatus] = Field(None, description="任务状态")
    error_message: Optional[str] = Field(None, description="错误信息")
    result: Optional[Dict[str, Any]] = Field(None, description="任务结果")


class TaskListResponse(BaseModel):
    """任务列表响应模型"""
    tasks: List[TaskResponse]
    total: int
    page: int
    page_size: int


class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    timestamp: datetime = Field(..., description="检查时间")
    version: str = Field(..., description="服务版本")
    components: Dict[str, Dict[str, Any]] = Field(..., description="组件状态")


class SystemStats(BaseModel):
    """系统统计信息"""
    total_users: int = Field(..., description="总用户数")
    total_sessions: int = Field(..., description="总会话数")
    total_messages: int = Field(..., description="总消息数")
    total_documents: int = Field(..., description="总文档数")
    total_entities: int = Field(..., description="总实体数")
    total_relationships: int = Field(..., description="总关系数")
    active_tasks: int = Field(..., description="活跃任务数")
    failed_tasks: int = Field(..., description="失败任务数")
    avg_response_time: float = Field(..., description="平均响应时间")
    uptime: float = Field(..., description="运行时间(秒)")


class LogLevel(str, Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogEntry(BaseModel):
    """日志条目模型"""
    timestamp: datetime = Field(..., description="时间戳")
    level: LogLevel = Field(..., description="日志级别")
    message: str = Field(..., description="日志消息")
    module: str = Field(..., description="模块名称")
    function: str = Field(..., description="函数名称")
    extra: Optional[Dict[str, Any]] = Field(None, description="额外信息")


class SystemMetrics(BaseModel):
    """系统指标模型"""
    cpu_usage: float = Field(..., description="CPU使用率")
    memory_usage: float = Field(..., description="内存使用率")
    disk_usage: float = Field(..., description="磁盘使用率")
    network_io: Dict[str, float] = Field(..., description="网络IO")
    database_connections: int = Field(..., description="数据库连接数")
    cache_hit_rate: float = Field(..., description="缓存命中率")
    api_requests_per_minute: int = Field(..., description="每分钟API请求数")
    error_rate: float = Field(..., description="错误率")


class AlertRule(BaseModel):
    """告警规则模型"""
    name: str = Field(..., description="规则名称")
    condition: str = Field(..., description="告警条件")
    threshold: float = Field(..., description="告警阈值")
    severity: str = Field(..., description="严重程度")
    enabled: bool = Field(default=True, description="是否启用")


class Alert(BaseModel):
    """告警模型"""
    id: str = Field(..., description="告警ID")
    rule_name: str = Field(..., description="规则名称")
    message: str = Field(..., description="告警信息")
    severity: str = Field(..., description="严重程度")
    triggered_at: datetime = Field(..., description="触发时间")
    resolved_at: Optional[datetime] = Field(None, description="解决时间")
    status: str = Field(..., description="告警状态")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")