# WebUI 本地移植分析文件 — Edge/Cloud 隔離

> **建立日期**：2025-12-04  
> **狀態**：🔄 實作進行中  
> **目標**：Phase 3.2 - 完整的 WebUI 本地版 + Edge/Cloud 功能隔離  
> **關聯**：[PHASE3_EDGE_ALL_IN_ONE.md](../plans/PHASE3_EDGE_ALL_IN_ONE.md)

---

## 📋 執行摘要

本文件分析現有 WebUI（Server 端）功能，**識別需要移植到 Edge 環境的組件**，並**進行 Edge 和 Cloud 的明確隔離**。

### 核心原則

根據 [proposal.md](../proposal.md) 的 Server-Edge-Runner 三層架構：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Cloud / Server Layer                             │
│  • 進階指令共享與排名      • 用戶討論區                                    │
│  • 用戶授權與信任評級      • 共享 LLM 分析服務                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                          HTTPS/WSS （當網路可用時）
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                      Edge Layer (ALL-in-One Edge App)                    │
│  • 用戶設定介面    • MCP Service       • Robot Service                   │
│  • 機器人監控      • LLM 處理器        • 本地佇列                          │
│  • 固件更新        • 插件系統          • 離線緩衝                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 移植目標

將 `WebUI/` 中的 **Edge 功能** 移植到 `electron-app/` 或本地服務，實現：
- **離線可用**：無需網路即可控制機器人
- **低延遲**：本地處理減少通訊延遲
- **邊緣優先**：Edge-First 設計原則
- **職責明確**：Edge 與 Cloud 功能清楚分離

---

## 🏗️ 移植方案比較

### 方案 A：純 Electron 前端

**方法**：將所有 Edge UI 直接在 Electron 渲染器中實作（純 HTML/CSS/JS）

```
electron-app/
├── renderer/
│   ├── index.html              # 統一啟動器（主入口）
│   ├── pages/
│   │   ├── dashboard.html      # 機器人儀表板
│   │   ├── command-center.html # 指令控制中心
│   │   ├── llm-settings.html   # LLM 設定
│   │   └── advanced-cmd.html   # 進階指令編輯器
│   ├── js/
│   │   ├── api-client.js       # 統一 API 封裝
│   │   └── robot_blocks.js     # Blockly 積木
│   └── css/
└── main.js
```

| 優點 | 缺點 |
|------|------|
| ✅ 最低延遲（無網路請求） | ❌ 需重寫所有 Jinja2 模板 |
| ✅ 完整桌面應用體驗 | ❌ 開發工作量大 |
| ✅ 離線完全可用 | ❌ 無法重用現有 Flask 代碼 |
| ✅ 無額外服務依賴 | ❌ 需維護兩套前端 |

**預估工時**：40-60 小時

---

### 方案 B：本地 Flask 服務 + Electron 載入

**方法**：建立獨立的 Edge Flask 服務，Electron 載入本地 Flask 頁面

```
src/edge_webui/                 # Edge 專用 Flask
├── __init__.py
├── app.py                      # Flask 應用
├── routes.py                   # 簡化路由
├── models.py                   # Edge 資料模型
├── templates/                  # 複製/調整 WebUI 模板
└── static/

electron-app/
├── main.js                     # 載入 Flask 頁面
└── renderer/                   # 備用/啟動器
```

| 優點 | 缺點 |
|------|------|
| ✅ 可重用大量 WebUI 代碼 | ❌ 需要額外 Flask 進程 |
| ✅ 保持 Jinja2 模板系統 | ❌ 增加資源消耗 |
| ✅ 開發速度較快 | ❌ 兩個 Flask 服務可能混淆 |
| ✅ 後端邏輯可共用 | ❌ 維護成本增加 |

**預估工時**：20-30 小時

---

### 方案 C：混合方案（✅ 推薦）

**方法**：擴展現有 Flask Service，新增 Edge UI 路由；Electron 可載入本地頁面

