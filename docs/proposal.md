# 機器人指令中介層系統（MCP 伺服器）

## 專案目標

**建立一個標準化的機器人指令中介平台（基於模型上下文協議 MCP），能夠安全、可靠地接收、處理並轉發來自人類與 AI 客戶端的指令至各種類型的機器人，並提供完整的監控、審計與人類介入能力。**

### 核心設計理念
1. **模組化架構**：各功能模組（指令處理、機器人抽象、通訊協定、認證授權、日誌監控）獨立設計，可單獨開發、測試與擴充。
2. **標準化契約**：所有模組間通訊採用統一的 JSON 資料格式，支援全鏈路追蹤（trace_id）。
3. **人類優先**：WebUI 提供完整的監控與介入能力，確保人類可隨時掌控系統。
4. **可擴充性**：新增機器人類型或通訊協定僅需最小化修改。
5. **安全與審計**：所有操作可追溯，敏感操作需審批，權限嚴格控管。


## 系統架構

### Server-Edge-Runner 三層架構（Phase 2+）

Phase 2 開始演進為 Server-Edge-Runner 三層架構，Phase 3 將完整實作：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Cloud / Server Layer                             │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                        Cloud Services                               │ │
│  │  • 進階指令共享與排名                                                │ │
│  │  • 用戶討論區                                                       │ │
│  │  • 用戶授權與信任評級                                                │ │
│  │  • 共享 LLM 分析服務（大數據優化）                                   │ │
│  │  • 固件倉庫                                                         │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                          HTTPS/WSS （當網路可用時）
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                      Edge Layer (ALL-in-One Edge App)                    │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                     Unified Launcher                                │ │
│  │  一鍵啟動/停止所有服務 | LLM 選擇介面 | 系統健康監控                 │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐        │
│  │   Local WebUI    │ │   MCP Service    │ │   Robot Service  │        │
│  │  • 用戶設定介面  │ │  • 指令協調      │ │  • 本地佇列      │        │
│  │  • 機器人監控   │ │  • LLM 處理器    │ │  • Worker Pool   │        │
│  │  • 固件更新     │ │  • 插件系統      │ │  • 離線緩衝      │        │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘        │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    Local LLM Provider                               │ │
│  │                 (Ollama / LM Studio / Cloud fallback)               │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                          Hardware Interface
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                          Runner Layer                                    │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                     Robot-Console                                   │ │
│  │  • 動作執行器（ActionExecutor）                                     │ │
│  │  • 協定適配（HTTP/MQTT/WS/Serial/ROS）                              │ │
│  │  • 緊急停止與安全機制                                               │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Humanoid   │  │     AGV     │  │    Drone    │  │     Arm     │    │
│  │   robot_7   │  │   robot_3   │  │   robot_9   │  │   robot_12  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 層級職責

| 層級 | 目錄 | 職責 |
|------|------|------|
| **Cloud/Server** | 雲端服務 | 進階指令共享、討論區、授權、LLM 分析 |
| **Edge** | `src/robot_service/`, `electron-app/`, `MCP/`, `WebUI/` | 本地處理、佇列、LLM、監控 |
| **Runner** | `Robot-Console/` | 動作執行、硬體控制、安全機制 |
| **共用** | `src/common/` | 日誌、時間、配置工具 |

### 資料流向

1. **指令下達**：用戶 → Edge WebUI → MCP（LLM 解析）→ Robot Service（佇列）→ Robot-Console → 機器人
2. **狀態回報**：機器人 → Robot-Console → Robot Service → Edge WebUI（即時顯示）
3. **雲端同步**：Edge ↔ Cloud（進階指令、用戶設定、分析資料）
4. **審計追蹤**：所有操作 → 本地事件日誌（含 trace_id）→ 可選上傳雲端

## 核心功能模組

### 1. MCP 服務層（中介層）
**職責**：統一的 API 入口、指令處理、路由與狀態管理

