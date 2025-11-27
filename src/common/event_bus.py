"""
Local Event Bus
記憶體內 Pub/Sub 事件匯流排，用於服務間事件通訊

提供：
- 非同步事件發布/訂閱
- 多訂閱者支援
- 萬用字元訂閱（topic.*）
- 事件歷史記錄（可選）
"""

import asyncio
import fnmatch
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from .datetime_utils import utc_now

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """事件"""
    topic: str
    data: Any
    timestamp: datetime = field(default_factory=utc_now)
    source: Optional[str] = None
    correlation_id: Optional[str] = None


# 事件處理器類型
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


@dataclass
class Subscription:
    """訂閱資訊"""
    id: str
    pattern: str
    handler: EventHandler
    created_at: datetime = field(default_factory=utc_now)
    is_pattern: bool = False


class LocalEventBus:
    """
    本地事件匯流排

    提供記憶體內的 Pub/Sub 機制：
    - 精確主題訂閱：`robot.status`
    - 萬用字元訂閱：`robot.*`、`*.updated`
    - 非同步事件傳遞
    - 可選的事件歷史記錄
    """

    def __init__(
        self,
        history_size: int = 100,
        enable_history: bool = True,
    ):
        """
        初始化事件匯流排

        Args:
            history_size: 事件歷史記錄大小
            enable_history: 是否啟用事件歷史
        """
        self._subscriptions: Dict[str, Subscription] = {}
        self._topic_handlers: Dict[str, Set[str]] = defaultdict(set)
        self._pattern_subscriptions: Dict[str, Set[str]] = defaultdict(set)  # pattern -> set of subscription_ids
        self._history: List[Event] = []
        self._history_size = history_size
        self._enable_history = enable_history
        self._subscription_counter = 0
        self._lock = asyncio.Lock()
        self._running = False

        logger.info("LocalEventBus initialized", extra={
            "history_size": history_size,
            "enable_history": enable_history,
            "service": "event_bus"
        })

    async def start(self) -> None:
        """啟動事件匯流排"""
        self._running = True
        logger.info("LocalEventBus started", extra={
            "service": "event_bus"
        })

    async def stop(self) -> None:
        """停止事件匯流排"""
        self._running = False
        logger.info("LocalEventBus stopped", extra={
            "service": "event_bus"
        })

    async def subscribe(
        self,
        pattern: str,
        handler: EventHandler,
    ) -> str:
        """
        訂閱事件

        Args:
            pattern: 主題模式（支援 * 萬用字元）
            handler: 事件處理器（非同步函式）

        Returns:
            訂閱 ID
        """
        async with self._lock:
            self._subscription_counter += 1
            subscription_id = f"sub_{self._subscription_counter}"

            is_pattern = '*' in pattern or '?' in pattern

            subscription = Subscription(
                id=subscription_id,
                pattern=pattern,
                handler=handler,
                is_pattern=is_pattern,
            )

            self._subscriptions[subscription_id] = subscription

            if is_pattern:
                self._pattern_subscriptions[pattern].add(subscription_id)
            else:
                self._topic_handlers[pattern].add(subscription_id)

            logger.debug("Subscription created", extra={
                "subscription_id": subscription_id,
                "pattern": pattern,
                "is_pattern": is_pattern,
                "service": "event_bus"
            })

            return subscription_id

    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        取消訂閱

        Args:
            subscription_id: 訂閱 ID

        Returns:
            是否成功取消
        """
        async with self._lock:
            if subscription_id not in self._subscriptions:
                return False

            subscription = self._subscriptions[subscription_id]

            if subscription.is_pattern:
                if subscription.pattern in self._pattern_subscriptions:
                    self._pattern_subscriptions[subscription.pattern].discard(subscription_id)
                    if not self._pattern_subscriptions[subscription.pattern]:
                        del self._pattern_subscriptions[subscription.pattern]
            else:
                if subscription.pattern in self._topic_handlers:
                    self._topic_handlers[subscription.pattern].discard(subscription_id)
                    if not self._topic_handlers[subscription.pattern]:
                        del self._topic_handlers[subscription.pattern]

            del self._subscriptions[subscription_id]

            logger.debug("Subscription removed", extra={
                "subscription_id": subscription_id,
                "pattern": subscription.pattern,
                "service": "event_bus"
            })

            return True

    async def publish(
        self,
        topic: str,
        data: Any,
        source: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> int:
        """
        發布事件

        Args:
            topic: 事件主題
            data: 事件資料
            source: 事件來源
            correlation_id: 關聯 ID

        Returns:
            接收到事件的訂閱者數量
        """
        event = Event(
            topic=topic,
            data=data,
            source=source,
            correlation_id=correlation_id,
        )

        # 記錄歷史
        if self._enable_history:
            async with self._lock:
                self._history.append(event)
                if len(self._history) > self._history_size:
                    self._history = self._history[-self._history_size:]

        # 取得匹配的訂閱
        matching_subscriptions = await self._get_matching_subscriptions(topic)

        if not matching_subscriptions:
            logger.debug("No subscribers for event", extra={
                "topic": topic,
                "service": "event_bus"
            })
            return 0

        # 非同步發送給所有訂閱者
        tasks = []
        for subscription in matching_subscriptions:
            task = asyncio.create_task(
                self._deliver_event(subscription, event)
            )
            tasks.append(task)

        # 等待所有傳遞完成
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logger.debug("Event published", extra={
            "topic": topic,
            "subscriber_count": len(matching_subscriptions),
            "source": source,
            "correlation_id": correlation_id,
            "service": "event_bus"
        })

        return len(matching_subscriptions)

    async def _get_matching_subscriptions(self, topic: str) -> List[Subscription]:
        """取得匹配主題的所有訂閱"""
        matching = []

        async with self._lock:
            # 精確匹配
            if topic in self._topic_handlers:
                for sub_id in self._topic_handlers[topic]:
                    if sub_id in self._subscriptions:
                        matching.append(self._subscriptions[sub_id])

            # 萬用字元匹配
            for pattern, sub_ids in self._pattern_subscriptions.items():
                if fnmatch.fnmatch(topic, pattern):
                    for sub_id in sub_ids:
                        if sub_id in self._subscriptions:
                            matching.append(self._subscriptions[sub_id])

        return matching

    async def _deliver_event(
        self,
        subscription: Subscription,
        event: Event,
    ) -> None:
        """傳遞事件給訂閱者"""
        try:
            await subscription.handler(event)
        except Exception as e:
            logger.error("Error delivering event", extra={
                "subscription_id": subscription.id,
                "pattern": subscription.pattern,
                "topic": event.topic,
                "error": str(e),
                "service": "event_bus"
            })

    async def get_history(
        self,
        topic_filter: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Event]:
        """
        取得事件歷史

        Args:
            topic_filter: 主題過濾（支援萬用字元）
            limit: 返回數量限制

        Returns:
            事件歷史列表
        """
        if not self._enable_history:
            return []

        async with self._lock:
            events = list(self._history)

        if topic_filter:
            events = [
                e for e in events
                if fnmatch.fnmatch(e.topic, topic_filter)
            ]

        if limit:
            events = events[-limit:]

        return events

    async def clear_history(self) -> None:
        """清除事件歷史"""
        async with self._lock:
            self._history.clear()

        logger.info("Event history cleared", extra={
            "service": "event_bus"
        })

    async def get_subscriptions(self) -> Dict[str, Dict[str, Any]]:
        """
        取得所有訂閱資訊

        Returns:
            訂閱資訊字典
        """
        async with self._lock:
            return {
                sub_id: {
                    "id": sub.id,
                    "pattern": sub.pattern,
                    "is_pattern": sub.is_pattern,
                    "created_at": sub.created_at.isoformat(),
                }
                for sub_id, sub in self._subscriptions.items()
            }

    async def get_topics(self) -> List[str]:
        """
        取得所有已註冊的主題

        Returns:
            主題列表
        """
        async with self._lock:
            return list(self._topic_handlers.keys())

    async def health_check(self) -> Dict[str, Any]:
        """
        健康檢查

        Returns:
            健康狀態資訊
        """
        async with self._lock:
            subscription_count = len(self._subscriptions)
            topic_count = len(self._topic_handlers)
            pattern_count = len(self._pattern_subscriptions)
            history_count = len(self._history)

        return {
            "status": "healthy" if self._running else "stopped",
            "running": self._running,
            "subscription_count": subscription_count,
            "topic_count": topic_count,
            "pattern_count": pattern_count,
            "history_count": history_count,
            "history_enabled": self._enable_history,
            "timestamp": utc_now().isoformat(),
        }
