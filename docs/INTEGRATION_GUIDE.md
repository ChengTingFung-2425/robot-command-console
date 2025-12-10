# WebUI/MCP/Robot-Console 完整整合指南

> **建立日期**：2025-12-10  
> **版本**：v1.0  
> **狀態**：Phase 3 整合文件

---

## 📋 整合概覽

本文件說明 WebUI、MCP 和 Robot-Console 三大模組的完整整合架構、資料流向和使用方式。

### 三層架構

```
┌──────────────────────────────────────────────────────────┐
│                     WebUI Layer                          │
│  • 使用者介面（Flask + Bootstrap）                        │
│  • 機器人儀表板、指令控制中心                             │
│  • 進階指令管理                                          │
└──────────────┬───────────────────────────────────────────┘
               │ HTTP REST API / MQTT
               ↓
┌──────────────────────────────────────────────────────────┐
│                     MCP Layer                            │
│  • Model Context Protocol 服務（FastAPI）                │
│  • 指令驗證、路由、認證                                   │
│  • LLM 整合、插件系統                                     │
└──────────────┬───────────────────────────────────────────┘
               │ Queue / Direct Call / MQTT
               ↓
┌──────────────────────────────────────────────────────────┐
│                 Robot-Console Layer                      │
│  • ActionExecutor（動作執行引擎）                         │
│  • PubSubClient（MQTT 訂閱）                             │
│  • 協定適配器（HTTP/MQTT/WebSocket）                     │
└──────────────────────────────────────────────────────────┘
```

---

## 🔄 資料流向

### 1. 指令下達流程（WebUI → MCP → Robot-Console）

```
使用者操作
    ↓
WebUI (routes.py)
    ├─→ POST /commands                # 發送指令
    │   ├─→ MQTT publish              # 方式 1: 直接透過 MQTT
    │   │   └─→ Robot-Console PubSub  # 訂閱並執行
    │   │
    │   └─→ HTTP POST to MCP          # 方式 2: 透過 MCP（建議）
    │       └─→ MCP /api/command
    │           ├─→ Schema 驗證
    │           ├─→ 認證授權
    │           └─→ Robot Service Queue
    │               └─→ CommandProcessor
    │                   └─→ ActionExecutor
    │
    └─→ GET /commands/{cmd_id}        # 查詢狀態
        └─→ 從資料庫或快取返回
```

### 2. 狀態回報流程（Robot-Console → MCP → WebUI）

```
Robot-Console ActionExecutor
    ↓
執行動作並產生事件
    ↓
EventLog (trace_id, status, result)
    ↓
方式 1: MQTT publish to status topic
    └─→ WebUI MQTT subscribe
        └─→ 更新 UI（WebSocket/SSE）
        
方式 2: HTTP callback to MCP
    └─→ MCP /api/events
        └─→ WebUI polling /api/events
```

### 3. 進階指令流程

```
WebUI: 建立進階指令
    ↓
定義動作序列 {"actions": ["go_forward", "turn_left", ...]}
    ↓
儲存到資料庫（Advanced_Command 表）
    ↓
使用者執行進階指令
    ↓
WebUI 展開為動作列表
    ↓
發送到 MCP/Robot-Console（與基礎指令相同流程）
```

---

## 🔌 整合點

### 1. WebUI ↔ MCP

#### HTTP REST API

**WebUI 呼叫 MCP 端點**：

| WebUI 路由 | MCP 端點 | 用途 |
|-----------|---------|------|
| `/api/llm/status` | `GET /api/llm/connection/status` | LLM 連線狀態 |
| `/api/llm/providers` | `GET /api/llm/providers` | LLM 提供商列表 |
| `/api/llm/providers/health` | `GET /api/llm/providers/health` | LLM 健康檢查 |
| `/commands` (POST) | `POST /api/command` | 發送指令 |
| `/commands/{id}` | `GET /api/command/{id}` | 查詢指令狀態 |

**配置**：
```python
# WebUI/app/routes.py
MCP_API_URL = os.environ.get('MCP_API_URL', 'http://localhost:8000/api')
```

#### MQTT（可選）

WebUI 可透過 `mqtt_client.py` 直接發送指令到機器人，但建議透過 MCP 以獲得：
- 統一的認證授權
- Schema 驗證
- 指令歷史記錄
- 錯誤處理

### 2. MCP ↔ Robot-Console

#### 方式 1: 本地佇列（推薦）

