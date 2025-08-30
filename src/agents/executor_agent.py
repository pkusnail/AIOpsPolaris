"""
执行智能体
负责具体操作的执行和验证
"""

from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime

from .base_agent import BaseAgent, AgentType, AgentState, AgentMessage, MessageType, ToolAgent

import logging
logger = logging.getLogger(__name__)


class ExecutorAgent(ToolAgent):
    """执行智能体"""
    
    def __init__(self):
        super().__init__(
            agent_id="executor",
            agent_type=AgentType.EXECUTOR,
            name="执行智能体",
            description="负责执行具体的运维操作和验证结果",
            max_steps=5
        )
        
        # 注册工具
        self._register_tools()
        
        # 模拟执行操作的结果
        self.mock_operations = {
            "restart_service": {
                "success_rate": 0.9,
                "time_cost": 30,  # seconds
                "description": "重启服务"
            },
            "check_logs": {
                "success_rate": 1.0,
                "time_cost": 10,
                "description": "检查日志"
            },
            "update_config": {
                "success_rate": 0.8,
                "time_cost": 60,
                "description": "更新配置"
            },
            "scale_resources": {
                "success_rate": 0.85,
                "time_cost": 180,
                "description": "扩容资源"
            },
            "run_diagnosis": {
                "success_rate": 0.95,
                "time_cost": 120,
                "description": "运行诊断"
            }
        }
    
    def _register_tools(self):
        """注册执行工具"""
        self.register_tool(
            "parse_execution_plan",
            self._parse_execution_plan,
            "解析执行计划"
        )
        
        self.register_tool(
            "execute_step",
            self._execute_step,
            "执行具体步骤"
        )
        
        self.register_tool(
            "verify_result",
            self._verify_result,
            "验证执行结果"
        )
        
        self.register_tool(
            "generate_report",
            self._generate_report,
            "生成执行报告"
        )
    
    async def process(self, state: AgentState) -> AgentState:
        """处理执行逻辑"""
        try:
            # 获取执行计划
            execution_plan = state.context.get("execution_plan", {})
            final_recommendation = state.context.get("final_recommendation", {})
            
            # 步骤1: 解析执行计划
            if state.current_step == 0:
                thought_msg = AgentMessage(
                    type=MessageType.THOUGHT,
                    content="开始执行运维操作",
                    agent_id=self.agent_id
                )
                state.add_message(thought_msg)
                
                parse_result = await self.use_tool("parse_execution_plan", execution_plan, final_recommendation)
                
                if parse_result["success"]:
                    parsed_plan = parse_result["result"]
                    state.context["parsed_execution_plan"] = parsed_plan
                    
                    action_msg = AgentMessage(
                        type=MessageType.ACTION,
                        content=f"解析执行计划，共 {len(parsed_plan['steps'])} 个步骤",
                        agent_id=self.agent_id
                    )
                    state.add_message(action_msg)
                else:
                    return await self.handle_error(state, Exception(parse_result["error"]))
            
            # 步骤2-4: 执行具体步骤
            elif 1 <= state.current_step <= 3:
                parsed_plan = state.context.get("parsed_execution_plan", {})
                steps = parsed_plan.get("steps", [])
                
                current_step_idx = state.current_step - 1
                
                if current_step_idx < len(steps):
                    step = steps[current_step_idx]
                    
                    # 执行步骤
                    execute_result = await self.use_tool("execute_step", step)
                    
                    if execute_result["success"]:
                        step_result = execute_result["result"]
                        
                        # 保存步骤结果
                        if "step_results" not in state.context:
                            state.context["step_results"] = []
                        state.context["step_results"].append(step_result)
                        
                        # 验证结果
                        verify_result = await self.use_tool("verify_result", step, step_result)
                        
                        if verify_result["success"]:
                            verification = verify_result["result"]
                            
                            status = "成功" if verification["success"] else "失败"
                            action_msg = AgentMessage(
                                type=MessageType.ACTION,
                                content=f"执行步骤 '{step['name']}': {status}",
                                agent_id=self.agent_id
                            )
                            state.add_message(action_msg)
                            
                            observation_msg = AgentMessage(
                                type=MessageType.OBSERVATION,
                                content=verification["message"],
                                agent_id=self.agent_id
                            )
                            state.add_message(observation_msg)
                        else:
                            return await self.handle_error(state, Exception(verify_result["error"]))
                    else:
                        return await self.handle_error(state, Exception(execute_result["error"]))
            
            # 步骤5: 生成执行报告
            elif state.current_step == 4:
                step_results = state.context.get("step_results", [])
                parsed_plan = state.context.get("parsed_execution_plan", {})
                
                report_result = await self.use_tool("generate_report", parsed_plan, step_results)
                
                if report_result["success"]:
                    report = report_result["result"]
                    state.context["execution_report"] = report
                    
                    # 格式化执行报告
                    report_summary = self._format_execution_report(report)
                    
                    answer_msg = AgentMessage(
                        type=MessageType.ANSWER,
                        content=report_summary,
                        agent_id=self.agent_id,
                        metadata={
                            "total_steps": len(step_results),
                            "successful_steps": report["successful_steps"],
                            "failed_steps": report["failed_steps"],
                            "overall_success": report["overall_success"]
                        }
                    )
                    state.add_message(answer_msg)
                    
                    state.is_complete = True
                else:
                    return await self.handle_error(state, Exception(report_result["error"]))
            
            return state
            
        except Exception as e:
            return await self.handle_error(state, e)
    
    async def _parse_execution_plan(
        self,
        execution_plan: Dict[str, Any],
        recommendation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """解析执行计划"""
        try:
            parsed_plan = {
                "plan_id": execution_plan.get("plan_id", "unknown"),
                "steps": [],
                "estimated_time": 0,
                "risk_level": "medium"
            }
            
            # 从推荐中提取实施步骤
            if recommendation.get("implementation_plan"):
                for i, step_name in enumerate(recommendation["implementation_plan"]):
                    step = {
                        "step_number": i + 1,
                        "name": step_name,
                        "operation_type": self._classify_operation(step_name),
                        "estimated_time": self._estimate_operation_time(step_name),
                        "required_permissions": self._get_required_permissions(step_name),
                        "rollback_possible": self._check_rollback_possibility(step_name)
                    }
                    parsed_plan["steps"].append(step)
                    parsed_plan["estimated_time"] += step["estimated_time"]
            
            # 确定风险级别
            risk_assessment = recommendation.get("risk_assessment", "")
            if "高风险" in risk_assessment:
                parsed_plan["risk_level"] = "high"
            elif "低风险" in risk_assessment:
                parsed_plan["risk_level"] = "low"
            
            return parsed_plan
            
        except Exception as e:
            self.logger.error(f"Failed to parse execution plan: {e}")
            raise
    
    def _classify_operation(self, step_name: str) -> str:
        """分类操作类型"""
        step_lower = step_name.lower()
        
        if any(keyword in step_lower for keyword in ["检查", "查看", "分析", "诊断"]):
            return "diagnosis"
        elif any(keyword in step_lower for keyword in ["重启", "启动", "停止"]):
            return "service_control"
        elif any(keyword in step_lower for keyword in ["配置", "修改", "更新"]):
            return "configuration"
        elif any(keyword in step_lower for keyword in ["扩容", "缩容", "增加"]):
            return "scaling"
        else:
            return "general"
    
    def _estimate_operation_time(self, step_name: str) -> int:
        """估计操作时间（秒）"""
        operation_type = self._classify_operation(step_name)
        
        time_estimates = {
            "diagnosis": 60,
            "service_control": 30,
            "configuration": 120,
            "scaling": 300,
            "general": 90
        }
        
        return time_estimates.get(operation_type, 90)
    
    def _get_required_permissions(self, step_name: str) -> List[str]:
        """获取所需权限"""
        operation_type = self._classify_operation(step_name)
        
        permission_map = {
            "diagnosis": ["read"],
            "service_control": ["admin", "service_manage"],
            "configuration": ["admin", "config_write"],
            "scaling": ["admin", "resource_manage"],
            "general": ["read", "write"]
        }
        
        return permission_map.get(operation_type, ["read"])
    
    def _check_rollback_possibility(self, step_name: str) -> bool:
        """检查是否可回滚"""
        operation_type = self._classify_operation(step_name)
        
        # 诊断操作通常不需要回滚
        if operation_type == "diagnosis":
            return True
        # 配置和服务控制可以回滚
        elif operation_type in ["configuration", "service_control"]:
            return True
        # 扩容操作较难回滚
        elif operation_type == "scaling":
            return False
        
        return True
    
    async def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行具体步骤"""
        try:
            step_name = step["name"]
            operation_type = step["operation_type"]
            
            # 模拟执行时间
            estimated_time = step["estimated_time"]
            actual_time = estimated_time + (-10 + 20 * (hash(step_name) % 100) / 100)  # 添加一些随机性
            
            # 模拟执行延迟
            await asyncio.sleep(min(2, actual_time / 30))  # 快速模拟
            
            # 根据操作类型模拟不同的结果
            if operation_type == "diagnosis":
                result = {
                    "output": f"诊断完成: 发现 {hash(step_name) % 3} 个潜在问题",
                    "data": {
                        "issues_found": hash(step_name) % 3,
                        "system_health": "良好" if hash(step_name) % 2 == 0 else "需要关注"
                    }
                }
            elif operation_type == "service_control":
                result = {
                    "output": f"服务操作完成: {step_name}",
                    "data": {
                        "service_status": "运行中",
                        "restart_time": f"{actual_time:.1f}秒"
                    }
                }
            elif operation_type == "configuration":
                result = {
                    "output": f"配置更新完成: {step_name}",
                    "data": {
                        "config_version": f"v{hash(step_name) % 10 + 1}.0",
                        "changes_applied": hash(step_name) % 5 + 1
                    }
                }
            elif operation_type == "scaling":
                result = {
                    "output": f"资源扩容完成: {step_name}",
                    "data": {
                        "new_capacity": f"{hash(step_name) % 5 + 2} 实例",
                        "scaling_time": f"{actual_time:.1f}秒"
                    }
                }
            else:
                result = {
                    "output": f"操作完成: {step_name}",
                    "data": {}
                }
            
            # 模拟成功/失败概率
            mock_op = self.mock_operations.get(operation_type, {"success_rate": 0.9})
            success = hash(step_name) % 100 < (mock_op["success_rate"] * 100)
            
            return {
                "step_name": step_name,
                "operation_type": operation_type,
                "success": success,
                "actual_time": actual_time,
                "result": result,
                "error": None if success else f"操作失败: {step_name}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to execute step: {e}")
            raise
    
    async def _verify_result(
        self,
        step: Dict[str, Any],
        step_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证执行结果"""
        try:
            verification = {
                "success": step_result["success"],
                "message": "",
                "metrics": {},
                "next_steps": []
            }
            
            if step_result["success"]:
                verification["message"] = f"步骤 '{step['name']}' 执行成功"
                
                # 根据操作类型添加验证信息
                operation_type = step["operation_type"]
                
                if operation_type == "diagnosis":
                    issues = step_result["result"]["data"].get("issues_found", 0)
                    if issues > 0:
                        verification["next_steps"].append(f"发现 {issues} 个问题，建议进一步处理")
                    else:
                        verification["message"] += "，系统状态良好"
                
                elif operation_type == "service_control":
                    verification["metrics"]["restart_time"] = step_result["result"]["data"].get("restart_time", "未知")
                    verification["message"] += "，服务已正常启动"
                
                elif operation_type == "configuration":
                    changes = step_result["result"]["data"].get("changes_applied", 0)
                    verification["metrics"]["changes_count"] = changes
                    verification["message"] += f"，应用了 {changes} 项配置更改"
                
                elif operation_type == "scaling":
                    capacity = step_result["result"]["data"].get("new_capacity", "未知")
                    verification["metrics"]["new_capacity"] = capacity
                    verification["message"] += f"，新容量: {capacity}"
            
            else:
                verification["message"] = f"步骤 '{step['name']}' 执行失败: {step_result.get('error', '未知错误')}"
                verification["next_steps"].append("检查错误原因并重试")
                
                if step["rollback_possible"]:
                    verification["next_steps"].append("考虑回滚操作")
            
            return verification
            
        except Exception as e:
            self.logger.error(f"Failed to verify result: {e}")
            raise
    
    async def _generate_report(
        self,
        parsed_plan: Dict[str, Any],
        step_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成执行报告"""
        try:
            successful_steps = sum(1 for result in step_results if result["success"])
            failed_steps = len(step_results) - successful_steps
            
            report = {
                "plan_id": parsed_plan["plan_id"],
                "execution_time": datetime.utcnow().isoformat(),
                "total_steps": len(step_results),
                "successful_steps": successful_steps,
                "failed_steps": failed_steps,
                "overall_success": failed_steps == 0,
                "total_time": sum(result["actual_time"] for result in step_results),
                "step_details": step_results,
                "summary": "",
                "recommendations": []
            }
            
            # 生成总结
            if report["overall_success"]:
                report["summary"] = f"执行计划成功完成，共执行 {report['total_steps']} 个步骤"
            else:
                report["summary"] = f"执行计划部分完成，{successful_steps} 个步骤成功，{failed_steps} 个步骤失败"
            
            # 生成建议
            if failed_steps > 0:
                report["recommendations"].append("检查失败步骤的错误原因")
                report["recommendations"].append("考虑重试失败的操作")
            
            if report["total_time"] > parsed_plan.get("estimated_time", 0) * 1.5:
                report["recommendations"].append("操作耗时超出预期，建议优化流程")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate report: {e}")
            raise
    
    def _format_execution_report(self, report: Dict[str, Any]) -> str:
        """格式化执行报告"""
        try:
            output = []
            output.append("## 执行报告")
            output.append("")
            output.append(f"**计划ID**: {report['plan_id']}")
            output.append(f"**执行时间**: {report['execution_time']}")
            output.append(f"**总体状态**: {'✅ 成功' if report['overall_success'] else '❌ 部分失败'}")
            output.append("")
            
            # 统计信息
            output.append("### 执行统计")
            output.append(f"- 总步骤数: {report['total_steps']}")
            output.append(f"- 成功步骤: {report['successful_steps']}")
            output.append(f"- 失败步骤: {report['failed_steps']}")
            output.append(f"- 总耗时: {report['total_time']:.1f} 秒")
            output.append("")
            
            # 步骤详情
            output.append("### 步骤详情")
            for i, step_result in enumerate(report["step_details"], 1):
                status = "✅" if step_result["success"] else "❌"
                output.append(f"{i}. {status} {step_result['step_name']} ({step_result['actual_time']:.1f}s)")
                
                if not step_result["success"] and step_result["error"]:
                    output.append(f"   错误: {step_result['error']}")
            output.append("")
            
            # 总结和建议
            output.append("### 总结")
            output.append(report["summary"])
            
            if report["recommendations"]:
                output.append("")
                output.append("### 建议")
                for rec in report["recommendations"]:
                    output.append(f"- {rec}")
            
            return "\n".join(output)
            
        except Exception as e:
            self.logger.error(f"Failed to format execution report: {e}")
            return "执行报告格式化失败"