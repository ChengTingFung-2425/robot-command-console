# MCP 服務模組設計說明

本文件定義 MCP（Model Context Protocol）服務模組的職責邊界、資料契約、處理流程與完成定義，對齊 `Project.prompt.md` 之規範，確保標準化、可擴充、可監督與可追溯。

## 1. 目標與原則
- 對外提供統一 API（HTTP/WebSocket/MQTT 可插拔），安全地下達指令、查詢狀態、訂閱事件。
- 標準化資料契約，具全鏈路追蹤（trace_id）與審計能力。
- 支援人類介入（審批/暫停/取消/覆寫），可觀測且高可用。

## 2. 模組邊界與子模組
- 指令處理（command）：接收、驗證、排隊、路由、重試、超時。
- 上下文管理（context）：指令上下文與狀態歷史；冪等鍵管理。
- 協定適配（protocols）：HTTP/WebSocket/MQTT/gRPC/ROS 等轉接與可靠傳輸。
- 機器人路由（robot_routing）：根據 robot_id 與 robot_type 路由至對應的 Robot-Console 模組。
- 認證授權（auth）：身份驗證、RBAC/ABAC、權限審計。
- 日誌/監控（logging_monitor）：事件、審計、指標、追蹤。

## 3. API 與資料契約（JSON）

通用欄位（所有請求/回應/事件建議包含）：
- trace_id（UUIDv4）、timestamp（ISO8601 UTC）、actor、source、labels。

3.1 指令請求 POST /api/command
Request Body：
{
	"trace_id": "...",
	"timestamp": "...",
	"actor": { "type": "human|ai|system", "id": "..." },
	"source": "webui|api|cli|scheduler",
	"command": {
		"id": "cmd-...",
		"type": "robot.move|robot.stop|...",
		"target": { "robot_id": "..." },
		"params": { },
		"timeout_ms": 10000,
		"priority": "low|normal|high"
	},
	"auth": { "token": "<redacted>" },
	"labels": { }
}

Response：
{
	"trace_id": "...",
	"timestamp": "...",
	"command": { "id": "cmd-...", "status": "accepted|running|succeeded|failed|cancelled" },
	"result": { "data": { }, "summary": "" },
	"error": { "code": "", "message": "", "details": {} }
}

3.2 查詢狀態 GET /api/status?command_id=...
Response：
{
	"trace_id": "...",
	"timestamp": "...",
	"command": { "id": "cmd-...", "status": "running|succeeded|failed|cancelled" },
	"progress": { "percent": 42, "stage": "navigating" },
	"error": { "code": "", "message": "", "details": {} }
}

3.3 事件訂閱 WS /api/events 或 SSE /api/events
Event：
{
	"trace_id": "...",
	"timestamp": "...",
	"severity": "INFO|WARN|ERROR",
	"category": "command|auth|protocol|robot|audit",
	"message": "...",
	"context": { "command_id": "cmd-..." }
}

3.4 上下文管理 GET/POST /api/context
以 trace_id 或 command.id 為鍵查詢/更新上下文。

3.5 錯誤格式（統一）
{
	"code": "ERR_TIMEOUT|ERR_UNAUTHORIZED|ERR_VALIDATION|ERR_ROUTING|ERR_PROTOCOL|ERR_INTERNAL",
	"message": "...",
	"details": { }
}

## 4. 指令處理流程
1) 接收與驗證（schema + 業務規則）
2) 認證/授權（AuthN/AuthZ）
3) 上下文豐富與冪等鍵處理
4) **機器人路由**：
   - 解析 command.target.robot_id 與 robot_type
   - 查詢機器人註冊表（可用性、能力、協定）
   - 路由至對應的 Robot-Console 實例
5) **執行與監控**（透過 Robot-Console）：
   - Robot-Console 接收標準化指令
   - 轉換為機器人特定格式
   - 透過協定適配器發送（HTTP/MQTT/WS 等）
   - 超時/重試/併發控制
6) 事件上報（accepted/running/succeeded/failed/cancelled）
7) 回應與最終狀態查詢/回調
8) 人類介入（pause/resume/cancel/override）

邊界條件：
- 超時與重試採用指數退避與抖動；避免雪崩。
- 機器人級併發鎖；跨機器人隔離。
- 錯誤分級：USER_ERROR（驗證/授權）與 SYSTEM_ERROR（協定/內部）。

