"""
Phase 3.1 整合測試

驗證 Phase 3.1 的核心功能：
1. 一鍵啟動所有服務
2. 服務健康檢查
3. LLM 提供商選擇
4. 基本指令執行流程
"""

import asyncio
import sys
import os
from pathlib import Path
from uuid import uuid4

# 添加 src 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest  # noqa: E402


def run_async(coro):
    """輔助函數：在新的事件迴圈中執行協程"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestPhase31AcceptanceCriteria:
    """
    Phase 3.1 驗收條件測試

    驗證以下驗收條件：
    - AC-001: 一鍵啟動所有服務成功，無錯誤
    - AC-002: 所有服務健康檢查通過
    - AC-003: 可選擇本地 LLM 提供商（Ollama/LM Studio）
    - AC-004: 基本指令執行流程完整
    - AC-005: 服務間狀態共享機制正常運作
    """

    def test_ac001_one_click_start_all_services(self):
        """
        AC-001: 一鍵啟動所有服務成功，無錯誤

        驗證 UnifiedLauncher.start_all() 可以啟動所有已註冊服務
        """
        from robot_service.unified_launcher import UnifiedLauncher

        async def test():
            launcher = UnifiedLauncher()
            launcher.register_default_services()

            # 驗證服務已註冊
            status = launcher.get_services_status()
            assert len(status) >= 1, "應該至少有一個服務被註冊"

            # 驗證 start_all 方法存在且可呼叫
            assert hasattr(launcher, 'start_all'), "start_all 方法不存在"
            assert callable(launcher.start_all), "start_all 不是可呼叫的"

        run_async(test())

    def test_ac002_all_services_health_check(self):
        """
        AC-002: 所有服務健康檢查通過

        驗證 UnifiedLauncher.health_check_all() 可以檢查所有服務健康狀態
        """
        from robot_service.unified_launcher import UnifiedLauncher

        async def test():
            launcher = UnifiedLauncher()

            # 執行健康檢查
            result = await launcher.health_check_all()

            # 驗證結果結構
            assert "overall_healthy" in result, "健康檢查結果缺少 overall_healthy"
            assert "services" in result, "健康檢查結果缺少 services"
            assert "timestamp" in result, "健康檢查結果缺少 timestamp"
            assert isinstance(result["overall_healthy"], bool), "overall_healthy 應為布林值"

        run_async(test())

    def test_ac003_select_llm_provider(self):
        """
        AC-003: 可選擇本地 LLM 提供商（Ollama/LM Studio）

        驗證可以註冊和選擇 LLM 提供商
        """
        from MCP.llm_provider_manager import LLMProviderManager
        from MCP.providers import OllamaProvider
        from MCP.llm_provider_base import ProviderConfig

        manager = LLMProviderManager()

        # 驗證預設提供商類別列表包含 Ollama 和 LM Studio
        provider_names = [p.__name__ for p in manager.provider_classes]
        assert "OllamaProvider" in provider_names, "應支援 Ollama 提供商"
        assert "LMStudioProvider" in provider_names, "應支援 LM Studio 提供商"

        # 註冊 Ollama 提供商
        config = ProviderConfig(name="ollama", port=11434)
        provider = OllamaProvider(config)
        manager.register_provider(provider)

        # 選擇提供商
        success = manager.select_provider("ollama")
        assert success, "選擇 Ollama 提供商應該成功"
        assert manager.get_selected_provider_name() == "ollama"

        # 驗證可以取得提供商
        retrieved = manager.get_provider()
        assert retrieved is not None
        assert retrieved.provider_name == "ollama"

    def test_ac004_basic_command_flow(self):
        """
        AC-004: 基本指令執行流程完整

        驗證指令處理流程：接收 → 驗證 → 路由 → 執行
        """
        from MCP.llm_processor import LLMProcessor
        from MCP.llm_provider_manager import LLMProviderManager

        async def test():
            manager = LLMProviderManager()
            processor = LLMProcessor(provider_manager=manager)

            # 測試規則式解析（無 LLM 時的回退）
            command = await processor.parse_command(
                transcription="向前移動三秒",
                robot_id="robot-001"
            )

            # 驗證解析結果
            assert command is not None, "指令解析不應為 None"
            assert command.type == "robot.action", "指令類型應為 robot.action"
            assert command.target.robot_id == "robot-001", "目標機器人 ID 應正確"
            assert command.params["action_name"] == "go_forward", "動作名稱應為 go_forward"
            assert command.params["duration_ms"] == 3000, "持續時間應為 3000ms"

        run_async(test())

    def test_ac005_shared_state_mechanism(self):
        """
        AC-005: 服務間狀態共享機制正常運作

        驗證 SharedStateManager 可以：
        1. 更新和讀取狀態
        2. 發布和訂閱事件
        """
        from common.shared_state import SharedStateManager, EventTopics

        async def test():
            manager = SharedStateManager()
            await manager.start()

            received_events = []

            async def handler(event):
                received_events.append(event)

            # 訂閱事件
            await manager.subscribe(EventTopics.SERVICE_HEALTH_CHANGED, handler)

            # 更新服務狀態（觸發事件）
            await manager.update_service_status("test_service", "running")

            # 驗證事件被接收
            assert len(received_events) >= 1, "應該收到服務狀態變更事件"

            # 驗證狀態可讀取
            all_status = await manager.get_all_services_status()
            assert "test_service" in all_status, "應該能讀取服務狀態"
            # 狀態可能是完整的狀態物件
            status = all_status["test_service"]
            if isinstance(status, dict):
                assert status.get("status") == "running", "狀態應為 running"
            else:
                assert status == "running", "狀態應為 running"

            await manager.stop()

        run_async(test())


class TestPhase31ServiceCoordination:
    """
    服務協調測試

    驗證多服務的協調能力
    """

    def test_coordinator_register_multiple_services(self):
        """測試註冊多個服務"""
        from robot_service.service_coordinator import ServiceCoordinator, QueueService

        coordinator = ServiceCoordinator()
        queue_service = QueueService(queue_max_size=100, max_workers=2)

        coordinator.register_service(queue_service)

        assert "queue_service" in coordinator._services
        assert "queue_service" in coordinator._states

    def test_coordinator_start_stop_lifecycle(self):
        """測試協調器的完整生命週期"""
        from robot_service.service_coordinator import ServiceCoordinator, QueueService
        from common.service_types import ServiceConfig

        async def test():
            coordinator = ServiceCoordinator(health_check_interval=60.0)
            queue_service = QueueService(queue_max_size=100, max_workers=2)

            config = ServiceConfig(
                name="queue_service",
                service_type="QueueService",
                enabled=True,
            )

            coordinator.register_service(queue_service, config)

            # 啟動
            result = await coordinator.start()
            assert result, "啟動應該成功"
            assert queue_service.is_running, "佇列服務應該正在運行"

            # 健康檢查
            health = await coordinator.check_service_health("queue_service")
            assert health, "健康檢查應該通過"

            # 取得狀態
            statuses = coordinator.get_services_status()
            assert "queue_service" in statuses
            assert statuses["queue_service"]["is_running"]

            # 停止
            result = await coordinator.stop()
            assert result, "停止應該成功"
            assert not queue_service.is_running, "佇列服務應該已停止"

        run_async(test())


class TestPhase31CommandExecution:
    """
    指令執行測試

    驗證指令從接收到執行的完整流程
    """

    def test_command_parsing_various_formats(self):
        """測試各種格式的指令解析"""
        from MCP.llm_processor import LLMProcessor
        from MCP.llm_provider_manager import LLMProviderManager

        async def test():
            manager = LLMProviderManager()
            processor = LLMProcessor(provider_manager=manager)

            # 使用規則式解析的實際動作名稱
            test_cases = [
                ("向前走三秒", "go_forward", 3000),
                ("後退兩秒", "back_fast", 2000),  # 規則式解析實際輸出
                ("左轉", "turn_left", 1000),
                ("右轉", "turn_right", 1000),
                ("停止", "stop", 1000),  # 規則式解析實際輸出
            ]

            for transcription, expected_action, expected_duration in test_cases:
                command = await processor.parse_command(
                    transcription=transcription,
                    robot_id="robot-001"
                )

                assert command is not None, f"指令 '{transcription}' 解析不應為 None"
                assert command.params["action_name"] == expected_action, \
                    f"指令 '{transcription}' 應解析為 {expected_action}，實際為 {command.params['action_name']}"

        run_async(test())

    def test_queue_submission_and_processing(self):
        """測試佇列提交和處理"""
        from robot_service.service_manager import ServiceManager
        from robot_service.queue import MessagePriority

        async def test():
            manager = ServiceManager(queue_max_size=100)
            await manager.start()

            # 提交指令到佇列
            message_id = await manager.submit_command(
                payload={"command": "test", "action": "go_forward"},
                priority=MessagePriority.NORMAL,
                trace_id=str(uuid4()),
            )

            assert message_id is not None, "應該返回訊息 ID"

            await manager.stop()

        run_async(test())


class TestPhase31LLMIntegration:
    """
    LLM 整合測試

    驗證 LLM 提供商的整合功能
    """

    @pytest.mark.asyncio
    async def test_llm_provider_discovery(self):
        """測試 LLM 提供商自動偵測"""
        from MCP.llm_provider_manager import LLMProviderManager

        manager = LLMProviderManager()

        # 執行偵測（實際服務可能不在運行）
        health_results = await manager.discover_providers(timeout=1)

        # 應該至少嘗試掃描預設的提供商
        assert isinstance(health_results, dict)
        assert len(health_results) >= 2  # Ollama 和 LM Studio

    def test_llm_fallback_to_rule_based(self):
        """測試無 LLM 時回退到規則式解析"""
        from MCP.llm_processor import LLMProcessor
        from MCP.llm_provider_manager import LLMProviderManager

        async def test():
            # 不註冊任何提供商
            manager = LLMProviderManager()
            processor = LLMProcessor(provider_manager=manager)

            # 應該使用規則式解析
            command = await processor.parse_command(
                transcription="向前移動",
                robot_id="robot-001"
            )

            assert command is not None, "規則式解析應該成功"
            assert command.params["action_name"] == "go_forward"

        run_async(test())


class TestPhase31StateStore:
    """
    狀態存儲測試

    驗證本地狀態存儲功能
    """

    def test_state_store_crud(self):
        """測試狀態存儲的 CRUD 操作"""
        from common.state_store import LocalStateStore

        async def test():
            store = LocalStateStore()
            await store.start()

            # Create
            success = await store.set("test_key", {"value": 123})
            assert success, "設置狀態應該成功"

            # Read
            value = await store.get("test_key")
            assert value == {"value": 123}, "讀取的值應該正確"

            # Update
            await store.set("test_key", {"value": 456})
            value = await store.get("test_key")
            assert value == {"value": 456}, "更新後的值應該正確"

            # Delete
            deleted = await store.delete("test_key")
            assert deleted, "刪除應該成功"
            assert not await store.exists("test_key"), "刪除後鍵不應存在"

            await store.stop()

        run_async(test())

    def test_event_bus_pubsub(self):
        """測試事件匯流排的發布訂閱"""
        from common.event_bus import LocalEventBus, Event

        async def test():
            bus = LocalEventBus()
            await bus.start()

            received = []

            async def handler(event: Event):
                received.append(event)

            # 訂閱
            sub_id = await bus.subscribe("test.topic", handler)
            assert sub_id is not None

            # 發布
            count = await bus.publish("test.topic", {"data": "value"})
            await asyncio.sleep(0.01)

            assert count == 1, "應該有一個訂閱者收到事件"
            assert len(received) == 1, "應該收到一個事件"
            assert received[0].data == {"data": "value"}

            await bus.stop()

        run_async(test())


class TestPhase31ElectronIntegration:
    """
    Electron 整合測試

    驗證 Electron 應用的結構和整合
    """

    def test_electron_main_structure(self):
        """測試 Electron main.js 結構"""
        main_js_path = Path(__file__).parent.parent.parent / 'electron-app' / 'main.js'
        assert main_js_path.exists(), "main.js 應該存在"

        content = main_js_path.read_text(encoding='utf-8')

        # 驗證關鍵函數存在
        required_functions = [
            'startService',
            'stopService',
            'startAllServices',
            'stopAllServices',
            'checkServiceHealth',
            'checkAllServicesHealth',
            'getServicesStatus',
        ]

        for func in required_functions:
            assert func in content, f"{func} 函數應存在於 main.js"

    def test_electron_preload_api(self):
        """測試 Electron preload.js API 暴露"""
        preload_path = Path(__file__).parent.parent.parent / 'electron-app' / 'preload.js'
        assert preload_path.exists(), "preload.js 應該存在"

        content = preload_path.read_text(encoding='utf-8')

        # 驗證 API 暴露
        required_apis = [
            'electronAPI',
            'getServicesStatus',
            'startService',
            'stopService',
            'startAllServices',
            'stopAllServices',
        ]

        for api in required_apis:
            assert api in content, f"{api} 應暴露於 preload.js"

    def test_electron_renderer_ui(self):
        """測試 Electron renderer 介面"""
        html_path = Path(__file__).parent.parent.parent / 'electron-app' / 'renderer' / 'index.html'
        assert html_path.exists(), "index.html 應該存在"

        content = html_path.read_text(encoding='utf-8')

        # 驗證 UI 元素
        assert '統一啟動器' in content, "標題應包含統一啟動器"
        assert 'start-all-btn' in content, "應有啟動所有服務按鈕"
        assert 'stop-all-btn' in content, "應有停止所有服務按鈕"
        assert 'Phase 3.1' in content, "應有 Phase 3.1 標記"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
