# Phase 1 執行待辦（可操作步驟）

此清單將 Phase 1 的目標拆解成短小、可執行的任務，每項任務包含預估時間與建議負責人，方便直接指派與執行。

- [ ] 12. 建立 `electron-app` scaffold — 4 小時
  - 預估：4 小時
  - 負責人：前端工程師
  - 工作內容：建立 `electron-app/` 目錄、初始化 `package.json`、新增 `main.js`、`renderer/index.html` 與基本 `npm start`。

- [ ] 13. 實作主進程（spawn Python + health-check） — 1 天
  - 預估：1 天
  - 負責人：前端工程師 + Python 工程師（協作）
  - 工作內容：在 `main.js` 實作 spawn Python 子進程、health-check 循環、崩潰處理（有限次重啟）與 app quit 時清理。

- [ ] 15. 建立 Python 範例服務（`py-service/app.py`） — 4 小時
  - 預估：4 小時
  - 負責人：Python 工程師
  - 工作內容：使用 Flask 或 FastAPI 建一個簡單 `GET /health` 與 `GET /ping` 回傳 JSON 範例。

- [ ] 14. 實作 Renderer 與 API 呼叫範例 — 4 小時
  - 預估：4 小時
  - 負責人：前端工程師
  - 工作內容：在 `renderer/index.html` 或小型 SPA 中實作 fetch 到 `http://127.0.0.1:PORT/ping` 並在畫面顯示回應。

- [ ] 16. 本地測試與驗證 round-trip — 0.5–1 天
  - 預估：0.5–1 天
  - 負責人：前端 + Python 工程師
  - 工作內容：啟動 Electron 與 Python，完成至少 3 次 round-trip，檢查錯誤日誌。

- [ ] 17. 量測 KPI 並記錄結果（`phase-1-results.md`） — 0.5 天
  - 預估：0.5 天
  - 負責人：前端工程師
  - 工作內容：測量啟動時間、API round-trip 平均延遲、記憶體使用量，將數據寫入結果檔並標註執行環境。

- [ ] 19. 建立 CI 範例：build & packaging 測試 — 1–2 天
  - 預估：1–2 天
  - 負責人：DevOps / 前端工程師
  - 工作內容：建立 CI job（或示例 shell script），在 runner 上執行 `npm ci && npm run build && npx electron-builder`（至少一平台）。

- [ ] 18. 撰寫技術審查報告並列出 Phase 2 任務 — 1 天
  - 預估：1 天
  - 負責人：Tech Lead
  - 工作內容：整理 POC 結果、KPI 是否達成、列出 Phase 2 的重構/模組化任務並估時優先順序。

註：每項任務完成後，請把檔案或程式碼推到分支 `feature/electron-poc` 並建立 PR，PR 描述中包含測試步驟與測量數據。
