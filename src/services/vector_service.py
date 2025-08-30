"""
向量数据库服务
基于Weaviate实现语义搜索功能
"""

import weaviate
from typing import List, Dict, Any, Optional, Tuple
import logging
import json
from datetime import datetime

from config.settings import settings

logger = logging.getLogger(__name__)


class VectorService:
    """向量数据库服务类"""
    
    def __init__(self):
        self.client = None
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化Weaviate客户端"""
        try:
            self.client = weaviate.Client(
                url=settings.weaviate.url,
                additional_headers={"X-Weaviate-Api-Key": settings.weaviate.api_key} if settings.weaviate.api_key else None,
                timeout_config=(5, 60)
            )
            self.logger.info(f"Connected to Weaviate at {settings.weaviate.url}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Weaviate: {e}")
            raise
    
    async def create_schema(self):
        """创建向量数据库Schema - Weaviate作为文档主存储"""
        try:
            # 删除现有类（如果存在）
            existing_classes = ["KnowledgeDocument", "LogEntry"]
            for class_name in existing_classes:
                try:
                    self.client.schema.delete_class(class_name)
                    self.logger.info(f"Deleted existing class: {class_name}")
                except:
                    pass
            
            # 创建知识文档类 - 包含完整的文档信息和元数据
            knowledge_doc_class = {
                "class": "KnowledgeDocument",
                "description": "Knowledge documents - 主存储，包含完整文档信息和元数据",
                "properties": [
                    {
                        "name": "title",
                        "dataType": ["text"],
                        "description": "Document title"
                    },
                    {
                        "name": "content", 
                        "dataType": ["text"],
                        "description": "Document content"
                    },
                    {
                        "name": "source",
                        "dataType": ["string"],
                        "description": "Source type (wiki, gitlab, jira, logs)"
                    },
                    {
                        "name": "source_id",
                        "dataType": ["string"],
                        "description": "ID in source system"
                    },
                    {
                        "name": "category",
                        "dataType": ["string"],
                        "description": "Document category"
                    },
                    {
                        "name": "tags",
                        "dataType": ["string[]"],
                        "description": "Document tags"
                    },
                    {
                        "name": "author",
                        "dataType": ["string"],
                        "description": "Document author"
                    },
                    {
                        "name": "version",
                        "dataType": ["string"],
                        "description": "Document version"
                    },
                    {
                        "name": "language",
                        "dataType": ["string"],
                        "description": "Document language"
                    },
                    {
                        "name": "file_path",
                        "dataType": ["string"],
                        "description": "Original file path"
                    },
                    {
                        "name": "created_at",
                        "dataType": ["date"],
                        "description": "Creation timestamp"
                    },
                    {
                        "name": "updated_at",
                        "dataType": ["date"],
                        "description": "Last update timestamp"
                    }
                ],
                "vectorizer": "none"  # 手动提供向量，更灵活控制
            }
            
            # 注意：实体和关系数据存储在Neo4j中，Weaviate专注于文档存储和语义搜索
            
            # 创建日志条目类
            log_entry_class = {
                "class": "LogEntry",
                "description": "System log entries",
                "properties": [
                    {
                        "name": "timestamp",
                        "dataType": ["date"],
                        "description": "Log timestamp"
                    },
                    {
                        "name": "level",
                        "dataType": ["string"],
                        "description": "Log level"
                    },
                    {
                        "name": "service",
                        "dataType": ["string"],
                        "description": "Service name"
                    },
                    {
                        "name": "message",
                        "dataType": ["text"],
                        "description": "Log message"
                    },
                    {
                        "name": "metadata",
                        "dataType": ["text"],
                        "description": "Additional metadata as JSON string"
                    }
                ],
                "vectorizer": "none"
            }
            
            # 创建类
            self.client.schema.create_class(knowledge_doc_class)
            self.client.schema.create_class(log_entry_class)
            
            self.logger.info("Schema created successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to create schema: {e}")
            raise
    
    async def add_knowledge_document(
        self,
        title: str,
        content: str,
        source: str,
        source_id: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        version: Optional[str] = None,
        language: str = "zh-CN",
        file_path: Optional[str] = None,
        vector: Optional[List[float]] = None
    ) -> str:
        """添加知识文档到向量数据库 - Weaviate作为主存储"""
        try:
            current_time = datetime.utcnow().isoformat()
            properties = {
                "title": title,
                "content": content,
                "source": source,
                "category": category or "未分类",
                "tags": tags or [],
                "author": author or "系统",
                "version": version or "1.0",
                "language": language,
                "created_at": current_time,
                "updated_at": current_time
            }
            
            if source_id:
                properties["source_id"] = source_id
            if file_path:
                properties["file_path"] = file_path
            
            # 添加对象
            uuid = self.client.data_object.create(
                data_object=properties,
                class_name="KnowledgeDocument",
                vector=vector
            )
            
            self.logger.info(f"Added knowledge document with UUID: {uuid}")
            return uuid
            
        except Exception as e:
            self.logger.error(f"Failed to add knowledge document: {e}")
            raise
    
    # 实体数据现在存储在Neo4j中，不在Weaviate存储
    
    async def vector_search(
        self,
        query_vector: List[float],
        class_name: str = "KnowledgeDocument",
        limit: int = 10,
        certainty: float = 0.7,
        where_filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """向量搜索"""
        try:
            query = (
                self.client.query
                .get(class_name)
                .with_near_vector({"vector": query_vector, "certainty": certainty})
                .with_limit(limit)
                .with_additional(["certainty", "distance"])
            )
            
            # 添加字段 - 只支持KnowledgeDocument
            if class_name == "KnowledgeDocument":
                query = query.with_fields("title content source source_id category tags author version language file_path created_at updated_at")
            
            # 添加过滤条件
            if where_filter:
                query = query.with_where(where_filter)
            
            result = query.do()
            
            if "data" in result and "Get" in result["data"] and class_name in result["data"]["Get"]:
                return result["data"]["Get"][class_name]
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            return []
    
    async def hybrid_search(
        self,
        query: str,
        query_vector: Optional[List[float]] = None,
        class_name: str = "KnowledgeDocument",
        limit: int = 10,
        alpha: float = 0.7
    ) -> List[Dict[str, Any]]:
        """混合搜索（BM25 + 向量搜索）"""
        try:
            search_query = self.client.query.get(class_name).with_limit(limit)
            
            if query_vector:
                # 混合搜索
                search_query = search_query.with_hybrid(
                    query=query,
                    vector=query_vector,
                    alpha=alpha  # 0 = pure BM25, 1 = pure vector search
                )
            else:
                # 纯BM25搜索
                search_query = search_query.with_bm25(query=query)
            
            # 添加字段 - 只支持KnowledgeDocument  
            if class_name == "KnowledgeDocument":
                search_query = search_query.with_fields("title content source source_id category tags author version language file_path created_at updated_at")
            
            search_query = search_query.with_additional(["score"])
            
            result = search_query.do()
            
            if "data" in result and "Get" in result["data"] and class_name in result["data"]["Get"]:
                return result["data"]["Get"][class_name]
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Hybrid search failed: {e}")
            return []
    
    async def keyword_search(
        self,
        query: str,
        class_name: str = "KnowledgeDocument",
        limit: int = 10,
        where_filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """关键词搜索（BM25）"""
        try:
            search_query = (
                self.client.query
                .get(class_name)
                .with_bm25(query=query)
                .with_limit(limit)
                .with_additional(["score"])
            )
            
            # 添加字段 - 只支持KnowledgeDocument  
            if class_name == "KnowledgeDocument":
                search_query = search_query.with_fields("title content source source_id category tags author version language file_path created_at updated_at")
            
            # 添加过滤条件
            if where_filter:
                search_query = search_query.with_where(where_filter)
            
            result = search_query.do()
            
            if "data" in result and "Get" in result["data"] and class_name in result["data"]["Get"]:
                return result["data"]["Get"][class_name]
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Keyword search failed: {e}")
            return []
    
    async def get_object_by_id(self, uuid: str) -> Optional[Dict[str, Any]]:
        """根据UUID获取对象"""
        try:
            result = self.client.data_object.get_by_id(uuid)
            return result
        except Exception as e:
            self.logger.error(f"Failed to get object by ID: {e}")
            return None
    
    async def update_object(
        self,
        uuid: str,
        properties: Dict[str, Any],
        vector: Optional[List[float]] = None
    ) -> bool:
        """更新对象"""
        try:
            self.client.data_object.update(
                uuid=uuid,
                data_object=properties,
                vector=vector
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to update object: {e}")
            return False
    
    async def delete_object(self, uuid: str) -> bool:
        """删除对象"""
        try:
            self.client.data_object.delete(uuid)
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete object: {e}")
            return False
    
    async def get_schema(self) -> Dict[str, Any]:
        """获取Schema信息"""
        try:
            return self.client.schema.get()
        except Exception as e:
            self.logger.error(f"Failed to get schema: {e}")
            return {}
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            stats = {}
            
            # 获取各类对象数量  
            for class_name in ["KnowledgeDocument", "LogEntry"]:
                try:
                    result = (
                        self.client.query
                        .aggregate(class_name)
                        .with_meta_count()
                        .do()
                    )
                    
                    if "data" in result and "Aggregate" in result["data"]:
                        count = result["data"]["Aggregate"][class_name][0]["meta"]["count"]
                        stats[f"{class_name.lower()}_count"] = count
                except:
                    stats[f"{class_name.lower()}_count"] = 0
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get stats: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            # 检查连接
            result = self.client.cluster.get_nodes_status()
            
            return {
                "status": "healthy",
                "nodes": result,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def close(self):
        """关闭连接"""
        if self.client:
            # Weaviate client没有显式的close方法
            self.client = None
            self.logger.info("Weaviate client connection closed")