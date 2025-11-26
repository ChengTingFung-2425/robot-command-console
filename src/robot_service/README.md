# Robot Service Module

模組化的機器人指令服務，支援 Electron 整合與獨立 CLI 模式。

## 概覽

Robot Service 提供：

- **模組化架構**：清晰的 API 界限與職責分離
- **服務協調器**：管理多個服務的啟動、停止與健康檢查
- **本地佇列系統**：記憶體內實作，可擴展至 Redis/Kafka
- **雙模式運行**：Electron 整合模式與獨立 CLI 模式
- **優先權佇列**：4 個等級的訊息優先權
- **非同步處理**：多工作協程並行處理
- **可觀測性**：結構化日誌與 Prometheus metrics

## 架構

```
src/robot_service/
├── __init__.py              # 模組入口
├── README.md                # 本文件
├── service_coordinator.py   # 服務協調器
├── service_manager.py       # 服務管理器
├── queue/                   # 佇列模組
│   ├── __init__.py
│   ├── interface.py         # 佇列抽象介面
│   ├── memory_queue.py      # 記憶體佇列實作
│   └── handler.py           # 佇列處理器
├── electron/                # Electron 整合模組
│   ├── __init__.py
│   └── flask_adapter.py     # Flask 適配器
└── cli/                     # CLI 模組
    ├── __init__.py
    └── runner.py            # CLI 執行器
```

## 服務協調器

服務協調器 (`ServiceCoordinator`) 負責管理多個服務的生命週期：

### 核心功能

- **服務註冊**：註冊、取消註冊服務
- **啟動/停止**：單個或批量啟動/停止服務
- **健康檢查**：定期檢查服務健康狀態
- **自動重啟**：失敗的服務可自動重啟
- **告警通知**：健康異常時發送告警

### 基本用法

```python
import asyncio
from robot_service.service_coordinator import (
    ServiceCoordinator,
    ServiceConfig,
    QueueService,
)

async def main():
    # 建立服務協調器
    coordinator = ServiceCoordinator(
        health_check_interval=30.0,  # 健康檢查間隔（秒）
        max_restart_attempts=3,       # 最大重啟嘗試次數
        restart_delay=2.0,            # 重啟延遲（秒）
        alert_threshold=3,            # 連續失敗閾值
    )
    
    # 建立佇列服務
    queue_service = QueueService(
        queue_max_size=1000,
        max_workers=5,
        poll_interval=0.1,
    )
    
    # 配置服務
    queue_config = ServiceConfig(
        name="queue_service",
        service_type="QueueService",
        enabled=True,
        auto_restart=True,
        max_restart_attempts=3,
    )
    
    # 註冊服務
    coordinator.register_service(queue_service, queue_config)
    
    # 啟動服務協調器（啟動所有服務並開始健康檢查）
    await coordinator.start()
    
    # 查看服務狀態
    status = coordinator.get_services_status()
    print(status)
    
    # ... 執行業務邏輯 ...
    
    # 停止服務協調器
    await coordinator.stop()

asyncio.run(main())
```

### 自訂服務

您可以實作 `ServiceBase` 介面來建立自訂服務：

```python
from robot_service.service_coordinator import ServiceBase
from typing import Any, Dict, Optional

class MyCustomService(ServiceBase):
    """自訂服務範例"""
    
    def __init__(self):
        self._running = False
    
    @property
    def name(self) -> str:
        return "my_custom_service"
    
    async def start(self) -> bool:
        """啟動服務"""
        self._running = True
        # 初始化邏輯
        return True
    
    async def stop(self, timeout: Optional[float] = None) -> bool:
        """停止服務"""
        self._running = False
        # 清理邏輯
        return True
    
    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        return {
            "status": "healthy" if self._running else "stopped",
            "details": {...}
        }
    
    @property
    def is_running(self) -> bool:
        return self._running
```

### 告警回呼

設定告警回呼以接收服務健康問題通知：

```python
async def alert_callback(title: str, body: str, context: dict):
    """處理告警"""
    print(f"[告警] {title}: {body}")
    # 可以發送到通知系統、記錄到日誌等

coordinator.set_alert_callback(alert_callback)
```

## 快速開始

### Electron 整合模式

在 `flask_service.py` 中：

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from robot_service.electron import create_flask_app
from robot_service.service_manager import ServiceManager

# 建立服務管理器
service_manager = ServiceManager(
    queue_max_size=1000,
    max_workers=5,
)

# 啟動服務
await service_manager.start()

# 建立 Flask 應用
app = create_flask_app(
    service_manager=service_manager,
    app_token=os.environ.get('APP_TOKEN'),
)

