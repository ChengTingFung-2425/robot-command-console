# Robot Command Console - 架構文件

## 專案概述

Robot Command Console 是一個用於機器人指令管理、路由與執行的整合式控制台與服務平台。本文件說明專案的目錄結構、模組職責與設計原則。

> **狀態**：Phase 3.1 已完成，Phase 3.2 進行中（Tiny 版本核心架構完成，待整合測試）  
> **最後更新**：2025-12-22

## 目錄結構（Phase 3）

```
robot-command-console/
├── src/                       # 源代碼
│   ├── common/               # 共用模組（Edge 和 Server 共用）
│   │   ├── __init__.py
│   │   ├── logging_utils.py  # 統一 JSON 日誌
│   │   ├── datetime_utils.py # 時間處理工具
│   │   ├── config.py         # 環境配置
│   │   ├── service_types.py  # 服務類型定義 (Phase 3.1)
│   │   ├── state_store.py    # 本地狀態存儲 (Phase 3.1)
│   │   ├── event_bus.py      # 事件匯流排 (Phase 3.1)
│   │   ├── shared_state.py   # 服務間狀態共享管理器 (Phase 3.1)
│   │   └── token_manager.py  # Token 管理
│   │
│   └── robot_service/        # Edge 環境：模組化機器人服務
│       ├── __init__.py
│       ├── service_manager.py
│       ├── service_coordinator.py  # 服務協調器 (Phase 3.1)
│       ├── unified_launcher.py     # 統一啟動器 (Phase 3.1)
│       ├── command_processor.py    # 指令處理器
│       ├── cli/              # CLI 模式
│       ├── electron/         # Electron 整合
│       ├── queue/            # 佇列系統
│       └── utils/            # Edge 工具（重導出 common）
│
├── electron-app/              # Edge 環境：Electron 應用程序 (Heavy 版本)
│   ├── main.js               # Electron 主程序
│   ├── preload.js            # 預載入腳本（安全橋接）
│   ├── renderer/             # 渲染器進程（UI）
│   │   ├── index.html
│   │   └── renderer.js
│   └── package.json          # Electron 專用依賴
│
├── qtwebview-app/            # Edge 環境：PyQt 應用程序 (Tiny 版本, Phase 3.2)
│   ├── main.py               # PyQt 主程式入口
│   ├── webview_window.py     # QtWebEngineView 封裝
│   ├── flask_manager.py      # Flask 服務管理器
│   ├── bridge.py             # QWebChannel JS-Python 橋接
│   ├── system_tray.py        # 系統托盤
│   ├── resources/            # 圖示與資源
│   ├── requirements.txt      # PyQt 依賴
│   └── build/                # 打包配置
│
├── MCP/                       # Server 環境：Model Context Protocol 服務
│   ├── api.py                # FastAPI 主應用
│   ├── auth_manager.py       # 認證管理
│   ├── command_handler.py    # 指令處理
│   ├── context_manager.py    # 上下文管理
│   ├── llm_processor.py      # LLM 處理器
│   ├── llm_provider_manager.py  # LLM 提供商管理器
│   ├── plugin_manager.py     # 插件管理器
│   ├── robot_router.py       # 機器人路由
│   ├── schema_validator.py   # Schema 驗證
│   ├── plugins/              # 插件目錄
│   ├── utils/                # Server 工具（重導出 common）
│   └── requirements.txt      # MCP 依賴
│
├── Robot-Console/             # 機器人執行層（可部署於 Edge 或 Server）
│   ├── action_executor.py    # 動作執行器
│   ├── pubsub.py            # 發布/訂閱機制
│   └── tools.py             # 工具函數
│
├── WebUI/                     # Server 環境：Web 使用者介面
│   ├── app/                  # Flask 應用
│   ├── migrations/           # 資料庫遷移
│   └── microblog.py          # WebUI 入口
│
├── tests/                     # 測試集合（統一，365+ 測試）
│   ├── test_*.py
│   └── phase3/               # Phase 3 測試套件
│
├── config/                    # 配置管理
│   └── README.md
│
├── docs/                      # 文檔
│   ├── architecture.md       # 本文件
│   ├── proposal.md           # 權威規格
│   ├── PROJECT_MEMORY.md     # 專案記憶與經驗教訓
│   ├── README.md             # 文件索引
│   ├── phase1/               # Phase 1 文檔
│   ├── phase2/               # Phase 2 文檔
│   ├── phase3/               # Phase 3 文檔
│   ├── user_guide/           # 使用者指南（版本選擇、安裝、TUI）
│   ├── development/          # 開發指南
│   ├── plans/                # 規劃文檔
│   ├── security/             # 安全文檔
│   ├── mcp/                  # MCP 相關文檔
│   ├── features/             # 功能文檔
│   ├── contract/             # JSON Schema 合約
│   ├── memory/               # 詳細經驗記錄
│   ├── archive/              # 歷史文檔
│   └── implementation/       # 實作細節
│
├── examples/                  # 範例代碼
│
├── flask_service.py           # Edge：Flask 背景服務入口
├── run_service_cli.py         # Edge：CLI 模式入口
├── unified_launcher_cli.py    # Edge：統一啟動器 CLI (Phase 3.1)
├── app.py                     # Server：WebUI 啟動入口
├── config.py                  # Flask 配置（向後相容）
├── requirements.txt           # Python 依賴
├── package.json               # 根層級 npm 腳本
└── README.md                  # 專案主文檔
```

