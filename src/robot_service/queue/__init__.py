"""
Queue 模組
提供訊息佇列抽象與實作（記憶體內、RabbitMQ、未來可擴充至 Kafka）
支援離線模式：離線時緩衝指令，在線後自動發送
"""

from .interface import QueueInterface, Message, MessagePriority
from .memory_queue import MemoryQueue
from .rabbitmq_queue import RabbitMQQueue
from .handler import QueueHandler
from .offline_buffer import OfflineBuffer, BufferEntry, BufferEntryStatus
from .offline_queue_service import OfflineQueueService

# Alias for backward compatibility
PriorityQueue = MemoryQueue

__all__ = [
    "QueueInterface",
    "Message",
    "MessagePriority",
    "MemoryQueue",
    "RabbitMQQueue",
    "PriorityQueue",  # Alias for MemoryQueue
    "QueueHandler",
    # 離線模式
    "OfflineBuffer",
    "BufferEntry",
    "BufferEntryStatus",
    "OfflineQueueService",
]
