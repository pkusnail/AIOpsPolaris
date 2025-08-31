"""
任务状态管理器
用于跟踪RCA分析任务的执行进度和状态
"""

import uuid
import asyncio
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class TaskStage:
    """任务阶段信息"""
    stage: str
    status: str  # pending, in_progress, completed, failed
    duration_ms: Optional[int] = None
    result: Optional[str] = None
    progress: float = 0.0
    current_detail: Optional[str] = None
    timestamp: Optional[str] = None

@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    status: str  # queued, processing, completed, failed
    progress: float
    current_stage: str
    current_stage_detail: str
    estimated_remaining: float
    total_duration: Optional[float] = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    stages: List[TaskStage] = None
    final_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class TaskManager:
    """任务状态管理器"""
    
    def __init__(self):
        self.tasks: Dict[str, TaskInfo] = {}
        self.stage_definitions = {
            "ner_extraction": {"name": "NER实体识别", "weight": 0.1},
            "hybrid_search": {"name": "混合搜索", "weight": 0.3},
            "topology_query": {"name": "拓扑查询", "weight": 0.2},
            "agent_reasoning": {"name": "Agent推理分析", "weight": 0.3},
            "result_formatting": {"name": "结果格式化", "weight": 0.1}
        }
    
    def create_task(self, user_id: str, message: str) -> str:
        """创建新任务"""
        task_id = f"task_{int(time.time())}_{str(uuid.uuid4())[:8]}"
        
        # 初始化所有阶段
        stages = []
        for stage_key, stage_info in self.stage_definitions.items():
            stage = TaskStage(
                stage=stage_info["name"],
                status="pending",
                progress=0.0,
                timestamp=datetime.now().isoformat()
            )
            stages.append(stage)
        
        task_info = TaskInfo(
            task_id=task_id,
            status="queued",
            progress=0.0,
            current_stage="等待开始",
            current_stage_detail="任务已排队，准备执行",
            estimated_remaining=3.5,
            created_at=datetime.now(),
            stages=stages
        )
        
        self.tasks[task_id] = task_info
        logger.info(f"创建任务: {task_id}, 用户: {user_id}, 消息: {message[:50]}...")
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id not in self.tasks:
            return None
        
        task_info = self.tasks[task_id]
        
        # 转换为字典格式
        result = {
            "task_id": task_info.task_id,
            "status": task_info.status,
            "progress": task_info.progress,
            "current_stage": task_info.current_stage,
            "current_stage_detail": task_info.current_stage_detail,
            "estimated_remaining": task_info.estimated_remaining,
            "total_duration": task_info.total_duration,
            "stages_completed": []
        }
        
        # 添加已完成的阶段信息
        for stage in task_info.stages:
            stage_dict = asdict(stage)
            if stage.status in ["completed", "failed", "in_progress"]:
                result["stages_completed"].append(stage_dict)
        
        # 如果任务完成，添加最终结果
        if task_info.status == "completed" and task_info.final_result:
            result["final_result"] = task_info.final_result
        
        # 如果任务失败，添加错误信息
        if task_info.status == "failed" and task_info.error:
            result["error"] = task_info.error
        
        return result
    
    def update_task_stage(self, task_id: str, stage_name: str, 
                         status: str, progress: float = None, 
                         result: str = None, duration_ms: int = None,
                         current_detail: str = None):
        """更新任务阶段状态"""
        if task_id not in self.tasks:
            logger.warning(f"任务不存在: {task_id}")
            return
        
        task_info = self.tasks[task_id]
        
        # 更新对应阶段
        for stage in task_info.stages:
            if stage.stage == stage_name:
                stage.status = status
                if progress is not None:
                    stage.progress = progress
                if result:
                    stage.result = result
                if duration_ms:
                    stage.duration_ms = duration_ms
                if current_detail:
                    stage.current_detail = current_detail
                stage.timestamp = datetime.now().isoformat()
                break
        
        # 更新任务整体状态
        self._update_task_progress(task_id)
        
        # 更新当前阶段信息
        if status == "in_progress":
            task_info.current_stage = stage_name
            task_info.current_stage_detail = current_detail or f"正在执行{stage_name}"
        
        logger.info(f"任务 {task_id} 阶段更新: {stage_name} -> {status}")
    
    def complete_task(self, task_id: str, final_result: Dict[str, Any]):
        """完成任务"""
        if task_id not in self.tasks:
            logger.warning(f"任务不存在: {task_id}")
            return
        
        task_info = self.tasks[task_id]
        task_info.status = "completed"
        task_info.progress = 1.0
        task_info.completed_at = datetime.now()
        task_info.total_duration = (
            task_info.completed_at - task_info.created_at
        ).total_seconds()
        task_info.final_result = final_result
        task_info.current_stage = "完成"
        task_info.current_stage_detail = "分析完成，结果已生成"
        task_info.estimated_remaining = 0.0
        
        logger.info(f"任务完成: {task_id}, 耗时: {task_info.total_duration:.2f}秒")
    
    def fail_task(self, task_id: str, error: str):
        """标记任务失败"""
        if task_id not in self.tasks:
            logger.warning(f"任务不存在: {task_id}")
            return
        
        task_info = self.tasks[task_id]
        task_info.status = "failed"
        task_info.completed_at = datetime.now()
        task_info.total_duration = (
            task_info.completed_at - task_info.created_at
        ).total_seconds()
        task_info.error = error
        task_info.current_stage = "失败"
        task_info.current_stage_detail = f"执行失败: {error}"
        task_info.estimated_remaining = 0.0
        
        logger.error(f"任务失败: {task_id}, 错误: {error}")
    
    def _update_task_progress(self, task_id: str):
        """更新任务整体进度"""
        task_info = self.tasks[task_id]
        
        total_weight = 0.0
        completed_weight = 0.0
        
        for i, stage in enumerate(task_info.stages):
            stage_key = list(self.stage_definitions.keys())[i]
            weight = self.stage_definitions[stage_key]["weight"]
            total_weight += weight
            
            if stage.status == "completed":
                completed_weight += weight
            elif stage.status == "in_progress":
                completed_weight += weight * stage.progress
        
        task_info.progress = completed_weight / total_weight if total_weight > 0 else 0.0
        
        # 更新预估剩余时间
        if task_info.progress > 0 and task_info.status == "processing":
            elapsed = (datetime.now() - task_info.created_at).total_seconds()
            estimated_total = elapsed / task_info.progress
            task_info.estimated_remaining = max(0, estimated_total - elapsed)
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务"""
        current_time = datetime.now()
        to_remove = []
        
        for task_id, task_info in self.tasks.items():
            age_hours = (current_time - task_info.created_at).total_seconds() / 3600
            if age_hours > max_age_hours:
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.tasks[task_id]
            logger.info(f"清理过期任务: {task_id}")
    
    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """获取所有任务状态"""
        return {
            task_id: self.get_task_status(task_id) 
            for task_id in self.tasks.keys()
        }

# 全局任务管理器实例
task_manager = TaskManager()