**子模組**：
- **指令處理**：接收、驗證（JSON Schema）、排隊、路由、重試、超時控制
- **認證授權**：JWT/OAuth2 身份驗證、RBAC/ABAC 權限控管、操作審計
- **上下文管理**：指令上下文、狀態歷史、冪等鍵管理、trace_id 追蹤
- **機器人路由**：機器人註冊表、健康檢查、負載平衡、容錯轉移
- **日誌監控**：事件流、審計記錄、性能指標、告警通知

**API 端點**：
- `POST /api/command`：下達指令
- `GET /api/status?command_id=xxx`：查詢狀態
- `WS /api/events`：事件訂閱（WebSocket/SSE）
- `GET /api/robots`：查詢可用機器人
- `POST /api/robots/register`：機器人註冊
- `POST /api/control/{pause|resume|cancel}`：介入操作
- `GET /api/advanced_commands`：查詢進階指令清單
- `POST /api/advanced_commands`：提交進階指令
- `POST /api/advanced_commands/{id}/audit`：審核進階指令（Admin/Auditor）

### 2. Robot-Console 層（機器人抽象）
**職責**：將標準化指令轉換為機器人特定格式，處理執行與回報

**核心組件**：
- **ActionExecutor**：基於執行緒佇列的動作執行引擎，支援並行、超時、中斷
- **協定適配器**：支援 HTTP、MQTT、WebSocket、gRPC、ROS/ROS2 等多種協定
- **工具定義（tools.py）**：提供給 AI 代理的動作清單與 JSON Schema
- **狀態回報**：執行進度、結果與錯誤即時回傳給 MCP

**支援的機器人類型**：
- **人形機器人**（Humanoid）：38+ 個動作（移動/格鬥/運動/舞蹈/手勢）
- **移動機器人**（AGV/AMR）：導航、路徑規劃、避障
- **機械臂**（Manipulator）：抓取、放置、組裝
- **無人機**（Drone）：起飛、降落、巡航
- **可擴充**：透過繼承基礎類別新增新類型

### 3. WebUI 層（人機介面）
**職責**：提供人類操作員的監控、控制與介入介面

**核心頁面**：
- **首頁**：專案介紹、登入/註冊入口
- **機器人儀表板**：顯示所有機器人狀態、能力與健康狀況
- **指令控制中心**：選擇機器人、選擇動作、輸入參數、下達指令
- **執行監控面板**：即時顯示進行中與歷史指令、進度條、事件流
- **進階指令分享區**：用戶建立、分享、瀏覽基於基礎指令組合的進階指令
- **審批中心**：高風險指令審批、審批歷史、稽核記錄（Admin/Auditor）
- **日誌與告警**：事件過濾、錯誤告警、匯出功能

**人類介入操作**：
- **暫停/繼續**（Pause/Resume）：暫時停止執行並可恢復
- **取消**（Cancel）：終止執行並記錄原因
- **覆寫**（Override）：修改執行中的參數（需審批）
- **緊急停止**（Emergency Stop）：立即停止所有機器人（最高權限）

**進階指令功能**：
- **建立**：登入用戶可基於基礎指令序列建立進階指令，提交審核
- **審核**：Admin/Auditor 可批准或拒絕進階指令
- **分享**：審核通過的進階指令公開展示，供其他用戶參考與使用
- **分類與搜尋**：依類別、關鍵字過濾進階指令

### 4. 通訊協定層
**支援的協定**：
- **HTTP/REST**：同步指令與查詢、適用於簡單請求
- **MQTT**：非同步訊息、IoT 場景、支援 QoS
- **WebSocket**：即時雙向通訊、適合狀態訂閱
- **gRPC**：高效能 RPC、適合內部服務通訊
- **ROS/ROS2**：機器人作業系統標準協定

**可靠性保證**：
- 重試機制（指數退避 + 隨機抖動）
- 超時控制與逾時處理
- 斷線重連與狀態同步
- 訊息去重（基於冪等鍵）
## 資料契約與標準化格式

### 指令請求（CommandRequest）
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

### 指令回應（CommandResponse）
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

