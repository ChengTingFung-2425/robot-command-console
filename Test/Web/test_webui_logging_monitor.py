import unittest

class TestWebUILoggingMonitoring(unittest.TestCase):
    def test_logging_monitor_module(self):
        try:
            from WebUI.app import logging_monitor
        except ImportError:
            self.skipTest('logging_monitor 模組尚未實作')
        # 測試日誌模組是否有 log_event 方法
        self.assertTrue(hasattr(logging_monitor, 'log_event'), '缺少 log_event 方法')

if __name__ == '__main__':
    unittest.main()
