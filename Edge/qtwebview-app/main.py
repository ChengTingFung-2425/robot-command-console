#!/usr/bin/env python3
"""
Tiny Edge App - 主程式入口
PyQt6 + 統一後端服務管理器 輕量版機器人指令控制台
"""

import logging
import sys
import os

# 將專案根目錄加入路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QCoreApplication

from webview_window import WebViewWindow
from main_window import HybridMainWindow

# 導入統一後端服務管理器
from src.common.backend_service_manager import BackendServiceManagerSync

# 設定日誌（秘密除錯模式由 BackendServiceManager 內部處理）
logging.basicConfig(
    level=logging.WARNING,  # 預設只顯示警告和錯誤
    format='%(message)s'  # 簡潔格式
)

logger = logging.getLogger(__name__)


def show_splash_screen(app):
    """顯示啟動畫面
    
    載入並顯示專業的啟動畫面圖片，包含：
    - 應用程式標誌和名稱
    - 版本資訊
    - 載入進度指示
    """
    from PyQt6.QtWidgets import QSplashScreen
    from PyQt6.QtGui import QPixmap, QColor
    from PyQt6.QtCore import Qt
    
    try:
        # 取得啟動畫面圖片路徑
        script_dir = os.path.dirname(os.path.abspath(__file__))
        splash_image_path = os.path.join(script_dir, 'resources', 'images', 'splash.png')
        
        # 載入啟動畫面圖片
        if os.path.exists(splash_image_path):
            pixmap = QPixmap(splash_image_path)
            logger.info(f"載入啟動畫面圖片：{splash_image_path}")
        else:
            # 如果圖片不存在，使用純色背景作為後備
            logger.error(f"找不到啟動畫面圖片：{splash_image_path}，使用預設背景")
            pixmap = QPixmap(640, 400)
            pixmap.fill(QColor(42, 45, 50))
        
        # 創建啟動畫面
        splash = QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)
        splash.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.SplashScreen
        )
        
        # 顯示訊息
        splash.showMessage(
            "正在初始化...",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
            QColor(100, 150, 255)
        )
        
        logger.info("Splash screen created successfully")
        return splash
        
    except Exception as e:
        logger.warning(f"無法創建啟動畫面: {e}")
        return None


def main():
    """主函式"""
    # 設定應用程式資訊
    QCoreApplication.setOrganizationName("RobotCommandConsole")
    QCoreApplication.setApplicationName("TinyEdgeApp")
    QCoreApplication.setApplicationVersion("1.0.0")

    # 建立 Qt 應用程式
    app = QApplication(sys.argv)
    app.setApplicationName("Robot Command Console - Tiny")
    
    # 顯示啟動畫面（可選）
    splash = show_splash_screen(app)
    if splash:
        splash.show()
        app.processEvents()

    # 啟動統一後端服務管理器（自動檢測秘密除錯模式）
    logger.info("Starting application...")
    
    backend_manager = BackendServiceManagerSync()
    
    try:
        success_count, total_count = backend_manager.start_all()
        
        if success_count == 0:
            QMessageBox.critical(
                None,
                "Startup Failed",
                "Unable to start backend services.\nPlease check system configuration."
            )
            sys.exit(1)
        elif success_count < total_count:
            QMessageBox.warning(
                None,
                "Partial Startup",
                f"Started {success_count}/{total_count} services.\n"
                "Some features may be unavailable."
            )
    except Exception as e:
        logger.error(f"Backend startup error: {e}")
        QMessageBox.critical(
            None,
            "Startup Error",
            f"An error occurred during startup:\n{e}"
        )
        sys.exit(1)

    # 建立主視窗 (使用混合架構 - Approach B)
    # window = WebViewWindow(backend_manager)  # 舊版 WebView
    window = HybridMainWindow(backend_manager)  # 新版混合架構
    
    # 關閉啟動畫面
    if splash:
        splash.finish(window)
    
    window.show()
    logger.info("Application ready")

    # 進入事件循環
    exit_code = app.exec()

    # 清理
    backend_manager.stop_all()
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
