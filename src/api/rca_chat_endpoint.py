"""
RCA集成聊天端点
将RAG搜索和Agent推理集成到Web API中
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class RCAChatService:
    """RCA聊天服务"""
    
    def __init__(self):
        self.rag_service = None
        self.reasoning_agent = None
        self._initialize_services()
    
    def _initialize_services(self):
        """初始化RAG和Agent服务"""
        try:
            # 动态导入避免启动时的依赖问题
            from ..services.improved_rag_service import ImprovedRAGService
            from ..agents.reasoning_agent import ReasoningAgent
            
            self.rag_service = ImprovedRAGService()
            self.reasoning_agent = ReasoningAgent()
            logger.info("RCA聊天服务初始化成功")
            
        except Exception as e:
            logger.error(f"RCA服务初始化失败: {e}")
            logger.error(traceback.format_exc())
    
    async def process_rca_query(self, query: str, session_id: str = "default") -> Dict[str, Any]:
        """处理RCA查询请求"""
        start_time = datetime.now()
        
        try:
            # 导入日志和NER工具
            from ..utils.rca_logger import rca_logger
            from ..utils.ner_extractor import ner_extractor
            from ..services.topology_service import topology_service
            
            # 记录查询开始
            rca_logger.log_query_start(query, session_id)
            logger.info(f"开始处理RCA查询: {query[:100]}...")
            
            # 1. 判断是否为RCA相关查询
            if not self._is_rca_query(query):
                return await self._handle_general_query(query)
            
            # 2. NER实体识别
            logger.info("执行NER实体识别...")
            entities = ner_extractor.extract_entities(query)
            service_names = ner_extractor.get_services(entities)
            components = ner_extractor.get_components(entities)
            rca_logger.log_ner_extraction(query, [{"text": e.text, "label": e.label, "confidence": e.confidence} for e in entities])
            
            # 3. RAG搜索获取相关证据
            logger.info("执行RAG混合搜索...")
            evidence_data = await self._search_evidence(query)
            if evidence_data:
                rca_logger.log_hybrid_search(query, evidence_data)
            
            # 4. Neo4j拓扑查询（如果识别到服务名）
            graph_evidence = []
            if service_names:
                logger.info(f"查询服务拓扑: {service_names}")
                topology_data = await topology_service.get_service_topology(service_names)
                graph_evidence = topology_data.get("relationships", [])
                rca_logger.log_neo4j_query(service_names, graph_evidence)
                
                # 将拓扑信息添加到证据中
                if evidence_data:
                    evidence_data["graph_evidence"] = graph_evidence
                    evidence_data["topology_services"] = topology_data.get("services", [])
            
            if not evidence_data or evidence_data.get("total_evidence", 0) == 0:
                return {
                    "response": "抱歉，我没有找到与您问题相关的具体信息。请提供更多详细描述，或检查数据是否已正确索引。",
                    "analysis_type": "insufficient_data",
                    "evidence_count": 0,
                    "timestamp": datetime.now(),
                    "session_id": session_id,
                    "processing_time": (datetime.now() - start_time).total_seconds()
                }
            
            # 5. Agent推理分析
            logger.info("执行Agent推理分析...")
            rca_result = await self._perform_rca_analysis(query, evidence_data, entities)
            
            # 6. 格式化响应
            formatted_response = self._format_rca_response(rca_result, evidence_data)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 记录最终结果
            if rca_result:
                rca_logger.log_final_result(
                    rca_result.get("primary_root_cause", "未知"),
                    rca_result.get("confidence", 0.0),
                    processing_time
                )
            
            logger.info(f"RCA查询处理完成，耗时: {processing_time:.2f}秒")
            
            return {
                "response": formatted_response,
                "analysis_type": "rca_analysis",
                "evidence_count": evidence_data.get("total_evidence", 0),
                "confidence": rca_result.get("confidence", 0.0) if rca_result else 0.0,
                "timestamp": datetime.now(),
                "session_id": session_id,
                "processing_time": processing_time,
                "raw_analysis": rca_result  # 为调试提供原始数据
            }
            
        except Exception as e:
            logger.error(f"RCA查询处理失败: {e}")
            logger.error(traceback.format_exc())
            
            return {
                "response": f"处理您的查询时出现了错误: {str(e)}。请稍后重试或联系管理员。",
                "analysis_type": "error",
                "error": str(e),
                "timestamp": datetime.now(),
                "session_id": session_id,
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
    
    def _is_rca_query(self, query: str) -> bool:
        """判断是否为RCA相关查询"""
        rca_keywords = [
            # 中文关键词
            "故障", "问题", "错误", "异常", "超时", "慢", "卡顿", "宕机", 
            "CPU", "内存", "磁盘", "网络", "数据库", "服务", "分析", "原因",
            "排查", "诊断", "修复", "解决", "incident", "root cause",
            # 英文关键词  
            "error", "failure", "timeout", "slow", "crash", "down",
            "performance", "issue", "problem", "troubleshoot", "debug",
            "analyze", "diagnosis", "fix", "solve", "service-", "database"
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in rca_keywords)
    
    async def _handle_general_query(self, query: str) -> Dict[str, Any]:
        """处理一般性查询"""
        try:
            # 对于非RCA查询，使用hybrid搜索获取相关知识
            if not self.rag_service:
                from ..services.improved_rag_service import ImprovedRAGService
                self.rag_service = ImprovedRAGService()
            
            search_result = await self.rag_service.hybrid_search(query, limit=3)
            knowledge_results = search_result.get("results", [])
            
            if knowledge_results and len(knowledge_results) > 0:
                response = "基于知识库，我找到了以下相关信息：\n\n"
                for i, result in enumerate(knowledge_results[:3], 1):
                    content = result.get("content", "")[:200]
                    source = result.get("source_type", "unknown")
                    response += f"{i}. [{source}] {content}...\n\n"
                
                response += "如果您需要更具体的故障诊断分析，请提供具体的错误信息或症状描述。"
            else:
                response = "我理解您的问题，但没有找到相关的具体信息。如果这是关于系统故障或性能问题，请提供更详细的症状描述，我可以为您进行根本原因分析。"
            
            return {
                "response": response,
                "analysis_type": "general_knowledge", 
                "evidence_count": len(knowledge_results) if knowledge_results else 0
            }
            
        except Exception as e:
            logger.error(f"处理一般查询失败: {e}")
            return {
                "response": "我会尽力帮助您。如果遇到技术问题，请提供具体的错误信息，我可以进行详细分析。",
                "analysis_type": "fallback",
                "evidence_count": 0
            }
    
    async def _search_evidence(self, query: str) -> Optional[Dict[str, Any]]:
        """搜索相关证据"""
        try:
            if not self.rag_service:
                logger.error("RAG服务未初始化")
                return None
            
            # 使用改进的RAG服务进行hybrid搜索
            search_result = await self.rag_service.hybrid_search(query, limit=15)
            
            # 转换为RCA分析需要的格式
            evidence = {
                "log_evidence": search_result.get("results", []),
                "total_evidence": search_result.get("total_results", 0),
                "search_type": search_result.get("search_type", "hybrid"),
                "vector_results": search_result.get("vector_results", 0),
                "bm25_results": search_result.get("bm25_results", 0)
            }
            
            logger.info(f"RAG混合搜索完成，找到证据: {evidence.get('total_evidence', 0)} 条 (向量:{evidence.get('vector_results', 0)}, BM25:{evidence.get('bm25_results', 0)})")
            return evidence
            
        except Exception as e:
            logger.error(f"证据搜索失败: {e}")
            return None
    
    async def _perform_rca_analysis(self, query: str, evidence_data: Dict[str, Any], entities: List = None) -> Optional[Dict[str, Any]]:
        """执行RCA分析"""
        try:
            # 模拟推理过程，实际中应该调用ReasoningAgent
            return await self._simulate_rca_reasoning(evidence_data, query, entities)
            
        except Exception as e:
            logger.error(f"RCA分析失败: {e}")
            return None
    
    async def _simulate_rca_reasoning(self, evidence_data: Dict[str, Any], incident_description: str, entities: List = None) -> Optional[Dict[str, Any]]:
        """模拟RCA推理过程"""
        try:
            from ..utils.rca_logger import rca_logger
            
            # 0. 检查数据匹配性（基于10个story的真实数据）
            self._check_data_consistency(incident_description, evidence_data)
            
            # 1. 症状分析
            symptoms = []
            incident_lower = incident_description.lower()
            
            symptom_patterns = {
                "cpu": {"type": "performance", "symptom": "CPU使用率过高", "severity": "high"},
                "memory": {"type": "performance", "symptom": "内存使用异常", "severity": "high"},
                "内存": {"type": "performance", "symptom": "内存问题", "severity": "high"},
                "timeout": {"type": "performance", "symptom": "响应超时", "severity": "high"},
                "slow": {"type": "performance", "symptom": "响应缓慢", "severity": "medium"},
                "error": {"type": "functional", "symptom": "功能错误", "severity": "medium"},
                "connection": {"type": "connectivity", "symptom": "连接问题", "severity": "high"},
                "disk": {"type": "performance", "symptom": "磁盘IO问题", "severity": "medium"}
            }
            
            for keyword, symptom_info in symptom_patterns.items():
                if keyword in incident_lower:
                    symptoms.append(symptom_info)
            
            # 2. 根因推理
            potential_causes = []
            
            # 基于日志证据推理
            log_evidence = evidence_data.get("log_evidence", [])
            
            for log in log_evidence:  # 分析所有日志证据
                content = log.get("content", "")
                content_lower = content.lower()
                
                # 使用hybrid_score而不是certainty
                score = log.get("hybrid_score", log.get("_additional", {}).get("certainty", 0.5))
                service = log.get("service_name", "unknown")
                
                # 过滤掉非服务相关的数据
                if service in ["unknown", "documentation", None] or not service or service.strip() == "":
                    # 如果是文档或unknown数据，跳过服务特定的推理，但记录为一般证据
                    logger.info(f"跳过非服务数据: {content[:60]}... (来源: {service})")
                    continue
                
                # 更详细的证据分析
                logger.info(f"分析证据: {content[:100]}... (服务: {service}, 得分: {score:.3f})")
                
                # 根据实际日志内容进行推理 - 分析任何可能的问题
                if any(word in content_lower for word in ["critical", "error", "failure", "异常", "错误"]):
                    potential_causes.append({
                        "cause": f"{service}服务出现故障: {content[:50]}...",
                        "confidence": score,
                        "evidence_type": "log",
                        "source": service
                    })
                
                elif "cpu" in content_lower and ("high" in content_lower or "critical" in content_lower or "过高" in content_lower):
                    potential_causes.append({
                        "cause": f"{service}服务CPU资源不足",
                        "confidence": score,
                        "evidence_type": "log",
                        "source": service
                    })
                elif "memory" in content_lower or "内存" in content_lower:
                    # 检查内存使用情况
                    if "usage" in content_lower or "使用" in content_lower or any(x in content for x in ["MB", "GB", "%"]):
                        # 提取内存使用情况
                        memory_info = content
                        potential_causes.append({
                            "cause": f"{service}服务内存使用情况: {memory_info}",
                            "confidence": score,
                            "evidence_type": "log", 
                            "source": service
                        })
                    else:
                        potential_causes.append({
                            "cause": f"{service}服务内存相关问题",
                            "confidence": score,
                            "evidence_type": "log", 
                            "source": service
                        })
                elif "timeout" in content_lower or "connection" in content_lower:
                    potential_causes.append({
                        "cause": f"{service}服务连接超时",
                        "confidence": score,
                        "evidence_type": "log",
                        "source": service
                    })
                elif "disk" in content_lower or "io" in content_lower:
                    potential_causes.append({
                        "cause": f"{service}服务磁盘IO问题",
                        "confidence": score,
                        "evidence_type": "log",
                        "source": service
                    })
                # 如果没有明确问题，但日志得分较高，也记录为潜在问题
                elif score > 0.7:
                    potential_causes.append({
                        "cause": f"{service}服务可能存在问题: {content[:50]}...",
                        "confidence": score * 0.8,  # 降低置信度
                        "evidence_type": "log",
                        "source": service
                    })
            
            # 基于图谱证据推理
            graph_evidence = evidence_data.get("graph_evidence", [])
            for rel in graph_evidence[:3]:
                service_name = rel.get('service')
                related_name = rel.get('related')
                relation_type = rel.get('relation')
                
                # 验证服务名有效性
                if not service_name or not related_name or service_name in ["unknown", None] or related_name in ["unknown", None]:
                    logger.info(f"跳过无效拓扑关系: {service_name} --[{relation_type}]--> {related_name}")
                    continue
                
                if relation_type == 'DEPENDS_ON':
                    potential_causes.append({
                        "cause": f"{service_name}依赖的{related_name}服务问题",
                        "confidence": 0.7,
                        "evidence_type": "dependency",
                        "source": service_name
                    })
                elif relation_type == 'DEPLOYED_ON':
                    potential_causes.append({
                        "cause": f"{related_name}主机资源问题",
                        "confidence": 0.6,
                        "evidence_type": "deployment",
                        "source": service_name
                    })
            
            # 如果没有找到具体原因，基于症状推理
            if not potential_causes and symptoms:
                for symptom in symptoms:
                    if symptom["type"] == "performance":
                        potential_causes.append({
                            "cause": "系统性能瓶颈",
                            "confidence": 0.6,
                            "evidence_type": "symptom",
                            "source": "system"
                        })
                    elif symptom["type"] == "connectivity":
                        potential_causes.append({
                            "cause": "网络连接问题",
                            "confidence": 0.6,
                            "evidence_type": "symptom",
                            "source": "network"
                        })
            
            # 过滤掉包含None或unknown的根因
            valid_causes = []
            for cause in potential_causes:
                cause_text = cause.get("cause", "")
                source = cause.get("source", "")
                
                # 过滤无效根因
                if ("None" in cause_text or "unknown" in cause_text or 
                    source in ["None", "unknown", None] or not cause_text.strip()):
                    logger.info(f"过滤无效根因: {cause_text} (来源: {source})")
                    continue
                    
                valid_causes.append(cause)
            
            potential_causes = valid_causes
            
            # 根据置信度排序
            potential_causes.sort(key=lambda x: x["confidence"], reverse=True)
            
            # 记录推理过程（在分析完成后）
            evidence_count = evidence_data.get("total_evidence", 0)
            rca_logger.log_reasoning_process(evidence_count, symptoms, potential_causes)
            
            # 3. 解决方案建议
            solutions = []
            
            for cause in potential_causes[:2]:  # 取前2个最可能的根因
                cause_text = cause["cause"]
                if "CPU" in cause_text:
                    solutions.append({
                        "solution": "扩容CPU资源或优化CPU密集型操作",
                        "priority": "high",
                        "estimated_time": "30分钟",
                        "steps": ["检查CPU使用率", "识别高CPU进程", "扩容或优化"]
                    })
                elif "内存" in cause_text or "memory" in cause_text.lower():
                    if "使用情况" in cause_text or "usage" in cause_text.lower():
                        solutions.append({
                            "solution": "监控内存使用趋势，根据需要调整内存分配",
                            "priority": "medium", 
                            "estimated_time": "20分钟",
                            "steps": ["分析当前内存使用", "检查内存使用趋势", "调整内存配置或优化应用"]
                        })
                    else:
                        solutions.append({
                            "solution": "检查内存泄露，重启相关服务",
                            "priority": "high", 
                            "estimated_time": "15分钟",
                            "steps": ["检查内存使用", "查找内存泄露", "重启服务"]
                        })
                elif "依赖" in cause_text:
                    solutions.append({
                        "solution": "检查依赖服务状态，修复服务间通信",
                        "priority": "medium",
                        "estimated_time": "45分钟",
                        "steps": ["检查依赖服务", "测试连通性", "修复通信问题"]
                    })
                elif "主机" in cause_text:
                    solutions.append({
                        "solution": "检查主机资源使用情况，考虑迁移服务",
                        "priority": "medium",
                        "estimated_time": "60分钟",
                        "steps": ["检查主机资源", "评估迁移方案", "执行服务迁移"]
                    })
                elif "连接" in cause_text:
                    solutions.append({
                        "solution": "检查网络连接和防火墙配置",
                        "priority": "high",
                        "estimated_time": "20分钟",
                        "steps": ["检查网络连通性", "验证防火墙规则", "测试端口访问"]
                    })
            
            # 4. 最终RCA结论
            if potential_causes:
                primary_cause = potential_causes[0]
                
                rca_conclusion = {
                    "incident_description": incident_description,
                    "primary_root_cause": primary_cause["cause"],
                    "confidence": primary_cause["confidence"],
                    "symptoms": symptoms,
                    "evidence_summary": {
                        "log_evidence_count": len(log_evidence),
                        "graph_evidence_count": len(graph_evidence),
                        "total_evidence": evidence_data.get("total_evidence", 0)
                    },
                    "alternative_causes": [c["cause"] for c in potential_causes[1:3]],
                    "recommended_solutions": solutions,
                    "analysis_timestamp": datetime.now().isoformat(),
                    "reasoning_chain": [
                        f"基于{len(log_evidence)}条日志证据",
                        f"结合{len(graph_evidence)}个依赖关系",
                        f"识别{len(symptoms)}个症状特征",
                        f"推理得出{len(potential_causes)}个潜在原因"
                    ]
                }
                
                return rca_conclusion
            else:
                return None
                
        except Exception as e:
            logger.error(f"RCA推理模拟失败: {e}")
            return None
    
    def _format_rca_response(self, rca_result: Dict[str, Any], evidence_data: Dict[str, Any]) -> str:
        """格式化RCA响应"""
        try:
            if not rca_result:
                return "很抱歉，基于当前可用的信息，我无法确定具体的根本原因。建议提供更多详细信息或检查系统日志。"
            
            response = f"## 🔍 根本原因分析报告\n\n"
            
            # 问题描述
            response += f"**问题描述**: {rca_result.get('incident_description', 'N/A')}\n\n"
            
            # 证据汇总
            evidence_summary = rca_result.get('evidence_summary', {})
            response += f"**📊 证据汇总**: 共分析了 {evidence_summary.get('total_evidence', 0)} 条证据\n"
            response += f"- 日志证据: {evidence_summary.get('log_evidence_count', 0)} 条\n"
            response += f"- 依赖关系: {evidence_summary.get('graph_evidence_count', 0)} 个\n\n"
            
            # 服务拓扑关系
            graph_evidence = evidence_data.get("graph_evidence", [])
            if graph_evidence:
                response += f"**🌐 服务拓扑关系**:\n"
                for rel in graph_evidence:
                    from_service = rel.get("from_service", "")
                    to_service = rel.get("to_service", "")  
                    relation = rel.get("relation", "")
                    
                    # 跳过无效关系
                    if not from_service or not to_service or from_service in ["None", None] or to_service in ["None", None]:
                        continue
                    
                    if relation == "DEPENDS_ON":
                        response += f"- 🔗 `{from_service}` 依赖 `{to_service}`\n"
                    elif relation == "CALLS":  
                        response += f"- 📞 `{from_service}` 调用 `{to_service}`\n"
                    elif relation == "ROUTES_TO":
                        response += f"- 🚦 `{from_service}` 路由到 `{to_service}`\n"
                    else:
                        response += f"- 🔗 `{from_service}` --[{relation}]--> `{to_service}`\n"
                response += "\n"
            
            # 详细证据信息
            log_evidence = evidence_data.get("log_evidence", [])
            valid_evidence_count = 0
            if log_evidence:
                response += f"**📋 关键证据详情**:\n"
                for evidence in log_evidence[:8]:  # 检查前8条，显示有效的
                    service_name = evidence.get("service_name", "unknown")
                    
                    # 跳过非服务数据
                    if service_name in ["unknown", "documentation", None]:
                        continue
                        
                    valid_evidence_count += 1
                    if valid_evidence_count > 3:  # 只显示前3条有效证据
                        break
                        
                    content = evidence.get("content", "")[:100]  # 截取前100字符
                    log_file = evidence.get("log_file", "unknown")
                    timestamp = evidence.get("timestamp", "unknown")
                    score = evidence.get("hybrid_score", evidence.get("_additional", {}).get("certainty", 0.5))
                    
                    response += f"\n**证据{valid_evidence_count}**: [得分: {score:.3f}]\n"
                    response += f"- 📁 **日志文件**: `{log_file}`\n"
                    response += f"- 🖥️  **服务**: `{service_name}`\n" 
                    response += f"- ⏰ **时间**: `{timestamp}`\n"
                    response += f"- 📝 **内容**: {content}...\n"
                response += "\n"
            
            # 主要根因
            primary_cause = rca_result.get('primary_root_cause', '未知')
            confidence = rca_result.get('confidence', 0.0)
            response += f"**🎯 主要根本原因**: {primary_cause}\n"
            response += f"**📈 置信度**: {confidence:.1%}\n\n"
            
            # 症状分析
            symptoms = rca_result.get('symptoms', [])
            if symptoms:
                response += f"**🩺 识别症状**:\n"
                for symptom in symptoms:
                    response += f"- {symptom.get('symptom', 'N/A')} ({symptom.get('severity', 'medium')})\n"
                response += "\n"
            
            # 备选原因
            alternative_causes = rca_result.get('alternative_causes', [])
            if alternative_causes:
                response += f"**🔄 其他可能原因**:\n"
                for i, cause in enumerate(alternative_causes[:2], 2):
                    response += f"{i}. {cause}\n"
                response += "\n"
            
            # 解决方案
            solutions = rca_result.get('recommended_solutions', [])
            if solutions:
                response += f"**💡 推荐解决方案**:\n\n"
                for i, solution in enumerate(solutions[:2], 1):
                    response += f"**方案 {i}**: {solution.get('solution', 'N/A')}\n"
                    response += f"- 优先级: {solution.get('priority', 'medium')}\n"
                    response += f"- 预计时间: {solution.get('estimated_time', 'N/A')}\n"
                    
                    steps = solution.get('steps', [])
                    if steps:
                        response += f"- 执行步骤:\n"
                        for step in steps:
                            response += f"  • {step}\n"
                    response += "\n"
            
            # 推理链
            reasoning_chain = rca_result.get('reasoning_chain', [])
            if reasoning_chain:
                response += f"**🧠 分析过程**:\n"
                for step in reasoning_chain:
                    response += f"• {step}\n"
                response += "\n"
            
            # 时间戳
            response += f"*分析时间: {rca_result.get('analysis_timestamp', 'N/A')}*"
            
            return response
            
        except Exception as e:
            logger.error(f"格式化RCA响应失败: {e}")
            return f"分析完成，但格式化输出时出现问题: {str(e)}"
    
    def _check_data_consistency(self, incident_description: str, evidence_data: Dict[str, Any]):
        """检查用户查询与实际数据的一致性"""
        try:
            from ..utils.rca_logger import rca_logger
            
            # 基于10个story的真实数据检查
            incident_lower = incident_description.lower()
            log_evidence = evidence_data.get("log_evidence", [])
            
            # 检查D1相关的内存vs磁盘问题
            if "service-d1" in incident_lower or "service d1" in incident_lower:
                if "内存" in incident_lower or "memory" in incident_lower:
                    # 检查实际日志是否支持内存问题
                    has_memory_evidence = any("memory" in log.get("content", "").lower() for log in log_evidence)
                    has_disk_evidence = any("disk" in log.get("content", "").lower() or "io" in log.get("content", "").lower() for log in log_evidence)
                    
                    if has_disk_evidence and not has_memory_evidence:
                        rca_logger.log_data_mismatch(
                            incident_description,
                            "内存问题",
                            "磁盘IO问题（基于incident_002_d1_disk_io_bottleneck）"
                        )
                        
            # 检查其他服务的数据匹配性
            service_mappings = {
                "service-b": "CPU过载问题（incident_001_service_b_cpu_overload）",
                "service-c": "网络分区问题（incident_010_network_partition）", 
                "service-a": "应用部署问题",
                "service-f": "数据库连接问题"
            }
            
            for service, expected_issue in service_mappings.items():
                if service in incident_lower and service != "service-d1":
                    # 可以在这里添加更多的一致性检查
                    pass
                    
        except Exception as e:
            logger.warning(f"数据一致性检查失败: {e}")


# 全局RCA聊天服务实例
rca_chat_service = RCAChatService()


async def process_rca_chat_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """处理RCA聊天请求的入口函数"""
    query = request.get("message", "")
    session_id = request.get("session_id", "default")
    
    if not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message is required"
        )
    
    return await rca_chat_service.process_rca_query(query, session_id)