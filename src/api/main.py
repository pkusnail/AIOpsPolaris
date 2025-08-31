"""
AIOps Polaris API - 统一版本
结合了完整功能和LLM适配器的智能运维平台API
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
import structlog
import psutil

# 导入模型
from ..models.system import HealthCheckResponse, SystemStats
from ..services.embedding_service import EmbeddingService
from ..services.database_service import DatabaseService
from ..services.metrics_service import get_metrics_service, MetricsService
from ..services.llm_adapter import get_llm_adapter, LLMAdapter
from ..agents import AIOpsGraph

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局服务实例
database_service: Optional[DatabaseService] = None
embedding_service: Optional[EmbeddingService] = None
aiops_graph: Optional[AIOpsGraph] = None
metrics_service: Optional[MetricsService] = None
llm_adapter: Optional[LLMAdapter] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    try:
        global database_service, embedding_service, aiops_graph, metrics_service, llm_adapter
        
        # 初始化监控服务
        metrics_service = get_metrics_service()
        
        # 初始化基础服务
        database_service = DatabaseService()
        embedding_service = EmbeddingService()
        
        # 初始化LLM适配器
        llm_adapter = get_llm_adapter()
        
        # 初始化AIOps主图
        aiops_graph = AIOpsGraph()
        
        logger.info("AIOps services initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        logger.error(traceback.format_exc())
        raise
    finally:
        # 清理资源
        if embedding_service:
            embedding_service.close()
        logger.info("AIOps services cleaned up")


# 创建FastAPI应用
app = FastAPI(
    title="AIOps Polaris API",
    description="智能运维平台API - 统一版本",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 依赖注入函数
def get_database_service() -> DatabaseService:
    if database_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service not initialized"
        )
    return database_service


def get_embedding_service() -> EmbeddingService:
    if embedding_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Embedding service not initialized"
        )
    return embedding_service


def get_aiops_graph() -> AIOpsGraph:
    if aiops_graph is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AIOps graph not initialized"
        )
    return aiops_graph


def get_metrics_service_dep() -> MetricsService:
    if metrics_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metrics service not initialized"
        )
    return metrics_service


def get_llm_adapter_dep() -> LLMAdapter:
    if llm_adapter is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM adapter not initialized"
        )
    return llm_adapter


# API 端点

@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "AIOps Polaris API - 智能运维平台",
        "version": "1.0.0",
        "timestamp": datetime.now(),
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "metrics": "/metrics", 
            "stats": "/stats",
            "chat": "/chat",
            "chat_stream": "/chat/stream",
            "task_status": "/chat/task_status/{task_id}",
            "llm_info": "/llm/info",
            "llm_reload": "/llm/reload"
        }
    }


@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint(metrics_svc: MetricsService = Depends(get_metrics_service_dep)):
    """Prometheus指标导出端点"""
    try:
        metrics_svc.increment_counter("api_requests_total", {"endpoint": "/metrics"})
        
        # 更新系统资源指标
        metrics_svc.update_system_resources()
        
        # 更新服务状态
        metrics_svc.update_service_status("database", database_service is not None)
        metrics_svc.update_service_status("embedding", embedding_service is not None)
        metrics_svc.update_service_status("aiops_graph", aiops_graph is not None)
        metrics_svc.update_service_status("llm", llm_adapter is not None)
        
        return PlainTextResponse(
            content=metrics_svc.get_prometheus_metrics(),
            media_type=metrics_svc.get_content_type()
        )
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get metrics"
        )


@app.get("/health", response_model=HealthCheckResponse)
async def health_check(metrics_svc: MetricsService = Depends(get_metrics_service_dep)):
    """健康检查"""
    try:
        metrics_svc.increment_counter("api_requests_total", {"endpoint": "/health"})
        
        # 检查各服务状态
        services = {
            "database": "healthy" if database_service else "unavailable",
            "embedding": "healthy" if embedding_service else "unavailable",
            "aiops_graph": "healthy" if aiops_graph else "unavailable",
            "metrics": "healthy" if metrics_service else "unavailable",
            "llm": "healthy" if llm_adapter else "unavailable"
        }
        
        # 系统状态
        system_status = "healthy"
        if any(status != "healthy" for status in services.values()):
            system_status = "degraded"
        
        return HealthCheckResponse(
            status=system_status,
            timestamp=datetime.now(),
            version="1.0.0",
            components={
                "database": {"status": "healthy" if database_service else "unavailable", "type": "mysql"},
                "embedding": {"status": "healthy" if embedding_service else "unavailable", "type": "service"},
                "aiops_graph": {"status": "healthy" if aiops_graph else "unavailable", "type": "graph"},
                "metrics": {"status": "healthy" if metrics_service else "unavailable", "type": "monitoring"},
                "llm": {"status": "healthy" if llm_adapter else "unavailable", "type": "language_model"}
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            version="1.0.0",
            components={"error": {"status": "error", "message": str(e)}}
        )


@app.get("/stats", response_model=Dict[str, Any])
async def get_system_stats(
    metrics_svc: MetricsService = Depends(get_metrics_service_dep)
):
    """获取系统统计信息"""
    try:
        metrics_svc.increment_counter("api_requests_total", {"endpoint": "/stats"})
        
        # 获取系统信息
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage('/')
        
        return {
            "system": {
                "cpu_usage": cpu_percent,
                "memory_usage": memory.percent,
                "memory_total": memory.total,
                "memory_available": memory.available,
                "disk_usage": (disk.used / disk.total) * 100,
                "disk_total": disk.total,
                "disk_free": disk.free
            },
            "services": {
                "database": "active" if database_service else "inactive",
                "embedding": "active" if embedding_service else "inactive",
                "aiops_graph": "active" if aiops_graph else "inactive",
                "llm": "active" if llm_adapter else "inactive"
            },
            "version": "1.0.0",
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system stats: {str(e)}"
        )


@app.post("/chat", response_model=Dict[str, Any])
async def chat(
    request: Dict[str, Any],
    llm: LLMAdapter = Depends(get_llm_adapter_dep),
    metrics_svc: MetricsService = Depends(get_metrics_service_dep)
):
    """智能聊天端点 - 集成完整RCA流程"""
    start_time = datetime.now()
    provider_name = "unknown"
    
    try:
        metrics_svc.increment_counter("api_requests_total", {"endpoint": "/chat"})
        
        query = request.get("message", "")
        if not query:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message is required"
            )
        
        # 获取提供商信息
        provider_info = llm.get_provider_info()
        provider_name = provider_info.get("provider", "unknown")
        
        # 优先尝试使用RCA聊天服务
        try:
            from .rca_chat_endpoint import process_rca_chat_request
            
            logger.info(f"尝试使用RCA聊天服务处理查询: {query[:50]}...")
            rca_result = await process_rca_chat_request(request)
            
            # 记录成功的RCA请求
            duration = (datetime.now() - start_time).total_seconds()
            metrics_svc.record_llm_request(
                provider="rca_pipeline",
                duration=duration,
                status="success",
                input_tokens=len(query.split()),
                output_tokens=len(rca_result.get("response", "").split())
            )
            
            return {
                "response": rca_result.get("response", "RCA分析完成，但响应为空"),
                "timestamp": datetime.now(),
                "session_id": request.get("session_id", "demo-session"),
                "llm_provider": "rca_pipeline",
                "analysis_type": rca_result.get("analysis_type", "unknown"),
                "evidence_count": rca_result.get("evidence_count", 0),
                "confidence": rca_result.get("confidence", 0.0),
                "processing_time": rca_result.get("processing_time", duration)
            }
            
        except Exception as rca_error:
            logger.warning(f"RCA聊天服务失败，回退到LLM适配器: {rca_error}")
            
            # 回退到原来的LLM适配器
            response = await llm.generate_response(query)
            
            # 记录成功的LLM请求
            duration = (datetime.now() - start_time).total_seconds()
            metrics_svc.record_llm_request(
                provider=provider_name,
                duration=duration,
                status="success",
                input_tokens=len(query.split()),
                output_tokens=len(response.split()) if response else 0
            )
            
            return {
                "response": response + "\n\n*注意: RCA分析服务暂时不可用，此回答来自基础LLM。*",
                "timestamp": datetime.now(),
                "session_id": request.get("session_id", "demo-session"),
                "llm_provider": provider_name,
                "analysis_type": "fallback_llm",
                "fallback_reason": str(rca_error)
            }
        
    except Exception as e:
        # 记录失败的LLM请求
        duration = (datetime.now() - start_time).total_seconds()
        metrics_svc.record_llm_request(
            provider=provider_name,
            duration=duration,
            status="error"
        )
        
        # 记录API错误
        error_type = type(e).__name__
        metrics_svc.record_api_error("/chat", error_type)
        
        logger.error(f"Chat failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat processing failed: {str(e)}"
        )


@app.post("/chat/stream", response_model=Dict[str, Any])
async def start_streaming_chat(
    request: Dict[str, Any],
    metrics_svc: MetricsService = Depends(get_metrics_service_dep)
):
    """启动流式聊天任务"""
    try:
        metrics_svc.increment_counter("api_requests_total", {"endpoint": "/chat/stream"})
        
        message = request.get("message", "")
        user_id = request.get("user_id", "")
        session_id = request.get("session_id")
        temperature = request.get("temperature", 0.7)
        
        if not message or not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message and user_id are required"
            )
        
        # 导入流式RCA服务
        from .streaming_rca_service import streaming_rca_service
        
        # 启动RCA任务
        task_id = await streaming_rca_service.start_rca_task(
            message=message,
            user_id=user_id, 
            session_id=session_id,
            temperature=temperature
        )
        
        logger.info(f"启动流式RCA任务: {task_id}")
        
        return {
            "success": True,
            "task_id": task_id,
            "session_id": session_id or f"session_{int(datetime.now().timestamp())}",
            "estimated_duration": 3.5,
            "message": "RCA分析任务已启动，请使用task_id轮询状态",
            "polling_interval": 500,  # 建议轮询间隔(毫秒)
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Failed to start streaming chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start streaming chat: {str(e)}"
        )


@app.get("/chat/task_status/{task_id}", response_model=Dict[str, Any])
async def get_task_status(
    task_id: str,
    metrics_svc: MetricsService = Depends(get_metrics_service_dep)
):
    """获取任务状态"""
    try:
        metrics_svc.increment_counter("api_requests_total", {"endpoint": "/task_status"})
        
        # 导入流式RCA服务
        from .streaming_rca_service import streaming_rca_service
        
        task_status = streaming_rca_service.get_task_status(task_id)
        
        if task_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        
        return task_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )


@app.post("/chat/multi_agent", response_model=Dict[str, Any])
async def start_multi_agent_chat(
    request: Dict[str, Any],
    metrics_svc: MetricsService = Depends(get_metrics_service_dep)
):
    """启动Multi-Agent RCA分析任务"""
    try:
        metrics_svc.increment_counter("api_requests_total", {"endpoint": "/chat/multi_agent"})
        
        message = request.get("message", "")
        user_id = request.get("user_id", "")
        session_id = request.get("session_id")
        
        if not message or not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message and user_id are required"
            )
        
        # 导入Enhanced流式RCA服务
        from .enhanced_streaming_rca_service import enhanced_streaming_rca_service
        
        task_id = await enhanced_streaming_rca_service.start_multi_agent_rca_task(
            message, user_id, session_id
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "session_id": session_id or f"session_{int(time.time())}",
            "message": "Multi-Agent RCA分析任务已启动",
            "polling_interval": 500,
            "supports_interruption": True,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Failed to start multi-agent chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start multi-agent chat: {str(e)}"
        )


@app.get("/chat/multi_agent_status/{task_id}", response_model=Dict[str, Any])
async def get_multi_agent_task_status(
    task_id: str,
    metrics_svc: MetricsService = Depends(get_metrics_service_dep)
):
    """获取Multi-Agent任务详细状态"""
    try:
        metrics_svc.increment_counter("api_requests_total", {"endpoint": "/multi_agent_status"})
        
        # 导入Enhanced流式RCA服务
        from .enhanced_streaming_rca_service import enhanced_streaming_rca_service
        
        task_status = enhanced_streaming_rca_service.get_multi_agent_task_status(task_id)
        
        if task_status is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Multi-Agent task {task_id} not found"
            )
        
        return task_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get multi-agent task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get multi-agent task status: {str(e)}"
        )


@app.post("/chat/interrupt/{task_id}", response_model=Dict[str, Any])
async def interrupt_multi_agent_task(
    task_id: str,
    request: Dict[str, Any] = None,
    metrics_svc: MetricsService = Depends(get_metrics_service_dep)
):
    """中断Multi-Agent任务执行"""
    try:
        metrics_svc.increment_counter("api_requests_total", {"endpoint": "/interrupt"})
        
        reason = "用户请求中断"
        if request:
            reason = request.get("reason", reason)
        
        # 导入Enhanced流式RCA服务
        from .enhanced_streaming_rca_service import enhanced_streaming_rca_service
        
        success = await enhanced_streaming_rca_service.interrupt_task(task_id, reason)
        
        if success:
            return {
                "success": True,
                "message": f"任务 {task_id} 已成功中断",
                "reason": reason,
                "timestamp": datetime.now()
            }
        else:
            return {
                "success": False,
                "message": f"任务 {task_id} 无法中断或不存在",
                "timestamp": datetime.now()
            }
        
    except Exception as e:
        logger.error(f"Failed to interrupt task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to interrupt task: {str(e)}"
        )


@app.get("/llm/info", response_model=Dict[str, Any])
async def get_llm_info(llm: LLMAdapter = Depends(get_llm_adapter_dep)):
    """获取当前LLM配置信息"""
    try:
        return {
            "llm_info": llm.get_provider_info(),
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Failed to get LLM info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get LLM info: {str(e)}"
        )


@app.post("/llm/reload")
async def reload_llm_config(llm: LLMAdapter = Depends(get_llm_adapter_dep)):
    """重新加载LLM配置"""
    try:
        llm.reload_config()
        return {
            "message": "LLM configuration reloaded successfully",
            "new_config": llm.get_provider_info(),
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Failed to reload LLM config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload LLM config: {str(e)}"
        )


# 会话管理端点
@app.get("/sessions/{user_id}")
async def get_user_sessions(
    user_id: str,
    metrics_svc: MetricsService = Depends(get_metrics_service_dep)
):
    """获取用户的会话列表"""
    try:
        metrics_svc.increment_counter("api_requests_total", {"endpoint": "/sessions"})
        # TODO: 实现会话管理逻辑
        return {
            "user_id": user_id,
            "sessions": [],
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Failed to get user sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user sessions: {str(e)}"
        )


@app.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    metrics_svc: MetricsService = Depends(get_metrics_service_dep)
):
    """获取会话的消息历史"""
    try:
        metrics_svc.increment_counter("api_requests_total", {"endpoint": "/session_messages"})
        # TODO: 实现消息历史逻辑
        return {
            "session_id": session_id,
            "messages": [],
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Failed to get session messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session messages: {str(e)}"
        )


@app.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    metrics_svc: MetricsService = Depends(get_metrics_service_dep)
):
    """删除会话"""
    try:
        metrics_svc.increment_counter("api_requests_total", {"endpoint": "/session_delete"})
        # TODO: 实现删除会话逻辑
        return {
            "message": f"Session {session_id} deleted successfully",
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete session: {str(e)}"
        )


# 知识图谱端点
@app.get("/knowledge/entities")
async def get_knowledge_entities(
    metrics_svc: MetricsService = Depends(get_metrics_service_dep)
):
    """获取知识图谱实体"""
    try:
        metrics_svc.increment_counter("api_requests_total", {"endpoint": "/knowledge_entities"})
        # TODO: 实现知识图谱查询逻辑
        return {
            "entities": [],
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Failed to get knowledge entities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get knowledge entities: {str(e)}"
        )


@app.post("/knowledge/extract")
async def extract_knowledge(
    request: Dict[str, Any],
    metrics_svc: MetricsService = Depends(get_metrics_service_dep)
):
    """从文本中提取知识"""
    try:
        metrics_svc.increment_counter("api_requests_total", {"endpoint": "/knowledge_extract"})
        # TODO: 实现知识抽取逻辑
        return {
            "extracted_entities": [],
            "extracted_relations": [],
            "timestamp": datetime.now()
        }
    except Exception as e:
        logger.error(f"Failed to extract knowledge: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract knowledge: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)