# WebUI 目錄說明# WebUI 目錄說明



本資料夾為「機器人指令中介層（MCP 伺服器）」的 Web 介面實作，依據專案提案（prosposal.md）設計，具備以下特點：



## 目標## 目標

WebUI 提供人類操作員與 AI 客戶端的互動入口，支援指令發送、狀態監控、日誌查詢與即時介入，確保人機協作安全與可追溯性。



## 模組化架構## 模組化架構

本 WebUI 採用模組化設計，主要模組包括：

- 指令路由與處理（routes.py）- 网页路由與處理（routes.py）

- 資料模型（models.py）- 数据库模型（models.py）

- 錯誤處理（errors.py）- 錯誤處理（errors.py）

- 郵件通知（email.py）- 郵件通知（email.py）

- 表單驗證（forms.py）- 表單驗證（forms.py）

- 日誌與監控（logging_monitor.py）- 設定管理（config.py）



所有設定統一由專案根目錄 config.py 提供。各模組可獨立維護、擴充，便於未來整合新功能或新型機器人。



## 目錄結構簡介## 目标功能

- app/：WebUI 主程式與模組- 指令驗證、排隊、分派與回應

- templates/：Jinja2 前端模板- 機器人狀態與指令結果監控

- translations/：多語系翻譯檔- 完整日誌查詢與即時監督介面

- migrations/：資料庫遷移管理- 認證授權與角色權限控管

- 日誌與監控（可擴充 logging_monitor 模組）

---

如需詳細設計理念與開發步驟，請參閱專案根目錄下的 prosposal.md。## 目錄結構簡介

# WebUI 模組說明

本資料夾包含機器人指令中介層（MCP，Middleware for Command Processing）專案的 Web 使用者介面實作。此 WebUI 提供給人類操作員（或管理者）一個直觀的介面，用於管理與監控下達給機器人或 AI 客戶端的指令、檢視狀態與日誌，以及在必要時進行即時干預。

README 目的：本檔案說明 WebUI 的目的、主要功能、目錄結構、快速啟動指引與開發注意事項，方便開發者與維運人員快速上手。

## 核心目標

- 提供安全且可追溯的指令發送介面。
- 顯示機器人與任務的即時狀態與歷史紀錄（事件日誌）。
- 支援進階指令建立、編輯與審核流程（包含角色與權限控管）。
- 整合通知（例如電子郵件）與監控模組，用以提示例外或需要人工介入的情況。

## 主要功能一覽

- 使用者認證與權限管理（登入、角色權限）。
- 指令建立、送出與排程（含進階／複合指令）。
- 指令路由與回應檢視（顯示指令狀態：待處理、進行中、完成、失敗）。
- 日誌查詢與過濾（按時間、指令 ID、使用者或狀態篩選）。
- 即時監控頁面（顯示機器人狀態、活動指令與統計數據）。
- 管理與設定頁面（系統設定、通知設定、外部服務整合）。

## 目錄結構

請參考下列重要路徑（相對於 `WebUI/` 根目錄）：

- `app/`：Web 應用程式主要模組，包含路由、表單、錯誤處理、郵件、日誌與資料模型等。
	- `app/routes.py`：HTTP 路由與視圖處理（網頁端點）。
	- `app/models.py`：資料庫模型定義（SQLAlchemy）。
	- `app/forms.py`：WTForms 表單定義與驗證。
	- `app/errors.py`：自訂錯誤處理邏輯。
	- `app/email.py`：電子郵件通知功能。
	- `app/logging_monitor.py`：日誌擷取與監控相關功能。

- `templates/`：Jinja2 模板，用於網頁前端呈現（例如 `home.html.j2`, `advanced_commands.html.j2` 等）。
- `static/`：靜態資源（CSS、JavaScript、images）。
- `migrations/`：資料庫遷移腳本（alembic）。
- `translations/`：國際化翻譯檔（如果啟用多語系）。
- `logs/`：本地測試或開發環境的日誌檔案（不建議在生產中儲存在 repo）。

## 快速啟動（開發環境）

以下為一組建議的步驟，假設你已在專案根目錄並已安裝 Python 3.8+：

1. 建議建立虛擬環境並安裝需求套件：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r WebUI/requirements.txt
```

2. 設定必要的環境變數（示範）：

```bash
export FLASK_APP=WebUI/microblog.py
export FLASK_ENV=development
# 若使用資料庫或郵件服務，設定相應的連線字串與憑證
```

3. 執行遷移（若需要）：

```bash
alembic -c WebUI/migrations/alembic.ini upgrade head
```

4. 啟動開發伺服器：

```bash
flask run --host=0.0.0.0 --port=5000
```

開啟瀏覽器並前往 http://localhost:5000 檢視 WebUI。

## 開發者注意事項

- 設定值與機密（例如資料庫連線字串、郵件金鑰）應放在專案根目錄的 `config.py` 或透過環境變數注入，避免直接放在 repo 中。
- 前端模板使用 Jinja2，若修改樣板請留意 XSS 與輸出逃逸機制。
- 若新增資料表或模型，請同時建立 Alembic migration 檔並測試升級流程。
- 日誌檔 `WebUI/logs/` 僅供開發測試，生產環境應設計集中式日誌（例如 ELK、CloudWatch）。

## 測試

本專案內含單元測試（位於 repo 的 `Test/` 與 `Web/` 資料夾）。建議在修改核心邏輯後執行相關測試套件。

例如使用 pytest：

```bash
pytest -q
```

## 後續改進建議

- 新增 API 文件（OpenAPI/Swagger）以便外部系統整合。
- 提供 Dockerfile 與 docker-compose 範例，快速建立相依服務（資料庫、郵件模擬器）。
- 加入前端自動化測試（Selenium、Playwright）與 CI 流程。

