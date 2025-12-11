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
        
        # 處理系統指令
        if robot_id == "system":
            await self._handle_system_command(action)
            return
        
        # 處理服務管理指令
        if robot_id == "service":
            await self._handle_service_command(action)
            return
        
        # TODO: 實作指令發送邏輯
        # 這裡需要整合 CommandProcessor 或直接發送到佇列
        
        # 暫時顯示在歷史中
        history = self.query_one("#history", CommandHistoryWidget)
        timestamp = datetime.now().strftime("%H:%M:%S")
        history.add_command(timestamp, robot_id, action, "pending")
    
    def _parse_command(self, command: str) -> tuple[str, str]:
        """
        解析指令格式
        
        支援格式：
        - action_name -> (robot-001, action_name)
        - robot-002:action_name -> (robot-002, action_name)
        - system:command -> (system, command)
        - service:service_name.action -> (service, service_name.action)
        - service:all.action -> (service, all.action) - 控制所有微服務
        
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
    
    async def _handle_service_command(self, command: str) -> None:
        """
        處理服務管理指令
        
        支援格式：
        - service_name.action (例如: mcp.start, queue.stop)
        - all.start/stop/healthcheck - 控制所有微服務
        - queue.cloud.on/off - 雲端路由控制
        - llm.provider["name"] - 設定 LLM 提供商
        
        支援動作：
        - start: 啟動服務
        - stop: 停止服務
        - restart: 重啟服務
        - healthcheck: 健康檢查
        
        Args:
            command: 服務管理指令
        """
        history = self.query_one("#history", CommandHistoryWidget)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 解析服務名稱和動作
        if "." not in command:
            history.add_command(timestamp, "service", command, "error")
            self.notify("Invalid service command format. Use: service:name.action", severity="error")
            return
        
        parts = command.split(".", 1)
        service_name = parts[0].strip()
        remaining = parts[1].strip()
        
        if not self.coordinator:
            history.add_command(timestamp, f"service:{service_name}", remaining, "error")
            self.notify("Coordinator not available", severity="error")
            return
        
        # 執行服務動作
        try:
            # 處理 all.action - 控制所有微服務
            if service_name == "all":
                await self._service_all_action(remaining)
                history.add_command(timestamp, "service:all", remaining, "success")
            
            # 處理 queue.cloud.on/off
            elif service_name == "queue" and remaining.startswith("cloud."):
                action = remaining.split(".", 1)[1] if "." in remaining else remaining
                await self._handle_queue_cloud(action)
                history.add_command(timestamp, "service:queue.cloud", action, "success")
            
            # 處理 llm.provider["name"]
            elif service_name == "llm" and remaining.startswith("provider["):
                # 解析 provider["name"]
                provider_name = self._parse_bracket_notation(remaining)
                if provider_name:
                    await self._handle_llm_provider(provider_name)
                    history.add_command(timestamp, "service:llm.provider", provider_name, "success")
                else:
                    raise ValueError("Invalid provider notation. Use: provider[\"name\"]")
            
            # 一般服務動作
            else:
                await self._service_single_action(service_name, remaining)
                history.add_command(timestamp, f"service:{service_name}", remaining, "success")
        
        except Exception as e:
            history.add_command(timestamp, f"service:{service_name}", remaining, "error")
            self.notify(f"Service command failed: {e}", severity="error")
    
    def _parse_bracket_notation(self, text: str) -> Optional[str]:
        """
        解析方括號標記法 provider["name"]
        
        Args:
            text: 包含方括號的文字
        
        Returns:
            提取的值，如果格式錯誤則返回 None
        """
        import re
        match = re.search(r'provider\[\"([^\"]+)\"\]', text)
        if match:
            return match.group(1)
        match = re.search(r"provider\['([^']+)'\]", text)
        if match:
            return match.group(1)
        return None
    
    async def _handle_queue_cloud(self, action: str) -> None:
        """
        處理佇列雲端路由控制
        
        Args:
            action: on 或 off
        """
        if action not in ["on", "off"]:
            raise ValueError(f"Invalid cloud action: {action}. Use 'on' or 'off'")
        
        enabled = (action == "on")
        
        # TODO: 實作實際的雲端路由控制
        # 這裡需要與 OfflineQueueService 或 NetworkMonitor 整合
        
        if enabled:
            self.notify("Cloud routing enabled - forcing internet routing", severity="information")
        else:
            self.notify("Cloud routing disabled - using local-only mode", severity="information")
    
    async def _handle_llm_provider(self, provider_name: str) -> None:
        """
        設定 LLM 提供商
        
        Args:
            provider_name: 提供商名稱 (例如: ollama, lmstudio)
        """
        # TODO: 實作實際的 LLM 提供商設定
        # 這裡需要與 LLMProviderManager 整合
        
        valid_providers = ["ollama", "lmstudio", "openai", "anthropic"]
        if provider_name.lower() not in valid_providers:
            self.notify(
                f"Unknown provider '{provider_name}'. Valid: {', '.join(valid_providers)}",
                severity="warning"
            )
            return
        
        self.notify(f"LLM provider set to: {provider_name}", severity="information")
    
    async def _service_single_action(self, service_name: str, action: str) -> None:
        """
        對單一服務執行動作
        
        Args:
            service_name: 服務名稱
            action: 動作名稱 (start/stop/restart/healthcheck)
        """
        if action == "start":
            success = await self.coordinator.start_service(service_name)
            if success:
                self.notify(f"Service '{service_name}' started", severity="information")
            else:
                self.notify(f"Failed to start service '{service_name}'", severity="error")
        
        elif action == "stop":
            success = await self.coordinator.stop_service(service_name)
            if success:
                self.notify(f"Service '{service_name}' stopped", severity="information")
            else:
                self.notify(f"Failed to stop service '{service_name}'", severity="error")
        
        elif action == "restart":
            # 先停止再啟動
            stop_success = await self.coordinator.stop_service(service_name)
            if stop_success:
                start_success = await self.coordinator.start_service(service_name)
                if start_success:
                    self.notify(f"Service '{service_name}' restarted", severity="information")
                else:
                    self.notify(f"Failed to restart service '{service_name}'", severity="error")
            else:
                self.notify(f"Failed to stop service '{service_name}' for restart", severity="error")
        
        elif action == "healthcheck":
            result = await self.coordinator.check_service_health(service_name)
            status = result.get("status", "unknown")
            if status == "healthy":
                self.notify(f"Service '{service_name}' is healthy", severity="information")
            else:
                self.notify(f"Service '{service_name}' is {status}", severity="warning")
        
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _service_all_action(self, action: str) -> None:
        """
        對所有服務執行動作
        
        Args:
            action: 動作名稱 (start/stop/healthcheck)
        """
        services_info = self.coordinator.get_all_services_info()
        service_names = list(services_info.keys())
        
        if action == "start":
            success = await self.coordinator.start()
            if success:
                self.notify(f"All services started ({len(service_names)} services)", severity="information")
            else:
                self.notify("Failed to start all services", severity="error")
        
        elif action == "stop":
            await self.coordinator.stop()
            self.notify(f"All services stopped ({len(service_names)} services)", severity="information")
        
        elif action == "healthcheck":
            results = await self.coordinator.check_all_services_health()
            healthy = sum(1 for r in results.values() if r.get("status") == "healthy")
            total = len(results)
            if healthy == total:
                self.notify(f"All services healthy ({healthy}/{total})", severity="information")
            else:
                unhealthy = total - healthy
                self.notify(f"{unhealthy} service(s) unhealthy ({healthy}/{total})", severity="warning")
        
        else:
            raise ValueError(f"Action '{action}' not supported for all services")
    
    async def _handle_system_command(self, command: str) -> None:
        """
        處理系統指令
        
        支援指令：
        - list: 列出所有機器人
        - show: 顯示系統狀態
        - healthcheck: 執行健康檢查
        
        Args:
            command: 系統指令名稱
        """
        history = self.query_one("#history", CommandHistoryWidget)
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if command == "list":
            # 列出所有機器人
            await self._system_list_robots()
            history.add_command(timestamp, "system", "list", "success")
        
        elif command == "show":
            # 顯示系統狀態
            await self._system_show_status()
            history.add_command(timestamp, "system", "show", "success")
        
        elif command == "healthcheck":
            # 執行健康檢查
            await self._system_healthcheck()
            history.add_command(timestamp, "system", "healthcheck", "success")
        
        else:
            # 未知的系統指令
            history.add_command(timestamp, "system", command, "error")
    
    async def _system_list_robots(self) -> None:
        """系統指令：列出所有機器人"""
        robot_widget = self.query_one("#robots", RobotStatusWidget)
        
        # 取得所有機器人資訊
        robots = list(robot_widget.robots_status.keys())
        
        if not robots:
            self.notify("No robots connected", severity="warning")
            return
        
        # 顯示機器人清單
        robot_list = "\n".join([f"  • {robot_id}" for robot_id in robots])
        self.notify(f"Connected Robots ({len(robots)}):\n{robot_list}", severity="information")
    
    async def _system_show_status(self) -> None:
        """系統指令：顯示系統狀態"""
        if not self.coordinator:
            self.notify("Coordinator not available", severity="error")
            return
        
        # 取得服務資訊
        services_info = self.coordinator.get_all_services_info()
        
        # 統計服務狀態
        running = sum(1 for info in services_info.values() if info.status == ServiceStatus.RUNNING)
        total = len(services_info)
        
        # 顯示系統狀態
        status_msg = f"System Status:\n  Services: {running}/{total} running"
        self.notify(status_msg, severity="information")
    
    async def _system_healthcheck(self) -> None:
        """系統指令：執行健康檢查"""
        if not self.coordinator:
            self.notify("Coordinator not available", severity="error")
            return
        
        # 執行健康檢查
        results = await self.coordinator.check_all_services_health()
        
        # 統計結果
        healthy = sum(1 for r in results.values() if r.get("status") == "healthy")
        total = len(results)
        
        # 顯示結果
        if healthy == total:
            self.notify(f"Health Check: All services healthy ({healthy}/{total})", severity="information")
        else:
            unhealthy = total - healthy
            self.notify(
                f"Health Check: {unhealthy} service(s) unhealthy ({healthy}/{total})",
                severity="warning"
            )
    
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
