"""
数据库服务层
处理MySQL数据库相关操作
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, and_, or_, text, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import uuid
import logging

from ..models.database import get_database
from ..models.session import UserSession, SessionMessage
from ..models.knowledge import KnowledgeDocument, Entity, Relationship
from ..models.system import SystemConfig, TaskQueue

logger = logging.getLogger(__name__)


class DatabaseService:
    """数据库服务类"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    # 用户会话相关方法
    async def create_user_session(
        self, 
        user_id: str, 
        session_metadata: Optional[Dict[str, Any]] = None
    ) -> UserSession:
        """创建用户会话"""
        async for db in get_database():
            try:
                session_id = str(uuid.uuid4())
                new_session = UserSession(
                    user_id=user_id,
                    session_id=session_id,
                    session_metadata=session_metadata or {}
                )
                db.add(new_session)
                await db.flush()
                await db.commit()
                await db.refresh(new_session)
                return new_session
            except Exception as e:
                self.logger.error(f"创建用户会话失败: {e}")
                await db.rollback()
                raise

    async def get_user_session(self, session_id: str) -> Optional[UserSession]:
        """获取用户会话"""
        async for db in get_database():
            try:
                stmt = select(UserSession).where(UserSession.session_id == session_id)
                result = await db.execute(stmt)
                return result.scalar_one_or_none()
            except Exception as e:
                self.logger.error(f"获取用户会话失败: {e}")
                return None

    async def get_user_sessions(
        self, 
        user_id: str, 
        page: int = 1, 
        page_size: int = 20,
        active_only: bool = True
    ) -> Tuple[List[UserSession], int]:
        """获取用户会话列表"""
        async for db in get_database():
            try:
                conditions = [UserSession.user_id == user_id]
                if active_only:
                    conditions.append(UserSession.is_active == True)
                
                # 计算总数
                count_stmt = select(func.count(UserSession.id)).where(and_(*conditions))
                total_result = await db.execute(count_stmt)
                total = total_result.scalar()
                
                # 获取分页数据
                offset = (page - 1) * page_size
                stmt = (
                    select(UserSession)
                    .where(and_(*conditions))
                    .order_by(UserSession.updated_at.desc())
                    .offset(offset)
                    .limit(page_size)
                )
                result = await db.execute(stmt)
                sessions = result.scalars().all()
                
                return list(sessions), total
            except Exception as e:
                self.logger.error(f"获取用户会话列表失败: {e}")
                return [], 0

    async def deactivate_session(self, session_id: str) -> bool:
        """停用会话"""
        async for db in get_database():
            try:
                stmt = (
                    update(UserSession)
                    .where(UserSession.session_id == session_id)
                    .values(is_active=False, updated_at=datetime.utcnow())
                )
                result = await db.execute(stmt)
                return result.rowcount > 0
            except Exception as e:
                self.logger.error(f"停用会话失败: {e}")
                return False

    # 会话消息相关方法
    async def save_message(
        self,
        session_id: str,
        user_id: str, 
        message: str,
        response: Optional[str] = None,
        message_type: str = "user",
        tokens_used: int = 0,
        processing_time: float = 0.0,
        message_metadata: Optional[Dict[str, Any]] = None
    ) -> SessionMessage:
        """保存会话消息"""
        async for db in get_database():
            try:
                new_message = SessionMessage(
                    session_id=session_id,
                    user_id=user_id,
                    message=message,
                    response=response,
                    message_type=message_type,
                    tokens_used=tokens_used,
                    processing_time=processing_time,
                    message_metadata=message_metadata or {}
                )
                db.add(new_message)
                await db.flush()
                await db.refresh(new_message)
                return new_message
            except Exception as e:
                self.logger.error(f"保存消息失败: {e}")
                await db.rollback()
                raise

    async def get_session_messages(
        self,
        session_id: str,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[SessionMessage], int]:
        """获取会话消息列表"""
        async for db in get_database():
            try:
                # 计算总数
                count_stmt = select(func.count(SessionMessage.id)).where(
                    SessionMessage.session_id == session_id
                )
                total_result = await db.execute(count_stmt)
                total = total_result.scalar()
                
                # 获取分页数据
                offset = (page - 1) * page_size
                stmt = (
                    select(SessionMessage)
                    .where(SessionMessage.session_id == session_id)
                    .order_by(SessionMessage.created_at.asc())
                    .offset(offset)
                    .limit(page_size)
                )
                result = await db.execute(stmt)
                messages = result.scalars().all()
                
                return list(messages), total
            except Exception as e:
                self.logger.error(f"获取会话消息失败: {e}")
                return [], 0

    # 知识文档相关方法
    async def save_knowledge_document(
        self,
        title: str,
        content: str,
        source: str,
        source_id: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        embedding_id: Optional[str] = None
    ) -> KnowledgeDocument:
        """保存知识文档"""
        async for db in get_database():
            try:
                new_doc = KnowledgeDocument(
                    title=title,
                    content=content,
                    source=source,
                    source_id=source_id,
                    category=category,
                    tags=tags,
                    embedding_id=embedding_id
                )
                db.add(new_doc)
                await db.flush()
                await db.refresh(new_doc)
                return new_doc
            except Exception as e:
                self.logger.error(f"保存知识文档失败: {e}")
                await db.rollback()
                raise

    async def search_knowledge_documents(
        self,
        query: str,
        source: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[KnowledgeDocument]:
        """搜索知识文档"""
        async for db in get_database():
            try:
                conditions = []
                
                # 全文搜索条件
                if query:
                    conditions.append(
                        text("MATCH(title, content) AGAINST(:query IN NATURAL LANGUAGE MODE) > 0")
                    )
                
                if source:
                    conditions.append(KnowledgeDocument.source == source)
                
                if category:
                    conditions.append(KnowledgeDocument.category == category)
                
                if not conditions:
                    conditions.append(text("1=1"))
                
                stmt = (
                    select(
                        KnowledgeDocument,
                        text("MATCH(title, content) AGAINST(:query IN NATURAL LANGUAGE MODE) as relevance_score")
                    )
                    .where(and_(*conditions))
                    .order_by(text("relevance_score DESC"))
                    .limit(limit)
                )
                
                result = await db.execute(stmt, {"query": query})
                documents = [row[0] for row in result.all()]
                
                return documents
            except Exception as e:
                self.logger.error(f"搜索知识文档失败: {e}")
                return []

    # 实体相关方法
    async def save_entity(
        self,
        name: str,
        entity_type: str,
        description: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        neo4j_id: Optional[int] = None
    ) -> Entity:
        """保存实体"""
        async for db in get_database():
            try:
                # 检查是否已存在
                existing_stmt = select(Entity).where(
                    and_(Entity.name == name, Entity.entity_type == entity_type)
                )
                existing_result = await db.execute(existing_stmt)
                existing_entity = existing_result.scalar_one_or_none()
                
                if existing_entity:
                    # 更新现有实体
                    stmt = (
                        update(Entity)
                        .where(Entity.id == existing_entity.id)
                        .values(
                            description=description,
                            properties=properties,
                            neo4j_id=neo4j_id,
                            updated_at=datetime.utcnow()
                        )
                    )
                    await db.execute(stmt)
                    await db.refresh(existing_entity)
                    return existing_entity
                else:
                    # 创建新实体
                    new_entity = Entity(
                        name=name,
                        entity_type=entity_type,
                        description=description,
                        properties=properties or {},
                        neo4j_id=neo4j_id
                    )
                    db.add(new_entity)
                    await db.flush()
                    await db.refresh(new_entity)
                    return new_entity
            except Exception as e:
                self.logger.error(f"保存实体失败: {e}")
                await db.rollback()
                raise

    async def get_entities(
        self,
        entity_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Entity]:
        """获取实体列表"""
        async for db in get_database():
            try:
                conditions = []
                if entity_type:
                    conditions.append(Entity.entity_type == entity_type)
                
                if conditions:
                    stmt = select(Entity).where(and_(*conditions)).limit(limit)
                else:
                    stmt = select(Entity).limit(limit)
                
                result = await db.execute(stmt)
                return list(result.scalars().all())
            except Exception as e:
                self.logger.error(f"获取实体列表失败: {e}")
                return []

    # 关系相关方法
    async def save_relationship(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        properties: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        neo4j_id: Optional[int] = None
    ) -> Relationship:
        """保存关系"""
        async for db in get_database():
            try:
                new_relationship = Relationship(
                    source_entity_id=source_entity_id,
                    target_entity_id=target_entity_id,
                    relationship_type=relationship_type,
                    properties=properties or {},
                    confidence=confidence,
                    neo4j_id=neo4j_id
                )
                db.add(new_relationship)
                await db.flush()
                await db.refresh(new_relationship)
                return new_relationship
            except Exception as e:
                self.logger.error(f"保存关系失败: {e}")
                await db.rollback()
                raise

    # 系统配置相关方法
    async def get_config(self, config_key: str) -> Optional[Any]:
        """获取系统配置"""
        async for db in get_database():
            try:
                stmt = select(SystemConfig).where(SystemConfig.config_key == config_key)
                result = await db.execute(stmt)
                config = result.scalar_one_or_none()
                return config.config_value if config else None
            except Exception as e:
                self.logger.error(f"获取系统配置失败: {e}")
                return None

    async def set_config(
        self,
        config_key: str,
        config_value: Any,
        description: Optional[str] = None
    ) -> bool:
        """设置系统配置"""
        async for db in get_database():
            try:
                # 尝试更新现有配置
                update_stmt = (
                    update(SystemConfig)
                    .where(SystemConfig.config_key == config_key)
                    .values(
                        config_value=config_value,
                        description=description,
                        updated_at=datetime.utcnow()
                    )
                )
                result = await db.execute(update_stmt)
                
                if result.rowcount == 0:
                    # 创建新配置
                    new_config = SystemConfig(
                        config_key=config_key,
                        config_value=config_value,
                        description=description
                    )
                    db.add(new_config)
                
                return True
            except Exception as e:
                self.logger.error(f"设置系统配置失败: {e}")
                await db.rollback()
                return False

    # 任务队列相关方法
    async def create_task(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        priority: int = 0,
        max_retries: int = 3,
        scheduled_at: Optional[datetime] = None
    ) -> TaskQueue:
        """创建任务"""
        async for db in get_database():
            try:
                new_task = TaskQueue(
                    task_type=task_type,
                    task_data=task_data,
                    priority=priority,
                    max_retries=max_retries,
                    scheduled_at=scheduled_at or datetime.utcnow()
                )
                db.add(new_task)
                await db.flush()
                await db.refresh(new_task)
                return new_task
            except Exception as e:
                self.logger.error(f"创建任务失败: {e}")
                await db.rollback()
                raise

    async def get_pending_tasks(self, limit: int = 10) -> List[TaskQueue]:
        """获取待执行任务"""
        async for db in get_database():
            try:
                stmt = (
                    select(TaskQueue)
                    .where(
                        and_(
                            TaskQueue.status == "pending",
                            TaskQueue.scheduled_at <= datetime.utcnow()
                        )
                    )
                    .order_by(TaskQueue.priority.desc(), TaskQueue.created_at.asc())
                    .limit(limit)
                )
                result = await db.execute(stmt)
                return list(result.scalars().all())
            except Exception as e:
                self.logger.error(f"获取待执行任务失败: {e}")
                return []

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """更新任务状态"""
        async for db in get_database():
            try:
                update_data = {
                    "status": status,
                    "updated_at": datetime.utcnow()
                }
                
                if status == "running":
                    update_data["started_at"] = datetime.utcnow()
                elif status in ["completed", "failed"]:
                    update_data["completed_at"] = datetime.utcnow()
                
                if result is not None:
                    update_data["result"] = result
                
                if error_message:
                    update_data["error_message"] = error_message
                
                stmt = update(TaskQueue).where(TaskQueue.id == task_id).values(**update_data)
                result = await db.execute(stmt)
                return result.rowcount > 0
            except Exception as e:
                self.logger.error(f"更新任务状态失败: {e}")
                return False