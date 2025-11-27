# Robot Command Console

本專案（robot-command-console）是一個用於機器人指令管理、路由與執行的整合式控制台與服務平台。目標是提供一套模組化、可測試且可部署的系統，用來接收、驗證、路由並執行來自各種介面（WebUI、API、排程或其他整合服務）的指令，同時保留豐富的日誌、驗證與合約（schema）檢查。

> **📢 Phase 2 重大更新** - 目錄結構已重新組織以提高模組化和清晰度。詳見 [架構說明](docs/architecture.md) 和 [遷移指南](docs/phase2/MIGRATION_GUIDE_PHASE2.md)。

> **🚀 架構演進方向** - 本專案將演進為 **Server-Edge-Runner** 三層架構，支援分散式部署與邊緣運算。

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
- **electron-app/** - Electron 桌面應用程序
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
- **electron-app/** - Edge 環境：Electron 應用程序（主程序、預載入腳本、渲染器）
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

## 快速啟動（開發者）

### 1. 安裝依賴

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r MCP/requirements.txt
```

### 2. 啟動服務

#### Electron 整合模式（預設）

```bash
# 由 Electron 自動啟動 Python 服務
npm start
```

#### 獨立 CLI 模式

```bash
# 執行 Robot Service（不依賴 Electron）
python3 run_service_cli.py --queue-size 1000 --workers 5
```

#### 手動啟動 Flask 服務

```bash
# 設定環境變數並啟動
APP_TOKEN=your-token-here PORT=5000 python3 flask_service.py
```

### 3. 啟動其他元件

```bash
# 啟動 MCP 服務
cd MCP
python3 start.py

# 啟動 WebUI
cd WebUI
python microblog.py
```

### 4. 執行測試

```bash
# 在專案根目錄執行所有測試
python3 -m pytest tests/ -v

# 執行特定測試
python3 -m pytest tests/test_queue_system.py -v
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
- [架構說明](docs/architecture.md) - 完整的專案架構與目錄結構說明（Phase 2）
- [Phase 2 遷移指南](docs/phase2/MIGRATION_GUIDE_PHASE2.md) - 從 Phase 1 遷移到 Phase 2 的詳細指南
- [README](README.md) - 本文件，快速啟動與概覽

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
