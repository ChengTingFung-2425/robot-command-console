---
mode: agent
---
## 專案總覽與作業規範

本文件定義本專案「機器人指令中介層」的設計原則、模組邊界、資料契約、處理流程與完成定義，確保系統模組化、可擴充、可監督、可追溯與高可用。

## 目標與核心原則
- 模組化與鬆耦合：MCP、指令/路由、通訊協定、認證/授權、日誌/監控、機器人抽象、WebUI 皆為清楚邊界的獨立模組。
- 標準化資料契約：所有請求/回應/事件均使用一致的 JSON 契約，並具全鏈路追蹤能力。
- 可監督與人類可介入：任何指令可被審批、暫停、取消、覆寫，且具即時狀態與審計軌跡。
- 安全與合規：強制身份驗證、授權與審計；敏感資訊不落地至原始碼。
- 高可用與可維護：明確的超時/重試策略、錯誤分級、可觀測性指標。

## 架構總覽（模組與職責）
- MCP 服務模組：統一接入層，負責指令標準化、上下文管理、驗證、授權、路由、觀測事件產生。
- 指令/路由模組：根據指令類型與目標路由到對應協定與機器人實作，處理重試與超時。
- 通訊協定模組：各協定（如串口、TCP、ROS、gRPC…）的轉接器，負責封包編解碼與傳輸可靠性。
- 認證/授權模組：身份驗證（如 JWT/OAuth2/Token）、RBAC/ABAC 授權、權限審計。
- 日誌與監控模組：集中化事件、審計、指標；支援查詢、告警與追蹤。
- 機器人抽象模組：統一機器人能力介面（如移動、抓取、狀態讀取），屏蔽廠商差異。
- WebUI 模組：人機界面，提供下達/審批/監控/介入，不直接與機器人通訊。

目錄參考：
- MCP：`MCP/Module.md`
- WebUI：`WebUI/Module.md`
- 測試：`Test/` 下各模組測試檔

## 標準資料契約（JSON）

通用欄位（所有請求/回應/事件均推薦包含）：
- trace_id：全鏈路追蹤 ID（UUIDv4）。
- timestamp：ISO8601 時間戳（UTC）。
- actor：觸發者（human|ai|system）與識別資訊。
- source：入口來源（webui|api|cli|scheduler|…）。
- labels：可選鍵值標籤（環境、租戶、任務編號等）。

指令請求 CommandRequest：
{
	"trace_id": "c1c5f2a0-6a0a-4f1e-9cc1-7b6f0a7a8d3e",
	"timestamp": "2025-10-15T08:30:00Z",
	"actor": { "type": "human", "id": "user_123" },
	"source": "webui",
	"command": {
		"id": "cmd-0001",
		"type": "robot.move",
		"target": { "robot_id": "rbx-01" },
		"params": { "x": 1.2, "y": -0.5, "theta": 0.0, "speed": 0.4 },
		"timeout_ms": 10000,
		"priority": "normal"
	},
	"auth": { "token": "<redacted>" },
	"labels": { "tenant": "acme", "env": "dev" }
}

指令回應 CommandResponse：
{
	"trace_id": "c1c5f2a0-6a0a-4f1e-9cc1-7b6f0a7a8d3e",
	"timestamp": "2025-10-15T08:30:01Z",
	"command": { "id": "cmd-0001", "status": "accepted|running|succeeded|failed|cancelled" },
	"result": { "data": { "distance": 1.7 }, "summary": "moved 1.7m" },
	"error": { "code": "", "message": "", "details": {} }
}

事件/日誌 EventLog（監控/審計用）：
{
	"trace_id": "c1c5f2a0-6a0a-4f1e-9cc1-7b6f0a7a8d3e",
	"timestamp": "2025-10-15T08:30:00Z",
	"severity": "INFO|WARN|ERROR",
	"category": "command|auth|protocol|robot|audit",
	"message": "Command routed to ROS adapter",
	"context": { "command_id": "cmd-0001", "adapter": "ros" }
}

錯誤格式（統一）：
{
	"code": "ERR_TIMEOUT|ERR_UNAUTHORIZED|ERR_VALIDATION|ERR_ROUTING|ERR_PROTOCOL|ERR_INTERNAL",
	"message": "人類可讀訊息",
	"details": { "hint": "排查建議或關鍵欄位" }
}

