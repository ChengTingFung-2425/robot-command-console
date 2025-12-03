"""
Service Manager
服務管理器，協調佇列與指令處理
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from .queue import Message, MessagePriority, MemoryQueue, QueueHandler
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
    ):
        """
        初始化服務管理器

        Args:
            queue_max_size: 佇列最大大小
            max_workers: 最大並行工作數
            poll_interval: 輪詢間隔（秒）
        """
        self.queue = MemoryQueue(max_size=queue_max_size)
        self.handler: Optional[QueueHandler] = None
        self.max_workers = max_workers
        self.poll_interval = poll_interval
        self._started = False

        logger.info("ServiceManager initialized", extra={
            "queue_max_size": queue_max_size,
            "max_workers": max_workers,
            "service": "robot_service"
        })

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

        # 使用 CommandProcessor 處理指令
        if not hasattr(self, '_command_processor'):
            self._command_processor = CommandProcessor()

        return await self._command_processor.process(message)

    def set_action_dispatcher(
        self,
        dispatcher: Callable[[str, List[str]], bool]
    ) -> None:
        """
        設定動作分派函式

        當需要將動作實際發送到機器人時，使用此方法注入分派邏輯。

        Args:
            dispatcher: 分派函式，接受 (robot_id, actions) 並返回成功與否
        """
        self._command_processor = CommandProcessor(action_dispatcher=dispatcher)
        logger.info("Action dispatcher configured", extra={
            "service": "robot_service"
        })

    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        handler_health = {}
        if self.handler:
            handler_health = await self.handler.health_check()

        return {
            "status": "healthy" if self._started else "stopped",
            "started": self._started,
            "handler": handler_health,
        }

    async def get_queue_stats(self) -> Dict[str, Any]:
        """取得佇列統計資訊"""
        return await self.queue.health_check()
