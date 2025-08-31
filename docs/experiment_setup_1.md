# AIOps根因分析实验环境设置 - 实验一

## 🎯 实验目标

构建一个完整的AIOps根因分析演示环境，用于训练和验证AI系统自动识别分布式系统故障根因的能力。通过模拟真实的微服务架构和故障场景，为LLM提供丰富的训练数据，提升自动化运维的智能化水平。

## 🏗 系统架构设计

### 微服务拓扑结构

```
                    [用户请求]
                         |
                   [Service A]
                    (API Gateway)
                    /          \
                  60%          40%
                  /              \
           [Service B]      [Service C]
         (Business Logic)   (Business Logic)
               |                    |
         Load Balanced         Cross-DC Call  
               |                    |
        /------+------\       [Service F]
       /       |       \    (External Integration)
  [Service D1] [Service D2] [Service D3]
 (Data Process) (Data Process) (Data Process)
       |           |           |
       +-----[MySQL DB]-------+
```

### 服务详细配置

| 服务 | 类型 | 技术栈 | 部署位置 | 端口 | 职责 |
|------|------|--------|----------|------|------|
| **Service A** | API Gateway | Spring Boot | DC-East | 8080 | 请求路由和负载均衡 |
| **Service B** | Business Logic | Java | DC-East | 8081 | 主要业务逻辑处理 |
| **Service C** | Business Logic | Node.js | DC-East | 8082 | 备选业务逻辑处理 |
| **Service D1-D3** | Data Processing | Java | DC-East | 8083 | 数据处理和持久化 |
| **Service F** | External Integration | Python Flask | DC-West | 8085 | 外部API集成和支付 |

### 调用链路设计

1. **主要路径 (60%流量)**: `A -> B -> (D1|D2|D3) -> MySQL`
   - 预期延迟: < 500ms
   - 故障模式: CPU过载、数据库连接池、磁盘IO

2. **备选路径 (40%流量)**: `A -> C -> F -> External API`
   - 预期延迟: < 800ms  
   - 故障模式: 跨DC网络、外部依赖、内存泄漏

### 基础设施配置

- **数据中心**: DC-East (主要服务), DC-West (Service F)
- **网络配置**: 
  - DC-East: 10.1.0.0/16
  - DC-West: 10.2.0.0/16
  - 跨DC延迟: 15-25ms
- **数据库**: MySQL Primary (DC-East), PostgreSQL (DC-West)
- **外部依赖**: Payment Gateway API (第三方)

## 🚨 故障场景设计

### 10个精心设计的Incident场景

| ID | 故障类型 | 主要根因 | 受影响服务 | 故障模式 | 训练价值 |
|----|---------|----------|------------|----------|----------|
| **INC-001** | CPU过载 | 低效算法 + 内存泄漏 | Service B | 资源耗尽 | 性能问题诊断 |
| **INC-002** | 磁盘IO瓶颈 | 日志轮转失效 | Service D1 | 存储问题 | 存储资源分析 |
| **INC-003** | 内存泄漏 | 连接池未释放 | Service F | JVM问题 | 内存管理诊断 |
| **INC-004** | 网络超时 | 交换机硬件故障 | Service C-F | 网络故障 | 网络层面分析 |
| **INC-005** | 连接池耗尽 | 配置不当 + 长查询 | Service D2 | 配置错误 | 数据库连接问题 |
| **INC-006** | 负载不均 | 路由配置错误 | Service A | 配置问题 | 负载均衡诊断 |
| **INC-007** | 磁盘空间满 | 清理任务失效 | Service D3 | 维护问题 | 磁盘空间管理 |
| **INC-008** | GC频繁 | 堆内存不足 | Service B | JVM调优 | 垃圾回收优化 |
| **INC-009** | 外部依赖 | 第三方API故障 | Service F | 依赖管理 | 外部服务分析 |
| **INC-010** | 网络分区 | 跨DC光纤中断 | Service C-F | 基础设施 | 网络分区处理 |

### 故障分类和模式

#### 1. 资源耗尽类 (40%)
- **CPU过载**: 算法效率、GC压力、线程阻塞
- **内存不足**: 内存泄漏、堆大小、对象积累  
- **磁盘问题**: IO瓶颈、空间不足、文件系统

#### 2. 配置错误类 (30%)
- **负载均衡**: 权重配置、路由规则
- **连接池**: 大小配置、超时设置、资源释放
- **参数调优**: JVM参数、应用配置

