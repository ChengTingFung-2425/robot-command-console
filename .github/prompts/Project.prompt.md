---
mode: agent
---

> 使用者為中文使用者，但為了提高編碼與撰寫速度偏好在程式碼中使用英文；因此請在程式碼外以中文進行撰寫與說明；若你在程式碼外讀到英文，請將其翻譯回中文。

---

## ⚠️ 必讀：專案記憶閱讀指南

**在進行任何貢獻之前，所有開發者必須優先閱讀以下專案記憶文件：**

| 文件 | 位置 | 用途 | 優先級 |
|------|------|------|--------|
| **proposal.md** | `docs/proposal.md` | **權威規格文件**：定義專案目標、核心設計理念、系統架構、模組職責、資料契約、實作路徑與成功標準 | 🔴 **最高** |
| **architecture.md** | `docs/architecture.md` | 目錄結構、環境隔離（Edge vs Server）、模組職責、資料流與設計原則 | 🟠 **高** |
| **MASTER_PLAN.md** | `docs/plans/MASTER_PLAN.md` | WebUI → Native App 轉換計畫，Phase 0-6 完整規劃、技術選型與交付物 | 🟠 **高** |
| **PROJECT_MEMORY.md** | `docs/PROJECT_MEMORY.md` | 架構決策記錄、共用工具模組說明、Phase 3 規劃概要 | 🟡 **中** |

> **🔴 重要提醒**：**`proposal.md` 是本專案的權威規格文件**。如遇任何規格疑義或文件間不一致，請以 `proposal.md` 為最終依據。

### 閱讀順序建議

1. **proposal.md**（必讀）：理解專案目標、核心模組與資料契約
2. **architecture.md**（必讀）：理解目錄結構與 Server-Edge-Runner 三層架構
3. **MASTER_PLAN.md**（建議）：理解專案演進路線與當前 Phase 狀態
4. **PROJECT_MEMORY.md**（參考）：查閱架構決策與共用工具

---

## 專案總覽與作業規範

本文件定義本專案「機器人指令中介層」的設計原則、模組邊界、資料契約、處理流程與完成定義，確保系統模組化、可擴充、可監督、可追溯與高可用。

> **說明：如遇規格疑義，請以 `docs/proposal.md` 為最終依據。**

## 目標與核心原則

