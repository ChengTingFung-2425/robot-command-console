# Phase 1（Electron）— 精煉計畫

目的：基於會議決議使用 Electron，將 Phase 1 規劃細化為可執行任務、時間估算、負責人建議與驗收條件，為 POC 與接下來的模組化工作做準備。

目標（Phase 1）
- 快速建立 Electron POC：Electron 啟動 + 本地 Python 背景服務啟動 + API round-trip。
- 定義開發環境、打包流程與基本安全策略（local-only、token）。
- 產出可交付文件：開發上手、打包說明、Python 整合與安全文件。

主要任務與估時（小型團隊）
1. 技術選型與架構確認 — 1 天
   - 完成架構圖（Renderer/Main/Background）、通訊方式（HTTP on localhost / unix socket）與安全要求。
2. 開發環境與 POC scaffold — 2–4 天
   - 建立 Electron 專案（使用 electron-forge / electron-builder 範本）。
   - 實作主進程啟動 Python 背景服務（spawn）與 health-check。
   - 實作簡單 Renderer，呼叫 local API 並顯示結果。
3. 打包與本地發佈測試 — 2–4 天
   - 使用 `electron-builder` 建立各平台開發包（至少完成一平台 end-to-end）。
   - 撰寫簽章/安裝器備註（若 target macOS 或 Windows）。
4. 文件產出（並行） — 2–3 天
   - `electron-dev-setup.md`、`electron-packaging.md`、`electron-python-integration.md`。
5. 技術審查與風險緩解 — 1–2 天
   - 審查 POC，列出 Phase 2 的重構/模組化任務。

負責人建議
- 技術負責：前端工程師 + 後端（Python）工程師配合（spawn / 升級策略）。
- 文件：由開發負責初稿，Tech Lead 審核。

交付物（Phase 1 完成時）
- Electron POC 程式碼（包含主進程、最小 Renderer、Python 背景服務範例）
- 三份文件：`electron-dev-setup.md`、`electron-packaging.md`、`electron-python-integration.md`
- 技術審查回報與 Phase 2 任務清單

驗收標準
- POC 在至少一平台可啟動並完成 Renderer → local API → 回應的 round-trip。
- 所有文件能讓新工程師依照指引在同一開發環境中啟動 POC。

風險與緩解
- 啟動/升級管理複雜：實作版本檢查與啟動守護邏輯，並在文件說明內嵌 vs 系統服務的差異。
- 安全性：預設本地回環綁定，短期 token，並在文件列出如何使用系統級安全存儲（Keychain/DPAPI）。

時間表（建議短期排程）
- Week 0（會議確認）: 本文件確認與任務分配
- Week 1: 技術選型、POC scaffold
- Week 2: 完成 POC、打包測試、文件初稿
- Week 3: 技術審查、修正、列出 Phase 2 任務
