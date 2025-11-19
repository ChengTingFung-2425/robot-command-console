"""
MCP 指令處理器
負責接收、驗證、排隊、路由、重試與超時控制
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from .config import MCPConfig
from .models import (
    CommandRequest,
    CommandResponse,
    CommandResult,
    CommandStatus,
    ErrorCode,
    ErrorDetail,
    Event,
    EventCategory,
    EventSeverity,
)
from .schema_validator import validator


logger = logging.getLogger(__name__)


class CommandHandler:
    """指令處理器"""
    
    def __init__(self, robot_router, context_manager, auth_manager, logging_monitor):
        """初始化指令處理器"""
        self.robot_router = robot_router
        self.context_manager = context_manager
        self.auth_manager = auth_manager
        self.logging_monitor = logging_monitor
        self.active_commands: Dict[str, Dict[str, Any]] = {}
    
    async def process_command(self, request: CommandRequest) -> CommandResponse:
        """處理指令"""
        command_id = request.command.id
        trace_id = request.trace_id
        
        try:
            # 0. Schema 驗證
            request_dict = request.dict()
            # 確保 timestamp 為 ISO8601 格式字串，並驗證格式
            ts = request.timestamp
            if isinstance(ts, datetime):
                request_dict["timestamp"] = ts.isoformat() + "Z"
            elif isinstance(ts, str):
                try:
                    # 支援 "Z" 結尾的 ISO8601
                    datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    request_dict["timestamp"] = ts
                except (ValueError, TypeError):
                    request_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
            else:
                request_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
            is_valid, error_msg = validator.validate_command_request(request_dict)
            if not is_valid:
                await self._emit_event(
                    trace_id,
                    EventSeverity.WARN,
                    EventCategory.COMMAND,
                    f"指令驗證失敗: {error_msg}",
                    {"command_id": command_id, "error": error_msg}
                )
                return self._create_error_response(
                    trace_id,
                    command_id,
                    ErrorCode.ERR_VALIDATION,
                    f"請求資料不符合 Schema: {error_msg}"
                )
            
            # 1. 驗證身份與授權
            if not await self._authenticate(request):
                await self._emit_event(
                    trace_id,
                    EventSeverity.WARN,
                    EventCategory.AUTH,
                    f"身份驗證失敗: command_id={command_id}",
                    {
                        "command_id": command_id,
                        "actor_id": request.actor.id,
                        "actor_type": request.actor.type
                    }
                )
                return self._create_error_response(
                    trace_id,
                    command_id,
                    ErrorCode.ERR_UNAUTHORIZED,
                    "身份驗證失敗"
                )
            
            if not await self._authorize(request):
                await self._emit_event(
                    trace_id,
                    EventSeverity.WARN,
                    EventCategory.AUTH,
                    f"授權失敗: command_id={command_id}",
                    {
                        "command_id": command_id,
                        "actor_id": request.actor.id,
                        "action": request.command.type,
                        "resource": request.command.target.robot_id
                    }
                )
                return self._create_error_response(
                    trace_id,
                    command_id,
                    ErrorCode.ERR_UNAUTHORIZED,
                    "權限不足"
                )
            
            # 2. 驗證資料格式與業務規則
            validation_error = await self._validate_command(request)
            if validation_error:
                return self._create_error_response(
                    trace_id,
                    command_id,
                    ErrorCode.ERR_VALIDATION,
                    validation_error
                )
            
            # 3. 檢查冪等性
            if await self._is_duplicate_command(command_id):
                logger.info(f"重複指令: {command_id}，返回快取結果")
                cached_response = await self._get_cached_response(command_id)
                if cached_response:
                    return cached_response
            
            # 4. 建立上下文
            await self.context_manager.create_context(trace_id, request)
            
            # 5. 發送接受事件
            await self._emit_event(
                trace_id,
                EventSeverity.INFO,
                EventCategory.COMMAND,
                f"指令已接受: {command_id}",
                {"command_id": command_id, "type": request.command.type}
            )
            
            # 6. 執行指令（非同步）
            asyncio.create_task(self._execute_command_async(request))
            
            # 7. 返回接受回應
            return CommandResponse(
                trace_id=trace_id,
                timestamp=datetime.utcnow(),
                command={"id": command_id, "status": CommandStatus.ACCEPTED.value},
                result=None,
                error=None
            )
            
        except Exception as e:
            logger.error(f"處理指令失敗: {e}", exc_info=True)
            await self._emit_event(
                trace_id,
                EventSeverity.ERROR,
                EventCategory.COMMAND,
                f"指令處理失敗: {str(e)}",
                {"command_id": command_id, "error": str(e)}
            )
            return self._create_error_response(
                trace_id,
                command_id,
                ErrorCode.ERR_INTERNAL,
                str(e)
            )
    
    async def _execute_command_async(self, request: CommandRequest):
        """非同步執行指令"""
        command_id = request.command.id
        trace_id = request.trace_id
        
        try:
            # 標記為執行中
            self.active_commands[command_id] = {
                "status": CommandStatus.RUNNING,
                "started_at": datetime.utcnow(),
                "request": request
            }
            
            await self._emit_event(
                trace_id,
                EventSeverity.INFO,
                EventCategory.COMMAND,
                f"指令開始執行: {command_id}",
                {"command_id": command_id}
            )
            
            # 路由到機器人
            robot_id = request.command.target.robot_id
            result = await self.robot_router.route_command(
                robot_id=robot_id,
                command_type=request.command.type,
                params=request.command.params,
                timeout_ms=request.command.timeout_ms,
                trace_id=trace_id
            )
            
            # 更新狀態
            if result.get("error"):
                status = CommandStatus.FAILED
                await self._emit_event(
                    trace_id,
                    EventSeverity.ERROR,
                    EventCategory.COMMAND,
                    f"指令執行失敗: {command_id}",
                    {"command_id": command_id, "error": result["error"]}
                )
            else:
                status = CommandStatus.SUCCEEDED
                await self._emit_event(
                    trace_id,
                    EventSeverity.INFO,
                    EventCategory.COMMAND,
                    f"指令執行成功: {command_id}",
                    {"command_id": command_id}
                )
            
            # 儲存結果
            response = CommandResponse(
                trace_id=trace_id,
                timestamp=datetime.utcnow(),
                command={"id": command_id, "status": status.value},
                result=CommandResult(
                    data=result.get("data"),
                    summary=result.get("summary", "")
                ) if not result.get("error") else None,
                error=ErrorDetail(
                    code=result["error"].get("code", ErrorCode.ERR_INTERNAL),
                    message=result["error"].get("message", ""),
                    details=result["error"].get("details")
                ) if result.get("error") else None
            )
            
            await self.context_manager.update_result(command_id, response)
            
        except asyncio.TimeoutError:
            logger.error(f"指令超時: {command_id}")
            await self._emit_event(
                trace_id,
                EventSeverity.ERROR,
                EventCategory.COMMAND,
                f"指令執行超時: {command_id}",
                {"command_id": command_id}
            )
            
        except Exception as e:
            logger.error(f"執行指令異常: {e}", exc_info=True)
            await self._emit_event(
                trace_id,
                EventSeverity.ERROR,
                EventCategory.COMMAND,
                f"指令執行異常: {str(e)}",
                {"command_id": command_id, "error": str(e)}
            )
            
        finally:
            self.active_commands.pop(command_id, None)
    
    async def get_command_status(self, command_id: str) -> Optional[Dict[str, Any]]:
        """查詢指令狀態"""
        # 先查詢執行中的指令
        if command_id in self.active_commands:
            return self.active_commands[command_id]
        
        # 查詢歷史記錄
        return await self.context_manager.get_command_status(command_id)
    
    async def cancel_command(self, command_id: str, trace_id: str) -> bool:
        """取消指令"""
        if command_id not in self.active_commands:
            return False
        
        try:
            # 標記為取消
            self.active_commands[command_id]["status"] = CommandStatus.CANCELLED
            
            await self._emit_event(
                trace_id,
                EventSeverity.INFO,
                EventCategory.COMMAND,
                f"指令已取消: {command_id}",
                {"command_id": command_id}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"取消指令失敗: {e}")
            return False
    
    async def _authenticate(self, request: CommandRequest) -> bool:
        """身份驗證"""
        if not request.auth or not request.auth.get("token"):
            return False
        
        return await self.auth_manager.verify_token(
            request.auth["token"],
            trace_id=request.trace_id
        )
    
    async def _authorize(self, request: CommandRequest) -> bool:
        """授權檢查"""
        return await self.auth_manager.check_permission(
            user_id=request.actor.id,
            action=request.command.type,
            resource=request.command.target.robot_id
        )
    
    async def _validate_command(self, request: CommandRequest) -> Optional[str]:
        """驗證指令"""
        # 基本驗證（Pydantic 已處理）
        
        # 業務規則驗證
        if request.command.timeout_ms < 100:
            return "超時時間不得小於 100ms"
        
        if request.command.timeout_ms > 600000:
            return "超時時間不得大於 600000ms (10分鐘)"
        
        return None
    
    async def _is_duplicate_command(self, command_id: str) -> bool:
        """檢查是否為重複指令"""
        return await self.context_manager.command_exists(command_id)
    
    async def _get_cached_response(self, command_id: str) -> Optional[CommandResponse]:
        """取得快取的回應"""
        return await self.context_manager.get_cached_response(command_id)
    
    async def _emit_event(
        self,
        trace_id: str,
        severity: EventSeverity,
        category: EventCategory,
        message: str,
        context: Dict[str, Any]
    ):
        """發送事件"""
        event = Event(
            trace_id=trace_id,
            severity=severity,
            category=category,
            message=message,
            context=context
        )
        await self.logging_monitor.emit_event(event)
    
    def _create_error_response(
        self,
        trace_id: str,
        command_id: str,
        error_code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> CommandResponse:
        """建立錯誤回應"""
        return CommandResponse(
            trace_id=trace_id,
            timestamp=datetime.utcnow(),
            command={"id": command_id, "status": CommandStatus.FAILED.value},
            result=None,
            error=ErrorDetail(
                code=error_code,
                message=message,
                details=details
            )
        )
