# WebUI 模組設計說明

本文件定義 WebUI 模組在本專案中的職責、互動流程、事件與即時性要求、介入操作、安全與可觀測性，對齊 `Project.prompt.md` 與 `MCP/Module.md`。

## 1. 職責與邊界
- WebUI 僅與 MCP 交互，永不直接連線機器人或協定適配器。
- 提供人機互動能力：登入/審批中心/指令下達/狀態面板/日誌查詢/告警訂閱。
- 提供人類介入控制：pause/resume/cancel/override，並完整產生日誌與審計事件。

## 2. 互動流程（對齊 MCP 契約）
1) 使用者登入（AuthN），獲取 Token；授權（AuthZ）決定可用功能。
2) 下達指令：組裝 CommandRequest（含 trace_id/actor/source/labels），POST 到 MCP `/api/command`。
3) 監控執行：
	 - 查詢：輪詢 `/api/status?command_id=...` 或
	 - 訂閱：透過 WebSocket/SSE `/api/events` 接收事件（accepted/running/...）。
4) 人類介入：於執行中狀態觸發 pause/resume/cancel/override；所有操作與審批紀錄寫入 Event（category=audit）。
5) 結果歸檔：將最終狀態、摘要與關鍵上下文關聯 trace_id 以供追溯與報表。

## 3. 即時性與事件
- 渲染來源：事件優先（WS/SSE），失連時回退輪詢。
- UI 狀態機：顯示 accepted → running → succeeded/failed/cancelled 流轉與進度。
- 告警：對錯誤與高風險事件彈出提醒與指引（排查建議/回滾操作）。

事件格式（參考 MCP）：
{
	"trace_id": "...",
	"timestamp": "...",
	"severity": "INFO|WARN|ERROR",
	"category": "command|auth|protocol|robot|audit",
	"message": "...",
	"context": { "command_id": "cmd-...", "user_id": "..." }
}

## 4. 介入操作與審批
- 高風險指令需先審批；審批結論、審批人與依據須記錄於審計事件。
- 支援操作：pause/resume/cancel/override；若覆寫需提供原因與風險提示。
- UI 應提供保護：二次確認、角色限制、節流與速率限制。

## 5. 安全與權限
- 身份驗證：JWT/OAuth2/Session 皆可，建議短期 Token + 刷新。
- 授權：RBAC（viewer/operator/admin/auditor）；頁面與操作基於權限控制顯示。
- 敏感資訊：前端不儲存明文秘鑰；錯誤訊息脫敏；避免在 URL 曝露敏感參數。

## 6. 可觀測性
- 使用者行為與關鍵操作產生 Event（category=audit）。
- UI 健康指標：事件延遲、斷線率、重連成功率。
- 與 MCP 之 trace_id 對齊，確保端到端追蹤。

## 7. 目錄結構對照
- `WebUI/app/*.py`：後端路由、錯誤處理、資料模型、郵件、表單。
- `WebUI/app/templates/*.j2`：頁面模板（狀態面板、日誌、審批、登入）。
- `WebUI/migrations/*`：資料庫遷移。
- `Test/Web/*`：對應測試檔，驗證路由、權限、日誌與 UI 結構。

## 8. 完成定義（DoD）
- 頁面與 API 對齊 MCP 契約；指令/事件流在本地可驗證。
- 測試涵蓋：登入/授權、下達指令、事件訂閱、介入操作、日誌產生。
- 安全檢查：權限控制、敏感資訊處理、錯誤脫敏。
- 可觀測性：事件與 trace_id 貫通，關鍵指標可查。

## 9. 下一步
- 定義介入操作的 API 與前端交互細節（確認對話、風險提示）。
- 建立告警訂閱與通知機制（Email/Webhook）。
- 強化 E2E 測試：模擬連線中斷、超時與重試。
