import unittest

class TestCommunicationProtocolsModule(unittest.TestCase):
    def test_protocol_support(self):
        try:
            from WebUI.app import protocols
        except ImportError:
            self.skipTest('protocols 尚未實作')
        # 測試協議支援
        supported = protocols.list_supported()
        self.assertIsInstance(supported, list)

if __name__ == '__main__':
    unittest.main()
