# 專案記憶與架構決策

> 此文件記錄專案的關鍵架構決策、設計模式和重要資訊，作為團隊的共享知識庫。

## 📋 重要文件索引

| 文件 | 用途 |
|------|------|
| [MASTER_PLAN.md](plans/MASTER_PLAN.md) | WebUI → Native App 轉換的完整計畫（合併版） |
| [architecture.md](architecture.md) | 系統架構與目錄結構說明 |
| [proposal.md](proposal.md) | 專案原始提案 |

## 🏗️ 架構演進

### Server-Edge-Runner 三層架構

本專案將演進為 **Server-Edge-Runner** 三層架構：

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Server      │────▶│      Edge       │────▶│     Runner      │
│  (MCP/WebUI)    │     │ (robot_service) │     │ (Robot-Console) │
│  集中管理/API   │     │ 本地處理/佇列   │     │ 機器人執行     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

| 層級 | 目前目錄 | 未來目錄（規劃） | 職責 |
|------|----------|------------------|------|
| Server | `MCP/`, `WebUI/` | `src/server/` | API Gateway、認證授權、數據持久化 |
| Edge | `src/robot_service/`, `electron-app/` | `src/edge/` | 本地佇列、離線支援、低延遲處理 |
| Runner | `Robot-Console/` | `src/runner/` | 機器人控制、感測器整合、安全機制 |
| 共用 | `src/common/` | `src/common/` | 日誌、時間工具、配置 |

### 基於 Microblog 的 Server-Client 架構

WebUI 基於 Flask Microblog 的 Server-Client 架構設計，未來將拆分為：
- **Server 端**：API 後端、認證授權、資料庫管理、業務邏輯
- **Edge 端**：前端 UI、本地快取、離線支援

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

## 🚀 Phase 3+ 規劃

- [ ] Server-Edge-Runner 架構完整實作
- [ ] Redis/Kafka 整合（分散式佇列）
- [ ] 邊緣運算支援（本地 LLM）
- [ ] Kubernetes 部署
- [ ] 多租戶支援

## 📝 重要提醒

1. **新增共用工具**：放在 `src/common/`，由 `MCP/utils/` 和 `src/robot_service/utils/` 重新導出
2. **環境區分**：使用 `ENV_TYPE=edge` 或 `ENV_TYPE=server`
3. **文檔位置**：規劃文檔放 `docs/plans/`，技術文檔放 `docs/`

---

**最後更新**：2025-11-26  
**版本**：Phase 2
