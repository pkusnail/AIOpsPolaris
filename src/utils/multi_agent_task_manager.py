"""
Multi-Agent任务状态管理器
支持Planner-Executor多Agent系统的详细状态跟踪
"""

import uuid
import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class AgentStatus:
    """单个Agent状态"""
    agent_id: str
    agent_name: str
    status: str  # waiting, working, done, failed
    current_action: Optional[str] = None
    progress: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None

@dataclass
class PlanStep:
    """规划步骤"""
    step_id: str
    step_name: str
    description: str
    assigned_agent: str
    status: str  # pending, executing, completed, failed
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他步骤
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[str] = None

@dataclass
class PlanningSession:
    """规划会话"""
    session_id: str
    plan_version: int
    plan_description: str
    steps: List[PlanStep]
    status: str  # planning, executing, completed, failed
    created_at: datetime
    reasoning: Optional[str] = None  # Planner的推理过程

@dataclass
class MultiAgentTaskInfo:
    """Multi-Agent任务信息"""
    task_id: str
    status: str  # queued, planning, executing, completed, failed, interrupted
    overall_progress: float
    current_phase: str  # planning, execution, review
    user_can_interrupt: bool
    
    # Planning相关
    planning_sessions: List[PlanningSession]
    current_plan_version: int
    
    # Agent状态
    agents: Dict[str, AgentStatus]
    
    # 时间戳
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 结果
    intermediate_conclusions: List[Dict[str, Any]] = field(default_factory=list)
    final_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class MultiAgentTaskManager:
    """Multi-Agent任务状态管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, MultiAgentTaskInfo] = {}
        
        # 定义系统中的所有agents
        self.available_agents = {
            "planner": {"name": "规划智能体", "description": "分析问题并制定执行计划"},
            "knowledge": {"name": "知识智能体", "description": "搜索和整理相关知识"},
            "reasoning": {"name": "推理智能体", "description": "进行逻辑推理和根因分析"},
            "executor": {"name": "执行智能体", "description": "生成具体的解决方案"},
            "monitor": {"name": "监控智能体", "description": "监控执行过程和结果验证"}
        }
    
    def create_multi_agent_task(self, user_id: str, message: str) -> str:
        """创建multi-agent任务"""
        task_id = f"ma_task_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        
        # 初始化所有agents状态
        agents = {}
        for agent_id, agent_info in self.available_agents.items():
            agents[agent_id] = AgentStatus(
                agent_id=agent_id,
                agent_name=agent_info["name"],
                status="waiting"
            )
        
        task_info = MultiAgentTaskInfo(
            task_id=task_id,
            status="queued",
            overall_progress=0.0,
            current_phase="planning",
            user_can_interrupt=True,
            planning_sessions=[],
            current_plan_version=0,
            agents=agents,
            created_at=datetime.now(),
            intermediate_conclusions=[]
        )
        
        self.tasks[task_id] = task_info
        logger.info(f"创建Multi-Agent任务: {task_id}, 用户: {user_id}")
        
        return task_id
    
    def start_planning_session(self, task_id: str, description: str) -> str:
        """开始新的规划会话"""
        if task_id not in self.tasks:
            return None
        
        task_info = self.tasks[task_id]
        
        # 创建新的规划会话
        session_id = f"plan_{task_info.current_plan_version + 1}"
        plan_session = PlanningSession(
            session_id=session_id,
            plan_version=task_info.current_plan_version + 1,
            plan_description=description,
            steps=[],
            status="planning",
            created_at=datetime.now()
        )
        
        task_info.planning_sessions.append(plan_session)
        task_info.current_plan_version += 1
        task_info.status = "planning"
        task_info.current_phase = "planning"
        
        # 更新Planner agent状态
        task_info.agents["planner"].status = "working"
        task_info.agents["planner"].current_action = "制定执行计划"
        task_info.agents["planner"].start_time = datetime.now()
        
        logger.info(f"任务 {task_id} 开始规划会话: {session_id}")
        return session_id
    
    def add_plan_step(self, task_id: str, step_name: str, description: str, 
                     assigned_agent: str, dependencies: List[str] = None):
        """添加规划步骤"""
        if task_id not in self.tasks:
            return
        
        task_info = self.tasks[task_id]
        if not task_info.planning_sessions:
            return
        
        current_session = task_info.planning_sessions[-1]
        step_id = f"step_{len(current_session.steps) + 1}"
        
        step = PlanStep(
            step_id=step_id,
            step_name=step_name,
            description=description,
            assigned_agent=assigned_agent,
            status="pending",
            dependencies=dependencies or []
        )
        
        current_session.steps.append(step)
        logger.info(f"任务 {task_id} 添加规划步骤: {step_name} -> {assigned_agent}")
    
    def complete_planning_session(self, task_id: str, reasoning: str):
        """完成规划会话"""
        if task_id not in self.tasks:
            return
        
        task_info = self.tasks[task_id]
        if not task_info.planning_sessions:
            return
        
        current_session = task_info.planning_sessions[-1]
        current_session.status = "completed"
        current_session.reasoning = reasoning
        
        # 更新Planner agent状态
        task_info.agents["planner"].status = "done"
        task_info.agents["planner"].end_time = datetime.now()
        task_info.agents["planner"].result = f"制定了{len(current_session.steps)}步执行计划"
        
        # 开始执行阶段
        task_info.status = "executing"
        task_info.current_phase = "execution"
        
        logger.info(f"任务 {task_id} 规划完成，进入执行阶段")
    
    def update_agent_status(self, task_id: str, agent_id: str, status: str, 
                          action: str = None, progress: float = None, 
                          result: str = None, error: str = None):
        """更新Agent状态"""
        if task_id not in self.tasks:
            return
        
        task_info = self.tasks[task_id]
        if agent_id not in task_info.agents:
            return
        
        agent = task_info.agents[agent_id]
        agent.status = status
        
        if action:
            agent.current_action = action
        if progress is not None:
            agent.progress = progress
        if result:
            agent.result = result
        if error:
            agent.error = error
            
        if status == "working" and not agent.start_time:
            agent.start_time = datetime.now()
        elif status in ["done", "failed"]:
            agent.end_time = datetime.now()
        
        # 更新整体进度
        self._update_overall_progress(task_id)
        
        logger.info(f"任务 {task_id} Agent状态更新: {agent_id} -> {status}")
    
    def add_intermediate_conclusion(self, task_id: str, step_id: str, 
                                  agent_id: str, conclusion: str, 
                                  confidence: float = 0.8):
        """添加中间结论"""
        if task_id not in self.tasks:
            return
        
        task_info = self.tasks[task_id]
        
        conclusion_data = {
            "step_id": step_id,
            "agent_id": agent_id,
            "agent_name": task_info.agents[agent_id].agent_name,
            "conclusion": conclusion,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        }
        
        task_info.intermediate_conclusions.append(conclusion_data)
        logger.info(f"任务 {task_id} 添加中间结论: {agent_id} - {conclusion[:50]}...")
    
    def interrupt_task(self, task_id: str, reason: str = "用户中断"):
        """中断任务执行"""
        if task_id not in self.tasks:
            return False
        
        task_info = self.tasks[task_id]
        if not task_info.user_can_interrupt:
            return False
        
        task_info.status = "interrupted"
        task_info.error = reason
        task_info.completed_at = datetime.now()
        
        # 停止所有正在工作的agents
        for agent in task_info.agents.values():
            if agent.status == "working":
                agent.status = "interrupted"
                agent.end_time = datetime.now()
        
        logger.info(f"任务 {task_id} 被中断: {reason}")
        return True
    
    def complete_multi_agent_task(self, task_id: str, final_result: Dict[str, Any]):
        """完成multi-agent任务"""
        if task_id not in self.tasks:
            return
        
        task_info = self.tasks[task_id]
        task_info.status = "completed"
        task_info.overall_progress = 1.0
        task_info.completed_at = datetime.now()
        task_info.final_result = final_result
        task_info.user_can_interrupt = False
        
        # 确保所有agents都标记为完成
        for agent in task_info.agents.values():
            if agent.status == "working":
                agent.status = "done"
                agent.end_time = datetime.now()
        
        logger.info(f"Multi-Agent任务完成: {task_id}")
    
    def fail_multi_agent_task(self, task_id: str, error: str):
        """标记multi-agent任务失败"""
        if task_id not in self.tasks:
            return
        
        task_info = self.tasks[task_id]
        task_info.status = "failed"
        task_info.error = error
        task_info.completed_at = datetime.now()
        task_info.user_can_interrupt = False
        
        logger.error(f"Multi-Agent任务失败: {task_id}, 错误: {error}")
    
    def get_multi_agent_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取multi-agent任务详细状态"""
        if task_id not in self.tasks:
            return None
        
        task_info = self.tasks[task_id]
        
        # 转换agents状态为字典
        agents_status = {}
        for agent_id, agent in task_info.agents.items():
            agents_status[agent_id] = asdict(agent)
        
        # 转换planning sessions
        planning_sessions = []
        for session in task_info.planning_sessions:
            session_dict = asdict(session)
            planning_sessions.append(session_dict)
        
        result = {
            "task_id": task_info.task_id,
            "status": task_info.status,
            "overall_progress": task_info.overall_progress,
            "current_phase": task_info.current_phase,
            "user_can_interrupt": task_info.user_can_interrupt,
            
            # Multi-agent特有信息
            "agents": agents_status,
            "planning_sessions": planning_sessions,
            "current_plan_version": task_info.current_plan_version,
            "intermediate_conclusions": task_info.intermediate_conclusions,
            
            # 时间信息
            "created_at": task_info.created_at.isoformat(),
            "started_at": task_info.started_at.isoformat() if task_info.started_at else None,
            "completed_at": task_info.completed_at.isoformat() if task_info.completed_at else None,
            
            # 结果
            "final_result": task_info.final_result,
            "error": task_info.error
        }
        
        return result
    
    def _update_overall_progress(self, task_id: str):
        """更新整体进度"""
        task_info = self.tasks[task_id]
        
        # 基于agents完成情况计算进度
        total_agents = len(task_info.agents)
        completed_agents = sum(1 for agent in task_info.agents.values() 
                             if agent.status in ["done", "failed"])
        working_agents = sum(agent.progress for agent in task_info.agents.values() 
                           if agent.status == "working")
        
        task_info.overall_progress = (completed_agents + working_agents) / total_agents
        
        # 如果所有关键agents完成，标记为完成
        key_agents = ["planner", "knowledge", "reasoning", "executor"]
        key_completed = all(
            task_info.agents[agent_id].status in ["done", "failed"] 
            for agent_id in key_agents 
            if agent_id in task_info.agents
        )
        
        if key_completed and task_info.status == "executing":
            task_info.status = "completing"

# 全局multi-agent任务管理器实例
multi_agent_task_manager = MultiAgentTaskManager()