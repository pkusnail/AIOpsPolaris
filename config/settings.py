"""
应用程序配置管理
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional, List, Dict, Any
import os


class DatabaseSettings(BaseSettings):
    """数据库配置"""
    url: str = Field(
        default="mysql+aiomysql://aiops_user:aiops_pass@localhost:3306/aiops",
        description="数据库连接URL"
    )
    pool_size: int = Field(default=10, description="连接池大小")
    max_overflow: int = Field(default=20, description="最大溢出连接数")
    pool_recycle: int = Field(default=3600, description="连接回收时间(秒)")
    echo: bool = Field(default=False, description="是否打印SQL语句")

    class Config:
        env_prefix = "DATABASE_"


class Neo4jSettings(BaseSettings):
    """Neo4j配置"""
    uri: str = Field(default="bolt://localhost:7687", description="Neo4j连接URI")
    user: str = Field(default="neo4j", description="用户名")
    password: str = Field(default="aiops123", description="密码")
    max_connection_lifetime: int = Field(default=30 * 60, description="最大连接生命周期(秒)")
    max_connection_pool_size: int = Field(default=50, description="最大连接池大小")
    connection_acquisition_timeout: int = Field(default=60, description="连接获取超时(秒)")

    class Config:
        env_prefix = "NEO4J_"


class WeaviateSettings(BaseSettings):
    """Weaviate配置"""
    url: str = Field(default="http://localhost:8080", description="Weaviate服务URL")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    timeout: int = Field(default=30, description="请求超时时间(秒)")

    class Config:
        env_prefix = "WEAVIATE_"


class RedisSettings(BaseSettings):
    """Redis配置"""
    url: str = Field(default="redis://:aiops123@localhost:6379/0", description="Redis连接URL")
    max_connections: int = Field(default=20, description="最大连接数")
    retry_on_timeout: bool = Field(default=True, description="超时时重试")
    socket_timeout: int = Field(default=30, description="Socket超时时间(秒)")

    class Config:
        env_prefix = "REDIS_"


class LLMSettings(BaseSettings):
    """LLM配置"""
    api_base: str = Field(default="http://localhost:8000/v1", description="LLM API基础URL")
    api_key: str = Field(default="dummy", description="API密钥")
    model: str = Field(default="Qwen/Qwen2-7B-Instruct", description="模型名称")
    max_tokens: int = Field(default=4096, description="最大token数")
    temperature: float = Field(default=0.7, description="生成温度")
    timeout: int = Field(default=60, description="请求超时时间(秒)")

    class Config:
        env_prefix = "VLLM_"


class EmbeddingSettings(BaseSettings):
    """嵌入模型配置"""
    model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="嵌入模型名称"
    )
    device: str = Field(default="cpu", description="运行设备")
    batch_size: int = Field(default=32, description="批处理大小")
    max_seq_length: int = Field(default=512, description="最大序列长度")

    class Config:
        env_prefix = "EMBEDDING_"


class SearchSettings(BaseSettings):
    """搜索配置"""
    default_limit: int = Field(default=10, description="默认搜索结果数量")
    max_limit: int = Field(default=100, description="最大搜索结果数量")
    similarity_threshold: float = Field(default=0.7, description="相似度阈值")
    vector_weight: float = Field(default=0.7, description="向量搜索权重")
    keyword_weight: float = Field(default=0.3, description="关键词搜索权重")

    class Config:
        env_prefix = "SEARCH_"


class TaskSettings(BaseSettings):
    """任务配置"""
    max_workers: int = Field(default=4, description="最大工作进程数")
    task_timeout: int = Field(default=300, description="任务超时时间(秒)")
    retry_delay: int = Field(default=60, description="重试延迟时间(秒)")
    cleanup_interval: int = Field(default=3600, description="清理间隔时间(秒)")

    class Config:
        env_prefix = "TASK_"


class LoggingSettings(BaseSettings):
    """日志配置"""
    level: str = Field(default="INFO", description="日志级别")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    file: Optional[str] = Field(default=None, description="日志文件路径")
    max_bytes: int = Field(default=10 * 1024 * 1024, description="日志文件最大大小")
    backup_count: int = Field(default=5, description="日志文件备份数量")

    class Config:
        env_prefix = "LOG_"


class SecuritySettings(BaseSettings):
    """安全配置"""
    secret_key: str = Field(
        default="aiops-secret-key-change-in-production",
        description="应用密钥"
    )
    algorithm: str = Field(default="HS256", description="JWT算法")
    access_token_expire_minutes: int = Field(default=30, description="访问令牌过期时间(分钟)")
    refresh_token_expire_days: int = Field(default=7, description="刷新令牌过期时间(天)")

    class Config:
        env_prefix = "SECURITY_"


class APISettings(BaseSettings):
    """API配置"""
    host: str = Field(default="0.0.0.0", description="服务器主机")
    port: int = Field(default=8000, description="服务器端口")
    workers: int = Field(default=1, description="工作进程数")
    reload: bool = Field(default=False, description="自动重载")
    cors_origins: List[str] = Field(
        default=["*"],
        description="CORS允许的源"
    )
    rate_limit: int = Field(default=100, description="速率限制(每分钟请求数)")

    class Config:
        env_prefix = "API_"


class MonitoringSettings(BaseSettings):
    """监控配置"""
    enable_metrics: bool = Field(default=True, description="启用指标收集")
    metrics_path: str = Field(default="/metrics", description="指标路径")
    health_check_path: str = Field(default="/health", description="健康检查路径")
    alert_webhook_url: Optional[str] = Field(default=None, description="告警Webhook URL")

    class Config:
        env_prefix = "MONITORING_"


class Settings(BaseSettings):
    """应用程序主配置"""
    
    # 基本信息
    app_name: str = Field(default="AIOps Polaris", description="应用名称")
    app_version: str = Field(default="1.0.0", description="应用版本")
    debug: bool = Field(default=False, description="调试模式")
    environment: str = Field(default="development", description="运行环境")

    # 各组件配置
    database: DatabaseSettings = DatabaseSettings()
    neo4j: Neo4jSettings = Neo4jSettings()
    weaviate: WeaviateSettings = WeaviateSettings()
    redis: RedisSettings = RedisSettings()
    llm: LLMSettings = LLMSettings()
    embedding: EmbeddingSettings = EmbeddingSettings()
    search: SearchSettings = SearchSettings()
    task: TaskSettings = TaskSettings()
    logging: LoggingSettings = LoggingSettings()
    security: SecuritySettings = SecuritySettings()
    api: APISettings = APISettings()
    monitoring: MonitoringSettings = MonitoringSettings()

    @validator("environment")
    def validate_environment(cls, v):
        allowed = ["development", "testing", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v

    def get_database_url(self) -> str:
        """获取数据库连接URL"""
        return self.database.url

    def get_neo4j_config(self) -> Dict[str, Any]:
        """获取Neo4j配置"""
        return {
            "uri": self.neo4j.uri,
            "auth": (self.neo4j.user, self.neo4j.password),
            "max_connection_lifetime": self.neo4j.max_connection_lifetime,
            "max_connection_pool_size": self.neo4j.max_connection_pool_size,
            "connection_acquisition_timeout": self.neo4j.connection_acquisition_timeout
        }

    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == "production"

    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.environment == "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 全局设置实例
settings = Settings()

# 导出常用配置
DATABASE_URL = settings.get_database_url()
NEO4J_CONFIG = settings.get_neo4j_config()
REDIS_URL = settings.redis.url
WEAVIATE_URL = settings.weaviate.url
LLM_API_BASE = settings.llm.api_base