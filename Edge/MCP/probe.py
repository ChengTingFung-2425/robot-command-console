"""
Endpoint Liveness Probe

檢查 LLM Copilot 端點是否存活
支援 HTTP 和 Unix socket 端點
"""

import socket
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Tuple, List
import urllib.request
import urllib.error

from .models import Endpoint, ProviderHealth


logger = logging.getLogger(__name__)


class EndpointProbe:
    """端點活躍性探測器"""

    @staticmethod
    def check_http_endpoint(endpoint: Endpoint) -> Tuple[bool, float, Optional[str]]:
        """
        檢查 HTTP/HTTPS 端點

        Args:
            endpoint: 端點配置

        Returns:
            (是否可用, 響應時間ms, 錯誤訊息)
        """
        start_time = time.time()
        error_message = None

        try:
            # 構建健康檢查 URL
            url = f"{endpoint.address.rstrip('/')}{endpoint.health_check_path}"

            # 發送請求
            timeout_s = endpoint.timeout_ms / 1000.0
            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", "LLM-Discovery-Probe/1.0")

            with urllib.request.urlopen(req, timeout=timeout_s) as response:
                status_code = response.getcode()
                is_available = 200 <= status_code < 300

                if not is_available:
                    error_message = f"HTTP {status_code}"

        except urllib.error.HTTPError as e:
            is_available = False
            error_message = f"HTTP {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            is_available = False
            error_message = f"URL Error: {e.reason}"
        except socket.timeout:
            is_available = False
            error_message = "Timeout"
        except Exception as e:
            is_available = False
            error_message = str(e)

        elapsed_time = (time.time() - start_time) * 1000  # 轉換為毫秒

        return is_available, elapsed_time, error_message

    @staticmethod
    def check_unix_socket(endpoint: Endpoint) -> Tuple[bool, float, Optional[str]]:
        """
        檢查 Unix socket 端點

        Args:
            endpoint: 端點配置

        Returns:
            (是否可用, 響應時間ms, 錯誤訊息)
        """
        start_time = time.time()
        error_message = None

        try:
            # 創建 socket 連接
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(endpoint.timeout_ms / 1000.0)

            # 嘗試連接
            sock.connect(endpoint.address)
            is_available = True

            # 關閉連接
            sock.close()

        except socket.timeout:
            is_available = False
            error_message = "Timeout"
        except socket.error as e:
            is_available = False
            error_message = f"Socket error: {e}"
        except Exception as e:
            is_available = False
            error_message = str(e)

        elapsed_time = (time.time() - start_time) * 1000  # 轉換為毫秒

        return is_available, elapsed_time, error_message

    @staticmethod
    def check_tcp_endpoint(endpoint: Endpoint) -> Tuple[bool, float, Optional[str]]:
        """
        檢查 TCP 端點

        Args:
            endpoint: 端點配置

        Returns:
            (是否可用, 響應時間ms, 錯誤訊息)
        """
        start_time = time.time()
        error_message = None

        try:
            # 解析地址 (host:port)
            if ":" in endpoint.address:
                host, port_str = endpoint.address.rsplit(":", 1)
                port = int(port_str)
            else:
                host = endpoint.address
                port = 80  # 預設端口

            # 創建 socket 連接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(endpoint.timeout_ms / 1000.0)

            # 嘗試連接
            sock.connect((host, port))
            is_available = True

            # 關閉連接
            sock.close()

        except socket.timeout:
            is_available = False
            error_message = "Timeout"
        except socket.error as e:
            is_available = False
            error_message = f"Socket error: {e}"
        except ValueError as e:
            is_available = False
            error_message = f"Invalid address format: {e}"
        except Exception as e:
            is_available = False
            error_message = str(e)

        elapsed_time = (time.time() - start_time) * 1000  # 轉換為毫秒

        return is_available, elapsed_time, error_message

    @staticmethod
    def probe_endpoint(endpoint: Endpoint) -> Tuple[bool, float, Optional[str]]:
        """
        探測端點（自動選擇方法）

        Args:
            endpoint: 端點配置

        Returns:
            (是否可用, 響應時間ms, 錯誤訊息)
        """
        if endpoint.type in ["http", "https"]:
            return EndpointProbe.check_http_endpoint(endpoint)
        elif endpoint.type == "unix-socket":
            return EndpointProbe.check_unix_socket(endpoint)
        elif endpoint.type == "tcp":
            return EndpointProbe.check_tcp_endpoint(endpoint)
        else:
            return False, 0.0, f"Unsupported endpoint type: {endpoint.type}"

    @staticmethod
    def check_provider_health(
        provider_id: str,
        endpoints: List[Endpoint],
        previous_failures: int = 0
    ) -> ProviderHealth:
        """
        檢查提供商的健康狀態（檢查所有端點）

        Args:
            provider_id: 提供商 ID
            endpoints: 端點列表
            previous_failures: 之前的連續失敗次數

        Returns:
            ProviderHealth 物件
        """
        available_endpoints = []
        total_response_time = 0.0
        all_failed = True
        any_available = False
        error_messages = []

        # 檢查每個端點
        for endpoint in endpoints:
            is_available, response_time, error = EndpointProbe.probe_endpoint(endpoint)

            if is_available:
                available_endpoints.append(endpoint.address)
                total_response_time += response_time
                any_available = True
                all_failed = False
            else:
                if error:
                    error_messages.append(f"{endpoint.address}: {error}")

        # 計算平均響應時間
        avg_response_time = total_response_time / len(available_endpoints) if available_endpoints else 0.0

        # 決定狀態
        if all_failed:
            status = "unavailable"
            consecutive_failures = previous_failures + 1
            error_message = "; ".join(error_messages) if error_messages else "All endpoints failed"
        elif any_available:
            status = "available"
            consecutive_failures = 0
            error_message = None
        else:
            status = "degraded"
            consecutive_failures = 0
            error_message = "Some endpoints unavailable"

        return ProviderHealth(
            provider_id=provider_id,
            status=status,
            last_check=datetime.now(timezone.utc),
            response_time_ms=avg_response_time,
            error_message=error_message,
            consecutive_failures=consecutive_failures,
            available_endpoints=available_endpoints,
        )
