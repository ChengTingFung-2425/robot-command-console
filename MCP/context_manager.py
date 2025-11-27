"""
MCP 上下文管理器
負責管理指令上下文、狀態歷史與冪等性
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from .models import CommandRequest, CommandResponse


logger = logging.getLogger(__name__)


class ContextManager:
    """上下文管理器"""

    def __init__(self):
        """初始化管理器"""
        self.contexts: Dict[str, Dict[str, Any]] = {}
        self.command_results: Dict[str, CommandResponse] = {}

    async def create_context(self, trace_id: str, request: CommandRequest):
        """建立上下文"""
        self.contexts[trace_id] = {
            "trace_id": trace_id,
            "command_id": request.command.id,
            "created_at": datetime.utcnow(),
            "request": request.dict(),
            "events": []
        }
        logger.debug(f"建立上下文: {trace_id}")

    async def get_context(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """取得上下文"""
        return self.contexts.get(trace_id)

    async def update_context(self, trace_id: str, updates: Dict[str, Any]):
        """更新上下文"""
        if trace_id in self.contexts:
            self.contexts[trace_id].update(updates)

    async def add_event_to_context(self, trace_id: str, event: Dict[str, Any]):
        """新增事件到上下文"""
        if trace_id in self.contexts:
            self.contexts[trace_id]["events"].append(event)

    async def command_exists(self, command_id: str) -> bool:
        """檢查指令是否已存在"""
        return command_id in self.command_results

    async def update_result(self, command_id: str, response: CommandResponse):
        """更新指令結果"""
        self.command_results[command_id] = response
        logger.debug(f"更新指令結果: {command_id}")

    async def get_cached_response(self, command_id: str) -> Optional[CommandResponse]:
        """取得快取的回應"""
        return self.command_results.get(command_id)

    async def get_command_status(self, command_id: str) -> Optional[Dict[str, Any]]:
        """取得指令狀態"""
        response = self.command_results.get(command_id)
        if response:
            return {
                "command_id": command_id,
                "status": response.command.get("status"),
                "result": response.result.dict() if response.result else None,
                "error": response.error.dict() if response.error else None,
                "timestamp": response.timestamp.isoformat()
            }
        return None
