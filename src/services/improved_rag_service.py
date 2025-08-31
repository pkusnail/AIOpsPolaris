"""
改进的RAG搜索服务 - 包含hybrid search和rerank
解决向量维度不匹配和搜索结果为空的问题
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import weaviate
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)


class ImprovedRAGService:
    """改进的RAG搜索服务，支持hybrid search和rerank"""
    
    def __init__(self):
        self.client = weaviate.Client("http://localhost:8080")
        # 使用与数据管道相同的模型
        self.sentence_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def encode_query(self, query: str) -> List[float]:
        """编码查询为384维向量"""
        try:
            embedding = self.sentence_model.encode(query)
            return embedding.tolist()
        except Exception as e:
            self.logger.error(f"编码查询失败: {e}")
            return []
    
    async def vector_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """向量相似性搜索"""
        try:
            query_vector = self.encode_query(query)
            if not query_vector:
                return []
            
            result = (
                self.client.query
                .get("EmbeddingCollection", ["content", "service_name", "source_type", "timestamp", "log_file"])
                .with_near_vector({"vector": query_vector, "certainty": 0.1})
                .with_limit(limit)
                .with_additional(["certainty", "distance"])
                .do()
            )
            
            if "data" in result and "Get" in result["data"] and "EmbeddingCollection" in result["data"]["Get"]:
                documents = result["data"]["Get"]["EmbeddingCollection"] or []
                if documents is None:
                    documents = []
                
                # 添加搜索类型和得分
                for doc in documents:
                    doc["search_type"] = "vector"
                    doc["score"] = doc.get("_additional", {}).get("certainty", 0.0)
                    
                self.logger.info(f"向量搜索找到 {len(documents)} 个结果")
                return documents
            else:
                self.logger.warning("向量搜索返回空结果")
                return []
                
        except Exception as e:
            self.logger.error(f"向量搜索失败: {e}")
            return []
    
    async def bm25_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """BM25全文搜索"""
        try:
            result = (
                self.client.query
                .get("FullTextCollection", ["content", "service_name", "source_type", "timestamp", "log_file"])
                .with_bm25(query=query)
                .with_limit(limit)
                .with_additional(["score"])
                .do()
            )
            
            self.logger.info(f"BM25查询结果: {result}")
            
            if "data" in result and "Get" in result["data"] and "FullTextCollection" in result["data"]["Get"]:
                documents = result["data"]["Get"]["FullTextCollection"] or []
                if documents is None:
                    documents = []
                
                # 添加搜索类型和得分
                for doc in documents:
                    doc["search_type"] = "bm25"
                    doc["score"] = float(doc.get("_additional", {}).get("score", 0.0))
                    
                self.logger.info(f"BM25搜索找到 {len(documents)} 个结果")
                return documents
            else:
                self.logger.warning(f"BM25搜索返回空结果，result keys: {result.keys() if result else 'None'}")
                return []
                
        except Exception as e:
            self.logger.error(f"BM25搜索失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def rerank_results(self, vector_results: List[Dict], bm25_results: List[Dict], 
                      query: str, alpha: float = 0.6) -> List[Dict[str, Any]]:
        """
        重排序hybrid search结果
        alpha: 向量搜索权重 (0-1), (1-alpha)为BM25权重
        """
        try:
            # 合并结果，去重
            all_results = {}
            
            # 添加向量搜索结果
            for doc in vector_results:
                content = doc.get('content', '')
                if content not in all_results:
                    all_results[content] = doc.copy()
                    all_results[content]['vector_score'] = doc.get('score', 0.0)
                    all_results[content]['bm25_score'] = 0.0
                else:
                    all_results[content]['vector_score'] = doc.get('score', 0.0)
            
            # 添加BM25搜索结果
            for doc in bm25_results:
                content = doc.get('content', '')
                if content not in all_results:
                    all_results[content] = doc.copy()
                    all_results[content]['vector_score'] = 0.0
                    all_results[content]['bm25_score'] = doc.get('score', 0.0)
                else:
                    all_results[content]['bm25_score'] = doc.get('score', 0.0)
            
            # 计算混合得分并重排序
            ranked_results = []
            for content, doc in all_results.items():
                # 归一化得分 (简单的线性归一化)
                vector_score = min(doc['vector_score'], 1.0)  # certainty已经是0-1
                bm25_score = min(doc['bm25_score'] / 3.0, 1.0) if doc['bm25_score'] > 0 else 0  # 简单归一化
                
                # 计算加权混合得分
                hybrid_score = alpha * vector_score + (1 - alpha) * bm25_score
                
                doc['hybrid_score'] = hybrid_score
                doc['search_type'] = 'hybrid'
                ranked_results.append(doc)
            
            # 按混合得分排序
            ranked_results.sort(key=lambda x: x['hybrid_score'], reverse=True)
            
            self.logger.info(f"重排序完成，合并结果: {len(ranked_results)} 个")
            return ranked_results
            
        except Exception as e:
            self.logger.error(f"重排序失败: {e}")
            # 如果重排序失败，返回向量搜索结果
            return vector_results + bm25_results
    
    async def hybrid_search(self, query: str, limit: int = 20, alpha: float = 0.6) -> Dict[str, Any]:
        """
        混合搜索: 结合向量搜索和BM25搜索，并重排序
        """
        try:
            self.logger.info(f"开始混合搜索: '{query}'")
            
            # 并行执行向量搜索和BM25搜索
            vector_task = self.vector_search(query, limit // 2)
            bm25_task = self.bm25_search(query, limit // 2)
            
            vector_results, bm25_results = await asyncio.gather(vector_task, bm25_task)
            
            # 重排序结果
            ranked_results = self.rerank_results(vector_results, bm25_results, query, alpha)
            
            # 截取最终结果
            final_results = ranked_results[:limit]
            
            return {
                "results": final_results,
                "total_results": len(final_results),
                "vector_results": len(vector_results),
                "bm25_results": len(bm25_results),
                "search_type": "hybrid_reranked",
                "query": query
            }
            
        except Exception as e:
            self.logger.error(f"混合搜索失败: {e}")
            return {
                "results": [],
                "total_results": 0,
                "vector_results": 0,
                "bm25_results": 0,
                "search_type": "hybrid_failed",
                "query": query,
                "error": str(e)
            }
    
    async def search_for_service(self, service_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """专门搜索特定服务的日志"""
        try:
            # 使用service_name作为查询，应该能匹配到相关服务的日志
            result = await self.hybrid_search(f"{service_name}", limit=limit)
            
            # 过滤结果，优先返回匹配服务名的
            service_results = []
            other_results = []
            
            for doc in result["results"]:
                doc_service = doc.get("service_name", "").lower()
                if service_name.lower() in doc_service:
                    service_results.append(doc)
                else:
                    other_results.append(doc)
            
            # 优先返回匹配的服务，然后是其他相关结果
            final_results = service_results + other_results[:limit-len(service_results)]
            
            self.logger.info(f"服务搜索 '{service_name}': 找到 {len(final_results)} 个结果")
            return final_results
            
        except Exception as e:
            self.logger.error(f"服务搜索失败: {e}")
            return []


# 简化的测试函数
async def test_improved_rag():
    """测试改进的RAG服务"""
    print("=== 测试改进的RAG服务 ===")
    
    service = ImprovedRAGService()
    
    # 测试queries
    test_queries = [
        "service-b",
        "service-b CPU",
        "CPU过载",
        "数据库连接"
    ]
    
    for query in test_queries:
        print(f"\n🔍 测试查询: '{query}'")
        
        # 测试混合搜索
        result = await service.hybrid_search(query, limit=5)
        
        print(f"   总结果: {result['total_results']}")
        print(f"   向量结果: {result['vector_results']}")
        print(f"   BM25结果: {result['bm25_results']}")
        
        # 显示前3个结果
        for i, doc in enumerate(result["results"][:3]):
            content = doc.get("content", "")[:80]
            service_name = doc.get("service_name", "N/A")
            score = doc.get("hybrid_score", 0.0)
            print(f"   结果{i+1} (得分{score:.3f}): [{service_name}] {content}...")


if __name__ == "__main__":
    asyncio.run(test_improved_rag())