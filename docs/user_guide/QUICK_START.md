# 快速入門指南

> **最後更新**：2025-12-22  
> **預計閱讀時間**：5 分鐘  
> **適用版本**：v1.0.0+

歡迎使用 Robot Command Console！本指南將帶您快速完成安裝並開始使用。

---

## 🎯 第一步：選擇版本

Robot Command Console 提供三種使用方式：

| 版本 | 特點 | 適合對象 | 安裝難度 |
|------|------|----------|----------|
| **Heavy (Electron)** | 完整 UI、豐富互動 | 開發者、進階用戶 | ⭐⭐ |
| **Tiny (PyQt)** | 輕量快速、低資源 | 生產環境、邊緣設備 | ⭐ |
| **TUI (終端)** | 純文字介面、SSH 友善 | 伺服器管理員 | ⭐ |

> 💡 **不確定選哪個？** 查看 [版本對比指引](TINY_VS_HEAVY.md)

---

## 📦 安裝步驟

### 選項 A：Tiny 版本（推薦新手）

**Windows 用戶**

1. 下載安裝包：[Releases 頁面](https://github.com/ChengTingFung-2425/robot-command-console/releases)
2. 執行 `.exe` 安裝程式
3. 完成安裝精靈
4. 從開始選單啟動

**macOS 用戶**

1. 下載對應的 `.dmg` 檔案（Intel 或 Apple Silicon）
2. 開啟 DMG，拖曳到應用程式資料夾
3. 首次啟動：右鍵 → 「打開」

**Linux 用戶**

```bash
# 下載 AppImage
wget https://github.com/ChengTingFung-2425/robot-command-console/releases/latest/download/robot-command-console-tiny-linux-x64.AppImage

# 賦予執行權限
chmod +x robot-command-console-tiny-*.AppImage

# 執行
./robot-command-console-tiny-*.AppImage
```

> 📖 詳細安裝說明：[Tiny 安裝指引](TINY_INSTALL_GUIDE.md)

---

### 選項 B：Heavy 版本（開發者）

```bash
# 1. 克隆倉庫
git clone https://github.com/ChengTingFung-2425/robot-command-console.git
cd robot-command-console

# 2. 安裝依賴
npm install
pip install -r requirements.txt

# 3. 啟動應用
npm start
```

---

### 選項 C：TUI 版本（終端機）

```bash
# 1. 克隆倉庫並安裝依賴（同選項 B）
git clone https://github.com/ChengTingFung-2425/robot-command-console.git
cd robot-command-console
pip install -r requirements.txt

# 2. 啟動 TUI
python3 run_tui.py
```

> 📖 詳細 TUI 使用：[TUI 使用指南](TUI_USER_GUIDE.md)

---

## 🚀 首次啟動設定

### 1. 建立管理員帳號

首次啟動時會提示建立管理員帳號：

- **使用者名稱**：您的登入帳號
- **電子郵件**：用於重設密碼
- **密碼**：至少 8 個字元，建議包含大小寫字母和數字

### 2. 連接機器人（可選）

如果您有實體機器人：

1. 點擊「機器人」頁面
2. 點擊「新增機器人」按鈕
3. 填寫機器人資訊：
   - **名稱**：給機器人一個識別名稱
   - **IP 地址**：機器人的網路位址
   - **埠號**：通訊埠（預設：8080）
   - **協定**：HTTP / MQTT / WebSocket
4. 點擊「測試連線」確認連接
5. 儲存設定

### 3. 配置 LLM（可選，用於 AI 功能）

如果您想使用 AI 輔助功能：

1. 前往「設定」→「LLM 設定」
2. 選擇提供商：
   - **Ollama**（本地，免費）
   - **LM Studio**（本地，免費）
   - **OpenAI**（雲端，需 API 金鑰）
3. 依提供商填寫配置
4. 測試連線

---

## 📋 第一個指令

### WebUI / Heavy / Tiny 版本

1. 在側邊欄選擇「指令中心」
2. 選擇目標機器人
3. 在指令輸入框輸入動作，例如：`go_forward`
4. 點擊「執行」按鈕
5. 觀察執行結果

### TUI 版本

1. 在底部指令輸入框輸入：`go_forward`
2. 按下 `Enter` 鍵
3. 在指令歷史區域查看執行結果

### 常用基本指令

| 指令 | 說明 |
|------|------|
| `go_forward` | 向前移動 |
| `go_backward` | 向後移動 |
| `turn_left` | 左轉 |
| `turn_right` | 右轉 |
| `stand` | 站立姿勢 |
| `wave_hand` | 揮手 |

---

## ✅ 驗證安裝

執行以下檢查確認系統正常：

### 1. 檢查服務狀態

**WebUI / Heavy / Tiny**：
- 前往「系統狀態」頁面
- 確認所有服務顯示綠色 ✓

**TUI**：
- 左上角「Services」區塊應顯示：
  - ● MCP Service [running]
  - ● Flask API [running]
  - ● Queue Service [running]

### 2. 執行測試指令

試著執行 `stand` 指令，應該能看到：
- ✅ 指令已發送
- ✅ 執行狀態：成功
- ✅ 機器人回應

---

## 🎓 下一步學習

### 基礎功能

- 📖 [功能完整參考](FEATURES_REFERENCE.md) - 了解所有功能
- 📖 [WebUI 使用指南](WEBUI_USER_GUIDE.md) - Web 介面詳細說明

### 進階功能

- 🔧 [整合指南](../INTEGRATION_GUIDE.md) - 與其他系統整合
- 🔒 [API 安全指南](../security/api-security-guide.md) - API 使用與安全

### 問題排解

- ❓ [常見問題 FAQ](FAQ.md) - 常見問題解答
- 🛠️ [疑難排解指南](TROUBLESHOOTING.md) - 問題診斷

---

## 🆘 需要協助？

### 查找答案

1. **常見問題**：[FAQ](FAQ.md)
2. **疑難排解**：[TROUBLESHOOTING.md](TROUBLESHOOTING.md)
3. **文件搜尋**：在 [docs/](../) 目錄中搜尋關鍵字

### 獲得支援

- **GitHub Issues**：[回報問題](https://github.com/ChengTingFung-2425/robot-command-console/issues)
- **GitHub Discussions**：[社群討論](https://github.com/ChengTingFung-2425/robot-command-console/discussions)

---

## 🎉 恭喜！

您已經完成快速入門，可以開始使用 Robot Command Console 了！

**推薦接下來：**
1. 探索更多功能：[功能完整參考](FEATURES_REFERENCE.md)
2. 了解最佳實踐：查看各功能詳細指南
3. 加入社群：分享您的使用經驗

---

**回到索引**：[用戶指南索引](USER_GUIDE_INDEX.md)
