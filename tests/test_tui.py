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
from common.service_types import ServiceStatus


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
        """測試廣播指令解析"""
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
