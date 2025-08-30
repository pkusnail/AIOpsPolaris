"""
知识库相关模型
"""

from sqlalchemy import Column, String, Text, DateTime, JSON, Float, BigInteger, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import ENUM
from .database import Base
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid


class KnowledgeDocument(Base):
    """知识库文档表"""
    __tablename__ = "knowledge_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(ENUM("wiki", "gitlab", "jira", "logs"), nullable=False, index=True)
    source_id = Column(String(100), nullable=True)
    category = Column(String(100), nullable=True, index=True)
    tags = Column(JSON, nullable=True)
    embedding_id = Column(String(100), nullable=True)  # Weaviate中的ID
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 创建全文索引
    __table_args__ = (
        Index('idx_title_content', 'title', 'content', mysql_prefix='FULLTEXT'),
    )


class Entity(Base):
    """实体表"""
    __tablename__ = "entities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    entity_type = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    properties = Column(JSON, nullable=True)
    neo4j_id = Column(BigInteger, nullable=True, index=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关联关系
    source_relationships = relationship("Relationship", foreign_keys="Relationship.source_entity_id", 
                                      back_populates="source_entity")
    target_relationships = relationship("Relationship", foreign_keys="Relationship.target_entity_id",
                                      back_populates="target_entity")

    # 唯一约束
    __table_args__ = (
        Index('unique_name_type', 'name', 'entity_type', unique=True),
    )


class Relationship(Base):
    """关系表"""
    __tablename__ = "relationships"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_entity_id = Column(String(36), ForeignKey("entities.id", ondelete="CASCADE"), 
                            nullable=False, index=True)
    target_entity_id = Column(String(36), ForeignKey("entities.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    relationship_type = Column(String(100), nullable=False, index=True)
    properties = Column(JSON, nullable=True)
    confidence = Column(Float, default=1.0)
    neo4j_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime, default=func.now())

    # 关联实体
    source_entity = relationship("Entity", foreign_keys=[source_entity_id], 
                               back_populates="source_relationships")
    target_entity = relationship("Entity", foreign_keys=[target_entity_id],
                               back_populates="target_relationships")


# Pydantic模型用于API交互
class KnowledgeDocumentCreate(BaseModel):
    """创建知识文档请求模型"""
    title: str = Field(..., description="文档标题")
    content: str = Field(..., description="文档内容")
    source: str = Field(..., description="数据源类型")
    source_id: Optional[str] = Field(None, description="源系统中的ID")
    category: Optional[str] = Field(None, description="文档分类")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class KnowledgeDocumentResponse(BaseModel):
    """知识文档响应模型"""
    id: str
    title: str
    content: str
    source: str
    source_id: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    embedding_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EntityCreate(BaseModel):
    """创建实体请求模型"""
    name: str = Field(..., description="实体名称")
    entity_type: str = Field(..., description="实体类型")
    description: Optional[str] = Field(None, description="实体描述")
    properties: Optional[Dict[str, Any]] = Field(None, description="实体属性")


class EntityResponse(BaseModel):
    """实体响应模型"""
    id: str
    name: str
    entity_type: str
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    neo4j_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RelationshipCreate(BaseModel):
    """创建关系请求模型"""
    source_entity_id: str = Field(..., description="源实体ID")
    target_entity_id: str = Field(..., description="目标实体ID")
    relationship_type: str = Field(..., description="关系类型")
    properties: Optional[Dict[str, Any]] = Field(None, description="关系属性")
    confidence: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="置信度")


class RelationshipResponse(BaseModel):
    """关系响应模型"""
    id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    properties: Optional[Dict[str, Any]] = None
    confidence: float
    neo4j_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str = Field(..., description="搜索查询", min_length=1)
    search_type: str = Field(default="hybrid", description="搜索类型: vector, keyword, hybrid")
    source: Optional[str] = Field(None, description="限制搜索的数据源")
    category: Optional[str] = Field(None, description="限制搜索的分类")
    limit: int = Field(default=10, ge=1, le=50, description="返回结果数量")
    threshold: Optional[float] = Field(0.7, ge=0.0, le=1.0, description="相似度阈值")


class SearchResult(BaseModel):
    """搜索结果项"""
    id: str
    title: str
    content: str
    source: str
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    score: float = Field(..., description="相关性得分")
    highlight: Optional[str] = Field(None, description="高亮片段")


class SearchResponse(BaseModel):
    """搜索响应模型"""
    results: List[SearchResult]
    total: int
    query: str
    search_type: str
    processing_time: float


class GraphQueryRequest(BaseModel):
    """图查询请求模型"""
    cypher: str = Field(..., description="Cypher查询语句")
    parameters: Optional[Dict[str, Any]] = Field(None, description="查询参数")
    limit: int = Field(default=100, ge=1, le=1000, description="结果数量限制")


class GraphQueryResponse(BaseModel):
    """图查询响应模型"""
    data: List[Dict[str, Any]]
    columns: List[str]
    summary: Dict[str, Any]
    processing_time: float