```
flask_service.py                # 現有：擴展為 Edge 完整服務
├── /health                     # 現有
├── /api/ping                   # 現有
├── /api/robots                 # 新增：機器人管理
├── /api/commands               # 新增：指令執行
├── /api/llm/*                  # 新增：LLM 管理代理
├── /ui/dashboard               # 新增：儀表板頁面
├── /ui/command-center          # 新增：指令控制中心
├── /ui/llm-settings            # 新增：LLM 設定
└── /ui/advanced-commands       # 新增：進階指令

electron-app/
├── main.js                     # 載入 Flask UI 頁面
├── renderer/index.html         # 統一啟動器（備用入口）
└── preload.js
```

| 優點 | 缺點 |
|------|------|
| ✅ 重用現有 Flask Service | ⚠️ Flask Service 功能擴展 |
| ✅ 單一服務進程 | ⚠️ 需要模板系統 |
| ✅ 最小架構變更 | ⚠️ 混合 API + UI 路由 |
| ✅ 可漸進式移植 | |
| ✅ 保持向後相容 | |

**預估工時**：15-25 小時

---

## ✅ 選擇方案 C：混合方案

### 選擇理由

1. **最小變更原則**：擴展現有 Flask Service，無需建立新服務
2. **重用代碼**：可複製 WebUI 模板並調整
3. **漸進式移植**：可逐步增加功能
4. **單一服務**：Electron 只需管理一個 Flask 進程

### 實作計畫

#### 階段 1：基礎擴展（✅ 已完成）
- [x] 分析 Edge/Cloud 功能隔離
- [x] 擴展 Flask Service 結構
- [x] 新增 Edge UI 模板目錄
- [x] 實作 Edge UI 藍圖 (`edge_ui.py`)
- [x] 實作機器人儀表板 API (`/api/edge/robots`)
- [x] 實作機器人儀表板頁面 (`/ui/dashboard`)
- [x] 實作指令控制中心頁面 (`/ui/command-center`)
- [x] 實作 LLM 設定頁面 (`/ui/llm-settings`)
- [x] 實作用戶設定頁面 (`/ui/settings`)
- [x] 建立 Edge UI CSS 樣式 (`edge.css`)
- [x] 建立通用 JavaScript (`edge-common.js`)

#### 階段 1.5：機器人監控儀表板增強（✅ 已完成）
- [x] 機器人類型系統（humanoid, agv, arm, drone, other）
- [x] 機器人健康檢查 API (`/api/edge/robots/<id>/health`)
- [x] 機器人健康歷史 API (`/api/edge/robots/<id>/health/history`)
- [x] 儀表板摘要 API (`/api/edge/dashboard/summary`)
- [x] 機器人類型 API (`/api/edge/robot-types`)
- [x] 機器人刪除 API (`DELETE /api/edge/robots/<id>`)
- [x] 儀表板摘要統計卡片
- [x] 機器人詳情對話框
- [x] 健康檢查按鈕與歷史顯示
- [x] 電量視覺化（高/中/低）
- [x] 測試覆蓋（23 個新測試）

#### 階段 2：指令控制
- [ ] 實作指令執行 API
- [ ] 實作指令控制中心頁面
- [ ] 整合狀態即時更新

#### 階段 3：LLM 管理
- [ ] 實作 LLM 狀態代理 API
- [ ] 實作 LLM 設定頁面

#### 階段 4：進階指令
- [ ] 移植 Blockly 編輯器
- [ ] 實作本地進階指令管理

---

## 🔍 WebUI 組件 Edge/Cloud 分類

### 完整功能分類表

