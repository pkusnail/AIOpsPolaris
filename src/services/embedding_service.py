"""
嵌入服务
处理文本向量化和语义相似度计算
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any, Optional, Union
import logging
import torch
from transformers import AutoTokenizer, AutoModel
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import pickle
from pathlib import Path

from config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """嵌入服务类"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.cache_dir = Path("cache/embeddings")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize_model()
    
    def _initialize_model(self):
        """初始化嵌入模型"""
        try:
            model_name = settings.embedding.model_name
            device = settings.embedding.device
            
            # 使用sentence-transformers
            self.model = SentenceTransformer(
                model_name,
                device=device
            )
            
            # 设置最大序列长度
            self.model.max_seq_length = settings.embedding.max_seq_length
            
            self.logger.info(f"Loaded embedding model: {model_name} on {device}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize embedding model: {e}")
            raise
    
    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _load_from_cache(self, cache_key: str) -> Optional[np.ndarray]:
        """从缓存加载向量"""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load cache: {e}")
        return None
    
    def _save_to_cache(self, cache_key: str, embedding: np.ndarray):
        """保存向量到缓存"""
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(embedding, f)
        except Exception as e:
            self.logger.warning(f"Failed to save cache: {e}")
    
    def _encode_single(self, text: str) -> np.ndarray:
        """编码单个文本"""
        try:
            # 检查缓存
            cache_key = self._get_cache_key(text)
            cached_embedding = self._load_from_cache(cache_key)
            if cached_embedding is not None:
                return cached_embedding
            
            # 生成嵌入
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True  # L2归一化
            )
            
            # 保存到缓存
            self._save_to_cache(cache_key, embedding)
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"Failed to encode text: {e}")
            raise
    
    def _encode_batch(self, texts: List[str]) -> List[np.ndarray]:
        """批量编码文本"""
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=settings.embedding.batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=len(texts) > 100
            )
            
            # 缓存结果
            for text, embedding in zip(texts, embeddings):
                cache_key = self._get_cache_key(text)
                self._save_to_cache(cache_key, embedding)
            
            return embeddings.tolist()
            
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
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # 计算余弦相似度
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
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
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            distance = np.linalg.norm(vec1 - vec2)
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
                norm = np.linalg.norm(combined_embedding)
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
                "model_name": settings.embedding.model_name,
                "device": settings.embedding.device,
                "max_seq_length": settings.embedding.max_seq_length,
                "embedding_dimension": self.model.get_sentence_embedding_dimension(),
                "vocabulary_size": len(self.model.tokenizer.get_vocab()) if hasattr(self.model, 'tokenizer') else None
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
        method: str = "kmeans"
    ) -> Dict[str, Any]:
        """文本聚类"""
        try:
            from sklearn.cluster import KMeans, DBSCAN
            from sklearn.metrics import silhouette_score
            
            # 生成嵌入
            embeddings = await self.encode_texts(texts)
            embeddings_array = np.array(embeddings)
            
            if method == "kmeans":
                clusterer = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            elif method == "dbscan":
                clusterer = DBSCAN(eps=0.3, min_samples=2)
            else:
                raise ValueError(f"Unknown clustering method: {method}")
            
            # 执行聚类
            loop = asyncio.get_event_loop()
            cluster_labels = await loop.run_in_executor(
                self.executor,
                clusterer.fit_predict,
                embeddings_array
            )
            
            # 计算轮廓系数
            if len(set(cluster_labels)) > 1:
                silhouette = silhouette_score(embeddings_array, cluster_labels)
            else:
                silhouette = 0.0
            
            # 组织结果
            clusters = {}
            for i, label in enumerate(cluster_labels):
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append({
                    "index": i,
                    "text": texts[i],
                    "embedding": embeddings[i]
                })
            
            return {
                "clusters": clusters,
                "labels": cluster_labels.tolist(),
                "n_clusters": len(set(cluster_labels)),
                "silhouette_score": silhouette
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