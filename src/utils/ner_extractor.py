"""
NER实体识别器
从用户查询中提取服务名、系统组件等关键实体
"""

import re
from typing import List, Dict, Any, Set
from dataclasses import dataclass


@dataclass
class Entity:
    """识别的实体"""
    text: str
    label: str
    confidence: float
    start: int
    end: int


class NERExtractor:
    """简化的NER实体提取器，专门用于运维场景"""
    
    def __init__(self):
        # 预定义的服务名模式 - 移除\b以支持中文
        self.service_patterns = [
            # 标准服务名格式
            r'service-[a-zA-Z]\d*',  # service-a, service-b1, service-d1
            r'service\s+[A-Za-z]\d*',  # service A, service D1, service d1  
            r'[Ss]ervice[_\-\s]*[A-Za-z]\d*',  # Service-A, service_B
        ]
        
        # 系统组件模式
        self.component_patterns = {
            'database': [r'\b(数据库|database|db|mysql|postgresql|redis|mongo)\b'],
            'network': [r'\b(网络|network|网卡|交换机|路由器|防火墙)\b'],  
            'storage': [r'\b(存储|storage|磁盘|disk|硬盘|SSD|HDD)\b'],
            'cpu': [r'\b(CPU|cpu|处理器|processor)\b'],
            'memory': [r'\b(内存|memory|RAM|ram)\b'],
            'load_balancer': [r'\b(负载均衡|load\s*balancer|LB|lb)\b'],
        }
        
        # 故障类型模式
        self.incident_patterns = {
            'performance': [r'\b(性能|performance|slow|慢|卡顿|延迟|latency)\b'],
            'error': [r'\b(错误|error|异常|exception|故障|failure|问题|problem)\b'],
            'timeout': [r'\b(超时|timeout|time\s*out)\b'],
            'connection': [r'\b(连接|connection|connect|网络中断|断开)\b'],
            'crash': [r'\b(崩溃|crash|宕机|down|offline)\b'],
        }
        
        # 运维操作模式
        self.operation_patterns = {
            'restart': [r'\b(重启|restart|reboot)\b'],
            'monitor': [r'\b(监控|monitor|monitoring|观察)\b'],
            'analyze': [r'\b(分析|analyze|analysis|诊断|diagnosis)\b'],
            'fix': [r'\b(修复|fix|repair|解决|solve)\b'],
        }
        
    def extract_entities(self, text: str) -> List[Entity]:
        """从文本中提取所有实体"""
        entities = []
        text_lower = text.lower()
        
        # 提取服务名
        services = self._extract_services(text)
        entities.extend(services)
        
        # 提取系统组件
        components = self._extract_components(text_lower)
        entities.extend(components)
        
        # 提取故障类型
        incidents = self._extract_incidents(text_lower)  
        entities.extend(incidents)
        
        # 提取运维操作
        operations = self._extract_operations(text_lower)
        entities.extend(operations)
        
        # 去重并排序
        entities = self._deduplicate_entities(entities)
        
        return entities
        
    def _extract_services(self, text: str) -> List[Entity]:
        """提取服务名"""
        entities = []
        
        for pattern in self.service_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                service_name = match.group().strip()
                # 标准化服务名
                normalized = self._normalize_service_name(service_name)
                
                entities.append(Entity(
                    text=normalized,
                    label="SERVICE",
                    confidence=0.9,
                    start=match.start(),
                    end=match.end()
                ))
                
        return entities
        
    def _normalize_service_name(self, service_name: str) -> str:
        """标准化服务名格式"""
        # 转换为标准格式: service-x
        service_name = service_name.lower()
        # 匹配更多格式: service d1, service D1, service-d1等
        service_name = re.sub(r'service[\s_-]*([a-z]\d*)', r'service-\1', service_name)
        return service_name
        
    def _extract_components(self, text: str) -> List[Entity]:
        """提取系统组件"""
        entities = []
        
        for component_type, patterns in self.component_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entities.append(Entity(
                        text=match.group(),
                        label=f"COMPONENT_{component_type.upper()}",
                        confidence=0.8,
                        start=match.start(),
                        end=match.end()
                    ))
                    
        return entities
        
    def _extract_incidents(self, text: str) -> List[Entity]:
        """提取故障类型"""
        entities = []
        
        for incident_type, patterns in self.incident_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entities.append(Entity(
                        text=match.group(),
                        label=f"INCIDENT_{incident_type.upper()}",
                        confidence=0.7,
                        start=match.start(),
                        end=match.end()
                    ))
                    
        return entities
        
    def _extract_operations(self, text: str) -> List[Entity]:
        """提取运维操作"""
        entities = []
        
        for op_type, patterns in self.operation_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)  
                for match in matches:
                    entities.append(Entity(
                        text=match.group(),
                        label=f"OPERATION_{op_type.upper()}",
                        confidence=0.6,
                        start=match.start(),
                        end=match.end()
                    ))
                    
        return entities
        
    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """去重重叠的实体"""
        # 按位置排序
        entities.sort(key=lambda x: (x.start, x.end))
        
        deduplicated = []
        for entity in entities:
            # 检查是否与已有实体重叠
            overlapped = False
            for existing in deduplicated:
                if self._is_overlapping(entity, existing):
                    # 保留置信度更高的实体
                    if entity.confidence > existing.confidence:
                        deduplicated.remove(existing)
                        deduplicated.append(entity)
                    overlapped = True
                    break
                    
            if not overlapped:
                deduplicated.append(entity)
                
        return deduplicated
        
    def _is_overlapping(self, entity1: Entity, entity2: Entity) -> bool:
        """检查两个实体是否重叠"""
        return not (entity1.end <= entity2.start or entity2.end <= entity1.start)
        
    def get_services(self, entities: List[Entity]) -> List[str]:
        """从实体列表中提取服务名"""
        services = []
        for entity in entities:
            if entity.label == "SERVICE":
                services.append(entity.text)
        return services
        
    def get_components(self, entities: List[Entity]) -> List[str]:
        """从实体列表中提取组件名"""
        components = []
        for entity in entities:
            if entity.label.startswith("COMPONENT_"):
                components.append(entity.text)
        return components
        
    def get_incidents(self, entities: List[Entity]) -> List[str]:
        """从实体列表中提取故障类型"""
        incidents = []
        for entity in entities:
            if entity.label.startswith("INCIDENT_"):
                incidents.append(entity.text)
        return incidents


# 全局NER提取器实例  
ner_extractor = NERExtractor()