| 功能 | 路由/檔案 | 環境 | 說明 | 移植優先級 |
|------|----------|------|------|------------|
| **用戶認證（本地）** | `/login`, `/logout` | 🟢 **Edge** | 本地簡化認證 | 🔴 高 |
| **用戶註冊** | `/register` | 🔵 Cloud | 雲端用戶管理 | ❌ 不移植 |
| **密碼重設** | `/reset_password*` | 🔵 Cloud | 需要郵件服務 | ❌ 不移植 |
| **機器人儀表板** | `/dashboard` | 🟢 **Edge** | 本地機器人監控 | 🔴 高 |
| **機器人註冊** | `/register_robot` | 🟢 **Edge** | 本地機器人管理 | 🔴 高 |
| **指令執行** | `/commands` | 🟢 **Edge** | 直接控制機器人 | 🔴 高 |
| **指令狀態查詢** | `/commands/<id>` | 🟢 **Edge** | 即時狀態追蹤 | 🔴 高 |
| **進階指令列表** | `/advanced_commands` | 🟡 **Edge+Cloud** | 本地列表 + 雲端共享 | 🟡 中 |
| **進階指令建立** | `/advanced_commands/create` | 🟢 **Edge** | 本地 Blockly 編輯器 | 🔴 高 |
| **進階指令編輯** | `/advanced_commands/edit/<id>` | 🟢 **Edge** | 本地編輯 | 🟡 中 |
| **進階指令審核** | `/advanced_commands/audit/<id>` | 🔵 Cloud | 社群審核機制 | ❌ 不移植 |
| **進階指令執行** | `/advanced_commands/<id>/execute` | 🟢 **Edge** | 本地執行 | 🔴 高 |
| **LLM 設定** | `/llm_settings` | 🟢 **Edge** | 本地 LLM 管理 | 🔴 高 |
| **LLM 狀態 API** | `/api/llm/*` | 🟢 **Edge** | 本地 LLM 狀態 | 🔴 高 |
| **用戶設定** | `/settings/ui`, `/user/edit_profile` | 🟢 **Edge** | 本地偏好設定 | 🔴 高 |
| **用戶檔案** | `/user/<username>` | 🔵 Cloud | 社群個人頁面 | ❌ 不移植 |
| **排行榜** | `/leaderboard` | 🔵 Cloud | 雲端用戶排名 | ❌ 不移植 |
| **媒體串流** | `/media_stream` | 🟢 **Edge** | 本地視訊串流 | 🟡 中 |

### 資料模型分類

| 模型 | 檔案 | 環境 | 說明 |
|------|------|------|------|
| `User` | `models.py` | 🟡 **Edge+Cloud** | Edge: 簡化本地用戶 / Cloud: 完整用戶管理 |
| `UserProfile` | `models.py` | 🔵 Cloud | 積分、等級、成就系統 |
| `Robot` | `models.py` | 🟢 **Edge** | 本地機器人資料 |
| `Command` | `models.py` | 🟢 **Edge** | 指令執行記錄 |
| `AdvancedCommand` | `models.py` | 🟡 **Edge+Cloud** | Edge: 本地指令 / Cloud: 共享指令 |
| `AdvCommand` | `models.py` | 🟢 **Edge** | 指令內容存儲 |
| `AdvancedCommandVersion` | `models.py` | 🔵 Cloud | 版本歷史（雲端同步） |
| `Achievement` | `models.py` | 🔵 Cloud | 成就定義 |
| `UserAchievement` | `models.py` | 🔵 Cloud | 用戶成就記錄 |

### 業務邏輯分類

| 模組 | 檔案 | 環境 | 說明 |
|------|------|------|------|
| `expand_advanced_command()` | `routes.py` | 🟢 **Edge** | 展開進階指令 |
| `send_actions_to_robot()` | `routes.py` | 🟢 **Edge** | 發送動作到機器人 |
| `award_points()` | `engagement.py` | 🔵 Cloud | 積分獎勵 |
| `grant_achievement()` | `engagement.py` | 🔵 Cloud | 成就授予 |
| `get_leaderboard()` | `engagement.py` | 🔵 Cloud | 排行榜查詢 |
| MQTT 客戶端 | `mqtt_client.py` | 🟢 **Edge** | 機器人通訊 |

---

## 🎯 Edge vs Cloud 職責明確定義

### 🟢 Edge 職責（需移植）

根據 [proposal.md](../proposal.md) Edge 層定義：