## 指令處理流程（高層級）
1) 接收：入口（WebUI/API/CLI）提交 CommandRequest，生成/傳入 trace_id。
2) 驗證：結構化驗證（schema）、業務校驗（機器人狀態/參數範圍）。
3) 認證與授權：驗證 token / session，執行 RBAC/ABAC 規則。
4) 上下文豐富：補齊預設值、租戶/環境標籤、冪等鍵。
5) 路由：依 command.type/target 送至對應協定適配器與機器人抽象。
6) 執行：協定轉換、傳輸；實施超時與重試；編排必要的子步驟。
7) 觀測：過程事件（accepted/running/succeeded/failed/cancelled）與關鍵指標上報。
8) 回應：即時回傳 accepted/running；完成後回調/輪詢查詢最終狀態。
9) 人類介入：可在 running 階段暫停、取消或覆寫（見下節）。

邊界條件與考量：
- 超時與重試：協定層與指令層分開配置；避免雪崩（退避抖動）。
- 冪等性：使用 command.id 或冪等鍵避免重複執行。
- 併發：同一機器人併發隊列與鎖；跨機器人併發隔離。
- 安全降級：授權失敗與驗證失敗需回應明確錯誤碼，不洩漏敏感資訊。

## 安全與存取控制
- 身份驗證（AuthN）：建議採 JWT/OAuth2 或可插拔 Token；支援短期 token 與刷新流程。
- 授權（AuthZ）：最小權限原則；RBAC 角色示例：viewer/operator/admin/auditor。
- 審計與追溯：所有安全相關操作（登入、審批、覆寫）必須記錄 EventLog（category=audit）。
- 秘密管理：API 金鑰、密碼、連線字串放置於環境變數或密管服務，不提交到版本庫。
- 輸入輸出安全：對命令參數作邊界/白名單校驗；輸出脫敏（PII/秘鑰）。

## 人類介入與手動覆寫
- 審批流程：高風險指令（如急停、越權操作）需人工審批後才可執行。
- 介入動作：pause/resume/cancel/override；所有介入需記審計事件並關聯 trace_id。
- 回滾與保護：支援安全停止/回復策略（如安全姿態、原地停止）。
- WebUI 呈現：清楚展示狀態流轉、當前風險與下一步建議。

## WebUI 模組職責界定
- 只與 MCP 交互：不直接連線機器人；透過 API/事件匯流排存取狀態與日誌。
- 功能：使用者登入/審批中心/指令下達/狀態面板/日誌查詢/告警訂閱。
- 體驗：即時性（WebSocket/SSE）、可觀測性（指標/追蹤）、可操作（介入按鈕）。
- 參考：`WebUI/Module.md`、`Test/Web/*.py` 測試用例。

## 擴充規範（指令/協定/機器人）
- 新指令類型：
	1) 定義 JSON Schema 與範例；
	2) 新增路由規則與 Handler；
	3) 單元測試（成功 + 驗證失敗 + 授權失敗 + 超時）。
- 新協定適配器：
	1) 實作統一介面（connect/send/receive/close、重試、超時）；
	2) 記錄協定層事件與錯誤碼映射；
	3) 壓力與可靠性測試。
- 新機器人廠商：
	1) 實作機器人抽象介面；
	2) 對接協定適配器；
	3) 完成驗證清單與測試。
- 命名與目錄：以模組邏輯分區；測試放置於 `Test/` 對應檔；文件放置於模組目錄下的 `Module.md`。

## 完成定義（Definition of Done）
- 有對應的資料契約（Schema/範例）與文件更新（MCP 或 WebUI 的 Module.md）。
- 單元測試涵蓋率達到基本場景（成功、驗證錯、授權錯、超時/重試、日誌產生）。
- 事件與審計：產生必要的 EventLog，包含 trace_id 與關鍵上下文。
- 安全檢查：敏感資訊不落地；權限與輸入檢查通過；沒有硬編碼密鑰。
- 可觀測性：關鍵指標（成功率、延遲、錯誤碼分佈）可被查詢。

## 下一步與落地任務
- 補齊 MCP 契約與處理流程細節：見 `MCP/Module.md`。
- WebUI 介面與交互流程：見 `WebUI/Module.md` 與 `Test/Web/` 測試檔。
- 逐步補充各模組單元測試：見 `Test/` 目錄下對應檔案。

## 結構整理與清理建議
>> 建立新檔案/資料夾後，請同步更新對應 `Module.md`，並移除不再使用或重複的檔案與相依。

最小檢查清單：
- 目錄命名與模組歸屬一致（MCP/WebUI/Protocol/Robot/Logs）。
- 無未使用的檔案與測試草稿；移除或合併陳舊文件。
- `requirements.txt` 僅保留實際使用套件；敏感設定移至環境變數。
- 文件以中文撰寫，與此規範一致；段落精簡、範例可直接複用。