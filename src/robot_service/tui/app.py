"""
Robot Console TUI Application

使用 Textual 建立的終端機互動介面。
"""

import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any

from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import Header, Footer, Static, Input, Label
from textual.binding import Binding
from textual.reactive import reactive

from ..service_coordinator import ServiceCoordinator
from common.service_types import ServiceStatus
from common.shared_state import SharedStateManager, EventTopics
from ..command_history_manager import CommandHistoryManager


class ServiceStatusWidget(Static):
    """服務狀態顯示元件"""
    
    status_text = reactive("")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.services_status: Dict[str, ServiceStatus] = {}
    
    def update_service_status(self, service_name: str, status: ServiceStatus):
        """更新服務狀態"""
        self.services_status[service_name] = status
        self._render_status()
    
    def _render_status(self):
        """渲染服務狀態"""
        lines = ["[bold cyan]Services[/bold cyan]", "─" * 30]
        
        status_icons = {
            ServiceStatus.STOPPED: "○",
            ServiceStatus.STARTING: "◐",
            ServiceStatus.RUNNING: "●",
            ServiceStatus.HEALTHY: "●",
            ServiceStatus.UNHEALTHY: "◍",
            ServiceStatus.STOPPING: "◑",
            ServiceStatus.ERROR: "✗",
        }
        
        status_colors = {
            ServiceStatus.STOPPED: "dim",
            ServiceStatus.STARTING: "yellow",
            ServiceStatus.RUNNING: "green",
            ServiceStatus.HEALTHY: "green",
            ServiceStatus.UNHEALTHY: "yellow",
            ServiceStatus.STOPPING: "yellow",
            ServiceStatus.ERROR: "red",
        }
        
        for service_name, status in self.services_status.items():
            icon = status_icons.get(status, "?")
            color = status_colors.get(status, "white")
            lines.append(f"[{color}]{icon}[/{color}] {service_name:20s} [{color}][{status.value}][/{color}]")
        
        self.status_text = "\n".join(lines)
    
    def render(self) -> str:
        return self.status_text


class RobotStatusWidget(Static):
    """機器人狀態顯示元件"""
    
    status_text = reactive("")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.robots_status: Dict[str, Dict[str, Any]] = {}
    
    def update_robot_status(self, robot_id: str, status: Dict[str, Any]):
        """更新機器人狀態"""
        self.robots_status[robot_id] = status
        self._render_status()
    
    def _render_status(self):
        """渲染機器人狀態"""
        lines = ["[bold cyan]Robot Status[/bold cyan]", "─" * 30]
        
        if not self.robots_status:
            lines.append("[dim]No robots connected[/dim]")
        else:
            for robot_id, status in self.robots_status.items():
                connected = status.get("connected", False)
                icon = "🤖" if connected else "⚠️"
                color = "green" if connected else "red"
                conn_status = "connected" if connected else "disconnected"
                
                lines.append(f"{icon} {robot_id:15s} [{color}][{conn_status}][/{color}]")
                
                if connected:
                    battery = status.get("battery_level", "N/A")
                    mode = status.get("mode", "Unknown")
                    lines.append(f"   Battery: {battery}%")
                    lines.append(f"   Mode: {mode}")
                lines.append("")
        
        self.status_text = "\n".join(lines)
    
    def render(self) -> str:
        return self.status_text


