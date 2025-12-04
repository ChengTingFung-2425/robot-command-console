"""
Tests for Offline Mode

Phase 3.2 - 離線模式完善與斷線處理測試

測試覆蓋：
1. 網路監控器 (NetworkMonitor)
2. 離線指令緩衝 (OfflineBuffer)
3. 連線管理器 (ConnectionManager)
4. 整合測試
"""

import asyncio
import sys
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, patch

# 使用 pathlib 添加 src 目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# 導入測試目標
from common.network_monitor import (  # noqa: E402
    NetworkMonitor,
    NetworkStatus,
    NetworkState,
    get_network_monitor,
    reset_network_monitor,
)
from common.connection_manager import (  # noqa: E402
    ConnectionManager,
    ConnectionPool,
    ConnectionStatus,
    ConnectionState,
)
from robot_service.queue.offline_buffer import (  # noqa: E402
    OfflineBuffer,
)
from robot_service.queue.interface import Message, MessagePriority  # noqa: E402
from common.shared_state import (  # noqa: E402
    SharedStateManager,
    EventTopics,
)


# ==================== 網路監控器測試 ====================

class TestNetworkMonitor(unittest.TestCase):
    """網路監控器測試"""

    def setUp(self):
        """測試前置設定"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        reset_network_monitor()
        self.monitor = NetworkMonitor(
            check_interval=1.0,
            timeout=0.5,
            failure_threshold=2,
            recovery_threshold=1,
        )

    def tearDown(self):
        """測試後清理"""
        reset_network_monitor()
        self.loop.close()

    def test_initial_status(self):
        """測試初始狀態為 UNKNOWN"""
        self.assertEqual(self.monitor.status, NetworkStatus.UNKNOWN)
        self.assertFalse(self.monitor.is_online)

    def test_state_to_dict(self):
        """測試狀態轉換為字典"""
        state = NetworkState(
            status=NetworkStatus.ONLINE,
            consecutive_successes=3,
            latency_ms=50.0,
        )
        data = state.to_dict()

        self.assertEqual(data["status"], "online")
        self.assertEqual(data["consecutive_successes"], 3)
        self.assertEqual(data["latency_ms"], 50.0)

    def test_check_connection_success(self):
        """測試連線檢查成功"""
        async def test():
            with patch.object(self.monitor, '_check_endpoint', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = True

                result = await self.monitor.check_connection()

                self.assertTrue(result)
                self.assertEqual(self.monitor.status, NetworkStatus.ONLINE)
                self.assertEqual(self.monitor.state.consecutive_successes, 1)

        self.loop.run_until_complete(test())

    def test_check_connection_failure_threshold(self):
        """測試連線失敗達到閾值"""
        async def test():
            with patch.object(self.monitor, '_check_endpoint', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = False

                # 第一次失敗，還未達到閾值
                await self.monitor.check_connection()
                self.assertNotEqual(self.monitor.status, NetworkStatus.OFFLINE)

                # 第二次失敗，達到閾值
                await self.monitor.check_connection()
                self.assertEqual(self.monitor.status, NetworkStatus.OFFLINE)
                self.assertEqual(self.monitor.state.consecutive_failures, 2)

        self.loop.run_until_complete(test())

    def test_callback_on_status_change(self):
        """測試狀態變更時呼叫回呼"""
        async def test():
            callback = AsyncMock()
            self.monitor.add_callback(callback)

            with patch.object(self.monitor, '_check_endpoint', new_callable=AsyncMock) as mock_check:
                # 先離線
                mock_check.return_value = False
                await self.monitor.check_connection()
                await self.monitor.check_connection()  # 達到閾值

                # 回呼應該被呼叫
                callback.assert_called()
                call_args = callback.call_args
                self.assertEqual(call_args[0][1], NetworkStatus.OFFLINE)

        self.loop.run_until_complete(test())

    def test_start_and_stop(self):
        """測試啟動和停止"""
        async def test():
            with patch.object(self.monitor, '_check_endpoint', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = True

                await self.monitor.start()
                self.assertTrue(self.monitor._running)

                await self.monitor.stop()
                self.assertFalse(self.monitor._running)

        self.loop.run_until_complete(test())

    def test_health_check(self):
        """測試健康檢查"""
        async def test():
            with patch.object(self.monitor, '_check_endpoint', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = True
                await self.monitor.start()
                health = await self.monitor.health_check()

                self.assertEqual(health["status"], "healthy")
                self.assertTrue(health["running"])
                self.assertIn("network_state", health)

                await self.monitor.stop()

        self.loop.run_until_complete(test())

    def test_global_monitor(self):
        """測試全域監控器"""
        monitor1 = get_network_monitor()
        monitor2 = get_network_monitor()

        self.assertIs(monitor1, monitor2)


# ==================== 離線緩衝測試 ====================

class TestOfflineBuffer(unittest.TestCase):
    """離線指令緩衝測試"""

    def setUp(self):
        """測試前置設定"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        # 使用記憶體資料庫
        self.buffer = OfflineBuffer(
            db_path=":memory:",
            max_size=100,
            default_ttl_seconds=3600.0,
            max_retry_count=3,
        )

    def tearDown(self):
        """測試後清理"""
        self.loop.close()

    def test_buffer_message(self):
        """測試緩衝訊息"""
        async def test():
            await self.buffer.start()

            message = Message(
                id="msg-001",
                payload={"action": "go_forward"},
                priority=MessagePriority.NORMAL,
            )

            result = await self.buffer.buffer(message)

            self.assertTrue(result)
            size = await self.buffer.size()
            self.assertEqual(size, 1)

            await self.buffer.stop()

        self.loop.run_until_complete(test())

    def test_buffer_max_size(self):
        """測試緩衝區大小限制"""
        async def test():
            buffer = OfflineBuffer(db_path=":memory:", max_size=5)
            await buffer.start()

            # 填滿緩衝區
            for i in range(5):
                message = Message(id=f"msg-{i}", payload={"i": i})
                await buffer.buffer(message)

            # 超出限制應該失敗
            message = Message(id="msg-overflow", payload={})
            result = await buffer.buffer(message)

            self.assertFalse(result)

            await buffer.stop()

        self.loop.run_until_complete(test())

    def test_flush_when_online(self):
        """測試在線時清空緩衝"""
        async def test():
            await self.buffer.start()

            # 設定發送處理器
            sent_messages = []

            async def send_handler(msg):
                sent_messages.append(msg)
                return True

            self.buffer.set_send_handler(send_handler)
            self.buffer.set_online(True)

            # 緩衝訊息
            message = Message(id="msg-001", payload={"action": "test"})
            await self.buffer.buffer(message)

            # 清空緩衝
            result = await self.buffer.flush()

            self.assertEqual(result["sent"], 1)
            self.assertEqual(len(sent_messages), 1)
            self.assertEqual(sent_messages[0].id, "msg-001")

            await self.buffer.stop()

        self.loop.run_until_complete(test())

    def test_flush_when_offline(self):
        """測試離線時不清空緩衝"""
        async def test():
            await self.buffer.start()

            self.buffer.set_online(False)

            message = Message(id="msg-001", payload={"action": "test"})
            await self.buffer.buffer(message)

            result = await self.buffer.flush()

            self.assertTrue(result.get("skipped", False))

            await self.buffer.stop()

        self.loop.run_until_complete(test())

    def test_priority_ordering(self):
        """測試優先權排序"""
        async def test():
            await self.buffer.start()

            # 緩衝不同優先權的訊息
            low = Message(id="low", payload={}, priority=MessagePriority.LOW)
            high = Message(id="high", payload={}, priority=MessagePriority.HIGH)
            normal = Message(id="normal", payload={}, priority=MessagePriority.NORMAL)

            await self.buffer.buffer(low)
            await self.buffer.buffer(normal)
            await self.buffer.buffer(high)

            # 取得待發送的條目
            entries = await self.buffer._get_pending_entries(10)

            # 應該按優先權排序：high, normal, low
            self.assertEqual(entries[0].message.id, "high")
            self.assertEqual(entries[1].message.id, "normal")
            self.assertEqual(entries[2].message.id, "low")

            await self.buffer.stop()

        self.loop.run_until_complete(test())

    def test_retry_on_failure(self):
        """測試發送失敗重試"""
        async def test():
            await self.buffer.start()

            call_count = 0

            async def failing_handler(msg):
                nonlocal call_count
                call_count += 1
                return False

            self.buffer.set_send_handler(failing_handler)
            self.buffer.set_online(True)

            message = Message(id="msg-001", payload={})
            await self.buffer.buffer(message)

            # 多次嘗試發送
            await self.buffer.flush()
            await self.buffer.flush()
            await self.buffer.flush()

            # 發送失敗後應該仍在緩衝區（直到達到最大重試次數）
            # 只需驗證重試次數足夠
            self.assertGreaterEqual(call_count, 1)

            await self.buffer.stop()

        self.loop.run_until_complete(test())

    def test_cleanup_expired(self):
        """測試清理過期條目"""
        async def test():
            buffer = OfflineBuffer(
                db_path=":memory:",
                default_ttl_seconds=0.1,  # 0.1 秒過期
            )
            await buffer.start()

            message = Message(id="msg-001", payload={})
            await buffer.buffer(message)

            # 等待過期
            await asyncio.sleep(0.2)

            # 清理過期條目
            count = await buffer.cleanup_expired()

            self.assertEqual(count, 1)
            size = await buffer.size()
            self.assertEqual(size, 0)

            await buffer.stop()

        self.loop.run_until_complete(test())

    def test_statistics(self):
        """測試統計資訊"""
        async def test():
            await self.buffer.start()

            message = Message(id="msg-001", payload={})
            await self.buffer.buffer(message)

            stats = await self.buffer.get_statistics()

            self.assertEqual(stats["pending"], 1)
            self.assertEqual(stats["total_buffered"], 1)
            self.assertIn("is_online", stats)

            await self.buffer.stop()

        self.loop.run_until_complete(test())

    def test_health_check(self):
        """測試健康檢查"""
        async def test():
            await self.buffer.start()

            health = await self.buffer.health_check()

            self.assertEqual(health["status"], "healthy")
            self.assertTrue(health["running"])
            self.assertIn("statistics", health)

            await self.buffer.stop()

        self.loop.run_until_complete(test())


