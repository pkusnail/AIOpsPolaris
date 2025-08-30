"""
智能体包 - 简化版本，用于演示目的
"""

# 简化实现，暂时移除复杂依赖
class SimpleAIOpsAgent:
    """简化的AIOps智能体，用于演示目的"""
    
    def __init__(self):
        self.name = "AIOps Assistant"
    
    async def process_query(self, query: str) -> str:
        """处理用户查询"""
        return f"收到查询: {query}。这是一个简化的响应，完整功能正在开发中。"

# 导出简化版本
AIOpsGraph = SimpleAIOpsAgent

__all__ = ["AIOpsGraph", "SimpleAIOpsAgent"]