# 當前階段待辦事項（Phase 3.2 Stage 5-7 為主）

> **建立日期**：2025-12-22  
> **範圍**：Phase 3.2 及之前需要完成的任務  
> **總數**：162 個待辦事項  
> **Phase 3.2 狀態**：Stage 1-4 已完成（核心架構），Stage 5-7 進行中（整合測試與發布）  
> **已過濾**：排除 Phase 4、5、6 及歷史 Phase 1、2 的任務

---

## 📊 Phase 3.2 當前狀態

根據 [Phase 3.2 實作總結](docs/phase3/PHASE3_2_IMPLEMENTATION_SUMMARY.md)：

| 階段 | 任務 | 狀態 | 說明 |
|------|------|------|------|
| **Phase 1** | 規劃與文檔 | ✅ 100% | 完整規劃文件、使用者指引、架構文件 |
| **Phase 2** | PyQt 基礎架構 | ✅ 100% | PyQt6 + QtWebEngine 應用程式、Flask 管理器 |
| **Phase 3** | JS-PyQt 橋接 | ✅ 100% | QWebChannel 橋接、原生功能整合 |
| **Phase 4** | 打包配置 | ✅ 100% | PyInstaller 腳本與跨平台配置 |
| **Phase 5** | Flask Blueprint 調整 | ⏳ 0% | **當前優先級** - 靜態資源本地化、路由重構 |
| **Phase 6** | 整合測試 | ⏳ 0% | 整合測試、跨平台驗證、打包測試 |
| **Phase 7** | 發布準備 | ⏳ 0% | 文件完善、發布流程、CI/CD |

### 整體統計

| 優先級 | 數量 | 說明 |
|--------|------|------|
| 🔴 **關鍵** | 91 | Phase 3.2 Stage 5-7，必須完成 |
| 🟠 **重要** | 36 | Phase 3.1 後續和文件，應該完成 |
| 🟡 **相關** | 35 | WebUI 遷移分析，可選完成 |
| **總計** | **162** | - |

---

## 🔴 關鍵任務：Phase 3.2 Stage 5-7（91 項）

> **當前階段**：Phase 3.2 Stage 5-7  
> **前置完成**：Stage 1-4 已完成（核心架構：PyQt、Flask、橋接、打包配置）  
> **目標**：完成 Flask Blueprint 調整、整合測試、發布準備  
> **來源**：[Phase 3.2 規劃](docs/phase3/PHASE3_2_QTWEBVIEW_PLAN.md)、[實作總結](docs/phase3/PHASE3_2_IMPLEMENTATION_SUMMARY.md)

### 📋 Stage 5 — Flask Blueprint 調整（9 項）

**當前優先級：🔴 最高**  
**阻塞後續**：必須完成才能進行測試

根據 [Phase 3.2 實作總結](docs/phase3/PHASE3_2_IMPLEMENTATION_SUMMARY.md) Phase 5 定義：

#### Flask Blueprint 重構
- [ ] 建立 `WebUI/app/routes_tiny.py`
- [ ] 統一路由前綴 `/ui/`
- [ ] 建立 `templates_tiny/` 目錄
- [ ] 簡化模板（移除複雜互動）

#### 靜態資源本地化
- [ ] 下載 Bootstrap 5.3
- [ ] 下載 jQuery 3.7
- [ ] 下載 Font Awesome 6.x
- [ ] 配置本地靜態資源路徑
- [ ] 移除所有 CDN 依賴

---

### 🧪 Stage 6 — 整合測試與驗證（17 項）

**當前優先級：🟠 高**  
**依賴**：Stage 5 完成  
**目標**：驗證 Tiny 版本功能完整性與跨平台相容性

根據 [Phase 3.2 實作總結](docs/phase3/PHASE3_2_IMPLEMENTATION_SUMMARY.md) Phase 6 定義：

#### 整合測試（5 項）
- [ ] 測試 Flask 服務啟動
- [ ] 測試 WebView 載入
- [ ] 測試 QWebChannel 橋接
- [ ] 測試健康檢查機制
- [ ] 測試自動重啟功能

#### 跨平台驗證（5 項）
- [ ] Windows 10/11 測試
- [ ] macOS 12+ 測試（Intel）
- [ ] macOS 12+ 測試（Apple Silicon）
- [ ] Ubuntu 22.04 測試
- [ ] Raspberry Pi 測試

#### 打包測試（7 項）
- [ ] Windows 打包與安裝測試
- [ ] macOS .app bundle 測試
- [ ] Linux AppImage 測試
- [ ] 驗證安裝包大小（目標 < 60MB）
- [ ] 驗證記憶體佔用（目標 < 250MB）
- [ ] 驗證啟動速度（目標 < 3 秒）
- [ ] 驗證離線運作

