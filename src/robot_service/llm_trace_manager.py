"""
LLM Trace Manager

追蹤 LLM 處理過程，記錄輸入、輸出和執行流程
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)


class TraceEventType(Enum):
    """追蹤事件類型"""
    INPUT_RECEIVED = "input_received"           # 收到輸入
    LLM_REQUEST = "llm_request"                 # 發送給 LLM
    LLM_RESPONSE = "llm_response"               # LLM 回應
    FUNCTION_CALL = "function_call"             # Function call
    FUNCTION_EXECUTED = "function_executed"     # Function 執行完成
    BRIDGE_CALL = "bridge_call"                 # Bridge 呼叫
    QUEUE_ENQUEUED = "queue_enqueued"          # 加入佇列
    ROBOT_EXECUTED = "robot_executed"           # 機器人執行
    ERROR = "error"                             # 錯誤
    COMPLETED = "completed"                     # 完成


class TraceEvent:
    """追蹤事件"""
    
    def __init__(
        self,
        trace_id: str,
        event_type: TraceEventType,
        data: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ):
        self.trace_id = trace_id
        self.event_type = event_type
        self.data = data
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "trace_id": self.trace_id,
            "event_type": self.event_type.value,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_json(self) -> str:
        """轉換為 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class LLMTraceManager:
    """
    LLM 追蹤管理器
    
    功能：
    - 追蹤 LLM 處理的完整流程
    - 記錄每個步驟的輸入和輸出
    - 提供即時追蹤和歷史查詢
    - 支援追蹤事件訂閱
    """
    
    def __init__(self, max_traces: int = 1000):
        """
        初始化追蹤管理器
        
        Args:
            max_traces: 最大保存的追蹤記錄數
        """
        self.max_traces = max_traces
        self._traces: Dict[str, List[TraceEvent]] = {}  # trace_id -> events
        self._active_traces: Dict[str, Dict[str, Any]] = {}  # trace_id -> metadata
        self._subscribers: List[Callable] = []
        self._lock = asyncio.Lock()
    
    def generate_trace_id(self) -> str:
        """生成追蹤 ID"""
        import uuid
        return f"trace-{uuid.uuid4().hex[:16]}"
    
    async def start_trace(
        self,
        trace_id: Optional[str] = None,
        input_type: str = "text",
        input_data: Any = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        開始新的追蹤
        
        Args:
            trace_id: 追蹤 ID（若未指定則自動生成）
            input_type: 輸入類型（text, speech）
            input_data: 輸入資料
            metadata: 額外的元資料
        
        Returns:
            追蹤 ID
        """
        if not trace_id:
            trace_id = self.generate_trace_id()
        
        async with self._lock:
            # 初始化追蹤
            self._traces[trace_id] = []
            self._active_traces[trace_id] = {
                "input_type": input_type,
                "started_at": datetime.now(),
                "metadata": metadata or {}
            }
            
            # 記錄輸入事件
            await self._add_event(
                trace_id,
                TraceEventType.INPUT_RECEIVED,
                {
                    "input_type": input_type,
                    "input_data": input_data,
                    "metadata": metadata
                }
            )
        
        logger.info(f"開始追蹤: {trace_id}, type={input_type}")
        return trace_id
    
    async def trace_llm_request(
        self,
        trace_id: str,
        messages: List[Dict[str, str]],
        functions: Optional[List[Dict[str, Any]]] = None,
        provider: str = "openai"
    ):
        """
        追蹤 LLM 請求
        
        Args:
            trace_id: 追蹤 ID
            messages: 發送給 LLM 的訊息
            functions: 可用的 functions
            provider: LLM 提供商
        """
        await self._add_event(
            trace_id,
            TraceEventType.LLM_REQUEST,
            {
                "provider": provider,
                "messages": messages,
                "functions_count": len(functions) if functions else 0,
                "functions": [f["name"] for f in functions] if functions else []
            }
        )
        logger.debug(f"追蹤 LLM 請求: {trace_id}, provider={provider}")
    
    async def trace_llm_response(
        self,
        trace_id: str,
        response: Dict[str, Any],
        processing_time_ms: float
    ):
        """
        追蹤 LLM 回應
        
        Args:
            trace_id: 追蹤 ID
            response: LLM 回應
            processing_time_ms: 處理時間（毫秒）
        """
        await self._add_event(
            trace_id,
            TraceEventType.LLM_RESPONSE,
            {
                "response": response,
                "processing_time_ms": processing_time_ms,
                "has_function_call": "function_call" in response
            }
        )
        logger.debug(f"追蹤 LLM 回應: {trace_id}, time={processing_time_ms}ms")
    
    async def trace_function_call(
        self,
        trace_id: str,
        function_name: str,
        arguments: Dict[str, Any]
    ):
        """
        追蹤 Function Call
        
        Args:
            trace_id: 追蹤 ID
            function_name: Function 名稱
            arguments: 參數
        """
        await self._add_event(
            trace_id,
            TraceEventType.FUNCTION_CALL,
            {
                "function_name": function_name,
                "arguments": arguments
            }
        )
        logger.debug(f"追蹤 Function Call: {trace_id}, func={function_name}")
    
    async def trace_function_executed(
        self,
        trace_id: str,
        function_name: str,
        result: Dict[str, Any],
        execution_time_ms: float
    ):
        """
        追蹤 Function 執行結果
        
        Args:
            trace_id: 追蹤 ID
            function_name: Function 名稱
            result: 執行結果
            execution_time_ms: 執行時間（毫秒）
        """
        await self._add_event(
            trace_id,
            TraceEventType.FUNCTION_EXECUTED,
            {
                "function_name": function_name,
                "result": result,
                "execution_time_ms": execution_time_ms,
                "success": result.get("success", False)
            }
        )
        logger.debug(f"追蹤 Function 執行: {trace_id}, func={function_name}, time={execution_time_ms}ms")
    
    async def trace_bridge_call(
        self,
        trace_id: str,
        endpoint: str,
        request: Dict[str, Any],
        response: Optional[Dict[str, Any]] = None
    ):
        """
        追蹤 Bridge 呼叫
        
        Args:
            trace_id: 追蹤 ID
            endpoint: 端點 URL
            request: 請求資料
            response: 回應資料
        """
        await self._add_event(
            trace_id,
            TraceEventType.BRIDGE_CALL,
            {
                "endpoint": endpoint,
                "request": request,
                "response": response
            }
        )
        logger.debug(f"追蹤 Bridge 呼叫: {trace_id}, endpoint={endpoint}")
    
    async def trace_queue_enqueued(
        self,
        trace_id: str,
        queue_name: str,
        message: Dict[str, Any]
    ):
        """
        追蹤加入佇列
        
        Args:
            trace_id: 追蹤 ID
            queue_name: 佇列名稱
            message: 訊息內容
        """
        await self._add_event(
            trace_id,
            TraceEventType.QUEUE_ENQUEUED,
            {
                "queue_name": queue_name,
                "message": message
            }
        )
        logger.debug(f"追蹤加入佇列: {trace_id}, queue={queue_name}")
    
    async def trace_robot_executed(
        self,
        trace_id: str,
        robot_id: str,
        action: str,
        result: Dict[str, Any]
    ):
        """
        追蹤機器人執行
        
        Args:
            trace_id: 追蹤 ID
            robot_id: 機器人 ID
            action: 動作名稱
            result: 執行結果
        """
        await self._add_event(
            trace_id,
            TraceEventType.ROBOT_EXECUTED,
            {
                "robot_id": robot_id,
                "action": action,
                "result": result
            }
        )
        logger.debug(f"追蹤機器人執行: {trace_id}, robot={robot_id}, action={action}")
    
    async def trace_error(
        self,
        trace_id: str,
        error: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        追蹤錯誤
        
        Args:
            trace_id: 追蹤 ID
            error: 錯誤訊息
            context: 錯誤上下文
        """
        await self._add_event(
            trace_id,
            TraceEventType.ERROR,
            {
                "error": error,
                "context": context
            }
        )
        logger.error(f"追蹤錯誤: {trace_id}, error={error}")
    
    async def complete_trace(
        self,
        trace_id: str,
        success: bool = True,
        final_result: Optional[Dict[str, Any]] = None
    ):
        """
        完成追蹤
        
        Args:
            trace_id: 追蹤 ID
            success: 是否成功
            final_result: 最終結果
        """
        async with self._lock:
            if trace_id in self._active_traces:
                started_at = self._active_traces[trace_id]["started_at"]
                duration_ms = (datetime.now() - started_at).total_seconds() * 1000
                
                await self._add_event(
                    trace_id,
                    TraceEventType.COMPLETED,
                    {
                        "success": success,
                        "final_result": final_result,
                        "duration_ms": duration_ms
                    }
                )
                
                # 移除活動追蹤
                del self._active_traces[trace_id]
                
                logger.info(f"完成追蹤: {trace_id}, success={success}, duration={duration_ms}ms")
    
    async def _add_event(
        self,
        trace_id: str,
        event_type: TraceEventType,
        data: Dict[str, Any]
    ):
        """
        新增追蹤事件
        
        Args:
            trace_id: 追蹤 ID
            event_type: 事件類型
            data: 事件資料
        """
        event = TraceEvent(trace_id, event_type, data)
        
        async with self._lock:
            if trace_id not in self._traces:
                self._traces[trace_id] = []
            
            self._traces[trace_id].append(event)
            
            # 限制追蹤記錄數量
            if len(self._traces) > self.max_traces:
                oldest_trace = min(self._traces.keys())
                del self._traces[oldest_trace]
        
        # 通知訂閱者
        await self._notify_subscribers(event)
    
    async def _notify_subscribers(self, event: TraceEvent):
        """
        通知訂閱者
        
        Args:
            event: 追蹤事件
        """
        for subscriber in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(event)
                else:
                    subscriber(event)
            except Exception as e:
                logger.exception(f"通知訂閱者時發生錯誤: {e}")
    
    def subscribe(self, callback: Callable[[TraceEvent], None]):
        """
        訂閱追蹤事件
        
        Args:
            callback: 回調函數
        """
        self._subscribers.append(callback)
        logger.debug(f"新增追蹤訂閱者: {callback}")
    
    def unsubscribe(self, callback: Callable[[TraceEvent], None]):
        """
        取消訂閱
        
        Args:
            callback: 回調函數
        """
        if callback in self._subscribers:
            self._subscribers.remove(callback)
            logger.debug(f"移除追蹤訂閱者: {callback}")
    
    async def get_trace(self, trace_id: str) -> Optional[List[TraceEvent]]:
        """
        取得追蹤記錄
        
        Args:
            trace_id: 追蹤 ID
        
        Returns:
            追蹤事件列表
        """
        async with self._lock:
            return self._traces.get(trace_id)
    
    async def get_all_traces(self) -> Dict[str, List[TraceEvent]]:
        """
        取得所有追蹤記錄
        
        Returns:
            所有追蹤記錄
        """
        async with self._lock:
            return self._traces.copy()
    
    async def get_active_traces(self) -> List[str]:
        """
        取得活動追蹤 ID 列表
        
        Returns:
            活動追蹤 ID 列表
        """
        async with self._lock:
            return list(self._active_traces.keys())
    
    async def get_trace_summary(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        取得追蹤摘要
        
        Args:
            trace_id: 追蹤 ID
        
        Returns:
            追蹤摘要
        """
        events = await self.get_trace(trace_id)
        if not events:
            return None
        
        # 提取關鍵資訊
        summary = {
            "trace_id": trace_id,
            "event_count": len(events),
            "started_at": events[0].timestamp.isoformat(),
            "events": []
        }
        
        # 分類事件
        for event in events:
            summary["events"].append({
                "type": event.event_type.value,
                "timestamp": event.timestamp.isoformat(),
                "summary": self._summarize_event(event)
            })
        
        # 計算總時長
        if len(events) > 1:
            duration = (events[-1].timestamp - events[0].timestamp).total_seconds() * 1000
            summary["duration_ms"] = duration
        
        return summary
    
    def _summarize_event(self, event: TraceEvent) -> str:
        """
        總結事件內容
        
        Args:
            event: 追蹤事件
        
        Returns:
            事件摘要
        """
        event_type = event.event_type
        data = event.data
        
        if event_type == TraceEventType.INPUT_RECEIVED:
            return f"Received {data.get('input_type')} input"
        elif event_type == TraceEventType.LLM_REQUEST:
            return f"Request to {data.get('provider')}"
        elif event_type == TraceEventType.LLM_RESPONSE:
            return f"Response in {data.get('processing_time_ms')}ms"
        elif event_type == TraceEventType.FUNCTION_CALL:
            return f"Call function: {data.get('function_name')}"
        elif event_type == TraceEventType.FUNCTION_EXECUTED:
            return f"Executed {data.get('function_name')} in {data.get('execution_time_ms')}ms"
        elif event_type == TraceEventType.BRIDGE_CALL:
            return f"Bridge call to {data.get('endpoint')}"
        elif event_type == TraceEventType.QUEUE_ENQUEUED:
            return f"Enqueued to {data.get('queue_name')}"
        elif event_type == TraceEventType.ROBOT_EXECUTED:
            return f"Robot {data.get('robot_id')} executed {data.get('action')}"
        elif event_type == TraceEventType.ERROR:
            return f"Error: {data.get('error')}"
        elif event_type == TraceEventType.COMPLETED:
            return f"Completed in {data.get('duration_ms')}ms"
        
        return str(data)
    
    async def export_trace(self, trace_id: str, format: str = "json") -> str:
        """
        匯出追蹤記錄
        
        Args:
            trace_id: 追蹤 ID
            format: 匯出格式（json, text）
        
        Returns:
            匯出的追蹤資料
        """
        events = await self.get_trace(trace_id)
        if not events:
            return ""
        
        if format == "json":
            return json.dumps(
                [event.to_dict() for event in events],
                ensure_ascii=False,
                indent=2
            )
        elif format == "text":
            lines = [f"Trace ID: {trace_id}", "=" * 80]
            for event in events:
                time_str = event.timestamp.strftime("%H:%M:%S.%f")[:-3]
                lines.append(f"[{time_str}] {event.event_type.value}: {self._summarize_event(event)}")
            return "\n".join(lines)
        
        return ""
