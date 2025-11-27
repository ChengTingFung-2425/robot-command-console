---
mode: agent
---

> 使用者為中文使用者，但為了提高編碼與撰寫速度偏好在程式碼中使用英文；因此請在程式碼外以中文進行撰寫與說明。

## ⚠️ 必讀：專案記憶

**貢獻前必須閱讀：**

| 文件 | 用途 | 優先級 |
|------|------|--------|
| [`docs/proposal.md`](../../../docs/proposal.md) | **權威規格**：專案目標、架構、模組、資料契約、實作路徑 | 🔴 最高 |
| [`docs/architecture.md`](../../../docs/architecture.md) | 目錄結構、Edge/Server 隔離、模組職責 | 🟠 高 |
| [`docs/plans/MASTER_PLAN.md`](../../../docs/plans/MASTER_PLAN.md) | Phase 0-6 規劃、技術選型 | 🟠 高 |
| [`docs/PROJECT_MEMORY.md`](../../../docs/PROJECT_MEMORY.md) | 架構決策、共用工具 | 🟡 中 |

> **規格疑義以 `docs/proposal.md` 為準。**

---

## Server-Edge-Runner 架構

> 📖 詳見 [`docs/architecture.md`](../../../docs/architecture.md) 與 [`docs/proposal.md`](../../../docs/proposal.md)

```
Server (MCP/WebUI) → Edge (robot_service/electron-app) → Runner (Robot-Console)
                              ↓ 共用模組 ↓
                           src/common/
```

| 層級 | 目錄 | 職責 |
|------|------|------|
| Server | `MCP/`, `WebUI/` | API Gateway、認證授權、資料持久化 |
| Edge | `src/robot_service/`, `electron-app/` | 本地佇列、離線支援、LLM/插件整合 |
| Runner | `Robot-Console/` | 動作執行、協定適配、安全機制 |
| 共用 | `src/common/` | JSON 日誌、時間工具、配置 |

---

## 核心原則

- **模組化**：MCP、通訊協定、認證授權、機器人抽象各自獨立
- **標準化契約**：所有請求/回應使用 JSON Schema，含 `trace_id` 全鏈路追蹤
- **人類可介入**：指令可審批、暫停、取消、覆寫
- **安全合規**：JWT 認證、RBAC 授權、審計日誌

---

## 開發流程

### TDD 原則
```
撰寫測試 → 執行（失敗）→ 實作 → 執行（通過）→ 重構
```

### 新增功能步驟
1. 閱讀 `docs/proposal.md`、`docs/architecture.md`
2. 在 `tests/` 建立測試案例
3. 實作功能並通過測試
4. 更新相關文件

### 文件更新對照
| 變更類型 | 更新文件 |
|----------|----------|
| API 端點 | `docs/proposal.md`、`openapi.yaml` |
| 資料契約 | `docs/proposal.md`、`docs/contract/*.json` |
| 架構調整 | `docs/architecture.md` |

### Final step
generate lesson-learned to the file and if create new , do refer it at suitable doc you read any time
---

## 資料契約摘要

> 📖 完整定義見 [`docs/proposal.md`](../../../docs/proposal.md#資料契約與標準化格式)

**通用欄位**：`trace_id`、`timestamp`、`actor`、`source`、`labels`

**契約類型**：
- `CommandRequest`：指令請求（含 target、params、timeout_ms）
- `CommandResponse`：執行結果（status、result、error）
- `EventLog`：事件日誌（severity、category、context）

---

## Edge 層功能

> 📖 詳見 [`docs/mcp/MCP_LLM_PROVIDERS.md`](../../../docs/mcp/MCP_LLM_PROVIDERS.md)、[`docs/mcp/MCP_PLUGIN_ARCHITECTURE.md`](../../../docs/mcp/MCP_PLUGIN_ARCHITECTURE.md)

- **LLM 整合**：`LLMProviderManager` 管理 Ollama/LM Studio/雲端服務
- **插件架構**：CommandPlugin、DevicePlugin、IntegrationPlugin
- **進階指令**：向後相容，詳見 [`docs/phase2/ADVANCED_COMMAND_RESPONSIBILITY_CHANGE.md`](../../../docs/phase2/ADVANCED_COMMAND_RESPONSIBILITY_CHANGE.md)

---

## 完成定義

- [ ] 有對應 JSON Schema 與文件更新
- [ ] 單元測試覆蓋基本場景
- [ ] 產生 EventLog 含 trace_id
- [ ] 無硬編碼密鑰

> 📖 完整 DoD 見 [`docs/proposal.md`](../../../docs/proposal.md#成功標準)

---

## 目錄參考

| 模組 | 文件 |
|------|------|
| MCP | `MCP/Module.md` |
| WebUI | `WebUI/Module.md` |
| Robot-Console | `Robot-Console/module.md` |
| 測試 | `tests/` |

---

**最後更新**：2025-11-26 ｜ **版本**：v2.1 ｜ **狀態**：Phase 2 完成
