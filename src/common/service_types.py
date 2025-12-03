"""
Service Types
共用的服務類型定義，用於服務協調器和其他模組
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class ServiceStatus(Enum):
    """服務狀態"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ServiceConfig:
    """服務配置"""
    name: str
    service_type: str
    enabled: bool = True
    auto_restart: bool = True
    max_restart_attempts: int = 3
    restart_delay_seconds: float = 2.0
    health_check_interval_seconds: float = 30.0
    startup_timeout_seconds: float = 5.0
    warmup_seconds: float = 2.0
    # 啟動異常恢復相關配置
    startup_retry_enabled: bool = True
    max_startup_retry_attempts: int = 3
    startup_retry_delay_seconds: float = 1.0
    extra_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceState:
    """服務狀態資訊"""
    config: ServiceConfig
    status: ServiceStatus = ServiceStatus.STOPPED
    restart_attempts: int = 0
    consecutive_failures: int = 0
    last_health_check: Optional[datetime] = None
    last_error: Optional[str] = None
    started_at: Optional[datetime] = None
    # 啟動重試計數
    startup_retry_count: int = 0
