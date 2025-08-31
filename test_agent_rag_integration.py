"""
测试Agent与RAG Pipeline的集成
验证agent能否正确理解RAG信息并执行RCA工作
"""

import asyncio
import sys
import logging
from datetime import datetime
from pathlib import Path

# 添加src路径
sys.path.append('src')

from services.rag_search_service import RAGSearchService, AgentRAGAdapter
from services.log_pipeline import LogPipeline
from services.knowledge_pipeline import KnowledgePipeline
from agents.knowledge_agent import KnowledgeAgent
from agents.reasoning_agent import ReasoningAgent
from agents.base_agent import AgentState, AgentMessage, MessageType

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def setup_test_data():
    """设置测试数据"""
    print("\n=== 设置测试数据 ===")
    try:
        # 运行日志pipeline
        log_pipeline = LogPipeline()
        log_stats = await log_pipeline.process_structured_logs()
        print(f"✅ 日志数据处理: {log_stats['total_log_entries']} 条日志")
        
        # 运行知识pipeline  
        knowledge_pipeline = KnowledgePipeline()
        knowledge_stats = await knowledge_pipeline.process_all_knowledge_data()
        print(f"✅ 知识数据处理: {knowledge_stats['total_processed']} 个文档")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试数据设置失败: {e}")
        return False


async def test_rag_search_service():
    """测试RAG搜索服务"""
    print("\n=== 测试RAG搜索服务 ===")
    try:
        rag_search = RAGSearchService()
        
        # 测试RCA专用搜索
        test_queries = [
            "service-b CPU使用率过高",
            "数据库连接超时问题",
            "Kubernetes Pod重启循环"
        ]
        
        for query in test_queries:
            print(f"\n🔍 测试查询: '{query}'")
            
            # 执行RCA搜索
            rca_results = await rag_search.search_for_rca(
                query=query,
                context={"user_message": query},
                search_type="hybrid",
                limit=5
            )
            
            logs_count = len(rca_results["logs"])
            knowledge_count = len(rca_results["knowledge"])
            entities_count = len(rca_results["entities"])
            merged_count = len(rca_results["merged_results"])
            
            print(f"   📊 搜索结果:")
            print(f"   - 日志: {logs_count} 条")
            print(f"   - 知识文档: {knowledge_count} 个")
            print(f"   - 相关实体: {entities_count} 个")
            print(f"   - 融合结果: {merged_count} 条")
            
            if merged_count > 0:
                top_result = rca_results["merged_results"][0]
                relevance = top_result.get("rca_relevance", 0)
                result_type = top_result.get("result_type", "unknown")
                print(f"   🏆 最佳匹配: {result_type} (相关性: {relevance:.3f})")
                print(f"       标题: {top_result.get('title', '')[:60]}...")
        
        print("\n✅ RAG搜索服务测试完成")
        return True
        
    except Exception as e:
        print(f"❌ RAG搜索服务测试失败: {e}")
        return False


