# 比較：Electron 與 Tauri（以「規劃與文件」難易度為核心）

目的：從專案規劃、文件準備與維運角度，比較選用 Electron 或 Tauri 會帶來的文件工作量、痛點與風險緩解建議，協助 Phase 1/2 規劃時估算所需產出。

**重點結論（摘要）**
- Electron：規劃與文件難易度較低，因其生態成熟、工具與範例豐富，文件可重用性高；但需要額外文件來管理體積/記憶體與安全性策略。
- Tauri：文件工作量偏高（初期），需撰寫 Rust 層整合、Rust 工具鏈安裝、與本地二進位互動的操作文件；長期可減少打包優化文件，但初期學習曲線與文件撰寫成本較高。

---

## 一、文件面向分類（所有專案通用）
- 技術選型紀錄：選型理由、比較矩陣、風險評估。
- 架構文件：系統架構圖、啟動流程、組件角色（Renderer/Main/Background）。
- 開發環境與上手指南：安裝依賴、環境變數、Debug 流程。
- 打包/發佈文件：打包指令、簽署流程、平台差異與已知限制。
- 安全與權限：本地 API 暴露控管、儲存敏感資訊方式、權限範圍。
- CI/CD 與自動化：建置 pipeline、測試、發佈到內部 channel 的步驟。
- 運維與監控：更新策略、遙測/錯誤追蹤、升級回滾流程。

這些文件類別在選擇 Electron 或 Tauri 時都會被觸發，但每個選項在「內容深度」與「新增文件需求」上有差別。

---

## 二、Electron：文件重點與難易度
- 開發與上手文件：低難度。Node.js / npm 工具鏈普遍熟悉，範例、模板（electron-forge、electron-builder）與社群文章豐富，文件可快速套用。
- 打包與發佈：中等難度。需撰寫不同平台的打包與簽署步驟，但有成熟工具支援，文件重點會放在 `electron-builder` 配置與簽章流程範例。
- 與 Python 背景服務整合：中等難度。文件需說明如何 spawn/監控 Python 子進程、local API token 流程、以及開發與發佈下的差異（例如系統服務 vs 內嵌啟動）。
- 安全與限制：中等偏高。需要文件明確指定本機接口限制、CSP、及敏感資料儲存（Keychain/DPAPI）範例。
- 持續維運文件：低難度。升級/回滾、Electron 版本更新可依社群指南撰寫。

估算文件工作量（小型團隊、POC→MVP）：
- 技術選型 + 架構文件：1–3 天
- 開發環境與上手文件：0.5–1.5 天
- 打包/發佈步驟文件（含簽章）：2–4 天
- Python 整合與安全文件：1–3 天
- CI/CD 與運維說明：1–2 天

***小結***：Electron 在文件與規劃上落地快，初期成本低，容易為利益關係人審核；必要時再投資於優化與安全文件。

---

## 三、Tauri：文件重點與難易度
- 開發與上手文件：較高難度。需新增 Rust 工具鏈安裝（rustup、cargo）、Tauri CLI、以及與前端建置工具的整合步驟。文件需明確列出平台差異（特別是 macOS code signing 與 Linux target 設定）。
- 打包與發佈：較高難度。Tauri 產出的二進位與打包流程與 Electron 不同（需配置 tauri.conf.json、使用 tauri-bundler、Rust target），文件需覆蓋 Rust 交叉編譯與平台簽章的細節。
- 與 Python 背景服務整合：較高難度。Tauri 預期是輕量包裝前端並呼叫外部二進位，文件需說明如何啟動/管理外部 Python 服務（spawn 邏輯、權限、升級路徑），以及在 Rust 層與 Python 層通訊的範例（若使用 stdin/stdout、socket 或 HTTP）。
- 安全與限制：高難度。雖然 Tauri 給出較嚴格的安全模型，但文件必須明確描述命令暴露、允許的外部介面、以及如何配置 tauri 的 allowlist/ACL。
- 持續維運文件：中等到高。Rust 生態與 Tauri 的版本更新路徑需要文件化，團隊需能處理 Rust 相關問題。

估算文件工作量（小型團隊、POC→MVP）：
- 技術選型 + 架構文件：2–4 天
- 開發環境與上手文件（含 Rust 安裝教學）：2–5 天
- 打包/發佈步驟文件（含 cross-compile 與簽章）：3–7 天
- Python 整合與安全文件：2–5 天
- CI/CD 與運維說明：2–4 天

***小結***：Tauri 在長期帶來更小的二進位體積與潛在效能，但在「文件與規劃」上初期成本與難度明顯較高；若團隊未熟悉 Rust，建議在 Phase 1 採 Electron POC，再視情況投入 Tauri POC。

---

## 四、對文件規劃的具體建議（實務層面）
1. 初期（Phase 1）：以 Electron 作為快速 POC，撰寫最小集合文件：技術選型、POC 架構、開發上手、Python 整合指南、簡易打包流程。
2. 若要同時評估 Tauri：將 Tauri 列為並行 POC（小型試驗），但在文件上預留模組：`tauri-setup.md`、`tauri-packaging.md`、`tauri-rust-integration.md`，以便事後擴充。
3. 對於兩條路徑都要覆蓋的文件，建立模板（例如 `docs/templates/packaging.md`、`docs/templates/security.md`），能讓文件撰寫與審查更高效。
4. 明確分離「開發文件」與「發佈/運維文件」，分配不同擁有人（開發負責上手與 POC 文件，運維或負責人負責簽章與發佈流程文件）。

---

## 五、檢核清單（以文件為中心，交付驗收）
- [ ] 技術選型報告（含比較矩陣與風險評估）
- [ ] POC 架構圖與啟動流程文件
- [ ] 開發環境上手指引（包含 Node/Python、以及 Rust 若適用）
- [ ] Python 整合與本地 API 安全文件（token、socket、CORS）
- [ ] 打包/簽章/發佈步驟（至少一個平台能完成 end-to-end）
- [ ] CI/CD 範例 pipeline（建置 + 打包 + 發佈到內部 channel）
- [ ] 監控與錯誤追蹤文件（如何設定 Sentry 或其他工具）

---

## 六、建議的下一步（我可以幫你做）
- 產出 `electron` POC 的最小文件套件（`dev-setup.md`、`packaging.md`、`python-integration.md`），讓團隊能立刻跑起 POC。
- 或者：產出 `tauri` POC 的文件骨架（重點在 Rust 安裝、cross-compile 與 tauri-bundler 範例），用來評估文件工作量與風險。

請告訴我你要我先產出哪一套文件（Electron POC 文件或 Tauri POC 文件骨架），我會接著建立檔案並把 TODO 標記為完成。
