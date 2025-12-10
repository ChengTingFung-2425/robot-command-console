#!/usr/bin/env python3
"""
QWebChannel 橋接
提供 JavaScript 與 Python 之間的通訊橋接
"""

import logging
import os
import platform

from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal, QUrl
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtGui import QDesktopServices

logger = logging.getLogger(__name__)

# 嘗試載入版本資訊
try:
    from __init__ import __version__
except ImportError:
    __version__ = "1.0.0"


class NativeBridge(QObject):
    """JS-Python 橋接物件"""

    # 信號 (Python → JS)
    notificationReceived = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent_widget = parent

    @pyqtSlot(str, str, result=str)
    def showFileDialog(self, mode: str, file_filter: str = "") -> str:
        """
        顯示檔案對話框
        
        Args:
            mode: 'open' 或 'save'
            file_filter: 檔案過濾器，例如 '*.json'
        
        Returns:
            選擇的檔案路徑，如果取消則返回空字串
        """
        logger.info(f"顯示檔案對話框: mode={mode}, filter={file_filter}")

        try:
            if mode == 'open':
                file_path, _ = QFileDialog.getOpenFileName(
                    self._parent_widget,
                    "選擇檔案",
                    os.path.expanduser("~"),
                    file_filter
                )
            elif mode == 'save':
                file_path, _ = QFileDialog.getSaveFileName(
                    self._parent_widget,
                    "儲存檔案",
                    os.path.expanduser("~"),
                    file_filter
                )
            else:
                logger.warning(f"不支援的模式: {mode}")
                return ""

            logger.info(f"選擇的檔案: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"檔案對話框錯誤: {e}")
            return ""

    @pyqtSlot(str, str)
    def showNotification(self, title: str, message: str):
        """
        顯示系統通知
        
        Args:
            title: 通知標題
            message: 通知內容
        """
        logger.info(f"顯示通知: {title} - {message}")
        
        # 發送信號給 QSystemTrayIcon
        self.notificationReceived.emit(title, message)

    @pyqtSlot(result=str)
    def getAppVersion(self) -> str:
        """取得應用程式版本"""
        return __version__

    @pyqtSlot(str)
    def openExternal(self, url: str):
        """
        開啟外部連結
        
        Args:
            url: 要開啟的 URL
        """
        logger.info(f"開啟外部連結: {url}")
        
        try:
            QDesktopServices.openUrl(QUrl(url))
        except Exception as e:
            logger.error(f"開啟外部連結失敗: {e}")

    @pyqtSlot(result=str)
    def getPlatform(self) -> str:
        """取得作業系統平台"""
        return platform.system()

    @pyqtSlot(str, result=str)
    def selectDirectory(self, title: str = "選擇資料夾") -> str:
        """
        選擇資料夾
        
        Args:
            title: 對話框標題
        
        Returns:
            選擇的資料夾路徑，如果取消則返回空字串
        """
        logger.info(f"選擇資料夾: {title}")
        
        try:
            dir_path = QFileDialog.getExistingDirectory(
                self._parent_widget,
                title,
                os.path.expanduser("~")
            )
            logger.info(f"選擇的資料夾: {dir_path}")
            return dir_path
        except Exception as e:
            logger.error(f"選擇資料夾錯誤: {e}")
            return ""