```python
# src/robot_service/service_manager.py
from .queue import PriorityQueue, Message
from .command_processor import CommandProcessor

queue = PriorityQueue()
processor = CommandProcessor(action_dispatcher=action_executor.dispatch)

# MCP 發送指令到佇列
message = Message(
    id=str(uuid4()),
    trace_id=request.trace_id,
    payload={"actions": ["go_forward"]},
    priority=1
)
await queue.enqueue(message)

# Robot Service Worker 處理
message = await queue.dequeue()
await processor.process(message)
```

#### 方式 2: MQTT

```python
# Robot-Console/pubsub.py
client = PubSubClient(settings, executor)
client.subscribe(topic="robot/commands")

# MCP 透過 MQTT publish
mqtt_client.publish(
    topic="robot/commands",
    payload=json.dumps({"actions": ["go_forward"]})
)
```

#### 方式 3: 直接呼叫（同進程）

```python
# MCP/command_handler.py
from Robot_Console.action_executor import ActionExecutor

executor = ActionExecutor()
success = executor.execute_actions(["go_forward", "turn_left"])
```

---

## 📊 資料契約

### CommandRequest（MCP 接收）

```json
{
  "trace_id": "uuid-v4",
  "timestamp": "2025-12-10T10:30:00Z",
  "actor": {
    "type": "human",
    "id": "user-123",
    "name": "張三"
  },
  "source": "webui",
  "command": {
    "id": "cmd-xxx",
    "type": "robot.action",
    "target": {
      "robot_id": "robot_7",
      "robot_type": "humanoid"
    },
    "params": {
      "action_name": "go_forward",
      "duration_ms": 3000
    },
    "timeout_ms": 10000,
    "priority": "normal"
  },
  "auth": {
    "token": "<jwt-token>"
  }
}
```

### Robot-Console 接收格式

```json
{
  "actions": ["go_forward", "turn_left", "go_forward"]
}
```

或舊格式（向後相容）：

```json
{
  "id": 123,
  "name": "前進後左轉"
}
```

### CommandResponse（MCP 回應）

```json
{
  "trace_id": "uuid-v4",
  "timestamp": "2025-12-10T10:30:05Z",
  "command": {
    "id": "cmd-xxx",
    "status": "succeeded"
  },
  "result": {
    "data": {
      "execution_time_ms": 2850,
      "actions_executed": 3
    },
    "summary": "動作執行完成"
  }
}
```

---

## 🚀 啟動整合系統

### 方式 1: 統一啟動器（推薦）

```bash
# 一鍵啟動所有服務
python3 unified_launcher_cli.py

# 服務包含：
# - Flask API (port 5000) - Edge 本地服務
# - MCP Service (port 8000) - 指令中介層
# - WebUI (port 8080) - Web 管理介面
# - Robot Service Queue - 本地佇列處理
```

### 方式 2: 個別啟動

```bash
# 終端 1: 啟動 Flask Service
APP_TOKEN=your_token PORT=5000 python3 flask_service.py

# 終端 2: 啟動 MCP Service
cd MCP
python3 start.py

# 終端 3: 啟動 WebUI
cd WebUI
python3 microblog.py

# 終端 4: 啟動 Robot-Console PubSub（可選，如果使用 MQTT）
cd Robot-Console
python3 pubsub.py
```

### 方式 3: Electron App

```bash
# 啟動 Electron 桌面應用（Heavy 版本）
npm start

# Electron 會自動啟動 Flask 背景服務
```

### 方式 4: PyQt App（Tiny 版本）

```bash
cd qtwebview-app
python3 main.py

# PyQt 會自動啟動 Flask 服務
```

---

## 🧪 整合測試

### 端到端測試腳本

```bash
# JavaScript 整合測試（Electron POC）
node test_integration.js

# Python 整合測試（Phase 3.1）
python3 -m pytest tests/phase3/test_phase3_1_integration.py -v
```

### 手動測試流程

1. **啟動所有服務**
   ```bash
   python3 unified_launcher_cli.py
   ```

2. **檢查健康狀態**
   ```bash
   # Flask Service
   curl http://localhost:5000/health
   
   # MCP Service
   curl http://localhost:8000/health
   
   # WebUI（透過瀏覽器）
   open http://localhost:8080
   ```

3. **發送測試指令（透過 WebUI）**
   - 登入 WebUI
   - 進入「指令控制中心」
   - 選擇機器人
   - 選擇動作（如 "go_forward"）
   - 點擊「發送」

4. **驗證指令執行**
   - 在 WebUI「執行監控面板」查看狀態
   - 檢查 MCP logs：`tail -f MCP/logs/*.log`
   - 檢查 Robot-Console logs（如果獨立運行）

