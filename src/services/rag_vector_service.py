"""
RAG向量数据库服务 - 重新设计支持混合搜索的两个Collection
1. EmbeddingCollection - 语义搜索，支持向量检索和rerank
2. FullTextCollection - 全文搜索，支持BM25和关键词匹配
"""

import weaviate
from typing import List, Dict, Any, Optional, Tuple, Union
import logging
import json
from datetime import datetime
import uuid as uuid_lib

from config.settings import settings

logger = logging.getLogger(__name__)


class RAGVectorService:
    """RAG向量数据库服务类 - 支持两个专门的Collection"""
    
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
    
    async def create_rag_schema(self):
        """创建RAG专用的两个Collection Schema"""
        try:
            # 删除现有的类（如果存在）
            existing_classes = ["EmbeddingCollection", "FullTextCollection", "KnowledgeDocument", "LogEntry"]
            for class_name in existing_classes:
                try:
                    self.client.schema.delete_class(class_name)
                    self.logger.info(f"Deleted existing class: {class_name}")
                except:
                    pass
            
            # 1. EmbeddingCollection - 用于语义搜索和向量检索
            embedding_collection_schema = {
                "class": "EmbeddingCollection",
                "description": "语义搜索专用Collection，支持向量检索和rerank",
                "vectorizer": "none",  # 手动提供向量
                "properties": [
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "文档内容或日志内容",
                        "tokenization": "word"
                    },
                    {
                        "name": "title",
                        "dataType": ["string"],
                        "description": "标题或摘要"
                    },
                    {
                        "name": "source_type",
                        "dataType": ["string"],
                        "description": "数据源类型: logs, wiki, gitlab, jira"
                    },
                    {
                        "name": "source_id",
                        "dataType": ["string"],
                        "description": "源系统中的唯一ID"
                    },
                    # 日志特定字段
                    {
                        "name": "service_name",
                        "dataType": ["string"],
                        "description": "服务名称"
                    },
                    {
                        "name": "hostname",
                        "dataType": ["string"],
                        "description": "机器名/主机名"
                    },
                    {
                        "name": "log_file",
                        "dataType": ["string"],
                        "description": "日志文件名"
                    },
                    {
                        "name": "line_number",
                        "dataType": ["int"],
                        "description": "日志行数"
                    },
                    {
                        "name": "log_level",
                        "dataType": ["string"],
                        "description": "日志级别: INFO, WARN, ERROR, DEBUG"
                    },
                    {
                        "name": "timestamp",
                        "dataType": ["date"],
                        "description": "时间戳"
                    },
                    # 通用元数据字段
                    {
                        "name": "category",
                        "dataType": ["string"],
                        "description": "分类"
                    },
                    {
                        "name": "tags",
                        "dataType": ["string[]"],
                        "description": "标签列表"
                    },
                    {
                        "name": "author",
                        "dataType": ["string"],
                        "description": "作者"
                    },
                    {
                        "name": "created_at",
                        "dataType": ["date"],
                        "description": "创建时间"
                    },
                    {
                        "name": "updated_at",
                        "dataType": ["date"],
                        "description": "更新时间"
                    },
                    {
                        "name": "metadata",
                        "dataType": ["text"],
                        "description": "额外元数据JSON字符串"
                    },
                    # RAG专用字段
                    {
                        "name": "chunk_index",
                        "dataType": ["int"],
                        "description": "文档分块索引"
                    },
                    {
                        "name": "chunk_size",
                        "dataType": ["int"],
                        "description": "分块大小"
                    },
                    {
                        "name": "parent_id",
                        "dataType": ["string"],
                        "description": "父文档ID"
                    }
                ]
            }
            
            # 2. FullTextCollection - 用于BM25全文搜索和关键词匹配
            fulltext_collection_schema = {
                "class": "FullTextCollection",
                "description": "全文搜索专用Collection，支持BM25和关键词匹配",
                "vectorizer": "none",
                "properties": [
                    {
                        "name": "content",
                        "dataType": ["text"],
                        "description": "文档内容或日志内容",
                        "tokenization": "word"
                    },
                    {
                        "name": "title",
                        "dataType": ["string"],
                        "description": "标题或摘要"
                    },
                    {
                        "name": "source_type",
                        "dataType": ["string"],
                        "description": "数据源类型: logs, wiki, gitlab, jira"
                    },
                    {
                        "name": "source_id",
                        "dataType": ["string"],
                        "description": "源系统中的唯一ID"
                    },
                    # 日志特定字段
                    {
                        "name": "service_name",
                        "dataType": ["string"],
                        "description": "服务名称"
                    },
                    {
                        "name": "hostname",
                        "dataType": ["string"],
                        "description": "机器名/主机名"
                    },
                    {
                        "name": "log_file",
                        "dataType": ["string"],
                        "description": "日志文件名"
                    },
                    {
                        "name": "line_number",
                        "dataType": ["int"],
                        "description": "日志行数"
                    },
                    {
                        "name": "log_level",
                        "dataType": ["string"],
                        "description": "日志级别: INFO, WARN, ERROR, DEBUG"
                    },
                    {
                        "name": "timestamp",
                        "dataType": ["date"],
                        "description": "时间戳"
                    },
                    # 通用元数据字段
                    {
                        "name": "category",
                        "dataType": ["string"],
                        "description": "分类"
                    },
                    {
                        "name": "tags",
                        "dataType": ["string[]"],
                        "description": "标签列表"
                    },
                    {
                        "name": "author",
                        "dataType": ["string"],
                        "description": "作者"
                    },
                    {
                        "name": "created_at",
                        "dataType": ["date"],
                        "description": "创建时间"
                    },
                    {
                        "name": "updated_at",
                        "dataType": ["date"],
                        "description": "更新时间"
                    },
                    {
                        "name": "metadata",
                        "dataType": ["text"],
                        "description": "额外元数据JSON字符串"
                    },
                    # 全文搜索优化字段
                    {
                        "name": "keywords",
                        "dataType": ["string[]"],
                        "description": "提取的关键词列表"
                    },
                    {
                        "name": "entities",
                        "dataType": ["string[]"],
                        "description": "识别的实体列表"
                    }
                ]
            }
            
            # 创建schemas
            self.client.schema.create_class(embedding_collection_schema)
            self.client.schema.create_class(fulltext_collection_schema)
            
            self.logger.info("RAG schema created successfully with EmbeddingCollection and FullTextCollection")
            
        except Exception as e:
            self.logger.error(f"Failed to create RAG schema: {e}")
            raise
    
    async def add_embedding_document(
        self,
        content: str,
        title: str = "",
        source_type: str = "unknown",
        source_id: Optional[str] = None,
        service_name: Optional[str] = None,
        hostname: Optional[str] = None,
        log_file: Optional[str] = None,
        line_number: Optional[int] = None,
        log_level: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_index: Optional[int] = None,
        chunk_size: Optional[int] = None,
        parent_id: Optional[str] = None,
        vector: Optional[List[float]] = None
    ) -> str:
        """添加文档到EmbeddingCollection"""
        try:
            current_time = datetime.utcnow()
            properties = {
                "content": content,
                "title": title,
                "source_type": source_type,
                "source_id": source_id or str(uuid_lib.uuid4()),
                "category": category or "未分类",
                "tags": tags or [],
                "author": author or "系统",
                "created_at": current_time.isoformat() + "Z",
                "updated_at": current_time.isoformat() + "Z",
                "metadata": json.dumps(metadata or {})
            }
            
            # 添加日志特定字段
            if service_name:
                properties["service_name"] = service_name
            if hostname:
                properties["hostname"] = hostname
            if log_file:
                properties["log_file"] = log_file
            if line_number is not None:
                properties["line_number"] = line_number
            if log_level:
                properties["log_level"] = log_level
            if timestamp:
                properties["timestamp"] = timestamp.isoformat() + "Z"
                
            # 添加RAG分块字段
            if chunk_index is not None:
                properties["chunk_index"] = chunk_index
            if chunk_size is not None:
                properties["chunk_size"] = chunk_size
            if parent_id:
                properties["parent_id"] = parent_id
            
            # 添加对象到EmbeddingCollection
            uuid = self.client.data_object.create(
                data_object=properties,
                class_name="EmbeddingCollection",
                vector=vector
            )
            
            self.logger.info(f"Added embedding document with UUID: {uuid}")
            return uuid
            
        except Exception as e:
            self.logger.error(f"Failed to add embedding document: {e}")
            raise
    
    async def add_fulltext_document(
        self,
        content: str,
        title: str = "",
        source_type: str = "unknown",
        source_id: Optional[str] = None,
        service_name: Optional[str] = None,
        hostname: Optional[str] = None,
        log_file: Optional[str] = None,
        line_number: Optional[int] = None,
        log_level: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        author: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        keywords: Optional[List[str]] = None,
        entities: Optional[List[str]] = None
    ) -> str:
        """添加文档到FullTextCollection"""
        try:
            current_time = datetime.utcnow()
            properties = {
                "content": content,
                "title": title,
                "source_type": source_type,
                "source_id": source_id or str(uuid_lib.uuid4()),
                "category": category or "未分类",
                "tags": tags or [],
                "author": author or "系统",
                "created_at": current_time.isoformat() + "Z",
                "updated_at": current_time.isoformat() + "Z",
                "metadata": json.dumps(metadata or {}),
                "keywords": keywords or [],
                "entities": entities or []
            }
            
            # 添加日志特定字段
            if service_name:
                properties["service_name"] = service_name
            if hostname:
                properties["hostname"] = hostname
            if log_file:
                properties["log_file"] = log_file
            if line_number is not None:
                properties["line_number"] = line_number
            if log_level:
                properties["log_level"] = log_level
            if timestamp:
                properties["timestamp"] = timestamp.isoformat() + "Z"
            
            # 添加对象到FullTextCollection
            uuid = self.client.data_object.create(
                data_object=properties,
                class_name="FullTextCollection"
            )
            
            self.logger.info(f"Added fulltext document with UUID: {uuid}")
            return uuid
            
        except Exception as e:
            self.logger.error(f"Failed to add fulltext document: {e}")
            raise
    
    def _build_filter_conditions(
        self,
        service_name: Optional[str] = None,
        hostname: Optional[str] = None,
        log_file: Optional[str] = None,
        line_number_range: Optional[Tuple[int, int]] = None,
        timestamp_range: Optional[Tuple[datetime, datetime]] = None,
        source_type: Optional[str] = None,
        log_level: Optional[str] = None,
        category: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """构建过滤条件"""
        conditions = []
        
        if service_name:
            conditions.append({
                "path": ["service_name"],
                "operator": "Equal",
                "valueText": service_name
            })
        
        if hostname:
            conditions.append({
                "path": ["hostname"],
                "operator": "Equal",
                "valueText": hostname
            })
        
        if log_file:
            conditions.append({
                "path": ["log_file"],
                "operator": "Equal",
                "valueText": log_file
            })
        
        if line_number_range:
            start_line, end_line = line_number_range
            conditions.append({
                "path": ["line_number"],
                "operator": "GreaterThanEqual",
                "valueInt": start_line
            })
            conditions.append({
                "path": ["line_number"],
                "operator": "LessThanEqual",
                "valueInt": end_line
            })
        
        if timestamp_range:
            start_time, end_time = timestamp_range
            conditions.append({
                "path": ["timestamp"],
                "operator": "GreaterThanEqual",
                "valueDate": start_time.isoformat() + "Z"
            })
            conditions.append({
                "path": ["timestamp"],
                "operator": "LessThanEqual",
                "valueDate": end_time.isoformat() + "Z"
            })
        
        if source_type:
            conditions.append({
                "path": ["source_type"],
                "operator": "Equal",
                "valueText": source_type
            })
        
        if log_level:
            conditions.append({
                "path": ["log_level"],
                "operator": "Equal",
                "valueText": log_level
            })
        
        if category:
            conditions.append({
                "path": ["category"],
                "operator": "Equal",
                "valueText": category
            })
        
        if not conditions:
            return None
        elif len(conditions) == 1:
            return conditions[0]
        else:
            return {
                "operator": "And",
                "operands": conditions
            }
    
    async def embedding_search(
        self,
        query_vector: List[float],
        limit: int = 10,
        certainty: float = 0.7,
        service_name: Optional[str] = None,
        hostname: Optional[str] = None,
        log_file: Optional[str] = None,
        line_number_range: Optional[Tuple[int, int]] = None,
        timestamp_range: Optional[Tuple[datetime, datetime]] = None,
        source_type: Optional[str] = None,
        log_level: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """EmbeddingCollection向量搜索，支持多维过滤"""
        try:
            where_filter = self._build_filter_conditions(
                service_name=service_name,
                hostname=hostname,
                log_file=log_file,
                line_number_range=line_number_range,
                timestamp_range=timestamp_range,
                source_type=source_type,
                log_level=log_level,
                category=category
            )
            
            query = (
                self.client.query
                .get("EmbeddingCollection", ["content", "title", "source_type", "source_id", "service_name", "hostname", "log_file", "line_number", "log_level", "timestamp", "category", "tags", "author", "created_at", "updated_at", "metadata", "chunk_index", "chunk_size", "parent_id"])
                .with_near_vector({"vector": query_vector, "certainty": certainty})
                .with_limit(limit)
                .with_additional(["certainty", "distance"])
            )
            
            if where_filter:
                query = query.with_where(where_filter)
            
            result = query.do()
            
            if "data" in result and "Get" in result["data"] and "EmbeddingCollection" in result["data"]["Get"]:
                return result["data"]["Get"]["EmbeddingCollection"]
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Embedding search failed: {e}")
            return []
    
    async def fulltext_search(
        self,
        query: str,
        limit: int = 10,
        service_name: Optional[str] = None,
        hostname: Optional[str] = None,
        log_file: Optional[str] = None,
        line_number_range: Optional[Tuple[int, int]] = None,
        timestamp_range: Optional[Tuple[datetime, datetime]] = None,
        source_type: Optional[str] = None,
        log_level: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """FullTextCollection BM25全文搜索，支持多维过滤"""
        try:
            where_filter = self._build_filter_conditions(
                service_name=service_name,
                hostname=hostname,
                log_file=log_file,
                line_number_range=line_number_range,
                timestamp_range=timestamp_range,
                source_type=source_type,
                log_level=log_level,
                category=category
            )
            
            search_query = (
                self.client.query
                .get("FullTextCollection", ["content", "title", "source_type", "source_id", "service_name", "hostname", "log_file", "line_number", "log_level", "timestamp", "category", "tags", "author", "created_at", "updated_at", "metadata", "keywords", "entities"])
                .with_bm25(query=query)
                .with_limit(limit)
                .with_additional(["score"])
            )
            
            if where_filter:
                search_query = search_query.with_where(where_filter)
            
            result = search_query.do()
            
            if "data" in result and "Get" in result["data"] and "FullTextCollection" in result["data"]["Get"]:
                return result["data"]["Get"]["FullTextCollection"]
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Fulltext search failed: {e}")
            return []
    
    async def hybrid_search_with_rerank(
        self,
        query: str,
        query_vector: Optional[List[float]] = None,
        limit: int = 10,
        alpha: float = 0.7,  # 0 = pure BM25, 1 = pure vector search
        service_name: Optional[str] = None,
        hostname: Optional[str] = None,
        log_file: Optional[str] = None,
        line_number_range: Optional[Tuple[int, int]] = None,
        timestamp_range: Optional[Tuple[datetime, datetime]] = None,
        source_type: Optional[str] = None,
        log_level: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """混合搜索 + Rerank - 同时查询两个Collection并融合结果"""
        try:
            results = {"embedding_results": [], "fulltext_results": [], "merged_results": []}
            
            # 1. 向量搜索 (如果提供了query_vector)
            if query_vector:
                embedding_results = await self.embedding_search(
                    query_vector=query_vector,
                    limit=limit,
                    service_name=service_name,
                    hostname=hostname,
                    log_file=log_file,
                    line_number_range=line_number_range,
                    timestamp_range=timestamp_range,
                    source_type=source_type,
                    log_level=log_level,
                    category=category
                )
                results["embedding_results"] = embedding_results
            
            # 2. 全文搜索
            fulltext_results = await self.fulltext_search(
                query=query,
                limit=limit,
                service_name=service_name,
                hostname=hostname,
                log_file=log_file,
                line_number_range=line_number_range,
                timestamp_range=timestamp_range,
                source_type=source_type,
                log_level=log_level,
                category=category
            )
            results["fulltext_results"] = fulltext_results
            
            # 3. 结果融合和Rerank
            merged_results = self._merge_and_rerank(
                embedding_results=results["embedding_results"],
                fulltext_results=fulltext_results,
                alpha=alpha,
                limit=limit
            )
            results["merged_results"] = merged_results
            
            return results
            
        except Exception as e:
            self.logger.error(f"Hybrid search with rerank failed: {e}")
            return {"embedding_results": [], "fulltext_results": [], "merged_results": []}
    
    def _merge_and_rerank(
        self,
        embedding_results: List[Dict[str, Any]],
        fulltext_results: List[Dict[str, Any]],
        alpha: float,
        limit: int
    ) -> List[Dict[str, Any]]:
        """融合和Rerank结果"""
        try:
            # 使用source_id作为去重键
            merged = {}
            
            # 处理向量搜索结果
            for result in embedding_results:
                source_id = result.get("source_id", "")
                if source_id:
                    certainty = result.get("_additional", {}).get("certainty", 0.0)
                    merged[source_id] = {
                        **result,
                        "embedding_score": certainty,
                        "fulltext_score": 0.0,
                        "final_score": certainty * alpha,
                        "search_source": "embedding"
                    }
            
            # 处理全文搜索结果
            for result in fulltext_results:
                source_id = result.get("source_id", "")
                if source_id:
                    bm25_score = result.get("_additional", {}).get("score", 0.0)
                    if source_id in merged:
                        # 已存在，更新分数
                        merged[source_id]["fulltext_score"] = bm25_score
                        merged[source_id]["final_score"] += bm25_score * (1 - alpha)
                        merged[source_id]["search_source"] = "hybrid"
                    else:
                        # 新结果
                        merged[source_id] = {
                            **result,
                            "embedding_score": 0.0,
                            "fulltext_score": bm25_score,
                            "final_score": bm25_score * (1 - alpha),
                            "search_source": "fulltext"
                        }
            
            # 按最终分数排序
            sorted_results = sorted(
                merged.values(),
                key=lambda x: x["final_score"],
                reverse=True
            )
            
            return sorted_results[:limit]
            
        except Exception as e:
            self.logger.error(f"Merge and rerank failed: {e}")
            return []
    
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
            
            for class_name in ["EmbeddingCollection", "FullTextCollection"]:
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
            self.client = None
            self.logger.info("RAG Vector service connection closed")