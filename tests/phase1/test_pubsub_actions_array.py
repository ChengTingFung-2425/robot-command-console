"""測試 pubsub.py 處理 actions 陣列的新功能

本測試套件驗證：
1. pubsub.py 正確處理包含 actions 陣列的負載
2. 向後相容性：仍支援 toolName 格式
3. 錯誤處理：無效的負載格式
4. 優先順序：actions 陣列優先於舊格式
"""

import json
import unittest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Mock AWS dependencies before importing
sys.modules['awscrt'] = MagicMock()
sys.modules['awscrt.auth'] = MagicMock()
sys.modules['awscrt.mqtt5'] = MagicMock()
sys.modules['awsiot'] = MagicMock()
sys.modules['awsiot.mqtt5_client_builder'] = MagicMock()

# 添加 Robot-Console 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'Robot-Console'))


class TestPubSubActionsArray(unittest.TestCase):
    """測試 PubSubClient 處理 actions 陣列"""

    def setUp(self):
        """設定測試環境"""
        # Mock ActionExecutor
        self.mock_executor = Mock()
        self.mock_executor.add_actions_to_queue = Mock()
        self.mock_executor.add_action_to_queue = Mock()

        # 設定最小的 settings
        self.settings = {
            'input_topic': 'test/topic',
            'input_endpoint': 'test-endpoint.iot.amazonaws.com',
            'input_clientId': 'test-client',
            'input_cert': '/tmp/cert.pem',
            'input_key': '/tmp/key.pem',
            'input_ca': '/tmp/ca.pem',
        }

    @patch('pubsub.mqtt5')
    @patch('pubsub.AdvancedDecoder')
    def test_actions_array_processing(self, mock_decoder_class, mock_mqtt5):
        """測試處理包含 actions 陣列的負載"""
        from pubsub import PubSubClient

        # 建立客戶端（不啟用舊解碼器）
        client = PubSubClient(self.settings, self.mock_executor)

        # 建立包含 actions 陣列的負載
        payload = {
            "actions": ["go_forward", "turn_left", "stand"]
        }

        # 建立 mock 的 publish packet
        mock_packet = Mock()
        mock_packet.topic = self.settings['input_topic']
        mock_packet.payload = json.dumps(payload).encode('utf-8')

        # Mock the PublishPacket class to return True for isinstance check
        mock_mqtt5.PublishPacket = type('PublishPacket', (), {})
        mock_packet.__class__ = mock_mqtt5.PublishPacket

        mock_packet_data = Mock()
        mock_packet_data.publish_packet = mock_packet

        # 呼叫處理函數
        client.on_publish_received(mock_packet_data)

        # 驗證：應該呼叫 add_actions_to_queue
        self.mock_executor.add_actions_to_queue.assert_called_once_with(
            ["go_forward", "turn_left", "stand"]
        )

        # 驗證：不應該呼叫單一動作方法
        self.mock_executor.add_action_to_queue.assert_not_called()

    @patch('pubsub.mqtt5')
    @patch('pubsub.AdvancedDecoder')
    def test_toolname_fallback(self, mock_decoder_class, mock_mqtt5):
        """測試 toolName 向後相容性"""
        from pubsub import PubSubClient

        # 建立客戶端
        client = PubSubClient(self.settings, self.mock_executor)

        # 建立包含 toolName 的負載
        payload = {
            "toolName": "bow"
        }

        # 建立 mock 的 publish packet
        mock_packet = Mock()
        mock_packet.topic = self.settings['input_topic']
        mock_packet.payload = json.dumps(payload).encode('utf-8')

        # Mock the PublishPacket class
        mock_mqtt5.PublishPacket = type('PublishPacket', (), {})
        mock_packet.__class__ = mock_mqtt5.PublishPacket

        mock_packet_data = Mock()
        mock_packet_data.publish_packet = mock_packet

        # 呼叫處理函數
        client.on_publish_received(mock_packet_data)

        # 驗證：應該呼叫 add_action_to_queue
        self.mock_executor.add_action_to_queue.assert_called_once_with("bow")

        # 驗證：不應該呼叫多動作方法
        self.mock_executor.add_actions_to_queue.assert_not_called()

    @patch('pubsub.mqtt5')
    @patch('pubsub.AdvancedDecoder')
    def test_invalid_actions_format(self, mock_decoder_class, mock_mqtt5):
        """測試無效的 actions 格式"""
        from pubsub import PubSubClient

        # 建立客戶端
        client = PubSubClient(self.settings, self.mock_executor)

        # 建立包含無效 actions 的負載（不是字串列表）
        payload = {
            "actions": ["go_forward", 123, "stand"]  # 包含非字串元素
        }

        # 建立 mock 的 publish packet
        mock_packet = Mock()
        mock_packet.topic = self.settings['input_topic']
        mock_packet.payload = json.dumps(payload).encode('utf-8')

        # Mock the PublishPacket class
        mock_mqtt5.PublishPacket = type('PublishPacket', (), {})
        mock_packet.__class__ = mock_mqtt5.PublishPacket

        mock_packet_data = Mock()
        mock_packet_data.publish_packet = mock_packet

        # 呼叫處理函數
        client.on_publish_received(mock_packet_data)

        # 驗證：不應該呼叫任何執行方法
        self.mock_executor.add_actions_to_queue.assert_not_called()
        self.mock_executor.add_action_to_queue.assert_not_called()

    @patch('pubsub.mqtt5')
    @patch('pubsub.AdvancedDecoder')
    def test_actions_priority_over_toolname(self, mock_decoder_class, mock_mqtt5):
        """測試 actions 陣列優先於 toolName"""
        from pubsub import PubSubClient

        # 建立客戶端
        client = PubSubClient(self.settings, self.mock_executor)

        # 建立同時包含 actions 和 toolName 的負載
        payload = {
            "actions": ["go_forward", "turn_left"],
            "toolName": "bow"  # 應該被忽略
        }

        # 建立 mock 的 publish packet
        mock_packet = Mock()
        mock_packet.topic = self.settings['input_topic']
        mock_packet.payload = json.dumps(payload).encode('utf-8')

        # Mock the PublishPacket class
        mock_mqtt5.PublishPacket = type('PublishPacket', (), {})
        mock_packet.__class__ = mock_mqtt5.PublishPacket

        mock_packet_data = Mock()
        mock_packet_data.publish_packet = mock_packet

        # 呼叫處理函數
        client.on_publish_received(mock_packet_data)

        # 驗證：應該使用 actions 陣列
        self.mock_executor.add_actions_to_queue.assert_called_once_with(
            ["go_forward", "turn_left"]
        )

        # 驗證：不應該使用 toolName
        self.mock_executor.add_action_to_queue.assert_not_called()

    @patch('pubsub.mqtt5')
    @patch('pubsub.AdvancedDecoder')
    def test_empty_actions_array(self, mock_decoder_class, mock_mqtt5):
        """測試空的 actions 陣列"""
        from pubsub import PubSubClient

        # 建立客戶端
        client = PubSubClient(self.settings, self.mock_executor)

        # 建立包含空 actions 陣列的負載
        payload = {
            "actions": []
        }

        # 建立 mock 的 publish packet
        mock_packet = Mock()
        mock_packet.topic = self.settings['input_topic']
        mock_packet.payload = json.dumps(payload).encode('utf-8')

        # Mock the PublishPacket class
        mock_mqtt5.PublishPacket = type('PublishPacket', (), {})
        mock_packet.__class__ = mock_mqtt5.PublishPacket

        mock_packet_data = Mock()
        mock_packet_data.publish_packet = mock_packet

        # 呼叫處理函數
        client.on_publish_received(mock_packet_data)

        # 驗證：應該呼叫 add_actions_to_queue（即使是空列表）
        self.mock_executor.add_actions_to_queue.assert_called_once_with([])

    @patch('pubsub.AdvancedDecoder')
    def test_legacy_decoder_disabled_by_default(self, mock_decoder_class):
        """測試舊解碼器預設為停用"""
        from pubsub import PubSubClient

        # 建立客戶端（預設不啟用舊解碼器）
        client = PubSubClient(self.settings, self.mock_executor)

        # 驗證：decoder 應該是 None
        self.assertIsNone(client.decoder)

        # 驗證：不應該建立 AdvancedDecoder 實例
        mock_decoder_class.assert_not_called()

    @patch('pubsub.AdvancedDecoder')
    def test_legacy_decoder_can_be_enabled(self, mock_decoder_class):
        """測試可以啟用舊解碼器"""
        from pubsub import PubSubClient

        # 在 settings 中啟用舊解碼器
        settings_with_legacy = self.settings.copy()
        settings_with_legacy['enable_legacy_decoder'] = True
        settings_with_legacy['mcp_base_url'] = 'http://localhost:5000'

        # 建立客戶端
        _ = PubSubClient(settings_with_legacy, self.mock_executor)

        # 驗證：應該建立 AdvancedDecoder
        mock_decoder_class.assert_called_once_with(
            mcp_base_url='http://localhost:5000'
        )

    @patch('pubsub.mqtt5')
    @patch('pubsub.AdvancedDecoder')
    @patch('pubsub.logging')
    def test_large_actions_array_warning(self, mock_logging, mock_decoder_class, mock_mqtt5):
        """測試大型 actions 陣列會產生警告"""
        from pubsub import PubSubClient, MAX_RECOMMENDED_ACTIONS

        # 建立客戶端
        client = PubSubClient(self.settings, self.mock_executor)

        # 建立包含大量動作的負載（超過建議上限）
        large_actions = [f"action_{i}" for i in range(MAX_RECOMMENDED_ACTIONS + 10)]
        payload = {"actions": large_actions}

        # 建立 mock 的 publish packet
        mock_packet = Mock()
        mock_packet.topic = self.settings['input_topic']
        mock_packet.payload = json.dumps(payload).encode('utf-8')

        # Mock the PublishPacket class
        mock_mqtt5.PublishPacket = type('PublishPacket', (), {})
        mock_packet.__class__ = mock_mqtt5.PublishPacket

        mock_packet_data = Mock()
        mock_packet_data.publish_packet = mock_packet

        # 呼叫處理函數
        client.on_publish_received(mock_packet_data)

        # 驗證：應該記錄警告訊息
        mock_logging.warning.assert_called_once()
        warning_call = mock_logging.warning.call_args[0][0]
        self.assertIn("exceeds recommended max", warning_call)

        # 驗證：仍然應該處理動作
        self.mock_executor.add_actions_to_queue.assert_called_once_with(large_actions)

    @patch('pubsub.mqtt5')
    @patch('pubsub.AdvancedDecoder')
    def test_actions_not_list_error(self, mock_decoder_class, mock_mqtt5):
        """測試 actions 不是列表時的錯誤處理"""
        from pubsub import PubSubClient

        # 建立客戶端
        client = PubSubClient(self.settings, self.mock_executor)

        # 建立包含非列表 actions 的負載
        payload = {"actions": "not_a_list"}

        # 建立 mock 的 publish packet
        mock_packet = Mock()
        mock_packet.topic = self.settings['input_topic']
        mock_packet.payload = json.dumps(payload).encode('utf-8')

        # Mock the PublishPacket class
        mock_mqtt5.PublishPacket = type('PublishPacket', (), {})
        mock_packet.__class__ = mock_mqtt5.PublishPacket

        mock_packet_data = Mock()
        mock_packet_data.publish_packet = mock_packet

        # 呼叫處理函數
        client.on_publish_received(mock_packet_data)

        # 驗證：不應該呼叫任何執行方法
        self.mock_executor.add_actions_to_queue.assert_not_called()
        self.mock_executor.add_action_to_queue.assert_not_called()


