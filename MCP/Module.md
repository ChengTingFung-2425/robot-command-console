# MCP 服務模組設計說明

本文件以精簡版本說明 MCP（Model Context Protocol）服務模組的職責邊界、資料契約、處理流程與完成定義，對齊 `Project.prompt.md` 及 `proposal.md`，確保標準化、可擴充、可觀測與可追溯。

## 1. 目標與原則
- 對外提供統一 API（HTTP／WebSocket／MQTT 可插拔），安全地下達指令、查詢狀態、訂閱事件。
- 資料契約標準化，貫穿 `trace_id` 與審計資訊。
- 支援人類介入（審批／暫停／取消／覆寫），高可用、可觀測。

## 2. 模組邊界與子模組
- 指令處理（command）：接收、驗證、排隊、路由、重試、超時。
- 上下文管理（context）：上下文與狀態歷史、冪等鍵。
- 協定適配（protocols）：HTTP／WebSocket／MQTT／gRPC／ROS 適配與可靠傳輸。
- 機器人路由（robot_routing）：依 `robot_id`／`robot_type` 路由至對應 Robot-Console。
- 認證授權（auth）：身份驗證、RBAC／ABAC、權限審計。
- 日誌監控（logging_monitor）：事件、審計、指標、追蹤。

## 3. API 與資料契約（JSON）

通用欄位（建議所有請求／回應／事件包含）：`trace_id`（UUIDv4）、`timestamp`（ISO8601 UTC）、`actor`、`source`、`labels`。

### 3.1 指令請求 POST /api/command
請求：
```json
{
	"trace_id": "...",
	"timestamp": "...",
	"actor": { "type": "human|ai|system", "id": "..." },
	"source": "webui|api|cli|scheduler",
	"command": {
		"id": "cmd-...",
		"type": "robot.move|robot.stop|...",
		"target": { "robot_id": "..." },
		"params": {},
		"timeout_ms": 10000,
		"priority": "low|normal|high"
	},
	"auth": { "token": "<redacted>" },
	"labels": {}
}
```

回應：
```json
{
	"trace_id": "...",
	"timestamp": "...",
	"command": { "id": "cmd-...", "status": "accepted|running|succeeded|failed|cancelled" },
	"result": { "data": {}, "summary": "" },
	"error": { "code": "", "message": "", "details": {} }
}
```

備註（與 Robot-Console 對齊）：緊急停止（E-Stop）由 WebUI 觸發時，`type` 可用 `robot.stop` 或 `params.action_name = stop` 並提高 `priority`（如 `high`），以確保優先處理。

### 3.2 查詢狀態 GET /api/status?command_id=...
```json
{
	"trace_id": "...",
	"timestamp": "...",
	"command": { "id": "cmd-...", "status": "running|succeeded|failed|cancelled" },
	"progress": { "percent": 42, "stage": "navigating" },
	"error": { "code": "", "message": "", "details": {} }
}
```

### 3.3 事件訂閱 WS /api/events（或 SSE /api/events）
```json
{
	"trace_id": "...",
	"timestamp": "...",
	"severity": "INFO|WARN|ERROR",
	"category": "command|auth|protocol|robot|audit",
	"message": "...",
	"context": { "command_id": "cmd-..." }
}
```

### 3.4 上下文管理 GET／POST /api/context
以 `trace_id` 或 `command.id` 為鍵查詢／更新上下文。

### 3.5 錯誤格式（統一）
```json
{
	"code": "ERR_TIMEOUT|ERR_UNAUTHORIZED|ERR_VALIDATION|ERR_ROUTING|ERR_PROTOCOL|ERR_INTERNAL",
	"message": "...",
	"details": {}
}
```

## 4. 指令處理流程（精簡）
1) 驗證：Schema＋業務規則；AuthN／AuthZ。
2) 上下文與冪等：填充 metadata、處理冪等鍵。
3) 機器人路由：解析 `robot_id`／`robot_type`，查註冊表（能力、協定、可用性），定位 Robot-Console。
4) 執行與監控：Robot-Console 轉換並透過協定適配器發送（HTTP／MQTT／WS 等），控制超時／重試／併發。
5) 事件：上報 accepted／running／succeeded／failed／cancelled。
6) 回應：提供即時狀態與最終查詢；支持人類介入（pause／resume／cancel／override）。

邊界條件：
- 重試採指數退避＋抖動；避免雪崩效應。
- 機器人級併發鎖；跨機器人隔離。
- 錯誤分級：USER_ERROR（驗證／授權）與 SYSTEM_ERROR（協定／內部）。

## 5. 錯誤碼表（最小集）
- ERR_VALIDATION：請求資料不符合 Schema／業務規則。
- ERR_UNAUTHORIZED：身份驗證或授權失敗。
- ERR_ROUTING：無對應路由或目標不可達。
