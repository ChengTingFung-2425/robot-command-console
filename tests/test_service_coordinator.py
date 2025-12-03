"""
測試 Service Coordinator
驗證服務協調器的核心功能
"""

import asyncio
import sys
import os
import unittest
from typing import Any, Dict, Optional

# 添加 src 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from robot_service.service_coordinator import (  # noqa: E402
    ServiceCoordinator,
    ServiceBase,
    QueueService,
)
from common.service_types import ServiceStatus, ServiceConfig  # noqa: E402


class MockService(ServiceBase):
    """模擬服務用於測試"""

    def __init__(self, name: str = "mock_service"):
        self._name = name
        self._running = False
        self._health_result = {"status": "healthy"}
        self._start_success = True
        self._stop_success = True

    @property
    def name(self) -> str:
        return self._name

    async def start(self) -> bool:
        if self._start_success:
            self._running = True
        return self._start_success

    async def stop(self, timeout: Optional[float] = None) -> bool:
        if self._stop_success:
            self._running = False
        return self._stop_success

    async def health_check(self) -> Dict[str, Any]:
        return self._health_result

    @property
    def is_running(self) -> bool:
        return self._running

    def set_health_result(self, result: Dict[str, Any]) -> None:
        """設定健康檢查結果"""
        self._health_result = result

    def set_start_success(self, success: bool) -> None:
        """設定啟動是否成功"""
        self._start_success = success

    def set_stop_success(self, success: bool) -> None:
        """設定停止是否成功"""
        self._stop_success = success


class TestServiceStatus(unittest.TestCase):
    """測試 ServiceStatus 列舉"""

    def test_status_values(self):
        """測試狀態值"""
        self.assertEqual(ServiceStatus.STOPPED.value, "stopped")
        self.assertEqual(ServiceStatus.STARTING.value, "starting")
        self.assertEqual(ServiceStatus.RUNNING.value, "running")
        self.assertEqual(ServiceStatus.HEALTHY.value, "healthy")
        self.assertEqual(ServiceStatus.UNHEALTHY.value, "unhealthy")
        self.assertEqual(ServiceStatus.STOPPING.value, "stopping")
        self.assertEqual(ServiceStatus.ERROR.value, "error")


class TestServiceConfig(unittest.TestCase):
    """測試 ServiceConfig"""

    def test_default_config(self):
        """測試預設配置"""
        config = ServiceConfig(name="test", service_type="test_type")

        self.assertEqual(config.name, "test")
        self.assertEqual(config.service_type, "test_type")
        self.assertTrue(config.enabled)
        self.assertTrue(config.auto_restart)
        self.assertEqual(config.max_restart_attempts, 3)
        self.assertEqual(config.restart_delay_seconds, 2.0)
        self.assertEqual(config.health_check_interval_seconds, 30.0)
        self.assertEqual(config.startup_timeout_seconds, 5.0)
        self.assertEqual(config.warmup_seconds, 2.0)


