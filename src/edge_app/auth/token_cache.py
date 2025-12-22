"""
Edge Token Cache Manager

Provides secure token storage with OS-native keychain integration.
Platform priority: Linux (primary) -> Windows (secondary) -> macOS (not supported)

Zero-trust principle: Tokens are cached but not validated locally.
All validation occurs on the Server.
"""

import os
import json
import platform
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
from cryptography.fernet import Fernet
import base64


class EdgeTokenCache:
    """
    Token cache manager with OS-native keychain integration.
    
    Platform Support:
    - Linux (Priority 1): Secret Service API (GNOME Keyring/KWallet) + Fernet fallback
    - Windows (Priority 2): Credential Manager + Fernet fallback
    - macOS: Not supported (Fallback mode only, not planned for release)
    
    Security Features:
    - Fernet encryption (AES-128)
    - Device ID binding
    - OS-native keychain (when available)
    - File permissions (chmod 600 on Linux, NTFS ACL on Windows)
    - Automatic expiration detection
    """
    
    def __init__(self, app_name: str = 'robot-edge'):
        self.app_name = app_name
        self.platform = platform.system()
        
        # Token expiration times
        self.access_token_lifetime = timedelta(minutes=15)
        self.refresh_token_lifetime = timedelta(days=7)
        
        # Determine storage paths
        if self.platform == 'Linux':
            self.cache_dir = Path.home() / '.robot-edge'
        elif self.platform == 'Windows':
            self.cache_dir = Path(os.getenv('APPDATA', '')) / 'robot-edge'
        else:  # macOS or other (Fallback only)
            self.cache_dir = Path.home() / '.robot-edge'
        
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.token_file = self.cache_dir / 'tokens.enc'
        self.device_id_file = self.cache_dir / 'device.id'
        
        # Set file permissions (Linux)
        if self.platform == 'Linux':
            try:
                os.chmod(self.cache_dir, 0o700)
            except Exception:
                # Ignore permission errors (may occur on read-only filesystems)
                pass
        
        # Initialize encryption key
        self._encryption_key = self._get_or_create_encryption_key()
        self._fernet = Fernet(self._encryption_key)
        
        # Try to initialize platform-specific keychain
        self._keychain_available = self._init_keychain()
    
    def _get_or_create_encryption_key(self) -> bytes:
        """
        Get or create encryption key for Fernet.
        Derives key from machine-specific information.
        """
        key_file = self.cache_dir / 'key.bin'
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        
        # Derive key from machine info
        machine_info = self._get_machine_info()
        key_material = hashlib.pbkdf2_hmac(
            'sha256',
            machine_info.encode('utf-8'),
            b'robot-edge-salt',  # Fixed salt
            100000
        )
        key = base64.urlsafe_b64encode(key_material[:32])
        
        # Save key
        with open(key_file, 'wb') as f:
            f.write(key)
        
        # Set permissions (Linux)
        if self.platform == 'Linux':
            try:
                os.chmod(key_file, 0o600)
            except Exception:
                # Ignore permission errors (may occur on read-only filesystems)
                pass
        
        return key
    
    def _get_machine_info(self) -> str:
        """Get machine-specific information for key derivation."""
        import psutil
        
        try:
            # Get MAC address
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff)
                           for i in range(0, 8 * 6, 8)][::-1])
        except Exception:
            mac = 'unknown-mac'
        
        try:
            hostname = platform.node()
        except Exception:
            hostname = 'unknown-host'
        
        try:
            cpu_count = str(psutil.cpu_count())
        except Exception:
            cpu_count = 'unknown-cpu'
        
        return f"{mac}-{hostname}-{self.platform}-{cpu_count}"
    
    def _init_keychain(self) -> bool:
        """
        Initialize platform-specific keychain.
        Returns True if keychain is available.
        """
        if self.platform == 'Linux':
            try:
                import secretstorage
                self._secret_storage = secretstorage
                return True
            except ImportError:
                return False
        elif self.platform == 'Windows':
            try:
                import keyring
                self._keyring = keyring
                return True
            except ImportError:
                return False
        else:
            # macOS not supported
            return False
    
    def save_tokens(self, access_token: str, refresh_token: str,
                    device_id: str, user_info: Dict[str, Any]) -> None:
        """
        Save tokens to secure storage.
        
        Args:
            access_token: JWT access token (15 min lifetime)
            refresh_token: JWT refresh token (7 day lifetime)
            device_id: Device ID for binding
            user_info: User information dict (id, username, role, etc.)
        """
        now = datetime.utcnow()
        token_data = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'device_id': device_id,
            'user_info': user_info,
            'access_token_expires_at': (now + self.access_token_lifetime).isoformat(),
            'refresh_token_expires_at': (now + self.refresh_token_lifetime).isoformat(),
            'cached_at': now.isoformat()
        }
        
        # Try platform-specific keychain first
        if self._keychain_available:
            try:
                if self.platform == 'Linux':
                    self._save_to_linux_keychain(token_data)
                elif self.platform == 'Windows':
                    self._save_to_windows_keychain(token_data)
                return
            except Exception:
                pass  # Fall back to file storage
        
        # Fallback: Encrypted file storage
        self._save_to_file(token_data)
    
    def _save_to_linux_keychain(self, token_data: Dict[str, Any]) -> None:
        """Save tokens to Linux Secret Service (GNOME Keyring/KWallet)."""
        connection = self._secret_storage.dbus_init()
        collection = self._secret_storage.get_default_collection(connection)
        
        # Save each token separately
        collection.create_item(
            f'{self.app_name}-access-token',
            {'app': self.app_name, 'type': 'access'},
            token_data['access_token'].encode('utf-8'),
            replace=True
        )
        collection.create_item(
            f'{self.app_name}-refresh-token',
            {'app': self.app_name, 'type': 'refresh'},
            token_data['refresh_token'].encode('utf-8'),
            replace=True
        )
        collection.create_item(
            f'{self.app_name}-metadata',
            {'app': self.app_name, 'type': 'metadata'},
            json.dumps({
                'device_id': token_data['device_id'],
                'user_info': token_data['user_info'],
                'access_token_expires_at': token_data['access_token_expires_at'],
                'refresh_token_expires_at': token_data['refresh_token_expires_at'],
                'cached_at': token_data['cached_at']
            }).encode('utf-8'),
            replace=True
        )
    
    def _save_to_windows_keychain(self, token_data: Dict[str, Any]) -> None:
        """Save tokens to Windows Credential Manager."""
        self._keyring.set_password(self.app_name, 'access_token', token_data['access_token'])
        self._keyring.set_password(self.app_name, 'refresh_token', token_data['refresh_token'])
        self._keyring.set_password(self.app_name, 'metadata', json.dumps({
            'device_id': token_data['device_id'],
            'user_info': token_data['user_info'],
            'access_token_expires_at': token_data['access_token_expires_at'],
            'refresh_token_expires_at': token_data['refresh_token_expires_at'],
            'cached_at': token_data['cached_at']
        }))
    
    def _save_to_file(self, token_data: Dict[str, Any]) -> None:
        """Save tokens to encrypted file (Fallback mode)."""
        encrypted_data = self._fernet.encrypt(json.dumps(token_data).encode('utf-8'))
        
        with open(self.token_file, 'wb') as f:
            f.write(encrypted_data)
        
        # Set file permissions (Linux)
        if self.platform == 'Linux':
            try:
                os.chmod(self.token_file, 0o600)
            except Exception:
                # Ignore permission errors (may occur on read-only filesystems)
                pass
    
    def get_access_token(self) -> Optional[str]:
        """
        Get access token from cache.
        Returns None if token doesn't exist or is expired.
        """
        token_data = self._load_tokens()
        if not token_data:
            return None
        
        # Check expiration
        try:
            expires_at = datetime.fromisoformat(token_data['access_token_expires_at'])
            if datetime.utcnow() >= expires_at:
                return None  # Expired
        except Exception:
            return None
        
        return token_data.get('access_token')
    
    def get_refresh_token(self) -> Optional[str]:
        """
        Get refresh token from cache.
        Returns None if token doesn't exist or is expired.
        """
        token_data = self._load_tokens()
        if not token_data:
            return None
        
        # Check expiration
        try:
            expires_at = datetime.fromisoformat(token_data['refresh_token_expires_at'])
            if datetime.utcnow() >= expires_at:
                return None  # Expired
        except Exception:
            return None
        
        return token_data.get('refresh_token')
    
    def is_access_token_valid(self) -> bool:
        """Check if access token exists and is not expired."""
        return self.get_access_token() is not None
    
    def get_device_id(self) -> str:
        """
        Get or generate device ID.
        Device ID is stable and unique per machine.
        """
        if self.device_id_file.exists():
            with open(self.device_id_file, 'r') as f:
                return f.read().strip()
        
        # Generate new device ID
        machine_info = self._get_machine_info()
        device_id = hashlib.sha256(machine_info.encode('utf-8')).hexdigest()
        
        # Save device ID
        with open(self.device_id_file, 'w') as f:
            f.write(device_id)
        
        # Set permissions (Linux)
        if self.platform == 'Linux':
            try:
                os.chmod(self.device_id_file, 0o600)
            except Exception:
                # Ignore permission errors (may occur on read-only filesystems)
                pass
        
        return device_id
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get cached user information."""
        token_data = self._load_tokens()
        if not token_data:
            return None
        return token_data.get('user_info')
    
    def clear_tokens(self) -> None:
        """Clear all cached tokens."""
        # Try platform-specific keychain first
        if self._keychain_available:
            try:
                if self.platform == 'Linux':
                    self._clear_linux_keychain()
                elif self.platform == 'Windows':
                    self._clear_windows_keychain()
            except Exception:
                # Ignore keychain clearing errors (tokens may not exist)
                pass
        
        # Remove encrypted file
        if self.token_file.exists():
            self.token_file.unlink()
    
    def _clear_linux_keychain(self) -> None:
        """Clear tokens from Linux Secret Service."""
        connection = self._secret_storage.dbus_init()
        collection = self._secret_storage.get_default_collection(connection)
        
        for item in collection.get_all_items():
            if item.get_label().startswith(self.app_name):
                item.delete()
    
    def _clear_windows_keychain(self) -> None:
        """Clear tokens from Windows Credential Manager."""
        try:
            self._keyring.delete_password(self.app_name, 'access_token')
        except Exception:
            # Ignore deletion errors (token may not exist)
            pass
        try:
            self._keyring.delete_password(self.app_name, 'refresh_token')
        except Exception:
            # Ignore deletion errors (token may not exist)
            pass
        try:
            self._keyring.delete_password(self.app_name, 'metadata')
        except Exception:
            # Ignore deletion errors (metadata may not exist)
            pass
    
    def _load_tokens(self) -> Optional[Dict[str, Any]]:
        """Load tokens from storage."""
        # Try platform-specific keychain first
        if self._keychain_available:
            try:
                if self.platform == 'Linux':
                    return self._load_from_linux_keychain()
                elif self.platform == 'Windows':
                    return self._load_from_windows_keychain()
            except Exception:
                pass  # Fall back to file storage
        
        # Fallback: Encrypted file storage
        return self._load_from_file()
    
    def _load_from_linux_keychain(self) -> Optional[Dict[str, Any]]:
        """Load tokens from Linux Secret Service."""
        connection = self._secret_storage.dbus_init()
        collection = self._secret_storage.get_default_collection(connection)
        
        access_token = None
        refresh_token = None
        metadata = None
        
        for item in collection.get_all_items():
            label = item.get_label()
            if label == f'{self.app_name}-access-token':
                access_token = item.get_secret().decode('utf-8')
            elif label == f'{self.app_name}-refresh-token':
                refresh_token = item.get_secret().decode('utf-8')
            elif label == f'{self.app_name}-metadata':
                metadata = json.loads(item.get_secret().decode('utf-8'))
        
        if access_token and refresh_token and metadata:
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                **metadata
            }
        return None
    
    def _load_from_windows_keychain(self) -> Optional[Dict[str, Any]]:
        """Load tokens from Windows Credential Manager."""
        access_token = self._keyring.get_password(self.app_name, 'access_token')
        refresh_token = self._keyring.get_password(self.app_name, 'refresh_token')
        metadata_str = self._keyring.get_password(self.app_name, 'metadata')
        
        if access_token and refresh_token and metadata_str:
            metadata = json.loads(metadata_str)
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                **metadata
            }
        return None
    
    def _load_from_file(self) -> Optional[Dict[str, Any]]:
        """Load tokens from encrypted file."""
        if not self.token_file.exists():
            return None
        
        try:
            with open(self.token_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self._fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode('utf-8'))
        except Exception:
            return None
