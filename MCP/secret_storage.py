"""
秘密儲存抽象層
提供統一介面以支援多種秘密儲存後端
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SecretStorage(ABC):
    """秘密儲存抽象基類"""

    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        """
        獲取秘密
        
        Args:
            key: 秘密的鍵
            
        Returns:
            秘密值，如果不存在則返回 None
        """
        pass

    @abstractmethod
    def set_secret(self, key: str, value: str) -> bool:
        """
        設定秘密
        
        Args:
            key: 秘密的鍵
            value: 秘密值
            
        Returns:
            成功返回 True，失敗返回 False
        """
        pass

    @abstractmethod
    def delete_secret(self, key: str) -> bool:
        """
        刪除秘密
        
        Args:
            key: 秘密的鍵
            
        Returns:
            成功返回 True，失敗返回 False
        """
        pass

    @abstractmethod
    def list_secrets(self) -> list[str]:
        """
        列出所有秘密鍵
        
        Returns:
            秘密鍵列表
        """
        pass


class EnvironmentSecretStorage(SecretStorage):
    """
    環境變數秘密儲存
    僅支援讀取，不支援寫入和刪除
    """

    def get_secret(self, key: str) -> Optional[str]:
        """從環境變數獲取秘密"""
        value = os.getenv(key)
        if value:
            logger.debug(f"Retrieved secret from environment: {key}")
        return value

    def set_secret(self, key: str, value: str) -> bool:
        """環境變數儲存不支援設定"""
        logger.warning("EnvironmentSecretStorage does not support set_secret")
        return False

    def delete_secret(self, key: str) -> bool:
        """環境變數儲存不支援刪除"""
        logger.warning("EnvironmentSecretStorage does not support delete_secret")
        return False

    def list_secrets(self) -> list[str]:
        """環境變數儲存不支援列表"""
        logger.warning("EnvironmentSecretStorage does not support list_secrets")
        return []


class FileSecretStorage(SecretStorage):
    """
    檔案型秘密儲存
    將秘密儲存在加密的 JSON 檔案中
    
    注意：此實作使用簡單的 JSON 儲存，不包含加密
    生產環境應使用加密檔案或外部秘密管理服務
    """

    def __init__(self, file_path: str = None):
        """
        初始化檔案儲存
        
        Args:
            file_path: 秘密檔案路徑，預設為 ~/.robot-console/secrets.json
        """
        if file_path is None:
            home = Path.home()
            config_dir = home / ".robot-console"
            config_dir.mkdir(exist_ok=True)
            file_path = str(config_dir / "secrets.json")

        self.file_path = file_path
        self._ensure_file_exists()
        logger.info(f"FileSecretStorage initialized: {self.file_path}")

    def _ensure_file_exists(self):
        """確保檔案存在"""
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                json.dump({}, f)
            # 設定檔案權限為僅擁有者可讀寫
            os.chmod(self.file_path, 0o600)

    def _read_secrets(self) -> Dict[str, str]:
        """讀取所有秘密"""
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read secrets file: {e}")
            return {}

    def _write_secrets(self, secrets: Dict[str, str]) -> bool:
        """寫入所有秘密"""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(secrets, f, indent=2)
            # 確保檔案權限
            os.chmod(self.file_path, 0o600)
            return True
        except Exception as e:
            logger.error(f"Failed to write secrets file: {e}")
            return False

    def get_secret(self, key: str) -> Optional[str]:
        """從檔案獲取秘密"""
        secrets = self._read_secrets()
        value = secrets.get(key)
        if value:
            logger.debug(f"Retrieved secret from file: {key}")
        return value

    def set_secret(self, key: str, value: str) -> bool:
        """設定秘密到檔案"""
        secrets = self._read_secrets()
        secrets[key] = value
        success = self._write_secrets(secrets)
        if success:
            logger.info(f"Secret stored to file: {key}")
        return success

    def delete_secret(self, key: str) -> bool:
        """從檔案刪除秘密"""
        secrets = self._read_secrets()
        if key in secrets:
            del secrets[key]
            success = self._write_secrets(secrets)
            if success:
                logger.info(f"Secret deleted from file: {key}")
            return success
        return False

    def list_secrets(self) -> list[str]:
        """列出所有秘密鍵"""
        secrets = self._read_secrets()
        return list(secrets.keys())


class KeychainSecretStorage(SecretStorage):
    """
    macOS Keychain 秘密儲存（Stub 實作）
    
    注意：這是一個 stub 實作，用於展示介面
    實際使用需要安裝 keyring 套件並實作完整功能
    """

    def __init__(self, service_name: str = "robot-console"):
        """
        初始化 Keychain 儲存
        
        Args:
            service_name: Keychain 服務名稱
        """
        self.service_name = service_name
        logger.warning(
            "KeychainSecretStorage is a stub implementation. "
            "Install 'keyring' package for full functionality."
        )

    def get_secret(self, key: str) -> Optional[str]:
        """從 Keychain 獲取秘密（Stub）"""
        logger.warning(f"KeychainSecretStorage.get_secret called but not implemented: {key}")
        # 實際實作應該使用 keyring.get_password(self.service_name, key)
        return None

    def set_secret(self, key: str, value: str) -> bool:
        """設定秘密到 Keychain（Stub）"""
        logger.warning(f"KeychainSecretStorage.set_secret called but not implemented: {key}")
        # 實際實作應該使用 keyring.set_password(self.service_name, key, value)
        return False

    def delete_secret(self, key: str) -> bool:
        """從 Keychain 刪除秘密（Stub）"""
        logger.warning(f"KeychainSecretStorage.delete_secret called but not implemented: {key}")
        # 實際實作應該使用 keyring.delete_password(self.service_name, key)
        return False

    def list_secrets(self) -> list[str]:
        """列出所有秘密鍵（Stub）"""
        logger.warning("KeychainSecretStorage.list_secrets called but not implemented")
        return []


class DPAPISecretStorage(SecretStorage):
    """
    Windows DPAPI 秘密儲存（Stub 實作）
    
    注意：這是一個 stub 實作，用於展示介面
    實際使用需要安裝 pywin32 套件並實作完整功能
    """

    def __init__(self, storage_path: str = None):
        """
        初始化 DPAPI 儲存
        
        Args:
            storage_path: 加密資料儲存路徑
        """
        if storage_path is None:
            home = Path.home()
            config_dir = home / ".robot-console"
            config_dir.mkdir(exist_ok=True)
            storage_path = str(config_dir / "secrets.dpapi")

        self.storage_path = storage_path
        logger.warning(
            "DPAPISecretStorage is a stub implementation. "
            "Install 'pywin32' package for full functionality."
        )

    def get_secret(self, key: str) -> Optional[str]:
        """從 DPAPI 獲取秘密（Stub）"""
        logger.warning(f"DPAPISecretStorage.get_secret called but not implemented: {key}")
        # 實際實作應該使用 win32crypt.CryptUnprotectData
        return None

    def set_secret(self, key: str, value: str) -> bool:
        """設定秘密到 DPAPI（Stub）"""
        logger.warning(f"DPAPISecretStorage.set_secret called but not implemented: {key}")
        # 實際實作應該使用 win32crypt.CryptProtectData
        return False

    def delete_secret(self, key: str) -> bool:
        """從 DPAPI 刪除秘密（Stub）"""
        logger.warning(f"DPAPISecretStorage.delete_secret called but not implemented: {key}")
        return False

    def list_secrets(self) -> list[str]:
        """列出所有秘密鍵（Stub）"""
        logger.warning("DPAPISecretStorage.list_secrets called but not implemented")
        return []


class ChainedSecretStorage(SecretStorage):
    """
    鏈式秘密儲存
    按順序嘗試多個儲存後端，直到找到秘密或全部失敗
    寫入操作只會寫入到第一個支援寫入的後端
    """

    def __init__(self, storages: list[SecretStorage]):
        """
        初始化鏈式儲存
        
        Args:
            storages: 秘密儲存後端列表，按優先級排序
        """
        if not storages:
            raise ValueError("ChainedSecretStorage requires at least one storage backend")
        self.storages = storages
        logger.info(f"ChainedSecretStorage initialized with {len(storages)} backends")

    def get_secret(self, key: str) -> Optional[str]:
        """依序從多個後端獲取秘密"""
        for storage in self.storages:
            try:
                value = storage.get_secret(key)
                if value is not None:
                    logger.debug(f"Secret found in {storage.__class__.__name__}: {key}")
                    return value
            except Exception as e:
                logger.error(f"Error getting secret from {storage.__class__.__name__}: {e}")
                continue

        logger.debug(f"Secret not found in any backend: {key}")
        return None

    def set_secret(self, key: str, value: str) -> bool:
        """設定秘密到第一個支援的後端"""
        for storage in self.storages:
            try:
                if storage.set_secret(key, value):
                    logger.info(f"Secret stored in {storage.__class__.__name__}: {key}")
                    return True
            except Exception as e:
                logger.error(f"Error setting secret in {storage.__class__.__name__}: {e}")
                continue

        logger.error(f"Failed to store secret in any backend: {key}")
        return False

    def delete_secret(self, key: str) -> bool:
        """從所有後端刪除秘密"""
        success = False
        for storage in self.storages:
            try:
                if storage.delete_secret(key):
                    logger.info(f"Secret deleted from {storage.__class__.__name__}: {key}")
                    success = True
            except Exception as e:
                logger.error(f"Error deleting secret from {storage.__class__.__name__}: {e}")
                continue

        return success

    def list_secrets(self) -> list[str]:
        """列出所有後端的秘密鍵（去重）"""
        all_keys = set()
        for storage in self.storages:
            try:
                keys = storage.list_secrets()
                all_keys.update(keys)
            except Exception as e:
                logger.error(f"Error listing secrets from {storage.__class__.__name__}: {e}")
                continue

        return sorted(list(all_keys))


def create_default_storage() -> SecretStorage:
    """
    建立預設的秘密儲存
    
    使用鏈式儲存，優先順序：
    1. 環境變數（唯讀）
    2. 檔案儲存（讀寫）
    
    Returns:
        預設的秘密儲存實例
    """
    return ChainedSecretStorage([
        EnvironmentSecretStorage(),
        FileSecretStorage()
    ])
