"""
知识数据处理Pipeline
从GitLab/Jira/Wiki数据源读取并在Weaviate两个Collection中建立索引
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from .rag_vector_service import RAGVectorService
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class KnowledgePipeline:
    """知识数据处理管道类"""
    
    def __init__(self):
        self.rag_service = RAGVectorService()
        self.embedding_service = EmbeddingService()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def process_wiki_data(self, wiki_dir: str = "./data/wiki/") -> Dict[str, Any]:
        """处理Wiki知识文档"""
        try:
            stats = {
                'total_files': 0,
                'processed_docs': 0,
                'error_count': 0
            }
            
            wiki_path = Path(wiki_dir)
            if not wiki_path.exists():
                raise FileNotFoundError(f"Wiki directory not found: {wiki_dir}")
            
            # 处理JSON格式的wiki文档
            json_files = list(wiki_path.glob("*.json"))
            md_files = list(wiki_path.glob("*.md"))
            
            stats['total_files'] = len(json_files) + len(md_files)
            
            # 处理JSON文件
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        wiki_data = json.load(f)
                    
                    if isinstance(wiki_data, list):
                        for doc in wiki_data:
                            await self._process_wiki_document(doc, str(json_file))
                            stats['processed_docs'] += 1
                    elif isinstance(wiki_data, dict):
                        await self._process_wiki_document(wiki_data, str(json_file))
                        stats['processed_docs'] += 1
                        
                except Exception as e:
                    self.logger.error(f"Failed to process wiki file {json_file}: {e}")
                    stats['error_count'] += 1
            
            # 处理Markdown文件
            for md_file in md_files:
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 创建文档对象
                    doc = {
                        'title': md_file.stem,
                        'content': content,
                        'category': '技术文档',
                        'tags': ['markdown', '架构'],
                        'author': '技术团队',
                        'last_updated': datetime.utcnow().isoformat()
                    }
                    
                    await self._process_wiki_document(doc, str(md_file))
                    stats['processed_docs'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Failed to process markdown file {md_file}: {e}")
                    stats['error_count'] += 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to process wiki data: {e}")
            raise
    
    async def _process_wiki_document(self, doc: Dict[str, Any], file_path: str):
        """处理单个Wiki文档"""
        try:
            content = doc.get('content', '')
            title = doc.get('title', '')
            
            if not content and not title:
                return
            
            # 文档分块（如果内容过长）
            chunks = self._chunk_document(content, max_chunk_size=512)
            
            for idx, chunk in enumerate(chunks):
                source_id = f"wiki_{doc.get('id', '')}_{idx}"
                
                # 生成向量
                embedding = None
                try:
                    embedding = await self.embedding_service.encode_text(chunk)
                except Exception as e:
                    self.logger.warning(f"Failed to generate embedding for wiki chunk: {e}")
                
                # 提取关键词和实体
                keywords = self._extract_wiki_keywords(chunk, doc.get('tags', []))
                entities = self._extract_wiki_entities(chunk)
                
                # 解析时间戳
                timestamp = None
                if 'last_updated' in doc:
                    try:
                        timestamp = datetime.fromisoformat(doc['last_updated'].replace('Z', ''))
                    except:
                        timestamp = datetime.utcnow()
                else:
                    timestamp = datetime.utcnow()
                
                common_fields = {
                    'content': chunk,
                    'title': f"{title} (Part {idx + 1})" if len(chunks) > 1 else title,
                    'source_type': 'wiki',
                    'source_id': source_id,
                    'category': doc.get('category', '知识文档'),
                    'tags': keywords,
                    'author': doc.get('author', '系统'),
                    'timestamp': timestamp,
                    'metadata': {
                        'original_file': file_path,
                        'document_id': doc.get('id', ''),
                        'chunk_index': idx,
                        'total_chunks': len(chunks)
                    }
                }
                
                # 索引到EmbeddingCollection
                if embedding:
                    await self.rag_service.add_embedding_document(
                        vector=embedding,
                        chunk_index=idx,
                        chunk_size=len(chunk),
                        parent_id=doc.get('id', ''),
                        **common_fields
                    )
                
                # 索引到FullTextCollection
                await self.rag_service.add_fulltext_document(
                    keywords=keywords,
                    entities=entities,
                    **common_fields
                )
            
        except Exception as e:
            self.logger.error(f"Failed to process wiki document: {e}")
    
    async def process_gitlab_data(self, gitlab_dir: str = "./data/gitlab/") -> Dict[str, Any]:
        """处理GitLab数据"""
        try:
            stats = {'processed_count': 0, 'error_count': 0}
            
            gitlab_path = Path(gitlab_dir)
            json_files = list(gitlab_path.glob("*.json"))
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        gitlab_data = json.load(f)
                    
                    if isinstance(gitlab_data, list):
                        for item in gitlab_data:
                            await self._process_gitlab_item(item, str(json_file))
                            stats['processed_count'] += 1
                    elif isinstance(gitlab_data, dict):
                        await self._process_gitlab_item(gitlab_data, str(json_file))
                        stats['processed_count'] += 1
                        
                except Exception as e:
                    self.logger.error(f"Failed to process GitLab file {json_file}: {e}")
                    stats['error_count'] += 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to process GitLab data: {e}")
            raise
    
    async def _process_gitlab_item(self, item: Dict[str, Any], file_path: str):
        """处理单个GitLab项目/MR"""
        try:
            # 构建文档内容
            title = item.get('title', '')
            description = item.get('description', '')
            
            content_parts = []
            if title:
                content_parts.append(f"标题: {title}")
            if description:
                content_parts.append(f"描述: {description}")
            
            # 添加变更文件信息
            if 'files_changed' in item:
                files_text = "变更文件: " + ", ".join(item['files_changed'])
                content_parts.append(files_text)
            
            # 添加标签信息
            if 'labels' in item:
                labels_text = "标签: " + ", ".join(item['labels'])
                content_parts.append(labels_text)
            
            content = "\n".join(content_parts)
            
            if not content:
                return
            
            source_id = f"gitlab_{item.get('id', '')}"
            
            # 生成向量
            embedding = None
            try:
                embedding = await self.embedding_service.encode_text(content)
            except Exception as e:
                self.logger.warning(f"Failed to generate embedding for GitLab item: {e}")
            
            # 提取关键词和实体
            keywords = self._extract_gitlab_keywords(item)
            entities = self._extract_gitlab_entities(item)
            
            # 解析时间戳
            timestamp = datetime.utcnow()
            if 'created_at' in item:
                try:
                    timestamp = datetime.fromisoformat(item['created_at'].replace('Z', ''))
                except:
                    pass
            
            common_fields = {
                'content': content,
                'title': title,
                'source_type': 'gitlab',
                'source_id': source_id,
                'category': '代码变更',
                'tags': keywords,
                'author': item.get('author', ''),
                'timestamp': timestamp,
                'metadata': {
                    'original_file': file_path,
                    'merge_request_id': item.get('id'),
                    'files_changed': item.get('files_changed', []),
                    'labels': item.get('labels', [])
                }
            }
            
            # 双重索引
            if embedding:
                await self.rag_service.add_embedding_document(
                    vector=embedding,
                    **common_fields
                )
            
            await self.rag_service.add_fulltext_document(
                keywords=keywords,
                entities=entities,
                **common_fields
            )
            
        except Exception as e:
            self.logger.error(f"Failed to process GitLab item: {e}")
    
    async def process_jira_data(self, jira_dir: str = "./data/jira/") -> Dict[str, Any]:
        """处理Jira工单数据"""
        try:
            stats = {'processed_count': 0, 'error_count': 0}
            
            jira_path = Path(jira_dir)
            json_files = list(jira_path.glob("*.json"))
            
            for json_file in json_files:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        jira_data = json.load(f)
                    
                    if isinstance(jira_data, list):
                        for item in jira_data:
                            await self._process_jira_item(item, str(json_file))
                            stats['processed_count'] += 1
                    elif isinstance(jira_data, dict):
                        await self._process_jira_item(jira_data, str(json_file))
                        stats['processed_count'] += 1
                        
                except Exception as e:
                    self.logger.error(f"Failed to process Jira file {json_file}: {e}")
                    stats['error_count'] += 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to process Jira data: {e}")
            raise
    
    async def _process_jira_item(self, item: Dict[str, Any], file_path: str):
        """处理单个Jira工单"""
        try:
            title = item.get('title', item.get('summary', ''))
            description = item.get('description', '')
            
            content_parts = []
            if title:
                content_parts.append(f"工单: {title}")
            if description:
                content_parts.append(f"描述: {description}")
            
            # 添加组件信息
            if 'components' in item:
                components_text = "组件: " + ", ".join(item['components'])
                content_parts.append(components_text)
            
            content = "\n".join(content_parts)
            
            if not content:
                return
            
            source_id = f"jira_{item.get('id', item.get('key', ''))}"
            
            # 生成向量
            embedding = None
            try:
                embedding = await self.embedding_service.encode_text(content)
            except Exception as e:
                self.logger.warning(f"Failed to generate embedding for Jira item: {e}")
            
            # 提取关键词和实体
            keywords = self._extract_jira_keywords(item)
            entities = self._extract_jira_entities(item)
            
            # 解析时间戳
            timestamp = datetime.utcnow()
            if 'created' in item:
                try:
                    timestamp = datetime.fromisoformat(item['created'].replace('Z', ''))
                except:
                    pass
            
            common_fields = {
                'content': content,
                'title': title,
                'source_type': 'jira',
                'source_id': source_id,
                'category': item.get('type', '工单'),
                'tags': keywords,
                'author': item.get('reporter', ''),
                'timestamp': timestamp,
                'metadata': {
                    'original_file': file_path,
                    'jira_key': item.get('key'),
                    'issue_id': item.get('id'),
                    'priority': item.get('priority'),
                    'status': item.get('status'),
                    'components': item.get('components', [])
                }
            }
            
            # 双重索引
            if embedding:
                await self.rag_service.add_embedding_document(
                    vector=embedding,
                    **common_fields
                )
            
            await self.rag_service.add_fulltext_document(
                keywords=keywords,
                entities=entities,
                **common_fields
            )
            
        except Exception as e:
            self.logger.error(f"Failed to process Jira item: {e}")
    
    def _chunk_document(self, content: str, max_chunk_size: int = 512) -> List[str]:
        """文档分块"""
        try:
            if len(content) <= max_chunk_size:
                return [content]
            
            chunks = []
            sentences = content.split('。')  # 按句子分割
            
            current_chunk = ""
            for sentence in sentences:
                if len(current_chunk + sentence) <= max_chunk_size:
                    current_chunk += sentence + "。"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence + "。"
            
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            return chunks if chunks else [content]
            
        except Exception as e:
            self.logger.error(f"Failed to chunk document: {e}")
            return [content]
    
    def _extract_wiki_keywords(self, content: str, existing_tags: List[str]) -> List[str]:
        """提取Wiki关键词"""
        try:
            keywords = list(existing_tags)  # 从已有标签开始
            content_lower = content.lower()
            
            # 技术关键词
            tech_keywords = [
                'kubernetes', 'docker', 'mysql', 'redis', 'nginx', 'prometheus',
                'grafana', 'elasticsearch', 'kafka', 'rabbitmq', 'mongodb',
                'postgresql', 'jenkins', 'gitlab', 'jira', 'api', 'microservice',
                'cpu', 'memory', 'disk', 'network', 'monitoring', 'alerting'
            ]
            
            for keyword in tech_keywords:
                if keyword in content_lower:
                    keywords.append(keyword)
            
            # 运维关键词
            ops_keywords = [
                '故障', '排查', '监控', '告警', '性能', '优化', '部署', '配置',
                '备份', '恢复', '安全', '日志', '指标', '健康检查'
            ]
            
            for keyword in ops_keywords:
                if keyword in content:
                    keywords.append(keyword)
            
            return list(set(keywords))
            
        except Exception as e:
            self.logger.error(f"Failed to extract wiki keywords: {e}")
            return existing_tags
    
    def _extract_wiki_entities(self, content: str) -> List[str]:
        """提取Wiki实体"""
        try:
            entities = []
            content_lower = content.lower()
            
            # 服务实体
            service_patterns = [
                r'service-[a-z]',
                r'api-gateway',
                r'database',
                r'web-server'
            ]
            
            import re
            for pattern in service_patterns:
                matches = re.findall(pattern, content_lower)
                entities.extend([f'service:{match}' for match in matches])
            
            # 技术实体
            tech_entities = [
                'kubernetes', 'docker', 'mysql', 'redis', 'nginx', 'prometheus'
            ]
            
            for tech in tech_entities:
                if tech in content_lower:
                    entities.append(f'technology:{tech}')
            
            return list(set(entities))
            
        except Exception as e:
            self.logger.error(f"Failed to extract wiki entities: {e}")
            return []
    
    def _extract_gitlab_keywords(self, item: Dict[str, Any]) -> List[str]:
        """提取GitLab关键词"""
        try:
            keywords = []
            
            # 从标签获取
            if 'labels' in item:
                keywords.extend(item['labels'])
            
            # 从文件扩展名推断
            if 'files_changed' in item:
                for file_path in item['files_changed']:
                    ext = Path(file_path).suffix.lower()
                    if ext in ['.py', '.java', '.js', '.go', '.cpp']:
                        keywords.append(f'language:{ext[1:]}')
                    if 'docker' in file_path.lower():
                        keywords.append('docker')
                    if 'config' in file_path.lower():
                        keywords.append('configuration')
            
            # 从标题和描述提取
            text_content = f"{item.get('title', '')} {item.get('description', '')}"
            if 'bug' in text_content.lower():
                keywords.append('bug')
            if 'feature' in text_content.lower():
                keywords.append('feature')
            if 'fix' in text_content.lower():
                keywords.append('fix')
            
            return list(set(keywords))
            
        except Exception as e:
            self.logger.error(f"Failed to extract GitLab keywords: {e}")
            return []
    
    def _extract_gitlab_entities(self, item: Dict[str, Any]) -> List[str]:
        """提取GitLab实体"""
        try:
            entities = []
            
            # 从变更文件提取服务实体
            if 'files_changed' in item:
                for file_path in item['files_changed']:
                    path_parts = file_path.split('/')
                    for part in path_parts:
                        if 'service' in part.lower():
                            entities.append(f'service:{part}')
            
            # 从标签提取
            if 'labels' in item:
                for label in item['labels']:
                    if label.lower() in ['backend', 'frontend', 'database', 'api']:
                        entities.append(f'component:{label}')
            
            return list(set(entities))
            
        except Exception as e:
            self.logger.error(f"Failed to extract GitLab entities: {e}")
            return []
    
    def _extract_jira_keywords(self, item: Dict[str, Any]) -> List[str]:
        """提取Jira关键词"""
        try:
            keywords = []
            
            # 从类型和优先级获取
            if 'type' in item:
                keywords.append(item['type'])
            if 'priority' in item:
                keywords.append(f"priority:{item['priority']}")
            if 'status' in item:
                keywords.append(f"status:{item['status']}")
            
            # 从组件获取
            if 'components' in item:
                keywords.extend(item['components'])
            
            # 从内容提取
            text_content = f"{item.get('title', '')} {item.get('description', '')}"
            content_lower = text_content.lower()
            
            ops_keywords = [
                '故障', '异常', '错误', '超时', '连接', '性能', '监控',
                'cpu', 'memory', 'disk', 'network'
            ]
            
            for keyword in ops_keywords:
                if keyword in content_lower:
                    keywords.append(keyword)
            
            return list(set(keywords))
            
        except Exception as e:
            self.logger.error(f"Failed to extract Jira keywords: {e}")
            return []
    
    def _extract_jira_entities(self, item: Dict[str, Any]) -> List[str]:
        """提取Jira实体"""
        try:
            entities = []
            
            # 从组件提取服务实体
            if 'components' in item:
                for component in item['components']:
                    if 'service' in component.lower() or 'server' in component.lower():
                        entities.append(f'service:{component}')
                    else:
                        entities.append(f'component:{component}')
            
            # 从描述提取技术实体
            text_content = f"{item.get('title', '')} {item.get('description', '')}"
            content_lower = text_content.lower()
            
            tech_entities = [
                'kubernetes', 'docker', 'mysql', 'redis', 'nginx'
            ]
            
            for tech in tech_entities:
                if tech in content_lower:
                    entities.append(f'technology:{tech}')
            
            return list(set(entities))
            
        except Exception as e:
            self.logger.error(f"Failed to extract Jira entities: {e}")
            return []
    
    async def process_all_knowledge_data(self) -> Dict[str, Any]:
        """处理所有知识数据"""
        try:
            start_time = datetime.utcnow()
            
            # 创建schema
            await self.rag_service.create_rag_schema()
            
            # 并行处理各数据源
            wiki_stats, gitlab_stats, jira_stats = await asyncio.gather(
                self.process_wiki_data(),
                self.process_gitlab_data(),
                self.process_jira_data(),
                return_exceptions=True
            )
            
            # 处理异常结果
            if isinstance(wiki_stats, Exception):
                self.logger.error(f"Wiki processing failed: {wiki_stats}")
                wiki_stats = {'processed_count': 0, 'error_count': 1}
            
            if isinstance(gitlab_stats, Exception):
                self.logger.error(f"GitLab processing failed: {gitlab_stats}")
                gitlab_stats = {'processed_count': 0, 'error_count': 1}
            
            if isinstance(jira_stats, Exception):
                self.logger.error(f"Jira processing failed: {jira_stats}")
                jira_stats = {'processed_count': 0, 'error_count': 1}
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            total_stats = {
                'wiki': wiki_stats,
                'gitlab': gitlab_stats,
                'jira': jira_stats,
                'total_processed': (
                    wiki_stats.get('processed_docs', wiki_stats.get('processed_count', 0)) +
                    gitlab_stats.get('processed_count', 0) +
                    jira_stats.get('processed_count', 0)
                ),
                'total_errors': (
                    wiki_stats.get('error_count', 0) +
                    gitlab_stats.get('error_count', 0) +
                    jira_stats.get('error_count', 0)
                ),
                'processing_time': processing_time
            }
            
            self.logger.info(f"Knowledge pipeline completed: {total_stats}")
            return total_stats
            
        except Exception as e:
            self.logger.error(f"Knowledge pipeline failed: {e}")
            raise


# 便利函数
async def run_knowledge_pipeline():
    """运行知识数据处理管道"""
    pipeline = KnowledgePipeline()
    try:
        stats = await pipeline.process_all_knowledge_data()
        print(f"Knowledge pipeline completed: {stats}")
        return stats
    except Exception as e:
        logger.error(f"Knowledge pipeline failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(run_knowledge_pipeline())