"""測試 Edge 裝置綁定客戶端"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.edge_app.auth.device_binding import DeviceBindingClient


class TestDeviceBindingClient(unittest.TestCase):
    """測試 DeviceBindingClient 功能"""

    def setUp(self):
        """設置測試環境"""
        self.client = DeviceBindingClient(cloud_api_url="http://test-api.example.com")
        self.test_token = "test-access-token"

    def test_get_device_id(self):
        """測試取得 device_id"""
        with patch('src.edge_app.auth.device_id.DeviceIDGenerator.get_or_create') as mock_get:
            mock_get.return_value = 'a' * 64
            
            device_id = self.client.get_device_id()
            
            self.assertEqual(len(device_id), 64)
            mock_get.assert_called_once()

    def test_get_device_metadata(self):
        """測試取得裝置元資料"""
        metadata = self.client.get_device_metadata()
        
        self.assertIn('platform', metadata)
        self.assertIn('hostname', metadata)
        self.assertIn('device_type', metadata)
        self.assertIsInstance(metadata['platform'], str)

    def test_detect_device_type(self):
        """測試裝置類型偵測"""
        device_type = self.client._detect_device_type()
        
        # Should return one of the expected types
        self.assertIn(device_type, ['desktop', 'laptop', 'edge_device', 'unknown'])

    @patch('requests.post')
    @patch('src.edge_app.auth.device_id.DeviceIDGenerator.get_or_create')
    def test_register_device_success(self, mock_device_id, mock_post):
        """測試成功註冊裝置"""
        mock_device_id.return_value = 'b' * 64
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'success': True,
            'device': {
                'id': 1,
                'device_id': 'b' * 64,
                'device_name': 'Test Device'
            }
        }
        mock_post.return_value = mock_response
        
        result = self.client.register_device(self.test_token, device_name="Test Device")
        
        self.assertTrue(result['success'])
        self.assertIn('device', result)
        mock_post.assert_called_once()
        
        # Verify API call parameters
        call_args = mock_post.call_args
        self.assertIn('/api/auth/device/register', call_args[0][0])
        self.assertEqual(call_args[1]['headers']['Authorization'], f'Bearer {self.test_token}')

    @patch('requests.get')
    def test_list_devices(self, mock_get):
        """測試列出裝置"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'devices': [
                {'id': 1, 'device_name': 'Device 1'},
                {'id': 2, 'device_name': 'Device 2'}
            ],
            'total': 2
        }
        mock_get.return_value = mock_response
        
        result = self.client.list_devices(self.test_token)
        
        self.assertEqual(result['total'], 2)
        self.assertEqual(len(result['devices']), 2)
        mock_get.assert_called_once()

    @patch('requests.get')
    def test_get_device(self, mock_get):
        """測試取得特定裝置"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'device': {
                'id': 1,
                'device_name': 'My Device',
                'is_active': True
            }
        }
        mock_get.return_value = mock_response
        
        result = self.client.get_device(self.test_token, device_id=1)
        
        self.assertIn('device', result)
        self.assertEqual(result['device']['id'], 1)

    @patch('requests.put')
    def test_update_device(self, mock_put):
        """測試更新裝置資訊"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'device': {
                'id': 1,
                'device_name': 'Updated Name',
                'is_trusted': True
            }
        }
        mock_put.return_value = mock_response
        
        result = self.client.update_device(
            self.test_token,
            device_id=1,
            device_name="Updated Name",
            is_trusted=True
        )
        
        self.assertTrue(result['success'])
        self.assertEqual(result['device']['device_name'], 'Updated Name')

    @patch('requests.post')
    def test_unbind_device(self, mock_post):
        """測試解除裝置綁定"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'success': True,
            'message': 'Device unbound successfully'
        }
        mock_post.return_value = mock_response
        
        result = self.client.unbind_device(self.test_token, device_id=1)
        
        self.assertTrue(result['success'])

    @patch('requests.get')
    @patch('src.edge_app.auth.device_id.DeviceIDGenerator.get_or_create')
    def test_verify_device_bound_true(self, mock_device_id, mock_get):
        """測試驗證裝置已綁定"""
        current_device_id = 'c' * 64
        mock_device_id.return_value = current_device_id
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'devices': [
                {'device_id': current_device_id, 'is_active': True}
            ]
        }
        mock_get.return_value = mock_response
        
        is_bound = self.client.verify_device_bound(self.test_token)
        
        self.assertTrue(is_bound)

    @patch('requests.get')
    @patch('src.edge_app.auth.device_id.DeviceIDGenerator.get_or_create')
    def test_verify_device_bound_false(self, mock_device_id, mock_get):
        """測試驗證裝置未綁定"""
        mock_device_id.return_value = 'd' * 64
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'devices': [
                {'device_id': 'e' * 64, 'is_active': True}  # Different device
            ]
        }
        mock_get.return_value = mock_response
        
        is_bound = self.client.verify_device_bound(self.test_token)
        
        self.assertFalse(is_bound)

    @patch('requests.get')
    @patch('src.edge_app.auth.device_id.DeviceIDGenerator.get_or_create')
    def test_auto_register_already_bound(self, mock_device_id, mock_get):
        """測試自動註冊（裝置已綁定）"""
        current_device_id = 'f' * 64
        mock_device_id.return_value = current_device_id
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'devices': [
                {'device_id': current_device_id, 'is_active': True}
            ]
        }
        mock_get.return_value = mock_response
        
        result = self.client.auto_register_if_needed(self.test_token)
        
        self.assertTrue(result['success'])
        self.assertTrue(result['already_bound'])

    @patch('requests.post')
    @patch('requests.get')
    @patch('src.edge_app.auth.device_id.DeviceIDGenerator.get_or_create')
    def test_auto_register_not_bound(self, mock_device_id, mock_get, mock_post):
        """測試自動註冊（裝置未綁定）"""
        current_device_id = 'g' * 64
        mock_device_id.return_value = current_device_id
        
        # Mock verification (device not found)
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {'devices': []}
        mock_get.return_value = mock_get_response
        
        # Mock registration
        mock_post_response = Mock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {
            'success': True,
            'device': {'device_id': current_device_id}
        }
        mock_post.return_value = mock_post_response
        
        result = self.client.auto_register_if_needed(self.test_token)
        
        self.assertTrue(result['success'])
        self.assertFalse(result['already_bound'])


if __name__ == '__main__':
    unittest.main()
