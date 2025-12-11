"""
測試 TUI 模組
"""

import pytest
from unittest.mock import Mock

from src.robot_service.tui.app import (
    RobotConsoleTUI,
    ServiceStatusWidget,
    RobotStatusWidget,
    CommandHistoryWidget
)
from src.common.service_types import ServiceStatus


class TestServiceStatusWidget:
    """測試服務狀態元件"""
    
    def test_init(self):
        """測試初始化"""
        widget = ServiceStatusWidget()
        assert widget.services_status == {}
    
    def test_update_service_status(self):
        """測試更新服務狀態"""
        widget = ServiceStatusWidget()
        widget.update_service_status("test_service", ServiceStatus.RUNNING)
        
        assert "test_service" in widget.services_status
        assert widget.services_status["test_service"] == ServiceStatus.RUNNING
    
    def test_render_status(self):
        """測試渲染狀態"""
        widget = ServiceStatusWidget()
        widget.update_service_status("mcp_service", ServiceStatus.RUNNING)
        widget.update_service_status("queue_service", ServiceStatus.STOPPED)
        
        status_text = widget.status_text
        assert "mcp_service" in status_text
        assert "queue_service" in status_text
        assert "running" in status_text.lower()
        assert "stopped" in status_text.lower()


class TestRobotStatusWidget:
    """測試機器人狀態元件"""
    
    def test_init(self):
        """測試初始化"""
        widget = RobotStatusWidget()
        assert widget.robots_status == {}
    
    def test_update_robot_status(self):
        """測試更新機器人狀態"""
        widget = RobotStatusWidget()
        status = {
            "connected": True,
            "battery_level": 85,
            "mode": "Standby"
        }
        widget.update_robot_status("robot-001", status)
        
        assert "robot-001" in widget.robots_status
        assert widget.robots_status["robot-001"]["connected"] is True
        assert widget.robots_status["robot-001"]["battery_level"] == 85
    
    def test_render_status_connected(self):
        """測試渲染連接中的機器人"""
        widget = RobotStatusWidget()
        widget.update_robot_status("robot-001", {
            "connected": True,
            "battery_level": 90,
            "mode": "Active"
        })
        
        status_text = widget.status_text
        assert "robot-001" in status_text
        assert "connected" in status_text.lower()
        assert "90" in status_text
    
    def test_render_status_disconnected(self):
        """測試渲染未連接的機器人"""
        widget = RobotStatusWidget()
        widget.update_robot_status("robot-002", {
            "connected": False
        })
        
        status_text = widget.status_text
        assert "robot-002" in status_text
        assert "disconnected" in status_text.lower()


class TestCommandHistoryWidget:
    """測試指令歷史元件"""
    
    def test_init(self):
        """測試初始化"""
        widget = CommandHistoryWidget()
        assert widget.history == []
    
    def test_add_command(self):
        """測試新增指令"""
        widget = CommandHistoryWidget()
        
        # Mock the query_one method
        mock_static = Mock()
        widget.query_one = Mock(return_value=mock_static)
        
        widget.add_command("10:30:00", "robot-001", "go_forward", "success")
        
        assert len(widget.history) == 1
        assert "robot-001" in widget.history[0]
        assert "go_forward" in widget.history[0]
        assert "success" in widget.history[0]
    
    def test_add_command_limit(self):
        """測試指令歷史限制"""
        widget = CommandHistoryWidget()
        widget.query_one = Mock(return_value=Mock())
        
        # 新增 25 個指令
        for i in range(25):
            widget.add_command(
                f"10:{i:02d}:00",
                f"robot-{i:03d}",
                "test_action",
                "success"
            )
        
        # 應該只保留最近 20 筆
        assert len(widget.history) == 20