5. **測試進階指令**
   - 在「進階指令」頁面建立新指令
   - 定義動作序列
   - 執行並觀察結果

---

## 🔧 配置

### 環境變數

```bash
# Flask Service
export APP_TOKEN=your_secure_token
export PORT=5000

# MCP Service
export MCP_API_HOST=0.0.0.0
export MCP_API_PORT=8000
export MCP_JWT_SECRET=your_jwt_secret

# WebUI
export SECRET_KEY=your_secret_key
export SQLALCHEMY_DATABASE_URI=sqlite:///app.db
export MQTT_BROKER_HOST=localhost
export MQTT_BROKER_PORT=1883
export MCP_API_URL=http://localhost:8000/api

# Robot-Console (MQTT 模式)
export MQTT_ENDPOINT=localhost
export MQTT_PORT=1883
export MQTT_CLIENT_ID=robot_console_1
export INPUT_TOPIC=robot/commands
export OUTPUT_TOPIC=robot/status
```

### 配置檔案

```yaml
# Robot-Console/settings.yaml
mqtt_endpoint: localhost
mqtt_port: 1883
client_id: robot_console_1
input_topic: robot/commands
output_topic: robot/status
enable_legacy_decoder: false  # 停用舊格式解碼器
```

---

## 🐛 除錯指南

### 常見問題

#### 1. WebUI 無法連接到 MCP

**症狀**：WebUI LLM 狀態顯示「無法連接」

**檢查**：
```bash
# 確認 MCP 服務運行
curl http://localhost:8000/health

# 檢查 WebUI 配置
echo $MCP_API_URL
```

**解決**：
```bash
export MCP_API_URL=http://localhost:8000/api
```

#### 2. 指令發送失敗

**症狀**：指令狀態顯示「failed」

**檢查**：
```bash
# 檢查 MCP logs
tail -f MCP/logs/*.log

# 檢查 Robot Service logs
tail -f logs/robot_service.log
```

**常見原因**：
- 動作名稱無效（不在 VALID_ACTIONS 中）
- 機器人離線
- MQTT 連線中斷

#### 3. Robot-Console 未收到指令

**症狀**：指令已發送但機器人無反應

**檢查**：
```bash
# 確認 Robot-Console 運行
ps aux | grep pubsub

# 檢查 MQTT 連線
mosquitto_sub -t "robot/commands" -v
```

**解決**：
- 確認 MQTT broker 運行
- 檢查 topic 配置是否一致
- 驗證 MQTT 認證（如有）

---

## 📈 效能監控

### Prometheus Metrics

```bash
# Flask Service metrics
curl http://localhost:5000/metrics

# MCP Service metrics
curl http://localhost:8000/metrics
```

### 關鍵指標

| 指標 | 端點 | 說明 |
|------|------|------|
| `command_total` | MCP | 指令總數 |
| `command_duration_seconds` | MCP | 指令執行時間 |
| `queue_size` | Robot Service | 佇列長度 |
| `worker_active` | Robot Service | 活躍 Worker 數 |

---

## 🔐 安全考量

### 認證流程

1. **WebUI → MCP**：
   - WebUI 使用者登入取得 JWT token
   - 所有 API 請求帶上 `Authorization: Bearer <token>`
   - MCP 驗證 JWT 簽名和過期時間

2. **MCP → Robot-Console**：
   - 本地佇列：無需認證（同機器）
   - MQTT：可配置 MQTT 認證（username/password 或 TLS）

### 最佳實踐

- ✅ 使用 HTTPS/WSS 於生產環境
- ✅ 定期輪替 JWT secret 和 API tokens
- ✅ 限制 API rate limiting
- ✅ 記錄所有敏感操作（audit log）
- ✅ 使用 RBAC 控管權限

---

## 📚 相關文件

| 文件 | 說明 |
|------|------|
| [proposal.md](proposal.md) | 權威規格 |
| [architecture.md](architecture.md) | 系統架構 |
| [MASTER_PLAN.md](plans/MASTER_PLAN.md) | Phase 0-6 規劃 |
| [MCP Module](../MCP/Module.md) | MCP 模組設計 |
| [Robot-Console Module](../Robot-Console/module.md) | Robot-Console 設計 |
| [WebUI Module](../WebUI/Module.md) | WebUI 模組設計 |

---

## 🤝 貢獻指南

整合點變更需要：

1. 更新本文件的資料流向圖
2. 更新資料契約 JSON Schema
3. 新增整合測試用例
4. 更新 API 文件（OpenAPI）

---

**最後更新**：2025-12-10  
**版本**：v1.0  
**維護者**：開發團隊
