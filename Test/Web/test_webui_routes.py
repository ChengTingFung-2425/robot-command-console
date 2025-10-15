import unittest

class TestWebUIRoutes(unittest.TestCase):
    def test_routes_module(self):
        try:
            from WebUI.app import routes
        except ImportError:
            self.skipTest('routes 模組尚未實作')
        # 測試 routes 是否有 route_command 方法
        self.assertTrue(hasattr(routes, 'route_command'), '缺少 route_command 方法')

if __name__ == '__main__':
    unittest.main()
