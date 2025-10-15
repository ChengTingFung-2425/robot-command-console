import unittest

class TestWebUIRobotModel(unittest.TestCase):
    def test_models_module(self):
        try:
            from WebUI.app import models
        except ImportError:
            self.skipTest('models 模組尚未實作')
        # 測試 models 是否有 RobotBase 類別
        self.assertTrue(hasattr(models, 'RobotBase'), '缺少 RobotBase 類別')

if __name__ == '__main__':
    unittest.main()
