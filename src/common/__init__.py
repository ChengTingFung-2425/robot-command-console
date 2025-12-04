"""
共用模組
提供 Edge（本地/邊緣）和 Server（伺服器端）環境共用的工具與類別

此模組包含：
- logging_utils: 統一的 JSON 結構化日誌
- datetime_utils: 時間處理工具
- config: 共用配置載入器
- service_types: 服務類型定義
- state_store: 本地狀態存儲
- event_bus: 事件匯流排
- shared_state: 服務間狀態共享管理器
- network_monitor: 網路連線監控
- connection_manager: 服務連線管理

環境隔離：
- Edge: 運行於本地/邊緣設備（Electron、CLI）
- Server: 運行於伺服器端（MCP API、WebUI）
"""

from .logging_utils import CustomJsonFormatter, setup_json_logging, get_logger
from .datetime_utils import utc_now, utc_now_iso, parse_iso_datetime, format_timestamp, seconds_since, is_expired
from .config import (
    Environment,
    BaseConfig,
    EdgeConfig,
    ServerConfig,
    get_config,
)
from .service_types import (
    ServiceStatus,
    ServiceConfig,
    ServiceState,
)
from .state_store import (
    LocalStateStore,
    StateEntry,
)
from .event_bus import (
    LocalEventBus,
    Event,
    Subscription,
    EventHandler,
)
from .shared_state import (
    SharedStateManager,
    StateKeys,
    EventTopics,
    RobotStatus,
    QueueStatus,
)
from .token_manager import (
    TokenManager,
    TokenInfo,
    TokenRotationEvent,
    get_edge_token_manager,
    reset_edge_token_manager,
)
from .network_monitor import (
    NetworkMonitor,
    NetworkStatus,
    NetworkState,
    get_network_monitor,
    reset_network_monitor,
)
from .connection_manager import (
    ConnectionManager,
    ConnectionPool,
    ConnectionStatus,
    ConnectionState,
)

__version__ = "1.0.0"
__all__ = [
    # 日誌工具
    "CustomJsonFormatter",
    "setup_json_logging",
    "get_logger",
    # 時間工具
    "utc_now",
    "utc_now_iso",
    "parse_iso_datetime",
    "format_timestamp",
    "seconds_since",
    "is_expired",
    # 配置
    "Environment",
    "BaseConfig",
    "EdgeConfig",
    "ServerConfig",
    "get_config",
    # 服務類型
    "ServiceStatus",
    "ServiceConfig",
    "ServiceState",
    # 狀態存儲
    "LocalStateStore",
    "StateEntry",
    # 事件匯流排
    "LocalEventBus",
    "Event",
    "Subscription",
    "EventHandler",
    # 共享狀態管理
    "SharedStateManager",
    "StateKeys",
    "EventTopics",
    "RobotStatus",
    "QueueStatus",
    # Token 管理
    "TokenManager",
    "TokenInfo",
    "TokenRotationEvent",
    "get_edge_token_manager",
    "reset_edge_token_manager",
    # 網路監控
    "NetworkMonitor",
    "NetworkStatus",
    "NetworkState",
    "get_network_monitor",
    "reset_network_monitor",
    # 連線管理
    "ConnectionManager",
    "ConnectionPool",
    "ConnectionStatus",
    "ConnectionState",
]
