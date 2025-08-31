"""
RAG Pipeline集成测试脚本
快速验证索引建立和搜索功能
"""

import asyncio
import sys
import logging
from datetime import datetime
from pathlib import Path

# 添加src路径
sys.path.append('src')

from services.rag_vector_service import RAGVectorService
from services.log_pipeline import LogPipeline
from services.knowledge_pipeline import KnowledgePipeline
from services.knowledge_graph_pipeline import KnowledgeGraphPipeline
from services.embedding_service import EmbeddingService

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_rag_schema():
    """测试RAG Schema创建"""
    print("\n=== 测试RAG Schema创建 ===")
    try:
        rag_service = RAGVectorService()
        await rag_service.create_rag_schema()
        
        schema = await rag_service.get_schema()
        class_names = [cls['class'] for cls in schema.get('classes', [])]
        
        print(f"✅ Schema创建成功")
        print(f"✅ 发现Collections: {class_names}")
        
        if 'EmbeddingCollection' in class_names and 'FullTextCollection' in class_names:
            print("✅ 两个专用Collection已创建")
            return True
        else:
            print("❌ Collection创建失败")
            return False
            
    except Exception as e:
        print(f"❌ Schema创建失败: {e}")
        return False


async def test_log_pipeline():
    """测试日志处理pipeline"""
    print("\n=== 测试日志处理Pipeline ===")
    try:
        # 检查日志目录
        logs_dir = Path("./data/logs/")
        if not logs_dir.exists():
            print("❌ 日志目录不存在")
            return False
        
        log_files = list(logs_dir.glob("*.log"))
        print(f"📁 发现 {len(log_files)} 个日志文件")
        
        if len(log_files) == 0:
            print("❌ 没有日志文件")
            return False
        
        # 运行日志pipeline
        log_pipeline = LogPipeline()
        stats = await log_pipeline.process_structured_logs()
        
        print(f"✅ 日志处理完成:")
        print(f"   - 处理incidents: {stats['incidents_processed']}")
        print(f"   - 总日志条目: {stats['total_log_entries']}")
        print(f"   - 处理时间: {stats['processing_time']:.2f}秒")
        
        return stats['total_log_entries'] > 0
        
    except Exception as e:
        print(f"❌ 日志pipeline失败: {e}")
        return False


async def test_knowledge_pipeline():
    """测试知识数据pipeline"""
    print("\n=== 测试知识数据Pipeline ===")
    try:
        knowledge_pipeline = KnowledgePipeline()
        stats = await knowledge_pipeline.process_all_knowledge_data()
        
        print(f"✅ 知识数据处理完成:")
        print(f"   - Wiki文档: {stats['wiki'].get('processed_docs', 0)}")
        print(f"   - GitLab项目: {stats['gitlab'].get('processed_count', 0)}")
        print(f"   - Jira工单: {stats['jira'].get('processed_count', 0)}")
        print(f"   - 总处理数: {stats['total_processed']}")
        print(f"   - 处理时间: {stats['processing_time']:.2f}秒")
        
        return stats['total_processed'] > 0
        
    except Exception as e:
        print(f"❌ 知识pipeline失败: {e}")
        return False


