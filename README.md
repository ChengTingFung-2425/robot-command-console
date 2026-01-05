# Robot Command Console

本專案（robot-command-console）是一個用於機器人指令管理、路由與執行的整合式控制台與服務平台。目標是提供一套模組化、可測試且可部署的系統，用來接收、驗證、路由並執行來自各種介面（WebUI、API、排程或其他整合服務）的指令，同時保留豐富的日誌、驗證與合約（schema）檢查。

> **📢 Phase 2 重大更新** - 目錄結構已重新組織以提高模組化和清晰度。詳見 [架構說明](docs/architecture.md) 和 [遷移指南](docs/phase2/MIGRATION_GUIDE_PHASE2.md)。

> **🚀 架構演進方向** - 本專案將演進為 **Server-Edge-Runner** 三層架構，支援分散式部署與邊緣運算。

> **🎉 雙版本策略（Phase 3.2）** - 提供 **Heavy (Electron)** 與 **Tiny (PyQt)** 兩個版本，使用者可根據需求選擇。詳見 [版本選擇指引](docs/user_guide/TINY_VS_HEAVY.md)。

> **✨ 統一整合完成（Phase 3.3）** - 提供統一部署套件 (`unified-edge-app/`)，一鍵啟動所有服務。雲端/社群功能已分離至 `Cloud/` 目錄。

## 核心目的

- 集中管理來自多來源的機器人指令。  
- 提供可插拔的模組（MCP、Robot-Console、WebUI），方便開發、測試與部署。  
- 支援合約驅動的請求/回應格式（JSON schema），強化驗證與互通性。  
- 內建測試與監控範例，協助維持系統可靠性。
- **Server-Edge-Runner 架構**：支援伺服器、邊緣設備與執行層分離部署。

## 架構概覽