#### 3. 网络相关类 (20%)
- **跨DC通信**: 网络延迟、带宽限制、连接中断
- **网络分区**: 完全断连、部分可达、路由问题
- **DNS/连接**: 域名解析、端口占用、防火墙

#### 4. 外部依赖类 (10%)
- **第三方API**: 超时、限流、服务不可用
- **数据库**: 连接问题、查询性能、锁等待
- **基础设施**: 硬件故障、服务重启

## 📁 数据文件结构

```
AIOpsPolaris/
├── data/
│   ├── rca/                           # 根因分析案例数据
│   │   ├── incident_001.json         # Service B CPU过载详细分析
│   │   ├── incident_002.json         # Service D1 磁盘IO瓶颈
│   │   ├── incident_003.json         # Service F 内存泄漏
│   │   ├── incident_004.json         # Service C网络超时
│   │   ├── incident_005.json         # Service D2 连接池耗尽
│   │   ├── incident_006.json         # Service A 负载均衡异常
│   │   ├── incidents_007_010.json    # 其余4个incident合集
│   │   └── rca_analysis_patterns.md  # LLM训练的RCA分析模式
│   ├── logs/                          # 虚拟故障日志 (时间窗口: 故障前后1小时)
│   │   ├── incident_001_service_b_cpu_overload.log
│   │   ├── incident_002_d1_disk_io_bottleneck.log
│   │   ├── incident_010_network_partition.log
│   │   └── [其他incident日志待生成]
│   └── wiki/                          # 系统架构知识库
│       ├── service_architecture_kg.cypher  # Neo4j知识图谱脚本
│       └── system_architecture.md          # 详细架构文档
└── docs/
    └── experiment_setup_1.md         # 本文档
```

### Incident数据格式

每个incident包含以下结构化信息：

```json
{
  "incident_id": "INC-2025-001",
  "title": "描述性标题",
  "occurred_at": "故障开始时间",
  "resolved_at": "故障解决时间", 
  "duration_minutes": 135,
  "severity": "HIGH|MEDIUM|CRITICAL",
  "affected_services": ["受影响的服务列表"],
  "affected_call_paths": ["受影响的调用链"],
  "symptoms": {
    "user_facing": "用户感知的问题",
    "monitoring_alerts": ["监控告警列表"]
  },
  "root_cause": {
    "primary": "主要根因",
    "secondary": "次要因素"
  },
  "analysis_steps": ["分析步骤1", "分析步骤2", "..."],
  "resolution": "解决方案",
  "lessons_learned": ["经验教训"],
  "impact_metrics": {
    "requests_affected": 45000,
    "revenue_impact_usd": 12000,
    "customers_affected": 230
  }
}
```

## 🤖 LLM训练设计

### 根因分析通用方法论

```
症状识别 → 影响范围 → 时间线分析 → 依赖排查 → 根因确定 → 解决验证
```

### 核心分析模式

1. **资源耗尽模式**: CPU/内存/磁盘资源问题分析
2. **配置错误模式**: 负载均衡、连接池、参数配置问题
3. **网络故障模式**: 跨DC、网络分区、连接超时问题  
4. **依赖服务模式**: 外部API、数据库、基础设施问题

### LLM训练Prompt模板

#### 通用根因分析模板
```
你是一个专业的AIOps根因分析专家。请基于以下信息进行故障根因分析：

**系统架构**：
- 服务A（API网关）-> 服务B/C（业务逻辑）-> 服务D1/D2/D3/F（数据处理）
- 调用链：A->B->D* (60%) 和 A->C->F (40%)

**故障症状**：[具体症状]
**相关日志**：[时序日志]  
**系统指标**：[监控数据]

请按以下格式分析：
1. 症状总结
2. 影响范围  
3. 时间线分析
4. 假设验证
5. 根本原因
6. 解决方案
7. 预防措施
```

#### 特定故障类型模板
- **CPU过载分析**: 重点关注性能指标和代码变更
- **网络故障分析**: 重点关注连通性和基础设施
- **内存问题分析**: 重点关注JVM指标和对象泄漏
- **配置问题分析**: 重点关注参数设置和部署变更

### 训练数据特点

- **真实性**: 基于生产环境常见故障模式
- **多样性**: 覆盖不同故障类型和复杂度
- **完整性**: 包含完整的分析过程和解决方案
- **结构化**: 标准化的数据格式便于机器学习
- **时序性**: 包含故障演进的时间线信息