---

### 📦 Stage 7 — 發布準備（8 項）

**當前優先級：🟡 中**  
**依賴**：Stage 6 完成  
**目標**：準備 Tiny 版本正式發布

根據 [Phase 3.2 實作總結](docs/phase3/PHASE3_2_IMPLEMENTATION_SUMMARY.md) Phase 7 定義：

#### 文件完善（4 項）
- [ ] 完善 FAQ.md
- [ ] 完善 TROUBLESHOOTING.md
- [ ] 完善 QUICK_START.md
- [ ] 完善 HEAVY_INSTALL_GUIDE.md

#### 發布流程（4 項）
- [ ] 準備 GitHub Release 說明
- [ ] 準備官網更新內容
- [ ] 建立 CI/CD 自動打包流程
- [ ] 測試自動更新機制

---

### ✅ 驗收標準（57 項）

**目標**：確保 Phase 3.2 達成目標  
**參考**：[Phase 3.2 規劃文件](docs/phase3/PHASE3_2_QTWEBVIEW_PLAN.md) 完成定義章節

這些驗收標準貫穿 Stage 5-7，用於驗證：
1. Tiny 版本功能完整性
2. 與 Heavy 版本的 API 相容性
3. 跨平台穩定性
4. 效能目標（安裝包 < 60MB，記憶體 < 250MB，啟動 < 3 秒）

#### Stage 1：基礎架構（4 項）
- [ ] PyQt 主視窗可啟動
- [ ] Flask 服務自動啟動
- [ ] WebView 載入 Flask 首頁
- [ ] 應用程式可正常關閉

#### Stage 2：靜態資源（4 項）
- [ ] 所有靜態資源本地化
- [ ] Tiny Blueprint 實作完成
- [ ] UI 路徑統一為 `/ui/*`
- [ ] 無 CDN 依賴

#### Stage 3：JS-Python 橋接（4 項）
- [ ] QWebChannel 正確設定
- [ ] 檔案對話框功能正常
- [ ] 系統通知功能正常
- [ ] JS-Python 雙向通訊正常

#### Stage 4：系統托盤（4 項）
- [ ] 系統托盤圖示顯示
- [ ] 托盤選單功能完整
- [ ] 最小化至托盤
- [ ] 雙擊托盤開啟視窗

#### Stage 5：健康檢查（4 項）
- [ ] 健康檢查機制實作
- [ ] 服務異常自動重啟
- [ ] 重啟最多 3 次
- [ ] UI 顯示服務狀態

#### Stage 6：打包（5 項）
- [ ] PyInstaller 配置完成
- [ ] Windows 打包成功
- [ ] macOS 打包成功
- [ ] Linux 打包成功
- [ ] 跨平台測試通過

#### 整體驗收（5 項）
- [ ] 雙版本皆可正常運作
- [ ] 文件完整（安裝、選擇、FAQ）
- [ ] GitHub Release 發布
- [ ] 官網更新版本說明
- [ ] 所有測試通過

#### 功能驗收（27 項）
- [ ] PyQt 視窗正常啟動
- [ ] Flask 服務自動啟動於動態埠
- [ ] WebView 正確載入 Flask 首頁
- [ ] 應用程式可正常關閉
- [ ] 所有頁面可離線載入
- [ ] 無 CDN 請求
- [ ] UI 保持基礎功能
- [ ] 與 Heavy 版本 API 相容
- [ ] QWebChannel 正確初始化
- [ ] JS 可呼叫 Python 函式
- [ ] Python 可發送信號至 JS
- [ ] 檔案對話框正常運作
- [ ] 系統通知正常顯示
- [ ] 托盤圖示正常顯示
- [ ] 選單可正常開啟
- [ ] 最小化至托盤
- [ ] 雙擊托盤開啟視窗
- [ ] 定期健康檢查
- [ ] 服務異常自動重啟
- [ ] 重啟時 UI 顯示載入中
- [ ] 最多重試 3 次
- [ ] Windows 可執行檔正常運作
- [ ] macOS .app 正常運作
- [ ] Linux AppImage 正常運作
- [ ] 安裝包大小 < 60MB
- [ ] 記憶體佔用 < 250MB
- [ ] 啟動速度 < 3 秒

---

## 🟠 重要任務：Phase 3.1 後續與文件（36 項）

> **Phase 3.1 狀態**：✅ 已完成（2025-12-04）  
> **當前需求**：完善後續工作，確保 Phase 3 整體品質  
> **來源**：[Phase 3.1 狀態報告](docs/phase3/PHASE3_1_STATUS_REPORT.md)