class TestRobotConsoleTUI:
    """測試 TUI 應用"""
    
    @pytest.mark.asyncio
    async def test_init(self):
        """測試初始化"""
        app = RobotConsoleTUI()
        
        assert app.coordinator is None
        assert app.state_manager is None
        assert app.history_manager is None
        assert app._running is False
    
    @pytest.mark.asyncio
    async def test_init_with_dependencies(self):
        """測試使用依賴初始化"""
        mock_coordinator = Mock()
        mock_state_manager = Mock()
        mock_history_manager = Mock()
        
        app = RobotConsoleTUI(
            coordinator=mock_coordinator,
            state_manager=mock_state_manager,
            history_manager=mock_history_manager
        )
        
        assert app.coordinator is mock_coordinator
        assert app.state_manager is mock_state_manager
        assert app.history_manager is mock_history_manager
    
    @pytest.mark.asyncio
    async def test_refresh_services(self):
        """測試刷新服務狀態"""
        mock_coordinator = Mock()
        mock_coordinator.get_all_services_info.return_value = {
            "test_service": Mock(status=ServiceStatus.RUNNING)
        }
        
        app = RobotConsoleTUI(coordinator=mock_coordinator)
        
        # Mock the query_one method
        mock_widget = Mock()
        app.query_one = Mock(return_value=mock_widget)
        
        await app._refresh_services()
        
        mock_widget.update_service_status.assert_called_once_with(
            "test_service",
            ServiceStatus.RUNNING
        )
    
    def test_parse_command_basic(self):
        """測試基本指令解析"""
        app = RobotConsoleTUI()
        
        robot_id, action = app._parse_command("go_forward")
        assert robot_id == "robot-001"
        assert action == "go_forward"
    
    def test_parse_command_with_robot(self):
        """測試指定機器人的指令解析"""
        app = RobotConsoleTUI()
        
        robot_id, action = app._parse_command("robot-002:turn_left")
        assert robot_id == "robot-002"
        assert action == "turn_left"
    
    def test_parse_command_all_robots(self):
        """測試廣播指令解析（使用 all:action 格式）"""
        app = RobotConsoleTUI()
        
        robot_id, action = app._parse_command("all:stand")
        assert robot_id == "all"
        assert action == "stand"
    
    def test_parse_command_with_spaces(self):
        """測試帶空格的指令解析"""
        app = RobotConsoleTUI()
        
        robot_id, action = app._parse_command("  robot-003 : wave_hand  ")
        assert robot_id == "robot-003"
        assert action == "wave_hand"
    
    def test_parse_command_system(self):
        """測試系統指令解析"""
        app = RobotConsoleTUI()
        
        robot_id, action = app._parse_command("system:list")
        assert robot_id == "system"
        assert action == "list"
        
        robot_id, action = app._parse_command("system:show")
        assert robot_id == "system"
        assert action == "show"
        
        robot_id, action = app._parse_command("system:healthcheck")
        assert robot_id == "system"
        assert action == "healthcheck"
    
    def test_parse_command_service(self):
        """測試服務管理指令解析"""
        app = RobotConsoleTUI()
        
        robot_id, action = app._parse_command("service:mcp.start")
        assert robot_id == "service"
        assert action == "mcp.start"
        
        robot_id, action = app._parse_command("service:queue.stop")
        assert robot_id == "service"
        assert action == "queue.stop"
        
        robot_id, action = app._parse_command("service:all.healthcheck")
        assert robot_id == "service"
        assert action == "all.healthcheck"
    
    @pytest.mark.asyncio
    async def test_service_start(self):
        """測試服務啟動"""
        async def mock_start_service(name):
            return True
        
        mock_coordinator = Mock()
        mock_coordinator.start_service = mock_start_service
        
        app = RobotConsoleTUI(coordinator=mock_coordinator)
        app.notify = Mock()
        
        await app._service_single_action("mcp_service", "start")
        
        app.notify.assert_called_once()
        call_args = app.notify.call_args[0][0]
        assert "started" in call_args
    
    @pytest.mark.asyncio
    async def test_service_stop(self):
        """測試服務停止"""
        async def mock_stop_service(name):
            return True
        
        mock_coordinator = Mock()
        mock_coordinator.stop_service = mock_stop_service
        
        app = RobotConsoleTUI(coordinator=mock_coordinator)
        app.notify = Mock()
        
        await app._service_single_action("queue_service", "stop")
        
        app.notify.assert_called_once()
        call_args = app.notify.call_args[0][0]
        assert "stopped" in call_args
    
    @pytest.mark.asyncio
    async def test_service_restart(self):
        """測試服務重啟"""
        async def mock_stop_service(name):
            return True
        
        async def mock_start_service(name):
            return True
        
        mock_coordinator = Mock()
        mock_coordinator.stop_service = mock_stop_service
        mock_coordinator.start_service = mock_start_service
        
        app = RobotConsoleTUI(coordinator=mock_coordinator)
        app.notify = Mock()
        
        await app._service_single_action("flask_service", "restart")
        
        app.notify.assert_called_once()
        call_args = app.notify.call_args[0][0]
        assert "restarted" in call_args
    
    @pytest.mark.asyncio
    async def test_service_healthcheck(self):
        """測試單一服務健康檢查"""
        async def mock_check_health(name):
            return {"status": "healthy"}
        
        mock_coordinator = Mock()
        mock_coordinator.check_service_health = mock_check_health
        
        app = RobotConsoleTUI(coordinator=mock_coordinator)
        app.notify = Mock()
        
        await app._service_single_action("mcp_service", "healthcheck")
        
        app.notify.assert_called_once()
        call_args = app.notify.call_args[0][0]
        assert "healthy" in call_args
    
    @pytest.mark.asyncio
    async def test_service_all_start(self):
        """測試啟動所有服務"""
        async def mock_start():
            return True
        
        mock_coordinator = Mock()
        mock_coordinator.start = mock_start
        mock_coordinator.get_all_services_info.return_value = {
            "service1": Mock(),
            "service2": Mock()
        }
        
        app = RobotConsoleTUI(coordinator=mock_coordinator)
        app.notify = Mock()
        
        await app._service_all_action("start")
        
        app.notify.assert_called_once()
        call_args = app.notify.call_args[0][0]
        assert "All services started" in call_args
    
    @pytest.mark.asyncio
    async def test_service_all_healthcheck(self):
        """測試所有服務健康檢查"""
        async def mock_healthcheck():
            return {
                "service1": {"status": "healthy"},
                "service2": {"status": "healthy"}
            }
        
        mock_coordinator = Mock()
        mock_coordinator.check_all_services_health = mock_healthcheck
        mock_coordinator.get_all_services_info.return_value = {
            "service1": Mock(),
            "service2": Mock()
        }
        
        app = RobotConsoleTUI(coordinator=mock_coordinator)
        app.notify = Mock()
        
        await app._service_all_action("healthcheck")
        
        app.notify.assert_called_once()
        call_args = app.notify.call_args[0][0]
        assert "All services healthy" in call_args
    
    @pytest.mark.asyncio
    async def test_handle_queue_cloud_on(self):
        """測試啟用雲端路由"""
        app = RobotConsoleTUI()
        app.notify = Mock()
        
        await app._handle_queue_cloud("on")
        
        app.notify.assert_called_once()
        call_args = app.notify.call_args[0][0]
        assert "Cloud routing enabled" in call_args
    
    @pytest.mark.asyncio
    async def test_handle_queue_cloud_off(self):
        """測試停用雲端路由"""
        app = RobotConsoleTUI()
        app.notify = Mock()
        
        await app._handle_queue_cloud("off")
        
        app.notify.assert_called_once()
        call_args = app.notify.call_args[0][0]
        assert "Cloud routing disabled" in call_args
    
    @pytest.mark.asyncio
    async def test_handle_llm_provider(self):
        """測試設定 LLM 提供商"""
        app = RobotConsoleTUI()
        app.notify = Mock()
        
        await app._handle_llm_provider("ollama")
        
        app.notify.assert_called_once()
        call_args = app.notify.call_args[0][0]
        assert "LLM provider set to: ollama" in call_args
    
    def test_parse_bracket_notation(self):
        """測試解析方括號標記法"""
        app = RobotConsoleTUI()
        
        # 測試雙引號
        result = app._parse_bracket_notation('provider["ollama"]')
        assert result == "ollama"
        
        # 測試單引號
        result = app._parse_bracket_notation("provider['lmstudio']")
        assert result == "lmstudio"
        
        # 測試無效格式
        result = app._parse_bracket_notation("provider[ollama]")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_system_list_robots(self):
        """測試系統指令：列出機器人"""
        app = RobotConsoleTUI()
        
        # Mock widgets
        mock_robot_widget = Mock()
        mock_robot_widget.robots_status = {
            "robot-001": {"connected": True},
            "robot-002": {"connected": True}
        }
        app.query_one = Mock(return_value=mock_robot_widget)
        app.notify = Mock()
        
        await app._system_list_robots()
        
        app.notify.assert_called_once()
        call_args = app.notify.call_args[0][0]
        assert "Connected Robots" in call_args
        assert "robot-001" in call_args
        assert "robot-002" in call_args
    
    @pytest.mark.asyncio
    async def test_system_show_status(self):
        """測試系統指令：顯示狀態"""
        from unittest.mock import PropertyMock
        
        mock_coordinator = Mock()
        
        # Create mock service info objects with proper status property
        service1 = Mock()
        type(service1).status = PropertyMock(return_value=ServiceStatus.RUNNING)
        service2 = Mock()
        type(service2).status = PropertyMock(return_value=ServiceStatus.RUNNING)
        service3 = Mock()
        type(service3).status = PropertyMock(return_value=ServiceStatus.STOPPED)
        
        mock_coordinator.get_all_services_info.return_value = {
            "service1": service1,
            "service2": service2,
            "service3": service3
        }
        
        app = RobotConsoleTUI(coordinator=mock_coordinator)
        app.notify = Mock()
        
        await app._system_show_status()
        
        app.notify.assert_called_once()
        call_args = app.notify.call_args[0][0]
        assert "System Status" in call_args
        # Check for the count - should be 2/3
        assert "/3" in call_args and "running" in call_args
    
    @pytest.mark.asyncio
    async def test_system_healthcheck(self):
        """測試系統指令：健康檢查"""
        async def mock_healthcheck():
            return {
                "service1": {"status": "healthy"},
                "service2": {"status": "healthy"},
                "service3": {"status": "unhealthy"}
            }
        
        mock_coordinator = Mock()
        mock_coordinator.check_all_services_health = mock_healthcheck
        
        app = RobotConsoleTUI(coordinator=mock_coordinator)
        app.notify = Mock()
        
        await app._system_healthcheck()
        
        app.notify.assert_called_once()
        call_args = app.notify.call_args[0][0]
        assert "Health Check" in call_args
        assert "unhealthy" in call_args


