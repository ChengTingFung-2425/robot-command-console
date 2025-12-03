"""
指令處理器模組
負責將佇列訊息轉換為 Robot-Console 動作執行

此模組實現了 ServiceManager._default_processor 的真正邏輯，
將標準化的指令格式轉換為 ActionExecutor 可執行的動作。
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from .queue import Message

logger = logging.getLogger(__name__)

# 有效的基礎動作列表（與 Robot-Console/action_executor.py 同步）
# 使用 frozenset 防止意外修改
VALID_ACTIONS = frozenset({
    "back_fast", "bow", "chest", "dance_eight", "dance_five", "dance_four",
    "dance_nine", "dance_seven", "dance_six", "dance_ten", "dance_three", "dance_two",
    "go_forward", "kung_fu", "left_kick", "left_move_fast", "left_shot_fast",
    "left_uppercut", "push_ups", "right_kick", "right_move_fast", "right_shot_fast",
    "right_uppercut", "sit_ups", "squat", "squat_up", "stand", "stand_up_back",
    "stand_up_front", "stepping", "stop", "turn_left", "turn_right", "twist",
    "wave", "weightlifting", "wing_chun"
})


class CommandProcessor:
    """
    指令處理器

    負責：
    - 解析佇列訊息中的指令
    - 驗證動作有效性
    - 將動作分派到 ActionExecutor
    - 錯誤處理與日誌記錄
    """

    def __init__(
        self,
        action_dispatcher: Optional[Callable[[str, List[str]], bool]] = None,
    ):
        """
        初始化指令處理器

        Args:
            action_dispatcher: 動作分派函式，接受 (robot_id, actions) 並返回成功與否
                             如果未提供，將使用預設的日誌記錄行為
        """
        self.action_dispatcher = action_dispatcher or self._default_dispatcher

        logger.info("CommandProcessor initialized", extra={
            "has_dispatcher": action_dispatcher is not None,
            "service": "robot_service.command_processor"
        })

    async def process(self, message: Message) -> bool:
        """
        處理佇列訊息

        Args:
            message: 佇列訊息

        Returns:
            處理是否成功
        """
        try:
            payload = message.payload

            logger.info("Processing command message", extra={
                "message_id": message.id,
                "trace_id": message.trace_id,
                "payload_type": type(payload).__name__,
                "service": "robot_service.command_processor"
            })

            # 提取動作
            actions = self._extract_actions(payload)

            if not actions:
                logger.warning("No valid actions found in message", extra={
                    "message_id": message.id,
                    "trace_id": message.trace_id,
                    "service": "robot_service.command_processor"
                })
                return True  # 空訊息視為成功處理

            # 驗證動作
            invalid_actions = [a for a in actions if a not in VALID_ACTIONS and a != "wait"]
            if invalid_actions:
                logger.warning("Invalid actions found", extra={
                    "message_id": message.id,
                    "trace_id": message.trace_id,
                    "invalid_actions": invalid_actions,
                    "service": "robot_service.command_processor"
                })
                # 過濾掉無效動作
                actions = [a for a in actions if a in VALID_ACTIONS]

            # 提取目標機器人 ID
            robot_id = self._extract_robot_id(payload)

            # 分派動作
            success = self.action_dispatcher(robot_id, actions)

            logger.info("Command processed", extra={
                "message_id": message.id,
                "trace_id": message.trace_id,
                "robot_id": robot_id,
                "actions_count": len(actions),
                "success": success,
                "service": "robot_service.command_processor"
            })

            return success

        except Exception as e:
            logger.error("Error processing command", extra={
                "message_id": message.id,
                "trace_id": message.trace_id,
                "error": str(e),
                "service": "robot_service.command_processor"
            }, exc_info=True)
            return False

    def _extract_actions(self, payload: Dict[str, Any]) -> List[str]:
        """
        從 payload 中提取動作列表

        支援的格式：
        1. {"actions": ["action1", "action2", ...]}  # 新格式
        2. {"action_name": "go_forward"}  # 單一動作
        3. {"command": {"params": {"action_name": "go_forward"}}}  # MCP 格式
        4. {"base_commands": [{"command": "action1"}, ...]}  # 進階指令格式

        Args:
            payload: 訊息 payload

        Returns:
            動作名稱列表
        """
        actions = []

        # 格式 1: actions 陣列（新格式，最高優先級）
        if "actions" in payload:
            actions_data = payload["actions"]
            if isinstance(actions_data, list):
                for item in actions_data:
                    if isinstance(item, str):
                        actions.append(item)
                    elif isinstance(item, dict) and "action_name" in item:
                        actions.append(item["action_name"])
                    elif isinstance(item, dict) and "command" in item:
                        actions.append(item["command"])
                return actions

        # 格式 2: 單一 action_name
        if "action_name" in payload:
            return [payload["action_name"]]

        # 格式 3: MCP 格式
        if "command" in payload:
            command = payload["command"]
            if isinstance(command, dict):
                params = command.get("params", {})
                if "action_name" in params:
                    return [params["action_name"]]
                # 動作序列格式
                if "actions" in params:
                    return self._extract_actions({"actions": params["actions"]})

        # 格式 4: 進階指令格式
        if "base_commands" in payload:
            base_commands = payload["base_commands"]
            if isinstance(base_commands, list):
                for cmd in base_commands:
                    if isinstance(cmd, dict) and "command" in cmd:
                        cmd_name = cmd["command"]
                        # 跳過特殊指令
                        if cmd_name not in ("wait", "advanced_command"):
                            actions.append(cmd_name)
                return actions

        # 格式 5: toolName（舊格式，向後相容）
        if "toolName" in payload:
            return [payload["toolName"]]

        return actions

    def _extract_robot_id(self, payload: Dict[str, Any]) -> str:
        """
        從 payload 中提取機器人 ID

        Args:
            payload: 訊息 payload

        Returns:
            機器人 ID，如果找不到則返回預設值
        """
        # 直接指定的 robot_id
        if "robot_id" in payload:
            return payload["robot_id"]

        # MCP 格式
        if "command" in payload:
            command = payload["command"]
            if isinstance(command, dict):
                target = command.get("target", {})
                if isinstance(target, dict) and "robot_id" in target:
                    return target["robot_id"]

        # 預設值
        return "default"

    def _default_dispatcher(self, robot_id: str, actions: List[str]) -> bool:
        """
        預設的動作分派函式（僅記錄日誌）

        在實際使用中，應該透過 action_dispatcher 參數注入真正的分派邏輯。

        Args:
            robot_id: 機器人 ID
            actions: 動作列表

        Returns:
            始終返回 True
        """
        logger.info("Default dispatcher: actions recorded", extra={
            "robot_id": robot_id,
            "actions": actions,
            "actions_count": len(actions),
            "service": "robot_service.command_processor"
        })
        return True


def create_action_executor_dispatcher(
    executor_factory: Callable[[str], Any],
) -> Callable[[str, List[str]], bool]:
    """
    建立連接到 ActionExecutor 的分派函式

    Args:
        executor_factory: 工廠函式，根據 robot_id 返回 ActionExecutor 實例

    Returns:
        分派函式
    """
    def dispatcher(robot_id: str, actions: List[str]) -> bool:
        try:
            executor = executor_factory(robot_id)
            if executor is None:
                logger.warning("No executor found for robot", extra={
                    "robot_id": robot_id,
                    "service": "robot_service.command_processor"
                })
                return False

            # 使用 ActionExecutor 的 add_actions_to_queue 方法
            executor.add_actions_to_queue(actions)

            logger.info("Actions dispatched to executor", extra={
                "robot_id": robot_id,
                "actions_count": len(actions),
                "service": "robot_service.command_processor"
            })
            return True

        except Exception as e:
            logger.error("Error dispatching to executor", extra={
                "robot_id": robot_id,
                "error": str(e),
                "service": "robot_service.command_processor"
            }, exc_info=True)
            return False

    return dispatcher


def create_mqtt_dispatcher(
    mqtt_publish_func: Callable[[str, Dict[str, Any]], bool],
) -> Callable[[str, List[str]], bool]:
    """
    建立 MQTT 發布分派函式

    Args:
        mqtt_publish_func: MQTT 發布函式，接受 (topic, payload) 並返回成功與否

    Returns:
        分派函式
    """
    def dispatcher(robot_id: str, actions: List[str]) -> bool:
        try:
            topic = f"{robot_id}/topic"
            payload = {"actions": actions}

            success = mqtt_publish_func(topic, payload)

            logger.info("Actions published via MQTT", extra={
                "robot_id": robot_id,
                "topic": topic,
                "actions_count": len(actions),
                "success": success,
                "service": "robot_service.command_processor"
            })
            return success

        except Exception as e:
            logger.error("Error publishing via MQTT", extra={
                "robot_id": robot_id,
                "error": str(e),
                "service": "robot_service.command_processor"
            }, exc_info=True)
            return False

    return dispatcher
