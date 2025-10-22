"""
MCP 日誌監控模組
負責事件記錄、審計、指標收集與追蹤
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from .models import Event, EventCategory, EventSeverity


logger = logging.getLogger(__name__)


class LoggingMonitor:
    """日誌監控器"""
    
    def __init__(self):
        """初始化監控器"""
        self.events: List[Event] = []
        self.metrics: Dict[str, Any] = defaultdict(int)
        self.event_subscribers: List[callable] = []
    
    async def emit_event(self, event: Event):
        """發送事件"""
        # 記錄事件
        self.events.append(event)
        
        # 記錄日誌
        log_method = self._get_log_method(event.severity)
        log_method(f"[{event.category.value}] {event.message} (trace_id={event.trace_id})")
        
        # 更新指標
        self.metrics[f"event_{event.category.value}_{event.severity.value}"] += 1
        
        # 通知訂閱者
        for subscriber in self.event_subscribers:
            try:
                await subscriber(event)
            except Exception as e:
                logger.error(f"事件訂閱者錯誤: {e}")
    
    def _get_log_method(self, severity: EventSeverity):
        """取得日誌方法"""
        mapping = {
            EventSeverity.DEBUG: logger.debug,
            EventSeverity.INFO: logger.info,
            EventSeverity.WARN: logger.warning,
            EventSeverity.ERROR: logger.error
        }
        return mapping.get(severity, logger.info)
    
    async def get_events(
        self,
        trace_id: Optional[str] = None,
        category: Optional[EventCategory] = None,
        severity: Optional[EventSeverity] = None,
        limit: int = 100
    ) -> List[Event]:
        """查詢事件"""
        events = self.events
        
        if trace_id:
            events = [e for e in events if e.trace_id == trace_id]
        
        if category:
            events = [e for e in events if e.category == category]
        
        if severity:
            events = [e for e in events if e.severity == severity]
        
        return events[-limit:]
    
    async def get_metrics(self) -> Dict[str, Any]:
        """取得指標"""
        return dict(self.metrics)
    
    async def subscribe_events(self, callback: callable):
        """訂閱事件"""
        self.event_subscribers.append(callback)
    
    async def unsubscribe_events(self, callback: callable):
        """取消訂閱事件"""
        if callback in self.event_subscribers:
            self.event_subscribers.remove(callback)
    
    async def record_metric(self, name: str, value: Any):
        """記錄指標"""
        self.metrics[name] = value
    
    async def increment_metric(self, name: str, delta: int = 1):
        """增加指標計數"""
        self.metrics[name] += delta
