# Phase 1 — 技術規格草案（Technical Specification Draft）

目的：為將 `WebUI` 轉換為原生/混合 App 做出技術選型、驗證主要風險，並提供可執行的 POC 路徑與時間估算。

概覽
- 目前專案主要為 Python Web 應用／微服務（見 `WebUI` 與 `MCP` 等模組）。
- 目標優先順序：桌面（Windows/macOS/Linux）→ 若需則支援行動（Android/iOS）。

候選技術（重點比較）
- Electron
  - 優點：成熟、生態完整（打包、更新、原生模組）、開發週期短、Node 生態豐富。
  - 缺點：應用體積大、記憶體消耗較高。
  - 適用情境：需要快速產出桌面 App、團隊熟悉 JS/Node、生態需求多。
- Tauri
  - 優點：二進位體積小、較低的記憶體使用、較佳的安全性模型（基於 Rust）、可與外部二進位溝通。
  - 缺點：較新的技術、若需擴展 Rust 層有學習成本；與 Python 後端整合需設計啟動與 IPC 模式。
  - 適用情境：對體積與安全性有高要求，且團隊願意處理 Rust 工具鏈。
- Capacitor（或 Cordova）
  - 優點：以 Web 技術快速包裝移動 App，較少變動前端。
  - 缺點：原生能力有限；桌面支援不如 Electron / Tauri。
  - 適用情境：以現有 Web 前端快速導向行動平台。
- React Native / Flutter
  - 優點：專為行動設計，原生 UI 體驗好（Flutter 跨平台表現佳）。
  - 缺點：需要重寫大量前端；開發成本高。
  - 適用情境：若重視行動原生體驗且願意投入重寫成本。

推薦（初期策略）
- 桌面優先：使用 Electron 作為第一版 POC 與開發流程（快速、風險低）。
- 長期優化：若二進位體積與記憶體為關鍵指標，可在 Phase 2/3 評估以 Tauri 重寫包裝層。
- 行動選項：若需行動原生體驗，採雙路徑：短期採 Capacitor/PWA 快速上線；長期採 React Native 或 Flutter 重構。

架構建議（桌面路徑，Electron POC）
- 組件
  - 前端 Renderer：現有 `WebUI` 前端靜態資源（或打包後的 SPA）由 Electron 加載。
  - 主進程（Main）：負責原生 API、打包配置、啟動/管理背景服務。
  - 背景服務（Python）：保留現有 Python 服務（例如 `app.py` / MCP 模組），以獨立進程啟動。
  - 通訊：Renderer ↔ Background via HTTP on localhost、Unix socket 或 IPC（建議先用 localhost + token）。

- 啟動流程（建議 POC 實作）
  1. Electron 主進程啟動。
  2. 檢查/啟動 Python 背景服務（spawn 子進程），或在系統服務模式下檢查是否已在執行。
  3. Renderer 載入本地網頁並用本地 API token 與背景服務通訊。

安全性與權限
- 本地服務應只綁定本機回環介面（127.0.0.1 / unix socket），並使用短期 token 或 API key 防止外部濫用。
- 關閉 CORS 或只允許內部請求來源。
- 對敏感資料加密儲存（例如 token 使用 OS 抽象的安全儲存：Keychain / DPAPI / Secret Service）。

打包與發佈考量
- Electron：使用 `electron-builder` 或 `electron-forge` 打包，支援 Windows installer、macOS dmg、Linux AppImage/deb。
- Tauri：使用 `tauri-bundler`（需 Rust 工具鏈），可得到更小的二進位檔。

相依性與開發環境
- Node.js 與 npm/yarn（Electron/Capacitor 工具鏈）
- Python 3.x 與專案相依套件（可用 venv/venv 管理）
- Rust 工具鏈（僅當採用 Tauri）

POC 建議（最小可驗證原型）
- 目標：建立一個 Electron 應用，可啟動本地 Python 背景服務並在 Renderer 顯示一個簡單頁面，能呼叫背景服務的 API 並顯示回應。
- 成功標準：能在 Windows/macOS/Linux 上啟動並完成一個 API round-trip（Renderer → local API → 回應），且可確認本地只對回環地址監聽。

時間估算（Phase 1 規格與 POC）
- 技術選型與設計文件：3–7 天
- POC（Electron + Python background）實作：5–10 天
- 技術審查與修正：2–4 天

主要風險與緩解策略
- 風險：Python 背景服務與包裝層的啟動/升級管理複雜。
  - 緩解：在 POC 階段實作啟動守護邏輯與版本檢查；清楚定義升級策略（內嵌 vs 外部安裝）。
- 風險：安全性 — 本地 HTTP 接口暴露風險。
  - 緩解：限制回環介面、短期 token、再加上本機存取控制與監控。
- 風險：二進位體積/記憶體。
  - 緩解：初期使用 Electron 快速驗證，若需優化再考慮 Tauri。

驗收條件（Phase 1 完成）
- 技術比對文件與選型理由完成並獲利害關係人確認。
- POC 成功運作：Electron 啟動 + Python 背景服務啟動 + API round-trip。
- 列出接下來 Phase 2 的技術任務與時間估算。

下一步（建議）
- 我可以為你：
  - 產出 POC 的最小實作範例（Electron 主進程 + spawn Python），或
  - 產出 Tauri 路徑的對比 POC 計畫，讓你評估是否要為小體積/安全做投資。
