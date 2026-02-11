"""測試裝置綁定 API"""

import sys
import os
import unittest
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from WebUI.app import create_app, db
from WebUI.app.models import User


class TestDeviceBindingAPI(unittest.TestCase):
    """測試裝置綁定 API 端點"""

    def setUp(self):
        """設置測試環境"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['SECRET_KEY'] = 'test-secret-key'
        
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            
            # Create test users
            self.user1 = User(username='testuser1', email='test1@example.com', role='operator')
            self.user1.set_password('password123')
            
            self.user2 = User(username='testuser2', email='test2@example.com', role='operator')
            self.user2.set_password('password123')
            
            self.admin_user = User(username='admin', email='admin@example.com', role='admin')
            self.admin_user.set_password('admin123')
            
            db.session.add_all([self.user1, self.user2, self.admin_user])
            db.session.commit()

    def tearDown(self):
        """清理測試環境"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def get_access_token(self, username='testuser1', password='password123'):
        """獲取測試用 access token"""
        response = self.client.post('/api/auth/login', json={
            'username': username,
            'password': password
        })
        data = json.loads(response.data)
        return data.get('access_token')

    def test_register_device_success(self):
        """測試成功註冊裝置"""
        token = self.get_access_token()
        
        response = self.client.post('/api/auth/device/register',
            json={
                'device_id': 'a' * 64,  # 64 chars SHA-256
                'device_name': 'My Laptop',
                'device_type': 'laptop',
                'platform': 'Linux',
                'hostname': 'mylaptop'
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('device', data)
        self.assertEqual(data['device']['device_name'], 'My Laptop')

    def test_register_device_invalid_id(self):
        """測試註冊裝置時使用無效的 device_id"""
        token = self.get_access_token()
        
        response = self.client.post('/api/auth/device/register',
            json={
                'device_id': 'short',  # 太短
                'device_name': 'My Device'
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_register_device_duplicate(self):
        """測試重複註冊裝置"""
        token = self.get_access_token()
        device_id = 'b' * 64
        
        # First registration
        self.client.post('/api/auth/device/register',
            json={
                'device_id': device_id,
                'device_name': 'Device 1',
                'platform': 'Windows'
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        
        # Duplicate registration by same user
        response = self.client.post('/api/auth/device/register',
            json={
                'device_id': device_id,
                'device_name': 'Device 1 Updated'
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('already registered', data['message'])

    def test_register_device_conflict(self):
        """測試裝置已綁定到其他使用者"""
        token1 = self.get_access_token('testuser1', 'password123')
        token2 = self.get_access_token('testuser2', 'password123')
        device_id = 'c' * 64
        
        # User1 registers device
        self.client.post('/api/auth/device/register',
            json={'device_id': device_id, 'platform': 'Linux'},
            headers={'Authorization': f'Bearer {token1}'}
        )
        
        # User2 tries to register same device
        response = self.client.post('/api/auth/device/register',
            json={'device_id': device_id, 'platform': 'Linux'},
            headers={'Authorization': f'Bearer {token2}'}
        )
        
        self.assertEqual(response.status_code, 409)
        data = json.loads(response.data)
        self.assertIn('already registered to another user', data['error'])

    def test_register_device_limit(self):
        """測試裝置數量限制"""
        token = self.get_access_token()
        
        # Register 10 devices (max limit)
        for i in range(10):
            device_id = str(i) * 64
            self.client.post('/api/auth/device/register',
                json={'device_id': device_id, 'platform': 'Linux'},
                headers={'Authorization': f'Bearer {token}'}
            )
        
        # Try to register 11th device
        response = self.client.post('/api/auth/device/register',
            json={'device_id': 'x' * 64, 'platform': 'Linux'},
            headers={'Authorization': f'Bearer {token}'}
        )
        
        self.assertEqual(response.status_code, 429)
        data = json.loads(response.data)
        self.assertIn('Device limit exceeded', data['error'])

    def test_list_devices(self):
        """測試列出使用者裝置"""
        token = self.get_access_token()
        
        # Register 2 devices
        for i in range(2):
            device_id = str(i) * 64
            self.client.post('/api/auth/device/register',
                json={'device_id': device_id, 'device_name': f'Device {i}'},
                headers={'Authorization': f'Bearer {token}'}
            )
        
        # List devices
        response = self.client.get('/api/auth/devices',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['total'], 2)
        self.assertEqual(len(data['devices']), 2)

    def test_get_device(self):
        """測試取得特定裝置資訊"""
        token = self.get_access_token()
        device_id = 'd' * 64
        
        # Register device
        register_response = self.client.post('/api/auth/device/register',
            json={'device_id': device_id, 'device_name': 'Test Device'},
            headers={'Authorization': f'Bearer {token}'}
        )
        device_data = json.loads(register_response.data)
        device_pk = device_data['device']['id']
        
        # Get device
        response = self.client.get(f'/api/auth/device/{device_pk}',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['device']['device_name'], 'Test Device')

    def test_update_device(self):
        """測試更新裝置資訊"""
        token = self.get_access_token()
        device_id = 'e' * 64
        
        # Register device
        register_response = self.client.post('/api/auth/device/register',
            json={'device_id': device_id, 'device_name': 'Original Name'},
            headers={'Authorization': f'Bearer {token}'}
        )
        device_data = json.loads(register_response.data)
        device_pk = device_data['device']['id']
        
        # Update device
        response = self.client.put(f'/api/auth/device/{device_pk}',
            json={'device_name': 'Updated Name', 'is_trusted': True},
            headers={'Authorization': f'Bearer {token}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['device']['device_name'], 'Updated Name')
        self.assertTrue(data['device']['is_trusted'])

    def test_unbind_device(self):
        """測試解除裝置綁定"""
        token = self.get_access_token()
        device_id = 'f' * 64
        
        # Register device
        register_response = self.client.post('/api/auth/device/register',
            json={'device_id': device_id},
            headers={'Authorization': f'Bearer {token}'}
        )
        device_data = json.loads(register_response.data)
        device_pk = device_data['device']['id']
        
        # Unbind device
        response = self.client.post(f'/api/auth/device/{device_pk}/unbind',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Verify device is inactive
        get_response = self.client.get(f'/api/auth/device/{device_pk}',
            headers={'Authorization': f'Bearer {token}'}
        )
        device_info = json.loads(get_response.data)
        self.assertFalse(device_info['device']['is_active'])

    def test_delete_device_admin_only(self):
        """測試刪除裝置（僅 Admin）"""
        # Create device as user
        user_token = self.get_access_token('testuser1', 'password123')
        register_response = self.client.post('/api/auth/device/register',
            json={'device_id': 'g' * 64},
            headers={'Authorization': f'Bearer {user_token}'}
        )
        device_data = json.loads(register_response.data)
        device_pk = device_data['device']['id']
        
        # Try to delete as non-admin
        response = self.client.delete(f'/api/auth/device/{device_pk}',
            headers={'Authorization': f'Bearer {user_token}'}
        )
        self.assertEqual(response.status_code, 403)
        
        # Delete as admin
        admin_token = self.get_access_token('admin', 'admin123')
        response = self.client.delete(f'/api/auth/device/{device_pk}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        self.assertEqual(response.status_code, 200)

    def test_unauthorized_access(self):
        """測試未授權訪問"""
        response = self.client.get('/api/auth/devices')
        self.assertEqual(response.status_code, 401)


if __name__ == '__main__':
    unittest.main()