class TestServiceCoordinator(unittest.TestCase):
    """測試 ServiceCoordinator"""

    def setUp(self):
        """設定測試環境"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """清理測試環境"""
        self.loop.close()

    def test_register_service(self):
        """測試註冊服務"""
        coordinator = ServiceCoordinator()
        service = MockService("test_service")

        coordinator.register_service(service)

        self.assertIn("test_service", coordinator._services)
        self.assertIn("test_service", coordinator._states)

    def test_register_service_with_config(self):
        """測試使用配置註冊服務"""
        coordinator = ServiceCoordinator()
        service = MockService("test_service")
        config = ServiceConfig(
            name="test_service",
            service_type="MockService",
            enabled=False,
            auto_restart=False,
        )

        coordinator.register_service(service, config)

        state = coordinator._states["test_service"]
        self.assertFalse(state.config.enabled)
        self.assertFalse(state.config.auto_restart)

    def test_register_running_service_raises_error(self):
        """測試替換正在運行的服務時拋出錯誤"""
        async def test():
            coordinator = ServiceCoordinator()
            service1 = MockService("test_service")
            service2 = MockService("test_service")

            coordinator.register_service(service1)
            await coordinator.start_service("test_service")

            with self.assertRaises(ValueError) as context:
                coordinator.register_service(service2)

            self.assertIn("Cannot replace running service", str(context.exception))

            await coordinator.stop_service("test_service")

        self.loop.run_until_complete(test())

    def test_register_duplicate_service_raises_error(self):
        """測試重複註冊服務時拋出錯誤"""
        coordinator = ServiceCoordinator()
        service1 = MockService("test_service")
        service2 = MockService("test_service")

        coordinator.register_service(service1)

        with self.assertRaises(ValueError) as context:
            coordinator.register_service(service2)

        self.assertIn("already registered", str(context.exception))
        self.assertIn("replace_service()", str(context.exception))

    def test_replace_service(self):
        """測試替換服務"""
        coordinator = ServiceCoordinator()
        service1 = MockService("test_service")
        service2 = MockService("test_service")

        coordinator.register_service(service1)
        coordinator.replace_service(service2)

        self.assertIs(coordinator._services["test_service"], service2)

    def test_replace_running_service_raises_error(self):
        """測試替換正在運行的服務時拋出錯誤"""
        async def test():
            coordinator = ServiceCoordinator()
            service1 = MockService("test_service")
            service2 = MockService("test_service")

            coordinator.register_service(service1)
            await coordinator.start_service("test_service")

            with self.assertRaises(ValueError) as context:
                coordinator.replace_service(service2)

            self.assertIn("Cannot replace running service", str(context.exception))

            await coordinator.stop_service("test_service")

        self.loop.run_until_complete(test())

    def test_replace_nonexistent_service(self):
        """測試替換不存在的服務（等同於 register）"""
        coordinator = ServiceCoordinator()
        service = MockService("test_service")

        coordinator.replace_service(service)

        self.assertIn("test_service", coordinator._services)

    def test_unregister_service(self):
        """測試取消註冊服務"""
        coordinator = ServiceCoordinator()
        service = MockService("test_service")

        coordinator.register_service(service)
        result = coordinator.unregister_service("test_service")

        self.assertTrue(result)
        self.assertNotIn("test_service", coordinator._services)
        self.assertNotIn("test_service", coordinator._states)

    def test_unregister_nonexistent_service(self):
        """測試取消註冊不存在的服務"""
        coordinator = ServiceCoordinator()

        result = coordinator.unregister_service("nonexistent")

        self.assertFalse(result)

    def test_start_service(self):
        """測試啟動服務"""
        async def test():
            coordinator = ServiceCoordinator()
            service = MockService("test_service")
            coordinator.register_service(service)

            result = await coordinator.start_service("test_service")

            self.assertTrue(result)
            self.assertTrue(service.is_running)
            state = coordinator._states["test_service"]
            self.assertEqual(state.status, ServiceStatus.RUNNING)

        self.loop.run_until_complete(test())

    def test_start_service_failure(self):
        """測試啟動服務失敗"""
        async def test():
            coordinator = ServiceCoordinator()
            service = MockService("test_service")
            service.set_start_success(False)
            coordinator.register_service(service)

            result = await coordinator.start_service("test_service")

            self.assertFalse(result)
            state = coordinator._states["test_service"]
            self.assertEqual(state.status, ServiceStatus.ERROR)

        self.loop.run_until_complete(test())

    def test_start_nonexistent_service(self):
        """測試啟動不存在的服務"""
        async def test():
            coordinator = ServiceCoordinator()

            result = await coordinator.start_service("nonexistent")

            self.assertFalse(result)

        self.loop.run_until_complete(test())

    def test_stop_service(self):
        """測試停止服務"""
        async def test():
            coordinator = ServiceCoordinator()
            service = MockService("test_service")
            coordinator.register_service(service)

            await coordinator.start_service("test_service")
            result = await coordinator.stop_service("test_service")

            self.assertTrue(result)
            self.assertFalse(service.is_running)
            state = coordinator._states["test_service"]
            self.assertEqual(state.status, ServiceStatus.STOPPED)

        self.loop.run_until_complete(test())

    def test_stop_not_running_service(self):
        """測試停止未運行的服務"""
        async def test():
            coordinator = ServiceCoordinator()
            service = MockService("test_service")
            coordinator.register_service(service)

            result = await coordinator.stop_service("test_service")

            self.assertTrue(result)

        self.loop.run_until_complete(test())

    def test_start_all_services(self):
        """測試啟動所有服務"""
        async def test():
            coordinator = ServiceCoordinator()
            service1 = MockService("service1")
            service2 = MockService("service2")

            coordinator.register_service(service1)
            coordinator.register_service(service2)

            results = await coordinator.start_all_services()

            self.assertTrue(results["service1"])
            self.assertTrue(results["service2"])
            self.assertTrue(service1.is_running)
            self.assertTrue(service2.is_running)

        self.loop.run_until_complete(test())

    def test_start_all_services_skip_disabled(self):
        """測試啟動所有服務時跳過禁用的服務"""
        async def test():
            coordinator = ServiceCoordinator()
            service1 = MockService("service1")
            service2 = MockService("service2")

            config1 = ServiceConfig(name="service1", service_type="Mock", enabled=True)
            config2 = ServiceConfig(name="service2", service_type="Mock", enabled=False)

            coordinator.register_service(service1, config1)
            coordinator.register_service(service2, config2)

            results = await coordinator.start_all_services()

            # 啟用的服務應該啟動成功
            self.assertTrue(results["service1"])
            # 禁用的服務返回 True 表示"跳過成功"，而非實際啟動
            self.assertTrue(results["service2"])
            self.assertTrue(service1.is_running)
            # 禁用的服務確實未運行
            self.assertFalse(service2.is_running)

        self.loop.run_until_complete(test())

    def test_stop_all_services(self):
        """測試停止所有服務"""
        async def test():
            coordinator = ServiceCoordinator()
            service1 = MockService("service1")
            service2 = MockService("service2")

            coordinator.register_service(service1)
            coordinator.register_service(service2)

            await coordinator.start_all_services()
            results = await coordinator.stop_all_services()

            self.assertTrue(results["service1"])
            self.assertTrue(results["service2"])
            self.assertFalse(service1.is_running)
            self.assertFalse(service2.is_running)

        self.loop.run_until_complete(test())

    def test_check_service_health(self):
        """測試檢查服務健康狀態"""
        async def test():
            coordinator = ServiceCoordinator()
            service = MockService("test_service")
            coordinator.register_service(service)

            await coordinator.start_service("test_service")
            result = await coordinator.check_service_health("test_service")

            self.assertTrue(result)
            state = coordinator._states["test_service"]
            self.assertEqual(state.status, ServiceStatus.HEALTHY)
            self.assertIsNotNone(state.last_health_check)

        self.loop.run_until_complete(test())

    def test_check_service_health_unhealthy(self):
        """測試檢查服務健康狀態 - 不健康"""
        async def test():
            coordinator = ServiceCoordinator(alert_threshold=10)  # 高閾值避免觸發重啟
            service = MockService("test_service")
            service.set_health_result({"status": "unhealthy"})
            coordinator.register_service(service)

            await coordinator.start_service("test_service")
            result = await coordinator.check_service_health("test_service")

            self.assertFalse(result)
            state = coordinator._states["test_service"]
            self.assertEqual(state.status, ServiceStatus.UNHEALTHY)
            self.assertEqual(state.consecutive_failures, 1)

        self.loop.run_until_complete(test())

    def test_check_service_health_not_running(self):
        """測試檢查未運行服務的健康狀態"""
        async def test():
            coordinator = ServiceCoordinator()
            service = MockService("test_service")
            coordinator.register_service(service)

            result = await coordinator.check_service_health("test_service")

            self.assertFalse(result)

        self.loop.run_until_complete(test())

    def test_check_all_services_health(self):
        """測試檢查所有服務的健康狀態"""
        async def test():
            coordinator = ServiceCoordinator()
            service1 = MockService("service1")
            service2 = MockService("service2")

            coordinator.register_service(service1)
            coordinator.register_service(service2)

            await coordinator.start_all_services()
            results = await coordinator.check_all_services_health()

            self.assertTrue(results["service1"])
            self.assertTrue(results["service2"])

        self.loop.run_until_complete(test())

    def test_get_services_status(self):
        """測試取得所有服務狀態"""
        async def test():
            coordinator = ServiceCoordinator()
            service = MockService("test_service")
            coordinator.register_service(service)

            await coordinator.start_service("test_service")

            statuses = coordinator.get_services_status()

            self.assertIn("test_service", statuses)
            status = statuses["test_service"]
            self.assertEqual(status["name"], "test_service")
            self.assertEqual(status["status"], "running")
            self.assertTrue(status["is_running"])

        self.loop.run_until_complete(test())

    def test_coordinator_health_check(self):
        """測試協調器自身的健康檢查"""
        async def test():
            coordinator = ServiceCoordinator()
            service = MockService("test_service")
            coordinator.register_service(service)

            await coordinator.start_service("test_service")
            await coordinator.check_service_health("test_service")

            coordinator._running = True
            health = await coordinator.health_check()

            self.assertEqual(health["status"], "healthy")
            self.assertTrue(health["running"])
            self.assertEqual(health["service_count"], 1)
            self.assertIn("test_service", health["services"])

        self.loop.run_until_complete(test())

    def test_coordinator_start_and_stop(self):
        """測試協調器啟動和停止"""
        async def test():
            coordinator = ServiceCoordinator(health_check_interval=1.0)
            service = MockService("test_service")
            coordinator.register_service(service)

            # 啟動
            result = await coordinator.start()
            self.assertTrue(result)
            self.assertTrue(coordinator._running)
            self.assertTrue(service.is_running)
            self.assertIsNotNone(coordinator._health_check_task)

            # 停止
            result = await coordinator.stop()
            self.assertTrue(result)
            self.assertFalse(coordinator._running)
            self.assertFalse(service.is_running)

        self.loop.run_until_complete(test())

    def test_alert_callback(self):
        """測試告警回呼"""
        async def test():
            coordinator = ServiceCoordinator()

            alerts = []

            async def alert_callback(title, body, context):
                alerts.append((title, body, context))

            coordinator.set_alert_callback(alert_callback)

            await coordinator._send_alert("Test Alert", "Test Body", {"key": "value"})

            self.assertEqual(len(alerts), 1)
            self.assertEqual(alerts[0][0], "Test Alert")
            self.assertEqual(alerts[0][1], "Test Body")
            self.assertEqual(alerts[0][2]["key"], "value")

        self.loop.run_until_complete(test())


class TestQueueService(unittest.TestCase):
    """測試 QueueService"""

    def setUp(self):
        """設定測試環境"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """清理測試環境"""
        self.loop.close()

    def test_queue_service_name(self):
        """測試佇列服務名稱"""
        service = QueueService()
        self.assertEqual(service.name, "queue_service")

    def test_queue_service_start_stop(self):
        """測試佇列服務啟動和停止"""
        async def test():
            service = QueueService(queue_max_size=100, max_workers=2)

            # 啟動
            result = await service.start()
            self.assertTrue(result)
            self.assertTrue(service.is_running)

            # 停止
            result = await service.stop(timeout=5.0)
            self.assertTrue(result)
            self.assertFalse(service.is_running)

        self.loop.run_until_complete(test())

    def test_queue_service_health_check(self):
        """測試佇列服務健康檢查"""
        async def test():
            service = QueueService()

            await service.start()

            health = await service.health_check()

            self.assertIn("status", health)
            self.assertTrue(health["started"])

            await service.stop()

        self.loop.run_until_complete(test())

    def test_queue_service_manager_access(self):
        """測試存取內部 ServiceManager"""
        service = QueueService()

        manager = service.manager

        self.assertIsNotNone(manager)


class TestServiceCoordinatorIntegration(unittest.TestCase):
    """整合測試 ServiceCoordinator 與 QueueService"""

    def setUp(self):
        """設定測試環境"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """清理測試環境"""
        self.loop.close()

    def test_coordinator_with_queue_service(self):
        """測試協調器與佇列服務整合"""
        async def test():
            coordinator = ServiceCoordinator(health_check_interval=60.0)
            queue_service = QueueService(queue_max_size=100, max_workers=2)

            config = ServiceConfig(
                name="queue_service",
                service_type="QueueService",
                enabled=True,
                auto_restart=True,
            )

            coordinator.register_service(queue_service, config)

            # 啟動
            result = await coordinator.start()
            self.assertTrue(result)
            self.assertTrue(queue_service.is_running)

            # 健康檢查
            health_result = await coordinator.check_service_health("queue_service")
            self.assertTrue(health_result)

            # 取得狀態
            statuses = coordinator.get_services_status()
            self.assertIn("queue_service", statuses)
            self.assertEqual(statuses["queue_service"]["status"], "healthy")

            # 停止
            result = await coordinator.stop()
            self.assertTrue(result)
            self.assertFalse(queue_service.is_running)

        self.loop.run_until_complete(test())


if __name__ == '__main__':
    unittest.main()