### 事件（Event）
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

## 安全性設計

### 認證（Authentication）
- **JWT Token**：短期 access token（15分鐘）+ refresh token（7天）
- **OAuth2**：支援第三方登入（Google/GitHub）
- **API Key**：用於 AI 代理與自動化腳本

### 授權（Authorization）
**角色定義（RBAC）**：
- **Viewer**（觀察者）：僅可查看機器人狀態與歷史記錄
- **Operator**（操作員）：可下達一般指令，需審批高風險操作
- **Admin**（管理員）：完整權限，包括審批、覆寫、緊急停止
- **Auditor**（稽核員）：可查看所有日誌與審計記錄，無操作權限

**權限粒度**：
- 指令類型限制（如僅允許移動類指令）
- 機器人範圍限制（僅可操作特定機器人）
- 時間窗口限制（僅在工作時間操作）

### 審計與合規
- 所有指令與介入操作記錄 trace_id、操作人、時間戳
- 敏感操作（覆寫、緊急停止）需雙因素確認
- 審計日誌不可刪除，僅可匯出與歸檔
- 支援合規報表生成（ISO 27001/SOC 2）

## 可觀測性與監控

### 關鍵指標（Metrics）
- **成功率**：指令執行成功/失敗比例
- **延遲**：P50/P95/P99 執行時間
- **吞吐量**：每秒處理指令數（QPS）
- **錯誤分佈**：各錯誤碼的發生頻率
- **機器人健康**：在線率、響應時間、故障次數

### 告警規則
- 機器人離線超過 5 分鐘
- 指令失敗率超過 10%
- 平均延遲超過閾值（如 5 秒）
- 認證失敗次數異常（潛在攻擊）

### 追蹤（Tracing）
- 全鏈路 trace_id 追蹤
- 支援 OpenTelemetry 標準
- 可視化執行時間線與依賴關係

## 實作路徑

### 階段總覽

| Phase | 名稱 | 狀態 | 說明 |
|-------|------|------|------|
| Phase 0 | 探勘與需求收斂 | ✅ 完成 | 需求清單、目標平台矩陣 |
| Phase 1 | 技術選型與 Electron POC | ✅ 完成 | Electron 整合、Flask 背景服務 |
| Phase 2 | 模組化與後端服務層調整 | ✅ 完成 | 目錄重構、共用模組、LLM 整合、插件系統 |
| Phase 3 | ALL-in-One Edge App | 📋 規劃中 | Edge 部署、統一啟動器、Cloud 整合 |
| Phase 4 | 封裝、簽署與發佈管線 | ⏳ 待開始 | CI/CD、安裝程式 |
| Phase 5 | 測試、品質保證與監控 | ⏳ 待開始 | E2E 測試、錯誤追蹤 |
| Phase 6 | 釋出、支持與持續優化 | ⏳ 待開始 | 正式發佈、版本管理 |

### Phase 1：基礎架構（✅ 已完成）

- [x] MCP 服務層框架搭建（Flask/FastAPI）
- [x] 資料契約定義與 JSON Schema 驗證
- [x] 基礎認證授權（JWT + 簡單 RBAC）
- [x] Robot-Console 基礎抽象類別
- [x] 支援一種機器人類型（Humanoid）
- [x] 支援兩種協定（HTTP + MQTT）
- [x] Electron POC 完成

### Phase 2：模組化與後端服務層（✅ 已完成）

> 詳細內容請參見 [PHASE2_COMPLETION_SUMMARY.md](PHASE2_COMPLETION_SUMMARY.md)

**目錄結構重構**：
- [x] Electron 應用獨立至 `electron-app/`
- [x] 測試目錄標準化為 `tests/`
- [x] 共用模組建立於 `src/common/`
- [x] 機器人服務模組化至 `src/robot_service/`

**LLM 提供商整合**：
- [x] 自動偵測本地 LLM 服務（Ollama、LM Studio）
- [x] `LLMProviderManager` 統一管理介面
- [x] 健康監控與回退機制
- [x] 參見 [MCP_LLM_PROVIDERS.md](MCP_LLM_PROVIDERS.md)

