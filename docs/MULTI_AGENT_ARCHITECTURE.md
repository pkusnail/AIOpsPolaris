# Multi-Agent 智能RCA分析系统架构

## 🤖 Multi-Agent系统整体架构

```mermaid
graph TB
    subgraph "用户交互层"
        UI[Web UI 实时界面]
        POLL[长轮询机制<br/>500ms更新]
    end
    
    subgraph "任务管理层"
        TMgr[MultiAgentTaskManager<br/>任务状态管理]
        STREAM[EnhancedStreamingRCAService<br/>流式协调服务]
    end
    
    subgraph "Agent协作层"
        PLANNER[🧠 Planner Agent<br/>规划智能体]
        KNOWLEDGE[📚 Knowledge Agent<br/>知识智能体] 
        REASONING[🔍 Reasoning Agent<br/>推理智能体]
        EXECUTOR[⚡ Executor Agent<br/>执行智能体]
        MONITOR[📊 Monitor Agent<br/>监控智能体]
    end
    
    subgraph "服务支撑层"
        RAG[RAG搜索服务]
        NEO4J[Neo4j图谱服务]
        NER[NER实体识别]
        LLM[LLM推理服务]
    end
    
    subgraph "数据存储层"
        TASK_DATA[(任务状态数据)]
        PLAN_DATA[(规划会话数据)]
        EVIDENCE[(证据数据库)]
    end
    
    UI <--> POLL
    POLL <--> STREAM
    STREAM <--> TMgr
    
    STREAM --> PLANNER
    PLANNER --> KNOWLEDGE
    KNOWLEDGE --> REASONING  
    REASONING --> EXECUTOR
    EXECUTOR --> MONITOR
    
    KNOWLEDGE --> RAG
    KNOWLEDGE --> NEO4J
    KNOWLEDGE --> NER
    REASONING --> LLM
    EXECUTOR --> LLM
    
    TMgr --> TASK_DATA
    PLANNER --> PLAN_DATA
    KNOWLEDGE --> EVIDENCE
    
    style PLANNER fill:#e3f2fd
    style KNOWLEDGE fill:#e8f5e8
    style REASONING fill:#fff3e0
    style EXECUTOR fill:#fce4ec
    style STREAM fill:#f3e5f5
```

## 🔄 Agent协作工作流

```mermaid
sequenceDiagram
    participant User
    participant UI as Web UI
    participant Stream as StreamingService
    participant TaskMgr as TaskManager
    participant Planner as 🧠 Planner
    participant Knowledge as 📚 Knowledge  
    participant Reasoning as 🔍 Reasoning
    participant Executor as ⚡ Executor

    User->>UI: 提交问题: "service-b CPU异常"
    UI->>Stream: POST /chat/multi_agent
    Stream->>TaskMgr: create_multi_agent_task()
    TaskMgr-->>Stream: task_id: ma_task_123
    Stream-->>UI: 返回task_id和轮询接口
    
    par 用户轮询状态
        loop 每500ms
            UI->>Stream: GET /chat/multi_agent_status/{task_id}
            Stream->>TaskMgr: get_multi_agent_status()
            TaskMgr-->>Stream: 实时状态数据
            Stream-->>UI: Agent状态更新
        end
    and Agent协作执行
        Stream->>Planner: 开始规划阶段
        activate Planner
        Note over Planner: 分析问题制定5步执行计划<br/>1.实体识别 2.证据收集 3.拓扑分析<br/>4.根因推理 5.解决方案
        Planner->>TaskMgr: 添加规划步骤
        Planner-->>Stream: 规划完成
        deactivate Planner
        
        Stream->>Knowledge: 执行知识收集
        activate Knowledge
        Knowledge->>Knowledge: 1️⃣ NER实体识别
        Knowledge->>TaskMgr: 更新进度: 识别到service-b
        Knowledge->>Knowledge: 2️⃣ RAG混合搜索 
        Knowledge->>TaskMgr: 更新进度: 找到14条证据
        Knowledge->>Knowledge: 3️⃣ Neo4j拓扑查询
        Knowledge->>TaskMgr: 更新进度: 发现6个依赖关系
        Knowledge-->>Stream: 知识收集完成
        deactivate Knowledge
        
        Stream->>Reasoning: 执行根因分析
        activate Reasoning
        Note over Reasoning: 基于收集的证据进行多维度推理<br/>- CPU使用率时序分析<br/>- 服务依赖影响评估<br/>- 历史故障模式匹配
        Reasoning->>TaskMgr: 更新推理结论
        Reasoning-->>Stream: 根因分析完成
        deactivate Reasoning
        
        Stream->>Executor: 生成解决方案
        activate Executor
        Note over Executor: 基于根因分析生成具体方案<br/>1.立即监控CPU趋势<br/>2.检查服务配置<br/>3.分析依赖状态<br/>4.实施负载均衡
        Executor->>TaskMgr: 更新解决方案
        Executor-->>Stream: 方案生成完成
        deactivate Executor
        
        Stream->>TaskMgr: complete_multi_agent_task()
        TaskMgr->>TaskMgr: 整合最终结果
    end
    
    UI->>Stream: 获取最终结果
    Stream-->>UI: 完整分析报告
    UI-->>User: 显示Agent协作过程和最终结果
```