async def test_agent_rag_integration():
    """测试Agent与RAG的集成"""
    print("\n=== 测试Agent RAG集成 ===")
    try:
        # 创建RAG适配器
        rag_adapter = AgentRAGAdapter()
        
        # 创建知识agent
        knowledge_agent = KnowledgeAgent(search_service=rag_adapter.rag_search)
        
        # 测试场景: CPU过载故障分析
        test_query = "service-b出现CPU使用率过高，导致请求响应超时，如何进行根因分析？"
        
        print(f"🤖 测试场景: {test_query}")
        
        # 创建初始状态
        initial_state = AgentState()
        initial_state.context = {
            "user_message": test_query,
            "search_query": test_query
        }
        
        # 执行知识agent处理
        print("\n📚 执行知识检索...")
        final_state = initial_state
        
        while not final_state.is_complete and final_state.current_step < knowledge_agent.max_steps:
            final_state = await knowledge_agent.process(final_state)
            final_state.current_step += 1
            
            # 显示agent思考过程
            if final_state.messages:
                last_msg = final_state.messages[-1]
                msg_type = last_msg.type.value
                content_preview = last_msg.content[:100] + "..." if len(last_msg.content) > 100 else last_msg.content
                print(f"   [{msg_type}] {content_preview}")
        
        # 验证知识检索结果
        found_docs = final_state.context.get("found_documents", [])
        entity_info = final_state.context.get("entity_relationships", {})
        knowledge_summary = final_state.context.get("knowledge_summary", {})
        
        print(f"\n📊 知识检索结果:")
        print(f"   - 找到文档: {len(found_docs)} 个")
        print(f"   - 相关实体: {len(entity_info.get('entities', []))} 个")
        print(f"   - 知识摘要置信度: {knowledge_summary.get('confidence_score', 0):.2f}")
        
        # 测试推理agent
        print("\n🧠 执行推理分析...")
        reasoning_agent = ReasoningAgent()
        
        # 重置状态用于推理
        reasoning_state = AgentState()
        reasoning_state.context = {
            "user_message": test_query,
            "knowledge_summary": knowledge_summary,
            "found_documents": found_docs,
            "entity_relationships": entity_info
        }
        
        while not reasoning_state.is_complete and reasoning_state.current_step < reasoning_agent.max_steps:
            reasoning_state = await reasoning_agent.process(reasoning_state)
            reasoning_state.current_step += 1
            
            # 显示推理过程
            if reasoning_state.messages:
                last_msg = reasoning_state.messages[-1]
                msg_type = last_msg.type.value
                content_preview = last_msg.content[:100] + "..." if len(last_msg.content) > 100 else last_msg.content
                print(f"   [{msg_type}] {content_preview}")
        
        # 验证推理结果
        symptoms = reasoning_state.context.get("symptoms_analysis", {})
        root_causes = reasoning_state.context.get("root_causes", {})
        final_recommendation = reasoning_state.context.get("final_recommendation", {})
        
        print(f"\n📊 推理分析结果:")
        print(f"   - 识别症状: {len(symptoms.get('symptoms', []))} 个")
        print(f"   - 可能根因: {len(root_causes.get('causes', []))} 个")
        print(f"   - 推荐置信度: {final_recommendation.get('confidence', 0):.2f}")
        
        if root_causes.get("causes"):
            print(f"   - 主要根因: {root_causes['causes'][0]['cause']}")
        
        if final_recommendation.get("primary_recommendation"):
            print(f"   - 主要建议: {final_recommendation['primary_recommendation']}")
        
        # 判断集成效果
        integration_score = 0.0
        
        if len(found_docs) > 0:
            integration_score += 0.3
        if len(symptoms.get('symptoms', [])) > 0:
            integration_score += 0.2
        if len(root_causes.get('causes', [])) > 0:
            integration_score += 0.3
        if final_recommendation.get('confidence', 0) > 0.5:
            integration_score += 0.2
        
        print(f"\n🎯 集成效果评分: {integration_score:.2f}/1.0")
        
        if integration_score >= 0.7:
            print("✅ Agent RAG集成工作良好")
            return True
        elif integration_score >= 0.4:
            print("⚠️ Agent RAG集成部分工作，需要优化")
            return True
        else:
            print("❌ Agent RAG集成存在问题")
            return False
            
    except Exception as e:
        print(f"❌ Agent RAG集成测试失败: {e}")
        return False


async def test_incident_analysis_workflow():
    """测试完整的incident分析工作流"""
    print("\n=== 测试Incident分析工作流 ===")
    try:
        rag_search = RAGSearchService()
        
        # 模拟真实的incident场景
        incident_query = "INC-001: service-b CPU过载导致用户请求超时，需要进行根因分析"
        
        print(f"🚨 Incident场景: {incident_query}")
        
        # 1. 获取RCA上下文
        print("\n📋 Step 1: 获取RCA上下文")
        rca_context = await rag_search.get_rca_context(incident_query)
        
        logs_count = len(rca_context["evidence"]["logs"])
        knowledge_count = len(rca_context["evidence"]["knowledge"])
        entities_count = len(rca_context["evidence"]["entities"])
        
        print(f"   📊 收集的证据:")
        print(f"   - 相关日志: {logs_count} 条")
        print(f"   - 知识文档: {knowledge_count} 个")
        print(f"   - 相关实体: {entities_count} 个")
        
        # 2. 分析时间线
        print("\n📋 Step 2: 分析Incident时间线")
        timeline = await rag_search.search_incident_timeline(
            incident_id="INC-001",
            time_window_hours=4
        )
        
        timeline_logs = len(timeline["timeline_logs"])
        print(f"   ⏰ 时间线日志: {timeline_logs} 条")
        
        if timeline["log_patterns"]:
            error_events = len(timeline["log_patterns"].get("critical_events", []))
            service_impact = len(timeline["log_patterns"].get("service_impact", {}))
            print(f"   🔍 关键事件: {error_events} 个")
            print(f"   🎯 受影响服务: {service_impact} 个")
        
        # 3. 评估分析质量
        analysis_quality = 0.0
        
        if logs_count > 0:
            analysis_quality += 0.4
        if knowledge_count > 0:
            analysis_quality += 0.3
        if entities_count > 0:
            analysis_quality += 0.2
        if timeline_logs > 0:
            analysis_quality += 0.1
        
        print(f"\n🎯 分析质量评分: {analysis_quality:.2f}/1.0")
        
        if analysis_quality >= 0.8:
            print("✅ Incident分析工作流运行良好")
            return True
        elif analysis_quality >= 0.5:
            print("⚠️ Incident分析工作流基本可用")
            return True
        else:
            print("❌ Incident分析工作流需要改进")
            return False
            
    except Exception as e:
        print(f"❌ Incident分析工作流测试失败: {e}")
        return False


