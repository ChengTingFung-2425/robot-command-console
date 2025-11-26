"""
共用配置模組
提供環境配置載入與驗證

此模組支援 Edge 和 Server 環境的配置管理
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Environment(Enum):
    """執行環境類型"""
    EDGE = "edge"           # 邊緣設備（本地 Electron、CLI）
    SERVER = "server"       # 伺服器端（MCP API、WebUI）
    DEVELOPMENT = "dev"     # 開發環境
    TESTING = "test"        # 測試環境
    PRODUCTION = "prod"     # 生產環境


@dataclass
class BaseConfig:
    """基礎配置類別"""

    # 環境設定
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False

    # 日誌設定
    log_level: str = "INFO"
    log_format: str = "json"  # json 或 text

    # 服務識別
    service_name: str = "robot-service"
    service_version: str = "1.0.0"

    @classmethod
    def from_env(cls) -> "BaseConfig":
        """從環境變數載入配置"""
        env_str = os.environ.get("ENVIRONMENT", "dev").lower()
        env_map = {
            "edge": Environment.EDGE,
            "server": Environment.SERVER,
            "dev": Environment.DEVELOPMENT,
            "development": Environment.DEVELOPMENT,
            "test": Environment.TESTING,
            "testing": Environment.TESTING,
            "prod": Environment.PRODUCTION,
            "production": Environment.PRODUCTION,
        }

        return cls(
            environment=env_map.get(env_str, Environment.DEVELOPMENT),
            debug=os.environ.get("DEBUG", "false").lower() == "true",
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            log_format=os.environ.get("LOG_FORMAT", "json"),
            service_name=os.environ.get("SERVICE_NAME", "robot-service"),
            service_version=os.environ.get("SERVICE_VERSION", "1.0.0"),
        )


@dataclass
class EdgeConfig(BaseConfig):
    """Edge（邊緣/本地）環境配置"""

    environment: Environment = Environment.EDGE
    service_name: str = "robot-service-edge"

    # 佇列設定
    queue_max_size: int = 1000
    max_workers: int = 5
    poll_interval: float = 0.1

    # Flask 服務設定
    flask_host: str = "127.0.0.1"
    flask_port: int = 5000

    @classmethod
    def from_env(cls) -> "EdgeConfig":
        """從環境變數載入 Edge 配置"""
        base = BaseConfig.from_env()

        return cls(
            environment=Environment.EDGE,
            debug=base.debug,
            log_level=base.log_level,
            log_format=base.log_format,
            service_name=os.environ.get("SERVICE_NAME", "robot-service-edge"),
            service_version=base.service_version,
            queue_max_size=int(os.environ.get("QUEUE_MAX_SIZE", "1000")),
            max_workers=int(os.environ.get("MAX_WORKERS", "5")),
            poll_interval=float(os.environ.get("POLL_INTERVAL", "0.1")),
            flask_host=os.environ.get("FLASK_HOST", "127.0.0.1"),
            flask_port=int(os.environ.get("PORT", "5000")),
        )


@dataclass
class ServerConfig(BaseConfig):
    """Server（伺服器端）環境配置"""

    environment: Environment = Environment.SERVER
    service_name: str = "mcp-server"

    # API 設定
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS 設定
    cors_origins: list = field(default_factory=lambda: ["*"])

    # JWT 設定
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """從環境變數載入 Server 配置"""
        base = BaseConfig.from_env()

        cors_origins_str = os.environ.get("CORS_ORIGINS", "*")
        cors_origins = [o.strip() for o in cors_origins_str.split(",")]

        return cls(
            environment=Environment.SERVER,
            debug=base.debug,
            log_level=base.log_level,
            log_format=base.log_format,
            service_name=os.environ.get("SERVICE_NAME", "mcp-server"),
            service_version=base.service_version,
            api_host=os.environ.get("MCP_API_HOST", "0.0.0.0"),
            api_port=int(os.environ.get("MCP_API_PORT", "8000")),
            cors_origins=cors_origins,
            jwt_secret=os.environ.get("MCP_JWT_SECRET"),
            jwt_algorithm=os.environ.get("MCP_JWT_ALGORITHM", "HS256"),
            jwt_expiration_hours=int(os.environ.get("MCP_JWT_EXPIRATION_HOURS", "24")),
        )


def get_config() -> BaseConfig:
    """
    根據環境自動載入適當的配置

    Returns:
        EdgeConfig 或 ServerConfig
    """
    env_type = os.environ.get("ENV_TYPE", "edge").lower()

    if env_type == "server":
        return ServerConfig.from_env()
    else:
        return EdgeConfig.from_env()
