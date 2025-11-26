# Phase 2 技術規格

> 此文件詳述 Phase 2 的模組分解、實作順序與升級路徑。
> 
> **建立日期**：2025-11-26  
> **狀態**：✅ 已完成

---

## 目錄

1. [模組分解](#模組分解)
2. [實作順序](#實作順序)
3. [升級路徑](#升級路徑)
4. [API 契約](#api-契約)
5. [可觀測性](#可觀測性)
6. [安全機制](#安全機制)
7. [本地佇列](#本地佇列)

---

## 模組分解

### 1. 共用模組 (`src/common/`)

**職責**：提供 Edge 和 Server 共用的工具

| 檔案 | 功能 | 匯出 |
|------|------|------|
| `logging_utils.py` | 統一 JSON 結構化日誌 | `CustomJsonFormatter`, `setup_json_logging`, `get_logger` |
| `datetime_utils.py` | 時間處理工具 | `utc_now`, `utc_now_iso`, `parse_iso_datetime`, `format_timestamp` |
| `config.py` | 環境配置 | `EdgeConfig`, `ServerConfig`, `get_config` |

**使用範例**：

```python
# 日誌工具
from src.common.logging_utils import CustomJsonFormatter, setup_json_logging, get_logger

# 時間工具
from src.common.datetime_utils import utc_now, utc_now_iso

# 配置
from src.common.config import EdgeConfig, get_config
config = EdgeConfig.from_env()
```

### 2. 機器人服務模組 (`src/robot_service/`)

**職責**：Edge 環境的模組化背景服務

| 子目錄/檔案 | 功能 |
|-------------|------|
| `queue/` | 本地優先權佇列系統 |
| `cli/` | CLI 模式入口 |
| `electron/` | Electron 整合（Flask 適配器） |
| `utils/` | 工具函式（重導出 common） |
| `service_manager.py` | 服務協調器 |

**架構圖**：

```
src/robot_service/
├── __init__.py
├── service_manager.py      # 服務協調器
├── cli/                    # CLI 模式
│   └── __init__.py
├── electron/               # Electron 整合
│   ├── __init__.py
│   └── flask_adapter.py    # Flask API 適配器
├── queue/                  # 佇列系統
│   ├── __init__.py
│   ├── interface.py        # 佇列介面定義
│   ├── memory_queue.py     # 記憶體佇列實作
│   └── handler.py          # 訊息處理器
└── utils/                  # 工具函式
    ├── __init__.py
    ├── logging_utils.py    # 重導出 common
    └── datetime_utils.py   # 重導出 common
```

### 3. MCP 服務模組 (`MCP/`)

**職責**：Model Context Protocol 服務，提供統一 API

| 檔案 | 功能 |
|------|------|
| `api.py` | FastAPI 主應用 |
| `auth_manager.py` | 認證管理（JWT、RBAC） |
| `command_handler.py` | 指令處理 |
| `context_manager.py` | 上下文管理 |
| `llm_processor.py` | LLM 處理器 |
| `llm_provider_manager.py` | LLM 提供商管理 |
| `plugin_manager.py` | 插件管理 |
| `robot_router.py` | 機器人路由 |
| `schema_validator.py` | Schema 驗證 |
| `secret_storage.py` | 秘密儲存 |
| `logging_monitor.py` | 日誌監控 |

### 4. Electron 應用 (`electron-app/`)

**職責**：桌面應用程式介面

| 檔案 | 功能 |
|------|------|
| `main.js` | Electron 主程序 |
| `preload.js` | 安全橋接腳本 |
| `renderer/` | 前端 UI |
| `package.json` | Electron 專用依賴 |

---

## 實作順序

Phase 2 的實作遵循以下順序：

### Step 1：共用模組建立

1. 建立 `src/common/` 目錄
2. 實作 `logging_utils.py`（統一 JSON 日誌）
3. 實作 `datetime_utils.py`（時間處理工具）
4. 實作 `config.py`（EdgeConfig / ServerConfig）
5. 建立測試用例

### Step 2：機器人服務模組化

1. 建立 `src/robot_service/` 目錄結構
2. 實作 `queue/interface.py`（佇列介面）
3. 實作 `queue/memory_queue.py`（記憶體佇列）
4. 實作 `queue/handler.py`（訊息處理器）
5. 實作 `service_manager.py`（服務協調器）
6. 實作 `electron/flask_adapter.py`（Flask 適配器）
7. 建立測試用例

### Step 3：LLM 提供商整合

1. 實作 `MCP/llm_provider_base.py`（基礎類別）
2. 實作 `MCP/providers/ollama_provider.py`
3. 實作 `MCP/providers/lmstudio_provider.py`
4. 實作 `MCP/llm_provider_manager.py`
5. 建立測試用例

### Step 4：插件架構

1. 實作 `MCP/plugin_base.py`（基礎類別）
2. 實作 `MCP/plugin_manager.py`
3. 實作進階指令插件
4. 建立測試用例

### Step 5：安全強化

1. 實作 `MCP/auth_manager.py`（JWT + RBAC）
2. 實作 `MCP/secret_storage.py`（秘密儲存）
3. 更新 API 端點認證
4. 建立安全測試

### Step 6：可觀測性

1. 新增 Prometheus metrics 端點
2. 實作結構化 JSON 日誌
3. 新增 correlation ID 追蹤
4. 更新健康檢查端點

### Step 7：文檔與 CI

1. 建立 OpenAPI 規範（`openapi.yaml`）
2. 建立威脅模型（`threat-model.md`）
3. 建立安全檢查清單（`security-checklist.md`）
4. 設定 API 驗證 CI workflow

---

## 升級路徑

### 從 Phase 1 升級到 Phase 2

#### 目錄結構變更

| Phase 1 | Phase 2 |
|---------|---------|
| 根目錄 Electron 檔案 | `electron-app/` |
| `Test/` | `tests/` |
| 分散的日誌工具 | `src/common/` |
| 分散的服務邏輯 | `src/robot_service/` |

#### 匯入路徑變更

```python
# Phase 1
from flask_service import create_app

# Phase 2
from src.robot_service.electron import create_flask_app
```

#### 環境配置變更

```python
# Phase 1
PORT = os.environ.get('PORT', 5000)

# Phase 2
from src.common.config import EdgeConfig
config = EdgeConfig.from_env()
port = config.flask_port
```

### 從 Phase 2 升級到 Phase 3

Phase 3 將基於 Phase 2 的模組進行整合：

| Phase 2 模組 | Phase 3 運用 |
|-------------|-------------|
| `src/common/` | 繼續使用，擴充 Edge 專用工具 |
| `src/robot_service/queue/` | 整合至 Edge 服務層 |
| `LLMProviderManager` | 作為 Edge LLM 管理基礎 |
| `PluginManager` | 支援運行時插件熱載入 |

---

## API 契約

### OpenAPI 規範

Phase 2 建立了完整的 OpenAPI 3.1 規範（`openapi.yaml`），定義：

- 所有 API 端點
- 請求/回應格式
- 認證方案（Bearer Token）
- 錯誤回應格式

### 關鍵端點

| 端點 | 方法 | 認證 | 說明 |
|------|------|------|------|
| `/health` | GET | ❌ | 健康檢查 |
| `/metrics` | GET | ❌ | Prometheus metrics |
| `/auth/login` | POST | ❌ | 使用者登入 |
| `/auth/rotate` | POST | ✅ | Token 輪替 |
| `/command` | POST | ✅ | 建立指令 |
| `/robots` | GET | ✅ | 列出機器人 |
| `/robots/register` | POST | ✅ | 註冊機器人 |

### 資料契約

#### CommandRequest

```json
{
  "trace_id": "uuid-v4",
  "robot_id": "robot_001",
  "action": "go_forward",
  "params": {
    "distance": 100,
    "speed": 50
  },
  "timeout_ms": 10000,
  "priority": "NORMAL"
}
```

#### CommandResponse

```json
{
  "trace_id": "uuid-v4",
  "command_id": "cmd-123",
  "status": "pending",
  "timestamp": "2025-11-26T03:30:00.000Z"
}
```

---

## 可觀測性

### Prometheus Metrics

Phase 2 實作了以下 metrics：

| Metric 名稱 | 類型 | 說明 |
|------------|------|------|
| `flask_service_request_count_total` | Counter | 總請求數 |
| `flask_service_request_latency_seconds` | Histogram | 請求延遲 |
| `flask_service_error_count_total` | Counter | 錯誤數 |
| `flask_service_active_connections` | Gauge | 活躍連線數 |
| `flask_service_queue_size` | Gauge | 佇列大小 |

### 結構化日誌

所有日誌使用 JSON 格式：

```json
{
  "timestamp": "2025-11-26T03:30:00.000Z",
  "level": "INFO",
  "event": "module.name",
  "message": "Request completed",
  "service": "flask-service",
  "request_id": "uuid-v4",
  "correlation_id": "uuid-v4",
  "duration_seconds": 0.123
}
```

### Correlation ID

- 每個請求產生唯一的 `request_id`
- 跨服務追蹤使用 `correlation_id`
- 回應標頭包含 `X-Request-ID` 和 `X-Correlation-ID`

---

## 安全機制

### 認證（Authentication）

- **JWT Token**：短期 token（預設 24 小時）
- **Bearer Token**：用於 Electron-Flask 通訊
- **Token Rotation**：支援運行時輪替

### 授權（Authorization）

- **RBAC**：三種角色（admin、operator、viewer）
- **權限檢查**：每個操作前驗證權限
- **最小權限**：預設為 viewer 角色

### 秘密儲存

- **抽象層**：`SecretStorage` 介面
- **實作**：檔案型、Keychain、DPAPI（stub）
- **環境變數**：`JWT_SECRET`、`APP_TOKEN`

### 審計日誌

- 記錄所有認證嘗試
- 記錄權限檢查失敗
- 記錄敏感操作
- 包含 user_id、action、timestamp

---

## 本地佇列

### 架構

```
┌─────────────────────────────────────────────────────────────┐
│                      Queue System                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  Interface   │───►│   Handler    │───►│ Memory Queue │   │
│  │  (API 入口)  │    │  (處理邏輯)  │    │  (儲存層)    │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│                              │                               │
│                              ▼                               │
│                      ┌──────────────┐                       │
│                      │ Worker Pool  │                       │
│                      │  (執行緒池)  │                       │
│                      └──────────────┘                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 特性

- **優先權排序**：URGENT > HIGH > NORMAL > LOW
- **非同步處理**：使用 asyncio
- **Worker Pool**：可配置 worker 數量
- **離線緩衝**：網路斷線時暫存任務
- **可擴充**：介面設計支援 Redis/Kafka 替換

### 使用範例

```python
from src.robot_service.queue import MemoryQueue, QueueHandler, Message, MessagePriority

# 建立佇列
queue = MemoryQueue(max_size=1000)

# 建立處理器
handler = QueueHandler(queue=queue, processor=my_processor, max_workers=5)

# 啟動處理
await handler.start()

# 加入任務
message = Message(
    payload={"action": "go_forward"},
    priority=MessagePriority.HIGH,
    trace_id="trace-123"
)
await queue.enqueue(message)
```

---

## 驗收條件

### 功能驗收

- [x] 所有端點（除了 `/health`、`/metrics`）需要認證
- [x] 服務可獨立運行（CLI）或 Electron 管理
- [x] Metrics 端點提供 Prometheus 格式統計
- [x] 本地佇列可緩衝與重播 API 請求
- [x] Token 可在運行時輪替
- [x] 日誌覆蓋 ≥90% 請求且包含 correlation ID

### 文檔驗收

- [x] OpenAPI 規範完整
- [x] 威脅模型文件
- [x] 安全檢查清單
- [x] 可觀測性指南

### CI 驗收

- [x] OpenAPI 驗證
- [x] 安全測試
- [x] 文件檢查

---

## 參考文件

- [PHASE2_COMPLETION_SUMMARY.md](../../PHASE2_COMPLETION_SUMMARY.md) - Phase 2 完成摘要
- [observability.md](../../observability.md) - 可觀測性指南
- [security-checklist.md](../../security-checklist.md) - 安全檢查清單
- [threat-model.md](../../threat-model.md) - 威脅模型
- [openapi.yaml](../../../openapi.yaml) - OpenAPI 規範

---

**文件維護者**：開發團隊  
**最後更新**：2025-11-26