## 環境隔離：Edge vs Server

### Edge 環境（本地/邊緣）

Edge 環境運行於本地設備或邊緣節點，特點：
- 低延遲處理
- 離線支援
- 本地佇列系統
- 直接與機器人通訊

**組件**：
- `electron-app/` - Electron 桌面應用
- `src/robot_service/` - Python 背景服務
- `flask_service.py` - Flask API 入口
- `run_service_cli.py` - CLI 模式入口

**配置**：
```python
from src.common.config import EdgeConfig
config = EdgeConfig.from_env()
```

### Server 環境（伺服器端）

Server 環境運行於中央伺服器，特點：
- 集中管理多個 Edge 節點
- 用戶認證與授權
- 數據持久化
- Web 管理介面

**組件**：
- `MCP/` - Model Context Protocol API
- `WebUI/` - Web 管理介面
- `app.py` - WebUI 入口

**配置**：
```python
from src.common.config import ServerConfig
config = ServerConfig.from_env()
```

### 共用模組

`src/common/` 提供 Edge 和 Server 共用的工具：
- `logging_utils.py` - 統一 JSON 結構化日誌
- `datetime_utils.py` - 時間處理工具
- `config.py` - 環境配置類別

## 模組職責

### 1. Electron App (`electron-app/`)

**目的**：提供桌面應用程序介面

**組件**：
- `main.js` - Electron 主程序，負責：
  - 啟動 Python Flask 服務
  - 管理應用視窗
  - 健康檢查與監控
  - IPC 通訊
- `preload.js` - 安全橋接腳本（Context Isolation）
- `renderer/` - 前端 UI（HTML/CSS/JS）

**運行模式**：
```bash
npm start              # 從根目錄啟動
cd electron-app && npm start  # 從 electron-app 目錄啟動
```

### 2. Robot Service (`src/robot_service/`)

**目的**：模組化的背景 Python 服務

**特性**：
- 本地優先權佇列系統
- 雙模式運行：Electron 整合 + 獨立 CLI
- 非同步訊息處理
- Prometheus metrics 與結構化日誌

**運行模式**：
```bash
# Electron 整合模式（由 main.js 自動啟動）
npm start

# 獨立 CLI 模式
python3 run_service_cli.py --queue-size 1000 --workers 5

# Flask 服務模式（測試用）
APP_TOKEN=xxx PORT=5000 python3 flask_service.py

# 統一啟動器（一鍵啟動所有服務）
python3 unified_launcher_cli.py
```

### 3. MCP Service (`MCP/`)

**目的**：指令中介層，提供統一 API

**功能**：
- 指令接收、驗證、路由
- 認證與授權（JWT）
- Schema 驗證（JSON Schema）
- 上下文管理
- LLM 整合
- 可觀測性（metrics + 日誌）

**運行**：
```bash
cd MCP
python3 start.py
# 或
uvicorn api:app --host 0.0.0.0 --port 8000
```

### 4. Robot-Console (`Robot-Console/`)

**目的**：機器人執行層抽象

**功能**：
- 動作執行器（38+ 預定義動作）
- 發布/訂閱機制
- 多協定支援（MQTT/HTTP/WebSocket）
- 緊急停止機制

**注意**：進階指令解碼已移至 WebUI 處理

### 5. WebUI (`WebUI/`)

**目的**：Web 管理介面（基於 Flask Microblog 架構）

**架構說明**：
WebUI 基於 Flask Microblog 的 Server-Client 架構設計。目前為單體應用，未來將拆分為：
- **Server 端**：API 後端、認證授權、資料庫管理、業務邏輯
- **Edge 端**：前端 UI、本地快取、離線支援

**功能**：
- 使用者管理與認證（Session/JWT）
- 機器人狀態監控與儀表板
- 指令發送、歷史記錄與審計
- 進階指令展開與使用者互動
- 積分系統與排行榜（用戶互動）

