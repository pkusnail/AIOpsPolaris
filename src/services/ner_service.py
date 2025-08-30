"""
命名实体识别服务
基于spaCy和transformers实现实体抽取和关系识别
"""

import spacy
from spacy import displacy
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import re
from typing import List, Dict, Any, Optional, Tuple, Set
import logging
from datetime import datetime
import json
from collections import defaultdict
import asyncio
from concurrent.futures import ThreadPoolExecutor

from config.settings import settings

logger = logging.getLogger(__name__)


class NERService:
    """命名实体识别服务类"""
    
    def __init__(self):
        self.nlp = None
        self.ner_pipeline = None
        self.relation_patterns = {}
        self.entity_types = {
            # 技术组件
            'SERVICE': ['service', 'micro-service', 'microservice', 'api', 'application'],
            'DATABASE': ['database', 'db', 'mysql', 'redis', 'mongodb', 'postgresql'],
            'SERVER': ['server', 'host', 'machine', 'node', 'instance'],
            'CONTAINER': ['container', 'pod', 'docker'],
            'NETWORK': ['network', 'vpc', 'subnet', 'load-balancer'],
            
            # 错误和问题
            'ERROR': ['error', 'exception', 'failure', 'bug', 'issue'],
            'ALERT': ['alert', 'alarm', 'warning', 'notification'],
            
            # 指标和数值
            'METRIC': ['cpu', 'memory', 'disk', 'network', 'latency', 'throughput'],
            'LOG_LEVEL': ['debug', 'info', 'warn', 'error', 'fatal'],
            
            # 运维操作
            'ACTION': ['restart', 'deploy', 'rollback', 'scale', 'update'],
            'STATUS': ['running', 'stopped', 'failed', 'healthy', 'unhealthy']
        }
        
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize_models()
    
    def _initialize_models(self):
        """初始化NER模型"""
        try:
            # 加载spaCy模型
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                self.logger.warning("English model not found, using blank model")
                self.nlp = spacy.blank("en")
                # 添加基本组件
                if "tagger" not in self.nlp.pipe_names:
                    self.nlp.add_pipe("tagger")
                if "parser" not in self.nlp.pipe_names:
                    self.nlp.add_pipe("parser")
                if "ner" not in self.nlp.pipe_names:
                    self.nlp.add_pipe("ner")
            
            # 添加自定义实体类型到spaCy
            ner = self.nlp.get_pipe("ner")
            for entity_type in self.entity_types.keys():
                ner.add_label(entity_type)
            
            # 初始化关系模式
            self._initialize_relation_patterns()
            
            self.logger.info("NER models initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize NER models: {e}")
            raise
    
    def _initialize_relation_patterns(self):
        """初始化关系识别模式"""
        self.relation_patterns = {
            'DEPENDS_ON': [
                r'(\w+)\s+depends\s+on\s+(\w+)',
                r'(\w+)\s+requires\s+(\w+)',
                r'(\w+)\s+needs\s+(\w+)'
            ],
            'CONNECTS_TO': [
                r'(\w+)\s+connects?\s+to\s+(\w+)',
                r'(\w+)\s+links?\s+to\s+(\w+)',
                r'(\w+)\s+communicates?\s+with\s+(\w+)'
            ],
            'HOSTS': [
                r'(\w+)\s+hosts?\s+(\w+)',
                r'(\w+)\s+runs?\s+on\s+(\w+)',
                r'(\w+)\s+deployed\s+on\s+(\w+)'
            ],
            'CAUSES': [
                r'(\w+)\s+causes?\s+(\w+)',
                r'(\w+)\s+triggers?\s+(\w+)',
                r'(\w+)\s+leads?\s+to\s+(\w+)'
            ],
            'MONITORS': [
                r'(\w+)\s+monitors?\s+(\w+)',
                r'(\w+)\s+watches?\s+(\w+)',
                r'(\w+)\s+observes?\s+(\w+)'
            ],
            'AFFECTS': [
                r'(\w+)\s+affects?\s+(\w+)',
                r'(\w+)\s+impacts?\s+(\w+)',
                r'(\w+)\s+influences?\s+(\w+)'
            ]
        }
    
    def _extract_spacy_entities(self, text: str) -> List[Dict[str, Any]]:
        """使用spaCy提取实体"""
        try:
            doc = self.nlp(text)
            entities = []
            
            for ent in doc.ents:
                entities.append({
                    'text': ent.text,
                    'label': ent.label_,
                    'start': ent.start_char,
                    'end': ent.end_char,
                    'confidence': 1.0  # spaCy不直接提供置信度
                })
            
            return entities
            
        except Exception as e:
            self.logger.error(f"Failed to extract spaCy entities: {e}")
            return []
    
    def _extract_pattern_entities(self, text: str) -> List[Dict[str, Any]]:
        """使用正则模式提取领域特定实体"""
        entities = []
        
        try:
            # 技术术语模式
            patterns = {
                'SERVICE': [
                    r'\b\w+[-_]?service\b',
                    r'\b\w+[-_]?api\b',
                    r'\bmicroservice[-_]?\w*\b'
                ],
                'DATABASE': [
                    r'\bmysql\b',
                    r'\bredis\b', 
                    r'\bmongodb\b',
                    r'\bpostgresql\b',
                    r'\belasticsearch\b'
                ],
                'SERVER': [
                    r'\b\w+[-_]server[-_]?\d*\b',
                    r'\bhost[-_]?\w*\b',
                    r'\bnode[-_]?\d+\b'
                ],
                'CONTAINER': [
                    r'\bpod[-_]?\w*\b',
                    r'\bcontainer[-_]?\w*\b',
                    r'\bdocker[-_]?\w*\b'
                ],
                'ERROR': [
                    r'\b\w*error\w*\b',
                    r'\b\w*exception\w*\b',
                    r'\b\w*failure\w*\b'
                ],
                'METRIC': [
                    r'\bcpu\s+usage\b',
                    r'\bmemory\s+usage\b',
                    r'\bdisk\s+space\b',
                    r'\blatency\b',
                    r'\bthroughput\b'
                ],
                'LOG_LEVEL': [
                    r'\b(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b'
                ]
            }
            
            for entity_type, type_patterns in patterns.items():
                for pattern in type_patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        entities.append({
                            'text': match.group(),
                            'label': entity_type,
                            'start': match.start(),
                            'end': match.end(),
                            'confidence': 0.8
                        })
            
            return entities
            
        except Exception as e:
            self.logger.error(f"Failed to extract pattern entities: {e}")
            return []
    
    def _extract_ip_addresses(self, text: str) -> List[Dict[str, Any]]:
        """提取IP地址"""
        entities = []
        
        try:
            # IPv4地址模式
            ipv4_pattern = r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
            
            matches = re.finditer(ipv4_pattern, text)
            for match in matches:
                entities.append({
                    'text': match.group(),
                    'label': 'IP_ADDRESS',
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.9
                })
            
            return entities
            
        except Exception as e:
            self.logger.error(f"Failed to extract IP addresses: {e}")
            return []
    
    def _extract_timestamps(self, text: str) -> List[Dict[str, Any]]:
        """提取时间戳"""
        entities = []
        
        try:
            # 时间戳模式
            patterns = [
                r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z?',  # ISO格式
                r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',  # 标准格式
                r'\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}',  # 美式格式
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, text)
                for match in matches:
                    entities.append({
                        'text': match.group(),
                        'label': 'TIMESTAMP',
                        'start': match.start(),
                        'end': match.end(),
                        'confidence': 0.95
                    })
            
            return entities
            
        except Exception as e:
            self.logger.error(f"Failed to extract timestamps: {e}")
            return []
    
    def _merge_entities(self, entity_lists: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """合并多个实体列表，去重"""
        all_entities = []
        for entities in entity_lists:
            all_entities.extend(entities)
        
        # 按位置排序
        all_entities.sort(key=lambda x: x['start'])
        
        # 去重和合并重叠实体
        merged_entities = []
        for entity in all_entities:
            # 检查是否与现有实体重叠
            overlap_found = False
            for i, existing in enumerate(merged_entities):
                if (entity['start'] < existing['end'] and 
                    entity['end'] > existing['start']):
                    # 有重叠，选择置信度更高的
                    if entity['confidence'] > existing['confidence']:
                        merged_entities[i] = entity
                    overlap_found = True
                    break
            
            if not overlap_found:
                merged_entities.append(entity)
        
        return merged_entities
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """提取所有类型的实体"""
        try:
            entity_lists = [
                self._extract_spacy_entities(text),
                self._extract_pattern_entities(text),
                self._extract_ip_addresses(text),
                self._extract_timestamps(text)
            ]
            
            merged_entities = self._merge_entities(entity_lists)
            
            # 添加实体ID和额外信息
            for i, entity in enumerate(merged_entities):
                entity['id'] = f"entity_{i}"
                entity['source'] = 'ner_service'
                entity['extracted_at'] = datetime.utcnow().isoformat()
            
            return merged_entities
            
        except Exception as e:
            self.logger.error(f"Failed to extract entities: {e}")
            return []
    
    def extract_relationships(self, text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取实体间关系"""
        relationships = []
        
        try:
            # 基于模式的关系提取
            for relation_type, patterns in self.relation_patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        source_text = match.group(1)
                        target_text = match.group(2)
                        
                        # 查找对应的实体
                        source_entity = self._find_entity_by_text(source_text, entities)
                        target_entity = self._find_entity_by_text(target_text, entities)
                        
                        if source_entity and target_entity:
                            relationships.append({
                                'id': f"rel_{len(relationships)}",
                                'source_entity_id': source_entity['id'],
                                'target_entity_id': target_entity['id'],
                                'relationship_type': relation_type,
                                'confidence': 0.8,
                                'source_text': source_text,
                                'target_text': target_text,
                                'extracted_at': datetime.utcnow().isoformat()
                            })
            
            # 基于距离的关系推断
            distance_relations = self._infer_distance_relationships(text, entities)
            relationships.extend(distance_relations)
            
            return relationships
            
        except Exception as e:
            self.logger.error(f"Failed to extract relationships: {e}")
            return []
    
    def _find_entity_by_text(self, text: str, entities: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """根据文本查找实体"""
        text_lower = text.lower()
        for entity in entities:
            if entity['text'].lower() == text_lower:
                return entity
        return None
    
    def _infer_distance_relationships(self, text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """基于实体间距离推断关系"""
        relationships = []
        
        try:
            # 对于邻近的实体，推断可能的关系
            for i, entity1 in enumerate(entities):
                for j, entity2 in enumerate(entities[i+1:], i+1):
                    distance = entity2['start'] - entity1['end']
                    
                    # 如果实体间距离较近（小于50个字符）
                    if 0 < distance < 50:
                        # 根据实体类型推断关系
                        relation_type = self._infer_relation_type(
                            entity1['label'], 
                            entity2['label']
                        )
                        
                        if relation_type:
                            relationships.append({
                                'id': f"inferred_rel_{len(relationships)}",
                                'source_entity_id': entity1['id'],
                                'target_entity_id': entity2['id'],
                                'relationship_type': relation_type,
                                'confidence': 0.6,  # 推断关系置信度较低
                                'source_text': entity1['text'],
                                'target_text': entity2['text'],
                                'extracted_at': datetime.utcnow().isoformat(),
                                'inferred': True
                            })
            
            return relationships
            
        except Exception as e:
            self.logger.error(f"Failed to infer distance relationships: {e}")
            return []
    
    def _infer_relation_type(self, label1: str, label2: str) -> Optional[str]:
        """根据实体类型推断关系类型"""
        relation_rules = {
            ('SERVICE', 'DATABASE'): 'USES',
            ('SERVICE', 'SERVER'): 'RUNS_ON',
            ('CONTAINER', 'SERVER'): 'DEPLOYED_ON',
            ('ERROR', 'SERVICE'): 'AFFECTS',
            ('METRIC', 'SERVICE'): 'MEASURES',
            ('ALERT', 'ERROR'): 'TRIGGERED_BY'
        }
        
        # 双向查找
        key1 = (label1, label2)
        key2 = (label2, label1)
        
        if key1 in relation_rules:
            return relation_rules[key1]
        elif key2 in relation_rules:
            return relation_rules[key2]
        
        return None
    
    async def extract_from_document(
        self,
        title: str,
        content: str,
        source: str = "unknown"
    ) -> Dict[str, Any]:
        """从文档中提取实体和关系"""
        try:
            # 合并标题和内容
            full_text = f"{title}\n{content}"
            
            # 异步执行提取
            loop = asyncio.get_event_loop()
            entities = await loop.run_in_executor(
                self.executor,
                self.extract_entities,
                full_text
            )
            
            relationships = await loop.run_in_executor(
                self.executor,
                self.extract_relationships,
                full_text,
                entities
            )
            
            return {
                'entities': entities,
                'relationships': relationships,
                'source': source,
                'extracted_at': datetime.utcnow().isoformat(),
                'stats': {
                    'entity_count': len(entities),
                    'relationship_count': len(relationships),
                    'entity_types': self._count_entity_types(entities)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to extract from document: {e}")
            return {
                'entities': [],
                'relationships': [],
                'source': source,
                'extracted_at': datetime.utcnow().isoformat(),
                'error': str(e)
            }
    
    def _count_entity_types(self, entities: List[Dict[str, Any]]) -> Dict[str, int]:
        """统计实体类型分布"""
        type_counts = defaultdict(int)
        for entity in entities:
            type_counts[entity['label']] += 1
        return dict(type_counts)
    
    async def batch_extract(
        self,
        documents: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """批量提取实体和关系"""
        results = []
        
        try:
            for doc in documents:
                result = await self.extract_from_document(
                    doc.get('title', ''),
                    doc.get('content', ''),
                    doc.get('source', 'unknown')
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to batch extract: {e}")
            return []
    
    def visualize_entities(self, text: str, entities: List[Dict[str, Any]]) -> str:
        """可视化实体识别结果"""
        try:
            # 创建spaCy Doc对象用于可视化
            doc = self.nlp(text)
            
            # 转换实体格式
            spacy_entities = []
            for entity in entities:
                spacy_entities.append((
                    entity['start'],
                    entity['end'],
                    entity['label']
                ))
            
            # 设置实体
            doc.ents = [doc.char_span(start, end, label=label) 
                       for start, end, label in spacy_entities
                       if doc.char_span(start, end) is not None]
            
            # 生成HTML可视化
            html = displacy.render(doc, style="ent", jupyter=False)
            return html
            
        except Exception as e:
            self.logger.error(f"Failed to visualize entities: {e}")
            return ""
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取NER服务统计信息"""
        return {
            'supported_entity_types': list(self.entity_types.keys()),
            'supported_relation_types': list(self.relation_patterns.keys()),
            'model_info': {
                'spacy_model': self.nlp.meta if hasattr(self.nlp, 'meta') else {},
                'pipeline_components': self.nlp.pipe_names
            }
        }
    
    def close(self):
        """关闭服务"""
        if self.executor:
            self.executor.shutdown(wait=True)
            self.logger.info("NER service closed")