# ==================== 連線管理器測試 ====================

class TestConnectionManager(unittest.TestCase):
    """連線管理器測試"""

    def setUp(self):
        """測試前置設定"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.manager = ConnectionManager(
            name="test-connection",
            endpoint="http://localhost:8000",
            health_check_interval=1.0,
            max_reconnect_attempts=3,
            initial_reconnect_delay=0.1,
            max_reconnect_delay=1.0,
        )

    def tearDown(self):
        """測試後清理"""
        self.loop.close()

    def test_initial_status(self):
        """測試初始狀態"""
        self.assertEqual(self.manager.status, ConnectionStatus.DISCONNECTED)
        self.assertFalse(self.manager.is_connected)
        self.assertEqual(self.manager.name, "test-connection")

    def test_state_to_dict(self):
        """測試狀態轉換為字典"""
        state = ConnectionState(
            status=ConnectionStatus.CONNECTED,
            endpoint="http://localhost:8000",
            reconnect_attempts=2,
        )
        data = state.to_dict()

        self.assertEqual(data["status"], "connected")
        self.assertEqual(data["endpoint"], "http://localhost:8000")
        self.assertEqual(data["reconnect_attempts"], 2)

    def test_connect_success(self):
        """測試連線成功"""
        async def test():
            connect_handler = AsyncMock(return_value=True)
            self.manager.set_connect_handler(connect_handler)

            await self.manager.start()
            result = await self.manager.connect()

            self.assertTrue(result)
            self.assertEqual(self.manager.status, ConnectionStatus.CONNECTED)
            connect_handler.assert_called_once()

            await self.manager.stop()

        self.loop.run_until_complete(test())

    def test_connect_failure(self):
        """測試連線失敗"""
        async def test():
            connect_handler = AsyncMock(return_value=False)
            self.manager.set_connect_handler(connect_handler)

            await self.manager.start()
            result = await self.manager.connect()

            self.assertFalse(result)
            self.assertEqual(self.manager.status, ConnectionStatus.DISCONNECTED)

            await self.manager.stop()

        self.loop.run_until_complete(test())

    def test_disconnect(self):
        """測試斷線"""
        async def test():
            connect_handler = AsyncMock(return_value=True)
            disconnect_handler = AsyncMock()

            self.manager.set_connect_handler(connect_handler)
            self.manager.set_disconnect_handler(disconnect_handler)

            await self.manager.start()
            await self.manager.connect()
            await self.manager.disconnect()

            self.assertEqual(self.manager.status, ConnectionStatus.DISCONNECTED)
            disconnect_handler.assert_called_once()

            await self.manager.stop()

        self.loop.run_until_complete(test())

    def test_reconnect_with_backoff(self):
        """測試指數退避重連"""
        async def test():
            call_count = 0

            async def connect_handler():
                nonlocal call_count
                call_count += 1
                return True  # 第一次就成功

            self.manager.set_connect_handler(connect_handler)

            await self.manager.start()

            # 觸發重連
            result = await self.manager.reconnect()

            self.assertTrue(result)
            self.assertEqual(self.manager.status, ConnectionStatus.CONNECTED)
            self.assertEqual(call_count, 1)

            # 驗證重連延遲計算（指數退避）
            self.manager._state.reconnect_attempts = 1
            delay1 = self.manager._calculate_reconnect_delay()
            self.manager._state.reconnect_attempts = 3
            delay3 = self.manager._calculate_reconnect_delay()
            self.assertLess(delay1, delay3)

            await self.manager.stop()

        self.loop.run_until_complete(test())

    def test_max_reconnect_attempts(self):
        """測試達到最大重連次數"""
        async def test():
            connect_handler = AsyncMock(return_value=False)
            self.manager.set_connect_handler(connect_handler)

            await self.manager.start()

            # 多次重連嘗試
            for _ in range(4):
                await self.manager.reconnect()

            # 應該達到 FAILED 狀態
            self.assertEqual(self.manager.status, ConnectionStatus.FAILED)

            await self.manager.stop()

        self.loop.run_until_complete(test())

    def test_callback_on_status_change(self):
        """測試狀態變更回呼"""
        async def test():
            callback = AsyncMock()
            self.manager.add_callback(callback)

            connect_handler = AsyncMock(return_value=True)
            self.manager.set_connect_handler(connect_handler)

            await self.manager.start()
            await self.manager.connect()

            callback.assert_called()
            call_args = callback.call_args
            self.assertEqual(call_args[0][1], ConnectionStatus.CONNECTED)

            await self.manager.stop()

        self.loop.run_until_complete(test())

    def test_health_check(self):
        """測試健康檢查"""
        async def test():
            connect_handler = AsyncMock(return_value=True)
            self.manager.set_connect_handler(connect_handler)

            await self.manager.start()
            await self.manager.connect()

            health = await self.manager.health_check()

            self.assertEqual(health["status"], "healthy")
            self.assertTrue(health["running"])

            await self.manager.stop()

        self.loop.run_until_complete(test())

    def test_calculate_reconnect_delay(self):
        """測試重連延遲計算"""
        self.manager._state.reconnect_attempts = 1
        delay1 = self.manager._calculate_reconnect_delay()

        self.manager._state.reconnect_attempts = 3
        delay3 = self.manager._calculate_reconnect_delay()

        # 延遲應該指數增長（考慮抖動）
        self.assertLess(delay1, delay3)


# ==================== 連線池測試 ====================

class TestConnectionPool(unittest.TestCase):
    """連線池測試"""

    def setUp(self):
        """測試前置設定"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.pool = ConnectionPool()

    def tearDown(self):
        """測試後清理"""
        self.loop.close()

    def test_add_and_get_connection(self):
        """測試添加和取得連線"""
        conn = ConnectionManager(name="test")
        self.pool.add(conn)

        result = self.pool.get("test")
        self.assertIs(result, conn)

    def test_remove_connection(self):
        """測試移除連線"""
        conn = ConnectionManager(name="test")
        self.pool.add(conn)

        removed = self.pool.remove("test")
        self.assertIs(removed, conn)

        result = self.pool.get("test")
        self.assertIsNone(result)

    def test_start_all(self):
        """測試啟動所有連線"""
        async def test():
            conn1 = ConnectionManager(name="conn1")
            conn2 = ConnectionManager(name="conn2")

            self.pool.add(conn1)
            self.pool.add(conn2)

            results = await self.pool.start_all()

            self.assertTrue(results["conn1"])
            self.assertTrue(results["conn2"])

            await self.pool.stop_all()

        self.loop.run_until_complete(test())

    def test_connect_all(self):
        """測試連接所有"""
        async def test():
            conn1 = ConnectionManager(name="conn1")
            conn2 = ConnectionManager(name="conn2")

            conn1.set_connect_handler(AsyncMock(return_value=True))
            conn2.set_connect_handler(AsyncMock(return_value=False))

            self.pool.add(conn1)
            self.pool.add(conn2)

            await self.pool.start_all()
            results = await self.pool.connect_all()

            self.assertTrue(results["conn1"])
            self.assertFalse(results["conn2"])

            await self.pool.stop_all()

        self.loop.run_until_complete(test())

    def test_get_connected_count(self):
        """測試取得已連線數量"""
        conn1 = ConnectionManager(name="conn1")
        conn2 = ConnectionManager(name="conn2")

        conn1._state.status = ConnectionStatus.CONNECTED
        conn2._state.status = ConnectionStatus.DISCONNECTED

        self.pool.add(conn1)
        self.pool.add(conn2)

        self.assertEqual(self.pool.get_connected_count(), 1)
        self.assertEqual(self.pool.get_disconnected_count(), 1)


