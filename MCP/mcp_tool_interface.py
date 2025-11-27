"""
MCP 工具介面
將 MCP 指令功能暴露為工具，供 LLM 提供商呼叫
"""

import logging
from typing import Any, Dict, List, Optional

from .models import CommandSpec, CommandTarget, Priority

logger = logging.getLogger(__name__)


class MCPToolInterface:
    """
    MCP 工具介面
    
    將 MCP 功能包裝為結構化的工具定義，
    可注入到支援 function calling 的 LLM 提供商
    """

    def __init__(self, command_handler=None):
        """
        初始化 MCP 工具介面
        
        Args:
            command_handler: MCP 指令處理器實例
        """
        self.command_handler = command_handler
        self.logger = logging.getLogger(__name__)

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        取得 MCP 工具定義列表（OpenAI function calling 格式）
        
        Returns:
            工具定義列表
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "robot_move_forward",
                    "description": "讓機器人向前移動指定時間",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "robot_id": {
                                "type": "string",
                                "description": "機器人 ID"
                            },
                            "duration_ms": {
                                "type": "integer",
                                "description": "持續時間（毫秒）",
                                "minimum": 100,
                                "maximum": 10000
                            }
                        },
                        "required": ["robot_id", "duration_ms"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "robot_turn",
                    "description": "讓機器人轉向（左轉或右轉）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "robot_id": {
                                "type": "string",
                                "description": "機器人 ID"
                            },
                            "direction": {
                                "type": "string",
                                "enum": ["left", "right"],
                                "description": "轉向方向"
                            },
                            "duration_ms": {
                                "type": "integer",
                                "description": "持續時間（毫秒）",
                                "minimum": 100,
                                "maximum": 10000
                            }
                        },
                        "required": ["robot_id", "direction", "duration_ms"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "robot_stop",
                    "description": "立即停止機器人所有動作",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "robot_id": {
                                "type": "string",
                                "description": "機器人 ID"
                            }
                        },
                        "required": ["robot_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "robot_basic_action",
                    "description": "讓機器人執行基礎動作（根據 Robot-Console TOOL_LIST 定義）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "robot_id": {
                                "type": "string",
                                "description": "機器人 ID"
                            },
                            "action_name": {
                                "type": "string",
                                "enum": [
                                    "back_fast", "bow", "chest", "dance_two", "dance_three",
                                    "dance_four", "dance_five", "dance_six", "dance_seven",
                                    "dance_eight", "dance_nine", "dance_ten", "go_forward",
                                    "kung_fu", "left_kick", "left_move_fast", "left_shot_fast",
                                    "left_uppercut", "push_ups", "right_kick", "right_move_fast",
                                    "right_shot_fast", "right_uppercut", "sit_ups", "squat",
                                    "squat_up", "stand", "stand_up_back", "stand_up_front",
                                    "stepping", "stop", "turn_left", "turn_right", "twist",
                                    "wave", "weightlifting", "wing_chun"
                                ],
                                "description": "基礎動作名稱（37 種可用動作）"
                            }
                        },
                        "required": ["robot_id", "action_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "robot_gesture",
                    "description": "讓機器人執行特定手勢動作",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "robot_id": {
                                "type": "string",
                                "description": "機器人 ID"
                            },
                            "gesture": {
                                "type": "string",
                                "enum": ["wave", "bow", "stand", "twist", "squat"],
                                "description": "手勢類型"
                            }
                        },
                        "required": ["robot_id", "gesture"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "robot_dance",
                    "description": "讓機器人執行跳舞動作",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "robot_id": {
                                "type": "string",
                                "description": "機器人 ID"
                            },
                            "dance_number": {
                                "type": "integer",
                                "minimum": 2,
                                "maximum": 10,
                                "description": "舞蹈編號（2-10）"
                            }
                        },
                        "required": ["robot_id", "dance_number"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "robot_combat",
                    "description": "讓機器人執行戰鬥動作",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "robot_id": {
                                "type": "string",
                                "description": "機器人 ID"
                            },
                            "move": {
                                "type": "string",
                                "enum": [
                                    "kung_fu", "wing_chun", "left_kick", "right_kick",
                                    "left_uppercut", "right_uppercut", "left_shot_fast", "right_shot_fast"
                                ],
                                "description": "戰鬥動作"
                            }
                        },
                        "required": ["robot_id", "move"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "robot_exercise",
                    "description": "讓機器人執行運動動作",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "robot_id": {
                                "type": "string",
                                "description": "機器人 ID"
                            },
                            "exercise": {
                                "type": "string",
                                "enum": ["push_ups", "sit_ups", "squat", "squat_up", "chest", "weightlifting"],
                                "description": "運動動作"
                            }
                        },
                        "required": ["robot_id", "exercise"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "robot_get_status",
                    "description": "查詢機器人當前狀態",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "robot_id": {
                                "type": "string",
                                "description": "機器人 ID"
                            }
                        },
                        "required": ["robot_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "robot_execute_sequence",
                    "description": "讓機器人執行一系列動作序列",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "robot_id": {
                                "type": "string",
                                "description": "機器人 ID"
                            },
                            "actions": {
                                "type": "array",
                                "description": "動作序列",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "action_name": {
                                            "type": "string",
                                            "description": "動作名稱"
                                        },
                                        "duration_ms": {
                                            "type": "integer",
                                            "description": "持續時間（毫秒）"
                                        }
                                    },
                                    "required": ["action_name", "duration_ms"]
                                }
                            }
                        },
                        "required": ["robot_id", "actions"]
                    }
                }
            }
        ]

    def get_ollama_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        取得 Ollama 格式的工具定義
        
        Returns:
            Ollama 工具定義列表
        """
        tools = []
        for tool_def in self.get_tool_definitions():
            func = tool_def["function"]
            tools.append({
                "type": "function",
                "function": {
                    "name": func["name"],
                    "description": func["description"],
                    "parameters": func["parameters"]
                }
            })
        return tools

    async def execute_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        執行工具呼叫
        
        Args:
            tool_name: 工具名稱
            arguments: 工具參數
            trace_id: 追蹤 ID
            
        Returns:
            執行結果
        """
        try:
            self.logger.info(f"執行工具呼叫: {tool_name}", extra={
                "tool_name": tool_name,
                "arguments": arguments,
                "trace_id": trace_id
            })

            # 根據工具名稱路由到對應的處理函數
            if tool_name == "robot_move_forward":
                return await self._handle_move_forward(arguments, trace_id)
            elif tool_name == "robot_turn":
                return await self._handle_turn(arguments, trace_id)
            elif tool_name == "robot_stop":
                return await self._handle_stop(arguments, trace_id)
            elif tool_name == "robot_basic_action":
                return await self._handle_basic_action(arguments, trace_id)
            elif tool_name == "robot_gesture":
                return await self._handle_gesture(arguments, trace_id)
            elif tool_name == "robot_dance":
                return await self._handle_dance(arguments, trace_id)
            elif tool_name == "robot_combat":
                return await self._handle_combat(arguments, trace_id)
            elif tool_name == "robot_exercise":
                return await self._handle_exercise(arguments, trace_id)
            elif tool_name == "robot_get_status":
                return await self._handle_get_status(arguments, trace_id)
            elif tool_name == "robot_execute_sequence":
                return await self._handle_execute_sequence(arguments, trace_id)
            else:
                return {
                    "success": False,
                    "error": f"未知的工具: {tool_name}"
                }

        except Exception as e:
            self.logger.error(f"工具呼叫失敗: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def _handle_move_forward(
        self,
        arguments: Dict[str, Any],
        trace_id: Optional[str]
    ) -> Dict[str, Any]:
        """處理向前移動指令"""
        robot_id = arguments["robot_id"]
        duration_ms = arguments["duration_ms"]

        if not self.command_handler:
            return {"success": False, "error": "指令處理器未初始化"}

        # 建立指令請求
        command_spec = CommandSpec(
            type="robot.action",
            target=CommandTarget(robot_id=robot_id),
            params={
                "action_name": "go_forward",
                "duration_ms": duration_ms
            },
            priority=Priority.NORMAL
        )

        # 執行指令
        response = await self.command_handler.process_command_spec(
            command_spec,
            trace_id=trace_id
        )

        return {
            "success": True,
            "command_id": response.command_id if hasattr(response, 'command_id') else None,
            "status": response.status if hasattr(response, 'status') else "accepted",
            "message": f"機器人 {robot_id} 向前移動 {duration_ms}ms"
        }

    async def _handle_turn(
        self,
        arguments: Dict[str, Any],
        trace_id: Optional[str]
    ) -> Dict[str, Any]:
        """處理轉向指令"""
        robot_id = arguments["robot_id"]
        direction = arguments["direction"]
        duration_ms = arguments["duration_ms"]

        action_name = "turn_left" if direction == "left" else "turn_right"

        if not self.command_handler:
            return {"success": False, "error": "指令處理器未初始化"}

        command_spec = CommandSpec(
            type="robot.action",
            target=CommandTarget(robot_id=robot_id),
            params={
                "action_name": action_name,
                "duration_ms": duration_ms
            },
            priority=Priority.NORMAL
        )

        response = await self.command_handler.process_command_spec(
            command_spec,
            trace_id=trace_id
        )

        return {
            "success": True,
            "command_id": response.command_id if hasattr(response, 'command_id') else None,
            "status": response.status if hasattr(response, 'status') else "accepted",
            "message": f"機器人 {robot_id} {direction}轉 {duration_ms}ms"
        }

    async def _handle_stop(
        self,
        arguments: Dict[str, Any],
        trace_id: Optional[str]
    ) -> Dict[str, Any]:
        """處理停止指令"""
        robot_id = arguments["robot_id"]

        if not self.command_handler:
            return {"success": False, "error": "指令處理器未初始化"}

        command_spec = CommandSpec(
            type="robot.action",
            target=CommandTarget(robot_id=robot_id),
            params={
                "action_name": "stop",
                "duration_ms": 0
            },
            priority=Priority.HIGH
        )

        response = await self.command_handler.process_command_spec(
            command_spec,
            trace_id=trace_id
        )

        return {
            "success": True,
            "command_id": response.command_id if hasattr(response, 'command_id') else None,
            "status": response.status if hasattr(response, 'status') else "accepted",
            "message": f"機器人 {robot_id} 已停止"
        }

    async def _handle_gesture(
        self,
        arguments: Dict[str, Any],
        trace_id: Optional[str]
    ) -> Dict[str, Any]:
        """處理手勢指令"""
        robot_id = arguments["robot_id"]
        gesture = arguments["gesture"]

        # 手勢對應到基礎動作
        gesture_map = {
            "wave": "wave",
            "bow": "bow",
            "stand": "stand",
            "twist": "twist",
            "squat": "squat"
        }

        action_name = gesture_map.get(gesture, gesture)

        if not self.command_handler:
            return {"success": False, "error": "指令處理器未初始化"}

        command_spec = CommandSpec(
            type="robot.action",
            target=CommandTarget(robot_id=robot_id),
            params={
                "action_name": action_name
            },
            priority=Priority.NORMAL
        )

        response = await self.command_handler.process_command_spec(
            command_spec,
            trace_id=trace_id
        )

        return {
            "success": True,
            "command_id": response.command_id if hasattr(response, 'command_id') else None,
            "status": response.status if hasattr(response, 'status') else "accepted",
            "message": f"機器人 {robot_id} 執行手勢: {gesture}"
        }

    async def _handle_basic_action(
        self,
        arguments: Dict[str, Any],
        trace_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        處理基礎動作指令
        支援 Robot-Console TOOL_LIST 定義的 37 種動作
        """
        robot_id = arguments["robot_id"]
        action_name = arguments["action_name"]

        # 驗證動作名稱
        valid_actions = [
            "back_fast", "bow", "chest", "dance_two", "dance_three",
            "dance_four", "dance_five", "dance_six", "dance_seven",
            "dance_eight", "dance_nine", "dance_ten", "go_forward",
            "kung_fu", "left_kick", "left_move_fast", "left_shot_fast",
            "left_uppercut", "push_ups", "right_kick", "right_move_fast",
            "right_shot_fast", "right_uppercut", "sit_ups", "squat",
            "squat_up", "stand", "stand_up_back", "stand_up_front",
            "stepping", "stop", "turn_left", "turn_right", "twist",
            "wave", "weightlifting", "wing_chun"
        ]

        if action_name not in valid_actions:
            return {
                "success": False,
                "error": f"無效的動作: {action_name}，請使用有效的基礎動作"
            }

        if not self.command_handler:
            return {"success": False, "error": "指令處理器未初始化"}

        command_spec = CommandSpec(
            type="robot.action",
            target=CommandTarget(robot_id=robot_id),
            params={
                "action_name": action_name
            },
            priority=Priority.NORMAL
        )

        response = await self.command_handler.process_command_spec(
            command_spec,
            trace_id=trace_id
        )

        return {
            "success": True,
            "command_id": response.command_id if hasattr(response, 'command_id') else None,
            "status": response.status if hasattr(response, 'status') else "accepted",
            "message": f"機器人 {robot_id} 執行基礎動作: {action_name}"
        }

    async def _handle_dance(
        self,
        arguments: Dict[str, Any],
        trace_id: Optional[str]
    ) -> Dict[str, Any]:
        """處理跳舞指令"""
        robot_id = arguments["robot_id"]
        dance_number = arguments["dance_number"]

        # 驗證舞蹈編號範圍
        if not (2 <= dance_number <= 10):
            return {
                "success": False,
                "error": f"無效的舞蹈編號: {dance_number}，有效範圍為 2-10"
            }

        dance_map = {
            2: "dance_two",
            3: "dance_three",
            4: "dance_four",
            5: "dance_five",
            6: "dance_six",
            7: "dance_seven",
            8: "dance_eight",
            9: "dance_nine",
            10: "dance_ten"
        }

        action_name = dance_map[dance_number]

        if not self.command_handler:
            return {"success": False, "error": "指令處理器未初始化"}

        command_spec = CommandSpec(
            type="robot.action",
            target=CommandTarget(robot_id=robot_id),
            params={
                "action_name": action_name
            },
            priority=Priority.NORMAL
        )

        response = await self.command_handler.process_command_spec(
            command_spec,
            trace_id=trace_id
        )

        return {
            "success": True,
            "command_id": response.command_id if hasattr(response, 'command_id') else None,
            "status": response.status if hasattr(response, 'status') else "accepted",
            "message": f"機器人 {robot_id} 執行舞蹈: {action_name}"
        }

    async def _handle_combat(
        self,
        arguments: Dict[str, Any],
        trace_id: Optional[str]
    ) -> Dict[str, Any]:
        """處理戰鬥動作指令"""
        robot_id = arguments["robot_id"]
        move = arguments["move"]

        valid_moves = [
            "kung_fu", "wing_chun", "left_kick", "right_kick",
            "left_uppercut", "right_uppercut", "left_shot_fast", "right_shot_fast"
        ]

        if move not in valid_moves:
            return {
                "success": False,
                "error": f"無效的戰鬥動作: {move}"
            }

        if not self.command_handler:
            return {"success": False, "error": "指令處理器未初始化"}

        command_spec = CommandSpec(
            type="robot.action",
            target=CommandTarget(robot_id=robot_id),
            params={
                "action_name": move
            },
            priority=Priority.NORMAL
        )

        response = await self.command_handler.process_command_spec(
            command_spec,
            trace_id=trace_id
        )

        return {
            "success": True,
            "command_id": response.command_id if hasattr(response, 'command_id') else None,
            "status": response.status if hasattr(response, 'status') else "accepted",
            "message": f"機器人 {robot_id} 執行戰鬥動作: {move}"
        }

    async def _handle_exercise(
        self,
        arguments: Dict[str, Any],
        trace_id: Optional[str]
    ) -> Dict[str, Any]:
        """處理運動動作指令"""
        robot_id = arguments["robot_id"]
        exercise = arguments["exercise"]

        valid_exercises = ["push_ups", "sit_ups", "squat", "squat_up", "chest", "weightlifting"]

        if exercise not in valid_exercises:
            return {
                "success": False,
                "error": f"無效的運動動作: {exercise}"
            }

        if not self.command_handler:
            return {"success": False, "error": "指令處理器未初始化"}

        command_spec = CommandSpec(
            type="robot.action",
            target=CommandTarget(robot_id=robot_id),
            params={
                "action_name": exercise
            },
            priority=Priority.NORMAL
        )

        response = await self.command_handler.process_command_spec(
            command_spec,
            trace_id=trace_id
        )

        return {
            "success": True,
            "command_id": response.command_id if hasattr(response, 'command_id') else None,
            "status": response.status if hasattr(response, 'status') else "accepted",
            "message": f"機器人 {robot_id} 執行運動動作: {exercise}"
        }

    async def _handle_get_status(
        self,
        arguments: Dict[str, Any],
        trace_id: Optional[str]
    ) -> Dict[str, Any]:
        """處理查詢狀態指令"""
        robot_id = arguments["robot_id"]

        # 這裡應該呼叫實際的狀態查詢邏輯
        # 目前返回模擬狀態
        return {
            "success": True,
            "robot_id": robot_id,
            "status": "online",
            "battery": 85,
            "location": {"x": 10, "y": 20},
            "message": f"機器人 {robot_id} 狀態正常"
        }

    async def _handle_execute_sequence(
        self,
        arguments: Dict[str, Any],
        trace_id: Optional[str]
    ) -> Dict[str, Any]:
        """處理動作序列指令"""
        robot_id = arguments["robot_id"]
        actions = arguments["actions"]

        if not self.command_handler:
            return {"success": False, "error": "指令處理器未初始化"}

        command_spec = CommandSpec(
            type="robot.action.sequence",
            target=CommandTarget(robot_id=robot_id),
            params={
                "actions": actions
            },
            priority=Priority.NORMAL
        )

        response = await self.command_handler.process_command_spec(
            command_spec,
            trace_id=trace_id
        )

        return {
            "success": True,
            "command_id": response.command_id if hasattr(response, 'command_id') else None,
            "status": response.status if hasattr(response, 'status') else "accepted",
            "actions_count": len(actions),
            "message": f"機器人 {robot_id} 開始執行 {len(actions)} 個動作"
        }
