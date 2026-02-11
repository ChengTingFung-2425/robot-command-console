"""
Firmware Update Utilities
提供固件更新相關的工具函式，使用現有的 Python 套件
依賴: pywifi, paramiko, cryptography, scp, tqdm
"""
import os
import json
import hashlib
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime

# 使用現有套件
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import base64
import paramiko
from scp import SCPClient
import pywifi
from pywifi import const

logger = logging.getLogger(__name__)


class SecureConfigHandler:
    """安全配置檔案處理器 - 使用 cryptography 套件"""
    
    @staticmethod
    def derive_key(password: str, salt: bytes, iterations: int = 100000) -> bytes:
        """
        從密碼派生加密金鑰 (PBKDF2)
        使用 cryptography 套件
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
            backend=default_backend()
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    @staticmethod
    def decrypt_config(encrypted_file_path: str, user_token: str) -> Optional[Dict]:
        """
        解密配置檔案 - 使用 Fernet (cryptography)
        """
        try:
            with open(encrypted_file_path, 'rb') as f:
                data = f.read()
            
            # 檔案格式: [salt (32 bytes)][encrypted_data]
            if len(data) < 32:
                logger.error("Invalid encrypted file format")
                return None
            
            salt = data[:32]
            encrypted_data = data[32:]
            
            # 派生金鑰
            key = SecureConfigHandler.derive_key(user_token, salt)
            
            # 解密使用 Fernet
            f = Fernet(key)
            decrypted_json = f.decrypt(encrypted_data).decode()
            config = json.loads(decrypted_json)
            
            # 驗證時效性
            if 'metadata' in config and 'expires_at' in config['metadata']:
                expires_at = datetime.fromisoformat(config['metadata']['expires_at'])
                if datetime.now() > expires_at:
                    logger.error("Config file has expired")
                    return None
            
            return config.get('payload', config)
            
        except Exception as e:
            logger.error(f"Failed to decrypt config: {e}")
            return None
    
    @staticmethod
    def secure_delete(file_path: str, passes: int = 3) -> bool:
        """
        安全刪除檔案（多次覆寫）
        """
        try:
            if not os.path.exists(file_path):
                return True
            
            file_size = os.path.getsize(file_path)
            
            # 多次覆寫檔案內容
            with open(file_path, 'ba+', buffering=0) as f:
                for _ in range(passes):
                    f.seek(0)
                    f.write(os.urandom(file_size))
                    f.flush()
                    os.fsync(f.fileno())
            
            # 刪除檔案
            os.remove(file_path)
            logger.info(f"Securely deleted file: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to securely delete file: {e}")
            return False


class WiFiManager:
    """WiFi 連接管理器 - 使用 pywifi 套件（跨平台）"""
    
    def __init__(self):
        """初始化 pywifi"""
        self.wifi = pywifi.PyWiFi()
        self.iface = self.wifi.interfaces()[0] if self.wifi.interfaces() else None
    
    def connect_to_ap(self, ssid: str, password: str) -> Tuple[bool, str]:
        """
        連接到 WiFi AP - 使用 pywifi
        
        Args:
            ssid: WiFi SSID
            password: WiFi 密碼
            
        Returns:
            (是否成功, 錯誤訊息)
        """
        if not self.iface:
            return False, "No WiFi interface found"
        
        try:
            # 斷開當前連接
            self.iface.disconnect()
            
            # 創建 WiFi profile
            profile = pywifi.Profile()
            profile.ssid = ssid
            profile.auth = const.AUTH_ALG_OPEN
            profile.akm.append(const.AKM_TYPE_WPA2PSK)
            profile.cipher = const.CIPHER_TYPE_CCMP
            profile.key = password
            
            # 刪除所有舊的 profile
            self.iface.remove_all_network_profiles()
            
            # 添加新 profile
            tmp_profile = self.iface.add_network_profile(profile)
            
            # 連接
            self.iface.connect(tmp_profile)
            
            # 等待連接（最多10秒）
            import time
            for _ in range(10):
                time.sleep(1)
                if self.iface.status() == const.IFACE_CONNECTED:
                    logger.info(f"Successfully connected to {ssid}")
                    return True, "Connected successfully"
            
            return False, "Connection timeout"
            
        except Exception as e:
            logger.error(f"WiFi connection failed: {e}")
            return False, str(e)
    
    def get_connection_status(self) -> Dict[str, str]:
        """獲取當前 WiFi 連接狀態 - 使用 pywifi"""
        if not self.iface:
            return {"status": "no_interface"}
        
        try:
            status = self.iface.status()
            
            if status == const.IFACE_CONNECTED:
                # 嘗試獲取當前連接的 SSID
                profiles = self.iface.network_profiles()
                ssid = profiles[0].ssid if profiles else "Unknown"
                return {"status": "connected", "ssid": ssid}
            elif status == const.IFACE_CONNECTING:
                return {"status": "connecting"}
            else:
                return {"status": "disconnected"}
                
        except Exception as e:
            logger.error(f"Failed to get WiFi status: {e}")
            return {"status": "error", "error": str(e)}


class SSHClient:
    """SSH 客戶端 - 使用 paramiko 和 scp 套件"""
    
    def __init__(self, host: str, port: int, username: str, password: str):
        """
        初始化 SSH 客戶端 - 使用 paramiko
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client = None
    
    def connect(self) -> bool:
        """建立 SSH 連接 - 使用 paramiko"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.RejectPolicy())
            self.client.connect(
                self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10
            )
            logger.info(f"SSH connected to {self.host}")
            return True
        except Exception as e:
            logger.error(f"SSH connection failed: {e}")
            return False
    
    def upload_file(self, local_path: str, remote_path: str, progress_callback=None) -> bool:
        """
        上傳檔案 - 使用 scp 套件
        
        Args:
            local_path: 本地檔案路徑
            remote_path: 遠端檔案路徑
            progress_callback: 進度回調函式
            
        Returns:
            是否成功上傳
        """
        try:
            # 使用 scp 套件上傳檔案
            with SCPClient(self.client.get_transport(), progress=progress_callback) as scp:
                scp.put(local_path, remote_path)
            
            logger.info(f"File uploaded: {local_path} -> {remote_path}")
            return True
            
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return False
    
    def execute_command(self, command: str) -> Tuple[bool, str, str]:
        """
        執行遠端指令 - 使用 paramiko
        警告：確保 command 參數已經過適當的驗證和清理
        """
        try:
            # Note: caller should sanitize command input
            stdin, stdout, stderr = self.client.exec_command(command, timeout=60)
            exit_status = stdout.channel.recv_exit_status()
            
            stdout_text = stdout.read().decode()
            stderr_text = stderr.read().decode()
            
            return exit_status == 0, stdout_text, stderr_text
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return False, "", str(e)
    
    def close(self):
        """關閉 SSH 連接"""
        if self.client:
            self.client.close()
            logger.info("SSH connection closed")


def calculate_file_checksum(file_path: str, algorithm: str = 'sha256') -> str:
    """
    計算檔案 checksum - 使用內建 hashlib
    
    Args:
        file_path: 檔案路徑
        algorithm: 雜湊演算法 (md5, sha1, sha256)
        
    Returns:
        檔案的 checksum 字串
    """
    hash_func = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()

