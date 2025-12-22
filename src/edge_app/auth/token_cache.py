"""
Edge Token Cache

整合 DeviceIDGenerator、TokenEncryption 與 PlatformStorage，
提供完整的 Token 管理功能。
"""

import os
import json
import base64
import time
from typing import Optional, Dict, Any

from .device_id import DeviceIDGenerator
from .encryption import TokenEncryption
from .platform_storage import PlatformStorage


class EdgeTokenCache:
    """Edge Token 快取管理器
    
    功能：
    - Token 加密儲存（使用 PlatformStorage 或 fallback 至檔案）
    - 自動過期檢測
    - Device ID 管理
    - 使用者資訊快取
    """
    
    def __init__(self, app_name: str = "robot-edge"):
        """初始化 Edge Token Cache
        
        Args:
            app_name: 應用程式名稱（用於隔離不同應用的儲存）
        """
        self.app_name = app_name
        self._device_id_gen = DeviceIDGenerator()
        self._encryption = TokenEncryption()
        self._platform_storage = PlatformStorage(app_name)
        
        # Cache directory
        home = os.path.expanduser("~")
        self._cache_dir = os.path.join(home, f".{app_name}")
        os.makedirs(self._cache_dir, exist_ok=True)
        
        # Token file path (fallback)
        self._token_file = os.path.join(self._cache_dir, "tokens.enc")
        
        # In-memory cache
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._device_id: Optional[str] = None
        self._user_info: Optional[Dict] = None
        
        # Load tokens if exist
        self._load_tokens()
    
    def save_tokens(self, access_token: str, refresh_token: str, 
                   device_id: str, user_info: Dict) -> bool:
        """儲存 Tokens 與使用者資訊
        
        Args:
            access_token: Access Token (JWT)
            refresh_token: Refresh Token (JWT)
            device_id: Device ID
            user_info: 使用者資訊
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Store in memory
            self._access_token = access_token
            self._refresh_token = refresh_token
            self._device_id = device_id
            self._user_info = user_info
            
            # Prepare data for storage
            data = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "device_id": device_id,
                "user_info": user_info
            }
            
            data_json = json.dumps(data)
            
            # Try platform storage first
            if self._platform_storage.is_available():
                encrypted_str = self._encryption.encrypt(data_json)
                success = self._platform_storage.save_secret(
                    "tokens",
                    encrypted_str
                )
                if success:
                    return True
            
            # Fallback to file storage
            encrypted_str = self._encryption.encrypt(data_json)
            with open(self._token_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_str)
            
            # Set file permissions (chmod 600)
            try:
                os.chmod(self._token_file, 0o600)
            except:  # May fail on Windows or read-only FS
                pass
            
            return True
            
        except Exception as e:
            print(f"Error saving tokens: {e}")
            return False
    
    def get_access_token(self) -> Optional[str]:
        """取得 Access Token
        
        Returns:
            Access Token or None if not available
        """
        if not self._access_token:
            self._load_tokens()
        return self._access_token
    
    def get_refresh_token(self) -> Optional[str]:
        """取得 Refresh Token
        
        Returns:
            Refresh Token or None if not available
        """
        if not self._refresh_token:
            self._load_tokens()
        return self._refresh_token
    
    def is_access_token_valid(self) -> bool:
        """檢查 Access Token 是否有效（未過期）
        
        Returns:
            True if valid, False otherwise
        """
        if not self._access_token:
            return False
        
        try:
            # Parse JWT to get exp claim
            exp = self._parse_token_exp(self._access_token)
            if exp is None:
                return False
            
            # Check if expired
            current_time = int(time.time())
            return current_time < exp
            
        except:
            return False
    
    def is_refresh_token_valid(self) -> bool:
        """檢查 Refresh Token 是否有效（未過期）
        
        Returns:
            True if valid, False otherwise
        """
        if not self._refresh_token:
            return False
        
        try:
            # Parse JWT to get exp claim
            exp = self._parse_token_exp(self._refresh_token)
            if exp is None:
                return False
            
            # Check if expired
            current_time = int(time.time())
            return current_time < exp
            
        except:
            return False
    
    def clear_tokens(self) -> bool:
        """清除所有 Tokens 與快取
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Clear memory cache
            self._access_token = None
            self._refresh_token = None
            self._device_id = None
            self._user_info = None
            
            # Try platform storage first
            if self._platform_storage.is_available():
                self._platform_storage.delete_secret("tokens")
            
            # Remove file if exists
            if os.path.exists(self._token_file):
                os.remove(self._token_file)
            
            return True
            
        except Exception as e:
            print(f"Error clearing tokens: {e}")
            return False
    
    def get_device_id(self) -> str:
        """取得 Device ID
        
        Returns:
            Device ID (64 char hex string)
        """
        if not self._device_id:
            self._device_id = self._device_id_gen.get_or_create()
        return self._device_id
    
    def get_user_info(self) -> Optional[Dict]:
        """取得使用者資訊
        
        Returns:
            User info dict or None if not available
        """
        if not self._user_info:
            self._load_tokens()
        return self._user_info
    
    def _load_tokens(self):
        """從儲存中載入 Tokens"""
        try:
            # Try platform storage first
            if self._platform_storage.is_available():
                encrypted_str = self._platform_storage.get_secret("tokens")
                if encrypted_str:
                    data_json = self._encryption.decrypt(encrypted_str)
                    data = json.loads(data_json)
                    
                    self._access_token = data.get("access_token")
                    self._refresh_token = data.get("refresh_token")
                    self._device_id = data.get("device_id")
                    self._user_info = data.get("user_info")
                    return
            
            # Fallback to file storage
            if os.path.exists(self._token_file):
                with open(self._token_file, 'r', encoding='utf-8') as f:
                    encrypted_str = f.read()
                
                data_json = self._encryption.decrypt(encrypted_str)
                data = json.loads(data_json)
                
                self._access_token = data.get("access_token")
                self._refresh_token = data.get("refresh_token")
                self._device_id = data.get("device_id")
                self._user_info = data.get("user_info")
                
        except Exception as e:
            # Handle corrupted or invalid data
            print(f"Error loading tokens: {e}")
            self._access_token = None
            self._refresh_token = None
            self._device_id = None
            self._user_info = None
    
    def _parse_token_exp(self, token: str) -> Optional[int]:
        """解析 JWT Token 的 exp 欄位
        
        Args:
            token: JWT token string
            
        Returns:
            Expiration timestamp or None if parsing fails
        """
        try:
            # JWT format: header.payload.signature
            parts = token.split('.')
            if len(parts) != 3:
                return None
            
            # Decode payload (base64url)
            payload_b64 = parts[1]
            # Add padding if needed
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += '=' * padding
            
            # Replace URL-safe characters
            payload_b64 = payload_b64.replace('-', '+').replace('_', '/')
            
            payload_json = base64.b64decode(payload_b64).decode('utf-8')
            payload = json.loads(payload_json)
            
            return payload.get('exp')
            
        except Exception as e:
            print(f"Error parsing token exp: {e}")
            return None