本專案基於 Flask Microblog 模式開發，將演進為 **Server-Edge-Runner** 三層架構：

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Server      │────▶│      Edge       │────▶│     Runner      │
│  (MCP/WebUI)    │     │ (robot_service) │     │ (Robot-Console) │
│  集中管理/API   │     │ 本地處理/佇列   │     │ 機器人執行     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Server Layer（伺服器層）
- **MCP/** - Model Context Protocol API（指令中介層）
- **WebUI/** - Web 管理介面（基於 Flask Microblog）
- 負責：用戶認證、API Gateway、數據持久化

### Edge Layer（邊緣層）
- **electron-app/** - Electron 桌面應用程序（Heavy 版本）
- **qtwebview-app/** - PyQt 桌面應用程序（Tiny 版本，Phase 3.2）
- **src/robot_service/** - 模組化機器人服務（背景服務）
- 負責：本地佇列、離線支援、低延遲處理

### Runner Layer（執行層）
- **Robot-Console/** - 機器人執行層與動作執行器
- 負責：直接控制機器人、感測器整合、安全機制

### 共用模組
- **src/common/** - Edge 和 Server 共用的工具（日誌、時間處理、配置）
- **tests/** - 統一測試集合
- **config/** - 配置管理

## 主要元件概覽

- **src/common/** - 共用工具模組（日誌格式器、時間工具、環境配置）
- **src/robot_service/** - Edge 環境：模組化機器人服務
  - 本地佇列系統（記憶體內，可擴展至 Redis/Kafka）
  - Electron 整合模式與獨立 CLI 模式
  - 清晰的 API 界限與可測試架構
- **electron-app/** - Edge 環境：Electron 應用程序（Heavy 版本，主程序、預載入腳本、渲染器）
- **qtwebview-app/** - Edge 環境：PyQt 應用程序（Tiny 版本，輕量化桌面應用）
- **MCP/** - Server 環境：管理核心後端服務（API、身分驗證、指令處理、上下文管理）
- **Robot-Console/** - 機器人執行層與相關工具（action executor、decoder、pubsub）
- **WebUI/** - Server 環境：Web 使用者介面（基於 Microblog 架構）
- **tests/** - 專案的自動化測試集合
- **config/** - 配置文件目錄
- **docs/** - 文檔目錄（含 Phase 1 文檔、規劃文檔）

## 主要功能（摘要）

- 指令接收與路由（支援多種輸入來源）。
- 驗證與合約（JSON schema）檢查。  
- 身分驗證與權限管理（模組化 auth）。
- 執行器抽象與模擬（便於開發與測試）。
- 日誌、監控與事件記錄。

## ⚠️ 重要變更：進階指令職責轉移

**從 2025-11-12 開始，進階指令的解碼已從 Robot-Console 轉移到 WebUI 處理。**

- **Robot-Console** 現在只接收預先解碼的基礎動作列表
- **WebUI** 負責進階指令的展開和使用者互動
- 向後相容：仍支援舊格式（可選啟用）

詳細說明請參閱：
- [進階指令職責變更說明](docs/phase2/ADVANCED_COMMAND_RESPONSIBILITY_CHANGE.md)
- [遷移指南](Robot-Console/MIGRATION_GUIDE.md)

## 🎯 選擇合適的版本

本專案提供兩個版本的桌面應用程式：

### Heavy (Electron) 版本
- **適合**：開發者、進階使用者、需要豐富 UI 互動
- **特點**：React 前端、完整開發工具、~150-300MB
- **安裝包**：`npm start` 或下載預編譯版本

### Tiny (PyQt) 版本
- **適合**：生產環境、資源受限設備、快速部署
- **特點**：輕量化、快速啟動、~40-60MB
- **啟動**：`python qtwebview-app/main.py`

**選擇指引**：[版本對比](docs/user_guide/TINY_VS_HEAVY.md) | [Tiny 安裝指引](docs/user_guide/TINY_INSTALL_GUIDE.md)

---

## 快速開始

> **💡 一般使用者請參考** → [用戶快速入門指南](docs/user_guide/QUICK_START.md)  
> 本節內容針對開發者與貢獻者

### 開發環境設定

```bash
# 1. 安裝依賴
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r MCP/requirements.txt

# 2. 一鍵啟動所有服務（推薦）
python3 start_all_services.py
```

這會自動啟動：
- **Flask API** (port 5000) - Edge 本地服務
- **MCP Service** (port 8000) - 指令中介層  
- **WebUI** (port 8080) - Web 管理介面

### 其他啟動方式

| 方式 | 指令 | 說明 |
|------|------|------|
| **Electron 開發** | `npm start` | 自動啟動 Python 服務 + GUI |
| **Tiny 開發** | `python qtwebview-app/main.py` | 輕量桌面應用 |
| **CLI 模式** | `python3 run_service_cli.py` | 無頭部署測試 |
| **手動啟動** | 見 [整合指南](docs/INTEGRATION_GUIDE.md) | 個別服務調試 |

### 執行測試

```bash
# 完整測試套件
python3 -m pytest tests/ -v

# 特定測試
python3 -m pytest tests/test_queue_system.py -v
```

📖 **詳細使用說明**：[用戶指南索引](docs/user_guide/USER_GUIDE_INDEX.md)

## 🔗 WebUI/MCP/Robot-Console 整合

本專案實現了三大模組的完整整合：

### 資料流向

```
WebUI（使用者介面）
    ↓ HTTP REST API
MCP（指令中介層）
    ↓ 本地佇列 / MQTT
Robot-Console（執行層）
    ↓
機器人硬體
```

### 整合方式

1. **WebUI → MCP**：透過 HTTP REST API 呼叫（如 `/api/command`）
2. **MCP → Robot-Console**：
   - 方式 1：本地佇列（推薦，低延遲）
   - 方式 2：MQTT（分散式環境）
   - 方式 3：直接呼叫（同進程）

### 關鍵文件

- 📘 [完整整合指南](docs/INTEGRATION_GUIDE.md) - 詳細資料流向、整合點、配置說明
- 🏗️ [系統架構](docs/architecture.md) - Server-Edge-Runner 三層架構
- 📋 [權威規格](docs/proposal.md) - 資料契約、API 端點定義

### 快速驗證整合

```bash
# 1. 啟動所有服務
python3 start_all_services.py

# 2. 執行端到端測試
python3 -m pytest tests/test_e2e_integration.py -v

# 3. 存取 WebUI（瀏覽器）
open http://localhost:8080
```

## 專案約定與延伸

- JSON schema 檔案放置於 `docs/contract/`，用於請求/回應與錯誤合約驗證。  
- 日誌檔與測試範例位於 `logs/` 與 `tests/` 資料夾。  
- 以模組化設計為主，便於替換不同的執行後端或外部整合。

## 貢獻

歡迎開發者提交 issue 與 PR。請遵守現有測試與程式碼風格，並在新增功能時補上對應的測試。

## 可觀測性（Observability）

本專案已整合完整的可觀測性功能，包括：

- **Prometheus Metrics** - 所有服務都提供 `/metrics` 端點，可監控 API 調用計數、錯誤率、佇列深度、機器人狀態等即時指標
- **結構化 JSON 日誌** - 統一使用 JSON 格式記錄日誌，包含 timestamp、level、event、correlation ID 和 trace ID
- **健康檢查** - Electron 主程序定期監控 Python 服務健康狀態並記錄狀態轉換

### Metrics 端點

- Flask Service: `http://127.0.0.1:5000/metrics`
- MCP Service: `http://localhost:8000/metrics`

### 快速開始

1. 啟動服務後訪問 metrics 端點：
```bash
curl http://127.0.0.1:5000/metrics
```

2. 查看結構化日誌（所有服務輸出 JSON 格式）：
```bash
# Electron 日誌會顯示在主控台
npm start

# Python 服務日誌也是 JSON 格式
python3 flask_service.py
```

詳細說明請參閱 [可觀測性指南](docs/features/observability-guide.md)。

## Robot Service 模組化架構

專案已將 Python 背景服務重構為 `src/robot_service/` 模組，提供：

- ✅ **清晰的 API 界限** - 模組化設計，職責分離
- ✅ **本地佇列系統** - 記憶體內實作，可擴展至 Redis/Kafka
- ✅ **雙模式運行** - Electron 整合與獨立 CLI 模式
- ✅ **優先權佇列** - 4 個等級的訊息優先權（URGENT/HIGH/NORMAL/LOW）
- ✅ **非同步處理** - 多工作協程並行處理
- ✅ **可測試性** - 完整的單元測試與整合測試

詳細文件：
- [Robot Service README](src/robot_service/README.md) - 模組使用說明
- [Queue Architecture](docs/features/queue-architecture.md) - 佇列架構與設計

## 參考與文件

### 核心文檔
- [文件索引](docs/README.md) - 完整的文件目錄與導航
- [架構說明](docs/architecture.md) - 完整的專案架構與目錄結構說明（Phase 2）
- [Phase 2 遷移指南](docs/phase2/MIGRATION_GUIDE_PHASE2.md) - 從 Phase 1 遷移到 Phase 2 的詳細指南
- [README](README.md) - 本文件，快速啟動與概覽

### 使用者指南
- **[用戶指南索引](docs/user_guide/USER_GUIDE_INDEX.md)** - 完整的用戶文件導航
- **[快速入門指南](docs/user_guide/QUICK_START.md)** - 5 分鐘快速上手
- **[完整安裝指南](docs/user_guide/INSTALLATION_GUIDE.md)** - 所有版本安裝說明 🆕
- **[常見問題 FAQ](docs/user_guide/FAQ.md)** - 常見問題與解答
- **[疑難排解指南](docs/user_guide/TROUBLESHOOTING.md)** - 問題診斷與解決
- **[功能完整參考](docs/user_guide/FEATURES_REFERENCE.md)** - 所有功能詳細說明
- **[WebUI 使用指南](docs/user_guide/WEBUI_USER_GUIDE.md)** - Web 介面詳細說明
- **[TUI 使用指南](docs/user_guide/TUI_USER_GUIDE.md)** - 終端介面操作與功能說明

### API 與安全性
- **[OpenAPI 規範](openapi.yaml)** - 完整的 API 合約定義（OpenAPI 3.1）
- **[API 與安全性使用指南](docs/security/api-security-guide.md)** - API 版本控制、認證流程、秘密管理使用說明
- **[威脅模型](docs/security/threat-model.md)** - STRIDE 威脅分析與緩解措施
- **[安全檢查清單](docs/security/security-checklist.md)** - 開發、測試、部署、維護階段安全檢查項
- **[API 安全實作摘要](docs/security/API_SECURITY_IMPLEMENTATION_SUMMARY.md)** - 完整實作細節與驗收標準

### 專業領域文檔
- [可觀測性指南](docs/features/observability-guide.md) - Prometheus metrics 和結構化日誌的完整文件
- [Queue Architecture](docs/features/queue-architecture.md) - 佇列系統架構與訊息合約
- [Robot Service](src/robot_service/README.md) - 模組化服務說明
- [MCP Module](MCP/README.md) - MCP 服務模組說明
- [Robot-Console](Robot-Console/README.md) - 機器人執行層說明

### 配置與測試
- [配置策略](config/README.md) - 配置管理說明
- [測試指南](docs/features/webui-testing-guide.md) - 測試編寫與執行指南

### 開發指南
- [Python Lint 指南](docs/development/PYTHON_LINT_GUIDE.md) - 程式碼風格與 lint 修復策略

## API 版本控制與認證

本專案現在支援標準化的 API 合約和完整的安全功能：

### 快速開始

```bash
# 1. 設定環境變數（開發環境）
export MCP_JWT_SECRET="dev-secret-$(date +%s)"
export APP_TOKEN="dev-token-$(date +%s)"
export MCP_JWT_EXPIRATION_HOURS=24

# 2. 啟動 MCP 服務
cd MCP
python3 start.py

# 3. 註冊使用者
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user1","username":"myuser","password":"securepass123","role":"operator"}'

# 4. 登入獲取 token
TOKEN=$(curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"myuser","password":"securepass123"}' | jq -r '.token')

# 5. 使用 token 存取 API
curl http://localhost:8000/v1/robots \
  -H "Authorization: Bearer $TOKEN"
```

### 主要功能

- **OpenAPI 3.1 規範**: 完整的 API 文件化，包含 12 個公開端點
- **版本控制**: `/v1` 路徑前綴，向後相容 `/api` 路徑
- **JWT 認證**: 所有端點（除了 `/health` 和 `/metrics`）都需要認證
- **Token 輪替**: `/v1/auth/rotate` 端點支援無縫 token 更新
- **角色權限**: 三種角色（admin、operator、viewer）與基於角色的存取控制
- **秘密管理**: 可插拔的秘密儲存後端（環境變數、檔案、keychain、DPAPI）
- **審計日誌**: 所有認證和授權事件都記錄到審計日誌

詳細說明請參閱 [API 與安全性使用指南](docs/security/api-security-guide.md)。
