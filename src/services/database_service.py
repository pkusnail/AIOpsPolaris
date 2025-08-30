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

    # 知识文档相关方法 - 仅存储业务统计信息，实际文档存储在Weaviate
    async def save_knowledge_document(
        self,
        weaviate_id: str,
        title: str,
        source: str,
        source_id: Optional[str] = None,
        category: Optional[str] = None
    ) -> KnowledgeDocument:
        """保存知识文档元数据和统计信息"""
        async for db in get_database():
            try:
                new_doc = KnowledgeDocument(
                    weaviate_id=weaviate_id,
                    title=title,
                    source=source,
                    source_id=source_id,
                    category=category
                )
                db.add(new_doc)
                await db.flush()
                await db.refresh(new_doc)
                return new_doc
            except Exception as e:
                self.logger.error(f"保存知识文档失败: {e}")
                await db.rollback()
                raise

    async def get_knowledge_document_by_weaviate_id(
        self,
        weaviate_id: str
    ) -> Optional[KnowledgeDocument]:
        """通过Weaviate ID获取知识文档记录"""
        async for db in get_database():
            try:
                stmt = select(KnowledgeDocument).where(
                    KnowledgeDocument.weaviate_id == weaviate_id
                )
                result = await db.execute(stmt)
                return result.scalar_one_or_none()
            except Exception as e:
                self.logger.error(f"通过Weaviate ID获取文档失败: {e}")
                return None
    
    async def update_document_stats(
        self,
        weaviate_id: str,
        increment_views: bool = True
    ) -> bool:
        """更新文档统计信息"""
        async for db in get_database():
            try:
                stmt = select(KnowledgeDocument).where(
                    KnowledgeDocument.weaviate_id == weaviate_id
                )
                result = await db.execute(stmt)
                doc = result.scalar_one_or_none()
                
                if doc and increment_views:
                    doc.view_count += 1
                    doc.last_accessed = datetime.utcnow()
                    await db.commit()
                    return True
                return False
            except Exception as e:
                self.logger.error(f"更新文档统计失败: {e}")
                return False
    
    async def get_document_stats(
        self,
        source: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取文档统计信息"""
        async for db in get_database():
            try:
                conditions = []
                if source:
                    conditions.append(KnowledgeDocument.source == source)
                if category:
                    conditions.append(KnowledgeDocument.category == category)
                
                if conditions:
                    where_clause = and_(*conditions)
                else:
                    where_clause = text("1=1")
                
                # 总数统计
                count_stmt = select(func.count(KnowledgeDocument.id)).where(where_clause)
                total_result = await db.execute(count_stmt)
                total_count = total_result.scalar()
                
                # 按源分组统计
                source_stmt = select(
                    KnowledgeDocument.source,
                    func.count(KnowledgeDocument.id).label('count')
                ).group_by(KnowledgeDocument.source)
                source_result = await db.execute(source_stmt)
                source_stats = {row.source: row.count for row in source_result.all()}
                
                # 按分类统计
                category_stmt = select(
                    KnowledgeDocument.category,
                    func.count(KnowledgeDocument.id).label('count')
                ).group_by(KnowledgeDocument.category)
                category_result = await db.execute(category_stmt)
                category_stats = {row.category: row.count for row in category_result.all()}
                
                return {
                    "total_documents": total_count,
                    "by_source": source_stats,
                    "by_category": category_stats
                }
            except Exception as e:
                self.logger.error(f"获取文档统计失败: {e}")
                return {"total_documents": 0, "by_source": {}, "by_category": {}}

    # 实体相关方法 - 仅存储业务统计信息，实际实体存储在Neo4j
    async def save_entity(
        self,
        name: str,
        entity_type: str,
        source_document_id: Optional[str] = None,
        confidence: float = 1.0
    ) -> Entity:
        """保存实体统计信息 - 实际实体存储在Neo4j"""
        async for db in get_database():
            try:
                # 检查是否已存在
                existing_stmt = select(Entity).where(
                    and_(Entity.name == name, Entity.entity_type == entity_type)
                )
                existing_result = await db.execute(existing_stmt)
                existing_entity = existing_result.scalar_one_or_none()
                
                if existing_entity:
                    # 更新现有实体统计
                    stmt = (
                        update(Entity)
                        .where(Entity.id == existing_entity.id)
                        .values(
                            mention_count=Entity.mention_count + 1,
                            last_mentioned=datetime.utcnow(),
                            confidence=confidence
                        )
                    )
                    await db.execute(stmt)
                    await db.commit()
                    await db.refresh(existing_entity)
                    return existing_entity
                else:
                    # 创建新实体统计记录
                    new_entity = Entity(
                        name=name,
                        entity_type=entity_type,
                        source_document_id=source_document_id,
                        confidence=confidence,
                        mention_count=1,
                        last_mentioned=datetime.utcnow()
                    )
                    db.add(new_entity)
                    await db.commit()
                    await db.refresh(new_entity)
                    return new_entity
            except Exception as e:
                self.logger.error(f"保存实体统计失败: {e}")
                await db.rollback()
                raise

    async def get_entities(
        self,
        entity_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Entity]:
        """获取实体统计列表 - 按提及次数排序"""
        async for db in get_database():
            try:
                conditions = []
                if entity_type:
                    conditions.append(Entity.entity_type == entity_type)
                
                if conditions:
                    stmt = (
                        select(Entity)
                        .where(and_(*conditions))
                        .order_by(Entity.mention_count.desc(), Entity.last_mentioned.desc())
                        .limit(limit)
                    )
                else:
                    stmt = (
                        select(Entity)
                        .order_by(Entity.mention_count.desc(), Entity.last_mentioned.desc())
                        .limit(limit)
                    )
                
                result = await db.execute(stmt)
                return list(result.scalars().all())
            except Exception as e:
                self.logger.error(f"获取实体统计列表失败: {e}")
                return []

    # 关系相关方法 - 仅存储业务统计信息，实际关系存储在Neo4j
    async def save_relationship(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        source_document_id: Optional[str] = None,
        confidence: float = 1.0
    ) -> Relationship:
        """保存关系统计信息 - 实际关系存储在Neo4j"""
        async for db in get_database():
            try:
                # 检查是否已存在相同关系
                existing_stmt = select(Relationship).where(
                    and_(
                        Relationship.source_entity_id == source_entity_id,
                        Relationship.target_entity_id == target_entity_id,
                        Relationship.relationship_type == relationship_type
                    )
                )
                existing_result = await db.execute(existing_stmt)
                existing_rel = existing_result.scalar_one_or_none()
                
                if existing_rel:
                    # 更新现有关系统计
                    stmt = (
                        update(Relationship)
                        .where(Relationship.id == existing_rel.id)
                        .values(
                            usage_count=Relationship.usage_count + 1,
                            last_used=datetime.utcnow(),
                            confidence=confidence
                        )
                    )
                    await db.execute(stmt)
                    await db.commit()
                    await db.refresh(existing_rel)
                    return existing_rel
                else:
                    # 创建新关系统计记录
                    new_relationship = Relationship(
                        source_entity_id=source_entity_id,
                        target_entity_id=target_entity_id,
                        relationship_type=relationship_type,
                        source_document_id=source_document_id,
                        confidence=confidence,
                        usage_count=1,
                        last_used=datetime.utcnow()
                    )
                    db.add(new_relationship)
                    await db.commit()
                    await db.refresh(new_relationship)
                    return new_relationship
            except Exception as e:
                self.logger.error(f"保存关系统计失败: {e}")
                await db.rollback()
                raise

    async def get_entity_stats(
        self,
        entity_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取实体统计信息"""
        async for db in get_database():
            try:
                conditions = []
                if entity_type:
                    conditions.append(Entity.entity_type == entity_type)
                
                if conditions:
                    where_clause = and_(*conditions)
                else:
                    where_clause = text("1=1")
                
                # 总数统计
                count_stmt = select(func.count(Entity.id)).where(where_clause)
                total_result = await db.execute(count_stmt)
                total_count = total_result.scalar()
                
                # 按类型统计
                type_stmt = select(
                    Entity.entity_type,
                    func.count(Entity.id).label('count'),
                    func.sum(Entity.mention_count).label('total_mentions')
                ).group_by(Entity.entity_type)
                type_result = await db.execute(type_stmt)
                type_stats = {
                    row.entity_type: {
                        'count': row.count,
                        'total_mentions': row.total_mentions or 0
                    } for row in type_result.all()
                }
                
                # 热门实体（按提及次数）
                popular_stmt = (
                    select(Entity.name, Entity.entity_type, Entity.mention_count)
                    .where(where_clause)
                    .order_by(Entity.mention_count.desc())
                    .limit(10)
                )
                popular_result = await db.execute(popular_stmt)
                popular_entities = [
                    {
                        'name': row.name,
                        'type': row.entity_type,
                        'mentions': row.mention_count
                    } for row in popular_result.all()
                ]
                
                return {
                    "total_entities": total_count,
                    "by_type": type_stats,
                    "popular_entities": popular_entities
                }
            except Exception as e:
                self.logger.error(f"获取实体统计失败: {e}")
                return {"total_entities": 0, "by_type": {}, "popular_entities": []}

    async def get_relationship_stats(self) -> Dict[str, Any]:
        """获取关系统计信息"""
        async for db in get_database():
            try:
                # 总数统计
                count_stmt = select(func.count(Relationship.id))
                total_result = await db.execute(count_stmt)
                total_count = total_result.scalar()
                
                # 按类型统计
                type_stmt = select(
                    Relationship.relationship_type,
                    func.count(Relationship.id).label('count'),
                    func.sum(Relationship.usage_count).label('total_usage')
                ).group_by(Relationship.relationship_type)
                type_result = await db.execute(type_stmt)
                type_stats = {
                    row.relationship_type: {
                        'count': row.count,
                        'total_usage': row.total_usage or 0
                    } for row in type_result.all()
                }
                
                return {
                    "total_relationships": total_count,
                    "by_type": type_stats
                }
            except Exception as e:
                self.logger.error(f"获取关系统计失败: {e}")
                return {"total_relationships": 0, "by_type": {}}

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