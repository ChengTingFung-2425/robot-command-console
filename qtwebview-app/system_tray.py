#!/usr/bin/env python3
"""
系統托盤
提供系統托盤圖示與快速操作選單
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class SystemTray(QSystemTrayIcon):
    """系統托盤圖示"""

    # 自訂信號
    show_window_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent=None):
        # 載入圖示 (如果有)
        # icon = QIcon("resources/icon.png")
        # super().__init__(icon, parent)
        
        # 暫時使用預設圖示
        super().__init__(parent)
        
        self._init_menu()
        
        # 雙擊托盤圖示顯示視窗
        self.activated.connect(self._on_activated)

    def _init_menu(self):
        """初始化選單"""
        menu = QMenu()

        # 顯示視窗
        show_action = QAction("顯示", self)
        show_action.triggered.connect(self.show_window_requested.emit)
        menu.addAction(show_action)

        menu.addSeparator()

        # 關於
        about_action = QAction("關於", self)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)

        menu.addSeparator()

        # 退出
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def _on_activated(self, reason):
        """托盤圖示被點擊"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window_requested.emit()

    def _show_about(self):
        """顯示關於對話框"""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(
            None,
            "關於 Robot Command Console - Tiny",
            "輕量版機器人指令控制台\n\n"
            "版本: 1.0.0\n"
            "基於 PyQt6 + Flask"
        )

    def show_notification(self, title: str, message: str, timeout: int = 3000):
        """顯示系統通知"""
        self.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            timeout
        )