**插件架構**：
- [x] 指令插件（`CommandPlugin`）
- [x] 裝置插件（`DevicePlugin`）
- [x] 整合插件（`IntegrationPlugin`）
- [x] 參見 [MCP_PLUGIN_ARCHITECTURE.md](MCP_PLUGIN_ARCHITECTURE.md)

**本地佇列系統**：
- [x] `src/robot_service/queue/` 優先權佇列
- [x] 非同步處理與 Worker Pool
- [x] 離線緩衝支援

**進階指令職責轉移**：
- [x] 進階指令解碼從 Robot-Console 移至 WebUI
- [x] 新格式 `{"actions": [...]}` 支援
- [x] 向後相容舊格式
- [x] 參見 [ADVANCED_COMMAND_RESPONSIBILITY_CHANGE.md](ADVANCED_COMMAND_RESPONSIBILITY_CHANGE.md)

### Phase 3：ALL-in-One Edge App（📋 規劃中）

> 詳細規劃請參見 [PHASE3_EDGE_ALL_IN_ONE.md](plans/PHASE3_EDGE_ALL_IN_ONE.md)

**核心目標**：將 MCP、WebUI、Robot-Console 整合為統一的 ALL-in-One Edge App，部署於消費級邊緣運算設備。

**Edge（本地）職責**：
- [ ] 用戶設定存儲
- [ ] 機器人監控與健康檢查
- [ ] 固件更新管理
- [ ] LLM 指令介面
- [ ] 離線模式支援

**Cloud（雲端）職責**：
- [ ] 進階指令共享與排名
- [ ] 用戶討論區
- [ ] 用戶授權與信任評級
- [ ] 共享 LLM 分析服務（大數據優化）

**子階段**：
- [ ] Phase 3.1：基礎整合（統一啟動器、服務協調、LLM 選擇 UI）
- [ ] Phase 3.2：功能完善（WebUI 本地版、監控、CLI/TUI）
- [ ] Phase 3.3：雲端整合（同步、共享指令、授權）
- [ ] Phase 3.4：打包與發佈（AppImage、DMG、NSIS、Docker）

**硬體目標**：
- Intel NUC / Beelink Mini-PC（x86_64）
- NVIDIA Jetson Nano/Xavier（ARM64 + GPU）
- Raspberry Pi 4/5（ARM64）

### Phase 4：封裝、簽署與發佈管線（⏳ 待開始）

- [ ] 自動化 CI/CD 腳本
- [ ] 打包與簽署設定（macOS、Windows、Linux）
- [ ] 發佈說明文件
- [ ] 安裝器或發佈包範例

### Phase 5：測試、品質保證與監控（⏳ 待開始）

- [ ] 測試計畫
- [ ] E2E 測試套件
- [ ] 錯誤追蹤設定（Sentry 等）
- [ ] 監控與使用分析儀表板

### Phase 6：釋出、支持與持續優化（⏳ 待開始）

- [ ] 發佈公告
- [ ] 支援手冊
- [ ] 版本管理策略
- [ ] 回饋蒐集與迭代計畫

## 技術棧

### 後端
- **語言**：Python 3.11+
- **框架**：Flask 2.x（現有）或 FastAPI（建議遷移）
- **資料庫**：PostgreSQL（指令歷史/審計日誌）+ Redis（快取/佇列）
- **訊息佇列**：RabbitMQ 或 Redis Pub/Sub
- **協定支援**：requests（HTTP）、paho-mqtt（MQTT）、websockets、grpcio

### 前端（WebUI）
- **現有**：Flask Templates + Bootstrap + jQuery
- **建議升級**：Vue.js 3 或 React（更好的即時性與互動）
- **即時通訊**：Socket.IO 或原生 WebSocket
- **視覺化**：Chart.js（指標圖表）、Timeline.js（事件時間軸）

