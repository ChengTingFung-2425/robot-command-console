import unittest

class TestMCPServerModule(unittest.TestCase):
    def test_mcp_server_context(self):
        try:
            from WebUI.app import mcp_server
        except ImportError:
            self.skipTest('mcp_server 尚未實作')
        # 測試 MCP 伺服器 context 處理
        ctx = mcp_server.get_context()
        self.assertIn('clients', ctx)

if __name__ == '__main__':
    unittest.main()