## 🔬 实验验证方法

### Neo4j知识图谱验证

```cypher
// 加载架构图谱
source data/wiki/service_architecture_kg.cypher

// 验证调用链路
MATCH (a:Service {name: 'service-a'})-[r:CALLS*1..3]->(target:Service)
RETURN a.name as source, target.name as destination, length(r) as hops;

// 验证依赖关系
MATCH (s:Service)-[r:DEPENDS_ON]->(dep)
RETURN s.name as service, type(r) as relationship, dep.name as dependency;
```

### 日志模式验证

检查日志是否包含完整的故障演进过程：
- **正常状态**: INFO级别，性能正常
- **故障征兆**: WARN增加，指标异常  
- **故障高峰**: ERROR/CRITICAL密集，服务不可用
- **恢复阶段**: 错误减少，性能恢复

### LLM分析质量评估

1. **准确性**: 根因分析是否指向真正问题源头
2. **完整性**: 是否考虑所有相关因素
3. **逻辑性**: 分析推理过程是否合理
4. **可操作性**: 解决方案是否具体可行
5. **预防性**: 是否提供避免复发建议

## 🚀 实验执行步骤

### 环境准备

1. **构建知识图谱**:
   ```bash
   # 连接Neo4j数据库
   neo4j-shell -file data/wiki/service_architecture_kg.cypher
   ```

2. **验证数据完整性**:
   ```bash
   # 检查文件结构
   ls -la data/rca/ data/logs/ data/wiki/
   
   # 验证JSON格式
   python -m json.tool data/rca/incident_001.json
   ```

### LLM训练准备

1. **准备训练数据**:
   - Incident结构化数据 (JSON格式)
   - 时序故障日志 (文本格式) 
   - 系统架构知识 (图谱 + 文档)
   - RCA分析模式 (方法论文档)

2. **设计Prompt工程**:
   - 通用分析模板
   - 特定故障类型模板
   - 日志模式识别模板
   - 结果验证模板

3. **建立评估基准**:
   - 人工专家分析结果作为Ground Truth
   - 分析准确性评分标准
   - 响应时间和效率指标

### 实验验证

1. **单一故障场景测试**: 使用每个incident独立测试LLM分析能力
2. **混合场景测试**: 组合多个相关故障测试复杂分析能力  
3. **实时分析测试**: 基于实时日志流进行在线分析
4. **对比基准测试**: 与人工专家分析结果进行对比验证

## 📊 预期成果

### 直接产出

1. **完整的AIOps演示环境**: 可运行的微服务系统架构
2. **丰富的故障案例库**: 10个不同类型的真实故障场景  
3. **结构化训练数据**: 为LLM优化的根因分析数据集
4. **专业分析模式**: 提取的故障分析方法论和最佳实践

### 能力验证

1. **自动故障识别**: AI能够从症状和日志中识别故障类型
2. **智能根因定位**: AI能够通过分析定位到真正的问题根源
3. **解决方案推荐**: AI能够基于根因提出合理的修复建议
4. **预防措施建议**: AI能够提供避免故障复发的预防性建议

### 技术突破

1. **多模态数据融合**: 整合日志、指标、架构等多种数据源
2. **时序模式识别**: 识别故障演进的时间序列模式
3. **因果关系推理**: 建立症状与根因之间的逻辑关系
4. **知识图谱应用**: 利用服务依赖图谱辅助分析

## 🔄 后续扩展计划

### 实验二: 实时故障检测
- 集成实时监控数据流
- 开发在线异常检测算法
- 建立自动告警和响应机制

### 实验三: 预测性维护  
- 基于历史数据预测故障风险
- 开发故障预防和容量规划能力
- 实现智能运维决策支持

### 实验四: 多租户场景
- 扩展到更复杂的微服务架构
- 支持多租户和多环境场景
- 验证大规模系统适用性

---

## 🎯 实验价值和意义

这个实验环境为AIOps领域提供了：

1. **标准化的测试平台**: 统一的故障场景和评估标准
2. **丰富的训练数据**: 高质量的根因分析案例库
3. **实用的分析方法**: 经过验证的故障诊断方法论
4. **可复现的实验**: 完整的环境配置和数据集
5. **产业化路径**: 面向实际生产环境的技术方案

通过这个实验，我们期望能够显著提升AIOps系统的智能化水平，为实现真正的自动化运维奠定技术基础。