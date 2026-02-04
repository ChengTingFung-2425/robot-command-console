"""
Service Manager
服務管理器，協調佇列與指令處理
支援 MemoryQueue（單機）、RabbitMQ（分散式）與 AWS SQS（雲端）
"""

import logging
import os
import threading
from typing import Any, Callable, Dict, List, Optional

from .queue import Message, MessagePriority, MemoryQueue, RabbitMQQueue, SQSQueue, QueueHandler, QueueInterface
from .command_processor import CommandProcessor


logger = logging.getLogger(__name__)


class ServiceManager:
    """
    服務管理器

    負責：
    - 初始化與管理佇列
    - 啟動與停止佇列處理器
    - 提供統一的 API 介面
    - 整合指令處理邏輯
    """

    def __init__(
        self,
        queue_max_size: Optional[int] = None,
        max_workers: int = 5,
        poll_interval: float = 0.1,
        queue_type: str = "memory",
        rabbitmq_url: Optional[str] = None,
        rabbitmq_config: Optional[Dict[str, Any]] = None,
        sqs_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化服務管理器

        Args:
            queue_max_size: 佇列最大大小（僅用於 MemoryQueue）
            max_workers: 最大並行工作數
            poll_interval: 輪詢間隔（秒）
            queue_type: 佇列類型 ("memory", "rabbitmq", 或 "sqs")
            rabbitmq_url: RabbitMQ 連線 URL（當 queue_type="rabbitmq" 時必需）
            rabbitmq_config: RabbitMQ 額外配置（exchange、queue 名稱等）
            sqs_config: AWS SQS 配置（queue_url、region 等）
        """
        self.queue_type = queue_type
        self.max_workers = max_workers
        self.poll_interval = poll_interval
        self._started = False

        # 根據配置建立佇列
        if queue_type == "rabbitmq":
            rabbitmq_url = rabbitmq_url or os.getenv(
                "RABBITMQ_URL",
                "amqp://guest:guest@localhost:5672/"
            )
            config = rabbitmq_config or {}

            self.queue: QueueInterface = RabbitMQQueue(
                url=rabbitmq_url,
                exchange_name=config.get("exchange_name", "robot.commands"),
                queue_name=config.get("queue_name", "robot.commands.queue"),
                dlx_name=config.get("dlx_name", "robot.commands.dlx"),
                dlq_name=config.get("dlq_name", "robot.commands.dlq"),
                prefetch_count=config.get("prefetch_count", max_workers),
                connection_pool_size=config.get("connection_pool_size", 2),
                channel_pool_size=config.get("channel_pool_size", 10),
            )

            logger.info("ServiceManager initialized with RabbitMQ", extra={
                "rabbitmq_url": rabbitmq_url,
                "exchange": config.get("exchange_name", "robot.commands"),
                "queue": config.get("queue_name", "robot.commands.queue"),
                "max_workers": max_workers,
                "service": "robot_service"
            })

        elif queue_type == "sqs":
            config = sqs_config or {}

            self.queue = SQSQueue(
                queue_url=config.get("queue_url"),
                queue_name=config.get("queue_name", "robot-edge-commands-queue"),
                dlq_name=config.get("dlq_name", "robot-edge-commands-dlq"),
                region_name=config.get("region_name", "us-east-1"),
                aws_access_key_id=config.get("aws_access_key_id"),
                aws_secret_access_key=config.get("aws_secret_access_key"),
                visibility_timeout=config.get("visibility_timeout", 30),
                wait_time_seconds=config.get("wait_time_seconds", 20),  # 使用長輪詢
                max_messages=config.get("max_messages", 10),
                use_fifo=config.get("use_fifo", False),
            )

            logger.info("ServiceManager initialized with AWS SQS", extra={
                "queue_name": config.get("queue_name", "robot-edge-commands-queue"),
                "region": config.get("region_name", "us-east-1"),
                "use_fifo": config.get("use_fifo", False),
                "wait_time_seconds": config.get("wait_time_seconds", 20),
                "max_workers": max_workers,
                "service": "robot_service"
            })

        else:
            # 預設使用 MemoryQueue
            self.queue = MemoryQueue(max_size=queue_max_size)

            logger.info("ServiceManager initialized with MemoryQueue", extra={
                "queue_max_size": queue_max_size,
                "max_workers": max_workers,
                "service": "robot_service"
            })

        self.handler: Optional[QueueHandler] = None

        # 初始化 CommandProcessor（使用預設分派器）
        self._command_processor = CommandProcessor()
        self._processor_lock = threading.Lock()

    async def start(self, processor=None) -> None:
        """
        啟動服務

        Args:
            processor: 訊息處理函式（可選，若無則使用預設處理器）
        """
        if self._started:
            logger.warning("ServiceManager already started", extra={
                "service": "robot_service"
            })
            return

        # 初始化 RabbitMQ 或 SQS（如果使用）
        if self.queue_type in ("rabbitmq", "sqs") and hasattr(self.queue, 'initialize'):
            await self.queue.initialize()
            logger.info(f"{self.queue_type.upper()} queue initialized", extra={
                "service": "robot_service"
            })

        # 使用預設或自訂處理器
        if processor is None:
            processor = self._default_processor

        self.handler = QueueHandler(
            queue=self.queue,
            processor=processor,
            max_workers=self.max_workers,
            poll_interval=self.poll_interval,
        )

        await self.handler.start()
        self._started = True

        logger.info("ServiceManager started", extra={
            "queue_type": self.queue_type,
            "service": "robot_service"
        })

    async def stop(self, timeout: Optional[float] = 30.0) -> None:
        """
        停止服務

        Args:
            timeout: 等待逾時（秒）
        """
        if not self._started:
            return

        logger.info("ServiceManager stopping", extra={
            "service": "robot_service"
        })

        if self.handler:
            await self.handler.stop(timeout=timeout)

        # 關閉 RabbitMQ 或 SQS 連線（如果使用）
        if self.queue_type in ("rabbitmq", "sqs") and hasattr(self.queue, 'close'):
            await self.queue.close()
            logger.info(f"{self.queue_type.upper()} connection closed", extra={
                "service": "robot_service"
            })

        self._started = False

        logger.info("ServiceManager stopped", extra={
            "service": "robot_service"
        })

    async def submit_command(
        self,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        提交指令到佇列

        Args:
            payload: 指令內容
            priority: 優先權
            trace_id: 追蹤 ID
            correlation_id: 關聯 ID

        Returns:
            訊息 ID，失敗則返回 None
        """
        message = Message(
            payload=payload,
            priority=priority,
            trace_id=trace_id,
            correlation_id=correlation_id,
        )

        success = await self.queue.enqueue(message)

        if success:
            logger.info("Command submitted", extra={
                "message_id": message.id,
                "trace_id": trace_id,
                "correlation_id": correlation_id,
                "service": "robot_service"
            })
            return message.id
        else:
            logger.error("Failed to submit command", extra={
                "trace_id": trace_id,
                "correlation_id": correlation_id,
                "service": "robot_service"
            })
            return None

    async def _default_processor(self, message: Message) -> bool:
        """
        預設訊息處理器

        使用 CommandProcessor 處理指令訊息，將指令轉換為動作並分派執行。

        Args:
            message: 要處理的訊息

        Returns:
            是否成功處理
        """
        logger.info("Processing message with default processor", extra={
            "message_id": message.id,
            "payload": message.payload,
            "trace_id": message.trace_id,
            "service": "robot_service"
        })

        # 使用已初始化的 CommandProcessor 處理指令
        return await self._command_processor.process(message)

    def set_action_dispatcher(
        self,
        dispatcher: Callable[[str, List[str]], bool]
    ) -> None:
        """
        設定動作分派函式

        當需要將動作實際發送到機器人時，使用此方法注入分派邏輯。
        注意：此方法應在服務啟動前呼叫，以避免處理中斷。

        Args:
            dispatcher: 分派函式，接受 (robot_id, actions) 並返回成功與否
        """
        with self._processor_lock:
            if self._started:
                logger.warning("Changing dispatcher while service is running", extra={
                    "service": "robot_service"
                })

            self._command_processor = CommandProcessor(action_dispatcher=dispatcher)
            logger.info("Action dispatcher configured", extra={
                "service": "robot_service"
            })

    async def health_check(self) -> Dict[str, Any]:
        """
        健康檢查

        Returns:
            健康狀態資訊
        """
        queue_health = await self.queue.health_check()
        # Add ServiceManager-specific fields
        return {
            **queue_health,
            "started": self._started,
            "handler": {
                "running": self._started,
                "max_workers": self.max_workers,
            }
        }

    async def get_queue_stats(self) -> Dict[str, Any]:
        """
        取得佇列統計資訊

        Returns:
            佇列統計資訊
        """
        health = await self.queue.health_check()
        return {
            "queue_type": self.queue_type,
            "queue_size": await self.queue.size(),
            "health": health,
            "handler_running": self._started,
            "max_workers": self.max_workers,
        }
