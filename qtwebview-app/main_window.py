#!/usr/bin/env python3
"""
Hybrid Main Window - Approach B
結合原生 Qt Widgets 與 QWebEngineView 的混合架構
"""

import logging
from typing import Optional

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QStackedWidget, QListWidget, QListWidgetItem,
    QLabel, QMessageBox, QStatusBar, QToolBar
)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage

logger = logging.getLogger(__name__)


class WebEnginePage(QWebEnginePage):
    """自訂 WebEnginePage 以處理 console 訊息"""

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        """記錄 JavaScript console 訊息"""
        logger.debug(f"JS Console [{source_id}:{line_number}]: {message}")


class NavigationWidget(QWidget):
    """原生導航側邊欄"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 導航列表
        self.nav_list = QListWidget()
        self.nav_list.setMaximumWidth(200)
        
        # 添加導航項目
        self._add_nav_item("🏠 儀表板", "dashboard")
        self._add_nav_item("🤖 機器人控制", "robot_control")
        self._add_nav_item("📝 指令歷史", "command_history")
        self._add_nav_item("🔧 固件更新", "firmware_update")
        self._add_nav_item("⚙️ 設定", "settings")
        
        layout.addWidget(self.nav_list)
        
        # 設定樣式
        self.setStyleSheet("""
            QListWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                border: none;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #3a3a3a;
            }
            QListWidget::item:selected {
                background-color: #0d7377;
            }
            QListWidget::item:hover {
                background-color: #323232;
            }
        """)
    
    def _add_nav_item(self, text: str, data: str):
        """添加導航項目"""
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, data)
        self.nav_list.addItem(item)


class DashboardWidget(QWidget):
    """儀表板 Widget（原生實作）"""
    
    def __init__(self, backend_manager, parent=None):
        super().__init__(parent)
        self.backend_manager = backend_manager
        self._init_ui()
        self._load_data()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        
        # 標題
        title = QLabel("📊 系統儀表板")
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px;")
        layout.addWidget(title)
        
        # 系統狀態區域
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        
        # 後端狀態
        self.backend_status = QLabel("後端: 連接中...")
        self.backend_status.setStyleSheet(
            "font-size: 14px; padding: 10px; background-color: #fff3cd; "
            "border-radius: 5px; color: #856404;"
        )
        status_layout.addWidget(self.backend_status)
        
        # 機器人數量
        self.robot_count_label = QLabel("機器人: 0 台")
        self.robot_count_label.setStyleSheet(
            "font-size: 14px; padding: 10px; background-color: #d1ecf1; "
            "border-radius: 5px; color: #0c5460;"
        )
        status_layout.addWidget(self.robot_count_label)
        
        # 最近指令
        self.command_count_label = QLabel("指令: 0 條")
        self.command_count_label.setStyleSheet(
            "font-size: 14px; padding: 10px; background-color: #d4edda; "
            "border-radius: 5px; color: #155724;"
        )
        status_layout.addWidget(self.command_count_label)
        
        status_layout.addStretch()
        layout.addWidget(status_container)
        
        # 快速操作區域
        quick_actions = QWidget()
        quick_layout = QHBoxLayout(quick_actions)
        
        from PyQt6.QtWidgets import QPushButton
        refresh_btn = QPushButton("🔄 重新整理")
        refresh_btn.clicked.connect(self._load_data)
        refresh_btn.setStyleSheet(
            "QPushButton { padding: 10px 20px; font-size: 14px; "
            "background-color: #0d7377; color: white; border: none; "
            "border-radius: 5px; }"
            "QPushButton:hover { background-color: #14a0a6; }"
        )
        quick_layout.addWidget(refresh_btn)
        quick_layout.addStretch()
        
        layout.addWidget(quick_actions)
        
        # 最近活動列表
        activity_label = QLabel("📋 最近活動")
        activity_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 15px 10px;")
        layout.addWidget(activity_label)
        
        from PyQt6.QtWidgets import QListWidget
        self.activity_list = QListWidget()
        self.activity_list.setStyleSheet(
            "QListWidget { border: 1px solid #dee2e6; border-radius: 5px; "
            "font-size: 13px; } "
            "QListWidget::item { padding: 10px; border-bottom: 1px solid #e9ecef; }"
        )
        layout.addWidget(self.activity_list)
        
        layout.addStretch()
    
    def _load_data(self):
        """載入儀表板數據"""
        try:
            flask_url = self.backend_manager.get_service_url('flask')
            if flask_url:
                self.backend_status.setText(f"後端: 運行中 ({flask_url})")
                self.backend_status.setStyleSheet(
                    "font-size: 14px; padding: 10px; background-color: #d4edda; "
                    "border-radius: 5px; color: #155724;"
                )
                
                # TODO: 實際從 API 載入數據
                # import requests
                # response = requests.get(f"{flask_url}/api/health")
                # data = response.json()
                
                # 模擬數據
                self.robot_count_label.setText("機器人: 3 台")
                self.command_count_label.setText("指令: 12 條")
                
                # 添加活動項目
                self.activity_list.clear()
                activities = [
                    "✅ 機器人 #1 已連接",
                    "📤 指令已發送到機器人 #2",
                    "🔄 系統狀態更新",
                    "✅ 固件檢查完成",
                ]
                for activity in activities:
                    self.activity_list.addItem(activity)
            else:
                self.backend_status.setText("後端: 未啟動")
                self.backend_status.setStyleSheet(
                    "font-size: 14px; padding: 10px; background-color: #f8d7da; "
                    "border-radius: 5px; color: #721c24;"
                )
        except Exception as e:
            logger.error(f"載入儀表板數據失敗: {e}")
            self.backend_status.setText(f"後端: 錯誤 - {str(e)[:30]}")
    
    def refresh(self):
        """公開方法：刷新數據"""
        self._load_data()


class RobotControlWidget(QWidget):
    """機器人控制 Widget（原生實作）"""
    
    def __init__(self, backend_manager, parent=None):
        super().__init__(parent)
        self.backend_manager = backend_manager
        self.selected_robot = None
        self._init_ui()
        self._load_robots()
    
    def _init_ui(self):
        """初始化 UI"""
        from PyQt6.QtWidgets import QSplitter, QGroupBox, QPushButton, QTextEdit, QLineEdit
        
        layout = QVBoxLayout(self)
        
        # 標題
        title = QLabel("🤖 機器人控制")
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px;")
        layout.addWidget(title)
        
        # 分割器：機器人列表 | 控制面板
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左側：機器人列表
        robot_list_container = QWidget()
        robot_list_layout = QVBoxLayout(robot_list_container)
        
        robot_list_title = QLabel("📋 機器人列表")
        robot_list_title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        robot_list_layout.addWidget(robot_list_title)
        
        from PyQt6.QtWidgets import QListWidget
        self.robot_list = QListWidget()
        self.robot_list.itemClicked.connect(self._on_robot_selected)
        self.robot_list.setStyleSheet(
            "QListWidget { border: 1px solid #dee2e6; border-radius: 5px; }"
            "QListWidget::item { padding: 10px; }"
            "QListWidget::item:selected { background-color: #0d7377; color: white; }"
        )
        robot_list_layout.addWidget(self.robot_list)
        
        refresh_btn = QPushButton("🔄 重新整理")
        refresh_btn.clicked.connect(self._load_robots)
        robot_list_layout.addWidget(refresh_btn)
        
        splitter.addWidget(robot_list_container)
        
        # 右側：控制面板
        control_panel_container = QWidget()
        control_panel_layout = QVBoxLayout(control_panel_container)
        
        # 機器人資訊
        info_group = QGroupBox("📊 機器人資訊")
        info_layout = QVBoxLayout(info_group)
        self.robot_info_label = QLabel("請選擇一個機器人")
        self.robot_info_label.setStyleSheet("padding: 10px; font-size: 14px;")
        info_layout.addWidget(self.robot_info_label)
        control_panel_layout.addWidget(info_group)
        
        # 指令輸入
        command_group = QGroupBox("⌨️ 指令輸入")
        command_layout = QVBoxLayout(command_group)
        
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("輸入指令...")
        self.command_input.setStyleSheet("padding: 8px; font-size: 14px;")
        command_layout.addWidget(self.command_input)
        
        send_btn = QPushButton("📤 發送指令")
        send_btn.clicked.connect(self._send_command)
        send_btn.setStyleSheet(
            "QPushButton { padding: 10px; font-size: 14px; "
            "background-color: #0d7377; color: white; border: none; border-radius: 5px; }"
            "QPushButton:hover { background-color: #14a0a6; }"
        )
        command_layout.addWidget(send_btn)
        
        control_panel_layout.addWidget(command_group)
        
        # 快速控制按鈕
        quick_control_group = QGroupBox("🎮 快速控制")
        quick_control_layout = QVBoxLayout(quick_control_group)
        
        from PyQt6.QtWidgets import QGridLayout
        button_grid = QGridLayout()
        
        quick_commands = [
            ("▶️ 前進", "move_forward"),
            ("◀️ 後退", "move_backward"),
            ("⏸️ 停止", "stop"),
            ("🔄 旋轉", "rotate"),
        ]
        
        for i, (text, cmd) in enumerate(quick_commands):
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked, c=cmd: self._quick_command(c))
            btn.setStyleSheet("padding: 10px; font-size: 13px;")
            button_grid.addWidget(btn, i // 2, i % 2)
        
        quick_control_layout.addLayout(button_grid)
        control_panel_layout.addWidget(quick_control_group)
        
        # 回應顯示
        response_group = QGroupBox("📝 執行結果")
        response_layout = QVBoxLayout(response_group)
        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        self.response_text.setStyleSheet("font-family: monospace; font-size: 12px;")
        self.response_text.setMaximumHeight(150)
        response_layout.addWidget(self.response_text)
        control_panel_layout.addWidget(response_group)
        
        control_panel_layout.addStretch()
        splitter.addWidget(control_panel_container)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)
    
    def _load_robots(self):
        """載入機器人列表"""
        try:
            self.robot_list.clear()
            
            # TODO: 從 API 載入實際機器人列表
            # flask_url = self.backend_manager.get_service_url('flask')
            # response = requests.get(f"{flask_url}/robots")
            # robots = response.json()
            
            # 模擬數據
            robots = [
                {"id": 1, "name": "Robot-01", "status": "online"},
                {"id": 2, "name": "Robot-02", "status": "offline"},
                {"id": 3, "name": "Robot-03", "status": "online"},
            ]
            
            for robot in robots:
                status_icon = "🟢" if robot["status"] == "online" else "🔴"
                item_text = f"{status_icon} {robot['name']}"
                from PyQt6.QtWidgets import QListWidgetItem
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, robot)
                self.robot_list.addItem(item)
            
            self.response_text.append(f"✅ 已載入 {len(robots)} 個機器人")
        except Exception as e:
            logger.error(f"載入機器人列表失敗: {e}")
            self.response_text.append(f"❌ 載入失敗: {e}")
    
    def _on_robot_selected(self, item):
        """機器人選擇處理"""
        robot = item.data(Qt.ItemDataRole.UserRole)
        self.selected_robot = robot
        
        status_icon = "🟢" if robot["status"] == "online" else "🔴"
        info_text = (
            f"ID: {robot['id']}\n"
            f"名稱: {robot['name']}\n"
            f"狀態: {status_icon} {robot['status']}"
        )
        self.robot_info_label.setText(info_text)
        self.response_text.append(f"✓ 已選擇: {robot['name']}")
    
    def _send_command(self):
        """發送自訂指令"""
        if not self.selected_robot:
            self.response_text.append("⚠️ 請先選擇一個機器人")
            return
        
        command = self.command_input.text().strip()
        if not command:
            self.response_text.append("⚠️ 請輸入指令")
            return
        
        try:
            # TODO: 實際發送指令到後端
            # flask_url = self.backend_manager.get_service_url('flask')
            # response = requests.post(
            #     f"{flask_url}/command",
            #     json={"robot_id": self.selected_robot["id"], "command": command}
            # )
            
            self.response_text.append(
                f"📤 發送指令到 {self.selected_robot['name']}: {command}"
            )
            self.response_text.append("✅ 指令已發送（模擬）")
            self.command_input.clear()
        except Exception as e:
            logger.error(f"發送指令失敗: {e}")
            self.response_text.append(f"❌ 發送失敗: {e}")
    
    def _quick_command(self, command):
        """快速指令"""
        if not self.selected_robot:
            self.response_text.append("⚠️ 請先選擇一個機器人")
            return
        
        self.response_text.append(
            f"🎮 快速指令: {command} → {self.selected_robot['name']}"
        )
        # TODO: 實際執行快速指令
        
    def refresh(self):
        """公開方法：刷新數據"""
        self._load_robots()


class CommandHistoryWidget(QWidget):
    """指令歷史 Widget（原生實作）"""
    
    def __init__(self, backend_manager, parent=None):
        super().__init__(parent)
        self.backend_manager = backend_manager
        self._init_ui()
        self._load_history()
    
    def _init_ui(self):
        """初始化 UI"""
        from PyQt6.QtWidgets import (QTableWidget, QTableWidgetItem, QPushButton,
                                     QLineEdit, QComboBox, QHeaderView)
        
        layout = QVBoxLayout(self)
        
        # 標題
        title = QLabel("📝 指令歷史")
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px;")
        layout.addWidget(title)
        
        # 篩選器
        filter_container = QWidget()
        filter_layout = QHBoxLayout(filter_container)
        
        # 搜尋框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜尋指令...")
        self.search_input.textChanged.connect(self._filter_history)
        filter_layout.addWidget(QLabel("🔍"))
        filter_layout.addWidget(self.search_input)
        
        # 狀態篩選
        self.status_filter = QComboBox()
        self.status_filter.addItems(["全部", "成功", "失敗", "執行中"])
        self.status_filter.currentTextChanged.connect(self._filter_history)
        filter_layout.addWidget(QLabel("狀態:"))
        filter_layout.addWidget(self.status_filter)
        
        # 重新整理按鈕
        refresh_btn = QPushButton("🔄 重新整理")
        refresh_btn.clicked.connect(self._load_history)
        filter_layout.addWidget(refresh_btn)
        
        filter_layout.addStretch()
        layout.addWidget(filter_container)
        
        # 指令表格
        self.command_table = QTableWidget()
        self.command_table.setColumnCount(6)
        self.command_table.setHorizontalHeaderLabels([
            "ID", "時間", "機器人", "指令", "狀態", "結果"
        ])
        
        # 設定表格樣式
        self.command_table.setStyleSheet(
            "QTableWidget { border: 1px solid #dee2e6; border-radius: 5px; "
            "gridline-color: #e9ecef; } "
            "QHeaderView::section { background-color: #f8f9fa; padding: 8px; "
            "font-weight: bold; border: none; }"
        )
        
        # 設定列寬
        header = self.command_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        
        self.command_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.command_table.itemClicked.connect(self._on_command_selected)
        
        layout.addWidget(self.command_table)
        
        # 詳細資訊面板
        from PyQt6.QtWidgets import QTextEdit
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setPlaceholderText("選擇一條指令查看詳細資訊")
        self.detail_text.setStyleSheet("font-family: monospace; font-size: 12px;")
        self.detail_text.setMaximumHeight(150)
        layout.addWidget(self.detail_text)
    
    def _load_history(self):
        """載入指令歷史"""
        try:
            # TODO: 從 API 載入實際歷史
            # flask_url = self.backend_manager.get_service_url('flask')
            # response = requests.get(f"{flask_url}/commands")
            # commands = response.json()
            
            # 模擬數據
            from datetime import datetime, timedelta
            commands = []
            for i in range(20):
                time_ago = datetime.now() - timedelta(minutes=i*5)
                commands.append({
                    "id": 100 + i,
                    "timestamp": time_ago.strftime("%Y-%m-%d %H:%M:%S"),
                    "robot": f"Robot-0{(i % 3) + 1}",
                    "command": f"move_forward {i*10}",
                    "status": ["success", "failed", "running"][i % 3],
                    "result": f"執行時間: {i}秒"
                })
            
            self.all_commands = commands
            self._display_commands(commands)
            
        except Exception as e:
            logger.error(f"載入指令歷史失敗: {e}")
            self.detail_text.append(f"❌ 載入失敗: {e}")
    
    def _display_commands(self, commands):
        """顯示指令列表"""
        from PyQt6.QtWidgets import QTableWidgetItem
        
        self.command_table.setRowCount(len(commands))
        
        for row, cmd in enumerate(commands):
            # ID
            self.command_table.setItem(row, 0, QTableWidgetItem(str(cmd["id"])))
            
            # 時間
            self.command_table.setItem(row, 1, QTableWidgetItem(cmd["timestamp"]))
            
            # 機器人
            self.command_table.setItem(row, 2, QTableWidgetItem(cmd["robot"]))
            
            # 指令
            self.command_table.setItem(row, 3, QTableWidgetItem(cmd["command"]))
            
            # 狀態
            status_text = {
                "success": "✅ 成功",
                "failed": "❌ 失敗",
                "running": "🔄 執行中"
            }.get(cmd["status"], cmd["status"])
            status_item = QTableWidgetItem(status_text)
            
            # 設定狀態顏色
            if cmd["status"] == "success":
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            elif cmd["status"] == "failed":
                status_item.setForeground(Qt.GlobalColor.red)
            else:
                status_item.setForeground(Qt.GlobalColor.blue)
            
            self.command_table.setItem(row, 4, status_item)
            
            # 結果
            self.command_table.setItem(row, 5, QTableWidgetItem(cmd["result"]))
            
            # 儲存完整數據
            for col in range(6):
                item = self.command_table.item(row, col)
                if item:
                    item.setData(Qt.ItemDataRole.UserRole, cmd)
    
    def _filter_history(self):
        """篩選歷史記錄"""
        if not hasattr(self, 'all_commands'):
            return
        
        search_text = self.search_input.text().lower()
        status_filter = self.status_filter.currentText()
        
        filtered = []
        for cmd in self.all_commands:
            # 狀態篩選
            if status_filter != "全部":
                status_map = {"成功": "success", "失敗": "failed", "執行中": "running"}
                if cmd["status"] != status_map.get(status_filter, status_filter):
                    continue
            
            # 文字搜尋
            if search_text and search_text not in cmd["command"].lower():
                continue
            
            filtered.append(cmd)
        
        self._display_commands(filtered)
    
    def _on_command_selected(self, item):
        """指令選擇處理"""
        cmd = item.data(Qt.ItemDataRole.UserRole)
        if cmd:
            detail_text = f"""
