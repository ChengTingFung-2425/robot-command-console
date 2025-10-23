"""
測試 MCP HTTP 請求的 SSL 憑證驗證設定
"""
import asyncio
import os
import ssl
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMCPSSLVerification(unittest.TestCase):
    """測試 SSL 驗證設定"""

    def setUp(self):
        """測試前設定"""
        # 儲存原始環境變數
        self.original_env = os.environ.get("MCP_SSL_VERIFY")

    def tearDown(self):
        """測試後清理"""
        # 恢復原始環境變數
        if self.original_env is not None:
            os.environ["MCP_SSL_VERIFY"] = self.original_env
        elif "MCP_SSL_VERIFY" in os.environ:
            del os.environ["MCP_SSL_VERIFY"]

    def test_ssl_verify_default_true(self):
        """測試 SSL_VERIFY 預設為 True"""
        # 清除環境變數以測試預設值
        if "MCP_SSL_VERIFY" in os.environ:
            del os.environ["MCP_SSL_VERIFY"]
        
        # 直接執行 config 程式碼以測試
        import sys
        import importlib.util
        
        spec = importlib.util.spec_from_file_location("test_config", "MCP/config.py")
        test_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_config)
        
        self.assertTrue(test_config.MCPConfig.SSL_VERIFY)

    def test_ssl_verify_env_true(self):
        """測試 SSL_VERIFY 環境變數設為 true"""
        os.environ["MCP_SSL_VERIFY"] = "true"
        
        import sys
        import importlib.util
        
        spec = importlib.util.spec_from_file_location("test_config", "MCP/config.py")
        test_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_config)
        
        self.assertTrue(test_config.MCPConfig.SSL_VERIFY)

    def test_ssl_verify_env_false(self):
        """測試 SSL_VERIFY 環境變數設為 false"""
        os.environ["MCP_SSL_VERIFY"] = "false"
        
        import sys
        import importlib.util
        
        spec = importlib.util.spec_from_file_location("test_config", "MCP/config.py")
        test_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(test_config)
        
        self.assertFalse(test_config.MCPConfig.SSL_VERIFY)


class TestRobotRouterSSL(unittest.TestCase):
    """測試 RobotRouter 的 SSL 設定"""

    @pytest.mark.asyncio
    async def test_https_request_with_ssl_verify_enabled(self):
        """測試 HTTPS 請求啟用 SSL 驗證"""
        from MCP.robot_router import RobotRouter
        from MCP.models import RobotRegistration, Protocol
        
        # 設定 SSL 驗證為 True
        os.environ["MCP_SSL_VERIFY"] = "true"
        import importlib
        from MCP import config
        importlib.reload(config)
        
        router = RobotRouter()
        
        # Mock aiohttp
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"result": "success"})
            
            mock_post = AsyncMock()
            mock_post.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.__aexit__ = AsyncMock(return_value=None)
            
            mock_session_instance = MagicMock()
            mock_session_instance.post = MagicMock(return_value=mock_post)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            
            mock_session.return_value = mock_session_instance
            
            # 執行 HTTPS 請求
            result = await router._send_http_command(
                endpoint="https://example.com",
                command_type="test",
                params={},
                timeout_ms=5000,
                trace_id="test-trace"
            )
            
            # 驗證結果
            self.assertIn("data", result)
            
            # 驗證 SSL context 被正確使用
            mock_session_instance.post.assert_called_once()
            call_kwargs = mock_session_instance.post.call_args[1]
            self.assertIn("ssl", call_kwargs)
            # SSL context 應該是 ssl.SSLContext 實例或 None（但不應該是 False）
            ssl_arg = call_kwargs["ssl"]
            if ssl_arg is not None:
                self.assertIsInstance(ssl_arg, ssl.SSLContext)

    @pytest.mark.asyncio
    async def test_https_request_with_ssl_verify_disabled(self):
        """測試 HTTPS 請求停用 SSL 驗證（開發環境）"""
        from MCP.robot_router import RobotRouter
        
        # 設定 SSL 驗證為 False
        os.environ["MCP_SSL_VERIFY"] = "false"
        import importlib
        from MCP import config
        importlib.reload(config)
        
        router = RobotRouter()
        
        # Mock aiohttp
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"result": "success"})
            
            mock_post = AsyncMock()
            mock_post.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.__aexit__ = AsyncMock(return_value=None)
            
            mock_session_instance = MagicMock()
            mock_session_instance.post = MagicMock(return_value=mock_post)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            
            mock_session.return_value = mock_session_instance
            
            # 執行 HTTPS 請求
            result = await router._send_http_command(
                endpoint="https://example.com",
                command_type="test",
                params={},
                timeout_ms=5000,
                trace_id="test-trace"
            )
            
            # 驗證結果
            self.assertIn("data", result)
            
            # 驗證 SSL 被設為 False
            mock_session_instance.post.assert_called_once()
            call_kwargs = mock_session_instance.post.call_args[1]
            self.assertIn("ssl", call_kwargs)
            self.assertFalse(call_kwargs["ssl"])

    @pytest.mark.asyncio
    async def test_http_request_no_ssl_context(self):
        """測試 HTTP 請求不設定 SSL context"""
        from MCP.robot_router import RobotRouter
        
        router = RobotRouter()
        
        # Mock aiohttp
        with patch("aiohttp.ClientSession") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"result": "success"})
            
            mock_post = AsyncMock()
            mock_post.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.__aexit__ = AsyncMock(return_value=None)
            
            mock_session_instance = MagicMock()
            mock_session_instance.post = MagicMock(return_value=mock_post)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock(return_value=None)
            
            mock_session.return_value = mock_session_instance
            
            # 執行 HTTP 請求（非 HTTPS）
            result = await router._send_http_command(
                endpoint="http://example.com",
                command_type="test",
                params={},
                timeout_ms=5000,
                trace_id="test-trace"
            )
            
            # 驗證結果
            self.assertIn("data", result)
            
            # 驗證 SSL context 為 None（HTTP 不需要）
            mock_session_instance.post.assert_called_once()
            call_kwargs = mock_session_instance.post.call_args[1]
            self.assertIn("ssl", call_kwargs)
            self.assertIsNone(call_kwargs["ssl"])


if __name__ == "__main__":
    # 執行 asyncio 測試需要特殊處理
    unittest.main()