**目錄結構**：
```
WebUI/
├── app/
│   ├── routes.py        # 路由處理
│   ├── models.py        # 資料庫模型
│   ├── forms.py         # 表單驗證
│   ├── engagement.py    # 用戶互動系統
│   ├── mqtt_client.py   # MQTT 通訊（連接 Edge）
│   └── templates/       # Jinja2 模板
├── migrations/          # 資料庫遷移
└── microblog.py         # 應用入口
```

**運行**：
```bash
cd WebUI
python microblog.py
```

**未來規劃（Edge/Server 分離）**：
```
# Phase 3+ 規劃
WebUI/
├── server/              # Server 端（API + 業務邏輯）
│   ├── api/
│   ├── services/
│   └── models/
└── edge/                # Edge 端（前端 + 本地處理）
    ├── components/
    ├── services/
    └── offline/
```

### 6. Tests (`tests/`)

**目的**：統一測試集合

**覆蓋範圍**：
- 認證合規性測試
- 指令處理測試
- 合約驗證測試
- 佇列系統測試
- 進階指令執行測試
- Pub/Sub 測試

**運行**：
```bash
python3 -m pytest tests/ -v
python3 -m pytest tests/test_queue_system.py -v
```

### 7. Config (`config/`)

**目的**：集中配置管理

**策略**：
- 環境變數優先
- `.env` 文件支援（開發環境）
- `config.py` 保留在根目錄（向後相容）

**配置類別**：
- Flask Service（`APP_TOKEN`, `PORT`）
- WebUI（`SECRET_KEY`, `SQLALCHEMY_DATABASE_URI`, `MQTT_*`）
- MCP Service（`MCP_API_*`, `MCP_JWT_SECRET`）

## 設計原則

### 1. 模組化
- 每個服務/模組職責清晰
- 松耦合設計，可獨立部署
- 清晰的 API 界限

### 2. 可測試性
- 所有核心功能都有測試覆蓋
- 使用 mock 隔離外部依賴
- 測試集中在 `tests/` 目錄

### 3. 可觀測性
- 統一的結構化 JSON 日誌
- Prometheus metrics 端點
- trace_id 追蹤
- 健康檢查端點

### 4. 安全性
- Bearer token 認證
- Context Isolation（Electron）
- Schema 驗證
- RBAC 權限控管

### 5. 可擴展性
- 本地佇列可擴展至 Redis/Kafka
- 支援多種協定（HTTP/WS/MQTT）
- 可插拔的執行後端

## 資料流

```
使用者 → Electron UI → Flask Service (5000) → Robot Service Queue
                                              ↓
                                        Worker Pool
                                              ↓
                    ← Response ← Pub/Sub ← Action Executor
```

或：

```
使用者 → WebUI (8080) → MCP API (8000) → Command Handler
                                              ↓
                                        Robot Router
                                              ↓
                    ← Response ← Robot-Console ← MQTT/HTTP
```

## 未來架構：Cloud-Edge-Runner（Phase 2+ 演進）

> **🚀 架構演進方向**：本專案將演進為 **Cloud-Edge-Runner** 三層架構，基於 proposal.md 的設計。

### 架構概覽（與 proposal.md 一致）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Cloud / Server Layer                             │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                        Cloud Services                               │ │
│  │  • 進階指令共享與排名                                                │ │
│  │  • 用戶討論區                                                       │ │
│  │  • 用戶授權與信任評級                                                │ │
│  │  • 共享 LLM 分析服務（大數據優化）                                   │ │
│  │  • 固件倉庫                                                         │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                          HTTPS/WSS （當網路可用時）
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                      Edge Layer (ALL-in-One Edge App)                    │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                     Unified Launcher                                │ │
│  │  一鍵啟動/停止所有服務 | LLM 選擇介面 | 系統健康監控                 │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐        │
│  │   Local WebUI    │ │   MCP Service    │ │   Robot Service  │        │
│  │  • 用戶設定介面  │ │  • 指令協調      │ │  • 本地佇列      │        │
│  │  • 機器人監控   │ │  • LLM 處理器    │ │  • Worker Pool   │        │
│  │  • 固件更新     │ │  • 插件系統      │ │  • 離線緩衝      │        │
│  └──────────────────┘ └──────────────────┘ └──────────────────┘        │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    Local LLM Provider                               │ │
│  │                 (Ollama / LM Studio / Cloud fallback)               │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                          Hardware Interface
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                          Runner Layer                                    │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                     Robot-Console                                   │ │
│  │  • 動作執行器（ActionExecutor）                                     │ │
│  │  • 協定適配（HTTP/MQTT/WS/Serial/ROS）                              │ │
│  │  • 緊急停止與安全機制                                               │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Humanoid   │  │     AGV     │  │    Drone    │  │     Arm     │    │
│  │   robot_7   │  │   robot_3   │  │   robot_9   │  │   robot_12  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 層級職責（與 proposal.md 一致）

