"""
Token 加密模組
使用 Fernet (AES-128) 對稱加密
"""
import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class TokenEncryption:
    """Token 加密/解密類別"""

    def __init__(self, storage_dir: Optional[str] = None):
        """
        初始化 Token 加密器

        Args:
            storage_dir: 金鑰儲存目錄（預設為 ~/.robot-edge）
        """
        if storage_dir is None:
            storage_dir = os.path.expanduser('~/.robot-edge')

        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, mode=0o700, exist_ok=True)

        self.key_file = os.path.join(self.storage_dir, 'encryption.key')
        self.salt_file = os.path.join(self.storage_dir, 'salt')

        self._fernet: Optional[Fernet] = None

    def _get_or_create_salt(self) -> bytes:
        """
        取得或建立 salt

        Returns:
            bytes: 32 bytes 的 salt
        """
        if os.path.exists(self.salt_file):
            with open(self.salt_file, 'rb') as f:
                return f.read()

        # 生成新的 salt
        salt = os.urandom(32)
        with open(self.salt_file, 'wb') as f:
            f.write(salt)

        # 設定檔案權限（Linux）
        if os.name == 'posix':
            os.chmod(self.salt_file, 0o600)

        return salt

    def _get_or_create_key(self) -> bytes:
        """
        取得或建立加密金鑰

        使用 PBKDF2 + 機器資訊派生金鑰

        Returns:
            bytes: Fernet key (44 bytes, base64 encoded)
        """
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                return f.read()

        # 取得 salt
        salt = self._get_or_create_salt()

        # 使用 PBKDF2 派生金鑰
        # 基礎密碼：結合機器資訊（hostname + platform）
        import platform
        import socket
        base_password = f"{socket.gethostname()}-{platform.platform()}".encode()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # Fernet 需要 32 bytes
            salt=salt,
            iterations=100000,
        )
        key_material = kdf.derive(base_password)

        # 轉換為 Fernet key（base64 編碼）
        fernet_key = base64.urlsafe_b64encode(key_material)

        # 儲存金鑰
        with open(self.key_file, 'wb') as f:
            f.write(fernet_key)

        # 設定檔案權限（Linux）
        if os.name == 'posix':
            os.chmod(self.key_file, 0o600)

        return fernet_key

    def _get_fernet(self) -> Fernet:
        """
        取得 Fernet 實例

        Returns:
            Fernet: 加密器實例
        """
        if self._fernet is None:
            key = self._get_or_create_key()
            self._fernet = Fernet(key)
        return self._fernet

    def encrypt(self, data: str) -> str:
        """
        加密資料

        Args:
            data: 要加密的字串

        Returns:
            str: 加密後的字串（base64 編碼）
        """
        fernet = self._get_fernet()
        encrypted_bytes = fernet.encrypt(data.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')

    def decrypt(self, encrypted_data: str) -> str:
        """
        解密資料

        Args:
            encrypted_data: 加密的字串

        Returns:
            str: 解密後的原始字串

        Raises:
            Exception: 解密失敗（資料損壞或金鑰錯誤）
        """
        fernet = self._get_fernet()
        decrypted_bytes = fernet.decrypt(encrypted_data.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
