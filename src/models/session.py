"""
用户会话相关模型
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import ENUM
from .database import Base
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid


class UserSession(Base):
    """用户会话表"""
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), nullable=False, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    session_metadata = Column(JSON, nullable=True)

    # 关联会话消息
    messages = relationship("SessionMessage", back_populates="session", cascade="all, delete-orphan")


class SessionMessage(Base):
    """会话消息表"""
    __tablename__ = "session_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(100), ForeignKey("user_sessions.session_id", ondelete="CASCADE"), 
                       nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    message_type = Column(ENUM("user", "assistant", "system"), default="user")
    created_at = Column(DateTime, default=func.now(), index=True)
    tokens_used = Column(Integer, default=0)
    processing_time = Column(Float, default=0.0)
    message_metadata = Column(JSON, nullable=True)

    # 关联用户会话
    session = relationship("UserSession", back_populates="messages")


# Pydantic模型用于API交互
class UserSessionCreate(BaseModel):
    """创建用户会话请求模型"""
    user_id: str = Field(..., description="用户ID")
    session_metadata: Optional[Dict[str, Any]] = Field(None, description="会话元数据")


class UserSessionResponse(BaseModel):
    """用户会话响应模型"""
    id: str
    user_id: str
    session_id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    session_metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class SessionMessageCreate(BaseModel):
    """创建会话消息请求模型"""
    message: str = Field(..., description="用户消息")
    message_type: str = Field(default="user", description="消息类型")
    message_metadata: Optional[Dict[str, Any]] = Field(None, description="消息元数据")


class SessionMessageResponse(BaseModel):
    """会话消息响应模型"""
    id: str
    session_id: str
    user_id: str
    message: str
    response: Optional[str] = None
    message_type: str
    created_at: datetime
    tokens_used: int = 0
    processing_time: float = 0.0
    message_metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str = Field(..., description="用户消息", min_length=1)
    user_id: str = Field(..., description="用户ID")
    session_id: Optional[str] = Field(None, description="会话ID，如果不提供则创建新会话")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="生成温度")
    max_tokens: Optional[int] = Field(4096, ge=1, le=8192, description="最大token数")
    stream: bool = Field(False, description="是否流式响应")


class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str = Field(..., description="助手响应")
    session_id: str = Field(..., description="会话ID")
    message_id: str = Field(..., description="消息ID")
    tokens_used: int = Field(..., description="使用的token数量")
    processing_time: float = Field(..., description="处理时间(秒)")
    suggestions: Optional[List[str]] = Field(None, description="建议的后续问题")


class SessionListResponse(BaseModel):
    """会话列表响应模型"""
    sessions: List[UserSessionResponse]
    total: int
    page: int
    page_size: int


class MessageListResponse(BaseModel):
    """消息列表响应模型"""
    messages: List[SessionMessageResponse]
    total: int
    page: int
    page_size: int