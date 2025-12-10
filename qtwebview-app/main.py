#!/usr/bin/env python3
"""
Tiny Edge App - 主程式入口
PyQt6 + Flask 輕量版機器人指令控制台
"""

import logging
import sys
import os

# 將專案根目錄加入路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QCoreApplication

from flask_manager import FlaskManager
from webview_window import WebViewWindow

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """主函式"""
    logger.info("啟動 Tiny Edge App...")

    # 設定應用程式資訊
    QCoreApplication.setOrganizationName("RobotCommandConsole")
    QCoreApplication.setApplicationName("TinyEdgeApp")
    QCoreApplication.setApplicationVersion("1.0.0")

    # 建立 Qt 應用程式
    app = QApplication(sys.argv)
    app.setApplicationName("Robot Command Console - Tiny")

    # 啟動 Flask 服務
    logger.info("啟動 Flask 服務...")
    flask_manager = FlaskManager()
    
    if not flask_manager.start():
        logger.error("Flask 服務啟動失敗")
        sys.exit(1)

    # 建立主視窗
    logger.info("建立主視窗...")
    window = WebViewWindow(flask_manager)
    window.show()

    logger.info("應用程式已啟動")

    # 進入事件循環
    exit_code = app.exec()

    # 清理
    logger.info("正在清理資源...")
    flask_manager.stop()

    logger.info(f"應用程式已退出 (exit code: {exit_code})")
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
