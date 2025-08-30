"""
Gradio前端界面
为DevOps用户提供友好的Web界面
"""

import gradio as gr
import httpx
import asyncio
import json
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import time

# API配置
API_BASE_URL = "http://localhost:8888"  # API服务地址
DEFAULT_USER_ID = "demo_user"

# 当前会话状态
current_session = {
    "session_id": None,
    "user_id": DEFAULT_USER_ID,
    "chat_history": []
}


async def call_api(endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
    """调用后端API"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            url = f"{API_BASE_URL}{endpoint}"
            
            if method == "GET":
                response = await client.get(url, params=data or {})
            elif method == "POST":
                response = await client.post(url, json=data or {})
            elif method == "DELETE":
                response = await client.delete(url)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "error": True,
                    "message": f"API调用失败: {response.status_code} - {response.text}"
                }
                
    except Exception as e:
        return {
            "error": True,
            "message": f"API调用异常: {str(e)}"
        }


def format_agent_messages(messages: List[Dict]) -> str:
    """格式化Agent消息"""
    formatted = []
    
    for msg in messages:
        agent_id = msg.get("agent_id", "unknown")
        msg_type = msg.get("type", "unknown")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")
        
        # 添加表情符号和格式化
        if agent_id == "system":
            emoji = "🤖"
        elif agent_id == "planner":
            emoji = "📋"
        elif agent_id == "knowledge":
            emoji = "🔍"
        elif agent_id == "reasoning":
            emoji = "🧠"
        elif agent_id == "executor":
            emoji = "⚙️"
        else:
            emoji = "💬"
        
        if msg_type == "thought":
            prefix = "💭"
        elif msg_type == "action":
            prefix = "🎯"
        elif msg_type == "observation":
            prefix = "👀"
        elif msg_type == "answer":
            prefix = "✅"
        elif msg_type == "error":
            prefix = "❌"
        else:
            prefix = "📝"
        
        formatted.append(f"{emoji} **{agent_id.title()}** {prefix} {content}")
    
    return "\n\n".join(formatted)


async def chat_with_aiops(message: str, history: List[Tuple[str, str]], show_details: bool = False) -> Tuple[List[Tuple[str, str]], str]:
    """与AIOps系统对话"""
    if not message.strip():
        return history, ""
    
    try:
        # 显示思考中状态
        thinking_history = history + [(message, "🤔 AIOps系统正在分析中，请稍候...")]
        
        # 调用聊天API
        response = await call_api(
            "/chat",
            method="POST",
            data={
                "message": message,
                "user_id": current_session["user_id"],
                "session_id": current_session.get("session_id"),
                "temperature": 0.7,
                "max_tokens": 4096,
                "stream": False
            }
        )
        
        if response.get("error"):
            error_msg = f"❌ 错误: {response.get('message', '未知错误')}"
            return history + [(message, error_msg)], ""
        
        # 更新会话ID
        if response.get("session_id"):
            current_session["session_id"] = response["session_id"]
        
        # 获取主要响应
        main_response = response.get("response", "抱歉，没有生成响应")
        
        # 构建详细信息
        details = ""
        if show_details and response.get("agent_messages"):
            details = "\n\n---\n\n**详细处理过程:**\n\n"
            details += format_agent_messages(response["agent_messages"])
            details += f"\n\n**处理统计:**\n"
            details += f"- 处理时间: {response.get('processing_time', 0):.2f}秒\n"
            details += f"- Token使用: {response.get('tokens_used', 0)}\n"
            details += f"- 会话ID: {response.get('session_id', 'N/A')}"
        
        final_response = main_response + details
        
        # 更新历史
        new_history = history + [(message, final_response)]
        
        # 添加到当前会话历史
        current_session["chat_history"].append({
            "user": message,
            "assistant": main_response,
            "timestamp": datetime.now().isoformat(),
            "details": response
        })
        
        return new_history, ""
        
    except Exception as e:
        error_msg = f"❌ 系统错误: {str(e)}"
        return history + [(message, error_msg)], ""


async def search_knowledge(query: str, search_type: str = "hybrid", source: str = "", limit: int = 5) -> str:
    """搜索知识库"""
    if not query.strip():
        return "请输入搜索查询"
    
    try:
        # 调用搜索API
        search_data = {
            "query": query,
            "search_type": search_type,
            "limit": limit
        }
        
        if source:
            search_data["source"] = source
        
        response = await call_api("/search", method="POST", data=search_data)
        
        if response.get("error"):
            return f"❌ 搜索失败: {response.get('message', '未知错误')}"
        
        results = response.get("results", [])
        total = response.get("total", 0)
        processing_time = response.get("processing_time", 0)
        
        if not results:
            return f"🔍 未找到相关结果 (处理时间: {processing_time:.2f}秒)"
        
        # 格式化搜索结果
        formatted_results = [f"🔍 **搜索结果** ({total} 个结果, {processing_time:.2f}秒)\n"]
        
        for i, result in enumerate(results, 1):
            title = result.get("title", "无标题")
            content = result.get("content", "")[:200] + "..." if len(result.get("content", "")) > 200 else result.get("content", "")
            source_info = result.get("source", "未知来源")
            score = result.get("score", 0)
            
            formatted_results.append(
                f"**{i}. {title}** (相关度: {score:.2f})\n"
                f"📄 来源: {source_info}\n"
                f"📝 内容: {content}\n"
            )
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"❌ 搜索异常: {str(e)}"


async def get_system_status() -> str:
    """获取系统状态"""
    try:
        # 获取健康检查
        health_response = await call_api("/health")
        
        if health_response.get("error"):
            return f"❌ 健康检查失败: {health_response.get('message')}"
        
        # 获取统计信息
        stats_response = await call_api("/stats")
        
        if stats_response.get("error"):
            stats_info = "统计信息获取失败"
        else:
            vector_db = stats_response.get("vector_database", {})
            knowledge_graph = stats_response.get("knowledge_graph", {})
            
            stats_info = f"""
**向量数据库:**
- 文档数量: {vector_db.get('knowledgedocument_count', 0)}
- 实体数量: {vector_db.get('entity_count', 0)}

**知识图谱:**
- 节点数量: {knowledge_graph.get('node_count', 0)}
- 关系数量: {knowledge_graph.get('relationship_count', 0)}
"""
        
        # 获取Agent状态
        agent_response = await call_api("/agent/status")
        
        if agent_response.get("error"):
            agent_info = "Agent状态获取失败"
        else:
            services = agent_response.get("services", {})
            agent_info = f"""
**Agent服务状态:**
- 搜索服务: {'✅' if services.get('search_service') else '❌'}
- 图数据库: {'✅' if services.get('graph_service') else '❌'}
- LLM服务: {'✅' if services.get('llm_service') else '❌'}
"""
        
        status_text = f"""
# 🤖 AIOps Polaris 系统状态

## ✅ 服务健康状态
**状态**: {health_response.get('status', '未知')}
**版本**: {health_response.get('version', '未知')}
**检查时间**: {health_response.get('timestamp', '未知')}

## 📊 系统统计
{stats_info}

## 🔧 服务状态
{agent_info}

## 💡 使用提示
- 🗣️ **智能对话**: 描述您遇到的运维问题，系统会自动分析并提供解决方案
- 🔍 **知识搜索**: 在知识库中搜索相关文档和最佳实践
- 📋 **会话管理**: 查看历史对话记录和会话详情

**示例问题:**
- "生产环境CPU使用率突然升高，用户反馈页面加载慢"
- "数据库连接池耗尽，如何处理？"  
- "Kubernetes Pod一直处于Pending状态"
- "如何优化MySQL查询性能？"
"""
        
        return status_text
        
    except Exception as e:
        return f"❌ 状态检查异常: {str(e)}"


async def extract_knowledge(text: str) -> str:
    """从文本中提取知识"""
    if not text.strip():
        return "请输入要分析的文本"
    
    try:
        response = await call_api(
            "/knowledge/extract",
            method="POST",
            data={"text": text, "source": "manual"}
        )
        
        if response.get("error"):
            return f"❌ 知识提取失败: {response.get('message')}"
        
        entities = response.get("entities", [])
        relationships = response.get("relationships", [])
        stats = response.get("stats", {})
        
        if not entities and not relationships:
            return "📝 未从文本中提取到实体或关系信息"
        
        result = ["# 🧠 知识提取结果\n"]
        
        # 统计信息
        result.append(f"**提取统计:**")
        result.append(f"- 实体数量: {stats.get('entity_count', len(entities))}")
        result.append(f"- 关系数量: {stats.get('relationship_count', len(relationships))}")
        result.append(f"- 实体类型分布: {stats.get('entity_types', {})}")
        result.append("")
        
        # 实体信息
        if entities:
            result.append("## 🏷️ 识别的实体")
            for entity in entities[:10]:  # 显示前10个
                result.append(f"- **{entity.get('text', '')}** ({entity.get('label', '未知类型')}) - 置信度: {entity.get('confidence', 0):.2f}")
            
            if len(entities) > 10:
                result.append(f"... 还有 {len(entities) - 10} 个实体")
            result.append("")
        
        # 关系信息
        if relationships:
            result.append("## 🔗 识别的关系")
            for rel in relationships[:10]:  # 显示前10个
                result.append(f"- **{rel.get('source_text', '')}** → **{rel.get('target_text', '')}** ({rel.get('relationship_type', '未知关系')})")
            
            if len(relationships) > 10:
                result.append(f"... 还有 {len(relationships) - 10} 个关系")
        
        return "\n".join(result)
        
    except Exception as e:
        return f"❌ 知识提取异常: {str(e)}"


def create_gradio_app():
    """创建Gradio应用"""
    
    # 自定义CSS样式
    custom_css = """
    .gradio-container {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    .chat-message {
        padding: 10px;
        margin: 5px 0;
        border-radius: 10px;
    }
    
    .user-message {
        background-color: #e3f2fd;
        text-align: right;
    }
    
    .assistant-message {
        background-color: #f5f5f5;
        text-align: left;
    }
    
    .status-panel {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #dee2e6;
    }
    """
    
    with gr.Blocks(
        title="🤖 AIOps Polaris - 智能运维助手",
        theme=gr.themes.Soft(),
        css=custom_css
    ) as app:
        
        # 标题和介绍
        gr.HTML("""
        <div style="text-align: center; padding: 20px;">
            <h1>🤖 AIOps Polaris</h1>
            <h3>智能运维助手 - 让运维更简单</h3>
            <p>基于AI的智能运维系统，提供故障诊断、知识搜索、根因分析等服务</p>
        </div>
        """)
        
        # 创建选项卡
        with gr.Tabs():
            
            # 智能对话选项卡
            with gr.TabItem("💬 智能对话", elem_id="chat-tab"):
                with gr.Row():
                    with gr.Column(scale=3):
                        chatbot = gr.Chatbot(
                            height=500,
                            placeholder="AIOps助手准备就绪，请描述您的运维问题...",
                            label="💬 智能运维对话"
                        )
                        
                        with gr.Row():
                            msg_input = gr.Textbox(
                                placeholder="请描述您遇到的运维问题，例如: '生产环境CPU使用率高，用户反馈页面加载慢'",
                                label="输入消息",
                                lines=2,
                                scale=4
                            )
                            send_btn = gr.Button("发送 🚀", variant="primary", scale=1)
                        
                        clear_btn = gr.Button("清空对话 🗑️", variant="secondary")
                    
                    with gr.Column(scale=1):
                        show_details = gr.Checkbox(
                            label="显示详细处理过程",
                            value=False,
                            info="展示Agent的详细分析步骤"
                        )
                        
                        gr.HTML("""
                        <div class="status-panel">
                            <h4>💡 使用提示</h4>
                            <ul>
                                <li>描述具体的运维问题和症状</li>
                                <li>包含错误信息、性能指标等</li>
                                <li>系统会自动进行故障分析</li>
                                <li>提供解决方案和操作建议</li>
                            </ul>
                        </div>
                        """)
                        
                        # 示例问题按钮
                        gr.HTML("<h4>🎯 示例问题</h4>")
                        
                        example1 = gr.Button("CPU使用率高问题", size="sm")
                        example2 = gr.Button("数据库连接失败", size="sm") 
                        example3 = gr.Button("Pod Pending状态", size="sm")
                        example4 = gr.Button("内存泄露排查", size="sm")
            
            # 知识搜索选项卡
            with gr.TabItem("🔍 知识搜索", elem_id="search-tab"):
                with gr.Row():
                    with gr.Column():
                        search_input = gr.Textbox(
                            placeholder="请输入搜索关键词，如: 'MySQL性能优化'、'Kubernetes故障排查'等",
                            label="搜索查询",
                            lines=1
                        )
                        
                        with gr.Row():
                            search_type = gr.Dropdown(
                                choices=["hybrid", "vector", "keyword", "graph"],
                                value="hybrid",
                                label="搜索类型",
                                info="hybrid=混合搜索, vector=语义搜索, keyword=关键词搜索, graph=图谱搜索"
                            )
                            
                            source_filter = gr.Dropdown(
                                choices=["", "wiki", "gitlab", "jira", "logs"],
                                value="",
                                label="数据源过滤",
                                info="可选择特定数据源"
                            )
                            
                            search_limit = gr.Slider(
                                minimum=1,
                                maximum=20,
                                value=5,
                                step=1,
                                label="结果数量"
                            )
                        
                        search_btn = gr.Button("搜索 🔍", variant="primary")
                    
                search_results = gr.Markdown(
                    value="",
                    label="搜索结果"
                )
            
            # 知识提取选项卡
            with gr.TabItem("🧠 知识提取", elem_id="extract-tab"):
                with gr.Row():
                    with gr.Column():
                        extract_input = gr.Textbox(
                            placeholder="请输入要分析的运维文本，系统将自动识别其中的实体和关系...",
                            label="输入文本",
                            lines=8
                        )
                        
                        extract_btn = gr.Button("提取知识 🧠", variant="primary")
                    
                    with gr.Column():
                        extract_results = gr.Markdown(
                            value="",
                            label="提取结果"
                        )
                        
                        gr.HTML("""
                        <div class="status-panel">
                            <h4>🧠 知识提取说明</h4>
                            <p>系统会自动识别文本中的:</p>
                            <ul>
                                <li>🏷️ 实体: 服务、数据库、服务器等</li>
                                <li>🔗 关系: 依赖关系、影响关系等</li>
                                <li>📊 统计: 实体类型分布等</li>
                            </ul>
                        </div>
                        """)
            
            # 系统状态选项卡
            with gr.TabItem("📊 系统状态", elem_id="status-tab"):
                status_display = gr.Markdown(
                    value="",
                    label="系统状态"
                )
                
                refresh_btn = gr.Button("刷新状态 🔄", variant="primary")
        
        # 事件绑定
        
        # 聊天事件
        async def send_message(message, history, details):
            return await chat_with_aiops(message, history, details)
        
        send_btn.click(
            fn=send_message,
            inputs=[msg_input, chatbot, show_details],
            outputs=[chatbot, msg_input]
        )
        
        msg_input.submit(
            fn=send_message,
            inputs=[msg_input, chatbot, show_details],
            outputs=[chatbot, msg_input]
        )
        
        clear_btn.click(
            fn=lambda: [],
            outputs=[chatbot]
        )
        
        # 示例问题点击事件
        example1.click(
            fn=lambda: "生产环境CPU使用率突然升高到90%，用户反馈页面加载很慢，请帮我分析原因并提供解决方案。",
            outputs=[msg_input]
        )
        
        example2.click(
            fn=lambda: "数据库连接池耗尽导致服务不可用，出现大量连接超时错误，如何快速处理？",
            outputs=[msg_input]
        )
        
        example3.click(
            fn=lambda: "Kubernetes集群中Pod一直处于Pending状态无法启动，显示资源不足，请协助排查。",
            outputs=[msg_input]
        )
        
        example4.click(
            fn=lambda: "Java应用出现内存泄露，堆内存使用率持续上升，如何定位和解决？",
            outputs=[msg_input]
        )
        
        # 搜索事件
        search_btn.click(
            fn=search_knowledge,
            inputs=[search_input, search_type, source_filter, search_limit],
            outputs=[search_results]
        )
        
        # 知识提取事件
        extract_btn.click(
            fn=extract_knowledge,
            inputs=[extract_input],
            outputs=[extract_results]
        )
        
        # 系统状态事件
        refresh_btn.click(
            fn=get_system_status,
            outputs=[status_display]
        )
        
        # 页面加载时自动获取系统状态
        app.load(
            fn=get_system_status,
            outputs=[status_display]
        )
    
    return app


if __name__ == "__main__":
    # 创建并启动Gradio应用
    app = create_gradio_app()
    
    # 启动应用
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=True,
        show_error=True,
        quiet=False
    )