class TestTUIErrorHandling:
    """測試 TUI 錯誤處理"""
    
    @pytest.mark.asyncio
    async def test_service_start_failure(self):
        """測試服務啟動失敗處理"""
        async def mock_start_service(name):
            return False  # 啟動失敗
        
        mock_coordinator = Mock()
        mock_coordinator.start_service = mock_start_service
        
        app = RobotConsoleTUI(coordinator=mock_coordinator)
        app.notify = Mock()
        
        await app._service_single_action("test_service", "start")
        
        # 應顯示失敗通知
        app.notify.assert_called_once()
        call_args = app.notify.call_args[0][0]
        assert "Failed" in call_args or "failed" in call_args
    
    @pytest.mark.asyncio
    async def test_invalid_service_action(self):
        """測試無效的服務動作"""
        mock_coordinator = Mock()
        
        app = RobotConsoleTUI(coordinator=mock_coordinator)
        app.notify = Mock()
        
        # 測試無效動作
        try:
            await app._service_single_action("test_service", "invalid_action")
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "Unknown action" in str(e)
    
    @pytest.mark.asyncio
    async def test_coordinator_not_available(self):
        """測試協調器不可用時的處理"""
        app = RobotConsoleTUI()  # 無協調器
        app.notify = Mock()
        
        # Mock query_one 和 history
        mock_history = Mock()
        app.query_one = Mock(return_value=mock_history)
        
        # 嘗試執行服務指令
        await app._handle_service_command("mcp.start")
        
        # 應顯示錯誤通知
        app.notify.assert_called()
        call_args = app.notify.call_args[0][0]
        assert "not available" in call_args or "Coordinator" in call_args
    
    @pytest.mark.asyncio
    async def test_invalid_command_format(self):
        """測試無效的指令格式"""
        mock_coordinator = Mock()
        app = RobotConsoleTUI(coordinator=mock_coordinator)
        app.notify = Mock()
        
        # Mock query_one 和 history
        mock_history = Mock()
        app.query_one = Mock(return_value=mock_history)
        
        # 測試缺少 '.' 分隔符的服務指令
        await app._handle_service_command("invalid_format")
        
        # 應顯示錯誤通知
        app.notify.assert_called()
        call_args = app.notify.call_args[0][0]
        assert "Invalid" in call_args or "format" in call_args
    
    @pytest.mark.asyncio
    async def test_invalid_cloud_action(self):
        """測試無效的雲端路由動作"""
        app = RobotConsoleTUI()
        app.notify = Mock()
        
        # 測試無效動作
        try:
            await app._handle_queue_cloud("invalid")
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "Invalid cloud action" in str(e)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