> **📖 完整說明**：參見 [`docs/proposal.md`](../../../docs/proposal.md#核心設計理念)

- 模組化與鬆耦合：MCP、指令/路由、通訊協定、認證/授權、日誌/監控、機器人抽象、WebUI 皆為清楚邊界的獨立模組。
- 標準化資料契約：所有請求/回應/事件均使用一致的 JSON 契約，並具全鏈路追蹤能力。
- 可監督與人類可介入：任何指令可被審批、暫停、取消、覆寫，且具即時狀態與審計軌跡。
- 安全與合規：強制身份驗證、授權與審計；敏感資訊不落地至原始碼。
- 高可用與可維護：明確的超時/重試策略、錯誤分級、可觀測性指標。
- **所有設計、資料契約、流程、完成定義等，若與 `docs/proposal.md` 有出入，請以 `docs/proposal.md` 為準。**

---

## Server-Edge-Runner 三層架構

> **📖 完整架構說明**：參見 [`docs/architecture.md`](../../../docs/architecture.md#未來架構server-edge-runner) 與 [`docs/proposal.md`](../../../docs/proposal.md#server-edge-runner-三層架構phase-2)

本專案採用 **Server-Edge-Runner** 三層架構設計：

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Server      │────▶│      Edge       │────▶│     Runner      │
│  (MCP/WebUI)    │     │(robot_service/  │     │ (Robot-Console) │
│  集中管理/API   │     │ electron-app/   │     │ 機器人執行     │
│                 │     │ ALL-in-One App) │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        └───────────────────────┴───────────────────────┘
                    ↓ 共用模組 ↓
               ┌─────────────────┐
               │   src/common/   │
               │ 日誌/時間/配置  │
               └─────────────────┘
```

### 層級職責速查

| 層級 | 目錄 | 職責 |
|------|------|------|
| **Server** | `MCP/`, `WebUI/` | 統一 API Gateway、認證授權、資料持久化、指令處理、上下文管理 |
| **Edge** | `src/robot_service/`, `electron-app/`, ALL-in-One Edge App | 本地佇列、離線支援、低延遲處理、LLM 整合、插件系統 |
| **Runner** | `Robot-Console/` | 動作執行器（ActionExecutor）、協定適配（HTTP/MQTT/WS/Serial/ROS）、緊急停止與安全機制 |
| **共用** | `src/common/` | 統一 JSON 日誌、時間處理工具、環境配置（EdgeConfig/ServerConfig） |

### 資料流向

1. **指令下達**：用戶 → Edge WebUI → MCP（LLM 解析）→ Robot Service（佇列）→ Robot-Console → 機器人
2. **狀態回報**：機器人 → Robot-Console → Robot Service → Edge WebUI（即時顯示）
3. **雲端同步**：Edge ↔ Cloud（進階指令、用戶設定、分析資料）
4. **審計追蹤**：所有操作 → 本地事件日誌（含 trace_id）→ 可選上傳雲端

---

## 架構總覽（模組與職責）

> **📖 詳細模組設計**：參見 [`docs/architecture.md`](../../../docs/architecture.md#模組職責)

- **MCP 服務模組**：統一接入層，負責指令標準化、上下文管理（依 MCP 規範）、驗證、授權、路由、觀測事件產生。
- **指令/路由模組**：根據指令類型與目標路由到對應協定與機器人實作，處理重試與超時。
- **通訊協定模組**：各協定（如串口、TCP、ROS、gRPC…）的轉接器，負責封包編解碼與傳輸可靠性。
- **認證/授權模組**：身份驗證（如 JWT/OAuth2/Token）、RBAC/ABAC 授權、權限審計。
- **日誌與監控模組**：集中化事件、審計、指標；支援查詢、告警與追蹤。
- **機器人抽象模組**：統一機器人能力介面（如移動、抓取、狀態讀取），屏蔽廠商差異。
- **WebUI 模組**：人機界面，提供下達/審批/監控/介入，不直接與機器人通訊。

### 目錄參考

- MCP：`MCP/Module.md`
- WebUI：`WebUI/Module.md`
- Robot-Console：`Robot-Console/module.md`
- 測試：`tests/` 下各模組測試檔
- 共用模組：`src/common/`

---

## 測試先行（Test-Driven Development, TDD）原則

> **📖 測試指南**：參見 [`docs/TESTING.md`](../../../docs/TESTING.md)

本專案嚴格遵循 **測試先行** 原則，旨在：
- **明確需求**：測試案例定義功能的明確需求與邊界條件。
- **確保品質**：每項功能必須有對應的測試覆蓋，包括成功路徑、失敗路徑、邊界案例與異常處理。
- **降低缺陷**：提前發現設計問題，減少後期修改成本。
- **易於重構**：測試作為執行檔案文件，確保重構不破壞既有功能。
- **可追溯性**：測試案例清楚記錄功能行為與驗收條件。

### TDD 開發流程

```
1. 撰寫測試案例 → 2. 執行測試（預期失敗）→ 3. 實作功能 → 4. 執行測試（預期通過）→ 5. 重構優化
```

---

## 文件更新政策

**所有程式碼變更必須同步更新相關文件**：

### 更新清單

| 變更類型 | 需更新的文件 |
|----------|--------------|
| 新增 API 端點 | `docs/proposal.md`（API 端點）、`openapi.yaml`、相關 `Module.md` |
| 資料契約變更 | `docs/proposal.md`（資料契約）、`docs/contract/*.json` |
| 架構調整 | `docs/architecture.md`、`docs/proposal.md`（架構章節） |
| 新增模組/目錄 | `docs/architecture.md`（目錄結構）、相關 `Module.md` |
| Phase 進度更新 | `docs/proposal.md`（實作路徑）、`docs/plans/MASTER_PLAN.md` |
| 共用工具變更 | `docs/PROJECT_MEMORY.md`（共用工具模組） |

### 文件一致性檢查

在提交 PR 前，請確認：
1. 所有程式碼變更已反映在相關文件中
2. 若修改 `docs/proposal.md`，已同步更新本文件（`Project.prompt.md`）
3. 測試案例已更新以覆蓋新功能或變更

---

## 新增功能時的重要步驟

> **📖 擴充規範**：見下文「擴充規範」章節與 [`docs/proposal.md`](../../../docs/proposal.md)

1. **閱讀專案記憶**：先閱讀 `docs/proposal.md`、`docs/architecture.md` 確認設計方向。
2. **參考擴充規範**：見下文「擴充規範」章節。
3. **測試先行**：在 `tests/` 目錄中先建立測試案例；若無對應測試檔則新增。
4. **實作功能**：根據規格與測試案例實作。
5. **驗證通過**：確保所有測試案例通過。
6. **更新文件**：同步更新相關文件（見上方「文件更新政策」）。

此流程確保新功能的一致性與完整性，絕勿跳過。如有疑問，請參考 `docs/proposal.md`。

---
## 標準資料契約（JSON Schema）

> **📖 完整契約定義**：參見 [`docs/proposal.md`](../../../docs/proposal.md#資料契約與標準化格式) 與 [`docs/contract/`](../../../docs/contract/)

### 設計原則

本專案嚴格遵循 **Model Context Protocol (MCP)** 規範：
- **標準化 JSON Schema**：所有指令/事件使用統一的 JSON Schema 驗證
- **全鏈路追蹤**：每個請求攜帶 `trace_id` (UUIDv4) 實現全鏈路追蹤
- **上下文管理**：依 MCP 規範實作完整的上下文與記憶管理（Context Management）
- **冪等性支援**：使用 `command.id` 或冪等鍵避免重複執行

### 通用欄位（所有請求/回應/事件均推薦包含）
- trace_id：全鏈路追蹤 ID（UUIDv4）。
- timestamp：ISO8601 時間戳（UTC）。
- actor：觸發者（human|ai|system）與識別資訊。
- source：入口來源（webui|api|cli|scheduler|…）。
- labels：可選鍵值標籤（環境、租戶、任務編號等）。

指令請求 CommandRequest（範例，詳見 proposal.md）：
```json
{
	"trace_id": "uuid-v4",
	"timestamp": "2025-10-16T10:30:00Z",
	"actor": {
		"type": "human|ai|system",
		"id": "user-123",
		"name": "張三"
	},
	"source": "webui|api|cli|scheduler",
	"command": {
		"id": "cmd-xxx",
		"type": "robot.action",
		"target": {
			"robot_id": "robot_7",
			"robot_type": "humanoid"
		},
		"params": {
			"action_name": "go_forward",
			"duration_ms": 3000,
			"speed": "normal"
		},
		"timeout_ms": 10000,
		"priority": "low|normal|high"
	},
	"auth": {
		"token": "<jwt-token>"
	},
	"labels": {
		"department": "研發部",
		"project": "demo-001"
	}
}
```

指令回應 CommandResponse（範例，詳見 proposal.md）：
```json
{
	"trace_id": "uuid-v4",
	"timestamp": "2025-10-16T10:30:05Z",
	"command": {
		"id": "cmd-xxx",
		"status": "accepted|running|succeeded|failed|cancelled"
	},
	"result": {
		"data": {
			"execution_time_ms": 2850,
			"final_position": {"x": 1.2, "y": 0.5}
		},
		"summary": "動作執行完成"
	},
	"error": {
		"code": "ERR_ROBOT_OFFLINE",
		"message": "機器人連線中斷",
		"details": {"last_ping": "2025-10-16T10:29:50Z"}
	}
}
```

事件/日誌 EventLog（監控/審計用，詳見 proposal.md）：
```json
{
	"trace_id": "uuid-v4",
	"timestamp": "2025-10-16T10:30:03Z",
	"severity": "INFO|WARN|ERROR",
	"category": "command|auth|protocol|robot|audit",
	"message": "機器人開始執行動作 go_forward",
	"context": {
		"command_id": "cmd-xxx",
		"robot_id": "robot_7",
		"user_id": "user-123"
	}
}
```

錯誤格式（統一，詳見 proposal.md）：
```json
{
	"code": "ERR_TIMEOUT|ERR_UNAUTHORIZED|ERR_VALIDATION|ERR_ROUTING|ERR_PROTOCOL|ERR_INTERNAL",
	"message": "人類可讀訊息",
	"details": { "hint": "排查建議或關鍵欄位" }
}
```

## 指令處理流程（高層級）

> **📖 完整處理流程**：參見 [`docs/proposal.md`](../../../docs/proposal.md#資料流向)
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

> **📖 完整安全設計**：參見 [`docs/proposal.md`](../../../docs/proposal.md#安全性設計)
- 身份驗證（AuthN）：建議採 JWT/OAuth2 或可插拔 Token；支援短期 token 與刷新流程。
- 授權（AuthZ）：最小權限原則；RBAC 角色示例：viewer/operator/admin/auditor。
- 審計與追溯：所有安全相關操作（登入、審批、覆寫）必須記錄 EventLog（category=audit）。
- 秘密管理：API 金鑰、密碼、連線字串放置於環境變數或密管服務，不提交到版本庫。
- 輸入輸出安全：對命令參數作邊界/白名單校驗；輸出脫敏（PII/秘鑰）。

## 人類介入與手動覆寫

> **📖 完整介入操作**：參見 [`docs/proposal.md`](../../../docs/proposal.md#3-webui-層人機介面)
- 審批流程：高風險指令（如急停、越權操作）需人工審批後才可執行。
- 介入動作：pause/resume/cancel/override；所有介入需記審計事件並關聯 trace_id。
- 回滾與保護：支援安全停止/回復策略（如安全姿態、原地停止）。
- WebUI 呈現：清楚展示狀態流轉、當前風險與下一步建議。

## WebUI 模組職責界定

> **📖 完整模組設計**：參見 [`docs/architecture.md`](../../../docs/architecture.md#5-webui-webui) 與 [`WebUI/Module.md`](../../../WebUI/Module.md)

- 只與 MCP 交互：不直接連線機器人；透過 API/事件匯流排存取狀態與日誌。
- 功能：使用者登入/審批中心/指令下達/狀態面板/日誌查詢/告警訂閱。
- 體驗：即時性（WebSocket/SSE）、可觀測性（指標/追蹤）、可操作（介入按鈕）。
- 參考：`WebUI/Module.md`、`tests/` 測試用例。

---

## Edge 層進階功能（LLM 與插件整合）

> **📖 詳細說明**：參見 [`docs/MCP_LLM_PROVIDERS.md`](../../../docs/MCP_LLM_PROVIDERS.md) 與 [`docs/MCP_PLUGIN_ARCHITECTURE.md`](../../../docs/MCP_PLUGIN_ARCHITECTURE.md)

### LLM 整合（Phase 2+）

Edge 層支援本地與雲端 LLM 提供商整合：
- **`LLMProviderManager`**：統一管理 LLM 提供商（Ollama、LM Studio、雲端服務）
- **自動偵測**：啟動時自動偵測本地可用的 LLM 服務
- **健康監控**：持續監控 LLM 服務狀態，支援自動回退
- **指令解析**：使用 LLM 解析自然語言指令為標準化 CommandRequest

### 插件架構（Phase 2+）

Edge 層提供可擴充的插件系統：
- **指令插件**（CommandPlugin）：擴充指令處理能力
- **裝置插件**（DevicePlugin）：支援新的機器人類型
- **整合插件**（IntegrationPlugin）：第三方服務整合

### 進階指令與向後相容性

> **📖 詳細說明**：參見 [`docs/ADVANCED_COMMAND_RESPONSIBILITY_CHANGE.md`](../../../docs/ADVANCED_COMMAND_RESPONSIBILITY_CHANGE.md)

- **進階指令解碼**：已從 Robot-Console 移至 WebUI 處理
- **新格式支援**：`{"actions": [...]}` 序列化動作格式
- **向後相容**：舊格式指令仍可正常執行
- **審計追蹤**：所有進階指令執行均記錄完整審計軌跡

---

## 可審計性要求

本專案所有操作必須符合以下可審計性要求：

1. **全鏈路追蹤**：每個請求攜帶 `trace_id`，可追溯完整執行路徑
2. **事件記錄**：所有操作產生 EventLog，包含 `trace_id`、`timestamp`、`actor`、`context`
3. **審計日誌**：安全相關操作（登入、審批、覆寫、緊急停止）記錄 `category=audit` 事件
4. **不可刪除**：審計日誌僅可匯出與歸檔，不可刪除
5. **合規報表**：支援生成 ISO 27001/SOC 2 合規報表

---

## 擴充規範（指令/協定/機器人）

> **📖 擴充指南**：參見 [`docs/proposal.md`](../../../docs/proposal.md)
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
- 命名與目錄：以模組邏輯分區；測試放置於 `tests/` 對應檔；文件放置於模組目錄下的 `Module.md`。

---

## 完成定義（Definition of Done）

> **📖 完整 DoD**：參見 [`docs/proposal.md`](../../../docs/proposal.md#成功標準)
- 有對應的資料契約（Schema/範例）與文件更新（MCP 或 WebUI 的 `Module.md`）。
- 單元測試涵蓋率達到基本場景（成功、驗證錯、授權錯、超時/重試、日誌產生）。
- 事件與審計：產生必要的 EventLog，包含 trace_id 與關鍵上下文。
- 安全檢查：敏感資訊不落地；權限與輸入檢查通過；沒有硬編碼密鑰。
- 可觀測性：關鍵指標（成功率、延遲、錯誤碼分佈）可被查詢。
- **如有疑慮，請參考 `docs/proposal.md` 的成功標準與範例。**

---

## 下一步與落地任務

> **📖 完整實作路徑**：參見 [`docs/proposal.md`](../../../docs/proposal.md#實作路徑) 與 [`docs/plans/MASTER_PLAN.md`](../../../docs/plans/MASTER_PLAN.md)

- 補齊 MCP 契約與處理流程細節：見 `MCP/Module.md`。
- WebUI 介面與交互流程：見 `WebUI/Module.md` 與 `tests/` 測試檔。
- 逐步補充各模組單元測試：見 `tests/` 目錄下對應檔案。
- Phase 3 規劃：見 [`docs/plans/PHASE3_EDGE_ALL_IN_ONE.md`](../../../docs/plans/PHASE3_EDGE_ALL_IN_ONE.md)。

---

## 結構整理與清理建議

> 建立新檔案/資料夾後，請同步更新對應 `Module.md`，並移除不再使用或重複的檔案與相依。

最小檢查清單：
- 目錄命名與模組歸屬一致（MCP/WebUI/src/common/Robot-Console）。
- 無未使用的檔案與測試草稿；移除或合併陳舊文件。
- `requirements.txt` 僅保留實際使用套件；敏感設定移至環境變數。
- 文件以中文撰寫，與此規範一致；段落精簡、範例可直接複用。

---

## 參考文件索引

### 權威規格文件

| 文件 | 用途 |
|------|------|
| [`docs/proposal.md`](../../../docs/proposal.md) | **權威規格**：專案目標、核心設計、資料契約、成功標準 |
| [`docs/architecture.md`](../../../docs/architecture.md) | 目錄結構、模組職責、Server-Edge-Runner 架構 |
| [`docs/plans/MASTER_PLAN.md`](../../../docs/plans/MASTER_PLAN.md) | WebUI → Native App 轉換完整計畫 |

### Phase 2 相關文件

| 文件 | 用途 |
|------|------|
| [`docs/PHASE2_COMPLETION_SUMMARY.md`](../../../docs/PHASE2_COMPLETION_SUMMARY.md) | Phase 2 完成摘要 |
| [`docs/MCP_LLM_PROVIDERS.md`](../../../docs/MCP_LLM_PROVIDERS.md) | LLM 提供商整合指南 |
| [`docs/MCP_PLUGIN_ARCHITECTURE.md`](../../../docs/MCP_PLUGIN_ARCHITECTURE.md) | 插件架構指南 |
| [`docs/ADVANCED_COMMAND_RESPONSIBILITY_CHANGE.md`](../../../docs/ADVANCED_COMMAND_RESPONSIBILITY_CHANGE.md) | 進階指令職責變更 |

### 模組設計文件

| 文件 | 用途 |
|------|------|
| `MCP/Module.md` | MCP 服務層詳細設計 |
| `WebUI/Module.md` | WebUI 模組設計 |
| `Robot-Console/module.md` | 機器人抽象層設計 |
| `docs/contract/*.json` | 資料契約 JSON Schema |

---

**最後更新**：2025-11-26  
**版本**：v2.0（對齊 Phase 2 完成狀態）  
**相關 Phase 狀態**：Phase 2 完成，Phase 3 規劃中