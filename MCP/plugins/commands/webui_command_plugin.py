"""
WebUI 指令插件
處理來自 WebUI 的特殊指令
"""

import logging
from typing import Any, Dict, List, Optional

from ...plugin_base import (
    CommandPluginBase,
    PluginCapability,
    PluginMetadata,
    PluginType,
)

logger = logging.getLogger(__name__)


class WebUICommandPlugin(CommandPluginBase):
    """
    WebUI 指令插件
    
    處理 WebUI 特定的指令，如：
    - emergency_stop: 緊急停止
    - video_stream_control: 視訊串流控制
    - ui_feedback: UI 回饋
    """
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="webui_command",
            version="1.0.0",
            author="MCP Team",
            description="處理 WebUI 特定指令",
            plugin_type=PluginType.INTEGRATION,
            capabilities=PluginCapability(
                supports_streaming=True,
                supports_async=True,
                supports_batch=False,
                requires_hardware=False,
                configurable=True
            ),
            dependencies=["advanced_command"],
            config_schema={
                "type": "object",
                "properties": {
                    "webui_url": {
                        "type": "string",
                        "description": "WebUI URL",
                        "default": "http://localhost:5000"
                    },
                    "enable_emergency_stop": {
                        "type": "boolean",
                        "description": "是否啟用緊急停止",
                        "default": True
                    }
                }
            }
        )
    
    async def _on_initialize(self) -> bool:
        """初始化插件"""
        self.webui_url = self.config.config.get("webui_url", "http://localhost:5000")
        self.logger.info(f"WebUI 指令插件初始化，WebUI URL: {self.webui_url}")
        return True
    
    async def _on_shutdown(self) -> bool:
        """關閉插件"""
        self.logger.info("WebUI 指令插件關閉")
        return True
    
    def get_supported_commands(self) -> List[str]:
        """取得支援的指令列表"""
        return [
            "emergency_stop",
            "video_stream_control",
            "ui_feedback",
            "robot_selection",
            "batch_command"
        ]
    
    async def execute_command(
        self,
        command_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """執行 WebUI 指令"""
        
        if command_name not in self.get_supported_commands():
            return {
                "success": False,
                "error": f"不支援的指令: {command_name}"
            }
        
        self.logger.info(f"執行 WebUI 指令: {command_name}", extra={
            "command": command_name,
            "parameters": parameters
        })
        
        if command_name == "emergency_stop":
            return await self._execute_emergency_stop(parameters, context)
        elif command_name == "video_stream_control":
            return await self._execute_video_stream_control(parameters, context)
        elif command_name == "ui_feedback":
            return await self._execute_ui_feedback(parameters, context)
        elif command_name == "robot_selection":
            return await self._execute_robot_selection(parameters, context)
        elif command_name == "batch_command":
            return await self._execute_batch_command(parameters, context)
        
        return {
            "success": False,
            "error": "未實作的指令"
        }
    
    async def _execute_emergency_stop(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """執行緊急停止"""
        robot_id = parameters.get("robot_id", "all")
        
        return {
            "success": True,
            "command": "emergency_stop",
            "robot_id": robot_id,
            "priority": "high",
            "actions": [
                {"action_name": "stop", "duration_ms": 0}
            ],
            "message": f"緊急停止指令已發送給 {robot_id}"
        }
    
    async def _execute_video_stream_control(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """執行視訊串流控制"""
        action = parameters.get("action", "start")  # start/stop/pause
        robot_id = parameters.get("robot_id")
        
        return {
            "success": True,
            "command": "video_stream_control",
            "action": action,
            "robot_id": robot_id,
            "message": f"視訊串流 {action} 已執行"
        }
    
    async def _execute_ui_feedback(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """執行 UI 回饋"""
        feedback_type = parameters.get("type", "notification")
        message = parameters.get("message", "")
        
        return {
            "success": True,
            "command": "ui_feedback",
            "type": feedback_type,
            "message": message
        }
    
    async def _execute_robot_selection(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """執行機器人選擇"""
        robot_ids = parameters.get("robot_ids", [])
        
        return {
            "success": True,
            "command": "robot_selection",
            "selected_robots": robot_ids,
            "count": len(robot_ids)
        }
    
    async def _execute_batch_command(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """執行批次指令"""
        commands = parameters.get("commands", [])
        
        return {
            "success": True,
            "command": "batch_command",
            "command_count": len(commands),
            "message": f"批次處理 {len(commands)} 個指令"
        }
