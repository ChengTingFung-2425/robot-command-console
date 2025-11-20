"""
Queue Interface
定義佇列的抽象介面，供不同後端實作
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4


class MessagePriority(Enum):
    """訊息優先權"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class Message:
    """佇列訊息"""
    id: str = field(default_factory=lambda: str(uuid4()))
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "id": self.id,
            "payload": self.payload,
            "priority": self.priority.value,
            "timestamp": self.timestamp.isoformat(),
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """從字典建立"""
        return cls(
            id=data.get("id", str(uuid4())),
            payload=data.get("payload", {}),
            priority=MessagePriority(data.get("priority", MessagePriority.NORMAL.value)),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(timezone.utc),
            trace_id=data.get("trace_id"),
            correlation_id=data.get("correlation_id"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            timeout_seconds=data.get("timeout_seconds"),
        )


class QueueInterface(ABC):
    """
    佇列抽象介面
    
    定義佇列操作的標準介面，可由不同後端實作：
    - MemoryQueue: 記憶體內實作（開發、測試）
    - RedisQueue: Redis 實作（生產環境、分散式）
    - KafkaQueue: Kafka 實作（高吞吐量、事件串流）
    """
    
    @abstractmethod
    async def enqueue(self, message: Message) -> bool:
        """
        將訊息加入佇列
        
        Args:
            message: 要加入的訊息
            
        Returns:
            是否成功加入
        """
        pass
    
    @abstractmethod
    async def dequeue(self, timeout: Optional[float] = None) -> Optional[Message]:
        """
        從佇列取出訊息（依優先權）
        
        Args:
            timeout: 等待逾時（秒），None 表示不等待
            
        Returns:
            訊息，若佇列為空且逾時則返回 None
        """
        pass
    
    @abstractmethod
    async def peek(self) -> Optional[Message]:
        """
        查看佇列頭部訊息但不取出
        
        Returns:
            訊息，若佇列為空則返回 None
        """
        pass
    
    @abstractmethod
    async def ack(self, message_id: str) -> bool:
        """
        確認訊息已處理
        
        Args:
            message_id: 訊息 ID
            
        Returns:
            是否成功確認
        """
        pass
    
    @abstractmethod
    async def nack(self, message_id: str, requeue: bool = True) -> bool:
        """
        拒絕訊息（處理失敗）
        
        Args:
            message_id: 訊息 ID
            requeue: 是否重新加入佇列
            
        Returns:
            是否成功處理
        """
        pass
    
    @abstractmethod
    async def size(self) -> int:
        """
        取得佇列大小
        
        Returns:
            佇列中的訊息數量
        """
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """清空佇列"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        健康檢查
        
        Returns:
            健康狀態資訊
        """
        pass
