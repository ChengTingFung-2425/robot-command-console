"""
測試服務啟動異常恢復邏輯
驗證子服務啟動失敗時的重試機制
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
)
from common.service_types import ServiceStatus, ServiceConfig  # noqa: E402


class FlakeyService(ServiceBase):
    """
    模擬不穩定的服務，用於測試啟動重試邏輯

    此服務會在前幾次啟動時失敗，然後成功啟動
    """

    def __init__(self, name: str = "flakey_service", failures_before_success: int = 2):
        """
        初始化模擬不穩定服務

        Args:
            name: 服務名稱
            failures_before_success: 成功前需要失敗的次數
        """
        self._name = name
        self._running = False
        self._health_result = {"status": "healthy"}
        self._start_attempts = 0
        self._failures_before_success = failures_before_success

    @property
    def name(self) -> str:
        return self._name

    async def start(self) -> bool:
        """
        嘗試啟動服務

        前 failures_before_success 次會失敗，之後成功
        """
        self._start_attempts += 1
        if self._start_attempts <= self._failures_before_success:
            return False
        self._running = True
        return True

    async def stop(self, timeout: Optional[float] = None) -> bool:
        self._running = False
        return True

    async def health_check(self) -> Dict[str, Any]:
        return self._health_result

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def start_attempts(self) -> int:
        """取得啟動嘗試次數"""
        return self._start_attempts

    def reset(self) -> None:
        """重置服務狀態"""
        self._start_attempts = 0
        self._running = False


class TimeoutService(ServiceBase):
    """模擬啟動超時的服務"""

    def __init__(self, name: str = "timeout_service", delay_seconds: float = 10.0):
        self._name = name
        self._running = False
        self._delay_seconds = delay_seconds

    @property
    def name(self) -> str:
        return self._name

    async def start(self) -> bool:
        await asyncio.sleep(self._delay_seconds)
        self._running = True
        return True

    async def stop(self, timeout: Optional[float] = None) -> bool:
        self._running = False
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy" if self._running else "stopped"}

    @property
    def is_running(self) -> bool:
        return self._running


class ExceptionService(ServiceBase):
    """模擬啟動時拋出異常的服務"""

    def __init__(
        self,
        name: str = "exception_service",
        exceptions_before_success: int = 2
    ):
        self._name = name
        self._running = False
        self._start_attempts = 0
        self._exceptions_before_success = exceptions_before_success

    @property
    def name(self) -> str:
        return self._name

    async def start(self) -> bool:
        self._start_attempts += 1
        if self._start_attempts <= self._exceptions_before_success:
            raise RuntimeError(f"Simulated startup error (attempt {self._start_attempts})")
        self._running = True
        return True

    async def stop(self, timeout: Optional[float] = None) -> bool:
        self._running = False
        return True

    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy" if self._running else "stopped"}

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def start_attempts(self) -> int:
        return self._start_attempts


class TestServiceConfigStartupRetry(unittest.TestCase):
    """測試 ServiceConfig 的啟動重試配置"""

    def test_default_startup_retry_config(self):
        """測試啟動重試的預設配置"""
        config = ServiceConfig(name="test", service_type="test_type")

        self.assertTrue(config.startup_retry_enabled)
        self.assertEqual(config.max_startup_retry_attempts, 3)
        self.assertEqual(config.startup_retry_delay_seconds, 1.0)

    def test_custom_startup_retry_config(self):
        """測試自訂啟動重試配置"""
        config = ServiceConfig(
            name="test",
            service_type="test_type",
            startup_retry_enabled=False,
            max_startup_retry_attempts=5,
            startup_retry_delay_seconds=0.5,
        )

        self.assertFalse(config.startup_retry_enabled)
        self.assertEqual(config.max_startup_retry_attempts, 5)
        self.assertEqual(config.startup_retry_delay_seconds, 0.5)


class TestStartupRecovery(unittest.TestCase):
    """測試服務啟動異常恢復邏輯"""

    def setUp(self):
        """設定測試環境"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """清理測試環境"""
        self.loop.close()

    def test_startup_recovery_success_after_retries(self):
        """測試啟動失敗後重試成功"""
        async def test():
            coordinator = ServiceCoordinator()
            # 服務會在第 2 次嘗試後成功（共需 3 次嘗試）
            service = FlakeyService("flakey_service", failures_before_success=2)

            config = ServiceConfig(
                name="flakey_service",
                service_type="FlakeyService",
                startup_retry_enabled=True,
                max_startup_retry_attempts=3,
                startup_retry_delay_seconds=0.1,  # 短延遲以加速測試
            )

            coordinator.register_service(service, config)

            result = await coordinator.start_service("flakey_service")

            self.assertTrue(result)
            self.assertTrue(service.is_running)
            self.assertEqual(service.start_attempts, 3)  # 1 初始 + 2 重試

            state = coordinator._states["flakey_service"]
            self.assertEqual(state.status, ServiceStatus.RUNNING)
            self.assertEqual(state.startup_retry_count, 2)  # 進行了 2 次重試

        self.loop.run_until_complete(test())

    def test_startup_recovery_failure_exhausted_retries(self):
        """測試啟動失敗且重試次數用盡"""
        async def test():
            coordinator = ServiceCoordinator()
            # 服務會在第 5 次嘗試後才成功，但我們只允許 2 次重試
            service = FlakeyService("always_fail", failures_before_success=10)

            config = ServiceConfig(
                name="always_fail",
                service_type="FlakeyService",
                startup_retry_enabled=True,
                max_startup_retry_attempts=2,
                startup_retry_delay_seconds=0.1,
            )

            coordinator.register_service(service, config)

            result = await coordinator.start_service("always_fail")

            self.assertFalse(result)
            self.assertFalse(service.is_running)
            self.assertEqual(service.start_attempts, 3)  # 1 初始 + 2 重試

            state = coordinator._states["always_fail"]
            self.assertEqual(state.status, ServiceStatus.ERROR)
            self.assertEqual(state.startup_retry_count, 2)

        self.loop.run_until_complete(test())

    def test_startup_recovery_disabled(self):
        """測試禁用啟動重試"""
        async def test():
            coordinator = ServiceCoordinator()
            service = FlakeyService("no_retry", failures_before_success=2)

            config = ServiceConfig(
                name="no_retry",
                service_type="FlakeyService",
                startup_retry_enabled=False,  # 禁用重試
            )

            coordinator.register_service(service, config)

            result = await coordinator.start_service("no_retry")

            self.assertFalse(result)
            self.assertFalse(service.is_running)
            self.assertEqual(service.start_attempts, 1)  # 只嘗試了 1 次

            state = coordinator._states["no_retry"]
            self.assertEqual(state.status, ServiceStatus.ERROR)
            self.assertEqual(state.startup_retry_count, 0)

        self.loop.run_until_complete(test())

    def test_startup_recovery_with_exception(self):
        """測試啟動時拋出異常的恢復"""
        async def test():
            coordinator = ServiceCoordinator()
            service = ExceptionService("exception_service", exceptions_before_success=2)

            config = ServiceConfig(
                name="exception_service",
                service_type="ExceptionService",
                startup_retry_enabled=True,
                max_startup_retry_attempts=3,
                startup_retry_delay_seconds=0.1,
            )

            coordinator.register_service(service, config)

            result = await coordinator.start_service("exception_service")

            self.assertTrue(result)
            self.assertTrue(service.is_running)
            self.assertEqual(service.start_attempts, 3)

            state = coordinator._states["exception_service"]
            self.assertEqual(state.status, ServiceStatus.RUNNING)

        self.loop.run_until_complete(test())

    def test_startup_success_first_try(self):
        """測試第一次啟動就成功（無需重試）"""
        async def test():
            coordinator = ServiceCoordinator()
            service = FlakeyService("success_first", failures_before_success=0)

            config = ServiceConfig(
                name="success_first",
                service_type="FlakeyService",
                startup_retry_enabled=True,
                max_startup_retry_attempts=3,
            )

            coordinator.register_service(service, config)

            result = await coordinator.start_service("success_first")

            self.assertTrue(result)
            self.assertTrue(service.is_running)
            self.assertEqual(service.start_attempts, 1)

            state = coordinator._states["success_first"]
            self.assertEqual(state.status, ServiceStatus.RUNNING)
            self.assertEqual(state.startup_retry_count, 0)

        self.loop.run_until_complete(test())

    def test_startup_recovery_alerts(self):
        """測試啟動重試時的告警觸發"""
        async def test():
            coordinator = ServiceCoordinator()
            service = FlakeyService("alert_test", failures_before_success=2)

            alerts = []

            async def alert_callback(title, body, context):
                alerts.append({
                    "title": title,
                    "body": body,
                    "context": context
                })

            coordinator.set_alert_callback(alert_callback)

            config = ServiceConfig(
                name="alert_test",
                service_type="FlakeyService",
                startup_retry_enabled=True,
                max_startup_retry_attempts=3,
                startup_retry_delay_seconds=0.1,
            )

            coordinator.register_service(service, config)

            result = await coordinator.start_service("alert_test")

            self.assertTrue(result)

            # 應該收到 2 次重試告警
            retry_alerts = [a for a in alerts if a["context"].get("alert_type") == "startup_retry"]
            self.assertEqual(len(retry_alerts), 2)

            # 驗證告警內容
            self.assertEqual(retry_alerts[0]["context"]["retry_attempt"], 1)
            self.assertEqual(retry_alerts[1]["context"]["retry_attempt"], 2)

        self.loop.run_until_complete(test())

    def test_startup_failure_final_alert(self):
        """測試啟動失敗後的最終告警"""
        async def test():
            coordinator = ServiceCoordinator()
            service = FlakeyService("final_alert", failures_before_success=10)

            alerts = []

            async def alert_callback(title, body, context):
                alerts.append({
                    "title": title,
                    "body": body,
                    "context": context
                })

            coordinator.set_alert_callback(alert_callback)

            config = ServiceConfig(
                name="final_alert",
                service_type="FlakeyService",
                startup_retry_enabled=True,
                max_startup_retry_attempts=2,
                startup_retry_delay_seconds=0.1,
            )

            coordinator.register_service(service, config)

            result = await coordinator.start_service("final_alert")

            self.assertFalse(result)

            # 應該收到最終失敗告警
            failed_alerts = [a for a in alerts if a["context"].get("alert_type") == "startup_failed"]
            self.assertEqual(len(failed_alerts), 1)
            self.assertEqual(failed_alerts[0]["context"]["total_attempts"], 3)

        self.loop.run_until_complete(test())

    def test_get_services_status_includes_startup_retry_count(self):
        """測試 get_services_status 包含 startup_retry_count"""
        async def test():
            coordinator = ServiceCoordinator()
            service = FlakeyService("status_test", failures_before_success=1)

            config = ServiceConfig(
                name="status_test",
                service_type="FlakeyService",
                startup_retry_enabled=True,
                max_startup_retry_attempts=3,
                startup_retry_delay_seconds=0.1,
            )

            coordinator.register_service(service, config)

            await coordinator.start_service("status_test")

            statuses = coordinator.get_services_status()

            self.assertIn("status_test", statuses)
            self.assertIn("startup_retry_count", statuses["status_test"])
            self.assertEqual(statuses["status_test"]["startup_retry_count"], 1)

        self.loop.run_until_complete(test())


class TestStartupRecoveryIntegration(unittest.TestCase):
    """整合測試：啟動異常恢復與服務協調器"""

    def setUp(self):
        """設定測試環境"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """清理測試環境"""
        self.loop.close()

    def test_start_all_services_with_flakey_service(self):
        """測試 start_all_services 包含不穩定服務"""
        async def test():
            coordinator = ServiceCoordinator(health_check_interval=60.0)

            # 正常服務
            from tests.test_service_coordinator import MockService
            normal_service = MockService("normal_service")

            # 不穩定服務
            flakey_service = FlakeyService("flakey_service", failures_before_success=1)

            config_normal = ServiceConfig(
                name="normal_service",
                service_type="MockService",
            )
            config_flakey = ServiceConfig(
                name="flakey_service",
                service_type="FlakeyService",
                startup_retry_enabled=True,
                max_startup_retry_attempts=3,
                startup_retry_delay_seconds=0.1,
            )

            coordinator.register_service(normal_service, config_normal)
            coordinator.register_service(flakey_service, config_flakey)

            result = await coordinator.start()

            self.assertTrue(result)
            self.assertTrue(normal_service.is_running)
            self.assertTrue(flakey_service.is_running)

            await coordinator.stop()

        self.loop.run_until_complete(test())

    def test_coordinator_start_with_one_failing_service(self):
        """測試協調器啟動時有一個服務持續失敗"""
        async def test():
            coordinator = ServiceCoordinator(health_check_interval=60.0)

            from tests.test_service_coordinator import MockService
            normal_service = MockService("normal_service")

            always_fail = FlakeyService("always_fail", failures_before_success=100)

            config_normal = ServiceConfig(
                name="normal_service",
                service_type="MockService",
            )
            config_fail = ServiceConfig(
                name="always_fail",
                service_type="FlakeyService",
                startup_retry_enabled=True,
                max_startup_retry_attempts=2,
                startup_retry_delay_seconds=0.1,
            )

            coordinator.register_service(normal_service, config_normal)
            coordinator.register_service(always_fail, config_fail)

            result = await coordinator.start()

            # 協調器應該回報失敗（有服務無法啟動）
            self.assertFalse(result)

            # 正常服務仍應該運行
            self.assertTrue(normal_service.is_running)
            self.assertFalse(always_fail.is_running)

            await coordinator.stop()

        self.loop.run_until_complete(test())


if __name__ == '__main__':
    unittest.main()
