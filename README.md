# Robot Command Console

本專案（robot-command-console）是一個用於機器人指令管理、路由與執行的整合式控制台與服務平台。目標是提供一套模組化、可測試且可部署的系統，用來接收、驗證、路由並執行來自各種介面（WebUI、API、排程或其他整合服務）的指令，同時保留豐富的日誌、驗證與合約（schema）檢查。

> **📢 Phase 2 重大更新** - 目錄結構已重新組織以提高模組化和清晰度。詳見 [架構說明](docs/architecture.md) 和 [遷移指南](docs/MIGRATION_GUIDE_PHASE2.md)。

## 核心目的

- 集中管理來自多來源的機器人指令。  
- 提供可插拔的模組（MCP、Robot-Console、WebUI），方便開發、測試與部署。  
- 支援合約驅動的請求/回應格式（JSON schema），強化驗證與互通性。  
- 內建測試與監控範例，協助維持系統可靠性。

## 主要元件概覽

- **src/robot_service/** - 模組化機器人服務（新增）
  - 本地佇列系統（記憶體內，可擴展至 Redis/Kafka）
  - Electron 整合模式與獨立 CLI 模式
  - 清晰的 API 界限與可測試架構
- **electron-app/** - Electron 應用程序（主程序、預載入腳本、渲染器）
- **MCP/** - 管理核心後端服務（API、身分驗證、指令處理、上下文管理、日誌監控）
- **Robot-Console/** - 機器人執行層與相關工具（action executor、decoder、pubsub）
- **WebUI/** - 提供使用者介面與微服務整合的範例實作（microblog 與 Web UI routes）
- **tests/** - 專案的自動化測試集合，包含單元測試與整合測試範例
- **config/** - 配置文件目錄（集中管理配置策略）

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
- [進階指令職責變更說明](docs/ADVANCED_COMMAND_RESPONSIBILITY_CHANGE.md)
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

詳細說明請參閱 [可觀測性指南](docs/observability.md)。

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
- [Queue Architecture](docs/queue-architecture.md) - 佇列架構與設計

## 參考與文件

### 核心文檔
- [架構說明](docs/architecture.md) - 完整的專案架構與目錄結構說明（Phase 2）
- [Phase 2 遷移指南](docs/MIGRATION_GUIDE_PHASE2.md) - 從 Phase 1 遷移到 Phase 2 的詳細指南
- [README](README.md) - 本文件，快速啟動與概覽

### 專業領域文檔
- [可觀測性指南](docs/observability.md) - Prometheus metrics 和結構化日誌的完整文件
- [Queue Architecture](docs/queue-architecture.md) - 佇列系統架構與訊息合約
- [Robot Service](src/robot_service/README.md) - 模組化服務說明
- [MCP Module](MCP/README.md) - MCP 服務模組說明
- [Robot-Console](Robot-Console/README.md) - 機器人執行層說明

### 配置與測試
- [配置策略](config/README.md) - 配置管理說明
- [測試指南](docs/testing-guide.md) - 測試編寫與執行指南

## CI: 自動將 main 同步到各分支（新增）

本倉庫新增了一個 GitHub Actions 工作流程 `./github/workflows/sync-main-to-branches.yml`，會在 `main` 有 push（例如合併 PR）時嘗試把 `origin/main` merge 回其他遠端分支，並將合併後的結果 push 回對應分支。

注意事項：

- 使用預設的 `GITHUB_TOKEN` 應可執行一般的 push，但若目標分支設定為受保護（protected）且需要額外審查或強制檢查，push 可能會被拒絕。若需要跨受保護分支自動推送，請改用有適當權限的 Personal Access Token（PAT），並將其存為 repository secret，再在 workflow 中使用該 PAT（取代預設憑證）。
- 若某分支與 `main` 的合併發生衝突，該分支會被跳過（workflow 會記錄失敗的分支）。目前實作不會自動解決衝突或建立 PR；若希望自動建立包含衝突的 PR 以便手動處理，可進一步擴充 workflow。
- 請注意避免把不應自動同步的分支（例如臨時測試分支或維護分支）放入同步列表；目前 workflow 會自動排除 `main`、`gh-pages` 與 `HEAD`，你可以根據需要再修改檔案以排除更多分支。

如果需要，我可以把 README 中這段改為更詳細的操作範例（包含如何用 PAT 推送與示範保護分支設定）。
