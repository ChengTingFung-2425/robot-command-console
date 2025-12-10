# Tiny 版本安裝指引

> **最後更新**：2025-12-10  
> **適用版本**：v1.0.0+

---

## 系統需求

### 最低需求

- **作業系統**：Windows 10/11, macOS 12+, Ubuntu 20.04+, Debian 11+
- **記憶體**：2GB RAM
- **磁碟空間**：100MB 可用空間
- **處理器**：任何現代 x64 或 ARM64 處理器

### 建議規格

- **記憶體**：4GB+ RAM
- **磁碟空間**：500MB+ 可用空間（含資料庫）

---

## Windows 安裝

### 1. 下載安裝包

前往 [GitHub Releases](https://github.com/ChengTingFung-2425/robot-command-console/releases)

下載：`robot-command-console-tiny-v1.0.0-win-x64.exe`

### 2. 執行安裝程式

1. 雙擊 `.exe` 檔案
2. 如果出現 Windows Defender 警告，點擊「更多資訊」→「仍要執行」
3. 依照安裝精靈指示完成安裝
4. 選擇安裝路徑（預設：`C:\Program Files\TinyEdgeApp`）
5. 選擇是否建立桌面捷徑

### 3. 首次啟動

1. 從開始選單或桌面捷徑啟動應用程式
2. 首次啟動會自動初始化資料庫
3. 等待服務就緒（約 5-10 秒）
4. 瀏覽器視窗自動開啟

---

## macOS 安裝

### 1. 下載安裝包

前往 [GitHub Releases](https://github.com/ChengTingFung-2425/robot-command-console/releases)

- Intel Mac：`robot-command-console-tiny-v1.0.0-mac-x64.dmg`
- Apple Silicon：`robot-command-console-tiny-v1.0.0-mac-arm64.dmg`

### 2. 安裝應用程式

1. 開啟 `.dmg` 檔案
2. 將 `TinyEdgeApp.app` 拖曳至「應用程式」資料夾
3. 首次啟動時，按住 `Control` 點擊應用程式，選擇「打開」
4. 在安全性提示中點擊「打開」

### 3. 允許網路連線

首次啟動時，macOS 會詢問是否允許網路連線，請點擊「允許」。

---

## Linux 安裝

### 方法 1：AppImage（推薦）

1. 下載 AppImage：
```bash
wget https://github.com/ChengTingFung-2425/robot-command-console/releases/download/v1.0.0/robot-command-console-tiny-v1.0.0-linux-x64.AppImage
```

2. 賦予執行權限：
```bash
chmod +x robot-command-console-tiny-v1.0.0-linux-x64.AppImage
```

3. 執行：
```bash
./robot-command-console-tiny-v1.0.0-linux-x64.AppImage
```

### 方法 2：從原始碼執行

1. 複製儲存庫：
```bash
git clone https://github.com/ChengTingFung-2425/robot-command-console.git
cd robot-command-console
```

2. 安裝依賴：
```bash
pip install -r requirements.txt
pip install -r qtwebview-app/requirements.txt
```

3. 執行應用程式：
```bash
python qtwebview-app/main.py
```

---

## 首次設定

### 1. 建立管理員帳號

首次啟動會引導您建立管理員帳號：

1. 輸入使用者名稱
2. 輸入電子郵件
3. 設定密碼（至少 8 個字元）
4. 確認密碼

### 2. 配置 LLM 提供商（可選）

如果您想使用 AI 功能：

1. 前往「設定」→「LLM 設定」
2. 選擇提供商：
   - **Ollama**（本地）
   - **LM Studio**（本地）
   - **OpenAI**（雲端）
3. 配置 API 金鑰或本地服務地址

### 3. 連接機器人

1. 前往「機器人」頁面
2. 點擊「新增機器人」
3. 輸入機器人資訊：
   - 名稱
   - IP 地址
   - 連接埠
   - 協定類型
4. 測試連線
5. 儲存

---

## 常見問題

### Q: 啟動失敗，顯示「埠號被佔用」

**A:** 預設埠號 5100-5199 可能被其他應用程式使用。應用程式會自動尋找可用埠號，請稍候片刻重試。

### Q: 視窗空白或無法載入

**A:** 
1. 檢查防火牆設定，確保允許應用程式網路連線
2. 嘗試重新啟動應用程式
3. 查看日誌檔案：`logs/tinyedgeapp.log`

### Q: macOS 提示「無法打開，因為它來自未識別的開發者」

**A:** 
1. 按住 `Control` 點擊應用程式
2. 選擇「打開」
3. 在彈出視窗點擊「打開」

### Q: Linux 缺少依賴庫

**A:** 安裝必要的系統套件：
```bash
# Ubuntu/Debian
sudo apt-get install libxcb-xinerama0 libxcb-cursor0

# Fedora
sudo dnf install xcb-util-cursor
```

### Q: 如何更新到新版本？

**A:** 
1. 下載最新版本的安裝包
2. 關閉舊版本應用程式
3. 安裝新版本（會自動覆蓋舊版本）
4. 資料庫和設定會自動保留

---

## 解除安裝

### Windows

1. 前往「設定」→「應用程式」
2. 搜尋「TinyEdgeApp」
3. 點擊「解除安裝」

### macOS

1. 開啟「應用程式」資料夾
2. 將「TinyEdgeApp.app」拖曳至垃圾桶
3. 清空垃圾桶

### Linux

直接刪除 AppImage 檔案即可。

---

## 取得協助

- **文件**：[docs/](https://github.com/ChengTingFung-2425/robot-command-console/tree/main/docs)
- **問題回報**：[GitHub Issues](https://github.com/ChengTingFung-2425/robot-command-console/issues)（請標註 `[Tiny]`）
- **討論區**：[GitHub Discussions](https://github.com/ChengTingFung-2425/robot-command-console/discussions)

---

**下一步**：閱讀 [Tiny vs Heavy 版本對比](TINY_VS_HEAVY.md) 了解更多差異
