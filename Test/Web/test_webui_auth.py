import unittest

class TestWebUIAuth(unittest.TestCase):
    def test_auth_module(self):
        try:
            from WebUI.app import auth
        except ImportError:
            self.skipTest('auth 模組尚未實作')
        # 測試認證模組是否有 authenticate 方法
        self.assertTrue(hasattr(auth, 'authenticate'), '缺少 authenticate 方法')

if __name__ == '__main__':
    unittest.main()
