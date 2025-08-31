#!/usr/bin/env python3
"""
测试改进的RAG服务集成到RCA chat endpoint
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append('/home/alejandroseaah/AIOpsPolaris')

async def test_rca_chat_integration():
    """测试RCA聊天集成"""
    print("=== 测试RCA聊天集成 ===")
    
    try:
        from src.api.rca_chat_endpoint import rca_chat_service
        
        # 测试用户报告的问题查询
        test_query = "service-b CPU使用率过高，响应超时，请分析根本原因"
        
        print(f"🔍 测试查询: '{test_query}'")
        print("=" * 60)
        
        # 处理RCA查询
        result = await rca_chat_service.process_rca_query(test_query)
        
        print(f"✅ 分析类型: {result.get('analysis_type')}")
        print(f"📊 证据数量: {result.get('evidence_count')}")
        print(f"📈 置信度: {result.get('confidence', 0):.1%}")
        print(f"⏱️ 处理时间: {result.get('processing_time', 0):.2f}秒")
        print()
        print("📝 完整响应:")
        print("-" * 40)
        print(result.get('response', 'No response'))
        
        # 检查是否找到了evidence
        if result.get('evidence_count', 0) > 0:
            print(f"\n✅ 成功: 找到了 {result['evidence_count']} 条证据，RAG集成正常工作!")
            
            # 显示原始分析数据（调试信息）
            raw_analysis = result.get('raw_analysis')
            if raw_analysis:
                evidence_summary = raw_analysis.get('evidence_summary', {})
                print(f"   - 日志证据: {evidence_summary.get('log_evidence_count', 0)} 条")
                print(f"   - 依赖关系: {evidence_summary.get('graph_evidence_count', 0)} 个")
        else:
            print("❌ 失败: 没有找到相关证据，需要进一步调试")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_rca_chat_integration())