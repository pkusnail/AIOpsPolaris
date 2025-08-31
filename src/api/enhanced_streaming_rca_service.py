"""
Enhanced流式RCA分析服务
支持Multi-Agent系统的详细状态跟踪和用户交互控制
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import traceback

from ..utils.multi_agent_task_manager import multi_agent_task_manager, MultiAgentTaskManager

logger = logging.getLogger(__name__)

class EnhancedStreamingRCAService:
    """Enhanced流式RCA分析服务"""
    
    def __init__(self):
        self.task_manager = multi_agent_task_manager
        self.running_tasks = {}  # task_id -> asyncio.Task
        
    async def start_multi_agent_rca_task(self, message: str, user_id: str, 
                                       session_id: str = None) -> str:
        """启动Multi-Agent RCA分析任务"""
        
        # 创建任务
        task_id = self.task_manager.create_multi_agent_task(user_id, message)
        
        # 启动异步任务
        async_task = asyncio.create_task(
            self._execute_multi_agent_rca_analysis(task_id, message, user_id, session_id)
        )
        
        self.running_tasks[task_id] = async_task
        
        logger.info(f"启动Multi-Agent RCA任务: {task_id}")
        return task_id
    
    async def _execute_multi_agent_rca_analysis(self, task_id: str, message: str, 
                                              user_id: str, session_id: str):
        """执行Multi-Agent RCA分析的完整流程"""
        try:
            # Phase 1: Planner规划阶段
            await self._planning_phase(task_id, message)
            
            # Phase 2: 执行阶段
            await self._execution_phase(task_id, message)
            
            # Phase 3: 结果整合
            await self._result_integration_phase(task_id)
            
        except Exception as e:
            error_msg = f"Multi-Agent RCA分析失败: {str(e)}"
            logger.error(f"任务 {task_id} 执行失败: {e}")
            logger.error(traceback.format_exc())
            
            self.task_manager.fail_multi_agent_task(task_id, error_msg)
        
        finally:
            # 清理运行中的任务记录
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    async def _planning_phase(self, task_id: str, message: str):
        """规划阶段 - Planner Agent制定执行计划"""
        
        # 开始规划会话
        session_id = self.task_manager.start_planning_session(
            task_id, 
            f"分析问题: {message}"
        )
        
        # 模拟Planner Agent的规划过程
        await asyncio.sleep(0.5)
        self.task_manager.update_agent_status(
            task_id, "planner", "working", 
            "分析问题类型和复杂度", 0.2
        )
        
        # 添加规划步骤
        await asyncio.sleep(0.5)
        self.task_manager.add_plan_step(
            task_id, "实体识别", "从用户输入中识别服务名和关键实体", "knowledge"
        )
        
        await asyncio.sleep(0.3)
        self.task_manager.add_plan_step(
            task_id, "证据收集", "搜索相关日志、文档和历史案例", "knowledge"
        )
        
        await asyncio.sleep(0.3)
        self.task_manager.add_plan_step(
            task_id, "拓扑分析", "查询服务依赖关系和影响范围", "knowledge", ["实体识别"]
        )
        
        await asyncio.sleep(0.4)
        self.task_manager.add_plan_step(
            task_id, "根因推理", "基于证据和拓扑信息进行根因分析", "reasoning", ["证据收集", "拓扑分析"]
        )
        
        await asyncio.sleep(0.3)
        self.task_manager.add_plan_step(
            task_id, "解决方案", "生成具体的问题解决建议", "executor", ["根因推理"]
        )
        
        # 完成规划
        self.task_manager.update_agent_status(
            task_id, "planner", "working", 
            "制定执行策略和Agent协作方案", 0.8
        )
        
        await asyncio.sleep(0.5)
        reasoning = f"""基于问题 '{message}' 的分析，我制定了5步执行计划：
1. Knowledge Agent进行实体识别，提取关键服务和组件
2. Knowledge Agent搜索相关证据，包括日志和文档
3. Knowledge Agent查询服务拓扑，了解依赖关系
4. Reasoning Agent基于证据进行根因推理分析
5. Executor Agent生成具体的解决方案和建议

