# 文件目錄索引（Documentation Index）

## 核心文件

| 文件 | 說明 |
|------|------|
| [`proposal.md`](proposal.md) | **權威規格**：專案目標、架構、模組、資料契約、實作路徑 |
| [`architecture.md`](architecture.md) | 目錄結構、Edge/Server 隔離、模組職責 |
| [`PROJECT_MEMORY.md`](PROJECT_MEMORY.md) | 架構決策記錄、共用工具模組 |

---

## 目錄結構

### 📁 plans/
專案規劃文件

| 文件 | 說明 |
|------|------|
| [`MASTER_PLAN.md`](plans/MASTER_PLAN.md) | Phase 0-6 完整規劃 |
| [`PHASE3_EDGE_ALL_IN_ONE.md`](plans/PHASE3_EDGE_ALL_IN_ONE.md) | Phase 3 ALL-in-One Edge App 規劃 |
| [`webui-to-app/`](plans/webui-to-app/) | WebUI 轉 Native App 技術文件 |

### 📁 phase1/
Phase 1（Electron POC）相關文件

| 文件 | 說明 |
|------|------|
| [`PHASE1_INDEX.md`](phase1/PHASE1_INDEX.md) | Phase 1 文件索引 |
| [`PHASE1_README.md`](phase1/PHASE1_README.md) | Phase 1 總覽 |
| [`PHASE1_COMPLETE.md`](phase1/PHASE1_COMPLETE.md) | Phase 1 完成報告 |
| [`electron-testing-guide.md`](phase1/electron-testing-guide.md) | Electron 測試指南 |

### 📁 phase2/
Phase 2（模組化重構）相關文件

| 文件 | 說明 |
|------|------|
| [`PHASE2_COMPLETION_SUMMARY.md`](phase2/PHASE2_COMPLETION_SUMMARY.md) | Phase 2 完成摘要 |
| [`MIGRATION_GUIDE_PHASE2.md`](phase2/MIGRATION_GUIDE_PHASE2.md) | Phase 2 遷移指南 |
| [`robot-service-migration.md`](phase2/robot-service-migration.md) | Robot Service 遷移 |
| [`ADVANCED_COMMAND_RESPONSIBILITY_CHANGE.md`](phase2/ADVANCED_COMMAND_RESPONSIBILITY_CHANGE.md) | 進階指令職責變更 |

### 📁 mcp/
MCP（Model Context Protocol）相關文件

| 文件 | 說明 |
|------|------|
| [`MCP_LLM_PROVIDERS.md`](mcp/MCP_LLM_PROVIDERS.md) | LLM 提供商整合指南 |
| [`MCP_PLUGIN_ARCHITECTURE.md`](mcp/MCP_PLUGIN_ARCHITECTURE.md) | 插件架構設計 |

### 📁 security/
安全相關文件

| 文件 | 說明 |
|------|------|
| [`api-security-guide.md`](security/api-security-guide.md) | API 安全指南 |
| [`API_SECURITY_IMPLEMENTATION_SUMMARY.md`](security/API_SECURITY_IMPLEMENTATION_SUMMARY.md) | 安全實施摘要 |
| [`security-checklist.md`](security/security-checklist.md) | 安全檢查清單 |
| [`threat-model.md`](security/threat-model.md) | 威脅模型分析 |
| [`password-reset-implementation.md`](security/password-reset-implementation.md) | 密碼重設實施 |

### 📁 features/
功能實施文件

| 文件 | 說明 |
|------|------|
| [`observability-guide.md`](features/observability-guide.md) | 可觀測性指南 |
| [`observability-implementation.md`](features/observability-implementation.md) | 可觀測性實施摘要 |
| [`queue-architecture.md`](features/queue-architecture.md) | 佇列架構設計 |
| [`user-engagement-system.md`](features/user-engagement-system.md) | 用戶互動系統 |
| [`media-streaming-feature.md`](features/media-streaming-feature.md) | 媒體串流功能 |
| [`webui-testing-guide.md`](features/webui-testing-guide.md) | WebUI 測試指南 |

### 📁 contract/
JSON Schema 契約定義

| 文件 | 說明 |
|------|------|
| [`command_request.schema.json`](contract/command_request.schema.json) | 指令請求 Schema |
| [`command_response.schema.json`](contract/command_response.schema.json) | 指令回應 Schema |
| [`event_log.schema.json`](contract/event_log.schema.json) | 事件日誌 Schema |
| [`error.schema.json`](contract/error.schema.json) | 錯誤格式 Schema |

---

## 快速導航

- **入門**：[`proposal.md`](proposal.md) → [`architecture.md`](architecture.md)
- **Phase 狀態**：[`plans/MASTER_PLAN.md`](plans/MASTER_PLAN.md)
- **安全**：[`security/`](security/)
- **MCP/LLM**：[`mcp/`](mcp/)
- **測試**：[`phase1/electron-testing-guide.md`](phase1/electron-testing-guide.md)、[`features/webui-testing-guide.md`](features/webui-testing-guide.md)

---

**最後更新**：2025-11-26
