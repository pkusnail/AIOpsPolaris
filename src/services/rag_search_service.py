"""
RAG搜索服务 - 整合新的RAG Pipeline与现有Agent系统
为Agent提供统一的搜索接口，支持混合搜索和过滤
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

from .rag_vector_service import RAGVectorService
from .embedding_service import EmbeddingService
from .graph_service import GraphService

logger = logging.getLogger(__name__)


class RAGSearchService:
    """RAG搜索服务 - Agent专用接口"""
    
    def __init__(self):
        self.rag_service = RAGVectorService()
        self.embedding_service = EmbeddingService()
        self.graph_service = GraphService()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def search_for_rca(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        search_type: str = "hybrid",
        limit: int = 10
    ) -> Dict[str, Any]:
        """为RCA (根因分析) 提供专门的搜索功能"""
        try:
            start_time = datetime.utcnow()
            
            # 解析context中的过滤条件
            filters = self._parse_rca_context(context or {})
            
            # 生成查询向量
            query_vector = None
            try:
                query_vector = await self.embedding_service.encode_text(query)
            except Exception as e:
                self.logger.warning(f"Failed to generate query vector: {e}")
            
            results = {
                "logs": [],
                "knowledge": [],
                "entities": [],
                "merged_results": [],
                "search_metadata": {}
            }
            
            # 1. 搜索相关日志 (特别重要用于RCA)
            if search_type in ["hybrid", "logs"]:
                log_results = await self._search_logs_for_rca(
                    query, query_vector, filters, limit
                )
                results["logs"] = log_results
            
            # 2. 搜索知识文档
            if search_type in ["hybrid", "knowledge"]:
                knowledge_results = await self._search_knowledge_for_rca(
                    query, query_vector, filters, limit
                )
                results["knowledge"] = knowledge_results
            
            # 3. 查询相关实体和关系
            if search_type in ["hybrid", "graph"]:
                entity_results = await self._search_entities_for_rca(
                    query, filters
                )
                results["entities"] = entity_results
            
            # 4. 融合和重排序结果
            if search_type == "hybrid":
                merged_results = self._merge_rca_results(
                    results["logs"],
                    results["knowledge"], 
                    results["entities"],
                    limit
                )
                results["merged_results"] = merged_results
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            results["search_metadata"] = {
                "query": query,
                "search_type": search_type,
                "processing_time": processing_time,
                "filters_applied": filters,
                "total_results": len(results.get("merged_results", [])) or sum(len(results[k]) for k in ["logs", "knowledge", "entities"])
            }
            
            return results
            
        except Exception as e:
            self.logger.error(f"RCA search failed: {e}")
            return {
                "logs": [],
                "knowledge": [],
                "entities": [],
                "merged_results": [],
                "search_metadata": {"error": str(e)}
            }
    
    def _parse_rca_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """解析RCA上下文信息提取过滤条件"""
        filters = {}
        
        try:
            # 从用户查询中提取服务名
            user_message = context.get("user_message", "").lower()
            
            # 检测服务名
            services = ["service-a", "service-b", "service-c", "service-d", "service-e"]
            for service in services:
                if service in user_message:
                    filters["service_name"] = service
                    break
            
            # 检测日志级别
            log_levels = ["error", "warn", "info", "debug", "critical"]
            for level in log_levels:
                if level in user_message:
                    filters["log_level"] = level.upper()
                    break
            
            # 检测时间范围 (如果提供)
            if "最近" in context.get("user_message", ""):
                from datetime import timedelta
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(hours=24)  # 最近24小时
                filters["timestamp_range"] = (start_time, end_time)
            
            # 检测主机名
            hosts = ["d1-app-01", "d1-app-02", "d2-app-01", "d2-app-02"]
            for host in hosts:
                if host in user_message:
                    filters["hostname"] = host
                    break
            
            return filters
            
        except Exception as e:
            self.logger.error(f"Failed to parse RCA context: {e}")
            return {}
    
    async def _search_logs_for_rca(
        self,
        query: str,
        query_vector: Optional[List[float]],
        filters: Dict[str, Any],
        limit: int
    ) -> List[Dict[str, Any]]:
        """搜索与RCA相关的日志"""
        try:
            # 优先搜索ERROR级别的日志
            error_filters = {**filters, "log_level": "ERROR"}
            
            if query_vector:
                # 混合搜索错误日志
                hybrid_results = await self.rag_service.hybrid_search_with_rerank(
                    query=query,
                    query_vector=query_vector,
                    limit=limit // 2,
                    source_type="logs",
                    **error_filters
                )
                error_logs = hybrid_results.get("merged_results", [])
            else:
                # 全文搜索错误日志
                error_logs = await self.rag_service.fulltext_search(
                    query=query,
                    limit=limit // 2,
                    source_type="logs",
                    **error_filters
                )
            
            # 搜索其他级别的相关日志
            other_filters = {k: v for k, v in filters.items() if k != "log_level"}
            if query_vector:
                other_results = await self.rag_service.hybrid_search_with_rerank(
                    query=query,
                    query_vector=query_vector,
                    limit=limit // 2,
                    source_type="logs",
                    **other_filters
                )
                other_logs = other_results.get("merged_results", [])
            else:
                other_logs = await self.rag_service.fulltext_search(
                    query=query,
                    limit=limit // 2,
                    source_type="logs",
                    **other_filters
                )
            
            # 合并结果，ERROR日志优先
            all_logs = error_logs + other_logs
            
            # 为RCA添加特殊标记
            for log in all_logs:
                log["rca_relevance"] = self._calculate_rca_relevance(log, query)
                log["result_type"] = "log"
            
            # 按RCA相关性排序
            all_logs.sort(key=lambda x: x["rca_relevance"], reverse=True)
            
            return all_logs[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to search logs for RCA: {e}")
            return []
    
    async def _search_knowledge_for_rca(
        self,
        query: str,
        query_vector: Optional[List[float]],
        filters: Dict[str, Any],
        limit: int
    ) -> List[Dict[str, Any]]:
        """搜索与RCA相关的知识文档"""
        try:
            # 扩展查询以包含故障排查相关词汇
            rca_query = f"{query} 故障排查 troubleshooting 根因分析"
            
            knowledge_results = []
            
            if query_vector:
                # 语义搜索知识文档
                vector_results = await self.rag_service.embedding_search(
                    query_vector=query_vector,
                    limit=limit,
                    source_type="wiki"
                )
                knowledge_results.extend(vector_results)
            
            # 全文搜索相关文档
            fulltext_results = await self.rag_service.fulltext_search(
                query=rca_query,
                limit=limit,
                source_type="wiki"
            )
            knowledge_results.extend(fulltext_results)
            
            # 去重并添加RCA相关性评分
            unique_results = {}
            for result in knowledge_results:
                source_id = result.get("source_id", "")
                if source_id and source_id not in unique_results:
                    result["rca_relevance"] = self._calculate_knowledge_rca_relevance(result, query)
                    result["result_type"] = "knowledge"
                    unique_results[source_id] = result
            
            # 排序并返回
            sorted_results = sorted(
                unique_results.values(),
                key=lambda x: x["rca_relevance"],
                reverse=True
            )
            
            return sorted_results[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to search knowledge for RCA: {e}")
            return []
    
    async def _search_entities_for_rca(
        self,
        query: str,
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """搜索与RCA相关的实体"""
        try:
            # 查找查询中提到的实体
            query_words = query.lower().split()
            entities = []
            
            for word in query_words:
                if len(word) < 3:
                    continue
                
                # 查找匹配的实体
                cypher_query = """
                MATCH (e:Entity)
                WHERE toLower(e.name) CONTAINS $word
                   OR toLower(e.type) CONTAINS $word
                RETURN e.name as name, e.type as type, elementId(e) as node_id,
                       e.confidence as confidence
                LIMIT 5
                """
                
                results = await self.graph_service.execute_cypher(
                    cypher_query,
                    {"word": word}
                )
                
                for result in results:
                    entity_info = {
                        "name": result["name"],
                        "type": result["type"],
                        "node_id": result["node_id"],
                        "confidence": result.get("confidence", 0.5),
                        "result_type": "entity"
                    }
                    
                    # 查找相关实体
                    related_entities = await self.graph_service.find_related_entities(
                        entity_name=result["name"],
                        entity_type=result["type"],
                        max_depth=2
                    )
                    
                    entity_info["related_entities"] = related_entities[:5]
                    entity_info["rca_relevance"] = self._calculate_entity_rca_relevance(entity_info, query)
                    
                    entities.append(entity_info)
            
            # 去重并排序
            unique_entities = {}
            for entity in entities:
                key = f"{entity['name']}_{entity['type']}"
                if key not in unique_entities:
                    unique_entities[key] = entity
            
            sorted_entities = sorted(
                unique_entities.values(),
                key=lambda x: x["rca_relevance"],
                reverse=True
            )
            
            return sorted_entities[:10]
            
        except Exception as e:
            self.logger.error(f"Failed to search entities for RCA: {e}")
            return []
    
    def _calculate_rca_relevance(self, log: Dict[str, Any], query: str) -> float:
        """计算日志对RCA的相关性分数"""
        try:
            relevance = 0.0
            
            # 基础分数
            if log.get("log_level") == "ERROR":
                relevance += 0.4
            elif log.get("log_level") == "WARN":
                relevance += 0.2
            
            # 时间因素 (越近的日志越重要)
            if "timestamp" in log:
                try:
                    log_time = datetime.fromisoformat(log["timestamp"].replace('Z', ''))
                    time_diff = (datetime.utcnow() - log_time).total_seconds()
                    # 24小时内的日志有时间加分
                    if time_diff < 24 * 3600:
                        relevance += 0.2 * (1 - time_diff / (24 * 3600))
                except:
                    pass
            
            # 内容相关性
            content = log.get("content", "").lower()
            query_lower = query.lower()
            
            # 关键词匹配
            rca_keywords = ["error", "exception", "fail", "timeout", "crash", "down"]
            for keyword in rca_keywords:
                if keyword in content or keyword in query_lower:
                    relevance += 0.1
            
            # 服务名匹配
            if log.get("service_name") and log.get("service_name").lower() in query_lower:
                relevance += 0.3
            
            # 原始搜索分数
            if "final_score" in log:
                relevance += log["final_score"] * 0.3
            elif "_additional" in log:
                score = log["_additional"].get("certainty", log["_additional"].get("score", 0))
                relevance += score * 0.3
            
            return min(relevance, 1.0)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate RCA relevance: {e}")
            return 0.5
    
    def _calculate_knowledge_rca_relevance(self, doc: Dict[str, Any], query: str) -> float:
        """计算知识文档对RCA的相关性分数"""
        try:
            relevance = 0.0
            
            # 文档类型加分
            category = doc.get("category", "").lower()
            if "故障" in category or "troubleshooting" in category:
                relevance += 0.3
            if "排查" in category or "diagnostic" in category:
                relevance += 0.3
            
            # 标题和内容相关性
            title = doc.get("title", "").lower()
            content = doc.get("content", "").lower()
            
            rca_terms = ["故障", "排查", "根因", "解决", "troubleshoot", "diagnose", "fix", "resolve"]
            for term in rca_terms:
                if term in title:
                    relevance += 0.2
                if term in content:
                    relevance += 0.1
            
            # 查询匹配度
            query_lower = query.lower()
            query_words = query_lower.split()
            
            for word in query_words:
                if len(word) > 2:
                    if word in title:
                        relevance += 0.15
                    if word in content:
                        relevance += 0.1
            
            # 原始搜索分数
            if "final_score" in doc:
                relevance += doc["final_score"] * 0.4
            elif "_additional" in doc:
                score = doc["_additional"].get("certainty", doc["_additional"].get("score", 0))
                relevance += score * 0.4
            
            return min(relevance, 1.0)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate knowledge RCA relevance: {e}")
            return 0.5
    
    def _calculate_entity_rca_relevance(self, entity: Dict[str, Any], query: str) -> float:
        """计算实体对RCA的相关性分数"""
        try:
            relevance = 0.0
            
            # 实体类型相关性
            entity_type = entity.get("type", "").upper()
            if entity_type in ["SERVICE", "ERROR", "ALERT"]:
                relevance += 0.4
            elif entity_type in ["DATABASE", "SERVER", "CONTAINER"]:
                relevance += 0.3
            elif entity_type in ["METRIC", "LOG_LEVEL"]:
                relevance += 0.2
            
            # 名称匹配
            entity_name = entity.get("name", "").lower()
            query_lower = query.lower()
            
            if entity_name in query_lower:
                relevance += 0.4
            elif any(word in entity_name for word in query_lower.split()):
                relevance += 0.2
            
            # 相关实体数量
            related_count = len(entity.get("related_entities", []))
            relevance += min(related_count * 0.05, 0.2)
            
            # 实体置信度
            confidence = entity.get("confidence", 0.5)
            relevance += confidence * 0.2
            
            return min(relevance, 1.0)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate entity RCA relevance: {e}")
            return 0.5
    
    def _merge_rca_results(
        self,
        logs: List[Dict[str, Any]],
        knowledge: List[Dict[str, Any]],
        entities: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """融合RCA搜索结果"""
        try:
            all_results = []
            
            # 添加所有结果
            all_results.extend(logs)
            all_results.extend(knowledge)
            all_results.extend(entities)
            
            # 按RCA相关性排序
            all_results.sort(key=lambda x: x.get("rca_relevance", 0), reverse=True)
            
            # 确保不同类型的结果都有代表
            balanced_results = []
            log_count = 0
            knowledge_count = 0
            entity_count = 0
            
            for result in all_results:
                result_type = result.get("result_type", "unknown")
                
                # 保证结果类型平衡
                if result_type == "log" and log_count < limit // 2:
                    balanced_results.append(result)
                    log_count += 1
                elif result_type == "knowledge" and knowledge_count < limit // 3:
                    balanced_results.append(result)
                    knowledge_count += 1
                elif result_type == "entity" and entity_count < limit // 6:
                    balanced_results.append(result)
                    entity_count += 1
                elif len(balanced_results) < limit:
                    balanced_results.append(result)
                
                if len(balanced_results) >= limit:
                    break
            
            return balanced_results
            
        except Exception as e:
            self.logger.error(f"Failed to merge RCA results: {e}")
            return logs + knowledge + entities
    
    async def search_incident_timeline(
        self,
        incident_id: str,
        time_window_hours: int = 2
    ) -> Dict[str, Any]:
        """搜索incident时间线相关的所有数据"""
        try:
            from datetime import timedelta
            
            # 计算时间窗口
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=time_window_hours)
            
            # 搜索该时间窗口内的所有日志
            logs_results = await self.rag_service.fulltext_search(
                query=incident_id,
                timestamp_range=(start_time, end_time),
                source_type="logs",
                limit=50
            )
            
            # 按时间排序
            timeline_logs = sorted(
                logs_results,
                key=lambda x: x.get("timestamp", ""),
                reverse=False  # 按时间正序
            )
            
            # 分析日志模式
            patterns = self._analyze_log_patterns(timeline_logs)
            
            return {
                "incident_id": incident_id,
                "time_window": f"{start_time.isoformat()} to {end_time.isoformat()}",
                "timeline_logs": timeline_logs,
                "log_patterns": patterns,
                "total_logs": len(timeline_logs)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to search incident timeline: {e}")
            return {"incident_id": incident_id, "timeline_logs": [], "error": str(e)}
    
    def _analyze_log_patterns(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析日志模式"""
        try:
            patterns = {
                "error_progression": [],
                "service_impact": {},
                "peak_times": [],
                "critical_events": []
            }
            
            # 分析错误进展
            error_logs = [log for log in logs if log.get("log_level") == "ERROR"]
            if error_logs:
                patterns["error_progression"] = [
                    {
                        "timestamp": log.get("timestamp"),
                        "service": log.get("service_name"),
                        "message": log.get("content", "")[:100]
                    }
                    for log in error_logs[:10]
                ]
            
            # 分析服务影响
            service_counts = {}
            for log in logs:
                service = log.get("service_name", "unknown")
                level = log.get("log_level", "INFO")
                if service not in service_counts:
                    service_counts[service] = {"total": 0, "errors": 0, "warnings": 0}
                
                service_counts[service]["total"] += 1
                if level == "ERROR":
                    service_counts[service]["errors"] += 1
                elif level == "WARN":
                    service_counts[service]["warnings"] += 1
            
            patterns["service_impact"] = service_counts
            
            # 识别关键事件
            critical_keywords = ["crash", "fail", "timeout", "exception", "down"]
            for log in logs:
                content_lower = log.get("content", "").lower()
                if any(keyword in content_lower for keyword in critical_keywords):
                    patterns["critical_events"].append({
                        "timestamp": log.get("timestamp"),
                        "service": log.get("service_name"),
                        "event": log.get("content", "")[:150]
                    })
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Failed to analyze log patterns: {e}")
            return {}
    
    async def get_rca_context(self, query: str) -> Dict[str, Any]:
        """获取完整的RCA上下文信息"""
        try:
            # 执行综合搜索
            search_results = await self.search_for_rca(
                query=query,
                search_type="hybrid",
                limit=20
            )
            
            # 构建RCA上下文
            context = {
                "query": query,
                "search_timestamp": datetime.utcnow().isoformat(),
                "evidence": {
                    "logs": search_results["logs"][:10],
                    "knowledge": search_results["knowledge"][:5],
                    "entities": search_results["entities"][:5]
                },
                "patterns": {},
                "recommendations": []
            }
            
            # 分析模式
            if search_results["logs"]:
                context["patterns"] = self._analyze_log_patterns(search_results["logs"])
            
            # 生成初步建议
            context["recommendations"] = self._generate_initial_recommendations(
                search_results, query
            )
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to get RCA context: {e}")
            return {"query": query, "error": str(e)}
    
    def _generate_initial_recommendations(
        self,
        search_results: Dict[str, Any],
        query: str
    ) -> List[Dict[str, Any]]:
        """基于搜索结果生成初步建议"""
        try:
            recommendations = []
            
            # 基于错误日志的建议
            error_logs = [log for log in search_results["logs"] if log.get("log_level") == "ERROR"]
            if error_logs:
                recommendations.append({
                    "type": "immediate",
                    "action": "检查错误日志",
                    "details": f"发现 {len(error_logs)} 条ERROR日志，建议优先分析",
                    "priority": "high"
                })
            
            # 基于知识文档的建议
            if search_results["knowledge"]:
                recommendations.append({
                    "type": "knowledge",
                    "action": "参考相关文档",
                    "details": f"找到 {len(search_results['knowledge'])} 个相关知识文档",
                    "priority": "medium"
                })
            
            # 基于实体关系的建议
            if search_results["entities"]:
                recommendations.append({
                    "type": "investigation",
                    "action": "检查相关组件",
                    "details": f"发现 {len(search_results['entities'])} 个相关组件或服务",
                    "priority": "medium"
                })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Failed to generate initial recommendations: {e}")
            return []
    
    async def close(self):
        """关闭搜索服务"""
        try:
            self.rag_service.close()
            self.embedding_service.close()
            await self.graph_service.close()
            self.logger.info("RAG search service closed")
        except Exception as e:
            self.logger.error(f"Failed to close RAG search service: {e}")


# 为现有Agent系统提供适配器
class AgentRAGAdapter:
    """Agent RAG适配器 - 兼容现有Agent接口"""
    
    def __init__(self):
        self.rag_search = RAGSearchService()
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
        """兼容现有search_service接口的混合搜索"""
        try:
            # 转换为RCA搜索上下文
            context = {
                "user_message": query,
                "source_filter": source,
                "category_filter": category
            }
            
            # 执行RCA搜索
            rca_results = await self.rag_search.search_for_rca(
                query=query,
                context=context,
                search_type=search_type,
                limit=limit
            )
            
            # 转换为兼容格式
            if search_type == "hybrid":
                results = rca_results["merged_results"]
            elif search_type == "vector":
                results = rca_results["logs"] + rca_results["knowledge"]
            else:
                results = rca_results["knowledge"]
            
            return {
                "results": results,
                "total": len(results),
                "query": query,
                "search_type": search_type,
                "processing_time": rca_results["search_metadata"].get("processing_time", 0.0),
                "metadata": rca_results["search_metadata"]
            }
            
        except Exception as e:
            self.logger.error(f"Agent RAG adapter search failed: {e}")
            return {
                "results": [],
                "total": 0,
                "query": query,
                "search_type": search_type,
                "error": str(e)
            }