```
┌────────────────────────────────────────────────────────────────────────┐
│                         Edge 功能範圍                                   │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  📊 機器人監控              🔧 用戶設定                                 │
│  ├─ 即時狀態顯示            ├─ UI 偏好（主題、時間單位）                │
│  ├─ 電量/位置/連線          ├─ LLM 偏好設定                            │
│  ├─ 健康檢查                └─ 本地存儲 (SQLite/JSON)                  │
│  └─ 告警通知                                                            │
│                                                                         │
│  🤖 指令控制                🧩 進階指令（本地）                          │
│  ├─ 機器人選擇              ├─ Blockly 積木編輯器                       │
│  ├─ 動作選擇/發送           ├─ 指令驗證                                 │
│  ├─ 執行狀態監控            ├─ 本地儲存                                 │
│  └─ 歷史記錄                └─ 匯入/匯出                                │
│                                                                         │
│  🧠 LLM 管理                📡 通訊                                     │
│  ├─ 本地提供商掃描          ├─ MQTT 直接通訊                           │
│  ├─ Ollama/LM Studio        ├─ HTTP API                                │
│  ├─ 模型選擇                └─ WebSocket 即時更新                       │
│  └─ 健康狀態                                                            │
│                                                                         │
│  💾 本地存儲                🔐 本地認證（簡化）                          │
│  ├─ 機器人資料              ├─ 本地用戶（無需密碼重設）                  │
│  ├─ 指令歷史                ├─ Session 管理                            │
│  ├─ 進階指令快取            └─ 角色權限（本地）                         │
│  └─ 用戶偏好                                                            │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### 🔵 Cloud 職責（不移植）

根據 [proposal.md](../proposal.md) Cloud 層定義：

```
┌────────────────────────────────────────────────────────────────────────┐
│                         Cloud 功能範圍                                  │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  👥 社群功能                📊 數據分析                                 │
│  ├─ 用戶註冊（郵件驗證）    ├─ 指令使用統計                            │
│  ├─ 密碼重設                ├─ 群體行為分析                            │
│  ├─ 用戶討論區              └─ 最佳化建議                              │
│  └─ 用戶個人頁面                                                        │
│                                                                         │
│  🏆 遊戲化系統              🔄 進階指令共享                             │
│  ├─ 積分/等級系統           ├─ 社群提交                                 │
│  ├─ 成就/徽章               ├─ 審核流程                                 │
│  ├─ 排行榜                  ├─ 評分/排名                                │
│  └─ 信任評級                └─ 版本歷史                                 │
│                                                                         │
│  ☁️ 雲端 LLM                🔒 集中授權                                 │
│  ├─ 大數據優化模型          ├─ OAuth2/SSO                              │
│  ├─ 群體智慧學習            ├─ JWT Token 管理                          │
│  └─ 備援服務                └─ 信任評級                                 │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### 🟡 Edge+Cloud 混合功能

需要特別處理的混合功能：

| 功能 | Edge 部分 | Cloud 部分 |
|------|-----------|------------|
| **進階指令** | 本地建立、儲存、執行 | 社群共享、審核、排名 |
| **用戶管理** | 本地簡化用戶 | 完整註冊、驗證、密碼重設 |
| **指令歷史** | 本地記錄 | 雲端同步（可選） |
| **LLM** | 本地 Ollama/LM Studio | 雲端 LLM 服務（備援） |

---

## 🎯 移植範圍與優先級

### Phase 3.2 必須移植（高優先級）

1. **機器人儀表板**
   - 顯示所有本地機器人狀態
   - 即時連線狀態、電量、位置
   - 快速操作按鈕
   - **來源**：`WebUI/app/templates/robot_dashboard.html.j2`

2. **指令控制中心**
   - 選擇機器人
   - 選擇動作（從機器人能力清單）
   - 下達指令
   - 執行狀態監控
   - **來源**：`WebUI/app/routes.py` 的 `/commands` 端點

3. **LLM 設定介面**
   - 本地 LLM 提供商掃描（Ollama/LM Studio）
   - 提供商選擇與模型管理
   - 連線狀態監控
   - **來源**：`WebUI/app/templates/llm_settings.html.j2`

4. **本地用戶設定**
   - UI 偏好設定（時間單位、主題）
   - LLM 偏好設定
   - 本地存儲（SQLite/JSON）
   - **來源**：`src/common/state_store.py` + `WebUI/app/routes.py`

5. **進階指令建立器**
   - Blockly 積木編輯器
   - 動作序列組合
   - 指令驗證
   - 匯入/匯出功能
   - **來源**：`WebUI/app/templates/create_advanced_command.html.j2` + `static/js/robot_blocks.js`

### Phase 3.3 延後移植（中優先級）

1. **本地認證系統**
   - 簡化的本地用戶管理
   - 無需完整 OAuth2/JWT（本地環境）
   