# 執行
app.run(host='127.0.0.1', port=5000)
```

### 獨立 CLI 模式

```bash
# 使用預設設定
python3 run_service_cli.py

# 自訂配置
python3 run_service_cli.py \
  --queue-size 2000 \
  --workers 10 \
  --poll-interval 0.05 \
  --health-check-interval 60.0 \
  --log-level DEBUG
```

CLI 模式現在使用 `ServiceCoordinator` 來管理服務，提供：
- 定期健康檢查
- 自動服務重啟
- 結構化狀態報告

## API 端點

### 健康檢查

```bash
GET /health
```

回應：
```json
{
  "status": "healthy",
  "service": "robot-command-console-flask",
  "service_manager": {
    "status": "healthy",
    "started": true,
    "handler": {
      "status": "healthy",
      "running": true,
      "worker_count": 5,
      "queue": {
        "status": "healthy",
        "type": "memory",
        "total_size": 0
      }
    }
  }
}
```

### 提交指令

```bash
POST /api/command
Authorization: Bearer <token>
Content-Type: application/json

{
  "command": "move_forward",
  "robot_id": "robot-001",
  "priority": "NORMAL",
  "trace_id": "trace-123"
}
```

回應：
```json
{
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "request_id": "..."
}
```

### 佇列統計

```bash
GET /api/queue/stats
Authorization: Bearer <token>
```

回應：
```json
{
  "status": "healthy",
  "type": "memory",
  "queue_sizes": {
    "URGENT": 0,
    "HIGH": 0,
    "NORMAL": 2,
    "LOW": 0
  },
  "total_size": 2,
  "max_size": 1000,
  "statistics": {
    "total_enqueued": 10,
    "total_dequeued": 8,
    "total_acked": 8,
    "total_nacked": 0
  }
}
```

### Metrics

```bash
GET /metrics
```

Prometheus 格式的 metrics。

## 佇列系統

### 訊息格式

```python
from robot_service.queue import Message, MessagePriority

message = Message(
    payload={"command": "move_forward", "robot_id": "robot-001"},
    priority=MessagePriority.NORMAL,
    trace_id="trace-123",
    correlation_id="corr-456",
    max_retries=3,
    timeout_seconds=30,
)
```

### 優先權等級

1. **URGENT** - 緊急指令（例：緊急停止）
2. **HIGH** - 高優先權指令（例：安全相關）
3. **NORMAL** - 一般指令（預設）
4. **LOW** - 低優先權指令（例：統計、日誌）

### 自訂處理器

```python
from robot_service.queue import Message

async def custom_processor(message: Message) -> bool:
    """自訂訊息處理器"""
    try:
        # 處理訊息
        command = message.payload.get("command")
        robot_id = message.payload.get("robot_id")
        
        # 執行指令邏輯
        result = await execute_command(command, robot_id)
        
        return result.success
    except Exception as e:
        logger.error(f"Error: {e}")
        return False

# 使用自訂處理器
await service_manager.start(processor=custom_processor)
```

## 擴展

### Redis Queue (未來)

```python
from robot_service.queue import RedisQueue

queue = RedisQueue(
    host='localhost',
    port=6379,
    db=0,
)
```

### Kafka Queue (未來)

```python
from robot_service.queue import KafkaQueue

queue = KafkaQueue(
    bootstrap_servers=['localhost:9092'],
    topic='robot-commands',
)
```

## 測試

```bash
# 執行所有測試
python3 -m pytest tests/test_queue_system.py tests/test_service_coordinator.py -v

# 執行佇列系統測試
python3 -m pytest tests/test_queue_system.py -v

# 執行服務協調器測試
python3 -m pytest tests/test_service_coordinator.py -v
```

## 監控

### 結構化日誌

所有元件輸出 JSON 格式日誌：

```json
{
  "timestamp": "2025-11-20T02:16:34.246Z",
  "level": "INFO",
  "event": "robot_service.queue",
  "message": "Message enqueued",
  "message_id": "...",
  "priority": "NORMAL",
  "trace_id": "trace-123"
}
```

### Prometheus Metrics

- `flask_service_queue_size` - 佇列大小
- `flask_service_request_count_total` - 請求計數
- `flask_service_request_latency_seconds` - 請求延遲
- `flask_service_error_count_total` - 錯誤計數

## 相關文件

- [Queue Architecture](../../docs/queue-architecture.md) - 詳細架構說明
- [測試](../../Test/test_queue_system.py) - 單元測試

## 貢獻

歡迎提交 issue 與 PR。請遵守現有程式碼風格與測試規範。

## 授權

MIT License
