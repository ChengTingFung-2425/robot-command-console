# WebUI 目錄說明# WebUI 目錄說明



本資料夾為「機器人指令中介層（MCP 伺服器）」的 Web 介面實作，依據專案提案（proposal.md）設計，具備以下特點：



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

如需詳細設計理念與開發步驟，請參閱專案根目錄下的 proposal.md。## 目錄結構簡介

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

# WebUI 模組說明

子系統摘要：WebUI 提供給人類操作員與系統管理者的網頁介面，用於建立/管理指令、監控機器人狀態、檢視日誌與進行即時干預，並與 MCP 整合以下發指令與接收回報。

## 核心目標

- 提供安全且可追溯的指令發送介面
- 顯示機器人與任務之即時狀態與歷史事件
- 支援進階指令建立、審核與權限控管
- 整合通知與監控以提示異常或需要人工介入之情況

## 主要功能

- 使用者認證與角色權限管理
- 指令建立、送出、排程與複合指令支援
- 指令路由與回應檢視（待處理／進行中／完成／失敗）
- 日誌查詢與過濾（時間、指令 ID、使用者、狀態）
- 即時監控頁面（機器人狀態、活動指令、統計）

## 目錄結構（摘要）

- `app/`：Web 應用主要模組（路由、models、forms、errors、email、logging_monitor）
- `templates/`：Jinja2 前端模板
- `static/`：CSS / JS / images
- `migrations/`：alembic 資料庫遷移
- `translations/`：多語系翻譯檔
- `logs/`：開發/測試日誌（生產請使用集中式日誌）

重要檔案（相對於 `WebUI/`）：

- `microblog.py` — WebUI 啟動程式範例
- `requirements.txt` — WebUI 依賴
- `app/routes.py`, `app/models.py`, `app/forms.py`, `app/errors.py`, `app/email.py`

## 快速啟動（開發）

1. 建立虛擬環境並安裝依賴：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r WebUI/requirements.txt
```

2. 設定環境變數（示範）：

```bash
export FLASK_APP=WebUI/microblog.py
export FLASK_ENV=development
# 若使用資料庫或郵件服務，設定相應連線字串
```

3. 執行資料庫遷移（如需要）：

```bash
alembic -c WebUI/migrations/alembic.ini upgrade head
```

4. 啟動開發伺服器：

```bash
flask run --host=0.0.0.0 --port=5000
```

打開 http://localhost:5000 檢視 WebUI。

## 開發者注意事項

- 敏感設定（DB 連線字串、API 金鑰）請使用環境變數或 `config.py`，避免放在 repo
- 模板使用 Jinja2，請留意 XSS 與輸出逃逸
- 新增資料表時務必建立 Alembic migration 並測試升級流程

## 測試

專案包含多項測試（位於 `Test/` 及 `Web/`），建議在變更後執行：

```bash
pytest -q
```

## 改進建議

- 新增 OpenAPI / Swagger 文件以利系統整合
- 提供 Dockerfile 與 docker-compose 範例以快速建立相依服務
- 加入前端自動化測試與 CI

---

更多細節請參閱專案根目錄之 `proposal.md` 與 `WebUI/Module.md`。

