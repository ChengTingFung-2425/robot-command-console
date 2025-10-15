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
4) 路由至協定適配與機器人抽象
5) 執行與監控（超時/重試/併發控制）
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

## 9. 下一步
- 將協定適配器介面定義文件化（connect/send/receive/close、重試/超時約定）。
- 與 WebUI 對齊審批/介入操作 API 與事件語意。
- 擴充錯誤碼表與狀態機定義；補齊整合測試。
