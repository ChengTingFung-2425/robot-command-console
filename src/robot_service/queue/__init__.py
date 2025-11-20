"""
Queue 模組
提供訊息佇列抽象與實作（記憶體內、未來可擴充至 Redis/Kafka）
"""

from .interface import QueueInterface, Message, MessagePriority
from .memory_queue import MemoryQueue
from .handler import QueueHandler

__all__ = [
    "QueueInterface",
    "Message",
    "MessagePriority",
    "MemoryQueue",
    "QueueHandler",
]
