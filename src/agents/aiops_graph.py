"""
AIOps主图
协调各个Agent的工作流程
"""

from langgraph.graph import StateGraph, END
from typing import Dict, Any, Optional, AsyncGenerator
import logging
from datetime import datetime

from .base_agent import AgentState, AgentMessage, MessageType
from .planner_agent import PlannerAgent
from .knowledge_agent import KnowledgeAgent
from .reasoning_agent import ReasoningAgent
from .executor_agent import ExecutorAgent
from ..services.search_service import SearchService
from ..services.graph_service import GraphService

logger = logging.getLogger(__name__)


class AIOpsGraph:
    """AIOps主图类"""
    
    def __init__(
        self,
        search_service: Optional[SearchService] = None,
        graph_service: Optional[GraphService] = None,
        llm_service: Optional[Any] = None
    ):
        self.search_service = search_service
        self.graph_service = graph_service
        self.llm_service = llm_service
        
        # 初始化各个Agent
        self.planner = PlannerAgent(llm_service)
        self.knowledge = KnowledgeAgent(search_service, graph_service)
        self.reasoning = ReasoningAgent(llm_service)
        self.executor = ExecutorAgent()
        
        # 为Agent添加服务
        if search_service:
            self.planner.search_service = search_service
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 构建图
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """构建LangGraph工作流"""
        
        # 定义状态图
        workflow = StateGraph(AgentState)
        
        # 添加节点
        workflow.add_node("planner", self._run_planner)
        workflow.add_node("knowledge", self._run_knowledge)
        workflow.add_node("reasoning", self._run_reasoning)
        workflow.add_node("executor", self._run_executor)
        workflow.add_node("final", self._finalize_response)
        
        # 定义边和条件
        workflow.set_entry_point("planner")
        
        # 规划器 -> 知识检索
        workflow.add_edge("planner", "knowledge")
        
        # 知识检索 -> 推理分析
        workflow.add_edge("knowledge", "reasoning")
        
        # 推理分析 -> 条件路由（是否需要执行）
        workflow.add_conditional_edges(
            "reasoning",
            self._should_execute,
            {
                "execute": "executor",
                "final": "final"
            }
        )
        
        # 执行器 -> 最终响应
        workflow.add_edge("executor", "final")
        
        # 最终响应 -> 结束
        workflow.add_edge("final", END)
        
        return workflow.compile()
    
    async def _run_planner(self, state: AgentState) -> AgentState:
        """运行规划智能体"""
        try:
            self.logger.info("Running planner agent")
            
            # 添加阶段标记
            phase_msg = AgentMessage(
                type=MessageType.THOUGHT,
                content="📋 开始任务规划阶段",
                agent_id="system"
            )
            state.add_message(phase_msg)
            
            # 运行规划器
            updated_state = await self.planner.process(state)
            
            return updated_state
            
        except Exception as e:
            self.logger.error(f"Planner agent failed: {e}")
            return await self.planner.handle_error(state, e)
    
    async def _run_knowledge(self, state: AgentState) -> AgentState:
        """运行知识智能体"""
        try:
            self.logger.info("Running knowledge agent")
            
            # 添加阶段标记
            phase_msg = AgentMessage(
                type=MessageType.THOUGHT,
                content="🔍 开始知识检索阶段",
                agent_id="system"
            )
            state.add_message(phase_msg)
            
            # 重置步数计数器，让知识智能体从头开始
            knowledge_state = AgentState(
                messages=state.messages.copy(),
                context=state.context.copy(),
                current_step=0,
                max_steps=self.knowledge.max_steps,
                is_complete=False
            )
            
            # 运行知识检索
            updated_state = await self.knowledge.process(knowledge_state)
            
            # 将结果合并回主状态
            state.messages = updated_state.messages
            state.context.update(updated_state.context)
            
            return state
            
        except Exception as e:
            self.logger.error(f"Knowledge agent failed: {e}")
            return await self.knowledge.handle_error(state, e)
    
    async def _run_reasoning(self, state: AgentState) -> AgentState:
        """运行推理智能体"""
        try:
            self.logger.info("Running reasoning agent")
            
            # 添加阶段标记
            phase_msg = AgentMessage(
                type=MessageType.THOUGHT,
                content="🧠 开始推理分析阶段",
                agent_id="system"
            )
            state.add_message(phase_msg)
            
            # 重置步数计数器
            reasoning_state = AgentState(
                messages=state.messages.copy(),
                context=state.context.copy(),
                current_step=0,
                max_steps=self.reasoning.max_steps,
                is_complete=False
            )
            
            # 运行推理分析
            updated_state = await self.reasoning.process(reasoning_state)
            
            # 将结果合并回主状态
            state.messages = updated_state.messages
            state.context.update(updated_state.context)
            
            return state
            
        except Exception as e:
            self.logger.error(f"Reasoning agent failed: {e}")
            return await self.reasoning.handle_error(state, e)
    
    async def _run_executor(self, state: AgentState) -> AgentState:
        """运行执行智能体"""
        try:
            self.logger.info("Running executor agent")
            
            # 添加阶段标记
            phase_msg = AgentMessage(
                type=MessageType.THOUGHT,
                content="⚙️ 开始执行操作阶段",
                agent_id="system"
            )
            state.add_message(phase_msg)
            
            # 重置步数计数器
            executor_state = AgentState(
                messages=state.messages.copy(),
                context=state.context.copy(),
                current_step=0,
                max_steps=self.executor.max_steps,
                is_complete=False
            )
            
            # 运行执行器
            updated_state = await self.executor.process(executor_state)
            
            # 将结果合并回主状态
            state.messages = updated_state.messages
            state.context.update(updated_state.context)
            
            return state
            
        except Exception as e:
            self.logger.error(f"Executor agent failed: {e}")
            return await self.executor.handle_error(state, e)
    
    def _should_execute(self, state: AgentState) -> str:
        """决定是否需要执行具体操作"""
        try:
            # 检查推理结果中的建议
            final_recommendation = state.context.get("final_recommendation", {})
            
            # 如果有具体的实施计划，则执行
            if final_recommendation.get("implementation_plan"):
                implementation_plan = final_recommendation["implementation_plan"]
                
                # 检查是否包含需要执行的操作
                execution_keywords = [
                    "重启", "restart", "配置", "config", "部署", "deploy",
                    "扩容", "scale", "修复", "fix", "更新", "update"
                ]
                
                for step in implementation_plan:
                    step_lower = step.lower()
                    if any(keyword in step_lower for keyword in execution_keywords):
                        self.logger.info("Found executable operations, routing to executor")
                        return "execute"
            
            # 检查问题类型，某些类型需要执行
            execution_plan = state.context.get("execution_plan", {})
            problem_type = execution_plan.get("problem_type", "")
            
            if problem_type in ["troubleshooting", "deployment"]:
                return "execute"
            
            self.logger.info("No executable operations found, routing to final")
            return "final"
            
        except Exception as e:
            self.logger.error(f"Error in routing decision: {e}")
            return "final"  # 默认跳到最终响应
    
    async def _finalize_response(self, state: AgentState) -> AgentState:
        """最终响应整理"""
        try:
            # 添加阶段标记
            phase_msg = AgentMessage(
                type=MessageType.THOUGHT,
                content="✅ 整理最终响应",
                agent_id="system"
            )
            state.add_message(phase_msg)
            
            # 生成综合响应
            final_response = self._generate_comprehensive_response(state)
            
            final_msg = AgentMessage(
                type=MessageType.ANSWER,
                content=final_response,
                agent_id="system",
                metadata={
                    "session_complete": True,
                    "processing_time": self._calculate_processing_time(state)
                }
            )
            state.add_message(final_msg)
            
            state.is_complete = True
            return state
            
        except Exception as e:
            self.logger.error(f"Failed to finalize response: {e}")
            error_msg = AgentMessage(
                type=MessageType.ERROR,
                content=f"响应整理失败: {str(e)}",
                agent_id="system"
            )
            state.add_message(error_msg)
            state.is_complete = True
            return state
    
    def _generate_comprehensive_response(self, state: AgentState) -> str:
        """生成综合响应"""
        try:
            output = []
            output.append("# 🤖 AIOps Polaris 智能运维助手")
            output.append("")
            
            # 获取各阶段的结果
            execution_plan = state.context.get("execution_plan", {})
            knowledge_summary = state.context.get("knowledge_summary", {})
            final_recommendation = state.context.get("final_recommendation", {})
            execution_report = state.context.get("execution_report", {})
            
            # 问题分析总结
            if execution_plan:
                output.append("## 📊 问题分析")
                output.append(f"- **问题类型**: {execution_plan.get('problem_type', '未知')}")
                output.append(f"- **优先级**: {execution_plan.get('priority', '中等')}")
                output.append(f"- **复杂度**: {execution_plan.get('complexity', '中等')}")
                output.append("")
            
            # 知识检索结果
            if knowledge_summary:
                confidence = knowledge_summary.get("confidence_score", 0.0)
                output.append("## 🔍 知识检索")
                output.append(f"- **置信度**: {confidence:.2f}")
                
                if knowledge_summary.get("key_points"):
                    output.append("- **关键信息**:")
                    for point in knowledge_summary["key_points"][:3]:
                        output.append(f"  - {point}")
                output.append("")
            
            # 推理分析结果
            if final_recommendation:
                output.append("## 🧠 推理分析")
                output.append(f"- **主要建议**: {final_recommendation.get('primary_recommendation', '无')}")
                output.append(f"- **风险评估**: {final_recommendation.get('risk_assessment', '未评估')}")
                
                if final_recommendation.get("success_metrics"):
                    output.append("- **成功指标**:")
                    for metric in final_recommendation["success_metrics"][:3]:
                        output.append(f"  - {metric}")
                output.append("")
            
            # 执行结果
            if execution_report:
                output.append("## ⚙️ 执行结果")
                status = "✅ 成功" if execution_report.get("overall_success") else "⚠️ 部分成功"
                output.append(f"- **执行状态**: {status}")
                output.append(f"- **执行步骤**: {execution_report.get('successful_steps', 0)}/{execution_report.get('total_steps', 0)}")
                output.append(f"- **总耗时**: {execution_report.get('total_time', 0):.1f} 秒")
                output.append("")
            
            # 总结
            output.append("## 📝 总结")
            if execution_report and execution_report.get("overall_success"):
                output.append("✅ 问题已成功解决，所有操作执行完毕。")
            elif final_recommendation:
                output.append("💡 已完成问题分析并提供解决建议，请根据建议进行后续操作。")
            else:
                output.append("📋 已完成初步分析，建议进一步收集信息或联系技术团队。")
            
            return "\n".join(output)
            
        except Exception as e:
            self.logger.error(f"Failed to generate comprehensive response: {e}")
            return "响应生成失败，但分析过程已完成。"
    
    def _calculate_processing_time(self, state: AgentState) -> float:
        """计算处理时间"""
        try:
            if state.messages:
                start_time = state.messages[0].timestamp
                end_time = state.messages[-1].timestamp
                
                if start_time and end_time:
                    return (end_time - start_time).total_seconds()
            
            return 0.0
        except Exception:
            return 0.0
    
    async def process_user_message(
        self,
        user_message: str,
        user_id: str = "default",
        session_id: Optional[str] = None
    ) -> AsyncGenerator[AgentMessage, None]:
        """处理用户消息并流式返回结果"""
        try:
            # 创建初始状态
            initial_state = AgentState(
                messages=[],
                context={
                    "user_message": user_message,
                    "user_id": user_id,
                    "session_id": session_id or f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                },
                current_step=0,
                max_steps=20,  # 总体最大步数
                is_complete=False
            )
            
            # 添加用户消息
            user_msg = AgentMessage(
                type=MessageType.THOUGHT,
                content=f"用户查询: {user_message}",
                agent_id="user"
            )
            initial_state.add_message(user_msg)
            
            # 启动图执行
            self.logger.info(f"Starting AIOps graph processing for: {user_message}")
            
            # 使用图执行
            async for state in self.graph.astream(initial_state):
                # state是一个字典，包含当前节点的状态
                for node_name, node_state in state.items():
                    if hasattr(node_state, 'messages'):
                        # 返回新产生的消息
                        for message in node_state.messages:
                            if message.timestamp and message.timestamp > initial_state.messages[-1].timestamp:
                                yield message
            
        except Exception as e:
            self.logger.error(f"Graph processing failed: {e}")
            error_msg = AgentMessage(
                type=MessageType.ERROR,
                content=f"处理失败: {str(e)}",
                agent_id="system"
            )
            yield error_msg
    
    async def process_user_message_simple(
        self,
        user_message: str,
        user_id: str = "default",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """简化版本的消息处理，返回最终结果"""
        try:
            # 创建初始状态
            initial_state = AgentState(
                messages=[],
                context={
                    "user_message": user_message,
                    "user_id": user_id,
                    "session_id": session_id or f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                },
                current_step=0,
                max_steps=20,
                is_complete=False
            )
            
            # 添加用户消息
            user_msg = AgentMessage(
                type=MessageType.THOUGHT,
                content=f"用户查询: {user_message}",
                agent_id="user"
            )
            initial_state.add_message(user_msg)
            
            # 按顺序执行各个阶段
            # 1. 规划阶段
            state = await self._run_planner(initial_state)
            if state.error:
                return {"error": state.error, "messages": [msg.content for msg in state.messages]}
            
            # 2. 知识检索阶段
            state = await self._run_knowledge(state)
            if state.error:
                return {"error": state.error, "messages": [msg.content for msg in state.messages]}
            
            # 3. 推理分析阶段
            state = await self._run_reasoning(state)
            if state.error:
                return {"error": state.error, "messages": [msg.content for msg in state.messages]}
            
            # 4. 判断是否需要执行
            should_execute = self._should_execute(state)
            if should_execute == "execute":
                state = await self._run_executor(state)
            
            # 5. 最终整理
            state = await self._finalize_response(state)
            
            # 返回结果
            return {
                "success": True,
                "messages": [
                    {
                        "type": msg.type.value,
                        "content": msg.content,
                        "agent_id": msg.agent_id,
                        "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                        "metadata": msg.metadata
                    }
                    for msg in state.messages
                ],
                "context": state.context,
                "processing_time": self._calculate_processing_time(state)
            }
            
        except Exception as e:
            self.logger.error(f"Simple processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "messages": []
            }
    
    def get_agent_status(self) -> Dict[str, Any]:
        """获取各Agent状态"""
        return {
            "planner": self.planner.get_capabilities(),
            "knowledge": self.knowledge.get_capabilities(),
            "reasoning": self.reasoning.get_capabilities(),
            "executor": self.executor.get_capabilities(),
            "services": {
                "search_service": self.search_service is not None,
                "graph_service": self.graph_service is not None,
                "llm_service": self.llm_service is not None
            }
        }