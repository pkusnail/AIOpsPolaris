"""
测试API的RCA功能
验证通过web接口进行RCA分析
"""

import asyncio
import aiohttp
import json
from datetime import datetime


async def test_api_rca():
    """测试API的RCA功能"""
    print("🌐 测试API RCA功能...")
    
    # 测试场景
    test_queries = [
        "service-b CPU使用率过高导致响应超时，用户反馈页面加载缓慢",
        "database服务连接失败，多个服务无法访问数据库", 
        "请分析一下incident_001_service_b_cpu_overload.log中的问题"
    ]
    
    api_url = "http://localhost:8000"
    
    async with aiohttp.ClientSession() as session:
        # 先检查API是否可用
        try:
            async with session.get(f"{api_url}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"✅ API服务运行正常: {health_data['status']}")
                else:
                    print(f"❌ API服务异常: HTTP {response.status}")
                    return False
        except Exception as e:
            print(f"❌ 无法连接API服务: {e}")
            print("💡 请先启动API服务: uvicorn src.api.main:app --reload")
            return False
        
        # 测试RCA查询
        successful_queries = 0
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n📋 测试查询 {i}: {query[:50]}...")
            
            try:
                chat_data = {
                    "message": query,
                    "session_id": "test-rca-session"
                }
                
                async with session.post(
                    f"{api_url}/chat", 
                    json=chat_data,
                    timeout=30
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        response_text = result.get("response", "")
                        
                        print(f"✅ 查询成功")
                        print(f"   响应长度: {len(response_text)} 字符")
                        print(f"   LLM提供商: {result.get('llm_provider', 'unknown')}")
                        
                        # 检查响应是否包含RCA相关内容
                        rca_keywords = ["根因", "原因", "建议", "解决", "分析", "问题", "症状"]
                        keyword_count = sum(1 for keyword in rca_keywords if keyword in response_text)
                        
                        if keyword_count >= 3:
                            print(f"   ✅ 响应包含RCA内容 ({keyword_count}//{len(rca_keywords)} 关键词)")
                            successful_queries += 1
                        else:
                            print(f"   ⚠️ 响应缺少RCA内容 ({keyword_count}/{len(rca_keywords)} 关键词)")
                            print(f"   响应片段: {response_text[:100]}...")
                    else:
                        error_text = await response.text()
                        print(f"❌ 查询失败: HTTP {response.status}")
                        print(f"   错误信息: {error_text[:100]}...")
                        
            except asyncio.TimeoutError:
                print("❌ 查询超时")
            except Exception as e:
                print(f"❌ 查询异常: {e}")
        
        print(f"\n📊 API RCA测试结果: {successful_queries}/{len(test_queries)} 成功")
        
        if successful_queries == len(test_queries):
            print("🎉 API RCA功能完全可用！")
            return True
        elif successful_queries >= len(test_queries) * 0.7:
            print("✅ API RCA功能基本可用")
            return True
        else:
            print("❌ API RCA功能需要改进")
            return False


async def provide_usage_instructions():
    """提供使用说明"""
    print("\n" + "=" * 60)
    print("📖 Web UI RCA使用说明:")
    print("=" * 60)
    
    print("\n1. 🚀 启动API服务:")
    print("   uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000")
    
    print("\n2. 🌐 访问Web界面:")
    print("   浏览器打开: http://localhost:8000/docs")
    
    print("\n3. 💬 测试RCA查询:")
    print("   使用 /chat 端点，发送以下类型的查询:")
    
    examples = [
        "service-b CPU使用率过高，响应超时，请帮我分析根本原因",
        "数据库连接失败，多个服务无法访问，需要RCA分析",
        "请分析incident_001中service-b的CPU过载问题",
        "d1主机磁盘IO异常，部署的服务都变慢了",
        "redis连接超时，影响了哪些依赖服务？"
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"   示例{i}: {example}")
    
    print("\n4. 📊 预期响应内容:")
    print("   - 问题症状分析")
    print("   - 潜在根本原因") 
    print("   - 相关日志证据")
    print("   - 服务依赖分析")
    print("   - 解决方案建议")
    print("   - 置信度评估")
    
    print("\n5. 🔍 可用的数据范围:")
    print("   - 日志数据: incident_001, incident_002, incident_010")
    print("   - 服务: service-a, service-b, service-c, database, redis")
    print("   - 主机: host-1, host-2, d1") 
    print("   - 知识库: Wiki文档, GitLab项目, Jira工单")
    
    print(f"\n💡 当前RAG数据状态:")
    print(f"   - 向量索引: 234条记录")
    print(f"   - 知识图谱: 27个节点, 11个关系")
    print(f"   - 数据源: logs, wiki, gitlab, jira")


async def main():
    """主函数"""
    print("🚀 开始API RCA功能测试")
    print("=" * 60)
    
    # 测试API RCA功能
    api_success = await test_api_rca()
    
    # 提供使用说明
    await provide_usage_instructions()
    
    print(f"\n" + "=" * 60) 
    print("📋 测试总结:")
    print(f"   API RCA功能: {'✅ 可用' if api_success else '❌ 需要改进'}")
    
    if api_success:
        print("\n🎉 恭喜！你现在可以在Web UI中测试RCA功能了！")
        print("💡 按照上面的说明启动API服务并进行测试")
    else:
        print("\n⚠️ API需要集成完整的RCA流程")
        print("💡 当前只有基础LLM响应，缺少RAG搜索和推理逻辑")


if __name__ == "__main__":
    asyncio.run(main())