### Phase 3.1 後續工作（19 項）

**背景**：Phase 3.1 完成了統一啟動器、服務協調器和效能優化。以下是建議的後續改進任務。

來源：`docs/phase3/PHASE3_1_STATUS_REPORT.md` 下一步建議章節

#### 效能優化驗證
- [ ] 執行完整負載測試
- [ ] 驗證記憶體使用優化效果
- [ ] 驗證啟動時間改善
- [ ] 驗證服務協調器效能

#### 監控與日誌
- [ ] 完善 Prometheus metrics
- [ ] 實作關鍵路徑追蹤
- [ ] 優化日誌輸出
- [ ] 建立監控儀表板

#### 測試覆蓋
- [ ] 補充整合測試
- [ ] 補充端到端測試
- [ ] 補充效能測試
- [ ] 補充壓力測試

#### 文件更新
- [ ] 更新架構文件
- [ ] 更新 API 文件
- [ ] 更新部署指南
- [ ] 更新故障排除指南

#### 其他改進
- [ ] 錯誤處理完善
- [ ] 配置管理改進
- [ ] 安全性審查
- [ ] 程式碼品質檢查

---

### 架構改進（11 項）

**背景**：長期架構規劃，為未來 Phase 做準備  
**時機**：Phase 3.2 完成後考慮實施

來源：`docs/architecture.md` 未來發展章節

#### 核心功能
- [ ] WebUI 本地版完整實作
- [ ] 離線模式支援
- [ ] 雲端服務整合準備

#### 進階功能
- [ ] 分散式佇列（Redis/Kafka）規劃
- [ ] Kubernetes 部署規劃
- [ ] 多節點部署架構設計

#### 擴展性
- [ ] 更多機器人類型支援規劃
- [ ] 進階分析與報表設計
- [ ] 多租戶支援架構
- [ ] Cloud-Edge-Runner 架構完整規劃
- [ ] 擴展性測試

---

### TUI 用戶指南（6 項）

**背景**：TUI 功能已實作，需完善文件  
**目標**：提供完整的 TUI 使用指南

來源：`docs/user_guide/TUI_USER_GUIDE.md` 待完善章節

#### 文件完善
- [ ] 補充進階使用範例
- [ ] 補充鍵盤快捷鍵說明
- [ ] 補充配置選項說明
- [ ] 補充故障排除章節
- [ ] 補充常見問題 FAQ
- [ ] 補充視覺化截圖

---

## 🟡 相關任務：WebUI 遷移分析（35 項）

> **背景**：分析 WebUI 功能，確定 Tiny/Heavy 版本差異  
> **狀態**：分析文件，與 Phase 3.2 相關但非必要  
> **建議**：可選完成，有助於理解版本差異

來源：`docs/phase3/WEBUI_MIGRATION_ANALYSIS.md`

### 分析目標

此分析有助於：
1. 確定哪些 WebUI 功能適合 Tiny 版本
2. 確定哪些功能保留在 Heavy 版本
3. 制定模板簡化策略
4. 確保雙版本 API 相容性

### 功能評估（約 15 項）
- 評估 WebUI 各功能模組
- 確定哪些需要遷移到 Tiny 版本
- 確定哪些保留在 Heavy 版本

### 遷移策略（約 10 項）
- 制定模板簡化策略
- 制定路由整合方案
- 制定靜態資源處理方案

### 相容性測試（約 10 項）
- 測試 API 相容性
- 測試數據遷移
- 測試用戶體驗一致性

---

## 📝 執行建議（根據 Phase 目標）

### Phase 3.2 目標回顧

根據 [Phase 3.2 規劃](docs/phase3/PHASE3_2_QTWEBVIEW_PLAN.md)，Phase 3.2 的核心目標是：

1. **降低資源需求**：Tiny 版本記憶體 < 200MB，安裝包 < 50MB ✅ (已規劃)
2. **簡化部署**：單一執行檔，無需額外環境 ✅ (PyInstaller 已配置)
3. **跨平台支援**：Windows/macOS/Linux 統一方案 ⏳ (待測試)
4. **功能完整**：保留核心功能，API 相容 ⏳ (待驗證)
5. **雙版本並行**：使用者可自由選擇 ⏳ (待文件完善)

### 當前週期（本週）- Stage 5

**目標**：完成 Flask Blueprint 調整，解除測試阻塞

1. **立即開始**：
   - 建立 `WebUI/app/routes_tiny.py`
   - 下載並配置本地靜態資源（Bootstrap、jQuery、Font Awesome）
   - 統一路由前綴為 `/ui/`

