"""
測試基本指令執行流程貫通

本測試套件驗證指令從提交到處理的完整流程：
1. 訊息提交到佇列
2. 佇列處理器取出訊息
3. CommandProcessor 解析並處理指令
4. 動作分派到目標（模擬的 ActionExecutor）

資料流：
WebUI/API → ServiceManager → Queue → QueueHandler → CommandProcessor → ActionDispatcher
"""

import asyncio
import sys
import os
import unittest
from typing import Any, Dict, List
from unittest.mock import MagicMock

# 添加路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from robot_service.queue import Message, MessagePriority  # noqa: E402
from robot_service.command_processor import (  # noqa: E402
    CommandProcessor,
    VALID_ACTIONS,
    create_action_executor_dispatcher,
    create_mqtt_dispatcher,
)
from robot_service.service_manager import ServiceManager  # noqa: E402


class TestCommandProcessor(unittest.TestCase):
    """測試 CommandProcessor"""

    def setUp(self):
        """設定測試環境"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.dispatched_actions = []
        self.processor = CommandProcessor(
            action_dispatcher=self._mock_dispatcher
        )

    def tearDown(self):
        """清理測試環境"""
        self.loop.close()

    def _mock_dispatcher(self, robot_id: str, actions: List[str]) -> bool:
        """模擬的動作分派函式"""
        self.dispatched_actions.append({
            "robot_id": robot_id,
            "actions": actions
        })
        return True

    def test_process_actions_array_format(self):
        """測試處理 actions 陣列格式"""
        message = Message(
            payload={
                "robot_id": "robot_1",
                "actions": ["go_forward", "turn_left", "stand"]
            },
            priority=MessagePriority.NORMAL,
            trace_id="test-trace-1"
        )

        result = self.loop.run_until_complete(self.processor.process(message))

        self.assertTrue(result)
        self.assertEqual(len(self.dispatched_actions), 1)
        self.assertEqual(self.dispatched_actions[0]["robot_id"], "robot_1")
        self.assertEqual(
            self.dispatched_actions[0]["actions"],
            ["go_forward", "turn_left", "stand"]
        )

    def test_process_single_action_format(self):
        """測試處理單一 action_name 格式"""
        message = Message(
            payload={
                "robot_id": "robot_2",
                "action_name": "bow"
            },
            priority=MessagePriority.NORMAL,
            trace_id="test-trace-2"
        )

        result = self.loop.run_until_complete(self.processor.process(message))

        self.assertTrue(result)
        self.assertEqual(len(self.dispatched_actions), 1)
        self.assertEqual(self.dispatched_actions[0]["actions"], ["bow"])

    def test_process_mcp_format(self):
        """測試處理 MCP 格式"""
        message = Message(
            payload={
                "command": {
                    "target": {"robot_id": "robot_3"},
                    "params": {"action_name": "wave"}
                }
            },
            priority=MessagePriority.NORMAL,
            trace_id="test-trace-3"
        )

        result = self.loop.run_until_complete(self.processor.process(message))

        self.assertTrue(result)
        self.assertEqual(len(self.dispatched_actions), 1)
        self.assertEqual(self.dispatched_actions[0]["robot_id"], "robot_3")
        self.assertEqual(self.dispatched_actions[0]["actions"], ["wave"])

    def test_process_advanced_command_format(self):
        """測試處理進階指令格式"""
        message = Message(
            payload={
                "robot_id": "robot_4",
                "base_commands": [
                    {"command": "go_forward"},
                    {"command": "turn_right"},
                    {"command": "push_ups"}
                ]
            },
            priority=MessagePriority.NORMAL,
            trace_id="test-trace-4"
        )

        result = self.loop.run_until_complete(self.processor.process(message))

        self.assertTrue(result)
        self.assertEqual(len(self.dispatched_actions), 1)
        self.assertEqual(
            self.dispatched_actions[0]["actions"],
            ["go_forward", "turn_right", "push_ups"]
        )

    def test_process_toolName_legacy_format(self):
        """測試處理舊版 toolName 格式"""
        message = Message(
            payload={
                "robot_id": "robot_5",
                "toolName": "kung_fu"
            },
            priority=MessagePriority.NORMAL,
            trace_id="test-trace-5"
        )

        result = self.loop.run_until_complete(self.processor.process(message))

        self.assertTrue(result)
        self.assertEqual(self.dispatched_actions[0]["actions"], ["kung_fu"])

    def test_filter_invalid_actions(self):
        """測試過濾無效動作"""
        message = Message(
            payload={
                "robot_id": "robot_6",
                "actions": ["go_forward", "invalid_action", "stand"]
            },
            priority=MessagePriority.NORMAL,
            trace_id="test-trace-6"
        )

        result = self.loop.run_until_complete(self.processor.process(message))

        self.assertTrue(result)
        # 無效動作應該被過濾
        self.assertEqual(
            self.dispatched_actions[0]["actions"],
            ["go_forward", "stand"]
        )

    def test_all_actions_invalid(self):
        """測試所有動作都無效的情況"""
        message = Message(
            payload={
                "robot_id": "robot_x",
                "actions": ["invalid_action1", "invalid_action2"]
            },
            priority=MessagePriority.NORMAL,
            trace_id="test-trace-x"
        )

        result = self.loop.run_until_complete(self.processor.process(message))

        # 應該成功處理，但不分派任何動作
        self.assertTrue(result)
        self.assertEqual(len(self.dispatched_actions), 0)

    def test_skip_wait_commands(self):
        """測試跳過 wait 指令"""
        message = Message(
            payload={
                "robot_id": "robot_7",
                "base_commands": [
                    {"command": "go_forward"},
                    {"command": "wait", "duration_ms": 1000},
                    {"command": "stand"}
                ]
            },
            priority=MessagePriority.NORMAL,
            trace_id="test-trace-7"
        )

        result = self.loop.run_until_complete(self.processor.process(message))

        self.assertTrue(result)
        # wait 應該被跳過
        self.assertEqual(
            self.dispatched_actions[0]["actions"],
            ["go_forward", "stand"]
        )

    def test_empty_payload(self):
        """測試空 payload"""
        message = Message(
            payload={},
            priority=MessagePriority.NORMAL,
            trace_id="test-trace-8"
        )

        result = self.loop.run_until_complete(self.processor.process(message))

        # 空訊息應視為成功處理
        self.assertTrue(result)
        self.assertEqual(len(self.dispatched_actions), 0)

    def test_default_robot_id(self):
        """測試預設機器人 ID"""
        message = Message(
            payload={
                "actions": ["stand"]
            },
            priority=MessagePriority.NORMAL,
            trace_id="test-trace-9"
        )

        result = self.loop.run_until_complete(self.processor.process(message))

        self.assertTrue(result)
        # 應該使用預設的 robot_id
        self.assertEqual(self.dispatched_actions[0]["robot_id"], "default")


class TestCommandProcessorWithDefaultDispatcher(unittest.TestCase):
    """測試使用預設分派器的 CommandProcessor"""

    def setUp(self):
        """設定測試環境"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        # 不提供自訂分派器，使用預設行為
        self.processor = CommandProcessor()

    def tearDown(self):
        """清理測試環境"""
        self.loop.close()

    def test_default_dispatcher_logs_actions(self):
        """測試預設分派器記錄動作"""
        message = Message(
            payload={
                "robot_id": "test_robot",
                "actions": ["go_forward", "stand"]
            },
            priority=MessagePriority.NORMAL,
            trace_id="test-trace-default"
        )

        result = self.loop.run_until_complete(self.processor.process(message))

        # 預設分派器應該始終返回 True
        self.assertTrue(result)


