#!/usr/bin/env python3
"""
AIOps Polaris 命令行聊天工具
直接与系统进行交互测试
"""

import requests
import json
import sys
from datetime import datetime

API_BASE_URL = "http://localhost:8888"

def print_banner():
    """打印欢迎信息"""
    print("🤖 AIOps Polaris 智能运维助手")
    print("=" * 50)
    print("💡 输入您的问题，系统将为您提供智能运维建议")
    print("🔧 支持命令: /health, /stats, /quit")
    print("=" * 50)
    print()

def check_api_health():
    """检查API健康状态"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 系统状态: {data['status']}")
            return True
        else:
            print(f"❌ API不可用: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接到API: {e}")
        return False

def get_system_stats():
    """获取系统统计信息"""
    try:
        response = requests.get(f"{API_BASE_URL}/stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("📊 系统统计信息:")
            for key, value in data.items():
                if isinstance(value, dict):
                    print(f"  📁 {key}:")
                    for sub_key, sub_value in value.items():
                        print(f"    - {sub_key}: {sub_value}")
                else:
                    print(f"  📊 {key}: {value}")
        else:
            print(f"❌ 获取统计信息失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 统计信息获取错误: {e}")

def chat_with_aiops(message, user_id="cli_user"):
    """与AIOps系统聊天"""
    try:
        print("🔄 正在处理您的请求...")
        
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={
                "message": message,
                "user_id": user_id,
                "temperature": 0.7
            },
            timeout=30
        )
        
        print(f"📡 API响应状态: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                bot_response = result.get("response", "系统处理完成，但未生成响应")
                print("\n🤖 AIOps助手回复:")
                print("-" * 40)
                print(bot_response)
                print("-" * 40)
                
                # 显示处理信息
                if "processing_time" in result:
                    print(f"⏱️  处理时间: {result['processing_time']:.2f}秒")
                if "tokens_used" in result:
                    print(f"🔤 Token使用: {result['tokens_used']}")
                
                return True
            except json.JSONDecodeError:
                print(f"❌ 响应解析失败: {response.text}")
                return False
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 连接错误: {e}")
        return False

def search_knowledge(query):
    """搜索知识库"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/search",
            json={
                "query": query,
                "search_type": "hybrid",
                "limit": 3
            },
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            documents = result.get("documents", [])
            
            if documents:
                print("\n🔍 搜索结果:")
                print("-" * 40)
                for i, doc in enumerate(documents, 1):
                    print(f"{i}. 📄 {doc.get('title', 'Untitled')}")
                    print(f"   📂 来源: {doc.get('source', 'unknown')}")
                    content = doc.get('content', '')
                    if len(content) > 150:
                        content = content[:150] + "..."
                    print(f"   📝 内容: {content}")
                    print()
            else:
                print("❌ 未找到相关文档")
        else:
            print(f"❌ 搜索失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 搜索错误: {e}")

def main():
    """主函数"""
    print_banner()
    
    # 检查API健康状态
    if not check_api_health():
        print("请确保API服务正在运行: python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8888")
        sys.exit(1)
    
    print("🟢 系统连接成功！开始对话...")
    print("💡 提示: 尝试问一些运维相关的问题，比如:")
    print("  - 服务器CPU使用率过高怎么办？")
    print("  - 如何排查数据库连接超时问题？")
    print("  - 微服务架构的监控最佳实践")
    print()
    
    user_id = f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    while True:
        try:
            user_input = input("👤 您: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['/quit', '/exit', 'quit', 'exit']:
                print("👋 再见！感谢使用AIOps Polaris")
                break
            elif user_input.lower() == '/health':
                check_api_health()
                continue
            elif user_input.lower() == '/stats':
                get_system_stats()
                continue
            elif user_input.lower().startswith('/search '):
                query = user_input[8:]
                search_knowledge(query)
                continue
            elif user_input.lower() == '/help':
                print("🔧 可用命令:")
                print("  /health - 检查系统健康状态")
                print("  /stats  - 查看系统统计信息")
                print("  /search <查询> - 搜索知识库")
                print("  /quit   - 退出程序")
                continue
            
            # 正常聊天
            chat_with_aiops(user_input, user_id)
            print()
            
        except KeyboardInterrupt:
            print("\n👋 程序已退出")
            break
        except Exception as e:
            print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    main()