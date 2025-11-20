"""
MCP 服務設定管理
"""

import os
from typing import Any, Dict, Optional


class MCPConfig:
    """MCP 服務設定"""
    
    # API 設定
    API_HOST = os.getenv("MCP_API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("MCP_API_PORT", "8000"))
    
    # 資料庫設定
    DATABASE_URL = os.getenv("MCP_DATABASE_URL", "sqlite:///./mcp.db")
    
    # Redis 設定（用於分散式鎖與快取）
    REDIS_URL = os.getenv("MCP_REDIS_URL", "redis://localhost:6379/0")
    
    # 認證設定
    JWT_SECRET = os.getenv("MCP_JWT_SECRET", "change-this-secret-key")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRATION_HOURS = int(os.getenv("MCP_JWT_EXPIRATION_HOURS", "24"))
    
    # 指令處理設定
    COMMAND_TIMEOUT_MS = 10000  # 預設超時 10 秒
    MAX_RETRY_ATTEMPTS = 3
    RETRY_BACKOFF_BASE_MS = 1000
    RETRY_BACKOFF_MAX_MS = 30000
    
    # 機器人設定
    ROBOT_HEARTBEAT_INTERVAL_SEC = 30
    ROBOT_OFFLINE_THRESHOLD_SEC = 120
    
    # 日誌設定
    LOG_LEVEL = os.getenv("MCP_LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    
    # CORS 設定
    CORS_ORIGINS = os.getenv("MCP_CORS_ORIGINS", "*").split(",")
    
    # SSL 設定
    SSL_VERIFY = os.getenv("MCP_SSL_VERIFY", "true").lower() in ("true", "1", "yes")
    
    # 秘密儲存設定
    SECRET_STORAGE_BACKEND = os.getenv("MCP_SECRET_STORAGE_BACKEND", "file")  # file, keychain, dpapi, chained
    SECRET_STORAGE_FILE_PATH = os.getenv("MCP_SECRET_STORAGE_FILE_PATH")  # None = default path
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """取得所有設定"""
        return {
            k: v for k, v in cls.__dict__.items()
            if not k.startswith("_") and k.isupper()
        }
    
    @classmethod
    def get_secret_storage(cls):
        """
        獲取秘密儲存實例
        
        Returns:
            SecretStorage 實例
        """
        from .secret_storage import (
            FileSecretStorage,
            KeychainSecretStorage,
            DPAPISecretStorage,
            create_default_storage
        )
        
        backend = cls.SECRET_STORAGE_BACKEND.lower()
        
        if backend == "file":
            return FileSecretStorage(cls.SECRET_STORAGE_FILE_PATH)
        elif backend == "keychain":
            return KeychainSecretStorage()
        elif backend == "dpapi":
            return DPAPISecretStorage()
        elif backend == "chained":
            return create_default_storage()
        else:
            # 預設使用鏈式儲存
            return create_default_storage()