class TestPubSubBackwardCompatibility(unittest.TestCase):
    """測試向後相容性"""

    def setUp(self):
        """設定測試環境"""
        self.mock_executor = Mock()
        self.mock_executor.add_actions_to_queue = Mock()
        self.mock_executor.add_action_to_queue = Mock()

        self.settings = {
            'input_topic': 'test/topic',
            'input_endpoint': 'test-endpoint.iot.amazonaws.com',
            'input_clientId': 'test-client',
            'input_cert': '/tmp/cert.pem',
            'input_key': '/tmp/key.pem',
            'input_ca': '/tmp/ca.pem',
            'enable_legacy_decoder': True,
            'mcp_base_url': 'http://localhost:5000'
        }

    @patch('pubsub.mqtt5')
    @patch('pubsub.AdvancedDecoder')
    def test_legacy_sequence_format(self, mock_decoder_class, mock_mqtt5):
        """測試舊式 sequence 格式（需要啟用舊解碼器）"""
        from pubsub import PubSubClient

        # 設定 mock decoder 回傳值
        mock_decoder_instance = Mock()
        mock_decoder_instance.decode = Mock(return_value=["go_forward", "turn_left"])
        mock_decoder_class.return_value = mock_decoder_instance

        # 建立客戶端（啟用舊解碼器）
        client = PubSubClient(self.settings, self.mock_executor)

        # 建立舊式 sequence 格式的負載
        payload = {
            "type": "sequence",
            "steps": [
                {"action": "go_forward"},
                {"action": "turn_left"}
            ]
        }

        # 建立 mock 的 publish packet
        mock_packet = Mock()
        mock_packet.topic = self.settings['input_topic']
        mock_packet.payload = json.dumps(payload).encode('utf-8')

        # Mock the PublishPacket class
        mock_mqtt5.PublishPacket = type('PublishPacket', (), {})
        mock_packet.__class__ = mock_mqtt5.PublishPacket

        mock_packet_data = Mock()
        mock_packet_data.publish_packet = mock_packet

        # 呼叫處理函數
        client.on_publish_received(mock_packet_data)

        # 驗證：應該呼叫 decoder.decode
        mock_decoder_instance.decode.assert_called_once()

        # 驗證：應該使用解碼後的結果
        self.mock_executor.add_actions_to_queue.assert_called_once_with(
            ["go_forward", "turn_left"]
        )


if __name__ == '__main__':
    unittest.main()
