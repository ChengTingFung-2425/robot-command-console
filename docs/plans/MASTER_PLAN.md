# WebUI → Native App 轉換計畫（合併版）

> 此文件整合所有 Phase 1-6 規劃文檔，作為專案的單一參考來源。
> 
> **最後更新**：2025-11-26  
> **狀態**：Phase 1 已完成，Phase 2 進行中

---

## 目錄

1. [總覽與路線圖](#總覽與路線圖)
2. [Phase 0 — 探勘與需求收斂](#phase-0--探勘與需求收斂)
3. [Phase 1 — 技術選型與 Electron POC（已完成）](#phase-1--技術選型與-electron-poc已完成)
4. [Phase 2 — 模組化與後端服務層調整（進行中）](#phase-2--模組化與後端服務層調整進行中)
5. [Phase 3 — 前端移植為原生/混合 App](#phase-3--前端移植為原生混合-app)
6. [Phase 4 — 封裝、簽署與發佈管線](#phase-4--封裝簽署與發佈管線)
7. [Phase 5 — 測試、品質保證與監控](#phase-5--測試品質保證與監控)
8. [Phase 6 — 釋出、支持與持續優化](#phase-6--釋出支持與持續優化)
9. [技術規格與架構](#技術規格與架構)
10. [開發環境設置](#開發環境設置)
11. [打包與發佈](#打包與發佈)
12. [安全性指南](#安全性指南)

---

## 總覽與路線圖

### 目的

將現有的 `WebUI`（作為 web app）轉換成可跨平台發佈的應用程式（桌面或行動），同時保留原有功能並加入必要的原生整合。

### 時間表（粗略）

| Phase | 預估時間 | 狀態 |
|-------|----------|------|
| Phase 0 | 1–2 週 | ✅ 完成 |
| Phase 1 | 2–4 週 | ✅ 完成 |
| Phase 2 | 4–8 週 | 🔄 進行中 |
| Phase 3 | 4–12 週 | ⏳ 待開始 |
| Phase 4 | 1–4 週 | ⏳ 待開始 |
| Phase 5 | 2–6 週 | ⏳ 待開始 |
| Phase 6 | 持續 | ⏳ 待開始 |

### 技術選型決策

經評估，選用 **Electron** 作為桌面應用框架：
- ✅ 生態成熟、工具完整
- ✅ 開發週期短，風險低
- ✅ 與 Python 背景服務整合方便
- ⚠️ 體積較大（未來可考慮 Tauri 優化）

---

## Phase 0 — 探勘與需求收斂

**狀態**：✅ 完成

### 目標
蒐集使用者與業務需求，確認欲支援的平台與優先順序。

### 交付物
- [x] 需求清單
- [x] 目標平台矩陣（Windows/macOS/Linux 優先）
- [x] 風險評估報告
- [x] 成功衡量指標（KPIs）

### 驗收條件
- [x] 利害關係人確認需求文件並同意下一階段技術選型

---

## Phase 1 — 技術選型與 Electron POC（已完成）

**狀態**：✅ 完成

### 目標
- 在桌面平台上完成 Electron POC
- Electron 應用啟動，能啟動本地 Python 背景服務
- 完成一次完整的 API round-trip（Renderer → local API → 回應）

### 量化目標（KPIs）

| 指標 | 目標值 | 實際結果 |
|------|--------|----------|
| 可執行平台 | ≥1 個桌面平台 | ✅ Linux |
| 啟動時間 | < 5 秒 | ✅ 達成 |
| API round-trip | < 2000 ms | ✅ 達成 |
| 記憶體使用 | < 400 MB | ✅ 達成 |
| 安全限制 | 僅 127.0.0.1 | ✅ 達成 |

### 交付物
- [x] 可執行 POC 程式碼（`electron-app/`）
- [x] Python 背景服務（`flask_service.py`）
- [x] 開發文件（現已整合至本文件）
- [x] 技術審查報告

### 架構

```
┌─────────────────────────────────────────────────┐
│              Electron Application               │
├─────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────────────┐    │
│  │ Main Process│    │  Renderer Process   │    │
│  │  (main.js)  │◄──►│  (renderer.js)      │    │
│  └──────┬──────┘    └──────────┬──────────┘    │
│         │                      │               │
│         │ spawn                │ HTTP + Token  │
│         ▼                      ▼               │
│  ┌──────────────────────────────────────┐      │
│  │     Python Background Service        │      │
│  │     (flask_service.py @ 127.0.0.1)   │      │
│  └──────────────────────────────────────┘      │
└─────────────────────────────────────────────────┘
```

---

## Phase 2 — 模組化與後端服務層調整（進行中）

**狀態**：🔄 進行中

### 目標
- 將 `WebUI` 的後端或服務邏輯抽象化
- 建立穩定的本地 IPC 或 API 層
- 重構為 Server-Edge-Runner 三層架構

### 交付物
- [x] 重構後的服務層（`src/robot_service/`）
- [x] 共用工具模組（`src/common/`）
- [x] API/IPC 文件
- [ ] 完整測試用例

### 驗收條件
- [x] 本地背景服務可在開發平台以 CLI 或系統服務模式正常啟動
- [x] 前端能透過 IPC 呼叫並取得預期回應
- [ ] 所有模組遵循 Server-Edge-Runner 架構

### Server-Edge-Runner 架構

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Server      │────▶│      Edge       │────▶│     Runner      │
│  (MCP/WebUI)    │     │ (robot_service) │     │ (Robot-Console) │
│  集中管理/API   │     │ 本地處理/佇列   │     │ 機器人執行     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## Phase 3 — ALL-in-One Edge App 整合與部署

**狀態**：⏳ 待開始

> **詳細規劃文件**：[PHASE3_EDGE_ALL_IN_ONE.md](PHASE3_EDGE_ALL_IN_ONE.md)

### 目標

基於 Phase 2 建立的模組化架構與 LLM 整合能力，將 MCP、WebUI、Robot-Console 整合為統一的 ALL-in-One Edge App，部署於消費級邊緣運算設備。

### 核心功能

1. **統一啟動器**：一鍵啟動/停止所有服務
2. **LLM 選擇介面**：延續 Phase 2 的 `LLMProviderManager`，提供使用者選擇本地/雲端 LLM
3. **Edge-Cloud 分離**：
   - **Edge（本地）**：用戶設定、機器人監控、固件更新、指令介面
   - **Cloud（雲端）**：進階指令共享、討論區、用戶授權、共享 LLM 分析服務
4. **多模式部署**：GUI（Electron）、CLI/TUI、Docker

### 與 Phase 2 的銜接

| Phase 2 成果 | Phase 3 運用 |
|-------------|-------------|
| `src/common/` 共用模組 | 繼續使用，擴充 Edge 專用工具 |
| `src/robot_service/` 佇列系統 | 整合至 Edge 服務層 |
| `LLMProviderManager` | 作為 Edge LLM 管理基礎 |
| `PluginManager` | 支援運行時插件熱載入 |
| Server-Edge-Runner 架構 | 完整實作三層分離 |

### 交付物

#### Phase 3.1 — 基礎整合（4-6 週）
- [ ] 統一啟動器原型（Electron）
- [ ] 服務協調器（啟動/停止/健康檢查）
- [ ] 基礎 LLM 選擇介面
- [ ] 服務間狀態共享機制

#### Phase 3.2 — 功能完善（4-6 週）
- [ ] 完整的 WebUI 本地版
- [ ] 機器人監控儀表板
- [ ] 固件更新介面
- [ ] 離線模式支援
- [ ] CLI/TUI 版本

#### Phase 3.3 — 雲端整合（4-6 週）
- [ ] 雲端同步機制
- [ ] 進階指令共享功能
- [ ] 用戶授權整合
- [ ] 共享 LLM 服務整合

#### Phase 3.4 — 打包與發佈（2-4 週）
- [ ] Linux AppImage
- [ ] Windows 安裝程式
- [ ] macOS DMG
- [ ] Docker 映像

### 驗收條件
- [ ] 一鍵啟動所有服務，健康檢查通過
- [ ] 可選擇本地/雲端 LLM 提供商
- [ ] 離線模式下核心功能正常
- [ ] CLI 可完整操作所有功能
- [ ] 各平台安裝程式可用
- [ ] Docker 部署正常

### 硬體目標

| 類別 | 代表設備 | 最低規格 |
|------|---------|---------|
| Mini-PC | Intel NUC, Beelink | 4GB RAM, 32GB 儲存 |
| 邊緣運算 | NVIDIA Jetson | 4GB RAM, GPU |
| 單板電腦 | Raspberry Pi 4/5 | 4GB RAM |

---

## Phase 4 — 封裝、簽署與發佈管線

**狀態**：⏳ 待開始

### 目標
建立可重複的打包與發佈流程。

### 交付物
- [ ] 自動化 CI/CD 腳本
- [ ] 打包與簽署設定
- [ ] 發佈說明文件
- [ ] 安裝器或發佈包範例

### 打包配置範例

```json
{
  "build": {
    "appId": "com.example.robotconsole",
    "files": ["dist/**", "py-service/**"],
    "mac": {"target": ["dmg"]},
    "win": {"target": ["nsis"]},
    "linux": {"target": ["AppImage"]}
  }
}
```

### 打包指令

```bash
npx electron-builder --mac
npx electron-builder --win
npx electron-builder --linux
```

---

## Phase 5 — 測試、品質保證與監控

**狀態**：⏳ 待開始

### 目標
建立完整的 QA 流程與監控。

### 交付物
- [ ] 測試計畫
- [ ] E2E 測試套件
- [ ] 錯誤追蹤設定（Sentry 等）
- [ ] 監控與使用分析儀表板

---

## Phase 6 — 釋出、支持與持續優化

**狀態**：⏳ 待開始

### 目標
正式釋出產品，建立支援流程並持續收集回饋進行優化。

### 交付物
- [ ] 發佈公告
- [ ] 支援手冊
- [ ] 版本管理策略
- [ ] 回饋蒐集與迭代計畫

---

## 技術規格與架構

### 候選技術比較

| 技術 | 優點 | 缺點 | 適用情境 |
|------|------|------|----------|
| **Electron** ✅ | 成熟生態、開發週期短 | 體積大、記憶體消耗高 | 快速產出桌面 App |
| Tauri | 體積小、安全性佳 | 需 Rust 工具鏈 | 對體積/安全有高要求 |
| Capacitor | 快速包裝移動 App | 原生能力有限 | 快速導向行動平台 |
| React Native | 原生 UI 體驗好 | 需重寫前端 | 重視行動原生體驗 |

### 啟動流程

1. Electron 主進程啟動
2. 產生短期 Token
3. 檢查/啟動 Python 背景服務（spawn 子進程）
4. 執行 Health Check（最多 30 次重試）
5. Renderer 載入並用 Token 與背景服務通訊

### Spawn 範例

```javascript
const { spawn } = require('child_process');
const py = spawn('python', ['path/to/app.py'], { stdio: 'inherit' });

py.on('exit', (code) => console.log('python exit', code));

app.on('before-quit', () => {
  py.kill();
});
```

---

## 開發環境設置

### 先決條件

- Node.js（建議 LTS）與 npm
- Python 3.x 並建立虛擬環境

### 建置步驟

```bash
# 1. 取得專案
git clone <repo>
cd robot-command-console

# 2. 建立 Python venv 並安裝相依
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. 安裝 Node 依賴
npm install

# 4. 開發模式啟動
npm run start:dev
```

### Debug 小技巧

- Renderer 使用 DevTools
- 主進程可加入 `--inspect` 供 VSCode attach
- Python 日誌輸出到 console，方便追蹤 spawn 問題

---

## 打包與發佈

### 基本工具

- `electron-builder`
- 平台簽章工具：
  - macOS：Apple Developer ID + `codesign`
  - Windows：EV code signing

### Python 背景服務打包考量

| 方式 | 優點 | 缺點 |
|------|------|------|
| 內嵌 Python | 無需使用者安裝 | 跨平台二進位複雜 |
| 外部安裝 | 打包簡單 | 需使用者安裝 Python |

### CI/CD 範例（概要）

```bash
npm ci && npm run build && npx electron-builder
```

---

## 安全性指南

### 本地服務安全

- ✅ 監聽回環位址（127.0.0.1），避免綁定 0.0.0.0
- ✅ 使用短期 Token 認證
- ✅ Context Isolation 啟用
- ✅ 敏感資料使用 OS 安全儲存（Keychain/DPAPI/Secret Service）

### Token 流程

1. 主進程在每次啟動時產生短期 Token
2. Token 透過 `contextBridge` 傳遞給 Renderer
3. Renderer 在請求時加上 `Authorization: Bearer <token>` header
4. Python 服務驗證 Token

### CSP 建議

```html
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'self'; script-src 'self'">
```

---

## 風險與緩解策略

| 風險 | 緩解策略 |
|------|----------|
| Python 服務啟動/升級複雜 | 實作啟動守護邏輯與版本檢查 |
| 本地 HTTP 接口暴露 | 限制回環介面、使用 Token |
| 二進位體積/記憶體 | 初期 Electron，未來可考慮 Tauri |

---

## 附錄：原始文件對照

本文件整合了以下原始文件：
- `PLAN.md` → 總覽與路線圖
- `phase-1-goals-targets.md` → Phase 1 量化目標
- `phase-1-todos.md` → Phase 1 執行待辦
- `phase-1-electron-refined.md` → Phase 1 精煉計畫
- `phase-1-technical-spec.md` → 技術規格
- `electron-dev-setup.md` → 開發環境設置
- `electron-packaging.md` → 打包與發佈
- `electron-python-integration.md` → Python 整合
- `electron-vs-tauri-docs-planning.md` → 技術比較

---

**文件維護者**：開發團隊  
**下次審查**：Phase 2 完成時
