"""
FastAPI主应用
提供AIOps服务的REST API接口
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import uvicorn
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
import json
from datetime import datetime

from ..models.session import ChatRequest, ChatResponse
from ..models.knowledge import SearchRequest, SearchResponse
from ..models.system import HealthCheckResponse, SystemStats
from ..agents.aiops_graph import AIOpsGraph
from ..services.search_service import SearchService
from ..services.graph_service import GraphService
from ..services.vector_service import VectorService
from ..services.embedding_service import EmbeddingService
from ..services.database_service import DatabaseService
from ..services.ner_service import NERService
from config.settings import settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局服务实例
search_service = None
graph_service = None
vector_service = None
embedding_service = None
database_service = None
ner_service = None
aiops_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化服务
    try:
        logger.info("Initializing AIOps services...")
        
        global search_service, graph_service, vector_service, embedding_service
        global database_service, ner_service, aiops_graph
        
        # 初始化基础服务
        database_service = DatabaseService()
        embedding_service = EmbeddingService()
        vector_service = VectorService()
        graph_service = GraphService()
        ner_service = NERService()
        
        # 初始化搜索服务
        search_service = SearchService()
        search_service.vector_service = vector_service
        search_service.graph_service = graph_service
        search_service.database_service = database_service
        search_service.embedding_service = embedding_service
        
        # 初始化AIOps主图
        aiops_graph = AIOpsGraph(
            search_service=search_service,
            graph_service=graph_service,
            llm_service=None  # POC版本不使用真实LLM
        )
        
        logger.info("AIOps services initialized successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        yield
    finally:
        # 关闭服务
        logger.info("Shutting down AIOps services...")
        try:
            if search_service:
                await search_service.close()
            if graph_service:
                await graph_service.close()
            if vector_service:
                vector_service.close()
            if embedding_service:
                embedding_service.close()
            if ner_service:
                ner_service.close()
            logger.info("AIOps services closed successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# 创建FastAPI应用
app = FastAPI(
    title="AIOps Polaris",
    description="智能运维系统API",
    version="1.0.0",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 依赖函数
def get_search_service() -> SearchService:
    """获取搜索服务"""
    if search_service is None:
        raise HTTPException(status_code=503, detail="Search service not initialized")
    return search_service


def get_aiops_graph() -> AIOpsGraph:
    """获取AIOps图"""
    if aiops_graph is None:
        raise HTTPException(status_code=503, detail="AIOps graph not initialized")
    return aiops_graph


def get_database_service() -> DatabaseService:
    """获取数据库服务"""
    if database_service is None:
        raise HTTPException(status_code=503, detail="Database service not initialized")
    return database_service


# API路由

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """健康检查"""
    try:
        components = {}
        
        # 检查各个服务状态
        if vector_service:
            components["weaviate"] = await vector_service.health_check()
        
        if graph_service:
            components["neo4j"] = await graph_service.health_check()
        
        if embedding_service:
            components["embedding"] = {
                "status": "healthy",
                "model_info": embedding_service.get_model_info()
            }
        
        return HealthCheckResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            components=components
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@app.post("/chat", response_model=Dict[str, Any])
async def chat(
    request: ChatRequest,
    graph: AIOpsGraph = Depends(get_aiops_graph),
    db: DatabaseService = Depends(get_database_service)
):
    """智能运维对话接口"""
    try:
        start_time = datetime.utcnow()
        
        # 创建或获取用户会话
        session = None
        if request.session_id:
            session = await db.get_user_session(request.session_id)
        
        if not session:
            session = await db.create_user_session(
                user_id=request.user_id,
                session_metadata={"temperature": request.temperature, "max_tokens": request.max_tokens}
            )
        
        # 处理用户消息
        result = await graph.process_user_message_simple(
            user_message=request.message,
            user_id=request.user_id,
            session_id=session.session_id
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
        
        # 计算处理时间
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # 获取最终响应
        final_messages = [msg for msg in result["messages"] if msg["type"] == "answer"]
        final_response = final_messages[-1]["content"] if final_messages else "处理完成，但未生成响应"
        
        # 保存消息到数据库
        await db.save_message(
            session_id=session.session_id,
            user_id=request.user_id,
            message=request.message,
            response=final_response,
            message_type="user",
            tokens_used=len(request.message.split()) + len(final_response.split()),  # 简单估算
            processing_time=processing_time,
            message_metadata={"agent_messages": result["messages"]}
        )
        
        return {
            "success": True,
            "response": final_response,
            "session_id": session.session_id,
            "message_id": f"msg_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "tokens_used": len(request.message.split()) + len(final_response.split()),
            "processing_time": processing_time,
            "agent_messages": result["messages"],
            "suggestions": [
                "查看执行详情",
                "获取相关文档",
                "查询历史案例"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


@app.post("/search", response_model=Dict[str, Any])
async def search(
    request: SearchRequest,
    search_svc: SearchService = Depends(get_search_service)
):
    """知识搜索接口"""
    try:
        result = await search_svc.hybrid_search(
            query=request.query,
            search_type=request.search_type,
            source=request.source,
            category=request.category,
            limit=request.limit,
            threshold=request.threshold or 0.7
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/search/suggestions")
async def get_search_suggestions(
    query: str,
    limit: int = 5,
    search_svc: SearchService = Depends(get_search_service)
):
    """获取搜索建议"""
    try:
        suggestions = await search_svc.get_search_suggestions(query, limit)
        return {"suggestions": suggestions}
        
    except Exception as e:
        logger.error(f"Failed to get suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@app.get("/sessions/{user_id}")
async def get_user_sessions(
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    db: DatabaseService = Depends(get_database_service)
):
    """获取用户会话列表"""
    try:
        sessions, total = await db.get_user_sessions(user_id, page, page_size)
        
        return {
            "sessions": [
                {
                    "id": session.id,
                    "session_id": session.session_id,
                    "created_at": session.created_at.isoformat(),
                    "updated_at": session.updated_at.isoformat(),
                    "is_active": session.is_active,
                    "session_metadata": session.session_metadata
                }
                for session in sessions
            ],
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"Failed to get user sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get user sessions: {str(e)}")


@app.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    page: int = 1,
    page_size: int = 50,
    db: DatabaseService = Depends(get_database_service)
):
    """获取会话消息列表"""
    try:
        messages, total = await db.get_session_messages(session_id, page, page_size)
        
        return {
            "messages": [
                {
                    "id": msg.id,
                    "message": msg.message,
                    "response": msg.response,
                    "message_type": msg.message_type,
                    "created_at": msg.created_at.isoformat(),
                    "tokens_used": msg.tokens_used,
                    "processing_time": msg.processing_time,
                    "message_metadata": msg.message_metadata
                }
                for msg in messages
            ],
            "total": total,
            "page": page,
            "page_size": page_size
        }
        
    except Exception as e:
        logger.error(f"Failed to get session messages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session messages: {str(e)}")


@app.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: DatabaseService = Depends(get_database_service)
):
    """删除会话"""
    try:
        success = await db.deactivate_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"success": True, "message": "Session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


@app.get("/knowledge/entities")
async def get_entities(
    entity_type: Optional[str] = None,
    limit: int = 100,
    db: DatabaseService = Depends(get_database_service)
):
    """获取实体列表"""
    try:
        entities = await db.get_entities(entity_type, limit)
        
        return {
            "entities": [
                {
                    "id": entity.id,
                    "name": entity.name,
                    "entity_type": entity.entity_type,
                    "description": entity.description,
                    "properties": entity.properties,
                    "created_at": entity.created_at.isoformat(),
                    "updated_at": entity.updated_at.isoformat()
                }
                for entity in entities
            ],
            "total": len(entities)
        }
        
    except Exception as e:
        logger.error(f"Failed to get entities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get entities: {str(e)}")


@app.post("/knowledge/extract")
async def extract_knowledge(
    text: str,
    source: str = "manual"
):
    """从文本中提取知识"""
    try:
        if not ner_service:
            raise HTTPException(status_code=503, detail="NER service not initialized")
        
        # 模拟文档结构
        result = await ner_service.extract_from_document(
            title="Manual Input",
            content=text,
            source=source
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Knowledge extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Knowledge extraction failed: {str(e)}")


@app.get("/stats", response_model=Dict[str, Any])
async def get_system_stats(
    search_svc: SearchService = Depends(get_search_service),
    db: DatabaseService = Depends(get_database_service)
):
    """获取系统统计信息"""
    try:
        stats = await search_svc.get_search_stats()
        
        # 添加其他统计信息
        stats["api_info"] = {
            "version": "1.0.0",
            "uptime": "N/A",  # 可以添加实际的运行时间计算
            "environment": settings.environment
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.get("/agent/status")
async def get_agent_status(
    graph: AIOpsGraph = Depends(get_aiops_graph)
):
    """获取Agent状态"""
    try:
        status = graph.get_agent_status()
        return status
        
    except Exception as e:
        logger.error(f"Failed to get agent status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get agent status: {str(e)}")


# 错误处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP exception: {exc.detail}")
    return {
        "error": True,
        "status_code": exc.status_code,
        "message": exc.detail,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return {
        "error": True,
        "status_code": 500,
        "message": "Internal server error",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        workers=settings.api.workers
    )