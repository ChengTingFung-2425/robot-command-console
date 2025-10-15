import unittest

class TestWebUIConfig(unittest.TestCase):
    def test_config_module(self):
        try:
            from . import config
        except ImportError:
            self.skipTest('config 模組尚未實作')
        # 測試 config 是否有 Config 類別
        self.assertTrue(hasattr(config, 'Config'), '缺少 Config 類別')

if __name__ == '__main__':
    unittest.main()