## 🧠 Planner Agent 详细设计

### 规划策略
```mermaid
flowchart TD
    INPUT[用户问题输入] --> ANALYZE[问题分析]
    
    ANALYZE --> TYPE{问题类型识别}
    
    TYPE -->|性能问题| PERF_PLAN[性能分析计划<br/>1.资源监控<br/>2.瓶颈识别<br/>3.优化建议]
    TYPE -->|故障问题| FAULT_PLAN[故障分析计划<br/>1.错误定位<br/>2.影响范围<br/>3.恢复方案] 
    TYPE -->|网络问题| NET_PLAN[网络分析计划<br/>1.连通性检查<br/>2.拓扑分析<br/>3.路由诊断]
    TYPE -->|综合问题| COMP_PLAN[综合分析计划<br/>1.多维度诊断<br/>2.关联分析<br/>3.系统性解决]
    
    PERF_PLAN --> STEPS[生成执行步骤]
    FAULT_PLAN --> STEPS
    NET_PLAN --> STEPS  
    COMP_PLAN --> STEPS
    
    STEPS --> ASSIGN[分配Agent任务]
    ASSIGN --> TRACK[建立追踪机制]
    
    style ANALYZE fill:#e3f2fd
    style STEPS fill:#e8f5e8
    style ASSIGN fill:#fff3e0
```

### 规划数据结构
```python
@dataclass
class PlanningSession:
    session_id: str          # plan_1, plan_2...
    plan_version: int        # 规划版本号
    plan_description: str    # 规划描述
    steps: List[PlanStep]    # 执行步骤列表
    status: str              # planning, executing, completed
    reasoning: str           # Planner推理过程
    
@dataclass  
class PlanStep:
    step_id: str            # step_1, step_2...
    step_name: str          # "实体识别", "证据收集"
    description: str        # 详细描述
    assigned_agent: str     # "knowledge", "reasoning" 
    dependencies: List[str] # 依赖的其他步骤
    status: str            # pending, executing, completed
```

## 📚 Knowledge Agent 详细设计