## 5. 錯誤碼表（最小集）
- ERR_VALIDATION：請求資料不符合 schema/業務規則。
- ERR_UNAUTHORIZED：身份驗證或授權失敗。
- ERR_ROUTING：無對應路由或目標不可達。
- ERR_ROBOT_NOT_FOUND：指定的 robot_id 不存在或未註冊。
- ERR_ROBOT_OFFLINE：機器人離線或無回應。
- ERR_ROBOT_BUSY：機器人執行中，無法接受新指令。
- ERR_ACTION_INVALID：動作類型不支援。
- ERR_PROTOCOL：協定層錯誤（連線/封包/解碼）。
- ERR_TIMEOUT：執行逾時。
- ERR_INTERNAL：未預期錯誤。

## 6. 可觀測性與審計
- 事件：所有狀態流轉與介入操作均產生 Event（含 trace_id、command_id）。
- 指標：成功率、延遲分佈、錯誤碼分佈、併發量、佇列長度。
- 追蹤：跨模組與協定保留 trace_id；必要時串接 OpenTelemetry。

## 7. 安全要求
- AuthN：建議 JWT/OAuth2 或可插拔 Token。
- AuthZ：RBAC/ABAC，最小權限原則；審計記錄關鍵操作。
- 秘密管理：環境變數或密管服務；不得入庫。
- 資料最小化與脫敏；錯誤訊息不洩漏敏感資訊。

## 8. 完成定義（DoD）
- API 與資料契約已文件化並有 JSON 範例。
- 測試覆蓋：成功、驗證錯、授權錯、超時/重試、事件產生。
- 事件/指標可查詢；錯誤碼表同步文件。
- 安全檢查完成（無硬編碼密鑰、權限/輸入檢查）。

## 9. 機器人註冊與管理

### 9.1 機器人註冊表
MCP 維護一個機器人註冊表，包含：
- `robot_id`：唯一識別碼（如 "robot_7"）
- `robot_type`：機器人類型（humanoid/agv/arm/drone）
- `capabilities`：支援的動作清單
- `status`：online/offline/busy/maintenance
- `endpoint`：Robot-Console 實例的連線資訊
- `protocol`：優先通訊協定（HTTP/MQTT/WebSocket）
- `last_heartbeat`：最後心跳時間

### 9.2 機器人發現與健康檢查
- **自動註冊**：Robot-Console 啟動時向 MCP 註冊
- **心跳機制**：定期發送健康狀態（30秒間隔）
- **自動摘除**：超過 2 分鐘無心跳則標記為 offline
- **能力查詢**：WebUI 可查詢可用機器人清單與能力

### 9.3 負載平衡與容錯
- 相同類型的多個機器人可形成機群
- 根據狀態（idle/busy）與負載分配指令
- 單一機器人失敗時自動重試其他實例

## 10. 進階指令插件機制

### 10.1 設計理念
- **基於組合**：進階指令由多個基礎指令按序列組合而成
- **用戶貢獻**：登入用戶可建立、分享進階指令範例
- **審核機制**：Admin/Auditor 角色審核後方可公開
- **可重複使用**：審核通過的進階指令可被其他用戶直接引用

### 10.2 進階指令格式
進階指令以 JSON 陣列定義，包含：
- `name`：進階指令名稱（唯一）
- `description`：功能描述
- `category`：分類（導航/操作/巡檢等）
- `base_commands`：基礎指令序列，範例：
```json
[
  {"command": "go_forward", "duration_ms": 3000, "speed": "normal"},
  {"command": "turn_left", "duration_ms": 1000},
  {"command": "go_forward", "duration_ms": 2000}
]
```

### 10.3 執行流程
1. 用戶選擇已審核的進階指令
2. MCP 展開為基礎指令序列
3. 逐一執行基礎指令，保留 trace_id 連貫性
4. 任一步驟失敗可選擇中止或繼續
5. 整體執行狀態與進度回報

### 10.4 審核與管理
- **提交**：登入用戶建立進階指令，初始狀態為 `pending`
- **審核**：Admin/Auditor 可批准（`approved`）或拒絕（`rejected`）
- **編輯**：作者可編輯自己的進階指令，重新送審
- **分類與搜尋**：依類別、關鍵字過濾進階指令

### 10.5 安全性
- 基礎指令需通過標準驗證與授權流程
- 進階指令不得包含惡意或越權操作
- 審核時檢查指令合理性與安全性

## 11. 下一步
- 實作機器人註冊 API（POST /api/robots/register）
- 實作進階指令 API（POST /api/advanced_commands、GET /api/advanced_commands）
- 將協定適配器介面定義文件化（connect/send/receive/close、重試/超時約定）。
- 與 WebUI 對齊審批/介入操作 API 與事件語意。
- 擴充錯誤碼表與狀態機定義；補齊整合測試。
