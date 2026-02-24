# 函式庫參考文件（Library Reference）

> **用途**：說明本專案 `requirements.txt` 及 `package.json` 中每個函式庫的引入原因與使用目標。  
> 供開發者快速了解各套件的職責，避免重複引入功能相似的套件。
>
> **最後更新**：2026-02-24  
> **維護方式**：新增/移除套件時同步更新本文件

---

## 目錄

1. [Python 後端函式庫](#python-後端函式庫)
   - [Web 框架](#web-框架)
   - [Flask 擴充套件](#flask-擴充套件)
   - [資料庫](#資料庫)
   - [認證與安全](#認證與安全)
   - [資料驗證](#資料驗證)
   - [非同步與 HTTP](#非同步與-http)
   - [訊息佇列](#訊息佇列)
   - [可觀測性與監控](#可觀測性與監控)
   - [終端介面（TUI）](#終端介面tui)
   - [系統工具](#系統工具)
   - [開發與測試工具](#開發與測試工具)
2. [JavaScript / Electron 函式庫](#javascript--electron-函式庫)

---

## Python 後端函式庫

### Web 框架

| 套件 | 版本 | 用途 | 使用位置 |
|------|------|------|----------|
| **Flask** | 3.1.3 | 主要 Web 框架，提供路由、Blueprint、請求/回應處理。WebUI 與 Cloud API 均以 Flask 為基礎。 | `Edge/WebUI/`, `Cloud/api/` |
| **FastAPI** | ≥0.104.0 | MCP 邊緣層 API 使用的 ASGI Web 框架，提供型別驅動路由、依賴注入與自動產生 OpenAPI 文件。 | `Edge/MCP/api.py`, `Edge/MCP/` |
| **Uvicorn** | ≥0.24.0 | ASGI server，用於啟動 FastAPI MCP 服務（開發與部署）。支援 WebSocket 與 HTTP/2。 | `Edge/MCP/`（服務啟動命令與部署腳本） |
| **Pydantic** | ≥2.5.0 | MCP API 的資料模型與驗證層，配合 FastAPI 定義請求/回應 Schema，提供嚴格型別驗證。 | `Edge/MCP/` |
| **Werkzeug** | ≥3.0.1 | Flask 底層 WSGI 工具函式庫。額外使用 `secure_filename`（檔名消毒）與 `safe_join`（防路徑穿越）。**路徑安全的首選工具。** | `Cloud/api/storage.py`, `Edge/qtwebview-app/routes_firmware_tiny.py` |

### Flask 擴充套件

| 套件 | 版本 | 用途 | 使用位置 |
|------|------|------|----------|
| **Flask-Babel** | 2.0.0 | 國際化（i18n）與本地化（l10n）支援，提供翻譯字串與時區處理。 | `Edge/WebUI/` |
| **Flask-Bootstrap** | 3.3.7.1 | 整合 Bootstrap CSS 框架至 Flask 模板，提供 `render_form`、`render_field` 等便利巨集。 | `Edge/WebUI/templates/` |
| **Flask-Login** | 0.6.2 | 管理使用者登入狀態（session）、`current_user`、`@login_required` 裝飾器、記住我功能。 | `Edge/WebUI/app/__init__.py`, `Edge/WebUI/app/routes.py` |
| **Flask-Mail** | 0.9.1 | 透過 SMTP 發送電子郵件，用於密碼重設通知、系統告警信。 | `Edge/WebUI/app/email.py` |
| **Flask-Migrate** | 4.0.0 | 以 Alembic 為基礎的資料庫 Schema 遷移工具，管理 `migrations/` 目錄下的版本記錄。 | `Edge/WebUI/migrations/` |
| **Flask-Moment** | 1.0.5 | 在 Jinja2 模板中格式化時間戳記（基於 moment.js），支援相對時間顯示（如「3分鐘前」）。 | `Edge/WebUI/templates/` |
| **Flask-SQLAlchemy** | 3.0.2 | Flask 與 SQLAlchemy ORM 的整合橋接，提供 `db` 物件、`db.Model` 基礎類別。 | `Edge/WebUI/app/models.py`, `Edge/WebUI/app/__init__.py` |
| **Flask-WTF** | 1.0.1 | Flask 與 WTForms 的整合，提供 CSRF 保護、表單驗證。 | `Edge/WebUI/app/forms.py` |

### 資料庫

| 套件 | 版本 | 用途 | 使用位置 |
|------|------|------|----------|
| **SQLAlchemy** | 2.0.x | Python 的 ORM 與資料庫工具套件核心。Cloud 模組使用獨立的 SQLAlchemy Session（不依賴 Flask-SQLAlchemy）管理共享指令的資料庫操作。 | `Cloud/shared_commands/models.py`, `Cloud/shared_commands/database.py` |
| **psycopg2** | 2.9.5 | PostgreSQL 的 Python 驅動程式，作為 SQLAlchemy 後端連接生產資料庫。開發環境可改用 SQLite。 | 透過 SQLAlchemy 連線字串使用 |

### 認證與安全

| 套件 | 版本 | 用途 | 使用位置 |
|------|------|------|----------|
| **PyJWT** | 2.6.0 | JSON Web Token 的產生與驗證。用於 Access Token（15分鐘）、Refresh Token（7天）、API Key 等全部 JWT 流程。 | `Cloud/api/auth.py`, `Edge/WebUI/app/auth_api.py`, `Edge/MCP/auth_manager.py` |
| **passlib[bcrypt]** | ≥1.7.4 | 全面的密碼雜湊框架，支援 30+ 演算法。本專案以 bcrypt 後端雜湊密碼。`CloudAuthService.hash_password()` 使用此套件。 | `Cloud/api/auth.py` |
| **bcrypt** | ≥4.0.0,<4.1.0 | bcrypt 演算法的底層 C 擴充，passlib 的執行時期後端。同時也供 `werkzeug.security` 間接使用。 | 被 passlib 使用 |
| **cryptography** | ≥40.0.0 | 提供低階密碼學原語（AES-256-GCM、RSA、ECDSA 等）。用於 Edge Token 加密儲存（AES-256-GCM）。 | `Edge/robot_service/edge_token_cache.py`, `src/common/token_encryption.py` |
| **bleach** | 6.x | 白名單式 HTML 清理工具，防止 XSS 攻擊。用於清理用戶提交的指令說明、留言等富文字欄位。 | `Cloud/shared_commands/service.py` |

### 資料驗證

| 套件 | 版本 | 用途 | 使用位置 |
|------|------|------|----------|
| **jsonschema** | 4.21.1 | JSON Schema（Draft 4/7）驗證。用於合約測試（contract tests）驗證 API 請求/回應格式，以及 MCP 指令的 Schema 驗證。 | `Edge/MCP/schema_validator.py`, `tests/` |
| **email-validator** | ≥2.0.0 | 電子郵件地址格式驗證，供 WTForms 的 `Email()` 驗證器使用。 | `Edge/WebUI/app/forms.py` |
| **toml** | 0.10.2 | TOML 格式解析，讀取 `config.toml` 專案配置檔。 | `config.py` |
| **pyyaml** | ≥6.0 | YAML 格式解析，用於讀取 `openapi.yaml` 規格檔進行 OpenAPI 驗證。 | `tests/`, `openapi.yaml` 相關工具 |
| **openapi-spec-validator** | ≥0.7.1 | 驗證 `openapi.yaml` 是否符合 OpenAPI 3.x 規格，作為 CI 品質關卡。 | `tests/`, CI pipeline |

### 非同步與 HTTP

| 套件 | 版本 | 用途 | 使用位置 |
|------|------|------|----------|
| **aiohttp** | ≥3.9.0 | 非同步 HTTP 客戶端/伺服器框架。用於 LLM 提供商的健康檢查、非同步 API 呼叫（Ollama、LM Studio）。 | `Edge/MCP/providers/ollama_provider.py`, `Edge/MCP/providers/lmstudio_provider.py` |
| **requests** | ≥2.31.0 | 同步 HTTP 客戶端，用於 Edge 裝置綁定 API 呼叫、Cloud 同步客戶端等需要簡單同步請求的場景。 | `Edge/cloud_sync/sync_client.py`, `scripts/demo_device_binding.py` |

### 訊息佇列

| 套件 | 版本 | 用途 | 使用位置 |
|------|------|------|----------|
| **aio-pika** | ≥9.0.0 | asyncio 友善的 RabbitMQ 客戶端（基於 aiormq）。實作 `RabbitMQQueue`，支援 Topic Exchange、Priority Queue、DLX/DLQ、Publisher Confirms。 | `Edge/robot_service/queue/rabbitmq_queue.py` |
| **aioboto3** | ≥12.0.0 | boto3 的非同步包裝器，提供 asyncio 相容的 AWS SDK。用於 `SQSQueue` 實作，支援 Standard/FIFO 佇列、長輪詢、IAM Role 認證。 | `Edge/robot_service/queue/sqs_queue.py` |

### 可觀測性與監控

| 套件 | 版本 | 用途 | 使用位置 |
|------|------|------|----------|
| **prometheus_client** | ≥0.19.0 | Prometheus 指標客戶端，暴露 `/metrics` 端點供 Prometheus 抓取。記錄指令執行次數、延遲、錯誤率等 KPI。 | `Edge/MCP/`, `src/robot_service/` |
| **python-json-logger** | ≥2.0.7 | 將 Python 標準 `logging` 輸出格式化為結構化 JSON，方便 ELK Stack 收集與查詢。 | `src/common/logging_utils.py` |

### 終端介面（TUI）

| 套件 | 版本 | 用途 | 使用位置 |
|------|------|------|----------|
| **textual** | ≥0.47.0 | 現代 TUI（終端使用者介面）框架，基於 Rich。提供 Widget、Layout、事件系統。用於 `run_tui.py` 的全功能終端控制台。 | `run_tui.py`, `Edge/robot_service/tui/` |

### 系統工具

| 套件 | 版本 | 用途 | 使用位置 |
|------|------|------|----------|
| **psutil** | ≥5.9.0 | 跨平台程序與系統監控（CPU、記憶體、磁碟、網路、程序列表）。用於服務健康檢查儀表板顯示系統資源狀態。 | `Edge/robot_service/electron/edge_ui.py`, `unified_launcher_cli.py` |
| **Babel** | 2.11.0 | 國際化工具（Flask-Babel 的底層依賴），提供時區資料庫、語言代碼、複數形式處理。 | 透過 Flask-Babel 使用 |

### 開發與測試工具

| 套件 | 版本 | 用途 | 使用位置 |
|------|------|------|----------|
| **pytest** | ≥7.4.0 | 主要測試框架，提供 fixture、參數化、插件生態。`tests/` 目錄下所有測試均以 pytest 執行。 | `tests/`, `run_tests.py` |
| **pytest-cov** | ≥4.1.0 | pytest 的覆蓋率插件，產生 HTML/XML 覆蓋率報告，作為 CI 品質門檻。 | `run_tests.py`, CI pipeline |
| **pytest-asyncio** | ≥0.21.0 | 讓 pytest 支援 `async def` 測試函式與 async fixture，用於測試 aiohttp、aio-pika 等非同步模組。 | `tests/edge/`, `tests/cloud/` |
| **flake8** | ≥7.0.0 | Python 程式碼風格檢查（PEP 8）+ 靜態分析（pyflakes）。CI 必過關卡，禁止 E/F 級別錯誤。執行：`python3 -m flake8 src/ MCP/ --select=E,F --max-line-length=120` | CI pipeline, `check_lint.py` |
| **bandit** | ≥1.7.5 | Python 安全靜態分析工具，掃描常見安全漏洞（硬編碼密鑰、不安全函式呼叫、SQL injection 等）。 | CI pipeline |
| **djlint** | 1.19.7 | HTML/Jinja2 模板 Linter，檢查模板格式與潛在錯誤。 | `Edge/WebUI/templates/` |

---

## JavaScript / Electron 函式庫

> 定義於 `Edge/electron-app/package.json`

| 套件 | 版本 | 用途 | 使用位置 |
|------|------|------|----------|
| **electron** | ^39.x | 跨平台桌面應用框架（Chromium + Node.js）。主程序（`main.js`）負責視窗管理、啟動 Python 背景服務、產生短期 Token；渲染程序透過 contextBridge 呼叫 API。 | `Edge/electron-app/main.js`, `Edge/electron-app/renderer/` |
| **electron-builder** | ^26.x | Electron 應用的打包與發佈工具，生成 Linux AppImage、Windows NSIS、macOS DMG 安裝包。 | `Edge/electron-app/package.json` build 腳本 |

---

## 選型決策摘要

| 需求 | 選用套件 | 理由 |
|------|----------|------|
| 路徑安全 | `werkzeug.safe_join` | 已有依賴、語意明確、防三類攻擊 |
| JWT 認證 | `PyJWT` | 輕量、標準相容、Flask 生態主流 |
| 密碼雜湊 | `passlib[bcrypt]` + `bcrypt` | 業界標準強度、可調整因子 |
| Token 加密 | `cryptography` (AES-256-GCM) | FIPS 相容、GCM 提供認證加密 |
| XSS 防護 | `bleach` | 白名單式、可設定允許標籤 |
| 非同步 LLM | `aiohttp` | 輕量、asyncio 原生 |
| RabbitMQ | `aio-pika` | asyncio 友善、支援優先佇列 |
| AWS SQS | `aioboto3` | boto3 非同步包裝、IAM 整合 |
| 終端介面 | `textual` | 現代 Widget 架構、無 curses 限制 |

---

## 相關文件

- [proposal.md](../proposal.md) — 系統架構與技術棧定義
- [architecture.md](../architecture.md) — 三層架構說明
- [PROJECT_MEMORY.md](../PROJECT_MEMORY.md) — 經驗教訓與最佳實踐
- [security/TOKEN_SECURITY.md](../security/TOKEN_SECURITY.md) — Token 安全設計
