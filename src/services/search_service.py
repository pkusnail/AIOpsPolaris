"""
搜索服务
整合向量搜索、关键词搜索和图查询的混合搜索引擎
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import asyncio
from collections import defaultdict
import numpy as np

from .vector_service import VectorService
from .graph_service import GraphService
from .database_service import DatabaseService
from .embedding_service import EmbeddingService
from config.settings import settings

logger = logging.getLogger(__name__)


class SearchService:
    """混合搜索服务类"""
    
    def __init__(self):
        self.vector_service = VectorService()
        self.graph_service = GraphService()
        self.database_service = DatabaseService()
        self.embedding_service = EmbeddingService()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def hybrid_search(
        self,
        query: str,
        search_type: str = "hybrid",
        source: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.7
    ) -> Dict[str, Any]:
        """混合搜索：结合向量搜索、关键词搜索和图查询"""
        start_time = datetime.utcnow()
        
        try:
            results = []
            
            if search_type == "vector":
                results = await self._vector_search(query, limit, threshold)
            elif search_type == "keyword":
                results = await self._keyword_search(query, source, category, limit)
            elif search_type == "graph":
                results = await self._graph_search(query, limit)
            elif search_type == "hybrid":
                # 并行执行多种搜索
                vector_results, keyword_results, graph_results = await asyncio.gather(
                    self._vector_search(query, limit, threshold),
                    self._keyword_search(query, source, category, limit),
                    self._graph_search(query, limit//2),
                    return_exceptions=True
                )
                
                # 处理异常结果
                if isinstance(vector_results, Exception):
                    vector_results = []
                if isinstance(keyword_results, Exception):
                    keyword_results = []
                if isinstance(graph_results, Exception):
                    graph_results = []
                
                # 融合结果
                results = self._merge_search_results(
                    vector_results, 
                    keyword_results,
                    graph_results,
                    limit
                )
            else:
                raise ValueError(f"Unknown search type: {search_type}")
            
            # 计算处理时间
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "results": results,
                "total": len(results),
                "query": query,
                "search_type": search_type,
                "processing_time": processing_time,
                "metadata": {
                    "source_filter": source,
                    "category_filter": category,
                    "threshold": threshold
                }
            }
            
        except Exception as e:
            self.logger.error(f"Hybrid search failed: {e}")
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            return {
                "results": [],
                "total": 0,
                "query": query,
                "search_type": search_type,
                "processing_time": processing_time,
                "error": str(e)
            }
    
    async def _vector_search(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """向量相似性搜索"""
        try:
            # 生成查询向量
            query_embedding = await self.embedding_service.encode_query(query)
            
            # 构建过滤条件
            where_filter = None
            
            # 在Weaviate中搜索
            weaviate_results = await self.vector_service.vector_search(
                query_vector=query_embedding,
                class_name="KnowledgeDocument",
                limit=limit,
                certainty=threshold,
                where_filter=where_filter
            )
            
            # 转换结果格式
            results = []
            for item in weaviate_results:
                if "_additional" in item:
                    score = item["_additional"].get("certainty", 0.0)
                else:
                    score = 0.0
                
                results.append({
                    "id": item.get("mysql_id", ""),
                    "title": item.get("title", ""),
                    "content": item.get("content", "")[:500] + "..." if len(item.get("content", "")) > 500 else item.get("content", ""),
                    "source": item.get("source", ""),
                    "category": item.get("category"),
                    "tags": item.get("tags", []),
                    "score": score,
                    "search_type": "vector",
                    "highlight": self._generate_highlight(item.get("content", ""), query)
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            return []
    
    async def _keyword_search(
        self,
        query: str,
        source: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """关键词搜索（基于MySQL全文索引）"""
        try:
            # 使用数据库服务进行全文搜索
            documents = await self.database_service.search_knowledge_documents(
                query=query,
                source=source,
                category=category,
                limit=limit
            )
            
            # 转换结果格式
            results = []
            for doc in documents:
                results.append({
                    "id": doc.id,
                    "title": doc.title,
                    "content": doc.content[:500] + "..." if len(doc.content) > 500 else doc.content,
                    "source": doc.source,
                    "category": doc.category,
                    "tags": doc.tags or [],
                    "score": 0.8,  # MySQL全文搜索没有标准化评分
                    "search_type": "keyword",
                    "highlight": self._generate_highlight(doc.content, query)
                })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Keyword search failed: {e}")
            return []
    
    async def _graph_search(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """图查询搜索"""
        try:
            results = []
            
            # 首先尝试在图中查找与查询相关的实体
            related_entities = await self._find_query_entities(query)
            
            for entity in related_entities[:limit]:
                # 查找与实体相关的文档
                cypher_query = """
                MATCH (e:Entity {name: $entity_name})<-[:MENTIONS]-(d:Document)
                RETURN d.mysql_id as doc_id, d.title as title, d.content as content,
                       d.source as source, d.category as category
                LIMIT 3
                """
                
                graph_results = await self.graph_service.execute_cypher(
                    cypher_query,
                    {"entity_name": entity["name"]}
                )
                
                for result in graph_results:
                    results.append({
                        "id": result.get("doc_id", ""),
                        "title": result.get("title", ""),
                        "content": result.get("content", "")[:500] + "..." if result.get("content") and len(result.get("content")) > 500 else result.get("content", ""),
                        "source": result.get("source", ""),
                        "category": result.get("category"),
                        "tags": [],
                        "score": 0.7,
                        "search_type": "graph",
                        "related_entity": entity["name"],
                        "entity_type": entity["type"]
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Graph search failed: {e}")
            return []
    
    async def _find_query_entities(self, query: str) -> List[Dict[str, Any]]:
        """在查询中查找相关实体"""
        try:
            # 简单的实体匹配策略
            query_lower = query.lower()
            entities = []
            
            # 查找匹配的实体
            cypher_query = """
            MATCH (e:Entity)
            WHERE toLower(e.name) CONTAINS $query
               OR toLower(e.type) CONTAINS $query
            RETURN e.name as name, e.type as type, id(e) as node_id
            LIMIT 10
            """
            
            results = await self.graph_service.execute_cypher(
                cypher_query,
                {"query": query_lower}
            )
            
            for result in results:
                entities.append({
                    "name": result["name"],
                    "type": result["type"],
                    "node_id": result["node_id"]
                })
            
            return entities
            
        except Exception as e:
            self.logger.error(f"Failed to find query entities: {e}")
            return []
    
    def _merge_search_results(
        self,
        vector_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        graph_results: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """融合多种搜索结果"""
        try:
            # 使用加权评分融合结果
            vector_weight = settings.search.vector_weight
            keyword_weight = settings.search.keyword_weight
            graph_weight = 1.0 - vector_weight - keyword_weight
            
            # 收集所有结果并去重
            all_results = {}
            
            # 处理向量搜索结果
            for result in vector_results:
                doc_id = result["id"]
                if doc_id not in all_results:
                    all_results[doc_id] = result.copy()
                    all_results[doc_id]["final_score"] = result["score"] * vector_weight
                    all_results[doc_id]["score_details"] = {
                        "vector_score": result["score"],
                        "keyword_score": 0.0,
                        "graph_score": 0.0
                    }
                else:
                    all_results[doc_id]["score_details"]["vector_score"] = result["score"]
                    all_results[doc_id]["final_score"] += result["score"] * vector_weight
            
            # 处理关键词搜索结果
            for result in keyword_results:
                doc_id = result["id"]
                if doc_id not in all_results:
                    all_results[doc_id] = result.copy()
                    all_results[doc_id]["final_score"] = result["score"] * keyword_weight
                    all_results[doc_id]["score_details"] = {
                        "vector_score": 0.0,
                        "keyword_score": result["score"],
                        "graph_score": 0.0
                    }
                else:
                    all_results[doc_id]["score_details"]["keyword_score"] = result["score"]
                    all_results[doc_id]["final_score"] += result["score"] * keyword_weight
            
            # 处理图搜索结果
            for result in graph_results:
                doc_id = result["id"]
                if doc_id not in all_results:
                    all_results[doc_id] = result.copy()
                    all_results[doc_id]["final_score"] = result["score"] * graph_weight
                    all_results[doc_id]["score_details"] = {
                        "vector_score": 0.0,
                        "keyword_score": 0.0,
                        "graph_score": result["score"]
                    }
                else:
                    all_results[doc_id]["score_details"]["graph_score"] = result["score"]
                    all_results[doc_id]["final_score"] += result["score"] * graph_weight
                    # 保留图搜索的额外信息
                    if "related_entity" in result:
                        all_results[doc_id]["related_entity"] = result["related_entity"]
                    if "entity_type" in result:
                        all_results[doc_id]["entity_type"] = result["entity_type"]
            
            # 按最终得分排序
            sorted_results = sorted(
                all_results.values(),
                key=lambda x: x["final_score"],
                reverse=True
            )
            
            # 更新search_type为hybrid
            for result in sorted_results:
                result["search_type"] = "hybrid"
            
            return sorted_results[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to merge search results: {e}")
            return []
    
    def _generate_highlight(self, content: str, query: str, max_length: int = 200) -> str:
        """生成搜索结果高亮片段"""
        try:
            if not content or not query:
                return content[:max_length] + "..." if len(content) > max_length else content
            
            query_words = query.lower().split()
            content_lower = content.lower()
            
            # 找到第一个匹配的位置
            best_pos = -1
            for word in query_words:
                pos = content_lower.find(word)
                if pos != -1:
                    best_pos = pos
                    break
            
            if best_pos == -1:
                # 没有找到匹配，返回开头
                return content[:max_length] + "..." if len(content) > max_length else content
            
            # 计算高亮片段的起始和结束位置
            start = max(0, best_pos - max_length // 2)
            end = min(len(content), start + max_length)
            
            # 调整起始位置以避免截断单词
            if start > 0:
                while start < len(content) and content[start] != ' ':
                    start += 1
                start += 1
            
            # 调整结束位置以避免截断单词
            if end < len(content):
                while end > 0 and content[end] != ' ':
                    end -= 1
            
            highlight = content[start:end]
            
            # 添加省略号
            if start > 0:
                highlight = "..." + highlight
            if end < len(content):
                highlight = highlight + "..."
            
            return highlight
            
        except Exception as e:
            self.logger.error(f"Failed to generate highlight: {e}")
            return content[:max_length] + "..." if len(content) > max_length else content
    
    async def semantic_search(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.7
    ) -> Dict[str, Any]:
        """纯语义搜索"""
        return await self.hybrid_search(
            query=query,
            search_type="vector",
            limit=limit,
            threshold=threshold
        )
    
    async def find_similar_documents(
        self,
        doc_id: str,
        limit: int = 5
    ) -> Dict[str, Any]:
        """查找相似文档"""
        try:
            # 首先获取原文档
            original_doc = await self.database_service.get_knowledge_document_by_id(doc_id)
            if not original_doc:
                return {"results": [], "total": 0, "error": "Document not found"}
            
            # 使用文档内容作为查询
            query_text = f"{original_doc.title} {original_doc.content[:500]}"
            
            # 执行向量搜索
            results = await self.hybrid_search(
                query=query_text,
                search_type="vector",
                limit=limit + 1  # +1 因为可能包含原文档
            )
            
            # 过滤掉原文档
            filtered_results = [
                r for r in results["results"] 
                if r["id"] != doc_id
            ][:limit]
            
            return {
                "results": filtered_results,
                "total": len(filtered_results),
                "original_document": {
                    "id": original_doc.id,
                    "title": original_doc.title
                },
                "processing_time": results.get("processing_time", 0.0)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to find similar documents: {e}")
            return {"results": [], "total": 0, "error": str(e)}
    
    async def search_by_entity(
        self,
        entity_name: str,
        entity_type: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """根据实体搜索相关文档"""
        try:
            # 构建图查询
            if entity_type:
                cypher_query = """
                MATCH (e:Entity {name: $entity_name, type: $entity_type})<-[:MENTIONS]-(d:Document)
                RETURN d.mysql_id as doc_id, d.title as title, d.content as content,
                       d.source as source, d.category as category
                LIMIT $limit
                """
                params = {
                    "entity_name": entity_name,
                    "entity_type": entity_type,
                    "limit": limit
                }
            else:
                cypher_query = """
                MATCH (e:Entity {name: $entity_name})<-[:MENTIONS]-(d:Document)
                RETURN d.mysql_id as doc_id, d.title as title, d.content as content,
                       d.source as source, d.category as category, e.type as entity_type
                LIMIT $limit
                """
                params = {
                    "entity_name": entity_name,
                    "limit": limit
                }
            
            start_time = datetime.utcnow()
            graph_results = await self.graph_service.execute_cypher(cypher_query, params)
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # 转换结果格式
            results = []
            for result in graph_results:
                results.append({
                    "id": result.get("doc_id", ""),
                    "title": result.get("title", ""),
                    "content": result.get("content", "")[:500] + "..." if result.get("content") and len(result.get("content")) > 500 else result.get("content", ""),
                    "source": result.get("source", ""),
                    "category": result.get("category"),
                    "tags": [],
                    "score": 1.0,
                    "search_type": "entity",
                    "entity_name": entity_name,
                    "entity_type": result.get("entity_type", entity_type)
                })
            
            return {
                "results": results,
                "total": len(results),
                "query_entity": {
                    "name": entity_name,
                    "type": entity_type
                },
                "processing_time": processing_time
            }
            
        except Exception as e:
            self.logger.error(f"Failed to search by entity: {e}")
            return {"results": [], "total": 0, "error": str(e)}
    
    async def get_search_suggestions(
        self,
        query: str,
        limit: int = 5
    ) -> List[str]:
        """获取搜索建议"""
        try:
            suggestions = []
            
            # 基于已有实体生成建议
            entities = await self._find_query_entities(query)
            for entity in entities[:limit]:
                suggestions.append(f"{entity['name']} ({entity['type']})")
            
            # 添加一些通用的运维查询建议
            common_queries = [
                "CPU使用率高",
                "内存泄露问题",
                "数据库连接失败",
                "服务重启",
                "网络延迟",
                "磁盘空间不足",
                "日志错误",
                "性能优化"
            ]
            
            # 查找包含查询关键词的建议
            query_lower = query.lower()
            for common_query in common_queries:
                if query_lower in common_query.lower() and len(suggestions) < limit:
                    suggestions.append(common_query)
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Failed to get search suggestions: {e}")
            return []
    
    async def get_search_stats(self) -> Dict[str, Any]:
        """获取搜索统计信息"""
        try:
            # 获取各组件统计信息
            vector_stats = await self.vector_service.get_stats()
            graph_stats = await self.graph_service.get_graph_stats()
            
            return {
                "vector_database": vector_stats,
                "knowledge_graph": graph_stats,
                "search_settings": {
                    "vector_weight": settings.search.vector_weight,
                    "keyword_weight": settings.search.keyword_weight,
                    "default_limit": settings.search.default_limit,
                    "similarity_threshold": settings.search.similarity_threshold
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get search stats: {e}")
            return {}
    
    async def close(self):
        """关闭搜索服务"""
        try:
            await self.graph_service.close()
            self.vector_service.close()
            self.embedding_service.close()
            self.logger.info("Search service closed")
        except Exception as e:
            self.logger.error(f"Failed to close search service: {e}")