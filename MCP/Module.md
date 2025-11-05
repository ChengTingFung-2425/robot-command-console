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
````markdown
# MCP 服務模組設計說明

本文件以精簡版本說明 MCP（Model Context Protocol）服務模組的職責邊界、資料契約、處理流程與完成定義，對齊 `Project.prompt.md`，確保標準化、可擴充、可觀測與可追溯。

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
- ERR_ROBOT_NOT_FOUND：指定 `robot_id` 不存在或未註冊。
- ERR_ROBOT_OFFLINE：機器人離線或無回應。
- ERR_ROBOT_BUSY：機器人執行中，無法接受新指令。
- ERR_ACTION_INVALID：動作類型不支援。
- ERR_PROTOCOL：協定層錯誤（連線／封包／解碼）。
- ERR_TIMEOUT：執行逾時。
- ERR_INTERNAL：未預期錯誤。

## 6. 可觀測性與審計
- 事件：所有狀態流轉與介入操作均產生事件（含 `trace_id`、`command_id`）。
- 指標：成功率、延遲分佈、錯誤碼分佈、併發量、佇列長度。
- 追蹤：跨模組與協定保留 `trace_id`；必要時串接 OpenTelemetry。

## 7. 安全要求
- AuthN：建議 JWT／OAuth2 或可插拔 Token。
- AuthZ：RBAC／ABAC，最小權限原則；審計記錄關鍵操作。
- 秘密管理：環境變數或密管服務；不得入庫。
- 資料最小化與脫敏；錯誤訊息不洩漏敏感資訊。

## 8. 完成定義（DoD）
- API 與資料契約文件化，附最小 JSON 範例。
- 測試涵蓋：成功、驗證錯、授權錯、超時／重試、事件產生。
- 事件／指標可查詢；錯誤碼表同步文件。
- 安全檢查完成（無硬編碼密鑰、權限／輸入檢查）。

## 9. 機器人註冊與管理（精簡）
### 9.1 註冊表
`robot_id`、`robot_type`、`capabilities`、`status`（online／offline／busy／maintenance）、`endpoint`、`protocol`（HTTP／MQTT／WebSocket）、`last_heartbeat`。

### 9.2 發現與健康
- 自動註冊：Robot-Console 啟動時向 MCP 註冊。
- 心跳機制：固定間隔（例如 30 秒）。
- 自動摘除：超過 2 分鐘無心跳標記為 offline。
- 能力查詢：WebUI 可查詢可用機器人與能力。

### 9.3 負載與容錯
- 同類型可形成機群；依 idle／busy 與負載分配。
- 單一失敗自動重試其他實例（受限於語義與安全）。

## 10. 機器人工具清單（由機器人模組管理）

為了集中管理機器人可執行動作（便於能力查詢、版本化與對上游 API 的一致性），本專案將機器人模組的工具清單（原始位置：`Robot-Console/tools.py`）移交至 MCP 作為參考。MCP 會暴露能力查詢 API（例如：GET /api/robots/{robot_id}/capabilities 或 GET /api/tools），並提供每項工具的描述與參數 schema，以供 WebUI、LLM 代理與外部整合使用，並將這些項目傳遞給機器人模組。

下列為已納入 MCP 的工具清單（從 `Robot-Console/tools.py` 同步過來，含名稱與簡短描述）：

```
back_fast: 指示機器人快速向後移動。
bow: 指示機器人鞠躬。
chest: 指示機器人做胸部運動。
dance_eight: 指示機器人執行舞蹈「八」的動作。
dance_five: 指示機器人執行舞蹈「五」的動作。
dance_four: 指示機器人執行舞蹈「四」的動作。
dance_nine: 指示機器人執行舞蹈「九」的動作。
dance_seven: 指示機器人執行舞蹈「七」的動作。
dance_six: 指示機器人執行舞蹈「六」的動作。
dance_ten: 指示機器人執行舞蹈「十」的動作。
dance_three: 指示機器人執行舞蹈「三」的動作。
dance_two: 指示機器人執行舞蹈「二」的動作。
go_forward: 指示機器人向目前面向的方向前進。
kung_fu: 指示機器人執行功夫動作。
left_kick: 指示機器人做左側踢。
left_move_fast: 指示機器人快速向左移動。
left_shot_fast: 指示機器人做快速左拳動作。
left_uppercut: 指示機器人做左上鉤拳。
push_ups: 指示機器人做伏地挺身。
right_kick: 指示機器人做右側踢。
right_move_fast: 指示機器人快速向右移動。
right_shot_fast: 指示機器人做快速右拳動作。
right_uppercut: 指示機器人做右上鉤拳。
sit_ups: 指示機器人做仰臥起坐。
squat: 指示機器人蹲下。
squat_up: 指示機器人從蹲下動作站起來。
stand: 指示機器人站立並維持站姿。
stand_up_back: 指示機器人從仰臥（背部）姿勢站起來。
stand_up_front: 指示機器人從前方（可能為趴或前側姿勢）站起來。
stepping: 指示機器人執行踏步動作。
stop: 指示機器人停止所有當前動作或移動。
turn_left: 指示機器人向左轉。
turn_right: 指示機器人向右轉。
twist: 指示機器人扭轉身體。
wave: 指示機器人揮手。
weightlifting: 指示機器人執行舉重動作。
wing_chun: 指示機器人執行詠春動作。
```

使用說明與約定：
- API 資訊：MCP 應提供一個可以取得工具列表與每個工具 input schema 的端點（例如：GET /api/tools 或 GET /api/robots/{robot_id}/capabilities）。
- 版本化：工具的 schema 與描述會以版本號管理（例如：tools.v1、tools.v2），避免破壞向後相容性。
- 同步機制：Robot-Console 仍保留 `tools.py` 作為本地執行器映射與快速測試用，但任何權威變更需先在 MCP 的工具庫中更新，並透過 CI 或同步腳本下放到 Robot-Console（參見後述遷移說明）。

## 11. 下一步（Roadmap）
- 實作機器人註冊 API（POST /api/robots/register）。
- 實作進階指令 API（POST／GET /api/advanced_commands）。
- 文件化協定適配器介面（connect／send／receive／close、重試／超時）。
- 與 WebUI 對齊審批／介入操作 API 與事件語意（含 E-Stop 優先級）。
- 擴充錯誤碼表與狀態機定義；補齊整合測試。