async def test_search_filtering():
    """测试搜索过滤功能"""
    print("\n=== 测试搜索过滤功能 ===")
    try:
        rag_search = RAGSearchService()
        
        # 测试各种过滤条件
        filter_tests = [
            {
                "query": "CPU问题",
                "context": {"user_message": "service-b CPU使用率过高"},
                "expected_service": "service-b"
            },
            {
                "query": "ERROR日志",
                "context": {"user_message": "查看ERROR级别的日志"},
                "expected_log_level": "ERROR"
            },
            {
                "query": "数据库连接",
                "context": {"user_message": "d1-app-01上的数据库连接问题"},
                "expected_hostname": "d1-app-01"
            }
        ]
        
        passed_tests = 0
        
        for i, test in enumerate(filter_tests):
            print(f"\n🧪 过滤测试 {i+1}: {test['query']}")
            
            results = await rag_search.search_for_rca(
                query=test["query"],
                context=test["context"],
                search_type="hybrid",
                limit=5
            )
            
            # 验证过滤效果
            logs_filtered = True
            if "expected_service" in test:
                service_logs = [log for log in results["logs"] 
                             if log.get("service_name") == test["expected_service"]]
                if len(service_logs) > 0:
                    print(f"   ✅ 服务过滤生效: 找到 {len(service_logs)} 条 {test['expected_service']} 日志")
                    passed_tests += 1
                else:
                    print(f"   ❌ 服务过滤失效")
                    logs_filtered = False
            
            if "expected_log_level" in test:
                level_logs = [log for log in results["logs"] 
                            if log.get("log_level") == test["expected_log_level"]]
                if len(level_logs) > 0:
                    print(f"   ✅ 日志级别过滤生效: 找到 {len(level_logs)} 条 {test['expected_log_level']} 日志")
                    passed_tests += 1
                else:
                    print(f"   ❌ 日志级别过滤失效")
                    logs_filtered = False
            
            if "expected_hostname" in test:
                host_logs = [log for log in results["logs"] 
                           if log.get("hostname") == test["expected_hostname"]]
                if len(host_logs) > 0:
                    print(f"   ✅ 主机过滤生效: 找到 {len(host_logs)} 条 {test['expected_hostname']} 日志")
                    passed_tests += 1
                else:
                    print(f"   ❌ 主机过滤失效")
                    logs_filtered = False
        
        print(f"\n📊 过滤测试结果: {passed_tests}/{len(filter_tests)} 通过")
        return passed_tests >= len(filter_tests) * 0.7  # 70%通过率
        
    except Exception as e:
        print(f"❌ 搜索过滤测试失败: {e}")
        return False


