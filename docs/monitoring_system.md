# AIOps Polaris 监控系统文档

## 监控系统概览 ✅

AIOps Polaris 已经配置了完整的监控系统，包括 **Prometheus 数据收集** 和 **Grafana 可视化仪表盘**。

### 🎯 监控目标

监控系统主要监控以下几个方面：

1. **系统资源**: CPU、内存、磁盘使用情况
2. **应用服务**: 各个微服务的健康状态
3. **API性能**: HTTP请求统计、响应时间、错误率
4. **LLM服务**: AI对话请求、响应时间、token统计
5. **数据库连接**: 连接池状态、查询性能

## 📊 监控指标详细清单

### 系统资源指标
| 指标名称 | 类型 | 描述 |
|---------|-----|------|
| `aiops_cpu_usage_percent` | Gauge | CPU使用百分比 |
| `aiops_memory_usage_bytes` | Gauge | 内存使用情况(按类型分组) |
| `aiops_disk_usage_bytes` | Gauge | 磁盘使用情况(按类型分组) |

**示例数据**:
- CPU: 2.2% 使用率
- 内存: 总计67GB，使用21GB，可用44GB
- 磁盘: 实时统计总量、已用、可用空间

### 服务状态指标
| 指标名称 | 类型 | 描述 |
|---------|-----|------|
| `aiops_service_status` | Gauge | 服务健康状态 (1=健康, 0=不健康) |
| `aiops_database_connections_active` | Gauge | 活跃数据库连接数 |

**监控的服务**:
- ✅ database (数据库服务)
- ✅ embedding (嵌入向量服务) 
- ✅ aiops_graph (知识图谱服务)
- ✅ llm (大语言模型服务)

### API性能指标
| 指标名称 | 类型 | 描述 |
|---------|-----|------|
| `aiops_http_requests_total` | Counter | HTTP请求总数(按端点、状态码分组) |
| `aiops_http_request_duration_seconds` | Histogram | HTTP请求响应时间 |
| `aiops_http_requests_in_progress` | Gauge | 正在处理的请求数 |
| `aiops_api_errors_total` | Counter | API错误总数(按端点、错误类型分组) |

### LLM服务指标
| 指标名称 | 类型 | 描述 |
|---------|-----|------|
| `aiops_llm_requests_total` | Counter | LLM请求总数(按提供商、状态分组) |
| `aiops_llm_request_duration_seconds` | Histogram | LLM请求响应时间分布 |
| `aiops_llm_tokens_total` | Counter | 处理的token总数(按输入/输出分组) |

**支持的LLM提供商**:
- ✅ openai (OpenAI GPT模型)
- ✅ claude (Anthropic Claude模型)
- ✅ local_vllm (本地vLLM服务)
- ✅ demo (演示模式)

## 🔧 监控系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    监控数据流                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐    /metrics    ┌──────────────────┐   │
│  │   API服务    │ ──────────────► │   Prometheus     │   │
│  │              │     (30s)       │   数据收集       │   │
│  │ 指标收集器   │                 │                  │   │
│  └──────────────┘                 └──────────────────┘   │
│                                           │              │
│                                           │              │
│                                           ▼              │
│                                   ┌──────────────────┐   │
│                                   │     Grafana      │   │
│                                   │   可视化仪表盘   │   │
│                                   │                  │   │
│                                   └──────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 🖥️ 访问监控系统

### Prometheus (数据查询)
- **URL**: http://localhost:9090
- **用途**: 原始指标查询、告警规则配置
- **无需认证**

### Grafana (可视化仪表盘)  
- **URL**: http://localhost:3000
- **登录**: admin / aiops123
- **仪表盘**: AIOps文件夹下

## 📈 监控仪表盘

### 主要仪表盘内容

1. **系统状态概览**
   - 健康服务总数
   - 各服务状态指示灯
   - 实时系统负载

2. **系统资源监控**
   - CPU使用率趋势图
   - 内存使用情况(已用/可用)
   - 磁盘空间使用饼图

3. **API性能分析**
   - 请求速率趋势 (requests/sec)
   - 响应时间分布
   - 错误率统计

