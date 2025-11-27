# 統一啟動器開發指南

> **建立日期**：2025-11-27  
> **版本**：Phase 3.1.3  
> **狀態**：✅ 完成

## 概述

統一啟動器是 Phase 3.1 的核心功能，提供一鍵啟動所有服務與健康檢查能力。

## 架構

```
┌─────────────────────────────────────────────────────────────┐
│                   UnifiedLauncher                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  ProcessService │  │  ProcessService │  │ QueueService│ │
│  │  (Flask API)    │  │  (MCP Service)  │  │ (Internal)  │ │
│  │  Port: 5000     │  │  Port: 8000     │  │             │ │
│  └────────┬────────┘  └────────┬────────┘  └──────┬──────┘ │
│           │                    │                   │        │
│  ┌────────┴────────────────────┴───────────────────┴──────┐ │
│  │                   ServiceCoordinator                    │ │
│  │  • 服務生命週期管理                                     │ │
│  │  • 健康檢查協調                                         │ │
│  │  • 自動重啟與告警                                       │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 使用方式

### CLI 啟動

```bash
# 基本啟動
python3 unified_launcher_cli.py

# 調整日誌等級
python3 unified_launcher_cli.py --log-level DEBUG

# 自訂健康檢查間隔
python3 unified_launcher_cli.py --health-check-interval 60

# 調整重啟參數
python3 unified_launcher_cli.py --max-restart-attempts 5 --restart-delay 3.0
```

### 環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `APP_TOKEN` | Flask API 認證 token | 自動生成安全 token |
| `PORT` | Flask API 端口 | 5000 |
| `MCP_API_HOST` | MCP 服務主機 | 127.0.0.1 |
| `MCP_API_PORT` | MCP 服務端口 | 8000 |

### 程式碼使用

```python
from robot_service.unified_launcher import UnifiedLauncher

# 建立啟動器
launcher = UnifiedLauncher(
    health_check_interval=30.0,
    max_restart_attempts=3,
    restart_delay=2.0,
)

# 註冊預設服務
launcher.register_default_services()

# 啟動所有服務
await launcher.start_all()

# 健康檢查
result = await launcher.health_check_all()

# 停止所有服務
await launcher.stop_all()
```

## 服務配置

### ProcessServiceConfig

```python
from robot_service.unified_launcher import ProcessServiceConfig, ServiceType

config = ProcessServiceConfig(
    name="my_service",
    service_type=ServiceType.FLASK_API,
    command=["python3", "my_service.py"],
    port=5001,
    health_url="http://127.0.0.1:5001/health",
    working_dir="/path/to/dir",
    env={"MY_VAR": "value"},
    startup_timeout_seconds=15.0,
    health_check_timeout_seconds=5.0,
    enabled=True,
)
```

### 自訂服務註冊

```python
launcher = UnifiedLauncher()

# 註冊自訂服務
launcher.register_process_service(config)

# 或使用預設服務
launcher.register_default_services()
```

## 健康檢查

### 機制

1. 服務啟動後透過 HTTP 健康檢查確認就緒
2. 定期健康檢查監控服務狀態
3. 連續失敗達閾值時觸發告警和自動重啟

### 健康檢查回應格式

服務需提供 `/health` 端點，回應格式：

```json
{
  "status": "healthy",
  "service": "service-name",
  "timestamp": "2025-11-27T08:00:00+00:00"
}
```

## 預設服務

| 服務 | 類型 | 端口 | 健康檢查 |
|------|------|------|----------|
| Flask API | `flask-api` | 5000 | `/health` |
| MCP Service | `mcp-service` | 8000 | `/health` |
| Queue Service | `queue` | (內部) | ServiceManager |

## 測試

```bash
# 執行統一啟動器測試
python3 -m pytest tests/test_unified_launcher_phase3.py -v
```

## 相關文件

- [架構文件](../architecture.md)
- [Phase 3 規劃](../plans/PHASE3_EDGE_ALL_IN_ONE.md)
- [專案記憶](../PROJECT_MEMORY.md)

## 經驗教訓

### HTTP 會話重用

使用共享的 `aiohttp.ClientSession` 進行健康檢查，避免每次建立新會話的開銷。

### 競態條件防護

在非同步環境中存取可能為 None 的屬性前，先儲存引用再檢查。

### 安全 Token 生成

使用 `secrets.token_hex()` 生成加密安全的隨機 token，避免硬編碼預設值。

---

**維護者**：開發團隊  
**最後更新**：2025-11-27