### DevOps
- **容器化**：Docker + Docker Compose
- **編排**：Kubernetes（生產環境）
- **CI/CD**：GitHub Actions
- **監控**：Prometheus + Grafana
- **日誌**：ELK Stack（Elasticsearch + Logstash + Kibana）

## 風險與挑戰

### 技術風險
1. **協定相容性**：不同機器人使用不同協定，需要大量適配工作
   - **緩解**：優先支援主流協定，提供協定適配器範本
   
2. **即時性要求**：某些場景需要低延遲（如緊急停止）
   - **緩解**：使用 WebSocket 與優先佇列，關鍵指令直達

3. **併發控制**：多個指令同時操作同一機器人
   - **緩解**：機器人級別的鎖機制，佇列排序

### 業務風險
1. **安全性**：未授權操作或惡意指令
   - **緩解**：嚴格的認證授權、審批流程、操作審計

2. **可用性**：系統故障導致無法控制機器人
   - **緩解**：高可用架構、備援機制、降級策略

3. **可維護性**：新增機器人類型成本高
   - **緩解**：清晰的抽象層設計、完整文件、範例程式碼

## 成功標準

### 功能完整性
- ✅ 支援至少 3 種機器人類型
- ✅ 支援至少 3 種通訊協定
- ✅ WebUI 提供完整的監控與介入能力
- ✅ AI 代理可透過 API 下達指令

### 效能指標
- ✅ 指令延遲 P95 < 500ms
- ✅ 系統吞吐量 > 100 QPS
- ✅ 指令成功率 > 99%
- ✅ 機器人在線率 > 95%

### 安全與合規
- ✅ 所有操作可追溯（trace_id）
- ✅ 敏感操作需審批與雙因素確認
- ✅ 通過安全掃描（無高危漏洞）
- ✅ 符合資料保護法規（GDPR/CCPA）

### 可維護性
- ✅ 測試覆蓋率 > 80%
- ✅ API 文件完整（OpenAPI/Swagger）
- ✅ 新增機器人類型 < 1 人日
- ✅ 新增協定適配器 < 2 人日

## 參考資料

### 規劃文件
- [MASTER_PLAN.md](plans/MASTER_PLAN.md)：WebUI → Native App 轉換完整計畫
- [PHASE3_EDGE_ALL_IN_ONE.md](plans/PHASE3_EDGE_ALL_IN_ONE.md)：Phase 3 ALL-in-One Edge App 規劃
- [PROJECT_MEMORY.md](PROJECT_MEMORY.md)：專案記憶與架構決策

### Phase 2 文件
- [PHASE2_COMPLETION_SUMMARY.md](PHASE2_COMPLETION_SUMMARY.md)：Phase 2 完成摘要
- [MIGRATION_GUIDE_PHASE2.md](MIGRATION_GUIDE_PHASE2.md)：Phase 2 遷移指南
- [MCP_LLM_PROVIDERS.md](MCP_LLM_PROVIDERS.md)：LLM 提供商整合指南
- [MCP_PLUGIN_ARCHITECTURE.md](MCP_PLUGIN_ARCHITECTURE.md)：插件架構指南
- [ADVANCED_COMMAND_RESPONSIBILITY_CHANGE.md](ADVANCED_COMMAND_RESPONSIBILITY_CHANGE.md)：進階指令職責變更

### 模組設計文件
- `MCP/Module.md`：MCP 服務層詳細設計
- `Robot-Console/module.md`：機器人抽象層設計
- `WebUI/Module.md`：WebUI 模組設計
- `docs/contract/*.json`：資料契約 JSON Schema
- [architecture.md](architecture.md)：系統架構與目錄結構說明

### 技術標準
- Model Context Protocol（MCP）規範
- OpenAPI 3.0 規範（API 文件）
- OpenTelemetry 規範（追蹤與監控）
- ISO 27001（資訊安全管理）

---

**最後更新**：2025-11-26  
**版本**：v3.0  
**狀態**：Phase 2 完成，Phase 3 規劃中