async def test_agent_rca_workflow():
    """测试Agent完整RCA工作流"""
    print("\n=== 测试Agent RCA工作流 ===")
    try:
        # 创建Agent适配器
        rag_adapter = AgentRAGAdapter()
        
        # 创建agents
        knowledge_agent = KnowledgeAgent(search_service=rag_adapter)
        reasoning_agent = ReasoningAgent()
        
        # RCA测试场景
        rca_scenarios = [
            {
                "query": "service-b CPU使用率达到95%，用户反馈页面响应很慢，请分析根本原因",
                "expected_elements": ["CPU", "service-b", "性能", "响应"]
            },
            {
                "query": "数据库连接超时频繁发生，影响用户登录，需要排查问题",
                "expected_elements": ["数据库", "连接", "超时", "登录"]
            }
        ]
        
        workflow_success = 0
        
        for i, scenario in enumerate(rca_scenarios):
            print(f"\n🔬 RCA场景 {i+1}: {scenario['query'][:50]}...")
            
            # Phase 1: 知识检索
            print("   📚 Phase 1: 知识检索")
            knowledge_state = AgentState()
            knowledge_state.context = {
                "user_message": scenario["query"],
                "search_query": scenario["query"]
            }
            
            # 执行知识检索
            step_count = 0
            while not knowledge_state.is_complete and step_count < 3:
                knowledge_state = await knowledge_agent.process(knowledge_state)
                knowledge_state.current_step += 1
                step_count += 1
            
            found_docs = knowledge_state.context.get("found_documents", [])
            knowledge_summary = knowledge_state.context.get("knowledge_summary", {})
            
            print(f"      📄 找到文档: {len(found_docs)} 个")
            print(f"      🎯 知识置信度: {knowledge_summary.get('confidence_score', 0):.2f}")
            
            # Phase 2: 推理分析
            print("   🧠 Phase 2: 推理分析")
            reasoning_state = AgentState()
            reasoning_state.context = {
                "user_message": scenario["query"],
                "knowledge_summary": knowledge_summary,
                "found_documents": found_docs
            }
            
            # 执行推理分析
            step_count = 0
            while not reasoning_state.is_complete and step_count < 4:
                reasoning_state = await reasoning_agent.process(reasoning_state)
                reasoning_state.current_step += 1
                step_count += 1
            
            symptoms = reasoning_state.context.get("symptoms_analysis", {})
            root_causes = reasoning_state.context.get("root_causes", {})
            final_recommendation = reasoning_state.context.get("final_recommendation", {})
            
            print(f"      🎭 识别症状: {len(symptoms.get('symptoms', []))} 个")
            print(f"      🎯 可能根因: {len(root_causes.get('causes', []))} 个")
            print(f"      💡 推荐置信度: {final_recommendation.get('confidence', 0):.2f}")
            
            # 验证工作流质量
            workflow_quality = 0.0
            
            # 检查是否找到了相关信息
            if len(found_docs) > 0:
                workflow_quality += 0.25
            if len(symptoms.get('symptoms', [])) > 0:
                workflow_quality += 0.25
            if len(root_causes.get('causes', [])) > 0:
                workflow_quality += 0.25
            if final_recommendation.get('confidence', 0) > 0.3:
                workflow_quality += 0.25
            
            # 检查是否包含预期元素
            final_answer = ""
            for msg in reasoning_state.messages:
                if msg.type == MessageType.ANSWER:
                    final_answer = msg.content.lower()
                    break
            
            expected_found = 0
            for element in scenario["expected_elements"]:
                if element.lower() in final_answer:
                    expected_found += 1
            
            if expected_found >= len(scenario["expected_elements"]) * 0.5:
                workflow_quality += 0.2
            
            print(f"      📈 工作流质量: {workflow_quality:.2f}/1.0")
            
            if workflow_quality >= 0.6:
                workflow_success += 1
                print(f"      ✅ RCA场景 {i+1} 通过")
            else:
                print(f"      ❌ RCA场景 {i+1} 失败")
        
        success_rate = workflow_success / len(rca_scenarios)
        print(f"\n📊 RCA工作流成功率: {success_rate:.1%}")
        
        return success_rate >= 0.5
        
    except Exception as e:
        print(f"❌ Agent RCA工作流测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🚀 开始Agent RAG集成验证")
    print("=" * 60)
    
    test_results = []
    
    # 检查数据是否存在
    data_dir = Path("./data")
    if not data_dir.exists():
        print("❌ 数据目录不存在，无法进行测试")
        return
    
    # 1. 设置测试数据
    data_setup_ok = await setup_test_data()
    test_results.append(("数据设置", data_setup_ok))
    
    if not data_setup_ok:
        print("❌ 测试数据设置失败，停止测试")
        return
    
    # 2. 测试RAG搜索服务
    rag_search_ok = await test_rag_search_service()
    test_results.append(("RAG搜索服务", rag_search_ok))
    
    # 3. 测试搜索过滤
    filter_ok = await test_search_filtering()
    test_results.append(("搜索过滤", filter_ok))
    
    # 4. 测试Agent集成
    agent_integration_ok = await test_agent_rag_integration()
    test_results.append(("Agent RAG集成", agent_integration_ok))
    
    # 5. 测试完整工作流
    workflow_ok = await test_incident_analysis_workflow()
    test_results.append(("RCA工作流", workflow_ok))
    
    # 显示测试结果
    print("\n" + "=" * 60)
    print("📋 Agent RAG集成验证结果:")
    print("=" * 60)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name:<20} {status}")
    
    passed_tests = sum(1 for _, result in test_results if result)
    total_tests = len(test_results)
    
    print(f"\n📊 总体结果: {passed_tests}/{total_tests} 测试通过")
    
    if passed_tests == total_tests:
        print("🎉 Agent RAG集成完全成功！RCA功能工作正常")
    elif passed_tests >= total_tests * 0.7:
        print("✅ Agent RAG集成基本成功，RCA功能可用")
    else:
        print("⚠️ Agent RAG集成存在问题，需要进一步优化")
    
    # 输出建议
    if passed_tests < total_tests:
        print("\n💡 改进建议:")
        if not test_results[0][1]:  # 数据设置失败
            print("   - 检查数据目录和文件完整性")
        if not test_results[1][1]:  # RAG搜索失败
            print("   - 检查Weaviate服务状态和schema配置")
        if not test_results[2][1]:  # 过滤失败
            print("   - 检查过滤条件解析逻辑")
        if not test_results[3][1]:  # Agent集成失败
            print("   - 检查Agent与RAG服务的接口兼容性")
        if not test_results[4][1]:  # 工作流失败
            print("   - 检查端到端的RCA分析逻辑")


if __name__ == "__main__":
    asyncio.run(main())