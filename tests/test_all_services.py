#!/usr/bin/env python3
"""
AIOps Polaris 综合服务测试脚本
测试所有核心组件的集成功能
"""

import asyncio
import subprocess
import sys
import time
from pathlib import Path

# 添加项目根目录到Python路径
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

async def run_test_script(script_name: str, description: str) -> dict:
    """运行测试脚本"""
    script_path = current_dir / script_name
    
    if not script_path.exists():
        return {
            "status": "error",
            "message": f"测试脚本不存在: {script_path}"
        }
    
    print(f"\n{'='*20} {description} {'='*20}")
    
    try:
        # 运行测试脚本
        process = await asyncio.create_subprocess_exec(
            "python3", str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            "status": "success" if process.returncode == 0 else "failed",
            "returncode": process.returncode,
            "stdout": stdout.decode(),
            "stderr": stderr.decode()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def check_docker_services() -> dict:
    """检查Docker服务状态"""
    try:
        result = subprocess.run(
            ["docker-compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        if result.returncode != 0:
            return {"status": "error", "message": "无法获取Docker服务状态"}
        
        import json
        services = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                try:
                    service = json.loads(line)
                    services.append({
                        "name": service.get("Name"),
                        "status": service.get("State"),
                        "health": service.get("Health", "N/A")
                    })
                except json.JSONDecodeError:
                    continue
        
        return {"status": "success", "services": services}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def check_gpu_status() -> dict:
    """检查GPU状态"""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu", 
             "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            gpu_info = result.stdout.strip().split(', ')
            return {
                "status": "available",
                "name": gpu_info[0],
                "memory_used": f"{gpu_info[1]}MB",
                "memory_total": f"{gpu_info[2]}MB",
                "utilization": f"{gpu_info[3]}%",
                "temperature": f"{gpu_info[4]}°C"
            }
        else:
            return {"status": "unavailable", "message": "NVIDIA GPU不可用"}
    except FileNotFoundError:
        return {"status": "unavailable", "message": "nvidia-smi命令未找到"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def main():
    """主测试函数"""
    print("🚀 AIOps Polaris 综合服务测试")
    print("=" * 60)
    print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 检查系统环境
    print("\n📋 系统环境检查")
    print("-" * 30)
    
    # GPU状态
    gpu_status = check_gpu_status()
    if gpu_status["status"] == "available":
        print(f"✅ GPU: {gpu_status['name']}")
        print(f"   显存: {gpu_status['memory_used']}/{gpu_status['memory_total']}")
        print(f"   利用率: {gpu_status['utilization']}")
        print(f"   温度: {gpu_status['temperature']}")
    else:
        print(f"⚠️  GPU: {gpu_status.get('message', 'GPU状态未知')}")
    
    # Docker服务状态
    docker_status = check_docker_services()
    if docker_status["status"] == "success":
        print("🐳 Docker服务状态:")
        for service in docker_status["services"]:
            status_icon = "✅" if service["status"] == "running" else "❌"
            health_info = f" ({service['health']})" if service["health"] != "N/A" else ""
            print(f"   {status_icon} {service['name']}: {service['status']}{health_info}")
    else:
        print(f"❌ Docker状态检查失败: {docker_status['message']}")
    
    # 2. 运行各项测试
    test_results = {}
    
    # 测试配置
    tests = [
        {
            "script": "test_database_integration.py",
            "name": "数据库集成测试",
            "description": "测试MySQL, Neo4j, Weaviate, Redis连接"
        },
        {
            "script": "test_monitoring_integration.py", 
            "name": "监控系统集成测试",
            "description": "测试Prometheus和Grafana监控系统"
        },
        {
            "script": "test_vllm_integration.py",
            "name": "vLLM服务集成测试", 
            "description": "测试vLLM模型推理接口"
        }
    ]
    
    for test_config in tests:
        script_name = test_config["script"]
        test_name = test_config["name"]
        description = test_config["description"]
        
        print(f"\n🔍 正在运行: {test_name}")
        print(f"   {description}")
        
        result = await run_test_script(script_name, test_name)
        test_results[test_name] = result
        
        if result["status"] == "success":
            print(f"   ✅ {test_name} - 通过")
        elif result["status"] == "failed":
            print(f"   ❌ {test_name} - 失败")
            if result.get("stderr"):
                print(f"   错误输出: {result['stderr'][:200]}...")
        else:
            print(f"   ⚠️  {test_name} - 错误: {result.get('message', '未知错误')}")
        
        # 显示测试输出（简化版）
        if result.get("stdout"):
            # 只显示关键输出行
            output_lines = result["stdout"].split('\n')
            key_lines = [line for line in output_lines if any(keyword in line for keyword in ['✅', '❌', '🎯', '📊', '成功', '失败', '错误'])]
            if key_lines:
                print("   关键输出:")
                for line in key_lines[-3:]:  # 只显示最后3行关键输出
                    print(f"     {line}")
    
    # 3. 测试总结
    print("\n📊 测试总结")
    print("=" * 30)
    
    total_tests = len(test_results)
    successful_tests = sum(1 for result in test_results.values() if result["status"] == "success")
    failed_tests = sum(1 for result in test_results.values() if result["status"] == "failed")
    error_tests = sum(1 for result in test_results.values() if result["status"] == "error")
    
    print(f"总测试数: {total_tests}")
    print(f"✅ 成功: {successful_tests}")
    print(f"❌ 失败: {failed_tests}")
    print(f"⚠️  错误: {error_tests}")
    print(f"成功率: {(successful_tests/total_tests*100):.1f}%")
    
    if successful_tests == total_tests:
        print("\n🎉 所有测试通过！AIOps Polaris系统运行正常。")
    elif successful_tests > 0:
        print(f"\n⚠️  部分测试通过。建议检查失败的组件。")
    else:
        print(f"\n❌ 所有测试失败。请检查服务配置和连接。")
    
    # 4. 生成测试报告文件
    report_file = current_dir / "test_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# AIOps Polaris 测试报告\n\n")
        f.write(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 系统环境\n\n")
        if gpu_status["status"] == "available":
            f.write(f"- GPU: {gpu_status['name']}\n")
            f.write(f"- 显存: {gpu_status['memory_used']}/{gpu_status['memory_total']}\n")
            f.write(f"- GPU利用率: {gpu_status['utilization']}\n\n")
        else:
            f.write(f"- GPU: {gpu_status.get('message', 'GPU状态未知')}\n\n")
        
        f.write("## Docker服务状态\n\n")
        if docker_status["status"] == "success":
            for service in docker_status["services"]:
                f.write(f"- {service['name']}: {service['status']}")
                if service['health'] != "N/A":
                    f.write(f" ({service['health']})")
                f.write("\n")
        f.write("\n")
        
        f.write("## 测试结果\n\n")
        for test_name, result in test_results.items():
            status_icon = "✅" if result["status"] == "success" else "❌" if result["status"] == "failed" else "⚠️"
            f.write(f"### {status_icon} {test_name}\n\n")
            f.write(f"状态: {result['status']}\n\n")
            if result.get("stdout"):
                f.write("```\n")
                f.write(result["stdout"][-1000:])  # 只保留最后1000个字符
                f.write("\n```\n\n")
        
        f.write("## 总结\n\n")
        f.write(f"- 总测试数: {total_tests}\n")
        f.write(f"- 成功: {successful_tests}\n")
        f.write(f"- 失败: {failed_tests}\n")
        f.write(f"- 错误: {error_tests}\n")
        f.write(f"- 成功率: {(successful_tests/total_tests*100):.1f}%\n")
    
    print(f"\n📄 详细测试报告已保存到: {report_file}")
    
    return test_results

if __name__ == "__main__":
    asyncio.run(main())