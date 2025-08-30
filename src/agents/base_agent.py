"""
基础智能体类
定义所有Agent的通用接口和功能
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator
import logging
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """智能体类型"""
    PLANNER = "planner"
    KNOWLEDGE = "knowledge"
    REASONING = "reasoning"
    EXECUTOR = "executor"


class MessageType(Enum):
    """消息类型"""
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    ANSWER = "answer"
    ERROR = "error"


@dataclass
class AgentMessage:
    """智能体消息"""
    type: MessageType
    content: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    agent_id: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class AgentState:
    """智能体状态"""
    messages: List[AgentMessage]
    context: Dict[str, Any]
    current_step: int
    max_steps: int
    is_complete: bool
    error: Optional[str] = None

    def add_message(self, message: AgentMessage):
        """添加消息"""
        self.messages.append(message)
        self.current_step += 1

    def get_latest_message(self, message_type: MessageType = None) -> Optional[AgentMessage]:
        """获取最新消息"""
        if message_type is None:
            return self.messages[-1] if self.messages else None
        
        for message in reversed(self.messages):
            if message.type == message_type:
                return message
        return None

    def get_messages_by_type(self, message_type: MessageType) -> List[AgentMessage]:
        """获取指定类型的所有消息"""
        return [msg for msg in self.messages if msg.type == message_type]


class BaseAgent(ABC):
    """基础智能体抽象类"""
    
    def __init__(
        self,
        agent_id: str,
        agent_type: AgentType,
        name: str,
        description: str,
        max_steps: int = 10
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.name = name
        self.description = description
        self.max_steps = max_steps
        self.logger = logging.getLogger(f"{self.__class__.__name__}[{agent_id}]")
        
        # 工具和服务
        self.tools = []
        self.services = {}
        
    def add_tool(self, tool: Any):
        """添加工具"""
        self.tools.append(tool)
        self.logger.info(f"Added tool: {tool.__class__.__name__}")
    
    def add_service(self, service_name: str, service: Any):
        """添加服务"""
        self.services[service_name] = service
        self.logger.info(f"Added service: {service_name}")
    
    def get_service(self, service_name: str) -> Any:
        """获取服务"""
        return self.services.get(service_name)
    
    @abstractmethod
    async def process(self, state: AgentState) -> AgentState:
        """处理状态并返回更新后的状态"""
        pass
    
    async def should_continue(self, state: AgentState) -> bool:
        """判断是否应该继续处理"""
        if state.is_complete:
            return False
        
        if state.error:
            return False
            
        if state.current_step >= state.max_steps:
            self.logger.warning(f"Agent {self.agent_id} reached max steps ({state.max_steps})")
            return False
        
        return True
    
    async def create_initial_state(
        self,
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentState:
        """创建初始状态"""
        initial_message = AgentMessage(
            type=MessageType.THOUGHT,
            content=f"Processing user request: {user_message}",
            agent_id=self.agent_id
        )
        
        return AgentState(
            messages=[initial_message],
            context=context or {},
            current_step=0,
            max_steps=self.max_steps,
            is_complete=False
        )
    
    async def handle_error(self, state: AgentState, error: Exception) -> AgentState:
        """处理错误"""
        error_message = AgentMessage(
            type=MessageType.ERROR,
            content=f"Error in {self.name}: {str(error)}",
            agent_id=self.agent_id
        )
        
        state.add_message(error_message)
        state.error = str(error)
        state.is_complete = True
        
        self.logger.error(f"Agent {self.agent_id} encountered error: {error}")
        return state
    
    async def finalize(self, state: AgentState) -> AgentState:
        """完成处理"""
        state.is_complete = True
        
        final_message = AgentMessage(
            type=MessageType.THOUGHT,
            content=f"Agent {self.name} completed processing",
            agent_id=self.agent_id
        )
        state.add_message(final_message)
        
        return state
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取智能体能力描述"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type.value,
            "name": self.name,
            "description": self.description,
            "max_steps": self.max_steps,
            "tools": [tool.__class__.__name__ for tool in self.tools],
            "services": list(self.services.keys())
        }
    
    def format_message_for_llm(self, messages: List[AgentMessage]) -> str:
        """格式化消息供LLM使用"""
        formatted_messages = []
        
        for message in messages:
            timestamp_str = message.timestamp.strftime("%Y-%m-%d %H:%M:%S") if message.timestamp else ""
            agent_info = f"[{message.agent_id}]" if message.agent_id else ""
            
            formatted_msg = f"{timestamp_str} {agent_info} {message.type.value.upper()}: {message.content}"
            formatted_messages.append(formatted_msg)
        
        return "\n".join(formatted_messages)
    
    async def stream_response(
        self,
        state: AgentState
    ) -> AsyncGenerator[AgentMessage, None]:
        """流式返回处理过程"""
        try:
            while await self.should_continue(state):
                # 处理一步
                prev_message_count = len(state.messages)
                state = await self.process(state)
                
                # 返回新产生的消息
                for message in state.messages[prev_message_count:]:
                    yield message
                
                # 如果没有新消息且没有完成，可能卡住了
                if len(state.messages) == prev_message_count and not state.is_complete:
                    error_msg = AgentMessage(
                        type=MessageType.ERROR,
                        content=f"Agent {self.name} appears to be stuck",
                        agent_id=self.agent_id
                    )
                    state.add_message(error_msg)
                    state.is_complete = True
                    yield error_msg
                    break
            
            # 如果还没完成，进行最终处理
            if not state.is_complete:
                state = await self.finalize(state)
                # 返回最终消息
                final_message = state.get_latest_message()
                if final_message:
                    yield final_message
                    
        except Exception as e:
            error_state = await self.handle_error(state, e)
            error_msg = error_state.get_latest_message(MessageType.ERROR)
            if error_msg:
                yield error_msg


class ToolAgent(BaseAgent):
    """带工具的智能体基类"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tool_registry = {}
    
    def register_tool(self, name: str, func: callable, description: str):
        """注册工具函数"""
        self._tool_registry[name] = {
            "function": func,
            "description": description
        }
        self.logger.info(f"Registered tool: {name}")
    
    async def use_tool(
        self,
        tool_name: str,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """使用工具"""
        if tool_name not in self._tool_registry:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        try:
            tool_info = self._tool_registry[tool_name]
            result = await tool_info["function"](*args, **kwargs)
            
            return {
                "success": True,
                "result": result,
                "tool_name": tool_name
            }
            
        except Exception as e:
            self.logger.error(f"Tool {tool_name} execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name
            }
    
    def get_available_tools(self) -> Dict[str, str]:
        """获取可用工具列表"""
        return {
            name: info["description"] 
            for name, info in self._tool_registry.items()
        }