class TestServiceManagerIntegration(unittest.TestCase):
    """測試 ServiceManager 與 CommandProcessor 的整合"""

    def setUp(self):
        """設定測試環境"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.service_manager = ServiceManager(
            queue_max_size=100,
            max_workers=2,
            poll_interval=0.01
        )
        self.dispatched_actions = []

    def tearDown(self):
        """清理測試環境"""
        if self.service_manager._started:
            self.loop.run_until_complete(self.service_manager.stop())
        self.loop.close()

    def _mock_dispatcher(self, robot_id: str, actions: List[str]) -> bool:
        """模擬的動作分派函式"""
        self.dispatched_actions.append({
            "robot_id": robot_id,
            "actions": actions
        })
        return True

    def test_submit_and_process_command(self):
        """測試提交並處理指令"""
        # 設定動作分派器
        self.service_manager.set_action_dispatcher(self._mock_dispatcher)

        # 啟動服務
        self.loop.run_until_complete(self.service_manager.start())

        # 提交指令
        message_id = self.loop.run_until_complete(
            self.service_manager.submit_command(
                payload={
                    "robot_id": "integration_robot",
                    "actions": ["go_forward", "turn_left"]
                },
                priority=MessagePriority.NORMAL,
                trace_id="integration-test"
            )
        )

        self.assertIsNotNone(message_id)

        # 等待處理完成（給予足夠時間）
        for _ in range(50):  # 最多等待 0.5 秒
            if len(self.dispatched_actions) > 0:
                break
            self.loop.run_until_complete(asyncio.sleep(0.01))

        # 驗證動作已分派
        self.assertEqual(len(self.dispatched_actions), 1)
        self.assertEqual(
            self.dispatched_actions[0]["robot_id"],
            "integration_robot"
        )
        self.assertEqual(
            self.dispatched_actions[0]["actions"],
            ["go_forward", "turn_left"]
        )

    def test_priority_ordering(self):
        """測試優先級順序"""
        self.service_manager.set_action_dispatcher(self._mock_dispatcher)

        # 先添加訊息到佇列，但不啟動處理器
        # 這樣可以確保訊息按優先級排序

        # 先提交低優先級指令
        self.loop.run_until_complete(
            self.service_manager.submit_command(
                payload={"robot_id": "robot_low", "actions": ["stand"]},
                priority=MessagePriority.LOW,
                trace_id="low-priority"
            )
        )

        # 再提交高優先級指令
        self.loop.run_until_complete(
            self.service_manager.submit_command(
                payload={"robot_id": "robot_high", "actions": ["stop"]},
                priority=MessagePriority.HIGH,
                trace_id="high-priority"
            )
        )

        # 現在啟動處理器
        self.loop.run_until_complete(self.service_manager.start())

        # 等待處理完成
        for _ in range(50):
            if len(self.dispatched_actions) >= 2:
                break
            self.loop.run_until_complete(asyncio.sleep(0.01))

        # 驗證高優先級先處理
        # 由於佇列是優先級佇列，高優先級應該先被處理
        self.assertGreaterEqual(len(self.dispatched_actions), 2)
        self.assertEqual(
            self.dispatched_actions[0]["robot_id"],
            "robot_high"
        )


class TestDispatcherFactories(unittest.TestCase):
    """測試分派器工廠函式"""

    def test_create_action_executor_dispatcher(self):
        """測試建立 ActionExecutor 分派器"""
        mock_executor = MagicMock()
        mock_executor.add_actions_to_queue = MagicMock()

        def mock_factory(robot_id: str):
            return mock_executor

        dispatcher = create_action_executor_dispatcher(mock_factory)
        result = dispatcher("robot_1", ["go_forward", "stand"])

        self.assertTrue(result)
        mock_executor.add_actions_to_queue.assert_called_once_with(
            ["go_forward", "stand"]
        )

    def test_create_action_executor_dispatcher_no_executor(self):
        """測試當找不到執行器時的處理"""
        def mock_factory(robot_id: str):
            return None

        dispatcher = create_action_executor_dispatcher(mock_factory)
        result = dispatcher("robot_1", ["go_forward"])

        self.assertFalse(result)

    def test_create_mqtt_dispatcher(self):
        """測試建立 MQTT 分派器"""
        published_messages = []

        def mock_publish(topic: str, payload: Dict[str, Any]) -> bool:
            published_messages.append({"topic": topic, "payload": payload})
            return True

        dispatcher = create_mqtt_dispatcher(mock_publish)
        result = dispatcher("robot_1", ["go_forward", "turn_left"])

        self.assertTrue(result)
        self.assertEqual(len(published_messages), 1)
        self.assertEqual(published_messages[0]["topic"], "robot_1/topic")
        self.assertEqual(
            published_messages[0]["payload"]["actions"],
            ["go_forward", "turn_left"]
        )


class TestValidActions(unittest.TestCase):
    """測試有效動作列表"""

    def test_valid_actions_match_action_executor(self):
        """確認 VALID_ACTIONS 與 ActionExecutor 一致"""
        # 這些是 Robot-Console/action_executor.py 中定義的動作
        expected_actions = {
            "back_fast", "bow", "chest", "dance_eight", "dance_five", "dance_four",
            "dance_nine", "dance_seven", "dance_six", "dance_ten", "dance_three",
            "dance_two", "go_forward", "kung_fu", "left_kick", "left_move_fast",
            "left_shot_fast", "left_uppercut", "push_ups", "right_kick",
            "right_move_fast", "right_shot_fast", "right_uppercut", "sit_ups",
            "squat", "squat_up", "stand", "stand_up_back", "stand_up_front",
            "stepping", "stop", "turn_left", "turn_right", "twist", "wave",
            "weightlifting", "wing_chun"
        }

        self.assertEqual(VALID_ACTIONS, expected_actions)

    def test_valid_actions_count(self):
        """測試有效動作數量"""
        # 應有 37 種動作
        self.assertEqual(len(VALID_ACTIONS), 37)


if __name__ == '__main__':
    unittest.main()