📋 指令詳細資訊
═══════════════════════════════════════
ID: {cmd['id']}
時間: {cmd['timestamp']}
機器人: {cmd['robot']}
指令: {cmd['command']}
狀態: {cmd['status']}
結果: {cmd['result']}
═══════════════════════════════════════
"""
            self.detail_text.setPlainText(detail_text)
    
    def refresh(self):
        """公開方法：刷新數據"""
        self._load_history()


class FirmwareUpdateWidget(QWidget):
    """固件更新 Widget（原生實作 - 安全性優先）"""
    
    def __init__(self, backend_manager, parent=None):
        super().__init__(parent)
        self.backend_manager = backend_manager
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        
        # 標題
        title = QLabel("🔧 固件更新")
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px;")
        layout.addWidget(title)
        
        # 安全提示
        security_notice = QLabel(
            "⚠️ 固件更新需要連接到機器人的 WiFi AP\n"
            "請確保已從雲端下載加密的配置檔案"
        )
        security_notice.setStyleSheet(
            "background-color: #fff3cd; color: #856404; "
            "padding: 15px; border-radius: 5px; font-size: 14px;"
        )
        layout.addWidget(security_notice)
        
        # TODO: 添加固件更新元件
        # - WiFi AP 連接管理
        # - 加密檔案上傳
        # - 固件選擇與上傳
        # - 進度顯示
        # - 安全驗證流程
        
        layout.addStretch()


class SettingsWidget(QWidget):
    """設定 Widget（使用 WebView 載入 Flask UI）"""
    
    def __init__(self, backend_manager, parent=None):
        super().__init__(parent)
        self.backend_manager = backend_manager
        self.webview: Optional[QWebEngineView] = None
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 使用 WebView 載入複雜設定介面
        self.webview = QWebEngineView()
        page = WebEnginePage(self.webview)
        self.webview.setPage(page)
        
        layout.addWidget(self.webview)
        
        # 載入設定頁面
        self._load_settings_page()
    
    def _load_settings_page(self):
        """載入設定頁面"""
        try:
            flask_url = self.backend_manager.get_service_url('flask')
            if flask_url:
                # 載入設定路由（如果有的話）
                settings_url = f"{flask_url}/admin"  # 或其他設定路由
                self.webview.load(QUrl(settings_url))
        except Exception as e:
            logger.error(f"載入設定頁面失敗: {e}")


class HybridMainWindow(QMainWindow):
    """混合架構主視窗 - Approach B"""
    
    def __init__(self, backend_manager, parent=None):
        super().__init__(parent)
        self.backend_manager = backend_manager
        self.navigation: Optional[NavigationWidget] = None
        self.content_stack: Optional[QStackedWidget] = None
        
        self._init_ui()
        self._connect_signals()
        self._select_default_page()
    
    def _init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("Robot Command Console - Tiny")
        self.resize(1400, 900)
        
        # 建立工具欄
        self._create_toolbar()
        
        # 建立中央 Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主佈局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 建立分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左側：導航欄
        self.navigation = NavigationWidget()
        splitter.addWidget(self.navigation)
        
        # 右側：內容區域
        self.content_stack = QStackedWidget()
        
        # 添加頁面
        self.content_stack.addWidget(DashboardWidget(self.backend_manager))
        self.content_stack.addWidget(RobotControlWidget(self.backend_manager))
        self.content_stack.addWidget(CommandHistoryWidget(self.backend_manager))
        self.content_stack.addWidget(FirmwareUpdateWidget(self.backend_manager))
        self.content_stack.addWidget(SettingsWidget(self.backend_manager))
        
        splitter.addWidget(self.content_stack)
        
        # 設定分割器比例
        splitter.setStretchFactor(0, 0)  # 導航欄固定寬度
        splitter.setStretchFactor(1, 1)  # 內容區域可伸縮
        
        main_layout.addWidget(splitter)
        
        # 建立狀態欄
        self._create_statusbar()
        
        # 設定主題
        self._apply_theme()
    
    def _create_toolbar(self):
        """建立工具欄"""
        toolbar = QToolBar("主工具欄")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # 添加動作
        refresh_action = QAction("🔄 重新整理", self)
        refresh_action.triggered.connect(self._refresh_current_page)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        # TODO: 添加更多工具欄動作
    
    def _create_statusbar(self):
        """建立狀態欄"""
        statusbar = QStatusBar()
        self.setStatusBar(statusbar)
        
        # 顯示後端狀態
        try:
            flask_url = self.backend_manager.get_service_url('flask')
            statusbar.showMessage(f"後端服務: {flask_url or '未啟動'}")
        except Exception as e:
            statusbar.showMessage(f"後端狀態: 錯誤 - {e}")
    
    def _connect_signals(self):
        """連接信號"""
        if self.navigation:
            self.navigation.nav_list.currentRowChanged.connect(
                self._on_navigation_changed
            )
    
    def _select_default_page(self):
        """選擇預設頁面"""
        if self.navigation:
            self.navigation.nav_list.setCurrentRow(0)  # 預設選擇儀表板
    
    def _on_navigation_changed(self, index: int):
        """導航變更處理"""
        if self.content_stack and 0 <= index < self.content_stack.count():
            self.content_stack.setCurrentIndex(index)
            
            # 更新狀態欄
            nav_item = self.navigation.nav_list.item(index)
            if nav_item:
                page_name = nav_item.text().split(' ', 1)[1] if ' ' in nav_item.text() else nav_item.text()
                self.statusBar().showMessage(f"當前頁面: {page_name}")
    
    def _refresh_current_page(self):
        """重新整理當前頁面"""
        current_widget = self.content_stack.currentWidget()
        
        # 如果是 WebView，重新載入
        if isinstance(current_widget, SettingsWidget) and current_widget.webview:
            current_widget.webview.reload()
            self.statusBar().showMessage("頁面已重新載入", 3000)
        # 如果是原生 Widget 且有 refresh 方法，調用它
        elif hasattr(current_widget, 'refresh') and callable(current_widget.refresh):
            current_widget.refresh()
            self.statusBar().showMessage("數據已更新", 3000)
        else:
            self.statusBar().showMessage("當前頁面無需更新", 3000)
    
    def _apply_theme(self):
        """套用主題"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
            QStatusBar {
                background-color: #f8f9fa;
                border-top: 1px solid #dee2e6;
            }
            QToolBar {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
                padding: 5px;
            }
        """)
    
    def closeEvent(self, event):
        """視窗關閉事件"""
        reply = QMessageBox.question(
            self,
            '確認關閉',
            '確定要關閉應用程式嗎？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            logger.info("使用者確認關閉應用程式")
            event.accept()
        else:
            event.ignore()
