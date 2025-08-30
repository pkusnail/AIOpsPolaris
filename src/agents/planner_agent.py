"""
规划智能体
负责任务分解和执行计划制定
"""

from typing import Dict, Any, List, Optional
import json
import re
from datetime import datetime

from .base_agent import BaseAgent, AgentType, AgentState, AgentMessage, MessageType, ToolAgent
from ..services.search_service import SearchService
from config.settings import settings

import logging
logger = logging.getLogger(__name__)


class PlannerAgent(ToolAgent):
    """规划智能体"""
    
    def __init__(self, llm_service=None):
        super().__init__(
            agent_id="planner",
            agent_type=AgentType.PLANNER,
            name="规划智能体",
            description="负责分析用户问题并制定解决方案的执行计划",
            max_steps=5
        )
        
        self.llm_service = llm_service
        self.search_service = None
        
        # 注册工具
        self._register_tools()
        
        # 规划模板
        self.planning_templates = {
            "troubleshooting": {
                "pattern": r"(故障|问题|错误|异常|失败|不工作|无法|报警)",
                "steps": [
                    "问题确认和信息收集",
                    "相关文档和案例搜索", 
                    "根因分析",
                    "解决方案制定",
                    "实施建议"
                ]
            },
            "optimization": {
                "pattern": r"(优化|提升|改进|性能|效率|加速)",
                "steps": [
                    "现状分析",
                    "性能指标收集",
                    "最佳实践搜索",
                    "优化方案设计",
                    "实施计划"
                ]
            },
            "deployment": {
                "pattern": r"(部署|发布|上线|安装|配置)",
                "steps": [
                    "部署需求分析",
                    "环境准备清单",
                    "部署步骤规划",
                    "风险评估",
                    "回滚方案"
                ]
            },
            "monitoring": {
                "pattern": r"(监控|告警|日志|指标|观测)",
                "steps": [
                    "监控需求分析",
                    "指标定义",
                    "监控工具选择",
                    "告警策略设计",
                    "仪表盘设置"
                ]
            },
            "general": {
                "pattern": r".*",
                "steps": [
                    "需求理解",
                    "信息收集",
                    "方案制定",
                    "执行计划"
                ]
            }
        }
    
    def _register_tools(self):
        """注册规划工具"""
        self.register_tool(
            "analyze_query",
            self._analyze_query,
            "分析用户查询并识别问题类型"
        )
        
        self.register_tool(
            "create_plan",
            self._create_plan,
            "根据问题类型创建执行计划"
        )
        
        self.register_tool(
            "search_relevant_docs",
            self._search_relevant_docs,
            "搜索相关文档和知识"
        )
    
    async def process(self, state: AgentState) -> AgentState:
        """处理规划逻辑"""
        try:
            # 获取用户消息
            user_query = state.context.get("user_message", "")
            if not user_query:
                raise ValueError("No user message found in context")
            
            # 步骤1: 分析查询
            if state.current_step == 0:
                analysis_result = await self.use_tool("analyze_query", user_query)
                
                thought_msg = AgentMessage(
                    type=MessageType.THOUGHT,
                    content=f"分析用户查询: {user_query}",
                    agent_id=self.agent_id
                )
                state.add_message(thought_msg)
                
                if analysis_result["success"]:
                    analysis = analysis_result["result"]
                    state.context["query_analysis"] = analysis
                    
                    action_msg = AgentMessage(
                        type=MessageType.ACTION,
                        content=f"识别问题类型: {analysis['problem_type']}, 关键词: {', '.join(analysis['keywords'])}",
                        agent_id=self.agent_id
                    )
                    state.add_message(action_msg)
                else:
                    return await self.handle_error(state, Exception(analysis_result["error"]))
            
            # 步骤2: 搜索相关文档
            elif state.current_step == 1:
                search_result = await self.use_tool("search_relevant_docs", user_query)
                
                if search_result["success"]:
                    relevant_docs = search_result["result"]
                    state.context["relevant_docs"] = relevant_docs
                    
                    action_msg = AgentMessage(
                        type=MessageType.ACTION,
                        content=f"找到 {len(relevant_docs)} 个相关文档",
                        agent_id=self.agent_id
                    )
                    state.add_message(action_msg)
                else:
                    # 搜索失败不是致命错误，继续处理
                    state.context["relevant_docs"] = []
                    
                    observation_msg = AgentMessage(
                        type=MessageType.OBSERVATION,
                        content="未找到相关文档，将基于通用知识制定计划",
                        agent_id=self.agent_id
                    )
                    state.add_message(observation_msg)
            
            # 步骤3: 创建执行计划
            elif state.current_step == 2:
                analysis = state.context.get("query_analysis", {})
                relevant_docs = state.context.get("relevant_docs", [])
                
                plan_result = await self.use_tool("create_plan", analysis, relevant_docs)
                
                if plan_result["success"]:
                    execution_plan = plan_result["result"]
                    state.context["execution_plan"] = execution_plan
                    
                    # 格式化计划输出
                    plan_summary = self._format_plan(execution_plan)
                    
                    answer_msg = AgentMessage(
                        type=MessageType.ANSWER,
                        content=plan_summary,
                        agent_id=self.agent_id,
                        metadata={"execution_plan": execution_plan}
                    )
                    state.add_message(answer_msg)
                    
                    # 标记完成
                    state.is_complete = True
                else:
                    return await self.handle_error(state, Exception(plan_result["error"]))
            
            return state
            
        except Exception as e:
            return await self.handle_error(state, e)
    
    async def _analyze_query(self, query: str) -> Dict[str, Any]:
        """分析用户查询"""
        try:
            # 确定问题类型
            problem_type = "general"
            for template_name, template in self.planning_templates.items():
                if template_name != "general" and re.search(template["pattern"], query, re.IGNORECASE):
                    problem_type = template_name
                    break
            
            # 提取关键词
            keywords = self._extract_keywords(query)
            
            # 确定优先级
            priority = self._determine_priority(query)
            
            # 估计复杂度
            complexity = self._estimate_complexity(query)
            
            return {
                "problem_type": problem_type,
                "keywords": keywords,
                "priority": priority,
                "complexity": complexity,
                "original_query": query
            }
            
        except Exception as e:
            self.logger.error(f"Failed to analyze query: {e}")
            raise
    
    def _extract_keywords(self, query: str) -> List[str]:
        """提取关键词"""
        # 运维相关关键词
        tech_keywords = [
            "cpu", "内存", "磁盘", "网络", "数据库", "服务", "容器", "kubernetes",
            "mysql", "redis", "nginx", "apache", "docker", "监控", "日志",
            "性能", "优化", "故障", "报警", "部署", "配置"
        ]
        
        keywords = []
        query_lower = query.lower()
        
        for keyword in tech_keywords:
            if keyword in query_lower:
                keywords.append(keyword)
        
        return keywords
    
    def _determine_priority(self, query: str) -> str:
        """确定优先级"""
        high_priority_patterns = [
            r"(紧急|严重|宕机|无法访问|生产环境|critical|urgent)",
            r"(用户反馈|客户投诉|业务影响)"
        ]
        
        medium_priority_patterns = [
            r"(异常|错误|警告|慢|延迟)",
            r"(优化|改进|升级)"
        ]
        
        query_lower = query.lower()
        
        for pattern in high_priority_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return "high"
        
        for pattern in medium_priority_patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return "medium"
        
        return "low"
    
    def _estimate_complexity(self, query: str) -> str:
        """估计复杂度"""
        complexity_indicators = {
            "high": [
                "架构", "重构", "迁移", "集群", "分布式",
                "multi", "cluster", "architecture"
            ],
            "medium": [
                "配置", "部署", "优化", "监控", "集成",
                "config", "deploy", "optimize", "integrate"
            ]
        }
        
        query_lower = query.lower()
        
        for level, indicators in complexity_indicators.items():
            for indicator in indicators:
                if indicator in query_lower:
                    return level
        
        return "low"
    
    async def _search_relevant_docs(self, query: str) -> List[Dict[str, Any]]:
        """搜索相关文档"""
        try:
            if not self.search_service:
                # 如果没有搜索服务，返回空结果
                return []
            
            search_result = await self.search_service.hybrid_search(
                query=query,
                search_type="hybrid",
                limit=5
            )
            
            return search_result.get("results", [])
            
        except Exception as e:
            self.logger.error(f"Failed to search relevant docs: {e}")
            return []
    
    async def _create_plan(
        self,
        analysis: Dict[str, Any],
        relevant_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """创建执行计划"""
        try:
            problem_type = analysis.get("problem_type", "general")
            template = self.planning_templates[problem_type]
            
            # 基础计划步骤
            plan_steps = []
            for i, step_name in enumerate(template["steps"]):
                step = {
                    "step_number": i + 1,
                    "name": step_name,
                    "description": self._generate_step_description(step_name, analysis),
                    "estimated_time": self._estimate_step_time(step_name),
                    "required_tools": self._get_required_tools(step_name),
                    "success_criteria": self._define_success_criteria(step_name)
                }
                plan_steps.append(step)
            
            # 添加相关文档信息
            if relevant_docs:
                reference_step = {
                    "step_number": 0,
                    "name": "参考资料",
                    "description": "查阅相关文档和最佳实践",
                    "references": [
                        {
                            "title": doc.get("title", ""),
                            "source": doc.get("source", ""),
                            "relevance_score": doc.get("score", 0.0)
                        }
                        for doc in relevant_docs[:3]
                    ]
                }
                plan_steps.insert(0, reference_step)
            
            execution_plan = {
                "plan_id": f"plan_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "problem_type": problem_type,
                "priority": analysis.get("priority", "medium"),
                "complexity": analysis.get("complexity", "medium"),
                "estimated_total_time": sum(step.get("estimated_time", 30) for step in plan_steps),
                "steps": plan_steps,
                "created_at": datetime.utcnow().isoformat(),
                "metadata": {
                    "keywords": analysis.get("keywords", []),
                    "original_query": analysis.get("original_query", "")
                }
            }
            
            return execution_plan
            
        except Exception as e:
            self.logger.error(f"Failed to create plan: {e}")
            raise
    
    def _generate_step_description(self, step_name: str, analysis: Dict[str, Any]) -> str:
        """生成步骤描述"""
        descriptions = {
            "问题确认和信息收集": f"确认问题详情，收集相关的系统信息、错误日志和性能指标",
            "相关文档和案例搜索": "搜索知识库中的相关文档、最佳实践和类似问题的解决方案",
            "根因分析": "基于收集的信息和历史案例，分析问题的根本原因",
            "解决方案制定": "制定具体的解决方案，包括操作步骤和预期效果",
            "实施建议": "提供实施建议，包括风险评估和回滚计划",
            "现状分析": "分析当前系统状态，识别性能瓶颈和改进机会",
            "性能指标收集": "收集相关的性能指标和监控数据",
            "最佳实践搜索": "查找行业最佳实践和优化方案",
            "优化方案设计": "设计具体的优化方案和实施计划",
            "实施计划": "制定详细的实施计划和时间安排"
        }
        
        return descriptions.get(step_name, f"执行{step_name}相关任务")
    
    def _estimate_step_time(self, step_name: str) -> int:
        """估计步骤耗时（分钟）"""
        time_estimates = {
            "问题确认和信息收集": 15,
            "相关文档和案例搜索": 10,
            "根因分析": 20,
            "解决方案制定": 30,
            "实施建议": 15,
            "现状分析": 20,
            "性能指标收集": 15,
            "最佳实践搜索": 10,
            "优化方案设计": 45,
            "实施计划": 30
        }
        
        return time_estimates.get(step_name, 20)
    
    def _get_required_tools(self, step_name: str) -> List[str]:
        """获取步骤所需工具"""
        tool_requirements = {
            "问题确认和信息收集": ["日志查看工具", "系统监控工具"],
            "相关文档和案例搜索": ["知识库搜索", "文档检索"],
            "根因分析": ["日志分析工具", "性能分析工具"],
            "解决方案制定": ["配置管理工具", "部署工具"],
            "实施建议": ["风险评估工具", "变更管理工具"]
        }
        
        return tool_requirements.get(step_name, ["通用工具"])
    
    def _define_success_criteria(self, step_name: str) -> List[str]:
        """定义成功标准"""
        success_criteria = {
            "问题确认和信息收集": [
                "收集到完整的错误信息",
                "获得系统现状快照",
                "确认问题影响范围"
            ],
            "相关文档和案例搜索": [
                "找到相关的解决方案文档",
                "识别类似问题的处理方法",
                "收集最佳实践建议"
            ],
            "根因分析": [
                "识别出问题的根本原因",
                "理解问题产生的机制",
                "确定主要和次要因素"
            ],
            "解决方案制定": [
                "制定可行的解决方案",
                "评估方案的风险和收益",
                "准备详细的实施步骤"
            ]
        }
        
        return success_criteria.get(step_name, ["完成相关任务目标"])
    
    def _format_plan(self, plan: Dict[str, Any]) -> str:
        """格式化计划输出"""
        try:
            output = []
            output.append(f"## 执行计划 ({plan['plan_id']})")
            output.append("")
            output.append(f"**问题类型**: {plan['problem_type']}")
            output.append(f"**优先级**: {plan['priority']}")
            output.append(f"**复杂度**: {plan['complexity']}")
            output.append(f"**预计总时长**: {plan['estimated_total_time']} 分钟")
            output.append("")
            
            output.append("### 执行步骤")
            for step in plan['steps']:
                step_num = step['step_number']
                if step_num == 0:
                    output.append(f"**{step['name']}**:")
                    if 'references' in step:
                        for ref in step['references']:
                            output.append(f"- {ref['title']} (来源: {ref['source']}, 相关度: {ref['relevance_score']:.2f})")
                else:
                    output.append(f"**{step_num}. {step['name']}** ({step['estimated_time']}分钟)")
                    output.append(f"   {step['description']}")
                    
                    if step.get('success_criteria'):
                        output.append("   成功标准:")
                        for criteria in step['success_criteria']:
                            output.append(f"   - {criteria}")
                output.append("")
            
            return "\n".join(output)
            
        except Exception as e:
            self.logger.error(f"Failed to format plan: {e}")
            return "计划格式化失败"