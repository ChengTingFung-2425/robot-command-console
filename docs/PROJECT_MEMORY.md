# 專案記憶與架構決策

> 此文件記錄專案的關鍵架構決策、設計模式和重要資訊，作為團隊的共享知識庫。

## 📋 重要文件索引

| 文件 | 用途 |
|------|------|
| [MASTER_PLAN.md](plans/MASTER_PLAN.md) | WebUI → Native App 轉換的完整計畫（合併版） |
| [PHASE3_EDGE_ALL_IN_ONE.md](plans/PHASE3_EDGE_ALL_IN_ONE.md) | Phase 3 ALL-in-One Edge App 詳細規劃 |
| [phase3/PHASE3_1_STATUS_REPORT.md](phase3/PHASE3_1_STATUS_REPORT.md) | Phase 3.1 分析與優化狀態報告 |
| [phase2/PHASE2_COMPLETION_SUMMARY.md](phase2/PHASE2_COMPLETION_SUMMARY.md) | Phase 2 完成摘要與成果記錄 |
| [architecture.md](architecture.md) | 系統架構與目錄結構說明 |
| [proposal.md](proposal.md) | 專案提案（含 Phase 進度） |
| [mcp/MCP_LLM_PROVIDERS.md](mcp/MCP_LLM_PROVIDERS.md) | LLM 提供商整合指南（Phase 2） |
| [mcp/MCP_PLUGIN_ARCHITECTURE.md](mcp/MCP_PLUGIN_ARCHITECTURE.md) | 插件架構指南（Phase 2） |
| [phase2/MIGRATION_GUIDE_PHASE2.md](phase2/MIGRATION_GUIDE_PHASE2.md) | Phase 2 遷移指南 |

## 🏗️ 架構演進

### Cloud-Edge-Runner 三層架構（與 proposal.md 一致）

本專案演進為 **Cloud-Edge-Runner** 三層架構：

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Cloud/Server   │────▶│      Edge       │────▶│     Runner      │
│  (雲端服務)     │     │ (ALL-in-One)    │     │ (Robot-Console) │
│  共享/授權/分析  │     │ 本地處理/佇列   │     │ 機器人執行     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

| 層級 | 目錄 | 職責 |
|------|------|------|
| **Cloud/Server** | 雲端服務 | 進階指令共享、討論區、授權、LLM 分析 |
| **Edge** | `src/robot_service/`, `electron-app/`, `MCP/`, `WebUI/` | 本地處理、佇列、LLM、監控 |
| **Runner** | `Robot-Console/` | 動作執行、硬體控制、安全機制 |
| **共用** | `src/common/` | 日誌、時間工具、配置 |

### 資料流向

1. **指令下達**：用戶 → Edge WebUI → MCP（LLM 解析）→ Robot Service（佇列）→ Robot-Console → 機器人
2. **狀態回報**：機器人 → Robot-Console → Robot Service → Edge WebUI（即時顯示）
3. **雲端同步**：Edge ↔ Cloud（進階指令、用戶設定、分析資料）

## 📁 目錄結構決策

### Phase 2 變更（2025-11）

1. **文檔重組**
   - Phase 1 文檔移至 `docs/phase1/`
   - 規劃文檔移至 `docs/plans/`
   - 獨立文檔（ELECTRON_POC_README.md、TESTING.md、proposal.md）移至 `docs/`

2. **共用模組建立**
   - 建立 `src/common/` 作為 Edge 和 Server 共用的工具模組
   - 消除 `CustomJsonFormatter` 在 3 個文件中的重複定義
   - 統一時間處理工具（`utc_now`, `utc_now_iso`, etc.）

3. **環境配置**
   - `EdgeConfig` - 邊緣環境配置（Electron、CLI）
   - `ServerConfig` - 伺服器環境配置（MCP API、WebUI）
   - 透過 `ENV_TYPE` 環境變數區分環境

## 🔧 共用工具模組

### src/common/

```python
# 日誌工具
from common import CustomJsonFormatter, setup_json_logging, get_logger

# 時間工具
from common import utc_now, utc_now_iso, parse_iso_datetime, format_timestamp

# 配置
from common import EdgeConfig, ServerConfig, get_config
```

### 使用方式

```python
# Edge 環境
from src.common.config import EdgeConfig
config = EdgeConfig.from_env()

# Server 環境
from src.common.config import ServerConfig
config = ServerConfig.from_env()

# 自動偵測
from src.common.config import get_config
config = get_config()  # 根據 ENV_TYPE 自動選擇
```

## 🔐 安全相關決策

1. **Token 認證**：使用 `Bearer Token` 認證
2. **Context Isolation**：Electron 使用 preload script 隔離
3. **本地綁定**：Flask 服務只監聽 `127.0.0.1`

## 📊 測試策略

- 測試統一在 `tests/` 目錄
- 結構測試：`test_phase2_structure.py`
- 佇列測試：`test_queue_system.py`
- 共用模組測試：`test_common_module_imports()`

## 🚀 Phase 3 規劃 — ALL-in-One Edge App

> **詳細規劃**：參見 [PHASE3_EDGE_ALL_IN_ONE.md](plans/PHASE3_EDGE_ALL_IN_ONE.md)

### 核心目標

將 MCP、WebUI、Robot-Console 整合為統一的 ALL-in-One Edge App，部署於消費級邊緣運算設備。

### 基於 Phase 2 的延續

Phase 3 建立在 Phase 2 完成的基礎上：

| Phase 2 成果 | Phase 3 運用 |
|-------------|-------------|
| `src/common/` 共用模組 | 繼續使用，擴充 Edge 專用工具 |
| `src/robot_service/` 佇列系統 | 整合至 Edge 服務層 |
| `LLMProviderManager` | 作為 Edge LLM 管理基礎 |
| `PluginManager` | 支援運行時插件熱載入 |
| Server-Edge-Runner 架構 | 完整實作三層分離 |

### Edge vs Cloud 職責劃分

**Edge（本地）**：
- 用戶設定儲存
- 機器人監控
- 固件更新管理
- LLM 指令介面
- 離線模式支援

**Cloud（雲端）**：
- 進階指令共享與排名
- 用戶討論區
- 用戶授權與信任評級
- 共享 LLM 分析服務（大數據優化）

### 子階段規劃

- [x] **Phase 3.1**：分析與優化（代碼去重、datetime 修復、測試更新）
- [ ] **Phase 3.2**：功能完善（WebUI 本地版、監控、CLI/TUI）
- [ ] **Phase 3.3**：雲端整合（同步、共享指令、授權）
- [ ] **Phase 3.4**：打包與發佈（AppImage、DMG、NSIS、Docker）

### 硬體目標

- Intel NUC / Beelink Mini-PC（x86_64）
- NVIDIA Jetson Nano/Xavier（ARM64 + GPU）
- Raspberry Pi 4/5（ARM64）

## 📝 重要提醒

1. **新增共用工具**：放在 `src/common/`，由 `MCP/utils/` 和 `src/robot_service/utils/` 重新導出
2. **環境區分**：使用 `ENV_TYPE=edge` 或 `ENV_TYPE=server`
3. **文檔位置**：規劃文檔放 `docs/plans/`，技術文檔放 `docs/`
4. **Phase 3 文檔**：詳見 `docs/plans/PHASE3_EDGE_ALL_IN_ONE.md`

---

**最後更新**：2025-11-27  
**版本**：Phase 3.1 完成