2. **媒體串流**
   - WebRTC 本地串流
   - 機器人攝影機整合

3. **進階指令本地管理**
   - 本地指令庫
   - 匯入/匯出功能

### 雲端專用功能（不移植）

1. **排行榜** - 需要雲端數據彙整
2. **用戶成就系統** - 社群功能
3. **進階指令共享** - 雲端功能
4. **用戶討論區** - 社群功能

---

## 🏗️ 移植策略

### 策略一：Electron 渲染器擴展

**方法**：在現有 `electron-app/renderer/` 中新增頁面

```
electron-app/
├── renderer/
│   ├── index.html              # 現有：統一啟動器
│   ├── dashboard.html          # 新增：機器人儀表板
│   ├── command-center.html     # 新增：指令控制中心
│   ├── llm-settings.html       # 新增：LLM 設定
│   ├── command-builder.html    # 新增：進階指令建立器
│   ├── settings.html           # 新增：用戶設定
│   ├── js/
│   │   ├── renderer.js         # 現有：啟動器
│   │   ├── dashboard.js        # 新增
│   │   ├── command-center.js   # 新增
│   │   ├── robot_blocks.js     # 複製自 WebUI
│   │   └── ...
│   └── css/
│       └── ...
└── main.js                     # 更新：支援多視窗/路由
```

**優點**：
- 直接在 Electron 中運行，最低延遲
- 完整的桌面應用體驗
- 可使用 Node.js 原生功能

**缺點**：
- 需要重新實作前端邏輯（從 Jinja2 轉換）
- 無法直接使用 Flask 模板

### 策略二：本地 Flask 服務整合

**方法**：啟動本地 Flask 服務並在 Electron 中載入

```
electron-app/
├── main.js                     # 載入本地 Flask 頁面
├── preload.js
└── renderer/
    └── index.html              # 統一啟動器（備用）

src/edge_webui/                 # 新增：Edge 專用 WebUI
├── __init__.py
├── app.py                      # Flask 應用
├── routes.py                   # 路由（簡化版）
├── templates/                  # 複製/調整 WebUI 模板
└── static/                     # 靜態資源
```

**優點**：
- 可重用大量現有 WebUI 程式碼
- 保持 Flask 模板系統
- 開發速度快

**缺點**：
- 需要額外的本地服務
- 增加資源消耗

### 策略三：混合方法（建議）

**方法**：核心功能用 Electron 原生實作，複雜功能透過本地 Flask 服務

```
electron-app/
├── main.js
├── preload.js
└── renderer/
    ├── index.html              # 統一啟動器 + 導航
    ├── dashboard.html          # 原生：機器人儀表板
    ├── command-center.html     # 原生：指令控制中心
    ├── llm-settings.html       # 原生：LLM 設定
    └── ...

src/edge_webui/                 # Edge 專用 Flask
├── app.py
├── routes.py
├── templates/
│   └── command-builder.html    # 複雜功能：Blockly 編輯器
└── static/
    └── js/
        └── robot_blocks.js     # Blockly 積木定義
```

**優點**：
- 平衡開發速度與使用者體驗
- 核心功能本地化，複雜功能可漸進遷移
- 保持靈活性

---

## 📁 需要複製/遷移的檔案

### 必須複製

| 來源 | 目標 | 說明 |
|------|------|------|
| `WebUI/app/static/js/robot_blocks.js` | `electron-app/renderer/js/` 或 `src/edge_webui/static/js/` | Blockly 積木定義 |
| `WebUI/app/static/css/blockly_workspace.css` | 同上 | Blockly 樣式 |
| `WebUI/app/static/css/robot_dashboard.css` | 同上 | 儀表板樣式 |
| `WebUI/app/static/js/robot_dashboard.js` | 同上 | 儀表板邏輯 |

### 需要調整後複製

| 來源 | 說明 |
|------|------|
| `WebUI/app/templates/llm_settings.html.j2` | 移除 Jinja2 語法，改用純 HTML + JS |
| `WebUI/app/templates/robot_dashboard.html.j2` | 同上 |
| `WebUI/app/templates/create_advanced_command.html.j2` | 同上 |

### 需要新建

