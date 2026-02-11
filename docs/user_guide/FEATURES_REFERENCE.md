# 功能完整參考

> **最後更新**：2025-12-22  
> **適用版本**：v1.0.0+

本文件提供 Robot Command Console 所有功能的完整說明。

---

## 📑 目錄

- [核心功能](#核心功能)
  - [系統狀態監控](#系統狀態監控)
  - [健康檢查](#健康檢查)
  - [雲端同步狀態](#雲端同步狀態)
- [機器人管理](#機器人管理)
- [指令執行](#指令執行)
- [批次操作](#批次操作)
- [LLM 整合](#llm-整合)
- [服務管理](#服務管理)
- [監控與日誌](#監控與日誌)
- [安全與權限](#安全與權限)
- [整合與 API](#整合與-api)

---

## 核心功能

### 系統狀態監控

**功能說明**：即時顯示所有服務與機器人的狀態。

**存取方式**：
- **WebUI**：首頁「系統狀態」面板
- **TUI**：左上角 "Services" 和 "Robot Status" 區塊
- **API**：`GET /v1/status`

**顯示資訊**：
- 服務運行狀態（MCP、Flask、Queue）
- 機器人連線狀態
- 系統資源使用（CPU、記憶體、佇列深度）
- 最近執行的指令

**狀態指示**：
- 🟢 綠色：正常運行
- 🟡 黃色：警告（高負載、連線不穩）
- 🔴 紅色：錯誤（服務停止、連線失敗）

---

### 健康檢查

**功能說明**：定期檢查系統各元件健康狀態。

**檢查項目**：
- 服務可用性（HTTP 200 回應）
- 資料庫連線
- 佇列系統狀態
- 機器人連線狀態

**使用方式**：

**API**：
```bash
curl http://localhost:5000/health
curl http://localhost:8000/health
```

**回應範例**：
```json
{
  "status": "healthy",
  "timestamp": "2025-12-22T10:00:00Z",
  "services": {
    "database": {"status": "ok", "latency_ms": 5},
    "queue": {"status": "ok", "depth": 10, "capacity": 1000},
    "robot_connections": {"status": "ok", "connected": 3, "total": 3}
  },
  "uptime_seconds": 86400
}
```

---

### 雲端同步狀態

**功能說明**：即時顯示雲端同步服務的連線狀態與離線緩衝區資訊。

**存取方式**：
- **Edge UI**：首頁「☁️ 雲端同步狀態」面板
- **API**：`GET /api/edge/sync/status`

**顯示資訊**：
- **網路連線**：顯示當前網路連線狀態（在線/離線）
- **佇列服務**：顯示雲端佇列服務可用性狀態
- **緩衝區**：顯示離線緩衝區中待同步的項目數量
- **最後同步**：顯示最後一次成功同步的時間

**狀態指示**：
- 🟢 綠色（在線/可用）：系統正常運作，可即時同步
- 🟡 黃色（離線）：網路離線，指令將緩衝至本地
- 🔴 紅色（錯誤）：服務不可用或發生錯誤

**API 回應範例**：
```json
{
  "network": {
    "online": true,
    "status": "online"
  },
  "services": {
    "mcp": {
      "available": true,
      "status": "available"
    },
    "queue": {
      "available": true,
      "status": "available"
    }
  },
  "buffers": {
    "command": {
      "pending": 0,
      "failed": 0,
      "total_buffered": 125,
      "total_sent": 123
    },
    "sync": {
      "pending": 0,
      "failed": 0,
      "total_buffered": 45,
      "total_sent": 45
    }
  },
  "sync_enabled": true,
  "last_sync": "2026-02-11T08:00:00Z"
}
```

**使用情境**：
- **離線工作**：網路斷線時，系統自動將指令緩衝至本地 SQLite
- **自動同步**：網路恢復後，系統自動將緩衝的指令同步至雲端
- **狀態監控**：隨時了解有多少指令待同步，確保資料完整性

**注意事項**：
- 緩衝區會定期自動同步（預設每 10 秒檢查一次）
- 頁面會自動更新狀態，無需手動重新整理
- 離線模式下所有指令都會被緩衝，不會遺失

---

## 機器人管理

### 新增機器人

**功能說明**：註冊新的機器人到系統。

**步驟**：

**WebUI**：
1. 側邊欄選擇「機器人」
2. 點擊「新增機器人」按鈕
3. 填寫表單：
   - **名稱**：識別名稱（例如：`robot-001`）
   - **IP 地址**：機器人網路位址
   - **埠號**：通訊埠（預設 `8080`）
   - **協定**：HTTP / MQTT / WebSocket
   - **描述**：可選，機器人說明
4. 點擊「測試連線」
5. 連線成功後點擊「儲存」

**API**：
```bash
curl -X POST http://localhost:8000/v1/robots \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "robot_id": "robot-001",
    "name": "測試機器人",
    "ip": "192.168.1.100",
    "port": 8080,
    "protocol": "http"
  }'
```

---

### 編輯機器人資訊

**功能說明**：修改已註冊機器人的配置。

**可修改項目**：
- 名稱與描述
- 網路位址（IP、埠號）
- 協定類型
- 連線參數（timeout、重試次數）

**WebUI**：
1. 在機器人列表找到目標機器人
2. 點擊「編輯」按鈕
3. 修改欄位
4. 點擊「儲存」

**API**：
```bash
curl -X PUT http://localhost:8000/v1/robots/robot-001 \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"port": 8081}'
```

---

### 刪除機器人

**功能說明**：從系統移除機器人註冊。

**注意事項**：
- ⚠️ 刪除前確認沒有執行中的指令
- 歷史記錄會保留（可選擇一併刪除）

**WebUI**：
1. 找到目標機器人
2. 點擊「刪除」按鈕
3. 確認刪除

**API**：
```bash
curl -X DELETE http://localhost:8000/v1/robots/robot-001 \
  -H "Authorization: Bearer $TOKEN"
```

---

### 機器人狀態查詢

**功能說明**：查詢機器人即時狀態。

**資訊包含**：
- 連線狀態（已連線 / 未連線）
- 電量百分比
- 當前模式（Standby / Active / Charging）
- 最後心跳時間
- 執行中的指令

**API**：
```bash
curl http://localhost:8000/v1/robots/robot-001/status \
  -H "Authorization: Bearer $TOKEN"
```

**回應範例**：
```json
{
  "robot_id": "robot-001",
  "status": "connected",
  "battery": 85,
  "mode": "active",
  "last_heartbeat": "2025-12-22T10:00:00Z",
  "current_command": {
    "command_id": "cmd-123",
    "action": "go_forward",
    "progress": 50
  }
}
```

---

## 指令執行

### 基本指令執行

**功能說明**：向機器人發送單一動作指令。

**WebUI 使用**：
1. 選擇目標機器人
2. 在「指令輸入」區域輸入動作名稱
3. 點擊「執行」按鈕
4. 查看執行結果

**TUI 使用**：
```
# 發送到預設機器人
go_forward

# 指定機器人
robot-002:turn_left

# 廣播到所有機器人
all:stand
```

**API 使用**：
```bash
curl -X POST http://localhost:8000/v1/commands \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "robot-001",
    "action": "go_forward",
    "params": {},
    "timeout_ms": 30000
  }'
```

---

### 帶參數的指令

**功能說明**：執行需要參數的複雜指令。

**範例**：

**移動到指定座標**：
```json
{
  "target": "robot-001",
  "action": "move_to",
  "params": {
    "x": 100,
    "y": 50,
    "speed": 0.5
  }
}
```

**調整機器人姿勢**：
```json
{
  "target": "robot-001",
  "action": "set_pose",
  "params": {
    "roll": 0,
    "pitch": 10,
    "yaw": 45
  }
}
```

---

### 指令歷史查詢

**功能說明**：查看過去執行的指令記錄。

**查詢條件**：
- 時間範圍
- 目標機器人
- 執行狀態（成功 / 失敗 / 執行中）
- 動作類型

**WebUI**：
1. 側邊欄選擇「指令歷史」
2. 設定篩選條件
3. 點擊「搜尋」

**API**：
```bash
# 查詢最近 100 條記錄
curl "http://localhost:8000/v1/commands?limit=100" \
  -H "Authorization: Bearer $TOKEN"

# 篩選特定機器人
curl "http://localhost:8000/v1/commands?robot_id=robot-001" \
  -H "Authorization: Bearer $TOKEN"

# 篩選時間範圍
curl "http://localhost:8000/v1/commands?start=2025-12-22T00:00:00Z&end=2025-12-22T23:59:59Z" \
  -H "Authorization: Bearer $TOKEN"
```

---

### 指令取消

**功能說明**：中止正在執行的指令。

**使用場景**：
- 指令執行時間過長
- 機器人行為異常
- 誤發指令需要撤銷

**WebUI**：
1. 在「指令歷史」找到執行中的指令
2. 點擊「取消」按鈕
3. 確認取消

**TUI**：
```
system:cancel <command_id>
```

**API**：
```bash
curl -X POST http://localhost:8000/v1/commands/cmd-123/cancel \
  -H "Authorization: Bearer $TOKEN"
```

---

## 批次操作

### 批次指令執行

**功能說明**：一次執行多個指令序列。

**使用方式**：

**CLI**：
```bash
python3 run_batch_cli.py --file examples/batches/demo_sequence.json
```

**批次檔案格式**：
```json
{
  "batch_id": "batch-001",
  "commands": [
    {
      "target": "robot-001",
      "action": "stand",
      "params": {}
    },
    {
      "target": "robot-001",
      "action": "wave_hand",
      "delay_ms": 1000
    },
    {
      "target": "robot-002",
      "action": "go_forward",
      "params": {"distance": 100}
    }
  ],
  "options": {
    "continue_on_error": true,
    "max_retries": 3
  }
}
```

---

### 批次執行監控

**功能說明**：即時監控批次指令執行進度。

**CLI 監控模式**：
```bash
python3 run_batch_cli.py --file batch.json --monitor
```

**顯示資訊**：
- 總指令數 / 已完成數
- 成功 / 失敗 / 執行中
- 預估剩餘時間
- 當前執行的指令

**API 查詢**：
```bash
curl http://localhost:8000/v1/batches/batch-001 \
  -H "Authorization: Bearer $TOKEN"
```

---

## LLM 整合

### LLM 提供商配置

**功能說明**：設定 AI 語言模型服務。

**支援的提供商**：

| 提供商 | 類型 | 配置項目 |
|--------|------|----------|
| Ollama | 本地 | 服務地址、模型名稱 |
| LM Studio | 本地 | 服務地址、模型名稱 |
| OpenAI | 雲端 | API 金鑰、模型版本 |
| Anthropic | 雲端 | API 金鑰、模型版本 |

**WebUI 配置**：
1. 前往「設定」→「LLM 設定」
2. 選擇提供商
3. 填寫配置資訊
4. 點擊「測試連線」
5. 儲存設定

**配置檔案**：
```yaml
# config/llm.yaml
providers:
  - name: ollama
    type: local
    endpoint: http://localhost:11434
    model: llama2
    enabled: true
    
  - name: openai
    type: cloud
    api_key: sk-xxx
    model: gpt-4
    enabled: false
```

---

### 自然語言指令

**功能說明**：使用自然語言描述任務，由 LLM 轉換為機器人指令。

**使用方式**：

**WebUI**：
1. 切換到「自然語言」模式
2. 輸入描述，例如：「讓機器人向前走 3 步然後揮手」
3. LLM 解析為指令序列
4. 預覽並確認
5. 執行

**TUI**：
```
# 啟用 LLM 模式
service:llm.enable

# 輸入自然語言
nl:讓機器人轉一圈後停止
```

**解析範例**：
```
輸入："讓機器人向前走然後向左轉"
↓ LLM 解析
輸出：
[
  {"action": "go_forward", "params": {"steps": 5}},
  {"action": "turn_left", "params": {"angle": 90}}
]
```

---

### 指令建議

**功能說明**：根據上下文智慧建議下一步動作。

**觸發時機**：
- 指令執行完成後
- 使用者請求建議時
- 檢測到異常狀態時

**WebUI 顯示**：
- 在指令輸入區域下方顯示建議
- 點擊建議可直接執行

**範例**：
```
當前狀態：機器人已站立
建議動作：
1. wave_hand - 揮手打招呼
2. go_forward - 向前移動
3. sit - 坐下休息
```

---

## 服務管理

### 服務啟動與停止

**功能說明**：控制系統各服務的運行狀態。

**TUI 指令**：
```bash
# 啟動服務
service:mcp.start
service:flask.start
service:queue.start

# 停止服務
service:mcp.stop
service:flask.stop

# 重啟服務
service:mcp.restart

# 批次操作
service:all.start
service:all.stop
```

**API**：
```bash
# 啟動服務
curl -X POST http://localhost:8000/v1/services/mcp/start \
  -H "Authorization: Bearer $TOKEN"

# 停止服務
curl -X POST http://localhost:8000/v1/services/mcp/stop \
  -H "Authorization: Bearer $TOKEN"
```

---

### 服務健康檢查

**功能說明**：檢查服務運行狀態與效能指標。

**檢查項目**：
- HTTP 回應時間
- 資料庫連線狀態
- 佇列深度與容量
- 記憶體使用量

**TUI**：
```
service:mcp.healthcheck
service:all.healthcheck
```

**API**：
```bash
curl http://localhost:8000/health
curl http://localhost:5000/health
```

---

### 服務配置管理

**功能說明**：動態調整服務配置參數。

**可調整項目**：
- 佇列大小
- Worker 數量
- Timeout 設定
- 日誌等級

**配置檔案**：
```yaml
# config/services.yaml
flask:
  port: 5000
  workers: 4
  timeout: 30
  
mcp:
  port: 8000
  jwt_expiration: 3600
  
queue:
  size: 1000
  workers: 5
  priority_levels: 4
```

---

## 監控與日誌

### 即時指標監控

**功能說明**：顯示系統即時效能指標。

**Prometheus Metrics**：
```bash
# 存取 metrics 端點
curl http://localhost:5000/metrics
curl http://localhost:8000/metrics
```

**主要指標**：
- `http_requests_total` - HTTP 請求總數
- `http_request_duration_seconds` - 請求延遲
- `command_executions_total` - 指令執行總數
- `command_execution_duration_seconds` - 指令執行時間
- `queue_depth` - 佇列深度
- `robot_connections` - 機器人連線數

---

### 日誌查看

**功能說明**：查看與搜尋系統日誌。

**日誌位置**：
```
logs/
├── flask.log
├── mcp.log
├── queue.log
├── robot_service.log
└── error.log
```

**日誌格式**（JSON）：
```json
{
  "timestamp": "2025-12-22T10:00:00.123Z",
  "level": "INFO",
  "event": "command_executed",
  "trace_id": "trace-123",
  "context": {
    "robot_id": "robot-001",
    "action": "go_forward",
    "duration_ms": 1500
  }
}
```

**搜尋日誌**：
```bash
# 查找錯誤
grep "ERROR" logs/*.log

# 查找特定機器人
grep "robot-001" logs/*.log

# JSON 查詢（使用 jq）
cat logs/flask.log | jq 'select(.level == "ERROR")'
```

---

### 審計日誌

**功能說明**：記錄所有重要操作供審計使用。

**記錄事件**：
- 使用者登入/登出
- 指令執行（含參數）
- 配置變更
- 權限變更
- 機器人註冊/刪除

**查詢審計日誌**：
```bash
curl "http://localhost:8000/v1/audit?start=2025-12-22T00:00:00Z" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 安全與權限

### 使用者註冊

**功能說明**：建立新使用者帳號。

**API**：
```bash
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-001",
    "username": "operator1",
    "password": "secure-password",
    "email": "operator1@example.com",
    "role": "operator"
  }'
```

---

### 使用者登入

**功能說明**：身份驗證並取得 JWT Token。

**WebUI**：
1. 在登入頁面輸入帳號密碼
2. 點擊「登入」
3. 系統自動儲存 token

**API**：
```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "operator1",
    "password": "secure-password"
  }'
```

**回應**：
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2025-12-23T10:00:00Z",
  "user": {
    "user_id": "user-001",
    "username": "operator1",
    "role": "operator"
  }
}
```

---

### 角色權限

**功能說明**：基於角色的存取控制（RBAC）。

**三種內建角色**：

| 角色 | 權限說明 |
|------|----------|
| **admin** | 完整系統存取權限、使用者管理、配置變更 |
| **operator** | 執行指令、查看狀態、管理機器人 |
| **viewer** | 僅查看狀態與歷史記錄，無法執行操作 |

**權限矩陣**：

| 操作 | admin | operator | viewer |
|------|-------|----------|--------|
| 執行指令 | ✅ | ✅ | ❌ |
| 查看狀態 | ✅ | ✅ | ✅ |
| 管理機器人 | ✅ | ✅ | ❌ |
| 使用者管理 | ✅ | ❌ | ❌ |
| 系統配置 | ✅ | ❌ | ❌ |
| 查看日誌 | ✅ | ✅ | ✅ |

---

### Token 輪替

**功能說明**：定期更新認證 Token 提升安全性。

**API**：
```bash
curl -X POST http://localhost:8000/v1/auth/rotate \
  -H "Authorization: Bearer $OLD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "grace_period_seconds": 300
  }'
```

**回應**：
```json
{
  "new_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "old_token_expires_at": "2025-12-22T10:05:00Z",
  "new_token_expires_at": "2025-12-23T10:00:00Z"
}
```

---

## 整合與 API

### REST API

**功能說明**：完整的 RESTful API 供外部系統整合。

**API 文件**：
- OpenAPI 規範：`openapi.yaml`
- 線上文件：`http://localhost:8000/docs`

**主要端點**：

**機器人管理**：
- `GET /v1/robots` - 列出所有機器人
- `POST /v1/robots` - 註冊新機器人
- `GET /v1/robots/{id}` - 查詢機器人資訊
- `PUT /v1/robots/{id}` - 更新機器人資訊
- `DELETE /v1/robots/{id}` - 刪除機器人

**指令執行**：
- `POST /v1/commands` - 執行指令
- `GET /v1/commands` - 查詢指令歷史
- `GET /v1/commands/{id}` - 查詢指令詳情
- `POST /v1/commands/{id}/cancel` - 取消指令

**批次操作**：
- `POST /v1/batches` - 建立批次任務
- `GET /v1/batches/{id}` - 查詢批次狀態

---

### WebSocket 即時通訊

**功能說明**：雙向即時通訊，接收狀態更新。

**連線**：
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  console.log('Connected');
  // 發送認證
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'your-jwt-token'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

**訊息類型**：
- `status_update` - 機器人狀態更新
- `command_complete` - 指令執行完成
- `error` - 錯誤通知
- `heartbeat` - 心跳

---

### MQTT 整合

**功能說明**：透過 MQTT 協定與機器人通訊。

**主題結構**：
```
robot/{robot_id}/command    # 發送指令
robot/{robot_id}/status     # 接收狀態
robot/{robot_id}/telemetry  # 遙測資料
```

**發送指令**：
```bash
mosquitto_pub -t "robot/robot-001/command" \
  -m '{"action": "go_forward", "params": {}}'
```

**訂閱狀態**：
```bash
mosquitto_sub -t "robot/robot-001/status"
```

---

**回到索引**：[用戶指南索引](USER_GUIDE_INDEX.md)

**最後更新**：2025-12-22