class CommandHistoryWidget(ScrollableContainer):
    """指令歷史顯示元件"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history: List[str] = []
    
    def compose(self) -> ComposeResult:
        """組成元件"""
        yield Static("[bold cyan]Command History[/bold cyan]\n" + "─" * 70, id="history_header")
        yield Static("", id="history_content")
    
    def add_command(self, timestamp: str, robot_id: str, action: str, status: str):
        """新增指令到歷史"""
        color = "green" if status == "success" else "red"
        entry = f"[{timestamp}] {robot_id}: {action} ([{color}]{status}[/{color}])"
        self.history.append(entry)
        
        # 保留最近 20 筆
        if len(self.history) > 20:
            self.history = self.history[-20:]
        
        # 更新顯示
        content_widget = self.query_one("#history_content", Static)
        content_widget.update("\n".join(self.history))


class RobotConsoleTUI(App):
    """
    Robot Console Terminal UI Application
    
    提供終端機互動式介面，顯示：
    - 服務狀態（MCP、Flask、Queue）
    - 機器人狀態（連接狀態、電量、模式）
    - 指令歷史（最近執行的指令）
    - 指令輸入（發送新指令）
    """
    
    CSS = """
    Screen {
        layout: grid;
        grid-size: 2 3;
        grid-rows: 1fr 1fr 2fr;
    }
    
    #services {
        column-span: 1;
        row-span: 2;
        border: solid $primary;
        padding: 1;
    }
    
    #robots {
        column-span: 1;
        row-span: 2;
        border: solid $primary;
        padding: 1;
    }
    
    #history {
        column-span: 2;
        row-span: 1;
        border: solid $primary;
        padding: 1;
        height: 100%;
    }
    
    #input_container {
        column-span: 2;
        height: auto;
        padding: 1;
    }
    
    Input {
        margin: 1 0;
    }
    """
    
    TITLE = "Robot Console Edge - Terminal UI"
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("s", "services", "Services"),
        ("ctrl+c", "quit", "Quit"),
    ]
    
    def __init__(
        self,
        coordinator: Optional[ServiceCoordinator] = None,
        state_manager: Optional[SharedStateManager] = None,
        history_manager: Optional[CommandHistoryManager] = None,
    ):
        super().__init__()
        
        self.coordinator = coordinator
        self.state_manager = state_manager
        self.history_manager = history_manager
        
        # 內部狀態
        self._update_task: Optional[asyncio.Task] = None
        self._running = False
    
    def compose(self) -> ComposeResult:
        """組成 UI 元件"""
        yield Header(show_clock=True)
        
        yield ServiceStatusWidget(id="services")
        yield RobotStatusWidget(id="robots")
        yield CommandHistoryWidget(id="history")
        
        yield Container(
            Label("[bold]Command Input:[/bold]"),
            Input(placeholder="Enter command (e.g., 'go_forward', 'turn_left')"),
            id="input_container"
        )
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """應用啟動時"""
        self._running = True
        
        # 訂閱事件
        if self.state_manager:
            await self.state_manager.subscribe(
                EventTopics.ROBOT_STATUS_UPDATED,
                self._on_robot_status_updated
            )
            await self.state_manager.subscribe(
                EventTopics.COMMAND_COMPLETED,
                self._on_command_completed
            )
        
        # 啟動定期更新任務
        self._update_task = asyncio.create_task(self._periodic_update())
        
        # 初始更新
        await self._refresh_all()
    
    async def on_unmount(self) -> None:
        """應用關閉時"""
        self._running = False
        
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
    
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """處理指令輸入"""
        command = event.value.strip()
        
        if not command:
            return
        
        # 清空輸入
        event.input.value = ""
        
        # 解析指令格式
        robot_id, action = self._parse_command(command)
        
        # TODO: 實作指令發送邏輯
        # 這裡需要整合 CommandProcessor 或直接發送到佇列
        
        # 暫時顯示在歷史中
        history = self.query_one("#history", CommandHistoryWidget)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if robot_id == "all":
            # 廣播指令到所有機器人
            history.add_command(timestamp, "all robots", action, "pending")
        else:
            history.add_command(timestamp, robot_id, action, "pending")
    
    def _parse_command(self, command: str) -> tuple[str, str]:
        """
        解析指令格式
        
        支援格式：
        - action_name -> (robot-001, action_name)
        - robot-002:action_name -> (robot-002, action_name)
        - all:action_name -> (all, action_name)
        
        Args:
            command: 輸入的指令字串
        
        Returns:
            (robot_id, action_name) 元組
        """
        if ":" in command:
            parts = command.split(":", 1)
            robot_id = parts[0].strip()
            action = parts[1].strip()
        else:
            robot_id = "robot-001"  # 預設機器人
            action = command.strip()
        
        return robot_id, action
    
    async def action_refresh(self) -> None:
        """刷新所有狀態"""
        await self._refresh_all()
    
    async def action_services(self) -> None:
        """顯示服務詳細資訊"""
        # TODO: 實作服務詳細資訊彈窗
        pass
    
    async def _periodic_update(self) -> None:
        """定期更新狀態"""
        while self._running:
            try:
                await asyncio.sleep(5.0)
                if self._running:
                    await self._refresh_all()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log(f"Error in periodic update: {e}")
    
    async def _refresh_all(self) -> None:
        """刷新所有元件"""
        await self._refresh_services()
        await self._refresh_robots()
    
    async def _refresh_services(self) -> None:
        """刷新服務狀態"""
        if not self.coordinator:
            return
        
        service_widget = self.query_one("#services", ServiceStatusWidget)
        
        # 更新所有服務狀態
        services_info = self.coordinator.get_all_services_info()
        for service_name, info in services_info.items():
            service_widget.update_service_status(service_name, info.status)
    
    async def _refresh_robots(self) -> None:
        """刷新機器人狀態"""
        if not self.state_manager:
            return
        
        robot_widget = self.query_one("#robots", RobotStatusWidget)
        
        # 從共享狀態取得機器人清單
        # TODO: 實作取得所有機器人的方法
        # 暫時使用範例資料
        robot_widget.update_robot_status("robot-001", {
            "connected": True,
            "battery_level": 85,
            "mode": "Standby"
        })
    
    async def _on_robot_status_updated(self, event: Dict[str, Any]) -> None:
        """處理機器人狀態更新事件"""
        robot_id = event.get("data", {}).get("robot_id")
        status = event.get("data", {}).get("status", {})
        
        if robot_id and status:
            robot_widget = self.query_one("#robots", RobotStatusWidget)
            robot_widget.update_robot_status(robot_id, status)
    
    async def _on_command_completed(self, event: Dict[str, Any]) -> None:
        """處理指令完成事件"""
        data = event.get("data", {})
        robot_id = data.get("robot_id", "unknown")
        action = data.get("action", "unknown")
        status = data.get("status", "unknown")
        timestamp = data.get("timestamp", datetime.now().strftime("%H:%M:%S"))
        
        history = self.query_one("#history", CommandHistoryWidget)
        history.add_command(timestamp, robot_id, action, status)
