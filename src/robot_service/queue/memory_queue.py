"""
Memory Queue
記憶體內佇列實作，適用於單機部署與測試
"""

import asyncio
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .interface import Message, MessagePriority, QueueInterface


logger = logging.getLogger(__name__)


class MemoryQueue(QueueInterface):
    """
    記憶體內佇列實作

    使用 Python deque 實作優先權佇列，支援：
    - 按優先權排序
    - 非同步操作
    - 基本的等待與通知機制

    注意：此實作不支援分散式部署，僅適用於單機場景
    """

    def __init__(self, max_size: Optional[int] = None):
        """
        初始化記憶體佇列

        Args:
            max_size: 最大佇列大小，None 表示無限制
        """
        self.max_size = max_size
        self._queues = {
            MessagePriority.URGENT: deque(),
            MessagePriority.HIGH: deque(),
            MessagePriority.NORMAL: deque(),
            MessagePriority.LOW: deque(),
        }
        self._in_flight: Dict[str, Message] = {}  # 處理中的訊息
        self._event = asyncio.Event()  # 用於等待新訊息
        self._lock = asyncio.Lock()  # 用於同步存取
        self._total_enqueued = 0
        self._total_dequeued = 0
        self._total_acked = 0
        self._total_nacked = 0

        logger.info("MemoryQueue initialized", extra={
            "max_size": max_size,
            "service": "robot_service.queue"
        })

    async def enqueue(self, message: Message) -> bool:
        """將訊息加入佇列"""
        async with self._lock:
            current_size = sum(len(q) for q in self._queues.values())

            if self.max_size and current_size >= self.max_size:
                logger.warning("Queue full, rejecting message", extra={
                    "message_id": message.id,
                    "current_size": current_size,
                    "max_size": self.max_size,
                    "service": "robot_service.queue"
                })
                return False

            self._queues[message.priority].append(message)
            self._total_enqueued += 1

            logger.info("Message enqueued", extra={
                "message_id": message.id,
                "priority": message.priority.name,
                "trace_id": message.trace_id,
                "correlation_id": message.correlation_id,
                "service": "robot_service.queue"
            })

            # 通知等待的 dequeue
            self._event.set()

            return True

    async def dequeue(self, timeout: Optional[float] = None) -> Optional[Message]:
        """從佇列取出訊息（依優先權）"""
        deadline = None
        if timeout is not None:
            deadline = asyncio.get_event_loop().time() + timeout

        while True:
            async with self._lock:
                # 依優先權順序檢查佇列
                for priority in [MessagePriority.URGENT, MessagePriority.HIGH, 
                                MessagePriority.NORMAL, MessagePriority.LOW]:
                    queue = self._queues[priority]
                    if queue:
                        message = queue.popleft()
                        self._in_flight[message.id] = message
                        self._total_dequeued += 1

                        # 清除事件，準備下次等待
                        self._event.clear()

                        logger.info("Message dequeued", extra={
                            "message_id": message.id,
                            "priority": priority.name,
                            "trace_id": message.trace_id,
                            "service": "robot_service.queue"
                        })

                        return message

            # 佇列為空，檢查是否需要等待
            if timeout == 0:
                return None

            if deadline is not None:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    return None
                try:
                    await asyncio.wait_for(self._event.wait(), timeout=remaining)
                except asyncio.TimeoutError:
                    return None
            else:
                # 無逾時，永久等待
                await self._event.wait()

    async def peek(self) -> Optional[Message]:
        """查看佇列頭部訊息但不取出"""
        async with self._lock:
            for priority in [MessagePriority.URGENT, MessagePriority.HIGH,
                            MessagePriority.NORMAL, MessagePriority.LOW]:
                queue = self._queues[priority]
                if queue:
                    return queue[0]
            return None

    async def ack(self, message_id: str) -> bool:
        """確認訊息已處理"""
        async with self._lock:
            if message_id in self._in_flight:
                del self._in_flight[message_id]
                self._total_acked += 1

                logger.info("Message acknowledged", extra={
                    "message_id": message_id,
                    "service": "robot_service.queue"
                })

                return True

            logger.warning("Message not in flight", extra={
                "message_id": message_id,
                "service": "robot_service.queue"
            })
            return False

    async def nack(self, message_id: str, requeue: bool = True) -> bool:
        """拒絕訊息（處理失敗）"""
        async with self._lock:
            if message_id not in self._in_flight:
                logger.warning("Message not in flight", extra={
                    "message_id": message_id,
                    "service": "robot_service.queue"
                })
                return False

            message = self._in_flight[message_id]
            del self._in_flight[message_id]
            self._total_nacked += 1

            if requeue and message.retry_count < message.max_retries:
                message.retry_count += 1
                self._queues[message.priority].append(message)

                logger.info("Message nacked and requeued", extra={
                    "message_id": message_id,
                    "retry_count": message.retry_count,
                    "max_retries": message.max_retries,
                    "service": "robot_service.queue"
                })

                self._event.set()
                self._event.clear()
            else:
                logger.warning("Message nacked and dropped", extra={
                    "message_id": message_id,
                    "retry_count": message.retry_count,
                    "max_retries": message.max_retries,
                    "service": "robot_service.queue"
                })

            return True

    async def size(self) -> int:
        """取得佇列大小"""
        async with self._lock:
            return sum(len(q) for q in self._queues.values())

    async def clear(self) -> None:
        """清空佇列"""
        async with self._lock:
            for queue in self._queues.values():
                queue.clear()
            self._in_flight.clear()

            logger.info("Queue cleared", extra={
                "service": "robot_service.queue"
            })

    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        async with self._lock:
            queue_sizes = {
                priority.name: len(queue)
                for priority, queue in self._queues.items()
            }

            return {
                "status": "healthy",
                "type": "memory",
                "queue_sizes": queue_sizes,
                "in_flight_count": len(self._in_flight),
                "total_size": sum(queue_sizes.values()),
                "max_size": self.max_size,
                "statistics": {
                    "total_enqueued": self._total_enqueued,
                    "total_dequeued": self._total_dequeued,
                    "total_acked": self._total_acked,
                    "total_nacked": self._total_nacked,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
