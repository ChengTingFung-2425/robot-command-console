"""
RabbitMQ Queue Implementation
基於 aio-pika 的 RabbitMQ 佇列實作，遵循 best practices
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message as AMQPMessage
from aio_pika.abc import (
    AbstractChannel,
    AbstractConnection,
    AbstractExchange,
    AbstractQueue,
)
from aio_pika.pool import Pool

from .interface import Message, MessagePriority, QueueInterface


logger = logging.getLogger(__name__)


class RabbitMQQueue(QueueInterface):
    """
    RabbitMQ 佇列實作

    特性：
    - 持久化訊息（survive broker restart）
    - 優先權佇列（0-10，映射自 MessagePriority）
    - Dead Letter Exchange（DLX）處理失敗訊息
    - 連線池（提升效能與可靠性）
    - 自動重連機制
    - Publisher confirms（確保訊息送達）
    - Prefetch count（控制並發處理）

    架構：
    - Exchange: robot.commands (topic exchange)
    - Queue: robot.commands.queue (with DLX)
    - DLQ: robot.commands.dlq (dead letter queue)
    - Routing key: command.{priority}
    """

    # 優先權映射：MessagePriority -> RabbitMQ priority (0-10)
    PRIORITY_MAP = {
        MessagePriority.LOW: 2,
        MessagePriority.NORMAL: 5,
        MessagePriority.HIGH: 8,
        MessagePriority.URGENT: 10,
    }

    def __init__(
        self,
        url: str = "amqp://guest:guest@localhost:5672/",
        exchange_name: str = "robot.commands",
        queue_name: str = "robot.commands.queue",
        dlx_name: str = "robot.commands.dlx",
        dlq_name: str = "robot.commands.dlq",
        prefetch_count: int = 10,
        connection_pool_size: int = 2,
        channel_pool_size: int = 10,
    ):
        """
        初始化 RabbitMQ 佇列

        Args:
            url: RabbitMQ 連線 URL
            exchange_name: Exchange 名稱
            queue_name: 佇列名稱
            dlx_name: Dead Letter Exchange 名稱
            dlq_name: Dead Letter Queue 名稱
            prefetch_count: 預取數量（QoS）
            connection_pool_size: 連線池大小
            channel_pool_size: Channel 池大小
        """
        self.url = url
        self.exchange_name = exchange_name
        self.queue_name = queue_name
        self.dlx_name = dlx_name
        self.dlq_name = dlq_name
        self.prefetch_count = prefetch_count
        self.connection_pool_size = connection_pool_size
        self.channel_pool_size = channel_pool_size

        # 連線池
        self._connection: Optional[AbstractConnection] = None
        self._connection_pool: Optional[Pool] = None
        self._channel_pool: Optional[Pool] = None

        # Exchange 與 Queue 參考
        self._exchange: Optional[AbstractExchange] = None
        self._queue: Optional[AbstractQueue] = None
        self._dlx: Optional[AbstractExchange] = None
        self._dlq: Optional[AbstractQueue] = None

        # 統計資訊
        self._total_enqueued = 0
        self._total_dequeued = 0
        self._total_acked = 0
        self._total_nacked = 0

        # 初始化狀態
        self._initialized = False

        logger.info("RabbitMQQueue created", extra={
            "url": url,
            "exchange": exchange_name,
            "queue": queue_name,
            "service": "robot_service.queue.rabbitmq"
        })

    async def initialize(self) -> None:
        """初始化 RabbitMQ 連線與拓撲"""
        if self._initialized:
            return

        try:
            # 建立連線池
            async def get_connection() -> AbstractConnection:
                return await aio_pika.connect_robust(self.url)

            self._connection_pool = Pool(
                get_connection,
                max_size=self.connection_pool_size
            )

            # 建立 channel 池
            async def get_channel() -> AbstractChannel:
                async with self._connection_pool.acquire() as connection:
                    channel = await connection.channel()
                    await channel.set_qos(prefetch_count=self.prefetch_count)
                    return channel

            self._channel_pool = Pool(
                get_channel,
                max_size=self.channel_pool_size
            )

            # 宣告拓撲結構
            async with self._channel_pool.acquire() as channel:
                # 1. 宣告 DLX（處理失敗訊息）
                self._dlx = await channel.declare_exchange(
                    self.dlx_name,
                    ExchangeType.TOPIC,
                    durable=True
                )

                # 2. 宣告 DLQ
                self._dlq = await channel.declare_queue(
                    self.dlq_name,
                    durable=True
                )
                await self._dlq.bind(self._dlx, routing_key="#")

                # 3. 宣告主 Exchange
                self._exchange = await channel.declare_exchange(
                    self.exchange_name,
                    ExchangeType.TOPIC,
                    durable=True
                )

                # 4. 宣告主 Queue（帶 DLX、優先權、TTL）
                self._queue = await channel.declare_queue(
                    self.queue_name,
                    durable=True,
                    arguments={
                        "x-dead-letter-exchange": self.dlx_name,
                        "x-max-priority": 10,  # 支援優先權 0-10
                        # "x-message-ttl": 86400000,  # 可選：訊息 TTL (24h)
                    }
                )

                # 5. 綁定 Queue 到 Exchange（接收所有優先權）
                for priority in MessagePriority:
                    routing_key = f"command.{priority.name.lower()}"
                    await self._queue.bind(self._exchange, routing_key=routing_key)

            self._initialized = True

            logger.info("RabbitMQ topology initialized", extra={
                "exchange": self.exchange_name,
                "queue": self.queue_name,
                "dlx": self.dlx_name,
                "dlq": self.dlq_name,
                "service": "robot_service.queue.rabbitmq"
            })

        except Exception as e:
            logger.error("Failed to initialize RabbitMQ", extra={
                "error": str(e),
                "service": "robot_service.queue.rabbitmq"
            })
            raise

    async def close(self) -> None:
        """關閉連線池"""
        if self._channel_pool:
            await self._channel_pool.close()
        if self._connection_pool:
            await self._connection_pool.close()

        self._initialized = False

        logger.info("RabbitMQ connection closed", extra={
            "service": "robot_service.queue.rabbitmq"
        })

    async def enqueue(self, message: Message) -> bool:
        """將訊息發布到 RabbitMQ"""
        if not self._initialized:
            await self.initialize()

        try:
            async with self._channel_pool.acquire() as channel:
                exchange = await channel.get_exchange(self.exchange_name)

                # 序列化訊息
                body = json.dumps(message.to_dict()).encode()

                # 建立 AMQP 訊息（持久化、優先權）
                amqp_message = AMQPMessage(
                    body=body,
                    delivery_mode=DeliveryMode.PERSISTENT,  # 持久化
                    priority=self.PRIORITY_MAP[message.priority],
                    message_id=message.id,
                    timestamp=datetime.now(timezone.utc),
                    headers={
                        "trace_id": message.trace_id,
                        "correlation_id": message.correlation_id,
                        "retry_count": message.retry_count,
                        "max_retries": message.max_retries,
                    },
                )

                # 發布訊息（帶 routing key）
                routing_key = f"command.{message.priority.name.lower()}"
                await exchange.publish(
                    amqp_message,
                    routing_key=routing_key,
                    mandatory=True  # 確保訊息路由成功
                )

                self._total_enqueued += 1

                logger.info("Message published to RabbitMQ", extra={
                    "message_id": message.id,
                    "priority": message.priority.name,
                    "routing_key": routing_key,
                    "trace_id": message.trace_id,
                    "service": "robot_service.queue.rabbitmq"
                })

                return True

        except Exception as e:
            logger.error("Failed to enqueue message", extra={
                "message_id": message.id,
                "error": str(e),
                "service": "robot_service.queue.rabbitmq"
            })
            return False

    async def dequeue(self, timeout: Optional[float] = None) -> Optional[Message]:
        """從 RabbitMQ 取出訊息"""
        if not self._initialized:
            await self.initialize()

        try:
            async with self._channel_pool.acquire() as channel:
                queue = await channel.get_queue(self.queue_name)

                # 使用 get（非阻塞）或 iterator（阻塞）
                if timeout == 0:
                    # 非阻塞模式
                    incoming_message = await queue.get(timeout=0.1, fail=False)
                    if not incoming_message:
                        return None
                else:
                    # 阻塞模式（帶超時）
                    incoming_message = await queue.get(timeout=timeout, fail=False)
                    if not incoming_message:
                        return None

                # 解析訊息
                body = incoming_message.body.decode()
                data = json.loads(body)
                message = Message.from_dict(data)

                # 將 AMQP message 存儲以便後續 ack/nack
                message._amqp_message = incoming_message

                self._total_dequeued += 1

                logger.info("Message consumed from RabbitMQ", extra={
                    "message_id": message.id,
                    "priority": message.priority.name,
                    "trace_id": message.trace_id,
                    "service": "robot_service.queue.rabbitmq"
                })

                return message

        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error("Failed to dequeue message", extra={
                "error": str(e),
                "service": "robot_service.queue.rabbitmq"
            })
            return None

    async def peek(self) -> Optional[Message]:
        """查看佇列頭部訊息但不取出（RabbitMQ 不直接支援，使用基本 get）"""
        # 注意：RabbitMQ 沒有真正的 peek，這裡用 get + nack 模擬
        logger.warning("peek() not natively supported in RabbitMQ, using get+nack", extra={
            "service": "robot_service.queue.rabbitmq"
        })

        message = await self.dequeue(timeout=0)
        if message and hasattr(message, '_amqp_message'):
            # 立即 nack（重新入隊）
            await message._amqp_message.nack(requeue=True)
        return message

    async def ack(self, message_id: str) -> bool:
        """確認訊息已處理"""
        # 注意：實際的 ack 需要透過 message._amqp_message.ack()
        # 這裡只是記錄統計
        self._total_acked += 1

        logger.info("Message acknowledged", extra={
            "message_id": message_id,
            "service": "robot_service.queue.rabbitmq"
        })

        return True

    async def nack(self, message_id: str, requeue: bool = True) -> bool:
        """拒絕訊息（處理失敗）"""
        # 注意：實際的 nack 需要透過 message._amqp_message.nack()
        # 這裡只是記錄統計
        self._total_nacked += 1

        logger.info("Message nacked", extra={
            "message_id": message_id,
            "requeue": requeue,
            "service": "robot_service.queue.rabbitmq"
        })

        return True

    async def size(self) -> int:
        """取得佇列大小"""
        if not self._initialized:
            await self.initialize()

        try:
            async with self._channel_pool.acquire() as channel:
                queue = await channel.get_queue(self.queue_name)
                declaration_result = await queue.declare(passive=True)
                return declaration_result.message_count

        except Exception as e:
            logger.error("Failed to get queue size", extra={
                "error": str(e),
                "service": "robot_service.queue.rabbitmq"
            })
            return 0

    async def clear(self) -> None:
        """清空佇列"""
        if not self._initialized:
            await self.initialize()

        try:
            async with self._channel_pool.acquire() as channel:
                queue = await channel.get_queue(self.queue_name)
                await queue.purge()

            logger.info("Queue cleared", extra={
                "service": "robot_service.queue.rabbitmq"
            })

        except Exception as e:
            logger.error("Failed to clear queue", extra={
                "error": str(e),
                "service": "robot_service.queue.rabbitmq"
            })

    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        if not self._initialized:
            try:
                await self.initialize()
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "type": "rabbitmq",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        try:
            queue_size = await self.size()

            # 檢查連線狀態
            async with self._connection_pool.acquire() as connection:
                is_connected = not connection.is_closed

            return {
                "status": "healthy" if is_connected else "unhealthy",
                "type": "rabbitmq",
                "connected": is_connected,
                "queue_name": self.queue_name,
                "queue_size": queue_size,
                "exchange": self.exchange_name,
                "dlx": self.dlx_name,
                "dlq": self.dlq_name,
                "statistics": {
                    "total_enqueued": self._total_enqueued,
                    "total_dequeued": self._total_dequeued,
                    "total_acked": self._total_acked,
                    "total_nacked": self._total_nacked,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "type": "rabbitmq",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
