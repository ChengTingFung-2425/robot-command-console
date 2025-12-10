#!/usr/bin/env python3
"""
Flask 服務管理器
管理 Flask 服務的啟動、停止與健康檢查
"""

import logging
import os
import socket
import subprocess
import sys
import threading
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class FlaskManager:
    """Flask 服務管理器"""

    def __init__(self, base_port: int = 5100):
        self.base_port = base_port
        self.port: Optional[int] = None
        self.process: Optional[subprocess.Popen] = None
        self.token: Optional[str] = None
        self._health_check_thread: Optional[threading.Thread] = None
        self._stop_health_check = threading.Event()
        self._restart_count = 0
        self._max_restarts = 3

    def _find_available_port(self, start_port: int = 5100, max_attempts: int = 100) -> int:
        """尋找可用的埠號"""
        for port in range(start_port, start_port + max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('127.0.0.1', port))
                    return port
            except OSError:
                continue
        raise RuntimeError(f"無法找到可用埠號 (範圍 {start_port}-{start_port + max_attempts})")

    def _generate_token(self) -> str:
        """生成安全的 token"""
        import secrets
        return secrets.token_hex(32)

    def start(self) -> bool:
        """啟動 Flask 服務"""
        if self.process is not None:
            logger.warning("Flask 服務已在運行中")
            return True

        try:
            # 尋找可用埠
            self.port = self._find_available_port(self.base_port)
            logger.info(f"使用埠號: {self.port}")

            # 生成 token
            self.token = self._generate_token()

            # 準備環境變數
            env = os.environ.copy()
            env['PORT'] = str(self.port)
            env['APP_TOKEN'] = self.token
            env['FLASK_ENV'] = 'production'

            # 啟動 Flask 服務
            flask_script = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'flask_service.py'
            )

            self.process = subprocess.Popen(
                [sys.executable, flask_script],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            logger.info(f"Flask 服務已啟動 (PID: {self.process.pid})")

            # 等待服務就緒
            if not self._wait_for_ready(timeout=30):
                logger.error("Flask 服務啟動超時")
                self.stop()
                return False

            # 啟動健康檢查
            self._start_health_check()

            return True

        except Exception as e:
            logger.error(f"啟動 Flask 服務失敗: {e}")
            return False

    def _wait_for_ready(self, timeout: int = 30) -> bool:
        """等待服務就緒"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(
                    f"http://127.0.0.1:{self.port}/health",
                    timeout=2
                )
                if response.status_code == 200:
                    logger.info("Flask 服務已就緒")
                    return True
            except requests.RequestException:
                pass
            time.sleep(0.5)
        return False

    def stop(self):
        """停止 Flask 服務"""
        self._stop_health_check.set()

        if self._health_check_thread:
            self._health_check_thread.join(timeout=5)
            self._health_check_thread = None

        if self.process:
            logger.info("正在停止 Flask 服務...")
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("Flask 服務未正常終止，強制終止")
                self.process.kill()
                self.process.wait()
            self.process = None
            logger.info("Flask 服務已停止")

    def _start_health_check(self):
        """啟動健康檢查執行緒"""
        self._stop_health_check.clear()
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self._health_check_thread.start()

    def _health_check_loop(self):
        """健康檢查循環"""
        while not self._stop_health_check.is_set():
            time.sleep(5)  # 每 5 秒檢查一次

            if not self.is_healthy():
                logger.warning("Flask 服務健康檢查失敗")
                if self._restart_count < self._max_restarts:
                    logger.info(f"嘗試重啟服務 (第 {self._restart_count + 1}/{self._max_restarts} 次)")
                    self._restart_count += 1
                    self.stop()
                    if not self.start():
                        logger.error("重啟失敗")
                else:
                    logger.error(f"已達最大重啟次數 ({self._max_restarts})，停止重啟")
                    break

    def is_healthy(self) -> bool:
        """檢查服務是否健康"""
        if self.process is None:
            return False

        # 檢查進程是否存活
        if self.process.poll() is not None:
            return False

        # 檢查 HTTP 端點
        try:
            response = requests.get(
                f"http://127.0.0.1:{self.port}/health",
                timeout=2
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    def get_url(self) -> str:
        """取得 Flask 服務 URL"""
        if self.port is None:
            raise RuntimeError("Flask 服務尚未啟動")
        return f"http://127.0.0.1:{self.port}"
