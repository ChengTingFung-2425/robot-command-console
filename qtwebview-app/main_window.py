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
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        
        # 標題
        title = QLabel("📊 系統儀表板")
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px;")
        layout.addWidget(title)
        
        # 系統狀態
        status_label = QLabel("系統狀態: 運行中")
        status_label.setStyleSheet("font-size: 16px; padding: 10px; color: #0d7377;")
        layout.addWidget(status_label)
        
        # TODO: 添加更多儀表板元件
        # - 機器人狀態卡片
        # - 最近指令
        # - 系統資源使用率
        
        layout.addStretch()


class RobotControlWidget(QWidget):
    """機器人控制 Widget（原生實作）"""
    
    def __init__(self, backend_manager, parent=None):
        super().__init__(parent)
        self.backend_manager = backend_manager
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        
        # 標題
        title = QLabel("🤖 機器人控制")
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px;")
        layout.addWidget(title)
        
        # TODO: 添加控制元件
        # - 機器人列表
        # - 控制按鈕
        # - 狀態顯示
        
        layout.addStretch()


class CommandHistoryWidget(QWidget):
    """指令歷史 Widget（原生實作）"""
    
    def __init__(self, backend_manager, parent=None):
        super().__init__(parent)
        self.backend_manager = backend_manager
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        
        # 標題
        title = QLabel("📝 指令歷史")
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 20px;")
        layout.addWidget(title)
        
        # TODO: 添加歷史記錄元件
        # - 指令列表
        # - 篩選器
        # - 詳細資訊
        
        layout.addStretch()


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
        else:
            # TODO: 刷新原生 Widget 的數據
            self.statusBar().showMessage("數據已更新", 3000)
    
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
