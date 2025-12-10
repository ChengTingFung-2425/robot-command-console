#!/usr/bin/env python3
"""
WebView 視窗
QtWebEngineView 封裝，提供 Web UI 顯示與互動
"""

import logging
from typing import Optional

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMainWindow, QMessageBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage

logger = logging.getLogger(__name__)


class WebEnginePage(QWebEnginePage):
    """自訂 WebEnginePage 以處理 console 訊息"""

    def javaScriptConsoleMessage(self, level, message, line_number, source_id):
        """記錄 JavaScript console 訊息"""
        logger.debug(f"JS Console [{source_id}:{line_number}]: {message}")


class WebViewWindow(QMainWindow):
    """主視窗"""

    def __init__(self, flask_manager, parent=None):
        super().__init__(parent)
        self.flask_manager = flask_manager
        self.webview: Optional[QWebEngineView] = None
        
        self._init_ui()
        self._load_flask_ui()

    def _init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("Robot Command Console - Tiny")
        self.resize(1200, 800)

        # 建立 WebView
        self.webview = QWebEngineView()
        page = WebEnginePage(self.webview)
        self.webview.setPage(page)
        
        self.setCentralWidget(self.webview)

        # 設定圖示 (如果有)
        # icon_path = os.path.join(os.path.dirname(__file__), 'resources', 'icon.png')
        # if os.path.exists(icon_path):
        #     self.setWindowIcon(QIcon(icon_path))

    def _load_flask_ui(self):
        """載入 Flask UI"""
        try:
            url = self.flask_manager.get_url()
            logger.info(f"載入 UI: {url}")
            self.webview.load(QUrl(url))
        except Exception as e:
            logger.error(f"載入 UI 失敗: {e}")
            QMessageBox.critical(
                self,
                "錯誤",
                f"無法載入使用者介面:\n{e}"
            )

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
