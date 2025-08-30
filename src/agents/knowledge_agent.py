"""
知识智能体
负责知识检索和信息查找
"""

from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from .base_agent import BaseAgent, AgentType, AgentState, AgentMessage, MessageType, ToolAgent
from ..services.search_service import SearchService
from ..services.graph_service import GraphService

import logging
logger = logging.getLogger(__name__)


class KnowledgeAgent(ToolAgent):
    """知识智能体"""
    
    def __init__(self, search_service: SearchService = None, graph_service: GraphService = None):
        super().__init__(
            agent_id="knowledge",
            agent_type=AgentType.KNOWLEDGE,
            name="知识智能体",
            description="负责检索相关知识、文档和历史案例",
            max_steps=3
        )
        
        self.search_service = search_service
        self.graph_service = graph_service
        
        # 注册工具
        self._register_tools()
    
    def _register_tools(self):
        """注册知识检索工具"""
        self.register_tool(
            "search_documents",
            self._search_documents,
            "在知识库中搜索相关文档"
        )
        
        self.register_tool(
            "find_similar_cases",
            self._find_similar_cases,
            "查找类似的历史案例"
        )
        
        self.register_tool(
            "get_entity_relationships",
            self._get_entity_relationships,
            "获取实体关系和相关信息"
        )
        
        self.register_tool(
            "extract_key_information",
            self._extract_key_information,
            "从搜索结果中提取关键信息"
        )
    
    async def process(self, state: AgentState) -> AgentState:
        """处理知识检索逻辑"""
        try:
            # 获取查询信息
            user_query = state.context.get("user_message", "")
            search_query = state.context.get("search_query", user_query)
            
            if not search_query:
                raise ValueError("No search query found")
            
            # 步骤1: 搜索相关文档
            if state.current_step == 0:
                thought_msg = AgentMessage(
                    type=MessageType.THOUGHT,
                    content=f"开始搜索相关知识: {search_query}",
                    agent_id=self.agent_id
                )
                state.add_message(thought_msg)
                
                search_result = await self.use_tool("search_documents", search_query)
                
                if search_result["success"]:
                    documents = search_result["result"]
                    state.context["found_documents"] = documents
                    
                    action_msg = AgentMessage(
                        type=MessageType.ACTION,
                        content=f"找到 {len(documents)} 个相关文档",
                        agent_id=self.agent_id
                    )
                    state.add_message(action_msg)
                else:
                    observation_msg = AgentMessage(
                        type=MessageType.OBSERVATION,
                        content="文档搜索失败，将尝试其他检索方式",
                        agent_id=self.agent_id
                    )
                    state.add_message(observation_msg)
                    state.context["found_documents"] = []
            
            # 步骤2: 查找实体关系
            elif state.current_step == 1:
                entity_result = await self.use_tool("get_entity_relationships", search_query)
                
                if entity_result["success"]:
                    entity_info = entity_result["result"]
                    state.context["entity_relationships"] = entity_info
                    
                    if entity_info["entities"]:
                        action_msg = AgentMessage(
                            type=MessageType.ACTION,
                            content=f"发现 {len(entity_info['entities'])} 个相关实体",
                            agent_id=self.agent_id
                        )
                        state.add_message(action_msg)
                    else:
                        observation_msg = AgentMessage(
                            type=MessageType.OBSERVATION,
                            content="未发现相关实体关系",
                            agent_id=self.agent_id
                        )
                        state.add_message(observation_msg)
                else:
                    state.context["entity_relationships"] = {"entities": [], "relationships": []}
            
            # 步骤3: 提取和整理关键信息
            elif state.current_step == 2:
                documents = state.context.get("found_documents", [])
                entity_info = state.context.get("entity_relationships", {})
                
                extract_result = await self.use_tool(
                    "extract_key_information",
                    documents,
                    entity_info,
                    search_query
                )
                
                if extract_result["success"]:
                    key_info = extract_result["result"]
                    state.context["knowledge_summary"] = key_info
                    
                    # 格式化知识摘要
                    summary = self._format_knowledge_summary(key_info, documents, entity_info)
                    
                    answer_msg = AgentMessage(
                        type=MessageType.ANSWER,
                        content=summary,
                        agent_id=self.agent_id,
                        metadata={
                            "documents_found": len(documents),
                            "entities_found": len(entity_info.get("entities", [])),
                            "knowledge_summary": key_info
                        }
                    )
                    state.add_message(answer_msg)
                    
                    state.is_complete = True
                else:
                    return await self.handle_error(state, Exception(extract_result["error"]))
            
            return state
            
        except Exception as e:
            return await self.handle_error(state, e)
    
    async def _search_documents(
        self,
        query: str,
        search_type: str = "hybrid",
        limit: int = 10
    ) -> Dict[str, Any]:
        """搜索文档"""
        try:
            if not self.search_service:
                return {"results": [], "total": 0}
            
            search_result = await self.search_service.hybrid_search(
                query=query,
                search_type=search_type,
                limit=limit
            )
            
            return search_result.get("results", [])
            
        except Exception as e:
            self.logger.error(f"Failed to search documents: {e}")
            raise
    
    async def _find_similar_cases(
        self,
        query: str,
        case_type: str = "troubleshooting"
    ) -> List[Dict[str, Any]]:
        """查找相似案例"""
        try:
            # 构造案例搜索查询
            case_query = f"{case_type} {query} 解决方案"
            
            if not self.search_service:
                return []
            
            search_result = await self.search_service.hybrid_search(
                query=case_query,
                search_type="vector",  # 使用语义搜索查找相似案例
                limit=5
            )
            
            # 过滤出案例类型的文档
            cases = []
            for result in search_result.get("results", []):
                if any(keyword in result.get("title", "").lower() + result.get("content", "").lower() 
                      for keyword in ["案例", "解决", "处理", "方案"]):
                    cases.append(result)
            
            return cases
            
        except Exception as e:
            self.logger.error(f"Failed to find similar cases: {e}")
            return []
    
    async def _get_entity_relationships(self, query: str) -> Dict[str, Any]:
        """获取实体关系"""
        try:
            if not self.graph_service:
                return {"entities": [], "relationships": []}
            
            # 在图数据库中查找相关实体
            entities = await self._find_entities_in_query(query)
            
            relationships = []
            if entities:
                # 获取实体间的关系
                for entity in entities[:3]:  # 限制数量避免过多查询
                    related_entities = await self.graph_service.find_related_entities(
                        entity["name"],
                        entity["type"],
                        max_depth=2
                    )
                    
                    for related in related_entities[:5]:
                        relationships.append({
                            "source": entity,
                            "target": related,
                            "distance": related.get("distance", 1)
                        })
            
            return {
                "entities": entities,
                "relationships": relationships
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get entity relationships: {e}")
            return {"entities": [], "relationships": []}
    
    async def _find_entities_in_query(self, query: str) -> List[Dict[str, Any]]:
        """在查询中查找相关实体"""
        try:
            if not self.graph_service:
                return []
            
            # 简单的实体匹配
            query_words = query.lower().split()
            entities = []
            
            for word in query_words:
                if len(word) < 3:  # 忽略太短的词
                    continue
                
                # 在图数据库中搜索匹配的实体
                cypher_query = """
                MATCH (e:Entity)
                WHERE toLower(e.name) CONTAINS $word
                RETURN e.name as name, e.type as type, id(e) as node_id
                LIMIT 5
                """
                
                results = await self.graph_service.execute_cypher(
                    cypher_query,
                    {"word": word}
                )
                
                for result in results:
                    entities.append({
                        "name": result["name"],
                        "type": result["type"],
                        "node_id": result["node_id"]
                    })
            
            # 去重
            unique_entities = []
            seen_names = set()
            for entity in entities:
                if entity["name"] not in seen_names:
                    unique_entities.append(entity)
                    seen_names.add(entity["name"])
            
            return unique_entities[:10]  # 限制数量
            
        except Exception as e:
            self.logger.error(f"Failed to find entities in query: {e}")
            return []
    
    async def _extract_key_information(
        self,
        documents: List[Dict[str, Any]],
        entity_info: Dict[str, Any],
        query: str
    ) -> Dict[str, Any]:
        """提取关键信息"""
        try:
            key_info = {
                "summary": "",
                "key_points": [],
                "solutions": [],
                "best_practices": [],
                "related_topics": [],
                "confidence_score": 0.0
            }
            
            if not documents and not entity_info.get("entities"):
                key_info["summary"] = "未找到相关信息"
                key_info["confidence_score"] = 0.0
                return key_info
            
            # 分析文档内容
            if documents:
                # 提取关键点
                key_points = set()
                solutions = set()
                best_practices = set()
                
                for doc in documents:
                    content = doc.get("content", "")
                    title = doc.get("title", "")
                    
                    # 简单的关键信息提取
                    if "解决方案" in content or "solution" in content.lower():
                        solutions.add(self._extract_solution_snippet(content))
                    
                    if "最佳实践" in content or "best practice" in content.lower():
                        best_practices.add(self._extract_best_practice_snippet(content))
                    
                    # 提取标题作为关键点
                    if title:
                        key_points.add(title)
                
                key_info["key_points"] = list(key_points)[:5]
                key_info["solutions"] = list(solutions)[:3]
                key_info["best_practices"] = list(best_practices)[:3]
                key_info["confidence_score"] = min(0.8, len(documents) * 0.2)
            
            # 分析实体信息
            if entity_info.get("entities"):
                related_topics = []
                for entity in entity_info["entities"][:5]:
                    related_topics.append(f"{entity['name']} ({entity['type']})")
                
                key_info["related_topics"] = related_topics
                key_info["confidence_score"] = max(key_info["confidence_score"], 0.6)
            
            # 生成总结
            key_info["summary"] = self._generate_summary(key_info, query)
            
            return key_info
            
        except Exception as e:
            self.logger.error(f"Failed to extract key information: {e}")
            raise
    
    def _extract_solution_snippet(self, content: str, max_length: int = 200) -> str:
        """提取解决方案片段"""
        try:
            content_lower = content.lower()
            
            # 查找解决方案相关的句子
            keywords = ["解决方案", "solution", "解决", "fix", "处理方法"]
            
            for keyword in keywords:
                pos = content_lower.find(keyword)
                if pos != -1:
                    # 提取该位置前后的文本
                    start = max(0, pos - 50)
                    end = min(len(content), pos + max_length)
                    snippet = content[start:end].strip()
                    
                    if len(snippet) > 20:
                        return snippet
            
            return content[:max_length] if len(content) > max_length else content
            
        except Exception:
            return ""
    
    def _extract_best_practice_snippet(self, content: str, max_length: int = 200) -> str:
        """提取最佳实践片段"""
        try:
            content_lower = content.lower()
            
            # 查找最佳实践相关的句子
            keywords = ["最佳实践", "best practice", "建议", "recommendation", "优化"]
            
            for keyword in keywords:
                pos = content_lower.find(keyword)
                if pos != -1:
                    # 提取该位置前后的文本
                    start = max(0, pos - 30)
                    end = min(len(content), pos + max_length)
                    snippet = content[start:end].strip()
                    
                    if len(snippet) > 15:
                        return snippet
            
            return ""
            
        except Exception:
            return ""
    
    def _generate_summary(self, key_info: Dict[str, Any], query: str) -> str:
        """生成知识摘要"""
        try:
            summary_parts = []
            
            if key_info["key_points"]:
                summary_parts.append(f"找到 {len(key_info['key_points'])} 个相关知识点")
            
            if key_info["solutions"]:
                summary_parts.append(f"发现 {len(key_info['solutions'])} 个解决方案")
            
            if key_info["related_topics"]:
                summary_parts.append(f"识别出 {len(key_info['related_topics'])} 个相关主题")
            
            if not summary_parts:
                return "未找到直接相关的知识信息"
            
            return "、".join(summary_parts) + "。"
            
        except Exception:
            return "知识摘要生成失败"
    
    def _format_knowledge_summary(
        self,
        key_info: Dict[str, Any],
        documents: List[Dict[str, Any]],
        entity_info: Dict[str, Any]
    ) -> str:
        """格式化知识摘要"""
        try:
            output = []
            output.append("## 知识检索结果")
            output.append("")
            output.append(f"**摘要**: {key_info['summary']}")
            output.append(f"**置信度**: {key_info['confidence_score']:.2f}")
            output.append("")
            
            # 关键点
            if key_info["key_points"]:
                output.append("### 关键信息")
                for point in key_info["key_points"]:
                    output.append(f"- {point}")
                output.append("")
            
            # 解决方案
            if key_info["solutions"]:
                output.append("### 解决方案")
                for i, solution in enumerate(key_info["solutions"], 1):
                    output.append(f"{i}. {solution}")
                output.append("")
            
            # 最佳实践
            if key_info["best_practices"]:
                output.append("### 最佳实践")
                for practice in key_info["best_practices"]:
                    output.append(f"- {practice}")
                output.append("")
            
            # 相关主题
            if key_info["related_topics"]:
                output.append("### 相关主题")
                for topic in key_info["related_topics"]:
                    output.append(f"- {topic}")
                output.append("")
            
            # 参考文档
            if documents:
                output.append("### 参考文档")
                for doc in documents[:3]:
                    score = doc.get("score", 0.0)
                    output.append(f"- **{doc.get('title', 'Untitled')}** (相关度: {score:.2f})")
                    output.append(f"  来源: {doc.get('source', 'Unknown')}")
                output.append("")
            
            return "\n".join(output)
            
        except Exception as e:
            self.logger.error(f"Failed to format knowledge summary: {e}")
            return "知识摘要格式化失败"