### 三阶段知识收集
```mermaid
stateDiagram-v2
    [*] --> EntityRecognition: 开始知识收集
    
    state EntityRecognition {
        [*] --> NER_Processing
        NER_Processing --> Entity_Extraction: NER模型处理
        Entity_Extraction --> Service_Identification: 提取服务名
        Service_Identification --> Component_Analysis: 识别组件
        Component_Analysis --> [*]: 输出实体列表
    }
    
    EntityRecognition --> EvidenceCollection: 实体识别完成
    
    state EvidenceCollection {
        [*] --> Hybrid_Search
        Hybrid_Search --> Vector_Search: 语义搜索
        Hybrid_Search --> BM25_Search: 关键词搜索
        Vector_Search --> Result_Merge: 结果合并
        BM25_Search --> Result_Merge
        Result_Merge --> Rerank: 混合重排序
        Rerank --> [*]: 输出证据列表
    }
    
    EvidenceCollection --> TopologyAnalysis: 证据收集完成
    
    state TopologyAnalysis {
        [*] --> Neo4j_Query
        Neo4j_Query --> Service_Relations: 查询服务关系
        Service_Relations --> Dependency_Analysis: 依赖分析
        Dependency_Analysis --> Impact_Assessment: 影响评估
        Impact_Assessment --> [*]: 输出拓扑数据
    }
    
    TopologyAnalysis --> [*]: 知识收集完成
```

### 证据数据结构
```python
# RAG搜索返回的证据结构
{
    "content": "[ERROR] service-b: CPU usage critical: 89%",
    "log_file": "incident_001_service_b_cpu_overload.log",
    "service_name": "service-b", 
    "source_type": "logs",
    "timestamp": "2025-08-20T14:29:33.123Z",
    "search_type": "hybrid",
    "score": 0.8489469289779663,
    "vector_score": 0.8489469289779663,
    "bm25_score": 0.0,
    "hybrid_score": 0.5093681573867798
}

# Neo4j拓扑数据结构
{
    "services": [
        {
            "name": "service-b",
            "datacenter": "DC-East", 
            "status": "active"
        }
    ],
    "relationships": [
        {
            "from_service": "service-a",
            "to_service": "service-b",
            "relation": "DEPENDS_ON",
            "relation_data": {
                "timeout": "10s",
                "weight": 0.8
            }
        }
    ]
}
```

## 🔍 Reasoning Agent 详细设计

### 推理逻辑链
```mermaid
graph TD
    EVIDENCE[收集到的证据] --> PATTERN[模式识别]
    
    PATTERN --> TIME_ANALYSIS[时间序列分析<br/>发现趋势和异常点]
    PATTERN --> CORRELATION[关联分析<br/>识别因果关系]  
    PATTERN --> SIMILARITY[相似度分析<br/>匹配历史案例]
    
    TIME_ANALYSIS --> SYNTHESIS[综合推理]
    CORRELATION --> SYNTHESIS
    SIMILARITY --> SYNTHESIS
    
    SYNTHESIS --> HYPOTHESIS[假设生成<br/>可能的根本原因]
    HYPOTHESIS --> VALIDATION[假设验证<br/>与证据交叉检验]
    VALIDATION --> CONFIDENCE[置信度计算<br/>量化分析可信度]
    CONFIDENCE --> ROOT_CAUSE[根本原因结论]
    
    style PATTERN fill:#e3f2fd
    style SYNTHESIS fill:#e8f5e8
    style ROOT_CAUSE fill:#ffebee
```

### 推理算法
```python
class ReasoningEngine:
    def analyze_temporal_patterns(self, evidence_list):
        """时间序列模式分析"""
        # 按时间排序证据
        sorted_evidence = sorted(evidence_list, key=lambda x: x['timestamp'])
        
        # 检测异常时间点
        anomaly_points = detect_anomalies(sorted_evidence)
        
        # 分析事件序列
        event_sequence = extract_event_sequence(sorted_evidence)
        
        return {
            "timeline": sorted_evidence,
            "anomalies": anomaly_points, 
            "sequence": event_sequence
        }
    
    def correlate_service_dependencies(self, topology_data, evidence):
        """服务依赖关联分析"""
        affected_services = extract_services_from_evidence(evidence)
        dependency_chain = build_dependency_chain(topology_data, affected_services)
        
        # 计算故障传播路径
        propagation_paths = calculate_failure_propagation(dependency_chain)
        
        return {
            "affected_services": affected_services,
            "dependency_impact": dependency_chain,
            "propagation": propagation_paths
        }
```

