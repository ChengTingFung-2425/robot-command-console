"""
進階指令插件
處理複雜的機器人指令序列
"""

import logging
from typing import Any, Dict, List, Optional

from ...plugin_base import (
    CommandPluginBase,
    PluginCapability,
    PluginConfig,
    PluginMetadata,
    PluginType,
)

logger = logging.getLogger(__name__)


class AdvancedCommandPlugin(CommandPluginBase):
    """
    進階指令插件

    處理複雜的機器人動作序列，如：
    - patrol: 巡邏動作
    - dance: 跳舞動作
    - greet: 打招呼動作
    - complex_navigation: 複雜導航
    """

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="advanced_command",
            version="1.0.0",
            author="MCP Team",
            description="處理進階機器人指令序列",
            plugin_type=PluginType.COMMAND,
            capabilities=PluginCapability(
                supports_streaming=False,
                supports_async=True,
                supports_batch=True,
                requires_hardware=False,
                configurable=True
            ),
            dependencies=[],
            config_schema={
                "type": "object",
                "properties": {
                    "default_duration_ms": {
                        "type": "integer",
                        "description": "預設動作持續時間（毫秒）",
                        "default": 3000
                    },
                    "enable_logging": {
                        "type": "boolean",
                        "description": "是否記錄詳細日誌",
                        "default": True
                    }
                }
            }
        )

    def __init__(self, config: Optional[PluginConfig] = None):
        super().__init__(config)
        self.default_duration = 3000

    async def _on_initialize(self) -> bool:
        """初始化插件"""
        self.default_duration = self.config.config.get("default_duration_ms", 3000)
        self.logger.info(f"進階指令插件初始化，預設持續時間: {self.default_duration}ms")
        return True

    async def _on_shutdown(self) -> bool:
        """關閉插件"""
        self.logger.info("進階指令插件關閉")
        return True

    def get_supported_commands(self) -> List[str]:
        """取得支援的指令列表"""
        return [
            "patrol",
            "dance",
            "greet",
            "complex_navigation",
            "inspection",
            "presentation"
        ]

    def get_command_schema(self, command_name: str) -> Optional[Dict[str, Any]]:
        """取得指令參數 schema"""
        schemas = {
            "patrol": {
                "type": "object",
                "properties": {
                    "waypoints": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "x": {"type": "number"},
                                "y": {"type": "number"}
                            }
                        }
                    },
                    "speed": {
                        "type": "string",
                        "enum": ["slow", "normal", "fast"],
                        "default": "normal"
                    }
                },
                "required": ["waypoints"]
            },
            "dance": {
                "type": "object",
                "properties": {
                    "style": {
                        "type": "string",
                        "enum": ["simple", "complex", "freestyle"],
                        "default": "simple"
                    },
                    "duration_ms": {
                        "type": "integer",
                        "minimum": 1000,
                        "maximum": 30000,
                        "default": 10000
                    }
                }
            },
            "greet": {
                "type": "object",
                "properties": {
                    "greeting_type": {
                        "type": "string",
                        "enum": ["wave", "bow", "nod"],
                        "default": "wave"
                    },
                    "intensity": {
                        "type": "string",
                        "enum": ["gentle", "normal", "enthusiastic"],
                        "default": "normal"
                    }
                }
            }
        }
        return schemas.get(command_name)

    async def execute_command(
        self,
        command_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """執行進階指令"""

        if command_name not in self.get_supported_commands():
            return {
                "success": False,
                "error": f"不支援的指令: {command_name}"
            }

        self.logger.info(f"執行進階指令: {command_name}", extra={
            "command": command_name,
            "parameters": parameters,
            "context": context
        })

        # 根據指令類型分派
        if command_name == "patrol":
            return await self._execute_patrol(parameters, context)
        elif command_name == "dance":
            return await self._execute_dance(parameters, context)
        elif command_name == "greet":
            return await self._execute_greet(parameters, context)
        elif command_name == "complex_navigation":
            return await self._execute_complex_navigation(parameters, context)
        elif command_name == "inspection":
            return await self._execute_inspection(parameters, context)
        elif command_name == "presentation":
            return await self._execute_presentation(parameters, context)

        return {
            "success": False,
            "error": "未實作的指令"
        }

    async def _execute_patrol(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """執行巡邏指令"""
        waypoints = parameters.get("waypoints", [])
        speed = parameters.get("speed", "normal")

        # 將巡邏路徑展開為基本動作序列
        actions = []

        for i, waypoint in enumerate(waypoints):
            # 移動到路點
            actions.append({
                "action_name": "navigate_to",
                "duration_ms": 5000,
                "params": {
                    "x": waypoint.get("x"),
                    "y": waypoint.get("y"),
                    "speed": speed
                }
            })

            # 在路點停留並環顧
            actions.append({
                "action_name": "turn_360",
                "duration_ms": 4000
            })

        return {
            "success": True,
            "command": "patrol",
            "actions": actions,
            "waypoint_count": len(waypoints),
            "message": f"巡邏路徑已展開為 {len(actions)} 個動作"
        }

    async def _execute_dance(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """執行跳舞指令"""
        style = parameters.get("style", "simple")
        duration_ms = parameters.get("duration_ms", 10000)

        # 根據風格選擇動作序列
        if style == "simple":
            actions = [
                {"action_name": "wave", "duration_ms": 2000},
                {"action_name": "turn_left", "duration_ms": 1000},
                {"action_name": "turn_right", "duration_ms": 1000},
                {"action_name": "bow", "duration_ms": 2000}
            ]
        elif style == "complex":
            actions = [
                {"action_name": "wave", "duration_ms": 1500},
                {"action_name": "spin", "duration_ms": 2000},
                {"action_name": "wave", "duration_ms": 1500},
                {"action_name": "forward_back", "duration_ms": 2000},
                {"action_name": "bow", "duration_ms": 2000}
            ]
        else:  # freestyle
            actions = [
                {"action_name": "dance_two", "duration_ms": duration_ms}
            ]

        return {
            "success": True,
            "command": "dance",
            "actions": actions,
            "style": style,
            "message": f"跳舞動作已展開為 {len(actions)} 個動作"
        }

    async def _execute_greet(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """執行打招呼指令"""
        greeting_type = parameters.get("greeting_type", "wave")
        intensity = parameters.get("intensity", "normal")

        # 根據類型和強度調整動作
        duration_map = {
            "gentle": 2000,
            "normal": 3000,
            "enthusiastic": 4000
        }

        duration_ms = duration_map.get(intensity, 3000)

        actions = [
            {"action_name": greeting_type, "duration_ms": duration_ms}
        ]

        if intensity == "enthusiastic":
            # 熱情打招呼加上額外動作
            actions.append({"action_name": "wave", "duration_ms": 2000})

        return {
            "success": True,
            "command": "greet",
            "actions": actions,
            "greeting_type": greeting_type,
            "intensity": intensity,
            "message": f"打招呼動作已展開為 {len(actions)} 個動作"
        }

    async def _execute_complex_navigation(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """執行複雜導航指令"""
        # 簡化實作
        return {
            "success": True,
            "command": "complex_navigation",
            "actions": [
                {"action_name": "go_forward", "duration_ms": 3000},
                {"action_name": "turn_left", "duration_ms": 1000},
                {"action_name": "go_forward", "duration_ms": 2000}
            ],
            "message": "複雜導航已展開"
        }

    async def _execute_inspection(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """執行檢查指令"""
        return {
            "success": True,
            "command": "inspection",
            "actions": [
                {"action_name": "turn_360", "duration_ms": 4000},
                {"action_name": "scan_area", "duration_ms": 3000}
            ],
            "message": "檢查動作已展開"
        }

    async def _execute_presentation(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """執行展示指令"""
        return {
            "success": True,
            "command": "presentation",
            "actions": [
                {"action_name": "stand", "duration_ms": 2000},
                {"action_name": "wave", "duration_ms": 3000},
                {"action_name": "bow", "duration_ms": 2000}
            ],
            "message": "展示動作已展開"
        }
