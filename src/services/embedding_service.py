"""
嵌入服务
处理文本向量化和语义相似度计算
"""

import math
import random
from typing import List, Dict, Any, Optional, Union
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)


class EmbeddingService:
    """嵌入服务类 - 简化版本，用于演示目的"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.cache_dir = Path("cache/embeddings")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize_model()
    
    def _initialize_model(self):
        """初始化嵌入模型 - 简化版本，使用随机向量模拟"""
        try:
            # 简化实现：使用随机种子生成一致的向量
            self.embedding_dim = 768  # 标准BERT维度
            self.max_seq_length = 512
            
            self.logger.info(f"Initialized simple embedding service with {self.embedding_dim}d vectors")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize embedding model: {e}")
            raise
    
    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _load_from_cache(self, cache_key: str) -> Optional[List[float]]:
        """从缓存加载向量"""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load cache: {e}")
        return None
    
    def _save_to_cache(self, cache_key: str, embedding: List[float]):
        """保存向量到缓存"""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(embedding, f)
        except Exception as e:
            self.logger.warning(f"Failed to save cache: {e}")
    
    def _encode_single(self, text: str) -> List[float]:
        """编码单个文本 - 简化版本，使用哈希生成伪向量"""
        try:
            # 检查缓存
            cache_key = self._get_cache_key(text)
            cached_embedding = self._load_from_cache(cache_key)
            if cached_embedding is not None:
                return cached_embedding
            
            # 使用文本哈希生成一致的向量
            text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
            
            # 转换为数字种子
            seed = int(text_hash[:8], 16)
            random.seed(seed)
            
            # 生成随机向量
            embedding = [random.gauss(0, 1) for _ in range(self.embedding_dim)]
            
            # L2归一化
            norm = math.sqrt(sum(x*x for x in embedding))
            if norm > 0:
                embedding = [x / norm for x in embedding]
            
            # 保存到缓存
            self._save_to_cache(cache_key, embedding)
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"Failed to encode text: {e}")
            raise
    
    def _encode_batch(self, texts: List[str]) -> List[List[float]]:
        """批量编码文本 - 简化版本"""
        try:
            embeddings = []
            for text in texts:
                embedding = self._encode_single(text)
                embeddings.append(embedding)
            
            return embeddings
            
        except Exception as e:
            self.logger.error(f"Failed to encode batch: {e}")
            raise
    
    async def encode_text(self, text: str) -> List[float]:
        """异步编码单个文本"""
        try:
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                self.executor, 
                self._encode_single, 
                text
            )
            return embedding.tolist()
            
        except Exception as e:
            self.logger.error(f"Failed to encode text asynchronously: {e}")
            raise
    
    async def encode_texts(self, texts: List[str]) -> List[List[float]]:
        """异步批量编码文本"""
        try:
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                self.executor,
                self._encode_batch,
                texts
            )
            return embeddings
            
        except Exception as e:
            self.logger.error(f"Failed to encode texts asynchronously: {e}")
            raise
    
    def cosine_similarity(
        self, 
        embedding1: List[float], 
        embedding2: List[float]
    ) -> float:
        """计算余弦相似度"""
        try:
            # 计算点积
            dot_product = sum(x * y for x, y in zip(embedding1, embedding2))
            
            # 计算向量长度
            norm1 = math.sqrt(sum(x * x for x in embedding1))
            norm2 = math.sqrt(sum(x * x for x in embedding2))
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate cosine similarity: {e}")
            return 0.0
    
    def euclidean_distance(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """计算欧氏距离"""
        try:
            # 计算欧氏距离
            distance = math.sqrt(sum((x - y) ** 2 for x, y in zip(embedding1, embedding2)))
            return float(distance)
            
        except Exception as e:
            self.logger.error(f"Failed to calculate euclidean distance: {e}")
            return float('inf')
    
    def find_most_similar(
        self,
        query_embedding: List[float],
        embeddings: List[List[float]],
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """找到最相似的向量"""
        try:
            similarities = []
            
            for i, embedding in enumerate(embeddings):
                similarity = self.cosine_similarity(query_embedding, embedding)
                if similarity >= threshold:
                    similarities.append({
                        "index": i,
                        "similarity": similarity
                    })
            
            # 按相似度排序
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            
            return similarities
            
        except Exception as e:
            self.logger.error(f"Failed to find most similar: {e}")
            return []
    
    async def encode_knowledge_document(
        self,
        title: str,
        content: str,
        combine_strategy: str = "weighted"
    ) -> List[float]:
        """编码知识文档（标题+内容）"""
        try:
            if combine_strategy == "weighted":
                # 标题权重更高
                combined_text = f"{title} {title} {content}"
            elif combine_strategy == "separate":
                # 分别编码后平均
                title_embedding = await self.encode_text(title)
                content_embedding = await self.encode_text(content)
                
                # 加权平均 (标题权重0.3，内容权重0.7)
                title_weight = 0.3
                content_weight = 0.7
                
                combined_embedding = [
                    title_weight * t + content_weight * c 
                    for t, c in zip(title_embedding, content_embedding)
                ]
                
                # 重新归一化
                norm = math.sqrt(sum(x * x for x in combined_embedding))
                if norm > 0:
                    combined_embedding = [x / norm for x in combined_embedding]
                
                return combined_embedding
            else:
                # 默认策略：直接拼接
                combined_text = f"{title}\n{content}"
            
            return await self.encode_text(combined_text)
            
        except Exception as e:
            self.logger.error(f"Failed to encode knowledge document: {e}")
            raise
    
    async def encode_query(
        self,
        query: str,
        enhance_query: bool = True
    ) -> List[float]:
        """编码查询文本"""
        try:
            if enhance_query:
                # 查询增强：添加一些运维相关的上下文
                enhanced_query = f"运维问题 故障排查 {query}"
                return await self.encode_text(enhanced_query)
            else:
                return await self.encode_text(query)
                
        except Exception as e:
            self.logger.error(f"Failed to encode query: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        try:
            return {
                "model_name": "simple_hash_embeddings",
                "device": "cpu",
                "max_seq_length": self.max_seq_length,
                "embedding_dimension": self.embedding_dim,
                "vocabulary_size": None
            }
        except Exception as e:
            self.logger.error(f"Failed to get model info: {e}")
            return {}
    
    async def compute_text_similarity(
        self,
        text1: str,
        text2: str
    ) -> float:
        """计算两个文本的相似度"""
        try:
            embedding1 = await self.encode_text(text1)
            embedding2 = await self.encode_text(text2)
            
            return self.cosine_similarity(embedding1, embedding2)
            
        except Exception as e:
            self.logger.error(f"Failed to compute text similarity: {e}")
            return 0.0
    
    async def cluster_texts(
        self,
        texts: List[str],
        n_clusters: int = 5,
        method: str = "simple"
    ) -> Dict[str, Any]:
        """文本聚类 - 简化版本"""
        try:
            # 生成嵌入
            embeddings = await self.encode_texts(texts)
            
            # 简单聚类：基于相似度阈值
            clusters = {}
            cluster_labels = []
            current_cluster = 0
            
            for i, embedding in enumerate(embeddings):
                assigned = False
                
                # 检查是否与现有聚类中心相似
                for cluster_id, cluster_items in clusters.items():
                    if cluster_items:
                        # 计算与聚类中心的相似度
                        center_embedding = cluster_items[0]["embedding"]
                        similarity = self.cosine_similarity(embedding, center_embedding)
                        
                        if similarity > 0.8:  # 相似度阈值
                            clusters[cluster_id].append({
                                "index": i,
                                "text": texts[i],
                                "embedding": embedding
                            })
                            cluster_labels.append(cluster_id)
                            assigned = True
                            break
                
                # 如果没有分配到现有聚类，创建新聚类
                if not assigned:
                    clusters[current_cluster] = [{
                        "index": i,
                        "text": texts[i],
                        "embedding": embedding
                    }]
                    cluster_labels.append(current_cluster)
                    current_cluster += 1
            
            return {
                "clusters": clusters,
                "labels": cluster_labels,
                "n_clusters": len(clusters),
                "silhouette_score": 0.5  # 模拟得分
            }
            
        except Exception as e:
            self.logger.error(f"Failed to cluster texts: {e}")
            return {"clusters": {}, "labels": [], "n_clusters": 0, "silhouette_score": 0.0}
    
    def clear_cache(self):
        """清空缓存"""
        try:
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info("Embedding cache cleared")
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            cache_files = list(self.cache_dir.glob("*.pkl"))
            total_size = sum(f.stat().st_size for f in cache_files)
            
            return {
                "cache_files": len(cache_files),
                "total_size_mb": total_size / (1024 * 1024),
                "cache_dir": str(self.cache_dir)
            }
        except Exception as e:
            self.logger.error(f"Failed to get cache stats: {e}")
            return {"cache_files": 0, "total_size_mb": 0.0, "cache_dir": str(self.cache_dir)}
    
    def close(self):
        """关闭服务"""
        if self.executor:
            self.executor.shutdown(wait=True)
            self.logger.info("Embedding service closed")