## ⚡ Executor Agent 详细设计

### 解决方案生成策略
```mermaid
flowchart TD
    ROOT_CAUSE[根本原因] --> SOLUTION_TYPE{解决方案类型}
    
    SOLUTION_TYPE -->|立即修复| IMMEDIATE[立即解决方案<br/>🚨 紧急响应]
    SOLUTION_TYPE -->|预防措施| PREVENTION[预防性方案<br/>🛡️ 长期防护] 
    SOLUTION_TYPE -->|监控加强| MONITORING[监控强化<br/>📊 观察预警]
    
    IMMEDIATE --> IMM_ACTIONS[具体行动项<br/>• 重启服务<br/>• 扩容资源<br/>• 切换备用]
    PREVENTION --> PREV_ACTIONS[预防措施<br/>• 配置优化<br/>• 架构改进<br/>• 流程规范]
    MONITORING --> MON_ACTIONS[监控措施<br/>• 添加指标<br/>• 设置告警<br/>• 定期检查]
    
    IMM_ACTIONS --> PRIORITY[优先级排序]
    PREV_ACTIONS --> PRIORITY
    MON_ACTIONS --> PRIORITY
    
    PRIORITY --> TIMELINE[时间规划<br/>立即执行 vs 计划执行]
    TIMELINE --> VALIDATION[方案验证<br/>可行性评估]
    VALIDATION --> OUTPUT[输出解决方案]
    
    style IMMEDIATE fill:#ffebee
    style PREVENTION fill:#e8f5e8  
    style MONITORING fill:#e3f2fd
    style OUTPUT fill:#fff3e0
```

### 解决方案数据结构
```python
@dataclass
class Solution:
    priority: int           # 1-5优先级
    description: str        # 解决方案描述
    type: str              # immediate, follow_up, monitoring
    category: str          # restart, scale, config, monitor
    estimated_time: str    # 预计执行时间
    risk_level: str        # low, medium, high
    dependencies: List[str] # 前置条件
    validation_steps: List[str] # 验证步骤
    
# 生成的解决方案示例
solutions = [
    {
        "priority": 1,
        "description": "立即监控CPU使用率趋势，识别高消耗进程",
        "type": "immediate", 
        "category": "monitor",
        "estimated_time": "5分钟",
        "risk_level": "low"
    },
    {
        "priority": 2, 
        "description": "检查服务配置，调整资源限制参数",
        "type": "immediate",
        "category": "config", 
        "estimated_time": "15分钟",
        "risk_level": "medium"
    }
]
```

## 📊 任务状态管理

### 状态机设计
```mermaid
stateDiagram-v2
    [*] --> queued: create_task()
    queued --> planning: start_planning()
    
    state planning {
        [*] --> analyzing
        analyzing --> plan_creating
        plan_creating --> plan_review
        plan_review --> [*]
    }
    
    planning --> executing: complete_planning()
    
    state executing {
        [*] --> knowledge_phase
        knowledge_phase --> reasoning_phase
        reasoning_phase --> execution_phase
        execution_phase --> [*]
    }
    
    executing --> completed: all_agents_done()
    executing --> failed: agent_error()
    executing --> interrupted: user_interrupt()
    
    interrupted --> executing: resume_task()
    failed --> [*]
    completed --> [*]
```

### 进度计算算法
```python
def calculate_overall_progress(task_info):
    """计算整体进度"""
    agents = task_info.agents
    total_agents = len(agents)
    
    # 每个Agent的权重
    agent_weights = {
        'planner': 0.15,      # 规划阶段 15%
        'knowledge': 0.40,    # 知识收集 40% (最重要)
        'reasoning': 0.25,    # 推理分析 25%
        'executor': 0.20      # 解决方案 20%
    }
    
    progress = 0.0
    for agent_id, agent in agents.items():
        weight = agent_weights.get(agent_id, 1.0/total_agents)
        
        if agent.status == 'done':
            progress += weight * 1.0
        elif agent.status == 'working':  
            progress += weight * agent.progress
        # waiting或failed状态不计入进度
    
    return min(progress, 1.0)
```