async def test_search_functionality():
    """测试搜索功能"""
    print("\n=== 测试搜索功能 ===")
    try:
        rag_service = RAGVectorService()
        embedding_service = EmbeddingService()
        
        # 获取统计信息
        stats = await rag_service.get_stats()
        print(f"📊 索引统计:")
        print(f"   - EmbeddingCollection: {stats.get('embeddingcollection_count', 0)} 条")
        print(f"   - FullTextCollection: {stats.get('fulltextcollection_count', 0)} 条")
        
        if stats.get('embeddingcollection_count', 0) == 0:
            print("❌ 没有索引数据，无法测试搜索")
            return False
        
        # 测试不同类型的搜索
        test_queries = [
            "CPU使用率过高",
            "数据库连接超时", 
            "service-b故障",
            "Kubernetes Pod重启"
        ]
        
        for query in test_queries:
            print(f"\n🔍 测试查询: '{query}'")
            
            # 向量搜索
            try:
                query_vector = await embedding_service.encode_text(query)
                vector_results = await rag_service.embedding_search(
                    query_vector=query_vector,
                    limit=3
                )
                print(f"   📍 向量搜索: 找到 {len(vector_results)} 条结果")
                
                if vector_results:
                    top_result = vector_results[0]
                    certainty = top_result.get('_additional', {}).get('certainty', 0)
                    print(f"   📍 最佳匹配: {certainty:.3f} - {top_result.get('title', '')[:50]}...")
                    
            except Exception as e:
                print(f"   ❌ 向量搜索失败: {e}")
            
            # 全文搜索
            try:
                fulltext_results = await rag_service.fulltext_search(
                    query=query,
                    limit=3
                )
                print(f"   📍 全文搜索: 找到 {len(fulltext_results)} 条结果")
                
                if fulltext_results:
                    top_result = fulltext_results[0]
                    score = top_result.get('_additional', {}).get('score', 0)
                    print(f"   📍 最佳匹配: {score:.3f} - {top_result.get('title', '')[:50]}...")
                    
            except Exception as e:
                print(f"   ❌ 全文搜索失败: {e}")
            
            # 混合搜索
            try:
                query_vector = await embedding_service.encode_text(query)
                hybrid_results = await rag_service.hybrid_search_with_rerank(
                    query=query,
                    query_vector=query_vector,
                    limit=3
                )
                merged_results = hybrid_results['merged_results']
                print(f"   📍 混合搜索: 找到 {len(merged_results)} 条结果")
                
                if merged_results:
                    top_result = merged_results[0]
                    final_score = top_result.get('final_score', 0)
                    print(f"   📍 最佳匹配: {final_score:.3f} - {top_result.get('title', '')[:50]}...")
                    
            except Exception as e:
                print(f"   ❌ 混合搜索失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 搜索功能测试失败: {e}")
        return False


async def test_filtered_search():
    """测试过滤搜索"""
    print("\n=== 测试过滤搜索 ===")
    try:
        rag_service = RAGVectorService()
        embedding_service = EmbeddingService()
        
        # 测试服务过滤
        query_vector = await embedding_service.encode_text("CPU问题")
        
        service_b_results = await rag_service.embedding_search(
            query_vector=query_vector,
            service_name="service-b",
            limit=5
        )
        
        print(f"🔍 service-b过滤: 找到 {len(service_b_results)} 条结果")
        
        if service_b_results:
            for result in service_b_results[:2]:
                print(f"   - {result.get('title', '')}: {result.get('service_name', '')}")
        
        # 测试日志级别过滤
        error_results = await rag_service.fulltext_search(
            query="ERROR",
            log_level="ERROR",
            limit=5
        )
        
        print(f"🔍 ERROR级别过滤: 找到 {len(error_results)} 条结果")
        
        return len(service_b_results) > 0 or len(error_results) > 0
        
    except Exception as e:
        print(f"❌ 过滤搜索测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🚀 开始RAG Pipeline集成测试")
    print("=" * 50)
    
    test_results = []
    
    # 测试schema创建
    schema_ok = await test_rag_schema()
    test_results.append(("Schema创建", schema_ok))
    
    if not schema_ok:
        print("❌ Schema创建失败，停止后续测试")
        return
    
    # 测试日志pipeline
    log_ok = await test_log_pipeline()
    test_results.append(("日志Pipeline", log_ok))
    
    # 测试知识pipeline
    knowledge_ok = await test_knowledge_pipeline()
    test_results.append(("知识Pipeline", knowledge_ok))
    
    # 测试搜索功能
    if log_ok or knowledge_ok:
        search_ok = await test_search_functionality()
        test_results.append(("搜索功能", search_ok))
        
        # 测试过滤搜索
        filter_ok = await test_filtered_search()
        test_results.append(("过滤搜索", filter_ok))
    
    # 显示测试结果
    print("\n" + "=" * 50)
    print("📋 测试结果总结:")
    print("=" * 50)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<20} {status}")
    
    passed_tests = sum(1 for _, result in test_results if result)
    total_tests = len(test_results)
    
    print(f"\n📊 总体结果: {passed_tests}/{total_tests} 测试通过")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过！RAG Pipeline工作正常")
    elif passed_tests > 0:
        print("⚠️  部分测试通过，请检查失败的组件")
    else:
        print("💥 所有测试失败，请检查系统配置")


if __name__ == "__main__":
    asyncio.run(main())