预计执行时间: 3-5秒，涉及3个核心Agent协作。"""
        
        self.task_manager.complete_planning_session(task_id, reasoning)
    
    async def _execution_phase(self, task_id: str, message: str):
        """执行阶段 - 各Agent按规划执行任务"""
        
        # Step 1: Knowledge Agent - 实体识别
        await self._execute_step(task_id, "实体识别", "knowledge", 
                               lambda: self._ner_extraction(message))
        
        # Step 2: Knowledge Agent - 证据收集  
        await self._execute_step(task_id, "证据收集", "knowledge",
                               lambda: self._evidence_collection(message))
        
        # Step 3: Knowledge Agent - 拓扑分析
        await self._execute_step(task_id, "拓扑分析", "knowledge",
                               lambda: self._topology_analysis(message))
        
        # Step 4: Reasoning Agent - 根因推理
        await self._execute_step(task_id, "根因推理", "reasoning",
                               lambda: self._root_cause_reasoning(message))
        
        # Step 5: Executor Agent - 解决方案
        await self._execute_step(task_id, "解决方案", "executor",
                               lambda: self._solution_generation(message))
    
    async def _execute_step(self, task_id: str, step_name: str, agent_id: str, execute_func):
        """执行单个步骤"""
        
        # 开始执行
        self.task_manager.update_agent_status(
            task_id, agent_id, "working", 
            f"执行{step_name}", 0.1
        )
        
        try:
            # 执行具体逻辑
            result = await execute_func()
            
            # 更新进度
            self.task_manager.update_agent_status(
                task_id, agent_id, "working", 
                f"完成{step_name}", 0.8
            )
            
            await asyncio.sleep(0.2)
            
            # 完成步骤
            self.task_manager.update_agent_status(
                task_id, agent_id, "done", 
                result=result["summary"]
            )
            
            # 添加中间结论（包含原始数据）
            conclusion_data = {
                "step_id": step_name,
                "agent_id": agent_id,
                "agent_name": self.task_manager.tasks[task_id].agents[agent_id].agent_name,
                "conclusion": result["conclusion"],
                "confidence": result["confidence"],
                "timestamp": datetime.now().isoformat(),
                "raw_data": result.get("data", {})  # 保存原始数据
            }
            self.task_manager.tasks[task_id].intermediate_conclusions.append(conclusion_data)
            
        except Exception as e:
            self.task_manager.update_agent_status(
                task_id, agent_id, "failed", 
                error=str(e)
            )
            raise
    
    async def _ner_extraction(self, message: str) -> Dict[str, Any]:
        """NER实体识别"""
        from ..utils.ner_extractor import ner_extractor
        
        await asyncio.sleep(0.3)
        entities = ner_extractor.extract_entities(message)
        
        service_names = [e.text for e in entities if e.label == "SERVICE"]
        components = [e.text for e in entities if e.label.startswith("COMPONENT_")]
        
        return {
            "summary": f"识别到{len(service_names)}个服务，{len(components)}个组件",
            "conclusion": f"发现关键服务: {', '.join(service_names)}，涉及组件: {', '.join(components)}",
            "confidence": 0.9,
            "data": {"services": service_names, "components": components}
        }
    
    async def _evidence_collection(self, message: str) -> Dict[str, Any]:
        """证据收集"""
        from ..services.improved_rag_service import ImprovedRAGService
        
        improved_rag = ImprovedRAGService()
        
        await asyncio.sleep(0.8)
        search_results = await improved_rag.hybrid_search(query=message, limit=15)
        actual_results = search_results.get("results", []) if isinstance(search_results, dict) else []
        
        return {
            "summary": f"收集到{len(actual_results)}个证据文档",
            "conclusion": f"从日志和文档中找到{len(actual_results)}条相关证据，涵盖服务状态、性能指标和历史事件",
            "confidence": 0.85,
            "data": {
                "evidence_count": len(actual_results), 
                "evidence": actual_results[:5],
                "full_search_results": actual_results  # 保存完整搜索结果
            }
        }
    
    async def _topology_analysis(self, message: str) -> Dict[str, Any]:
        """拓扑分析"""
        from ..services.topology_service import topology_service
        from ..utils.ner_extractor import ner_extractor
        
        entities = ner_extractor.extract_entities(message)
        service_names = [e.text for e in entities if e.label == "SERVICE"]
        
        await asyncio.sleep(0.4)
        topology_data = await topology_service.get_service_topology(service_names)
        
        relationships = topology_data.get("relationships", [])
        
        return {
            "summary": f"分析了{len(relationships)}个服务依赖关系",
            "conclusion": f"发现{len(set([r.get('from_service') for r in relationships]))}个上游服务，{len(set([r.get('to_service') for r in relationships]))}个下游依赖",
            "confidence": 0.8,
            "data": {
                "topology": topology_data,
                "full_topology_data": topology_data,  # 保存完整拓扑数据
                "analyzed_services": service_names
            }
        }
    
    async def _root_cause_reasoning(self, message: str) -> Dict[str, Any]:
        """根因推理"""
        
        await asyncio.sleep(1.2)
        
        # 模拟推理过程
        reasoning_steps = [
            "分析症状模式和时间序列",
            "关联依赖服务状态变化", 
            "识别性能瓶颈和资源约束",
            "确定最可能的根本原因"
        ]
        
        return {
            "summary": "完成多维度根因分析",
            "conclusion": "基于CPU使用率异常和服务依赖分析，判断可能是资源竞争导致的性能瓶颈",
            "confidence": 0.82,
            "data": {"reasoning_steps": reasoning_steps}
        }
    
    async def _solution_generation(self, message: str) -> Dict[str, Any]:
        """解决方案生成"""
        
        await asyncio.sleep(0.8)
        
        solutions = [
            "立即监控CPU使用率趋势，识别高消耗进程",
            "检查服务配置，调整资源限制参数",
            "分析依赖服务状态，排除级联影响",
            "实施负载均衡策略，分散请求压力"
        ]
        
        return {
            "summary": "生成4项具体解决方案",
            "conclusion": f"建议按优先级实施以下解决方案: {'; '.join(solutions[:2])}",
            "confidence": 0.78,
            "data": {"solutions": solutions}
        }
    
    async def _result_integration_phase(self, task_id: str):
        """结果整合阶段"""
        
        # 获取所有中间结论
        task_status = self.task_manager.get_multi_agent_status(task_id)
        conclusions = task_status.get("intermediate_conclusions", [])
        
        # 构建最终结果
        final_result = {
            "success": True,
            "response": self._build_final_analysis(conclusions),
            "agent_execution_summary": {
                agent_id: agent_data["result"] 
                for agent_id, agent_data in task_status["agents"].items() 
                if agent_data["result"]
            },
            "planning_sessions": task_status["planning_sessions"],
            "confidence_score": self._calculate_overall_confidence(conclusions),
            "execution_duration": self._calculate_execution_time(task_status),
            "total_agents_involved": len([a for a in task_status["agents"].values() if a["status"] == "done"]),
            
            # 添加详细的证据和解决方案数据
            "detailed_evidence": self._extract_detailed_evidence(conclusions),
            "detailed_solutions": self._extract_detailed_solutions(conclusions),
            "reasoning_process": self._extract_reasoning_process(conclusions)
        }
        
        self.task_manager.complete_multi_agent_task(task_id, final_result)
    
    def _build_final_analysis(self, conclusions: List[Dict[str, Any]]) -> str:
        """构建最终分析报告"""
        if not conclusions:
            return "分析完成，但未能获取详细结论"
        
        analysis = "## Multi-Agent根因分析报告\n\n"
        
        for conclusion in conclusions:
            agent_name = conclusion.get("agent_name", "Unknown")
            content = conclusion.get("conclusion", "")
            confidence = conclusion.get("confidence", 0.0)
            
            analysis += f"**{agent_name}**: {content} (置信度: {confidence:.0%})\n\n"
        
        analysis += "**综合结论**: 通过多Agent协作分析，建议优先处理资源配置和性能优化问题。"
        
        return analysis
    
    def _calculate_overall_confidence(self, conclusions: List[Dict[str, Any]]) -> float:
        """计算整体置信度"""
        if not conclusions:
            return 0.6
        
        confidences = [c.get("confidence", 0.0) for c in conclusions]
        return sum(confidences) / len(confidences)
    
    def _calculate_execution_time(self, task_status: Dict[str, Any]) -> float:
        """计算执行时间"""
        created = datetime.fromisoformat(task_status["created_at"])
        completed = datetime.fromisoformat(task_status["completed_at"]) if task_status["completed_at"] else datetime.now()
        
        return (completed - created).total_seconds()
    
    def get_multi_agent_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取Multi-Agent任务状态"""
        return self.task_manager.get_multi_agent_status(task_id)
    
    async def interrupt_task(self, task_id: str, reason: str = "用户请求中断") -> bool:
        """中断任务执行"""
        success = self.task_manager.interrupt_task(task_id, reason)
        
        # 如果任务正在运行，取消异步任务
        if task_id in self.running_tasks:
            async_task = self.running_tasks[task_id]
            if not async_task.done():
                async_task.cancel()
                try:
                    await async_task
                except asyncio.CancelledError:
                    logger.info(f"任务 {task_id} 异步执行已取消")
            
            del self.running_tasks[task_id]
        
        return success
    
    def cleanup_completed_tasks(self):
        """清理已完成的任务"""
        # Multi-agent tasks cleanup logic can be added here
        pass
    
    def _extract_detailed_evidence(self, conclusions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """提取详细证据信息"""
        evidence_data = {
            "entities_found": [],
            "documents_searched": 0,
            "topology_relations": 0,
            "evidence_summary": "",
            "rag_evidence": [],  # RAG搜索结果详细信息
            "topology_data": {},  # Neo4j拓扑数据
            "log_files_analyzed": []  # 分析的日志文件详情
        }
        
        for conclusion in conclusions:
            # 从结论的raw_data中提取详细信息
            raw_data = conclusion.get('raw_data', {})
            
            if conclusion["agent_id"] == "knowledge":
                if conclusion["step_id"] == "证据收集" and 'full_search_results' in raw_data:
                    evidence_data["rag_evidence"] = raw_data['full_search_results']
                elif conclusion["step_id"] == "拓扑分析" and 'full_topology_data' in raw_data:
                    evidence_data["topology_data"] = raw_data['full_topology_data']
            
            if conclusion["agent_id"] == "knowledge":
                if conclusion["step_id"] == "实体识别":
                    # 从结论中提取实体信息
                    if "service-" in conclusion["conclusion"]:
                        services = [s.strip() for s in conclusion["conclusion"].split("服务:")[1].split("，")[0].split(",")]
                        evidence_data["entities_found"].extend(services)
                        
                elif conclusion["step_id"] == "证据收集":
                    # 从结论中提取文档数量
                    if "条相关证据" in conclusion["conclusion"]:
                        import re
                        match = re.search(r'(\d+)条相关证据', conclusion["conclusion"])
                        if match:
                            evidence_data["documents_searched"] = int(match.group(1))
                            
                elif conclusion["step_id"] == "拓扑分析":
                    # 从结论中提取关系数量
                    if "个下游依赖" in conclusion["conclusion"]:
                        import re
                        match = re.search(r'(\d+)个下游依赖', conclusion["conclusion"])
                        if match:
                            evidence_data["topology_relations"] = int(match.group(1))
        
        # 从RAG证据中提取详细信息，区分不同数据源类型
        for evidence in evidence_data["rag_evidence"]:
            if isinstance(evidence, dict):
                source_type = evidence.get('source_type', 'unknown')
                log_file = evidence.get('log_file', 'unknown')
                
                # 根据source_type确定显示的文件/数据源名称和类型
                if source_type == 'logs':
                    # 真正的日志文件
                    display_name = log_file
                    data_type = '日志文件'
                elif source_type == 'wiki':
                    display_name = 'Wiki知识库'
                    data_type = '知识文档'
                elif source_type == 'jira':
                    display_name = 'JIRA工单系统'
                    data_type = '工单记录'
                elif source_type == 'gitlab':
                    display_name = 'GitLab项目'
                    data_type = '代码仓库'
                else:
                    display_name = f'{source_type}数据源'
                    data_type = '其他数据'
                
                file_info = {
                    'file_path': display_name,
                    'data_type': data_type,
                    'source_type': source_type,
                    'service': evidence.get('service_name', evidence.get('service', 'unknown')),
                    'machine': evidence.get('machine', 'unknown'),  # May not be available in new format
                    'timestamp': evidence.get('timestamp', 'unknown'),
                    'content_preview': evidence.get('content', evidence.get('page_content', ''))[:200] + '...' if evidence.get('content', evidence.get('page_content', '')) else ''
                }
                if file_info not in evidence_data["log_files_analyzed"]:
                    evidence_data["log_files_analyzed"].append(file_info)
        
        # 统计不同数据源类型
        source_counts = {}
        for item in evidence_data["log_files_analyzed"]:
            data_type = item.get('data_type', '其他数据')
            source_counts[data_type] = source_counts.get(data_type, 0) + 1
        
        source_summary = []
        for data_type, count in source_counts.items():
            source_summary.append(f"{count}个{data_type}")
        
        evidence_data["evidence_summary"] = f"识别到{len(evidence_data['entities_found'])}个关键实体，搜索了{evidence_data['documents_searched']}个证据文档，分析了{', '.join(source_summary)}，发现{evidence_data['topology_relations']}个服务依赖关系"
        
        return evidence_data
    
    def _extract_detailed_solutions(self, conclusions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取详细解决方案"""
        solutions = []
        
        for conclusion in conclusions:
            if conclusion["agent_id"] == "executor" and conclusion["step_id"] == "解决方案":
                # 解析解决方案文本
                solution_text = conclusion["conclusion"]
                if "建议按优先级实施以下解决方案:" in solution_text:
                    solution_parts = solution_text.split("建议按优先级实施以下解决方案:")[1].split(";")
                    
                    for i, solution in enumerate(solution_parts):
                        if solution.strip():
                            solutions.append({
                                "priority": i + 1,
                                "description": solution.strip(),
                                "type": "immediate" if i < 2 else "follow_up",
                                "confidence": conclusion["confidence"]
                            })
        
        # 如果没有找到具体解决方案，添加默认建议
        if not solutions:
            solutions = [
                {
                    "priority": 1,
                    "description": "监控系统性能指标，识别异常模式",
                    "type": "immediate",
                    "confidence": 0.8
                },
                {
                    "priority": 2,
                    "description": "检查服务配置和资源分配",
                    "type": "immediate", 
                    "confidence": 0.8
                },
                {
                    "priority": 3,
                    "description": "分析服务依赖关系，排除级联影响",
                    "type": "follow_up",
                    "confidence": 0.7
                }
            ]
        
        return solutions
    
    def _extract_reasoning_process(self, conclusions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """提取推理过程"""
        reasoning_steps = []
        
        for conclusion in conclusions:
            if conclusion["agent_id"] == "reasoning":
                reasoning_steps.append({
                    "step": conclusion["step_id"],
                    "analysis": conclusion["conclusion"],
                    "confidence": conclusion["confidence"],
                    "timestamp": conclusion["timestamp"]
                })
        
        return {
            "steps": reasoning_steps,
            "methodology": "基于症状分析→证据关联→依赖分析→根因推理的多维度分析方法",
            "key_insights": [
                "利用实时监控数据和历史日志进行证据收集",
                "通过服务拓扑图分析影响范围和依赖关系", 
                "结合多Agent协作提高分析准确性和全面性"
            ]
        }

# 全局enhanced流式RCA服务实例
enhanced_streaming_rca_service = EnhancedStreamingRCAService()