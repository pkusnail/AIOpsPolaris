#!/usr/bin/env python3
"""
监控系统集成测试脚本
测试Prometheus指标收集和Grafana仪表盘
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, Any

# 服务端点配置
SERVICES = {
    "api": "http://localhost:8888",
    "prometheus": "http://localhost:9090",
    "grafana": "http://localhost:3000"
}

async def test_service_health(session: aiohttp.ClientSession, service_name: str, url: str) -> Dict[str, Any]:
    """测试服务健康状态"""
    try:
        async with session.get(f"{url}/health" if service_name == "api" else url) as response:
            if response.status == 200:
                if service_name == "api":
                    data = await response.json()
                    return {"status": "healthy", "details": data}
                else:
                    return {"status": "healthy", "details": "Service accessible"}
            else:
                return {"status": "unhealthy", "details": f"HTTP {response.status}"}
    except Exception as e:
        return {"status": "error", "details": str(e)}

async def test_prometheus_metrics(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """测试Prometheus指标收集"""
    try:
        # 测试API metrics端点
        async with session.get(f"{SERVICES['api']}/metrics") as response:
            if response.status == 200:
                metrics_data = await response.text()
                # 检查关键指标是否存在
                key_metrics = [
                    "aiops_http_requests_total",
                    "aiops_http_request_duration_seconds",
                    "aiops_system_info",
                    "aiops_memory_usage_bytes",
                    "aiops_cpu_usage_percent"
                ]
                
                found_metrics = []
                for metric in key_metrics:
                    if metric in metrics_data:
                        found_metrics.append(metric)
                
                return {
                    "status": "success",
                    "total_metrics": len(key_metrics),
                    "found_metrics": len(found_metrics),
                    "missing_metrics": [m for m in key_metrics if m not in found_metrics],
                    "sample_size": len(metrics_data)
                }
            else:
                return {"status": "error", "details": f"HTTP {response.status}"}
    except Exception as e:
        return {"status": "error", "details": str(e)}

async def test_prometheus_query(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """测试Prometheus查询API"""
    try:
        # 查询系统信息指标
        query_url = f"{SERVICES['prometheus']}/api/v1/query"
        params = {"query": "aiops_system_info"}
        
        async with session.get(query_url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    "status": "success",
                    "query_status": data.get("status"),
                    "result_type": data.get("data", {}).get("resultType"),
                    "results_count": len(data.get("data", {}).get("result", []))
                }
            else:
                return {"status": "error", "details": f"HTTP {response.status}"}
    except Exception as e:
        return {"status": "error", "details": str(e)}

async def test_grafana_datasource(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """测试Grafana数据源连接"""
    try:
        # Grafana API测试（使用默认admin用户）
        auth = aiohttp.BasicAuth("admin", "aiops123")
        
        async with session.get(f"{SERVICES['grafana']}/api/datasources", auth=auth) as response:
            if response.status == 200:
                datasources = await response.json()
                prometheus_ds = [ds for ds in datasources if ds.get("type") == "prometheus"]
                
                return {
                    "status": "success",
                    "total_datasources": len(datasources),
                    "prometheus_datasources": len(prometheus_ds),
                    "details": [{"name": ds.get("name"), "url": ds.get("url")} for ds in prometheus_ds]
                }
            else:
                return {"status": "error", "details": f"HTTP {response.status}"}
    except Exception as e:
        return {"status": "error", "details": str(e)}

async def simulate_api_traffic(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """模拟API流量以生成指标数据"""
    try:
        results = []
        
        # 模拟不同类型的请求
        test_requests = [
            ("GET", "/health"),
            ("GET", "/stats"),
            ("POST", "/search", {"query": "test search", "search_type": "hybrid", "limit": 5})
        ]
        
        for method, endpoint, data in test_requests:
            for i in range(3):  # 每个请求重复3次
                try:
                    url = f"{SERVICES['api']}{endpoint}"
                    if method == "GET":
                        async with session.get(url) as response:
                            status = response.status
                    else:
                        async with session.post(url, json=data) as response:
                            status = response.status
                    
                    results.append({"method": method, "endpoint": endpoint, "status": status})
                except Exception as e:
                    results.append({"method": method, "endpoint": endpoint, "error": str(e)})
                
                await asyncio.sleep(0.1)  # 短暂延迟
        
        return {"status": "success", "requests_sent": len(results), "results": results}
    except Exception as e:
        return {"status": "error", "details": str(e)}

async def main():
    """主测试函数"""
    print("🔍 AIOps Polaris 监控系统集成测试")
    print("=" * 50)
    
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        
        # 1. 测试服务健康状态
        print("\n1️⃣  测试服务健康状态...")
        for service_name, url in SERVICES.items():
            result = await test_service_health(session, service_name, url)
            status_icon = "✅" if result["status"] == "healthy" else "❌"
            print(f"   {status_icon} {service_name.upper()}: {result['status']}")
            if result["status"] != "healthy":
                print(f"      详情: {result['details']}")
        
        # 2. 生成一些API流量
        print("\n2️⃣  生成API流量以创建指标数据...")
        traffic_result = await simulate_api_traffic(session)
        if traffic_result["status"] == "success":
            print(f"   ✅ 成功发送 {traffic_result['requests_sent']} 个请求")
        else:
            print(f"   ❌ 流量生成失败: {traffic_result['details']}")
        
        # 等待指标更新
        print("   ⏳ 等待指标更新...")
        await asyncio.sleep(5)
        
        # 3. 测试Prometheus指标收集
        print("\n3️⃣  测试Prometheus指标收集...")
        metrics_result = await test_prometheus_metrics(session)
        if metrics_result["status"] == "success":
            print(f"   ✅ 找到 {metrics_result['found_metrics']}/{metrics_result['total_metrics']} 个关键指标")
            if metrics_result["missing_metrics"]:
                print(f"   ⚠️  缺失指标: {', '.join(metrics_result['missing_metrics'])}")
        else:
            print(f"   ❌ 指标收集测试失败: {metrics_result['details']}")
        
        # 4. 测试Prometheus查询
        print("\n4️⃣  测试Prometheus查询API...")
        query_result = await test_prometheus_query(session)
        if query_result["status"] == "success":
            print(f"   ✅ 查询成功，状态: {query_result['query_status']}")
            print(f"   📊 结果类型: {query_result['result_type']}, 结果数量: {query_result['results_count']}")
        else:
            print(f"   ❌ Prometheus查询失败: {query_result['details']}")
        
        # 5. 测试Grafana数据源
        print("\n5️⃣  测试Grafana数据源...")
        grafana_result = await test_grafana_datasource(session)
        if grafana_result["status"] == "success":
            print(f"   ✅ Grafana连接成功")
            print(f"   📈 总数据源: {grafana_result['total_datasources']}")
            print(f"   📈 Prometheus数据源: {grafana_result['prometheus_datasources']}")
            for ds in grafana_result["details"]:
                print(f"      - {ds['name']}: {ds['url']}")
        else:
            print(f"   ❌ Grafana测试失败: {grafana_result['details']}")
    
    print("\n🎯 测试完成！")
    print("\n📊 访问监控仪表盘:")
    print(f"   • API文档: {SERVICES['api']}/docs")
    print(f"   • API指标: {SERVICES['api']}/metrics")
    print(f"   • Prometheus: {SERVICES['prometheus']}")
    print(f"   • Grafana: {SERVICES['grafana']} (admin/aiops123)")

if __name__ == "__main__":
    asyncio.run(main())