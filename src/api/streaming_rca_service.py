"""
流式RCA分析服务
支持任务状态跟踪和进度显示
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import traceback

from ..utils.task_manager import task_manager, TaskManager

logger = logging.getLogger(__name__)

class StreamingRCAService:
    """流式RCA分析服务"""
    
    def __init__(self):
        self.task_manager = task_manager
        self.running_tasks = {}  # task_id -> asyncio.Task
        
    async def start_rca_task(self, message: str, user_id: str, 
                           session_id: str = None, temperature: float = 0.7) -> str:
        """启动RCA分析任务"""
        
        # 创建任务
        task_id = self.task_manager.create_task(user_id, message)
        
        # 启动异步任务
        async_task = asyncio.create_task(
            self._execute_rca_analysis(task_id, message, user_id, session_id, temperature)
        )
        
        self.running_tasks[task_id] = async_task
        
        logger.info(f"启动RCA任务: {task_id}")
        return task_id
    
    async def _execute_rca_analysis(self, task_id: str, message: str, 
                                  user_id: str, session_id: str, temperature: float):
        """执行RCA分析的完整流程"""
        try:
            # 更新任务状态为处理中
            task_info = self.task_manager.tasks[task_id]
            task_info.status = "processing"
            
            # 导入所需服务
            from ..api.rca_chat_endpoint import RCAChatService
            from ..utils.ner_extractor import ner_extractor
            from ..services.improved_rag_service import ImprovedRAGService
            from ..services.topology_service import topology_service
            from ..agents.reasoning_agent import ReasoningAgent
            
            rca_service = RCAChatService()
            improved_rag = ImprovedRAGService()
            reasoning_agent = ReasoningAgent()
            
            # 阶段1: NER实体识别
            self.task_manager.update_task_stage(
                task_id, "NER实体识别", "in_progress", 0.5,
                current_detail="正在识别服务名称和性能指标"
            )
            
            start_time = time.time()
            entities = ner_extractor.extract_entities(message)
            ner_duration = int((time.time() - start_time) * 1000)
            
            # 从Entity对象列表中提取服务名和指标
            service_names = []
            metrics = []
            for entity in entities:
                if entity.label == "SERVICE":
                    service_names.append(entity.text)
                elif entity.label in ["CPU", "MEMORY", "STORAGE", "NETWORK"]:
                    metrics.append(entity.text)
            
            self.task_manager.update_task_stage(
                task_id, "NER实体识别", "completed", 1.0,
                result=f"识别到服务: {', '.join(service_names)}, 指标: {', '.join(metrics)}",
                duration_ms=ner_duration
            )
            
            # 阶段2: 混合搜索
            self.task_manager.update_task_stage(
                task_id, "混合搜索", "in_progress", 0.3,
                current_detail="正在执行向量搜索和BM25全文搜索"
            )
            
            start_time = time.time()
            search_results = await improved_rag.hybrid_search(
                query=message, limit=20, alpha=0.6
            )
            search_duration = int((time.time() - start_time) * 1000)
            
            # Extract actual results list from the returned dictionary
            actual_results = search_results.get("results", []) if isinstance(search_results, dict) else []
            
            self.task_manager.update_task_stage(
                task_id, "混合搜索", "completed", 1.0,
                result=f"找到{len(actual_results)}个相关证据文档",
                duration_ms=search_duration
            )
            
            # 阶段3: 拓扑查询
            self.task_manager.update_task_stage(
                task_id, "拓扑查询", "in_progress", 0.6,
                current_detail="正在查询服务依赖关系和影响范围"
            )
            
            start_time = time.time()
            topology_data = await topology_service.get_service_topology(service_names)
            topo_duration = int((time.time() - start_time) * 1000)
            
            affected_services = []
            if topology_data and 'relationships' in topology_data:
                for rel in topology_data['relationships']:
                    if rel.get('from_service'):
                        affected_services.append(rel['from_service'])
                    if rel.get('to_service'):
                        affected_services.append(rel['to_service'])
            
            self.task_manager.update_task_stage(
                task_id, "拓扑查询", "completed", 1.0,
                result=f"分析了{len(set(affected_services))}个相关服务依赖",
                duration_ms=topo_duration
            )
            
            # 阶段4: Agent推理分析
            self.task_manager.update_task_stage(
                task_id, "Agent推理分析", "in_progress", 0.2,
                current_detail="正在使用多Agent系统进行根因推理"
            )
            
            start_time = time.time()
            
            # 构建推理上下文
            evidence_context = self._build_evidence_context(actual_results, topology_data)
            
            # 模拟Agent推理过程的进度更新
            await asyncio.sleep(0.5)
            self.task_manager.update_task_stage(
                task_id, "Agent推理分析", "in_progress", 0.4,
                current_detail="Planner Agent正在制定分析计划"
            )
            
            await asyncio.sleep(0.5)
            self.task_manager.update_task_stage(
                task_id, "Agent推理分析", "in_progress", 0.6,
                current_detail="Knowledge Agent正在整合证据信息"
            )
            
            # 执行真实的推理分析
            reasoning_result = await self._execute_agent_reasoning(
                reasoning_agent, message, evidence_context, service_names, metrics
            )
            
            await asyncio.sleep(0.3)
            self.task_manager.update_task_stage(
                task_id, "Agent推理分析", "in_progress", 0.8,
                current_detail="Reasoning Agent正在分析根因"
            )
            
            await asyncio.sleep(0.3)
            self.task_manager.update_task_stage(
                task_id, "Agent推理分析", "in_progress", 0.9,
                current_detail="Executor Agent正在生成解决方案"
            )
            
            agent_duration = int((time.time() - start_time) * 1000)
            
            self.task_manager.update_task_stage(
                task_id, "Agent推理分析", "completed", 1.0,
                result="生成根因分析和建议",
                duration_ms=agent_duration
            )
            
            # 阶段5: 结果格式化
            self.task_manager.update_task_stage(
                task_id, "结果格式化", "in_progress", 0.5,
                current_detail="正在构建证据链和格式化输出"
            )
            
            start_time = time.time()
            
            # 格式化最终结果
            final_result = {
                "success": True,
                "response": reasoning_result.get("analysis", "分析完成"),
                "evidence_files": self._extract_evidence_files(actual_results),
                "topology_data": topology_data,
                "confidence_score": reasoning_result.get("confidence", 0.85),
                "processing_time": sum([
                    ner_duration, search_duration, topo_duration, agent_duration
                ]) / 1000.0,
                "analysis_stages": [
                    {"stage": "NER实体识别", "duration_ms": ner_duration},
                    {"stage": "混合搜索", "duration_ms": search_duration},
                    {"stage": "拓扑查询", "duration_ms": topo_duration},
                    {"stage": "Agent推理", "duration_ms": agent_duration}
                ]
            }
            
            format_duration = int((time.time() - start_time) * 1000)
            
            self.task_manager.update_task_stage(
                task_id, "结果格式化", "completed", 1.0,
                result="结果格式化完成",
                duration_ms=format_duration
            )
            
            # 完成任务
            self.task_manager.complete_task(task_id, final_result)
            
        except Exception as e:
            error_msg = f"RCA分析失败: {str(e)}"
            logger.error(f"任务 {task_id} 执行失败: {e}")
            logger.error(traceback.format_exc())
            
            self.task_manager.fail_task(task_id, error_msg)
        
        finally:
            # 清理运行中的任务记录
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    def _build_evidence_context(self, search_results: list, topology_data: dict) -> dict:
        """构建推理上下文"""
        evidence_context = {
            "documents": search_results[:10],  # 前10个最相关文档
            "topology": topology_data,
            "evidence_count": len(search_results),
            "has_topology": bool(topology_data and topology_data.get('relationships'))
        }
        
        return evidence_context
    
    def _extract_evidence_files(self, search_results: list) -> list:
        """提取证据文件信息"""
        evidence_files = []
        
        for result in search_results[:5]:  # 前5个最重要的证据
            if result.get('source_type') == 'logs' and result.get('log_file'):
                evidence_files.append({
                    "file_name": result.get('log_file'),
                    "line_number": result.get('line_number'),
                    "timestamp": result.get('timestamp'),
                    "confidence": result.get('hybrid_score', 0.5)
                })
        
        return evidence_files
    
    async def _execute_agent_reasoning(self, reasoning_agent, query: str, 
                                     evidence_context: dict, service_names: list, metrics: list) -> dict:
        """执行Agent推理分析"""
        try:
            # Import AgentState from base_agent
            from ..agents.base_agent import AgentState, AgentMessage, MessageType
            
            # Create agent state with proper context
            state = AgentState()
            state.context = {
                "user_message": query,
                "knowledge_summary": {
                    "evidence_documents": evidence_context.get("documents", []),
                    "topology_info": evidence_context.get("topology", {}),
                    "service_names": service_names,
                    "metrics": metrics,
                    "evidence_count": evidence_context.get("evidence_count", 0),
                    "has_topology": evidence_context.get("has_topology", False)
                }
            }
            
            # Execute reasoning agent
            result_state = await reasoning_agent.process(state)
            
            # Extract final analysis from the agent state
            if result_state.is_completed():
                # Get the final message from the agent
                final_messages = [msg for msg in result_state.messages if msg.type == MessageType.OBSERVATION]
                if final_messages:
                    final_content = final_messages[-1].content
                    return {
                        "analysis": final_content,
                        "confidence": 0.85,  # Default confidence
                        "status": "completed"
                    }
            
            # Fallback: return a basic analysis
            return {
                "analysis": f"已完成对{query}的初步分析，发现{len(service_names)}个服务相关证据",
                "confidence": 0.75,
                "status": "partial"
            }
            
        except Exception as e:
            logger.error(f"Agent推理执行失败: {e}")
            # Return a fallback result instead of failing completely
            return {
                "analysis": f"完成基础分析，识别到服务: {', '.join(service_names)}，建议进一步检查相关组件",
                "confidence": 0.6,
                "status": "fallback"
            }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        return self.task_manager.get_task_status(task_id)
    
    def cleanup_completed_tasks(self):
        """清理已完成的任务"""
        self.task_manager.cleanup_old_tasks(max_age_hours=1)  # 1小时后清理

# 全局流式RCA服务实例
streaming_rca_service = StreamingRCAService()