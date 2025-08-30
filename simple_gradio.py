#!/usr/bin/env python3
"""
简化版Gradio前端界面
用于AIOps Polaris系统演示
"""

import gradio as gr
import requests
import json
from datetime import datetime

API_BASE_URL = "http://localhost:8888"

def chat_with_aiops(message, user_id="demo_user", history=None):
    """与AIOps系统聊天"""
    if not message.strip():
        return "", history or []
    
    try:
        # 调用API
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json={
                "message": message,
                "user_id": user_id,
                "temperature": 0.7
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            bot_response = result.get("response", "系统处理完成")
            
            # 更新历史记录
            if history is None:
                history = []
            history.append([message, bot_response])
            
            return "", history
        else:
            error_msg = f"API错误: {response.status_code} - {response.text}"
            if history is None:
                history = []
            history.append([message, error_msg])
            return "", history
            
    except Exception as e:
        error_msg = f"连接错误: {str(e)}"
        if history is None:
            history = []
        history.append([message, error_msg])
        return "", history

def search_knowledge(query, source="all"):
    """搜索知识库"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/search",
            json={
                "query": query,
                "search_type": "hybrid",
                "source": source if source != "all" else None,
                "limit": 5
            },
            timeout=15
        )
        
        if response.status_code == 200:
            results = response.json()
            documents = results.get("documents", [])
            
            if not documents:
                return "未找到相关文档"
            
            output = "## 搜索结果:\n\n"
            for i, doc in enumerate(documents, 1):
                output += f"**{i}. {doc.get('title', 'Untitled')}**\n"
                output += f"来源: {doc.get('source', 'unknown')}\n"
                content = doc.get('content', '')
                if len(content) > 200:
                    content = content[:200] + "..."
                output += f"内容: {content}\n\n"
            
            return output
        else:
            return f"搜索失败: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"搜索错误: {str(e)}"

def get_system_status():
    """获取系统状态"""
    try:
        # 健康检查
        health_response = requests.get(f"{API_BASE_URL}/health", timeout=10)
        if health_response.status_code != 200:
            return f"系统不健康: {health_response.status_code}"
        
        health_data = health_response.json()
        
        # 统计信息
        stats_response = requests.get(f"{API_BASE_URL}/stats", timeout=10)
        stats_data = stats_response.json() if stats_response.status_code == 200 else {}
        
        # 格式化输出
        output = "## 🟢 系统状态: 健康\n\n"
        output += f"**版本**: {health_data.get('version', 'unknown')}\n"
        output += f"**时间**: {health_data.get('timestamp', 'unknown')}\n\n"
        
        output += "### 服务组件状态:\n"
        components = health_data.get('components', {})
        for service, info in components.items():
            status = info.get('status', 'unknown')
            emoji = "🟢" if status == "healthy" else "🔴"
            output += f"- {emoji} **{service.upper()}**: {status}\n"
        
        if stats_data:
            output += "\n### 数据统计:\n"
            if 'knowledgedocument_count' in stats_data:
                output += f"- 📄 文档数量: {stats_data['knowledgedocument_count']}\n"
            if 'entity_count' in stats_data:
                output += f"- 🏷️ 实体数量: {stats_data['entity_count']}\n"
            if 'logentry_count' in stats_data:
                output += f"- 📋 日志数量: {stats_data['logentry_count']}\n"
        
        return output
        
    except Exception as e:
        return f"❌ 无法获取系统状态: {str(e)}"

# 创建Gradio界面
with gr.Blocks(title="AIOps Polaris", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 AIOps Polaris 智能运维系统")
    gr.Markdown("基于RAG + 混合搜索 + 多Agent架构的智能运维助手")
    
    with gr.Tab("💬 智能对话"):
        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="AIOps助手",
                    height=400,
                    avatar_images=["🧑‍💻", "🤖"]
                )
                msg = gr.Textbox(
                    label="输入您的问题",
                    placeholder="例如: 查询服务器CPU使用率过高的解决方案",
                    lines=2
                )
                with gr.Row():
                    submit_btn = gr.Button("发送", variant="primary")
                    clear_btn = gr.Button("清空对话")
            
            with gr.Column(scale=1):
                user_id_input = gr.Textbox(
                    label="用户ID",
                    value="demo_user",
                    interactive=True
                )
                gr.Markdown("### 🔧 快捷操作")
                gr.Markdown("- 查询系统状态")
                gr.Markdown("- 搜索知识库")
                gr.Markdown("- 分析日志异常")
    
    with gr.Tab("🔍 知识搜索"):
        with gr.Row():
            with gr.Column():
                search_query = gr.Textbox(
                    label="搜索查询",
                    placeholder="输入关键词搜索知识库",
                    lines=1
                )
                search_source = gr.Dropdown(
                    label="数据源",
                    choices=["all", "wiki", "gitlab", "jira", "logs"],
                    value="all"
                )
                search_btn = gr.Button("搜索", variant="primary")
            
            with gr.Column():
                search_results = gr.Markdown(label="搜索结果")
    
    with gr.Tab("📊 系统状态"):
        with gr.Column():
            refresh_btn = gr.Button("刷新状态", variant="primary")
            status_display = gr.Markdown(label="系统状态")
    
    # 事件绑定
    submit_btn.click(
        chat_with_aiops,
        inputs=[msg, user_id_input, chatbot],
        outputs=[msg, chatbot]
    )
    
    msg.submit(
        chat_with_aiops,
        inputs=[msg, user_id_input, chatbot],
        outputs=[msg, chatbot]
    )
    
    clear_btn.click(lambda: ([], ""), outputs=[chatbot, msg])
    
    search_btn.click(
        search_knowledge,
        inputs=[search_query, search_source],
        outputs=search_results
    )
    
    refresh_btn.click(
        get_system_status,
        outputs=status_display
    )
    
    # 页面加载时获取系统状态
    demo.load(get_system_status, outputs=status_display)

if __name__ == "__main__":
    print("🚀 启动AIOps Polaris前端界面...")
    print("🌐 访问地址: http://localhost:7860")
    print("💡 确保后端API服务运行在 http://localhost:8888")
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=False
    )