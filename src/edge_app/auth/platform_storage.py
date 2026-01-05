"""
Platform Storage Module

提供跨平台的安全 Token 儲存功能：
- Linux: Secret Service API (GNOME Keyring/KWallet)
- Windows: Credential Manager
- Fallback: 加密檔案儲存
"""

import os
import json
import platform as platform_mod
from pathlib import Path
from typing import Optional, Dict
from cryptography.fernet import Fernet


class PlatformStorage:
    """平台專用儲存管理器

    根據作業系統自動選擇最佳儲存方式：
    - Linux (優先): Secret Service API via D-Bus
    - Windows (次要): Credential Manager via keyring
    - Fallback: 加密檔案儲存
    """

    def __init__(self, app_name: str, storage_dir: Optional[str] = None):
        """初始化 Platform Storage

        Args:
            app_name: 應用程式名稱（用於隔離）
            storage_dir: 自訂儲存目錄（測試用）
        """
        self.app_name = app_name
        self.platform = platform_mod.system()
        self._use_native = False
        self._connection = None
        self._collection = None

        # 設定儲存目錄
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            if self.platform == 'Windows':
                self.storage_dir = Path(os.environ.get('APPDATA', '')) / 'robot-edge'
            else:
                self.storage_dir = Path.home() / '.robot-edge'

        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 嘗試初始化平台原生儲存
        self._init_native_storage()

    def _init_native_storage(self):
        """初始化平台原生儲存"""
        if self.platform == 'Linux':
            try:
                import secretstorage
                self._connection = secretstorage.dbus_init()
                self._collection = secretstorage.get_default_collection(self._connection)
                self._use_native = True
            except Exception:
                # Fallback to file storage
                pass  # D-Bus not available, use fallback
        elif self.platform == 'Windows':
            try:
                import keyring
                self._keyring = keyring
                self._use_native = True
            except Exception:
                # Fallback to file storage
                pass  # keyring not available, use fallback

    def is_available(self) -> bool:
        """檢查平台原生儲存是否可用

        Returns:
            True if native storage available, False otherwise
        """
        return self._use_native

    def save_secret(self, key: str, value: str) -> bool:
        """儲存 secret

        Args:
            key: Secret 鍵
            value: Secret 值

        Returns:
            True if successful, False otherwise
        """
        if self._use_native:
            if self.platform == 'Linux':
                return self._save_linux(key, value)
            elif self.platform == 'Windows':
                return self._save_windows(key, value)

        # Fallback to file storage
        return self._save_file(key, value)

    def get_secret(self, key: str) -> Optional[str]:
        """讀取 secret

        Args:
            key: Secret 鍵

        Returns:
            Secret 值或 None
        """
        if self._use_native:
            if self.platform == 'Linux':
                return self._get_linux(key)
            elif self.platform == 'Windows':
                return self._get_windows(key)

        # Fallback to file storage
        return self._get_file(key)

    def delete_secret(self, key: str) -> bool:
        """刪除 secret

        Args:
            key: Secret 鍵

        Returns:
            True if successful, False otherwise
        """
        if self._use_native:
            if self.platform == 'Linux':
                return self._delete_linux(key)
            elif self.platform == 'Windows':
                return self._delete_windows(key)

        # Fallback to file storage
        return self._delete_file(key)

    # Linux Secret Service methods

    def _save_linux(self, key: str, value: str) -> bool:
        """Linux Secret Service 儲存"""
        try:
            # Delete existing item if exists
            self._delete_linux(key)

            # Create new item
            label = f"{self.app_name}-{key}"
            attributes = {'app': self.app_name, 'key': key}
            self._collection.create_item(label, attributes, value.encode('utf-8'))
            return True
        except Exception:
            return False  # Secret Service error

    def _get_linux(self, key: str) -> Optional[str]:
        """Linux Secret Service 讀取"""
        try:
            attributes = {'app': self.app_name, 'key': key}
            items = self._collection.search_items(attributes)
            if items:
                secret = items[0].get_secret()
                return secret.decode('utf-8')
            return None
        except Exception:
            return None  # Secret Service error

    def _delete_linux(self, key: str) -> bool:
        """Linux Secret Service 刪除"""
        try:
            attributes = {'app': self.app_name, 'key': key}
            items = self._collection.search_items(attributes)
            for item in items:
                item.delete()
            return True
        except Exception:
            return False  # Secret Service error

    # Windows Credential Manager methods

    def _save_windows(self, key: str, value: str) -> bool:
        """Windows Credential Manager 儲存"""
        try:
            self._keyring.set_password(self.app_name, key, value)
            return True
        except Exception:
            return False  # Credential Manager error

    def _get_windows(self, key: str) -> Optional[str]:
        """Windows Credential Manager 讀取"""
        try:
            return self._keyring.get_password(self.app_name, key)
        except Exception:
            return None  # Credential Manager error

    def _delete_windows(self, key: str) -> bool:
        """Windows Credential Manager 刪除"""
        try:
            self._keyring.delete_password(self.app_name, key)
            return True
        except Exception:
            return False  # Credential Manager error

    # Fallback file storage methods

    def _get_secrets_file(self) -> Path:
        """取得 secrets 檔案路徑（包含 app_name）"""
        return self.storage_dir / f"secrets_{self.app_name}.enc"

    def _get_encryption_key(self) -> bytes:
        """取得或建立加密金鑰"""
        key_file = self.storage_dir / f"storage_key_{self.app_name}.key"

        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()

        # Generate new key
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)

        # Set restrictive permissions (Linux)
        if self.platform == 'Linux':
            try:
                os.chmod(key_file, 0o600)
            except Exception:
                pass  # May fail on read-only filesystem

        return key

    def _load_secrets_dict(self) -> Dict[str, str]:
        """載入 secrets 字典"""
        secrets_file = self._get_secrets_file()

        if not secrets_file.exists():
            return {}

        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)

            with open(secrets_file, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode('utf-8'))
        except Exception:
            return {}  # Corrupted or invalid file

    def _save_secrets_dict(self, secrets: Dict[str, str]) -> bool:
        """儲存 secrets 字典"""
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)

            json_data = json.dumps(secrets).encode('utf-8')
            encrypted_data = fernet.encrypt(json_data)

            secrets_file = self._get_secrets_file()
            with open(secrets_file, 'wb') as f:
                f.write(encrypted_data)

            # Set restrictive permissions (Linux)
            if self.platform == 'Linux':
                try:
                    os.chmod(secrets_file, 0o600)
                except Exception:
                    pass  # May fail on read-only filesystem

            return True
        except Exception:
            return False  # File write error

    def _save_file(self, key: str, value: str) -> bool:
        """檔案儲存模式 - 儲存"""
        secrets = self._load_secrets_dict()
        secrets[key] = value
        return self._save_secrets_dict(secrets)

    def _get_file(self, key: str) -> Optional[str]:
        """檔案儲存模式 - 讀取"""
        secrets = self._load_secrets_dict()
        return secrets.get(key)

    def _delete_file(self, key: str) -> bool:
        """檔案儲存模式 - 刪除"""
        secrets = self._load_secrets_dict()
        if key in secrets:
            del secrets[key]
            return self._save_secrets_dict(secrets)
        return True  # Key doesn't exist, consider success