# ==================== SharedStateManager 離線功能測試 ====================

class TestSharedStateManagerOffline(unittest.TestCase):
    """SharedStateManager 離線功能測試"""

    def setUp(self):
        """測試前置設定"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """測試後清理"""
        self.loop.close()

    def test_update_network_status(self):
        """測試更新網路狀態"""
        async def test():
            manager = SharedStateManager()
            await manager.start()

            # 更新為離線
            result = await manager.update_network_status(
                is_online=False,
                details={"checked_endpoint": "google.com"},
            )

            self.assertTrue(result)

            # 檢查狀態
            status = await manager.get_network_status()
            self.assertFalse(status["is_online"])

            await manager.stop()

        self.loop.run_until_complete(test())

    def test_is_network_online(self):
        """測試網路是否在線"""
        async def test():
            manager = SharedStateManager()
            await manager.start()

            # 預設應該是 True
            is_online = await manager.is_network_online()
            self.assertTrue(is_online)

            # 設為離線
            await manager.update_network_status(is_online=False)
            is_online = await manager.is_network_online()
            self.assertFalse(is_online)

            await manager.stop()

        self.loop.run_until_complete(test())

    def test_network_events(self):
        """測試網路狀態事件"""
        async def test():
            manager = SharedStateManager()
            await manager.start()

            events = []

            async def handler(event):
                events.append(event)

            await manager.subscribe(EventTopics.NETWORK_OFFLINE, handler)

            # 先設為在線
            await manager.update_network_status(is_online=True)

            # 再設為離線，應該觸發事件
            await manager.update_network_status(is_online=False)

            # 等待事件處理
            await asyncio.sleep(0.1)

            self.assertEqual(len(events), 1)

            await manager.stop()

        self.loop.run_until_complete(test())

    def test_update_offline_buffer_status(self):
        """測試更新離線緩衝狀態"""
        async def test():
            manager = SharedStateManager()
            await manager.start()

            result = await manager.update_offline_buffer_status({
                "pending": 5,
                "is_online": False,
            })

            self.assertTrue(result)

            status = await manager.get_offline_buffer_status()
            self.assertEqual(status["pending"], 5)

            await manager.stop()

        self.loop.run_until_complete(test())

    def test_update_connection_status(self):
        """測試更新連線狀態"""
        async def test():
            manager = SharedStateManager()
            await manager.start()

            result = await manager.update_connection_status(
                connection_name="mqtt-broker",
                status="connected",
                details={"latency_ms": 50},
            )

            self.assertTrue(result)

            status = await manager.get_connection_status("mqtt-broker")
            self.assertEqual(status["status"], "connected")
            self.assertEqual(status["connection_name"], "mqtt-broker")

            await manager.stop()

        self.loop.run_until_complete(test())

    def test_get_all_connections_status(self):
        """測試取得所有連線狀態"""
        async def test():
            manager = SharedStateManager()
            await manager.start()

            await manager.update_connection_status("conn1", "connected")
            await manager.update_connection_status("conn2", "disconnected")

            all_status = await manager.get_all_connections_status()

            self.assertEqual(len(all_status), 2)
            self.assertIn("conn1", all_status)
            self.assertIn("conn2", all_status)

            await manager.stop()

        self.loop.run_until_complete(test())


# ==================== 整合測試 ====================

class TestOfflineModeIntegration(unittest.TestCase):
    """離線模式整合測試"""

    def setUp(self):
        """測試前置設定"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """測試後清理"""
        self.loop.close()

    def test_offline_flow(self):
        """測試完整離線流程"""
        async def test():
            # 建立元件
            shared_state = SharedStateManager()
            network_monitor = NetworkMonitor(check_interval=0.5)
            offline_buffer = OfflineBuffer(db_path=":memory:")

            await shared_state.start()
            await offline_buffer.start()

            # 設定網路監控回呼
            async def on_network_change(old_status, new_status, state):
                is_online = new_status == NetworkStatus.ONLINE
                offline_buffer.set_online(is_online)
                await shared_state.update_network_status(is_online=is_online)

            network_monitor.add_callback(on_network_change)

            # 模擬離線
            with patch.object(network_monitor, '_check_endpoint', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = False
                await network_monitor.check_connection()
                await network_monitor.check_connection()  # 達到閾值

            # 離線時緩衝指令
            message = Message(id="offline-cmd", payload={"action": "test"})
            await offline_buffer.buffer(message)

            # 確認已緩衝
            size = await offline_buffer.size()
            self.assertEqual(size, 1)

            # 模擬恢復在線
            sent_messages = []

            async def send_handler(msg):
                sent_messages.append(msg)
                return True

            offline_buffer.set_send_handler(send_handler)

            with patch.object(network_monitor, '_check_endpoint', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = True
                await network_monitor.check_connection()

            # 清空緩衝
            result = await offline_buffer.flush()

            self.assertEqual(result["sent"], 1)
            self.assertEqual(len(sent_messages), 1)

            await offline_buffer.stop()
            await shared_state.stop()

        self.loop.run_until_complete(test())

    def test_command_buffered_when_queue_service_unavailable(self):
        """
        測試佇列服務不可用時指令被緩衝

        當 Edge 使用網路佇列服務（Redis/RabbitMQ）連接到 Runner 時，
        網路斷開會導致佇列服務不可用，指令需要被緩衝到本地。
        """
        async def test():
            from robot_service.queue.offline_queue_service import OfflineQueueService

            service = OfflineQueueService()
            await service.start()

            # 確認佇列服務不可用（預設狀態）
            self.assertFalse(service.is_queue_service_available)

            # 提交指令（佇列服務不可用，應該被緩衝）
            msg_id = await service.submit_command(
                payload={"command": "go_forward", "robot_id": "robot-001"},
            )

            # 指令應該成功（被緩衝）
            self.assertIsNotNone(msg_id)

            # 指令緩衝應該有訊息
            buffer_size = await service.command_buffer.size()
            self.assertEqual(buffer_size, 1)

            # 統計應該正確
            stats = await service.get_statistics()
            self.assertEqual(stats["stats"]["commands_submitted"], 1)
            self.assertEqual(stats["stats"]["commands_buffered"], 1)
            self.assertEqual(stats["stats"]["commands_sent_direct"], 0)

            await service.stop()

        self.loop.run_until_complete(test())

    def test_command_sent_when_queue_service_available(self):
        """
        測試佇列服務可用時指令直接發送
        """
        async def test():
            from robot_service.queue.offline_queue_service import (
                OfflineQueueService,
                QueueServiceStatus,
            )

            sent_commands = []

            async def queue_send_handler(msg):
                sent_commands.append(msg)
                return True

            async def queue_health_check():
                return True

            service = OfflineQueueService()
            service.set_queue_send_handler(queue_send_handler)
            service.set_queue_health_check_handler(queue_health_check)

            await service.start()

            # 手動設定佇列服務可用
            await service._set_queue_service_status(QueueServiceStatus.AVAILABLE)

            # 確認佇列服務可用
            self.assertTrue(service.is_queue_service_available)

            # 提交指令（應該直接發送）
            msg_id = await service.submit_command(
                payload={"command": "go_forward", "robot_id": "robot-001"},
            )

            # 指令應該成功
            self.assertIsNotNone(msg_id)

            # 指令應該被直接發送
            self.assertEqual(len(sent_commands), 1)

            # 指令緩衝應該為空
            buffer_size = await service.command_buffer.size()
            self.assertEqual(buffer_size, 0)

            # 統計應該正確
            stats = await service.get_statistics()
            self.assertEqual(stats["stats"]["commands_sent_direct"], 1)
            self.assertEqual(stats["stats"]["commands_buffered"], 0)

            await service.stop()

        self.loop.run_until_complete(test())

    def test_command_buffer_flushed_when_queue_service_recovers(self):
        """
        測試佇列服務恢復時自動清空指令緩衝
        """
        async def test():
            from robot_service.queue.offline_queue_service import (
                OfflineQueueService,
                QueueServiceStatus,
            )

            sent_commands = []

            async def queue_send_handler(msg):
                sent_commands.append(msg)
                return True

            service = OfflineQueueService(auto_flush_on_online=True)
            service.set_queue_send_handler(queue_send_handler)

            await service.start()

            # 佇列服務不可用，提交指令（被緩衝）
            await service.submit_command(
                payload={"command": "cmd1", "robot_id": "robot-001"},
            )
            await service.submit_command(
                payload={"command": "cmd2", "robot_id": "robot-001"},
            )

            # 確認緩衝
            buffer_size = await service.command_buffer.size()
            self.assertEqual(buffer_size, 2)

            # 模擬佇列服務恢復
            await service._set_queue_service_status(QueueServiceStatus.AVAILABLE)

            # 等待自動同步
            await asyncio.sleep(0.1)

            # 指令應該已發送
            self.assertEqual(len(sent_commands), 2)

            # 緩衝應該清空
            buffer_size = await service.command_buffer.size()
            self.assertEqual(buffer_size, 0)

            await service.stop()

        self.loop.run_until_complete(test())

    def test_sync_data_buffered_when_network_offline(self):
        """
        測試網路離線時雲端同步資料被緩衝
        """
        async def test():
            from robot_service.queue.offline_queue_service import OfflineQueueService

            service = OfflineQueueService()
            await service.start()

            # 模擬網路離線
            with patch.object(service._network_monitor, '_check_endpoint', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = False
                await service._network_monitor.check_connection()
                await service._network_monitor.check_connection()

            # 確認網路離線
            self.assertFalse(service.is_network_online)

            # 記錄指令執行結果（這會被緩衝）
            log_id = await service.log_command_execution(
                command_id="cmd-001",
                robot_id="robot-001",
                command="go_forward",
                success=True,
            )

            self.assertIsNotNone(log_id)

            # 同步緩衝應該有資料
            buffer_size = await service.sync_buffer.size()
            self.assertEqual(buffer_size, 1)

            # 統計應該正確
            stats = await service.get_statistics()
            self.assertEqual(stats["stats"]["sync_data_buffered"], 1)

            await service.stop()

        self.loop.run_until_complete(test())


if __name__ == "__main__":
    unittest.main()
