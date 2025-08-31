# AIOps Demo System Architecture

## 📋 系统概览

本系统是一个模拟的微服务架构，专门设计用于AIOps根因分析的演示和训练。系统包含5种不同类型的服务，分布在两个数据中心，支持多种调用链路。

## 🏗 服务架构图

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

## 📊 服务详细信息

### Service A - API Gateway
- **职责**: 系统入口点，负责请求路由和负载均衡
- **技术栈**: Spring Boot, Java 11
- **部署位置**: DC-East
- **端口**: 8080
- **调用比例**: 60% -> B, 40% -> C
- **关键配置**: 
  - Timeout: 5s (to B), 8s (to C)
  - Retry: 3次 (B), 2次 (C)

### Service B - Primary Business Logic
- **职责**: 主要业务逻辑处理
- **技术栈**: Java, Spring Boot
- **部署位置**: DC-East  
- **端口**: 8081
- **下游**: Service D 实例 (负载均衡)
- **关键配置**:
  - 连接池: 15个连接
  - JVM Heap: 2GB

### Service C - Secondary Business Logic  
- **职责**: 备选业务逻辑处理
- **技术栈**: Node.js, Express
- **部署位置**: DC-East
- **端口**: 8082
- **下游**: Service F (跨数据中心)
- **关键配置**:
  - Cross-DC timeout: 10s
  - Circuit breaker enabled

### Service D (D1, D2, D3) - Data Processing
- **职责**: 数据处理和持久化
- **技术栈**: Java, MyBatis
- **部署位置**: DC-East (3个实例)
- **端口**: 8083
- **数据库**: MySQL Primary (共享)
- **负载均衡权重**: 33%, 33%, 34%

### Service F - External Integration
- **职责**: 外部API集成和支付处理
- **技术栈**: Python Flask
- **部署位置**: DC-West
- **端口**: 8085  
- **外部依赖**: Payment Gateway API
- **数据库**: PostgreSQL Secondary

## 🔄 调用链路分析

### 主要调用路径

1. **Path A->B->D***: `用户请求 -> A -> B -> (D1|D2|D3) -> MySQL -> 响应`
   - **流量占比**: 60%
   - **预期延迟**: < 500ms
   - **故障模式**: CPU过载, 数据库连接池耗尽, 磁盘IO

2. **Path A->C->F**: `用户请求 -> A -> C -> F -> External API -> 响应`  
   - **流量占比**: 40%
   - **预期延迟**: < 800ms
   - **故障模式**: 跨DC网络, 外部API超时, 内存泄漏

## 🏢 基础设施架构

### 数据中心分布
- **DC-East**: Service A, B, C, D1-D3, MySQL
- **DC-West**: Service F, PostgreSQL

### 网络配置
- **DC-East Subnet**: 10.1.0.0/16
- **DC-West Subnet**: 10.2.0.0/16  
- **Inter-DC Latency**: 15-25ms
- **Cross-DC Bandwidth**: 1Gbps

### 数据库配置
- **MySQL Primary** (DC-East):
  - Version: 8.0
  - Connection Pool: 20
  - Used by: D1, D2, D3
  
- **PostgreSQL Secondary** (DC-West):
  - Version: 14.0
  - Connection Pool: 15  
  - Used by: F

## 🚨 常见故障模式

### 资源耗尽类
1. **CPU过载**: Service B处理复杂业务逻辑
2. **内存不足**: JVM heap不足或内存泄漏
3. **磁盘空间**: 日志文件或缓存积累
4. **磁盘IO**: 大量数据读写导致瓶颈

### 网络相关
1. **跨DC延迟**: C到F的网络问题
2. **连接超时**: 服务间网络中断
3. **网络分区**: DC间完全断连

### 依赖服务
1. **数据库连接池耗尽**: D服务实例连接过多
2. **外部API超时**: Payment Gateway响应慢
3. **负载均衡异常**: A服务路由配置错误

## 📊 监控指标

### 应用层监控
- **响应时间**: 95th percentile < 1s
- **错误率**: < 0.1%
- **QPS**: 峰值 1000 req/s
- **可用性**: > 99.9%

### 基础设施监控  
- **CPU使用率**: < 70%
- **内存使用率**: < 85%
- **磁盘IO等待**: < 20%
- **网络延迟**: DC内 < 5ms, 跨DC < 30ms

### 业务指标
- **成功交易率**: > 99.5%
- **支付成功率**: > 99.8%
- **用户会话成功率**: > 99.9%

## 🎯 AIOps使用场景

这个架构专门设计用于以下AIOps场景：

1. **多服务级联故障分析**
2. **负载均衡异常诊断**  
3. **跨数据中心网络问题**
4. **资源瓶颈识别和预测**
5. **外部依赖影响分析**
6. **分布式系统根因定位**

通过模拟真实的生产环境故障，为AI系统提供丰富的训练数据，提升自动化运维的智能化水平。