| 層級 | 目錄 | 職責 |
|------|------|------|
| **Cloud/Server** | 雲端服務 | 進階指令共享、討論區、授權、LLM 分析 |
| **Edge** | `src/robot_service/`, `electron-app/`, `MCP/`, `WebUI/` | 本地處理、佇列、LLM、監控 |
| **Runner** | `Robot-Console/` | 動作執行、硬體控制、安全機制 |
| **共用** | `src/common/` | 日誌、時間、配置工具 |

#### Cloud/Server Layer（雲端/伺服器層）
- **進階指令共享與排名**：社群共享指令庫
- **用戶討論區**：經驗分享平台
- **用戶授權與信任評級**：集中式認證
- **共享 LLM 分析服務**：大數據優化的 AI 服務
- **固件倉庫**：集中管理固件版本

#### Edge Layer（邊緣層）
- **本地處理**：低延遲指令執行、離線支援
- **本地佇列**：優先權佇列、重試機制
- **LLM 處理器**：本地 LLM 推論（Ollama/LM Studio）
- **插件系統**：可擴充的功能模組
- **狀態同步**：與 Cloud 定期同步

#### Runner Layer（執行層）
- **動作執行**：直接控制機器人
- **感測器整合**：收集機器人狀態
- **安全機制**：緊急停止、邊界檢查
- **協定支援**：HTTP/MQTT/WS/Serial/ROS

### 資料流向（與 proposal.md 一致）

1. **指令下達**：用戶 → Edge WebUI → MCP（LLM 解析）→ Robot Service（佇列）→ Robot-Console → 機器人
2. **狀態回報**：機器人 → Robot-Console → Robot Service → Edge WebUI（即時顯示）
3. **雲端同步**：Edge ↔ Cloud（進階指令、用戶設定、分析資料）
4. **審計追蹤**：所有操作 → 本地事件日誌（含 trace_id）→ 可選上傳雲端

### Phase 3.1 已完成功能

- [x] **統一啟動器**（`unified_launcher.py`）：一鍵啟動/停止所有服務
- [x] **服務協調器**（`service_coordinator.py`）：服務生命週期管理、健康檢查、自動重啟
- [x] **共享狀態管理器**（`shared_state.py`）：服務間狀態共享、事件通知
- [x] **本地狀態存儲**（`state_store.py`）：SQLite 持久化、TTL 過期支援
- [x] **事件匯流排**（`event_bus.py`）：Pub/Sub 事件通訊

### Phase 3.2+ 規劃

- [ ] **WebUI 本地版**：完整的 Edge 端用戶介面
- [x] **固件更新介面**：機器人固件管理（UI/API 已完成）
- [ ] **離線模式支援**：無網路環境下核心功能運作
- [x] **CLI/TUI 版本**：終端機介面支援（✅ 已完成）
- [ ] **雲端服務整合**：進階指令共享、討論區、授權服務
- [ ] **分散式佇列**：Redis/Kafka 整合
- [ ] **多節點部署**：Kubernetes 支援

## 未來擴展（Phase 3.2+）

- [ ] Cloud-Edge-Runner 架構完整實作
- [ ] Redis/Kafka 整合（分散式佇列）
- [ ] Kubernetes 部署
- [ ] 更多機器人類型支援
- [ ] 進階分析與報表
- [ ] 多租戶支援

## 參考文件

- [README.md](../README.md) - 專案概覽與快速啟動
- [proposal.md](proposal.md) - 權威規格
- [PROJECT_MEMORY.md](PROJECT_MEMORY.md) - 專案記憶與經驗教訓
- [observability.md](features/observability-guide.md) - 可觀測性指南
- [queue-architecture.md](features/queue-architecture.md) - 佇列架構詳解
- [Robot Service README](../src/robot_service/README.md) - Robot Service 說明
- [MCP Module](../MCP/Module.md) - MCP 模組設計
- [Robot-Console Module](../Robot-Console/module.md) - Robot-Console 設計
- [Python Lint 指南](development/PYTHON_LINT_GUIDE.md) - 程式碼風格與 lint 修復策略
- [Phase 3.1 狀態報告](phase3/PHASE3_1_STATUS_REPORT.md) - Phase 3.1 完成摘要

## 版本歷史

- **Phase 1** - 初始實作，功能完整性（已完成）
- **Phase 2** - 目錄重構，模組化清晰化（已完成）
- **Phase 3.1** - 基礎整合：統一啟動器、服務協調器、共享狀態（已完成）
- **Phase 3.2** - 功能完善：WebUI 本地版、離線模式、CLI/TUI（進行中 - TUI 已完成）