4. **LLM服务监控**
   - LLM请求统计(按提供商)
   - 平均响应时间
   - Token使用量统计

5. **错误和异常追踪**
   - API错误详细表格
   - 错误类型分布
   - 服务故障历史

## 🚨 告警配置

### 推荐告警规则

```yaml
groups:
  - name: aiops_alerts
    rules:
      - alert: HighCPUUsage
        expr: aiops_cpu_usage_percent > 80
        for: 5m
        annotations:
          summary: "CPU使用率过高: {{ $value }}%"
          
      - alert: LowMemoryAvailable
        expr: aiops_memory_usage_bytes{memory_type="available"} < 1073741824  # 1GB
        for: 5m
        annotations:
          summary: "可用内存不足: {{ $value | humanize }}B"
          
      - alert: ServiceDown
        expr: aiops_service_status == 0
        for: 1m
        annotations:
          summary: "服务 {{ $labels.service }} 不健康"
          
      - alert: HighLLMResponseTime
        expr: histogram_quantile(0.95, rate(aiops_llm_request_duration_seconds_bucket[5m])) > 10
        for: 5m
        annotations:
          summary: "LLM响应时间过长: {{ $value }}s"
```

## 🔍 监控数据示例

### 当前监控状态快照

```bash
# 系统资源
aiops_cpu_usage_percent: 2.2%
aiops_memory_usage_bytes{memory_type="used"}: 21.5GB
aiops_disk_usage_bytes{disk_type="free"}: 2.1GB

# 服务状态 (全部健康 ✅)
aiops_service_status{service="database"}: 1.0
aiops_service_status{service="embedding"}: 1.0  
aiops_service_status{service="aiops_graph"}: 1.0
aiops_service_status{service="llm"}: 1.0

# LLM使用情况
aiops_llm_requests_total{provider="openai",status="success"}: 3
aiops_llm_request_duration_seconds: 平均 1.2s
```

## 📝 监控运维指南

### 日常检查清单

1. **每日检查**:
   - [ ] 查看Grafana仪表盘总体状态
   - [ ] 确认所有服务状态为健康(绿色)
   - [ ] 检查是否有告警触发

2. **每周检查**:
   - [ ] 分析API性能趋势
   - [ ] 检查LLM使用量和成本
   - [ ] 清理过期的监控数据

3. **故障排除**:
   - [ ] 服务状态异常 → 检查对应容器日志
   - [ ] CPU/内存异常 → 检查系统负载和进程
   - [ ] LLM响应慢 → 检查API密钥和网络

### 监控数据保留策略

- **Prometheus**: 15天数据保留
- **Grafana**: 基于Prometheus数据源
- **日志**: Docker日志自动轮转

## 🎯 监控效果验证

### ✅ 验证清单

- [x] **Prometheus数据收集**: 30秒间隔收集所有指标
- [x] **系统资源监控**: CPU、内存、磁盘实时数据
- [x] **服务健康检查**: 4个核心服务状态监控
- [x] **API性能监控**: 请求量、响应时间、错误率
- [x] **LLM服务监控**: OpenAI请求成功率和响应时间
- [x] **Grafana仪表盘**: 多维度可视化展示
- [x] **数据持久化**: 指标数据正确存储和查询

### 🔧 问题排查

**常见问题**:

1. **Prometheus无数据** → 检查API服务的/metrics端点
2. **Grafana连接失败** → 验证Prometheus数据源配置
3. **指标缺失** → 确认服务正常运行并生成流量
4. **仪表盘空白** → 检查时间范围和查询语句

---

## 📊 总结

AIOps Polaris 的监控系统已经完全配置并正常运行，提供了：

1. **实时系统监控**: CPU 2.2%使用率，内存充足，服务全部健康
2. **完整的指标收集**: 系统资源、API性能、LLM服务全覆盖  
3. **可视化仪表盘**: Grafana多维度展示，便于运维分析
4. **告警机制**: 支持自定义告警规则和通知

监控系统正在持续收集数据，为系统运维和性能优化提供数据支持。