2. **本週完成**：
   - 所有 Stage 5 任務（9 項）
   - 移除 CDN 依賴，確保離線運作

### 下一週期（下週）- Stage 6

**目標**：執行完整測試，驗證功能和效能

1. **整合測試**：
   - Flask 服務啟動測試
   - WebView 載入測試
   - QWebChannel 橋接測試

2. **跨平台驗證**：
   - Windows 10/11 測試
   - macOS（Intel + Apple Silicon）測試
   - Linux（Ubuntu 22.04）測試

3. **打包測試**：
   - 驗證安裝包大小、記憶體佔用、啟動速度

### 第三週期（第三週）- Stage 7

**目標**：完成發布準備，達成 Phase 3.2 目標

1. **文件完善**：
   - FAQ.md、TROUBLESHOOTING.md
   - QUICK_START.md、HEAVY_INSTALL_GUIDE.md

2. **發布流程**：
   - GitHub Release 準備
   - CI/CD 自動打包流程
   - 自動更新機制測試

3. **最終驗收**：
   - 逐項檢查 57 個驗收標準
   - 確保達成 Phase 3.2 所有目標

### 持續工作（並行進行）

**Phase 3.1 後續工作**（19 項）：
- 可與 Stage 5-7 並行
- 效能監控、測試覆蓋、文件更新

**架構改進**（11 項）：
- 長期規劃，Phase 3.2 後考慮
- 離線模式、雲端整合、分散式佇列

**TUI 用戶指南**（6 項）：
- 持續完善，不阻塞 Phase 3.2

---

## 🎯 Phase 3.2 成功標準

根據 [Master Plan](docs/plans/MASTER_PLAN.md) 和 [Phase 3.2 規劃](docs/phase3/PHASE3_2_QTWEBVIEW_PLAN.md)：

### 必須達成
1. ✅ PyQt + Flask 架構運作正常（已完成）
2. ✅ JS-Python 橋接功能正常（已完成）
3. ✅ 打包配置完成（已完成）
4. ⏳ 離線運作（無 CDN 依賴）- Stage 5 目標
5. ⏳ 跨平台穩定性 - Stage 6 目標
6. ⏳ 雙版本文件完整 - Stage 7 目標

### 效能目標
- 安裝包 < 60MB（目標 < 50MB）
- 記憶體 < 250MB（目標 < 200MB）
- 啟動時間 < 3 秒（目標 < 2 秒）

### 功能目標
- 與 Heavy 版本 API 相容
- 核心功能完整（Dashboard、Commands、Robots、Advanced）
- 原生功能整合（檔案對話框、系統通知、系統托盤）

---

## 🔗 相關文件

### Phase 3.2 核心文件
- **詳細規劃**：[docs/phase3/PHASE3_2_QTWEBVIEW_PLAN.md](docs/phase3/PHASE3_2_QTWEBVIEW_PLAN.md)
- **實作總結**：[docs/phase3/PHASE3_2_IMPLEMENTATION_SUMMARY.md](docs/phase3/PHASE3_2_IMPLEMENTATION_SUMMARY.md)
- **版本對比**：[docs/user_guide/TINY_VS_HEAVY.md](docs/user_guide/TINY_VS_HEAVY.md)

### Phase 3.1 相關文件
- **狀態報告**：[docs/phase3/PHASE3_1_STATUS_REPORT.md](docs/phase3/PHASE3_1_STATUS_REPORT.md)
- **測試計畫**：[docs/phase3/TEST_PLAN_PHASE3_1.md](docs/phase3/TEST_PLAN_PHASE3_1.md)

### 其他相關文件
- **架構說明**：[docs/architecture.md](docs/architecture.md)
- **WebUI 遷移**：[docs/phase3/WEBUI_MIGRATION_ANALYSIS.md](docs/phase3/WEBUI_MIGRATION_ANALYSIS.md)
- **TUI 指南**：[docs/user_guide/TUI_USER_GUIDE.md](docs/user_guide/TUI_USER_GUIDE.md)

---

## ⚠️ 重要提醒

### 已過濾的任務
以下類型的任務**不包含**在此文件中：
- ✅ **Phase 1, 2**：已完成的歷史 Phase
- ⏭️ **Phase 4, 5, 6**：未來 Phase 的計劃任務
- 📚 **歷史文件**：已歸檔的規劃與分析文件
- 🔵 **參考清單**：安全檢查清單等參考用途的待辦事項（112+ 項）

### 專注當前
本文件幫助團隊**專注於當前階段**（Phase 3.2）及**近期必須完成**的任務，避免被大量未來規劃分散注意力。

---

**最後更新**：2025-12-22  
**下次審查**：Phase 3.2 Stage 5 完成後