## 🔄 实时交互机制

### 长轮询实现
```javascript
// 前端轮询逻辑
class MultiAgentMonitor {
    constructor(taskId) {
        this.taskId = taskId;
        this.pollInterval = 500; // 500ms轮询间隔
        this.isPolling = false;
    }
    
    async startPolling() {
        this.isPolling = true;
        while (this.isPolling) {
            try {
                const status = await this.fetchTaskStatus();
                this.updateUI(status);
                
                if (status.status === 'completed' || status.status === 'failed') {
                    this.stopPolling();
                    break;
                }
                
                await this.delay(this.pollInterval);
            } catch (error) {
                console.error('轮询错误:', error);
                await this.delay(this.pollInterval * 2); // 错误时延长间隔
            }
        }
    }
    
    async fetchTaskStatus() {
        const response = await fetch(`/chat/multi_agent_status/${this.taskId}`);
        return await response.json();
    }
    
    updateUI(status) {
        // 更新Agent状态显示
        this.renderAgentStatus(status.agents);
        // 更新进度条
        this.updateProgressBar(status.overall_progress);
        // 显示中间结论
        this.displayIntermediateResults(status.intermediate_conclusions);
    }
}
```

### 用户中断机制
```python
async def interrupt_multi_agent_task(task_id: str):
    """用户中断任务执行"""
    success = multi_agent_task_manager.interrupt_task(
        task_id, 
        reason="用户请求中断"
    )
    
    # 取消正在运行的异步任务
    if task_id in streaming_service.running_tasks:
        async_task = streaming_service.running_tasks[task_id]
        if not async_task.done():
            async_task.cancel()
            try:
                await async_task
            except asyncio.CancelledError:
                logger.info(f"任务 {task_id} 已成功中断")
    
    return {"success": success, "message": "任务已中断"}
```

## 📈 性能优化与监控

### Agent协作性能指标
```yaml
执行效率指标:
  - 平均任务完成时间: < 30秒
  - Agent切换延迟: < 100ms
  - 并发任务处理能力: > 10个/分钟

协作质量指标:  
  - 规划准确率: > 90%
  - 证据收集完整性: > 95%
  - 推理逻辑一致性: > 90%
  - 解决方案适用性: > 85%

用户体验指标:
  - 状态更新及时性: < 500ms
  - 中断响应时间: < 1秒  
  - UI渲染流畅度: > 60fps
```

### 监控和调试工具
```python
# Agent性能监控
class AgentMonitor:
    def track_agent_performance(self, agent_id, start_time, end_time, result):
        duration = end_time - start_time
        success = result.get('success', False)
        
        metrics = {
            'agent_id': agent_id,
            'duration_ms': duration * 1000,
            'success': success,
            'timestamp': datetime.now(),
            'memory_usage': get_memory_usage(),
            'cpu_usage': get_cpu_usage()
        }
        
        self.store_metrics(metrics)
        self.alert_if_anomaly(metrics)
    
    def generate_performance_report(self, time_range):
        """生成Agent性能报告"""
        return {
            'agent_efficiency': self.calculate_efficiency_by_agent(),
            'bottleneck_analysis': self.identify_bottlenecks(), 
            'optimization_suggestions': self.suggest_optimizations()
        }
```

---

> 💡 **设计原则**:
> - **松耦合**: Agent之间通过消息传递协作，避免直接依赖
> - **可观察性**: 每个步骤都有详细的状态跟踪和日志记录  
> - **容错性**: 单个Agent失败不影响整体流程，支持重试和降级
> - **可扩展性**: 易于添加新的Agent类型和协作模式
> - **用户体验**: 实时状态反馈，支持用户交互控制