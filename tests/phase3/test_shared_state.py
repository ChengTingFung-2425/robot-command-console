"""
測試服務間狀態共享機制
驗證 LocalStateStore、LocalEventBus 和 SharedStateManager 的核心功能
"""

import asyncio
import sys
import os
import unittest

# 添加 src 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from common.state_store import LocalStateStore  # noqa: E402
from common.event_bus import LocalEventBus, Event  # noqa: E402
from common.shared_state import (  # noqa: E402
    SharedStateManager,
    EventTopics,
    RobotStatus,
    QueueStatus,
)


class TestLocalStateStore(unittest.TestCase):
    """測試 LocalStateStore"""

    def setUp(self):
        """設定測試環境"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """清理測試環境"""
        self.loop.close()

    def test_set_and_get(self):
        """測試設置和取得狀態"""
        async def test():
            store = LocalStateStore()
            await store.start()

            # 設置狀態
            success = await store.set("key1", {"value": 123})
            self.assertTrue(success)

            # 取得狀態
            value = await store.get("key1")
            self.assertEqual(value, {"value": 123})

            await store.stop()

        self.loop.run_until_complete(test())

    def test_get_nonexistent(self):
        """測試取得不存在的狀態"""
        async def test():
            store = LocalStateStore()
            await store.start()

            value = await store.get("nonexistent")
            self.assertIsNone(value)

            await store.stop()

        self.loop.run_until_complete(test())

    def test_delete(self):
        """測試刪除狀態"""
        async def test():
            store = LocalStateStore()
            await store.start()

            await store.set("key1", "value1")
            self.assertTrue(await store.exists("key1"))

            deleted = await store.delete("key1")
            self.assertTrue(deleted)

            self.assertFalse(await store.exists("key1"))

            await store.stop()

        self.loop.run_until_complete(test())

    def test_ttl_expiration(self):
        """測試 TTL 過期"""
        async def test():
            store = LocalStateStore()
            await store.start()

            # 設置短 TTL
            await store.set("key1", "value1", ttl_seconds=0.1)
            self.assertTrue(await store.exists("key1"))

            # 等待過期
            await asyncio.sleep(0.2)

            # 應該已過期
            value = await store.get("key1")
            self.assertIsNone(value)

            await store.stop()

        self.loop.run_until_complete(test())

    def test_get_by_prefix(self):
        """測試前綴搜尋"""
        async def test():
            store = LocalStateStore()
            await store.start()

            await store.set("robot:1:status", {"connected": True})
            await store.set("robot:2:status", {"connected": False})
            await store.set("queue:status", {"pending": 5})

            robot_states = await store.get_by_prefix("robot:")
            self.assertEqual(len(robot_states), 2)
            self.assertIn("robot:1:status", robot_states)
            self.assertIn("robot:2:status", robot_states)

            await store.stop()

        self.loop.run_until_complete(test())

    def test_get_keys(self):
        """測試取得所有鍵"""
        async def test():
            store = LocalStateStore()
            await store.start()

            await store.set("key1", "value1")
            await store.set("key2", "value2")

            keys = await store.get_keys()
            self.assertEqual(len(keys), 2)
            self.assertIn("key1", keys)
            self.assertIn("key2", keys)

            await store.stop()

        self.loop.run_until_complete(test())

    def test_get_entry(self):
        """測試取得完整狀態條目"""
        async def test():
            store = LocalStateStore()
            await store.start()

            await store.set("key1", {"data": "test"}, metadata={"source": "test"})

            entry = await store.get_entry("key1")
            self.assertIsNotNone(entry)
            self.assertEqual(entry.key, "key1")
            self.assertEqual(entry.value, {"data": "test"})
            self.assertEqual(entry.metadata, {"source": "test"})
            self.assertIsNotNone(entry.created_at)
            self.assertIsNotNone(entry.updated_at)

            await store.stop()

        self.loop.run_until_complete(test())

    def test_clear(self):
        """測試清除所有狀態"""
        async def test():
            store = LocalStateStore()
            await store.start()

            await store.set("key1", "value1")
            await store.set("key2", "value2")

            await store.clear()

            keys = await store.get_keys()
            self.assertEqual(len(keys), 0)

            await store.stop()

        self.loop.run_until_complete(test())

    def test_health_check(self):
        """測試健康檢查"""
        async def test():
            store = LocalStateStore()
            await store.start()

            health = await store.health_check()
            self.assertEqual(health["status"], "healthy")
            self.assertTrue(health["running"])

            await store.stop()

        self.loop.run_until_complete(test())


class TestLocalEventBus(unittest.TestCase):
    """測試 LocalEventBus"""

    def setUp(self):
        """設定測試環境"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """清理測試環境"""
        self.loop.close()

    def test_subscribe_and_publish(self):
        """測試訂閱和發布"""
        async def test():
            bus = LocalEventBus()
            await bus.start()

            received_events = []

            async def handler(event: Event):
                received_events.append(event)

            sub_id = await bus.subscribe("test.topic", handler)
            self.assertIsNotNone(sub_id)

            await bus.publish("test.topic", {"data": "value"})
            await asyncio.sleep(0.01)  # 確保異步事件傳遞完成

            self.assertEqual(len(received_events), 1)
            self.assertEqual(received_events[0].topic, "test.topic")
            self.assertEqual(received_events[0].data, {"data": "value"})

            await bus.stop()

        self.loop.run_until_complete(test())

    def test_unsubscribe(self):
        """測試取消訂閱"""
        async def test():
            bus = LocalEventBus()
            await bus.start()

            received_events = []

            async def handler(event: Event):
                received_events.append(event)

            sub_id = await bus.subscribe("test.topic", handler)
            await bus.publish("test.topic", "data1")
            self.assertEqual(len(received_events), 1)

            await bus.unsubscribe(sub_id)
            await bus.publish("test.topic", "data2")
            self.assertEqual(len(received_events), 1)  # 沒有新事件

            await bus.stop()

        self.loop.run_until_complete(test())

    def test_wildcard_subscription(self):
        """測試萬用字元訂閱"""
        async def test():
            bus = LocalEventBus()
            await bus.start()

            received_events = []

            async def handler(event: Event):
                received_events.append(event)

            await bus.subscribe("robot.*", handler)

            await bus.publish("robot.connected", {"robot_id": "1"})
            await bus.publish("robot.disconnected", {"robot_id": "2"})
            await bus.publish("queue.updated", {"count": 5})  # 不匹配

            self.assertEqual(len(received_events), 2)

            await bus.stop()

        self.loop.run_until_complete(test())

    def test_multiple_subscribers(self):
        """測試多訂閱者"""
        async def test():
            bus = LocalEventBus()
            await bus.start()

            received1 = []
            received2 = []

            async def handler1(event: Event):
                received1.append(event)

            async def handler2(event: Event):
                received2.append(event)

            await bus.subscribe("test.topic", handler1)
            await bus.subscribe("test.topic", handler2)

            count = await bus.publish("test.topic", "data")
            await asyncio.sleep(0.01)  # 確保異步事件傳遞完成
            self.assertEqual(count, 2)

            self.assertEqual(len(received1), 1)
            self.assertEqual(len(received2), 1)

            await bus.stop()

        self.loop.run_until_complete(test())

    def test_multiple_pattern_subscribers(self):
        """測試多個萬用字元訂閱者"""
        async def test():
            bus = LocalEventBus()
            await bus.start()

            received1 = []
            received2 = []

            async def handler1(event: Event):
                received1.append(event)

            async def handler2(event: Event):
                received2.append(event)

            # 兩個處理器訂閱相同的萬用字元模式
            await bus.subscribe("robot.*", handler1)
            await bus.subscribe("robot.*", handler2)

            count = await bus.publish("robot.status", "data")
            await asyncio.sleep(0.01)  # 確保異步事件傳遞完成
            self.assertEqual(count, 2)

            self.assertEqual(len(received1), 1)
            self.assertEqual(len(received2), 1)

            await bus.stop()

        self.loop.run_until_complete(test())

    def test_event_history(self):
        """測試事件歷史"""
        async def test():
            bus = LocalEventBus(history_size=10, enable_history=True)
            await bus.start()

            await bus.publish("test.topic1", "data1")
            await bus.publish("test.topic2", "data2")

            history = await bus.get_history()
            self.assertEqual(len(history), 2)

            filtered = await bus.get_history(topic_filter="test.topic1")
            self.assertEqual(len(filtered), 1)

            await bus.stop()

        self.loop.run_until_complete(test())

    def test_health_check(self):
        """測試健康檢查"""
        async def test():
            bus = LocalEventBus()
            await bus.start()

            health = await bus.health_check()
            self.assertEqual(health["status"], "healthy")
            self.assertTrue(health["running"])

            await bus.stop()

        self.loop.run_until_complete(test())


class TestSharedStateManager(unittest.TestCase):
    """測試 SharedStateManager"""

    def setUp(self):
        """設定測試環境"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """清理測試環境"""
        self.loop.close()

    def test_robot_status_update(self):
        """測試機器人狀態更新"""
        async def test():
            manager = SharedStateManager()
            await manager.start()

            received_events = []

            async def handler(event: Event):
                received_events.append(event)

            await manager.subscribe(EventTopics.ROBOT_STATUS_UPDATED, handler)

            await manager.update_robot_status(
                "robot-001",
                {"connected": True, "battery_level": 85, "mode": "active"}
            )

            status = await manager.get_robot_status("robot-001")
            self.assertIsNotNone(status)
            self.assertEqual(status.robot_id, "robot-001")
            self.assertTrue(status.connected)
            self.assertEqual(status.battery_level, 85)
            self.assertEqual(status.mode, "active")

            self.assertEqual(len(received_events), 1)

            await manager.stop()

        self.loop.run_until_complete(test())

    def test_robot_connection_events(self):
        """測試機器人連線事件"""
        async def test():
            manager = SharedStateManager()
            await manager.start()

            connected_events = []
            disconnected_events = []

            async def on_connected(event: Event):
                connected_events.append(event)

            async def on_disconnected(event: Event):
                disconnected_events.append(event)

            await manager.subscribe(EventTopics.ROBOT_CONNECTED, on_connected)
            await manager.subscribe(EventTopics.ROBOT_DISCONNECTED, on_disconnected)

            # 初始連線
            await manager.update_robot_status("robot-001", {"connected": True})
            self.assertEqual(len(connected_events), 1)

            # 斷線
            await manager.update_robot_status("robot-001", {"connected": False})
            self.assertEqual(len(disconnected_events), 1)

            await manager.stop()

        self.loop.run_until_complete(test())

    def test_get_all_robots_status(self):
        """測試取得所有機器人狀態"""
        async def test():
            manager = SharedStateManager()
            await manager.start()

            await manager.update_robot_status("robot-001", {"connected": True})
            await manager.update_robot_status("robot-002", {"connected": False})

            all_status = await manager.get_all_robots_status()
            self.assertEqual(len(all_status), 2)
            self.assertIn("robot-001", all_status)
            self.assertIn("robot-002", all_status)

            await manager.stop()

        self.loop.run_until_complete(test())

    def test_queue_status_update(self):
        """測試佇列狀態更新"""
        async def test():
            manager = SharedStateManager()
            await manager.start()

            received_events = []

            async def handler(event: Event):
                received_events.append(event)

            await manager.subscribe(EventTopics.QUEUE_STATUS_UPDATED, handler)

            await manager.update_queue_status({
                "pending_count": 5,
                "processing_count": 2,
                "is_running": True,
            })

            status = await manager.get_queue_status()
            self.assertIsNotNone(status)
            self.assertEqual(status.pending_count, 5)
            self.assertEqual(status.processing_count, 2)
            self.assertTrue(status.is_running)

            self.assertEqual(len(received_events), 1)

            await manager.stop()

        self.loop.run_until_complete(test())

    def test_user_settings(self):
        """測試用戶設定"""
        async def test():
            manager = SharedStateManager()
            await manager.start()

            received_events = []

            async def handler(event: Event):
                received_events.append(event)

            await manager.subscribe(EventTopics.USER_SETTINGS_UPDATED, handler)

            await manager.update_user_settings({
                "theme": "dark",
                "language": "zh-TW",
            })

            settings = await manager.get_user_settings()
            self.assertEqual(settings["theme"], "dark")
            self.assertEqual(settings["language"], "zh-TW")

            # 測試合併更新
            await manager.update_user_settings({"notifications": True})
            settings = await manager.get_user_settings()
            self.assertEqual(settings["theme"], "dark")
            self.assertTrue(settings["notifications"])

            self.assertEqual(len(received_events), 2)

            await manager.stop()

        self.loop.run_until_complete(test())

    def test_service_status(self):
        """測試服務狀態"""
        async def test():
            manager = SharedStateManager()
            await manager.start()

            health_events = []
            started_events = []
            stopped_events = []

            async def on_health(event: Event):
                health_events.append(event)

            async def on_started(event: Event):
                started_events.append(event)

            async def on_stopped(event: Event):
                stopped_events.append(event)

            await manager.subscribe(EventTopics.SERVICE_HEALTH_CHANGED, on_health)
            await manager.subscribe(EventTopics.SERVICE_STARTED, on_started)
            await manager.subscribe(EventTopics.SERVICE_STOPPED, on_stopped)

            # 服務啟動
            await manager.update_service_status("flask", "running")
            self.assertEqual(len(started_events), 1)

            # 服務停止
            await manager.update_service_status("flask", "stopped")
            self.assertEqual(len(stopped_events), 1)

            # 健康變更事件
            self.assertEqual(len(health_events), 2)

            await manager.stop()

        self.loop.run_until_complete(test())

    def test_get_all_services_status(self):
        """測試取得所有服務狀態"""
        async def test():
            manager = SharedStateManager()
            await manager.start()

            await manager.update_service_status("flask", "running")
            await manager.update_service_status("mcp", "running")

            all_status = await manager.get_all_services_status()
            self.assertEqual(len(all_status), 2)
            self.assertIn("flask", all_status)
            self.assertIn("mcp", all_status)

            await manager.stop()

        self.loop.run_until_complete(test())

    def test_llm_provider(self):
        """測試 LLM 提供商設定"""
        async def test():
            manager = SharedStateManager()
            await manager.start()

            received_events = []

            async def handler(event: Event):
                received_events.append(event)

            await manager.subscribe(EventTopics.LLM_PROVIDER_CHANGED, handler)

            await manager.update_llm_provider("ollama", "llama2:7b")

            provider = await manager.get_llm_provider()
            model = await manager.get_llm_model()

            self.assertEqual(provider, "ollama")
            self.assertEqual(model, "llama2:7b")
            self.assertEqual(len(received_events), 1)

            await manager.stop()

        self.loop.run_until_complete(test())

    def test_command_events(self):
        """測試指令事件"""
        async def test():
            manager = SharedStateManager()
            await manager.start()

            submitted = []
            completed = []
            failed = []

            async def on_submitted(event: Event):
                submitted.append(event)

            async def on_completed(event: Event):
                completed.append(event)

            async def on_failed(event: Event):
                failed.append(event)

            await manager.subscribe(EventTopics.COMMAND_SUBMITTED, on_submitted)
            await manager.subscribe(EventTopics.COMMAND_COMPLETED, on_completed)
            await manager.subscribe(EventTopics.COMMAND_FAILED, on_failed)

            await manager.notify_command_submitted("cmd-1", "robot-001", "go_forward")
            await manager.notify_command_completed("cmd-1", "robot-001", {"success": True})
            await manager.notify_command_failed("cmd-2", "robot-001", "Connection timeout")

            self.assertEqual(len(submitted), 1)
            self.assertEqual(len(completed), 1)
            self.assertEqual(len(failed), 1)

            await manager.stop()

        self.loop.run_until_complete(test())

    def test_health_check(self):
        """測試健康檢查"""
        async def test():
            manager = SharedStateManager()
            await manager.start()

            health = await manager.health_check()
            self.assertEqual(health["status"], "healthy")
            self.assertTrue(health["running"])
            self.assertIn("state_store", health)
            self.assertIn("event_bus", health)

            await manager.stop()

        self.loop.run_until_complete(test())


class TestRobotStatusDataclass(unittest.TestCase):
    """測試 RobotStatus 資料類別"""

    def test_to_dict(self):
        """測試轉換為字典"""
        status = RobotStatus(
            robot_id="robot-001",
            connected=True,
            battery_level=85.5,
            mode="active",
        )

        data = status.to_dict()
        self.assertEqual(data["robot_id"], "robot-001")
        self.assertTrue(data["connected"])
        self.assertEqual(data["battery_level"], 85.5)
        self.assertEqual(data["mode"], "active")

    def test_from_dict(self):
        """測試從字典建立"""
        data = {
            "robot_id": "robot-001",
            "connected": True,
            "battery_level": 85.5,
            "mode": "active",
        }

        status = RobotStatus.from_dict(data)
        self.assertEqual(status.robot_id, "robot-001")
        self.assertTrue(status.connected)
        self.assertEqual(status.battery_level, 85.5)
        self.assertEqual(status.mode, "active")


class TestQueueStatusDataclass(unittest.TestCase):
    """測試 QueueStatus 資料類別"""

    def test_to_dict(self):
        """測試轉換為字典"""
        status = QueueStatus(
            pending_count=5,
            processing_count=2,
            completed_count=100,
            is_running=True,
        )

        data = status.to_dict()
        self.assertEqual(data["pending_count"], 5)
        self.assertEqual(data["processing_count"], 2)
        self.assertEqual(data["completed_count"], 100)
        self.assertTrue(data["is_running"])

    def test_from_dict(self):
        """測試從字典建立"""
        data = {
            "pending_count": 5,
            "processing_count": 2,
            "completed_count": 100,
            "is_running": True,
        }

        status = QueueStatus.from_dict(data)
        self.assertEqual(status.pending_count, 5)
        self.assertEqual(status.processing_count, 2)
        self.assertEqual(status.completed_count, 100)
        self.assertTrue(status.is_running)


if __name__ == '__main__':
    unittest.main()