| 檔案 | 說明 |
|------|------|
| `electron-app/renderer/navigation.js` | 頁面導航邏輯 |
| `electron-app/renderer/api-client.js` | 統一 API 呼叫封裝 |
| `src/edge_webui/app.py` | Edge 專用 Flask 應用（如採用策略二/三） |

---

## 🔗 API 端點對照

### 需要在本地實現的 API

| WebUI 端點 | 本地對應 | 說明 |
|------------|---------|------|
| `GET /dashboard` | 本地渲染 | 機器人儀表板頁面 |
| `GET /robots` | `Flask Service /api/robots` | 機器人清單 |
| `POST /commands` | `Flask Service /api/commands` | 發送指令 |
| `GET /commands/<id>` | `Flask Service /api/commands/<id>` | 查詢狀態 |
| `GET /api/llm/status` | `MCP /api/llm/connection/status` | LLM 連線狀態 |
| `GET /api/llm/providers` | `MCP /api/llm/providers` | LLM 提供商 |
| `POST /api/llm/providers/select` | `MCP /api/llm/providers/select` | 選擇提供商 |
| `POST /api/llm/providers/discover` | `MCP /api/llm/providers/discover` | 掃描提供商 |

### 已存在的本地 API（Flask Service）

| 端點 | 說明 |
|------|------|
| `GET /health` | 健康檢查 |
| `POST /api/ping` | 連線測試 |
| `GET /api/robots` | 機器人清單（需實作） |
| `POST /api/commands` | 發送指令（需實作） |

---

## 📋 實作檢查清單

### Phase 3.2 待辦事項

- [ ] **機器人儀表板**
  - [ ] 建立 `dashboard.html` 頁面
  - [ ] 實作機器人狀態卡片元件
  - [ ] 整合 WebSocket 即時更新
  - [ ] 樣式遷移（`robot_dashboard.css`）

- [ ] **指令控制中心**
  - [ ] 建立 `command-center.html` 頁面
  - [ ] 實作機器人選擇器
  - [ ] 實作動作選擇器（動態載入）
  - [ ] 實作指令發送與狀態監控

- [ ] **LLM 設定介面**
  - [ ] 建立 `llm-settings.html` 頁面
  - [ ] 實作提供商列表與健康狀態
  - [ ] 實作提供商選擇功能
  - [ ] 整合模型選擇器

- [ ] **進階指令建立器**
  - [ ] 複製 Blockly 相關資源
  - [ ] 建立 `command-builder.html` 頁面
  - [ ] 調整 Jinja2 模板為純 HTML
  - [ ] 測試積木功能

- [ ] **用戶設定**
  - [ ] 建立 `settings.html` 頁面
  - [ ] 整合 `SharedStateManager` 存儲
  - [ ] 實作 UI 偏好設定

- [ ] **導航系統**
  - [ ] 更新 `main.js` 支援多頁面
  - [ ] 建立統一導航列
  - [ ] 實作頁面切換邏輯

---

## 📝 附錄：關鍵程式碼片段

### Blockly 積木定義（需遷移）

```javascript
// WebUI/app/static/js/robot_blocks.js
// 定義了 37 種機器人動作積木
// 包含：移動、姿態、戰鬥、舞蹈、運動、控制積木
```

### LLM 狀態 API 調用（需調整）

```javascript
// 原：透過 WebUI 代理
fetch('/api/llm/status')

// 新：直接呼叫 MCP 或 Flask Service
fetch('http://127.0.0.1:8000/api/llm/connection/status')  // MCP
fetch('http://127.0.0.1:5000/api/llm/status')            // Flask Service
```

---

## 📚 參考文件

- [PHASE3_EDGE_ALL_IN_ONE.md](../plans/PHASE3_EDGE_ALL_IN_ONE.md) - Phase 3 規劃
- [PHASE3_1_STATUS_REPORT.md](PHASE3_1_STATUS_REPORT.md) - Phase 3.1 狀態
- [architecture.md](../architecture.md) - 系統架構
- [WebUI/Module.md](../../WebUI/Module.md) - WebUI 模組設計
- [proposal.md](../proposal.md) - 權威規格

---

**文件維護者**：Copilot  
**最後更新**：2025-12-04
