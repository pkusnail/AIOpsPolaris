"""
推理智能体
负责分析推理和决策制定
"""

from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from .base_agent import BaseAgent, AgentType, AgentState, AgentMessage, MessageType, ToolAgent

import logging
logger = logging.getLogger(__name__)


class ReasoningAgent(ToolAgent):
    """推理智能体"""
    
    def __init__(self, llm_service=None):
        super().__init__(
            agent_id="reasoning",
            agent_type=AgentType.REASONING,
            name="推理智能体",
            description="负责分析问题、推理根因和制定决策",
            max_steps=4
        )
        
        self.llm_service = llm_service
        
        # 注册工具
        self._register_tools()
        
        # 推理规则
        self.reasoning_rules = {
            "cause_effect": {
                "patterns": [
                    ("CPU使用率高", ["进程占用", "负载增加", "资源不足"]),
                    ("内存泄露", ["程序bug", "资源未释放", "配置错误"]),
                    ("数据库连接失败", ["网络问题", "认证失败", "资源耗尽"]),
                    ("服务响应慢", ["网络延迟", "数据库慢查询", "资源竞争"])
                ]
            },
            "dependency": {
                "service_db": "服务依赖数据库",
                "api_service": "API依赖后端服务",
                "container_host": "容器依赖主机资源"
            }
        }
    
    def _register_tools(self):
        """注册推理工具"""
        self.register_tool(
            "analyze_symptoms",
            self._analyze_symptoms,
            "分析问题症状和模式"
        )
        
        self.register_tool(
            "infer_root_causes",
            self._infer_root_causes,
            "推理可能的根本原因"
        )
        
        self.register_tool(
            "evaluate_solutions",
            self._evaluate_solutions,
            "评估解决方案的可行性"
        )
        
        self.register_tool(
            "make_recommendation",
            self._make_recommendation,
            "制定最终建议"
        )
    
    async def process(self, state: AgentState) -> AgentState:
        """处理推理逻辑"""
        try:
            user_query = state.context.get("user_message", "")
            knowledge_summary = state.context.get("knowledge_summary", {})
            
            # 步骤1: 分析症状
            if state.current_step == 0:
                thought_msg = AgentMessage(
                    type=MessageType.THOUGHT,
                    content="开始分析问题症状和模式",
                    agent_id=self.agent_id
                )
                state.add_message(thought_msg)
                
                symptoms_result = await self.use_tool("analyze_symptoms", user_query, knowledge_summary)
                
                if symptoms_result["success"]:
                    symptoms = symptoms_result["result"]
                    state.context["symptoms_analysis"] = symptoms
                    
                    action_msg = AgentMessage(
                        type=MessageType.ACTION,
                        content=f"识别到 {len(symptoms['symptoms'])} 个症状特征",
                        agent_id=self.agent_id
                    )
                    state.add_message(action_msg)
                else:
                    return await self.handle_error(state, Exception(symptoms_result["error"]))
            
            # 步骤2: 推理根因
            elif state.current_step == 1:
                symptoms = state.context.get("symptoms_analysis", {})
                
                causes_result = await self.use_tool("infer_root_causes", symptoms, knowledge_summary)
                
                if causes_result["success"]:
                    root_causes = causes_result["result"]
                    state.context["root_causes"] = root_causes
                    
                    action_msg = AgentMessage(
                        type=MessageType.ACTION,
                        content=f"推理出 {len(root_causes['causes'])} 个可能根因",
                        agent_id=self.agent_id
                    )
                    state.add_message(action_msg)
                else:
                    return await self.handle_error(state, Exception(causes_result["error"]))
            
            # 步骤3: 评估解决方案
            elif state.current_step == 2:
                root_causes = state.context.get("root_causes", {})
                
                solutions_result = await self.use_tool("evaluate_solutions", root_causes, knowledge_summary)
                
                if solutions_result["success"]:
                    solutions = solutions_result["result"]
                    state.context["evaluated_solutions"] = solutions
                    
                    action_msg = AgentMessage(
                        type=MessageType.ACTION,
                        content=f"评估了 {len(solutions['solutions'])} 个解决方案",
                        agent_id=self.agent_id
                    )
                    state.add_message(action_msg)
                else:
                    return await self.handle_error(state, Exception(solutions_result["error"]))
            
            # 步骤4: 制定最终建议
            elif state.current_step == 3:
                symptoms = state.context.get("symptoms_analysis", {})
                root_causes = state.context.get("root_causes", {})
                solutions = state.context.get("evaluated_solutions", {})
                
                recommendation_result = await self.use_tool(
                    "make_recommendation",
                    symptoms,
                    root_causes,
                    solutions
                )
                
                if recommendation_result["success"]:
                    recommendation = recommendation_result["result"]
                    state.context["final_recommendation"] = recommendation
                    
                    # 格式化推理结果
                    reasoning_summary = self._format_reasoning_result(
                        symptoms, root_causes, solutions, recommendation
                    )
                    
                    answer_msg = AgentMessage(
                        type=MessageType.ANSWER,
                        content=reasoning_summary,
                        agent_id=self.agent_id,
                        metadata={
                            "symptoms_count": len(symptoms.get("symptoms", [])),
                            "causes_count": len(root_causes.get("causes", [])),
                            "solutions_count": len(solutions.get("solutions", [])),
                            "confidence": recommendation.get("confidence", 0.0)
                        }
                    )
                    state.add_message(answer_msg)
                    
                    state.is_complete = True
                else:
                    return await self.handle_error(state, Exception(recommendation_result["error"]))
            
            return state
            
        except Exception as e:
            return await self.handle_error(state, e)
    
    async def _analyze_symptoms(
        self,
        query: str,
        knowledge_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析问题症状"""
        try:
            symptoms = {
                "symptoms": [],
                "severity": "medium",
                "category": "unknown",
                "patterns": []
            }
            
            query_lower = query.lower()
            
            # 识别症状关键词
            symptom_keywords = {
                "performance": ["慢", "延迟", "卡顿", "timeout", "slow", "latency"],
                "error": ["错误", "异常", "失败", "error", "exception", "failure"],
                "resource": ["内存", "cpu", "磁盘", "network", "memory", "disk"],
                "availability": ["宕机", "无法访问", "down", "unavailable", "offline"]
            }
            
            identified_symptoms = []
            for category, keywords in symptom_keywords.items():
                for keyword in keywords:
                    if keyword in query_lower:
                        identified_symptoms.append({
                            "type": category,
                            "keyword": keyword,
                            "confidence": 0.8
                        })
            
            symptoms["symptoms"] = identified_symptoms
            
            # 确定严重程度
            high_severity_patterns = ["宕机", "无法访问", "生产环境", "紧急", "critical"]
            if any(pattern in query_lower for pattern in high_severity_patterns):
                symptoms["severity"] = "high"
            elif any(pattern in query_lower for pattern in ["错误", "异常", "失败"]):
                symptoms["severity"] = "medium"
            else:
                symptoms["severity"] = "low"
            
            # 确定问题类别
            if any(s["type"] == "performance" for s in identified_symptoms):
                symptoms["category"] = "performance"
            elif any(s["type"] == "error" for s in identified_symptoms):
                symptoms["category"] = "functional"
            elif any(s["type"] == "availability" for s in identified_symptoms):
                symptoms["category"] = "availability"
            else:
                symptoms["category"] = "general"
            
            return symptoms
            
        except Exception as e:
            self.logger.error(f"Failed to analyze symptoms: {e}")
            raise
    
    async def _infer_root_causes(
        self,
        symptoms: Dict[str, Any],
        knowledge_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """推理根本原因"""
        try:
            root_causes = {
                "causes": [],
                "reasoning_path": [],
                "confidence_scores": {}
            }
            
            # 基于症状推理可能原因
            for symptom in symptoms.get("symptoms", []):
                symptom_type = symptom["type"]
                
                # 使用推理规则
                if symptom_type == "performance":
                    possible_causes = [
                        {"cause": "资源不足", "confidence": 0.7, "type": "resource"},
                        {"cause": "数据库查询慢", "confidence": 0.6, "type": "database"},
                        {"cause": "网络延迟", "confidence": 0.5, "type": "network"}
                    ]
                elif symptom_type == "error":
                    possible_causes = [
                        {"cause": "配置错误", "confidence": 0.8, "type": "configuration"},
                        {"cause": "代码bug", "confidence": 0.6, "type": "software"},
                        {"cause": "依赖服务异常", "confidence": 0.7, "type": "dependency"}
                    ]
                elif symptom_type == "resource":
                    possible_causes = [
                        {"cause": "资源泄露", "confidence": 0.8, "type": "software"},
                        {"cause": "负载过高", "confidence": 0.7, "type": "capacity"},
                        {"cause": "配置不当", "confidence": 0.6, "type": "configuration"}
                    ]
                elif symptom_type == "availability":
                    possible_causes = [
                        {"cause": "服务崩溃", "confidence": 0.9, "type": "software"},
                        {"cause": "硬件故障", "confidence": 0.6, "type": "hardware"},
                        {"cause": "网络中断", "confidence": 0.5, "type": "network"}
                    ]
                else:
                    possible_causes = [
                        {"cause": "未知问题", "confidence": 0.3, "type": "unknown"}
                    ]
                
                root_causes["causes"].extend(possible_causes)
                root_causes["reasoning_path"].append({
                    "step": f"从症状 '{symptom['keyword']}' 推理",
                    "symptom_type": symptom_type,
                    "inferred_causes": [c["cause"] for c in possible_causes]
                })
            
            # 去重并排序
            unique_causes = {}
            for cause in root_causes["causes"]:
                cause_name = cause["cause"]
                if cause_name not in unique_causes:
                    unique_causes[cause_name] = cause
                else:
                    # 取较高的置信度
                    unique_causes[cause_name]["confidence"] = max(
                        unique_causes[cause_name]["confidence"],
                        cause["confidence"]
                    )
            
            root_causes["causes"] = list(unique_causes.values())
            root_causes["causes"].sort(key=lambda x: x["confidence"], reverse=True)
            
            return root_causes
            
        except Exception as e:
            self.logger.error(f"Failed to infer root causes: {e}")
            raise
    
    async def _evaluate_solutions(
        self,
        root_causes: Dict[str, Any],
        knowledge_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """评估解决方案"""
        try:
            solutions = {
                "solutions": [],
                "evaluation_criteria": ["feasibility", "impact", "risk", "time_cost"],
                "recommended_order": []
            }
            
            # 为每个根因生成解决方案
            for cause in root_causes.get("causes", []):
                cause_type = cause.get("type", "unknown")
                cause_name = cause["cause"]
                
                # 根据原因类型生成解决方案
                if cause_type == "resource":
                    cause_solutions = [
                        {
                            "solution": "增加系统资源配置",
                            "feasibility": 0.8,
                            "impact": 0.9,
                            "risk": 0.3,
                            "time_cost": 2,  # hours
                            "steps": ["评估资源需求", "申请资源扩容", "执行扩容操作", "验证效果"]
                        },
                        {
                            "solution": "优化资源使用效率",
                            "feasibility": 0.9,
                            "impact": 0.7,
                            "risk": 0.2,
                            "time_cost": 4,
                            "steps": ["分析资源使用", "识别优化点", "实施优化", "性能测试"]
                        }
                    ]
                elif cause_type == "configuration":
                    cause_solutions = [
                        {
                            "solution": "检查和修正配置",
                            "feasibility": 0.9,
                            "impact": 0.8,
                            "risk": 0.4,
                            "time_cost": 1,
                            "steps": ["备份现有配置", "检查配置文件", "修正错误配置", "重启服务"]
                        }
                    ]
                elif cause_type == "software":
                    cause_solutions = [
                        {
                            "solution": "修复软件问题",
                            "feasibility": 0.7,
                            "impact": 0.9,
                            "risk": 0.5,
                            "time_cost": 8,
                            "steps": ["代码审查", "定位bug", "修复代码", "测试验证", "发布更新"]
                        },
                        {
                            "solution": "重启相关服务",
                            "feasibility": 1.0,
                            "impact": 0.6,
                            "risk": 0.3,
                            "time_cost": 0.5,
                            "steps": ["准备重启", "重启服务", "验证服务状态"]
                        }
                    ]
                else:
                    cause_solutions = [
                        {
                            "solution": "进一步诊断和分析",
                            "feasibility": 1.0,
                            "impact": 0.5,
                            "risk": 0.1,
                            "time_cost": 2,
                            "steps": ["收集更多信息", "深入分析", "制定具体方案"]
                        }
                    ]
                
                # 添加原因信息到解决方案
                for solution in cause_solutions:
                    solution["target_cause"] = cause_name
                    solution["cause_confidence"] = cause["confidence"]
                    solution["overall_score"] = (
                        solution["feasibility"] * 0.3 +
                        solution["impact"] * 0.4 +
                        (1 - solution["risk"]) * 0.2 +
                        (1 - min(solution["time_cost"] / 24, 1)) * 0.1
                    ) * cause["confidence"]
                
                solutions["solutions"].extend(cause_solutions)
            
            # 按综合评分排序
            solutions["solutions"].sort(key=lambda x: x["overall_score"], reverse=True)
            
            # 生成推荐顺序
            solutions["recommended_order"] = [
                {
                    "rank": i + 1,
                    "solution": sol["solution"],
                    "score": sol["overall_score"],
                    "priority": "高" if sol["overall_score"] > 0.7 else "中" if sol["overall_score"] > 0.5 else "低"
                }
                for i, sol in enumerate(solutions["solutions"][:5])
            ]
            
            return solutions
            
        except Exception as e:
            self.logger.error(f"Failed to evaluate solutions: {e}")
            raise
    
    async def _make_recommendation(
        self,
        symptoms: Dict[str, Any],
        root_causes: Dict[str, Any],
        solutions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """制定最终建议"""
        try:
            recommendation = {
                "primary_recommendation": "",
                "alternative_options": [],
                "implementation_plan": [],
                "risk_assessment": "",
                "success_metrics": [],
                "confidence": 0.0
            }
            
            # 选择主要推荐方案
            if solutions["solutions"]:
                best_solution = solutions["solutions"][0]
                recommendation["primary_recommendation"] = best_solution["solution"]
                recommendation["implementation_plan"] = best_solution["steps"]
                recommendation["confidence"] = best_solution["overall_score"]
                
                # 风险评估
                if best_solution["risk"] > 0.7:
                    recommendation["risk_assessment"] = "高风险：建议在维护窗口执行"
                elif best_solution["risk"] > 0.4:
                    recommendation["risk_assessment"] = "中等风险：建议做好备份和回滚准备"
                else:
                    recommendation["risk_assessment"] = "低风险：可以考虑在业务时间执行"
                
                # 备选方案
                for solution in solutions["solutions"][1:4]:
                    recommendation["alternative_options"].append({
                        "solution": solution["solution"],
                        "reason": f"备选方案，综合评分 {solution['overall_score']:.2f}"
                    })
            
            # 成功指标
            if symptoms["category"] == "performance":
                recommendation["success_metrics"] = [
                    "响应时间恢复正常",
                    "CPU/内存使用率降低",
                    "错误率减少"
                ]
            elif symptoms["category"] == "availability":
                recommendation["success_metrics"] = [
                    "服务可正常访问",
                    "健康检查通过",
                    "监控告警清除"
                ]
            else:
                recommendation["success_metrics"] = [
                    "问题症状消失",
                    "系统运行稳定",
                    "相关指标恢复正常"
                ]
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Failed to make recommendation: {e}")
            raise
    
    def _format_reasoning_result(
        self,
        symptoms: Dict[str, Any],
        root_causes: Dict[str, Any],
        solutions: Dict[str, Any],
        recommendation: Dict[str, Any]
    ) -> str:
        """格式化推理结果"""
        try:
            output = []
            output.append("## 问题分析与推理")
            output.append("")
            
            # 症状分析
            output.append("### 症状分析")
            output.append(f"**问题类别**: {symptoms.get('category', 'unknown')}")
            output.append(f"**严重程度**: {symptoms.get('severity', 'unknown')}")
            
            if symptoms.get("symptoms"):
                output.append("**识别的症状**:")
                for symptom in symptoms["symptoms"]:
                    output.append(f"- {symptom['keyword']} ({symptom['type']}) - 置信度: {symptom['confidence']:.2f}")
            output.append("")
            
            # 根因分析
            output.append("### 根因分析")
            if root_causes.get("causes"):
                for i, cause in enumerate(root_causes["causes"][:3], 1):
                    output.append(f"{i}. **{cause['cause']}** (类型: {cause['type']}, 置信度: {cause['confidence']:.2f})")
            output.append("")
            
            # 解决方案推荐
            output.append("### 解决方案推荐")
            output.append(f"**主要建议**: {recommendation.get('primary_recommendation', '无')}")
            output.append(f"**置信度**: {recommendation.get('confidence', 0.0):.2f}")
            output.append(f"**风险评估**: {recommendation.get('risk_assessment', '未评估')}")
            output.append("")
            
            # 实施计划
            if recommendation.get("implementation_plan"):
                output.append("**实施步骤**:")
                for i, step in enumerate(recommendation["implementation_plan"], 1):
                    output.append(f"{i}. {step}")
                output.append("")
            
            # 成功指标
            if recommendation.get("success_metrics"):
                output.append("**成功指标**:")
                for metric in recommendation["success_metrics"]:
                    output.append(f"- {metric}")
                output.append("")
            
            # 备选方案
            if recommendation.get("alternative_options"):
                output.append("### 备选方案")
                for option in recommendation["alternative_options"]:
                    output.append(f"- {option['solution']}: {option['reason']}")
                output.append("")
            
            return "\n".join(output)
            
        except Exception as e:
            self.logger.error(f"Failed to format reasoning result: {e}")
            return "推理结果格式化失败"