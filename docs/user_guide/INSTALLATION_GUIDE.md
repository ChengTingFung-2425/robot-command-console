# 完整安裝指南

> **最後更新**：2026-01-05  
> **適用版本**：v1.0.0+

本指南整合所有版本的安裝說明，幫助您選擇並安裝適合的 Robot Command Console 版本。

---

## 📋 目錄

- [版本選擇](#版本選擇)
- [系統需求](#系統需求)
- [Heavy 版本安裝](#heavy-版本安裝)
- [Tiny 版本安裝](#tiny-版本安裝)
- [TUI 版本安裝](#tui-版本安裝)
- [首次設定](#首次設定)
- [常見問題](#常見問題)

---

## 版本選擇

### 快速比較

| 特性 | Heavy (Electron) | Tiny (PyQt) | TUI (終端) |
|------|------------------|-------------|------------|
| **安裝包大小** | ~150-300MB | ~40-60MB | ~10MB |
| **記憶體佔用** | ~300-500MB | ~150-250MB | ~50-100MB |
| **啟動速度** | 2-5 秒 | 1-3 秒 | <1 秒 |
| **圖形介面** | ✅ React UI | ✅ Web UI | ❌ 純文字 |
| **開發工具** | ✅ 完整 | ⚠️ 有限 | ❌ 無 |
| **適用場景** | 開發/測試 | 生產環境 | 伺服器/SSH |

### 選擇建議

**選擇 Heavy** 如果您：
- 是開發者或進階使用者
- 需要完整的開發工具
- 硬體資源充足（RAM ≥ 4GB）

**選擇 Tiny** 如果您：
- 在生產環境部署
- 資源受限（RAM < 4GB）
- 需要穩定可靠的運行
- 在邊緣運算設備上使用

**選擇 TUI** 如果您：
- 在無頭伺服器運行
- 透過 SSH 遠端管理
- 只需要指令執行功能

---

## 系統需求

### 最低需求

| 組件 | 需求 |
|------|------|
| **作業系統** | Windows 10/11, macOS 12+, Ubuntu 20.04+, Debian 11+ |
| **記憶體** | 2GB RAM（Heavy需4GB+） |
| **磁碟空間** | 500MB 可用空間 |
| **處理器** | 任何現代 x64 或 ARM64 處理器 |
| **Python** | 3.10+ （從原始碼安裝時） |

### 建議規格

- **記憶體**：4GB+ RAM
- **磁碟空間**：1GB+ 可用空間（含資料庫）
- **網路**：可連接機器人的網路

---

## Heavy 版本安裝

### Windows

**方法 1：安裝包（推薦）**

1. 前往 [GitHub Releases](https://github.com/ChengTingFung-2425/robot-command-console/releases)
2. 下載 `robot-command-console-heavy-v1.0.0-win-x64.exe`
3. 雙擊執行，點擊「更多資訊」→「仍要執行」（如有 Windows Defender 警告）
4. 依照安裝精靈完成

**方法 2：從原始碼**

```powershell
# 1. 安裝 Node.js 和 Python 3.10+
# 2. 克隆倉庫
git clone https://github.com/ChengTingFung-2425/robot-command-console.git
cd robot-command-console

# 3. 安裝依賴
npm install
pip install -r requirements.txt

# 4. 啟動
npm start
```

### macOS

**方法 1：安裝包（推薦）**

1. 下載對應的 DMG：
   - Intel Mac：`robot-command-console-heavy-v1.0.0-mac-x64.dmg`
   - Apple Silicon：`robot-command-console-heavy-v1.0.0-mac-arm64.dmg`
2. 開啟 DMG，拖曳到「應用程式」資料夾
3. 首次啟動：按住 `Control` 點擊 → 「打開」

**方法 2：從原始碼**

```bash
# 1. 安裝 Homebrew（如果還沒有）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 安裝依賴
brew install node python@3.11

# 3. 克隆並安裝
git clone https://github.com/ChengTingFung-2425/robot-command-console.git
cd robot-command-console
npm install
pip3 install -r requirements.txt

# 4. 啟動
npm start
```

### Linux

**從原始碼安裝**

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install nodejs npm python3 python3-pip python3-venv git

# Fedora/RHEL
sudo dnf install nodejs npm python3 python3-pip git

# 克隆並安裝
git clone https://github.com/ChengTingFung-2425/robot-command-console.git
cd robot-command-console
npm install
pip3 install -r requirements.txt

# 啟動
npm start
```

---

## Tiny 版本安裝

### Windows

1. 前往 [GitHub Releases](https://github.com/ChengTingFung-2425/robot-command-console/releases)
2. 下載 `robot-command-console-tiny-v1.0.0-win-x64.exe`
3. 雙擊執行安裝程式
4. 選擇安裝路徑（預設：`C:\Program Files\TinyEdgeApp`）
5. 從開始選單啟動

### macOS

1. 下載對應的 DMG：
   - Intel Mac：`robot-command-console-tiny-v1.0.0-mac-x64.dmg`
   - Apple Silicon：`robot-command-console-tiny-v1.0.0-mac-arm64.dmg`
2. 開啟 DMG，拖曳到「應用程式」資料夾
3. 首次啟動：按住 `Control` 點擊 → 「打開」

### Linux

**方法 1：AppImage（推薦）**

```bash
# 下載 AppImage
wget https://github.com/ChengTingFung-2425/robot-command-console/releases/download/v1.0.0/robot-command-console-tiny-v1.0.0-linux-x64.AppImage

# 賦予執行權限
chmod +x robot-command-console-tiny-v1.0.0-linux-x64.AppImage

# 執行
./robot-command-console-tiny-v1.0.0-linux-x64.AppImage
```

**方法 2：從原始碼**

```bash
# 安裝依賴
sudo apt-get install python3 python3-pip python3-venv libxcb-xinerama0 libxcb-cursor0 libqt5webengine5

# 克隆並安裝
git clone https://github.com/ChengTingFung-2425/robot-command-console.git
cd robot-command-console
pip3 install -r requirements.txt
pip3 install -r qtwebview-app/requirements.txt

# 啟動
python3 qtwebview-app/main.py
```

---

## TUI 版本安裝

TUI 版本無需安裝包，直接從原始碼運行。

### 所有平台

```bash
# 1. 克隆倉庫
git clone https://github.com/ChengTingFung-2425/robot-command-console.git
cd robot-command-console

# 2. 建立虛擬環境（推薦）
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 啟動 TUI
python3 run_tui.py
```

📖 **詳細 TUI 使用**：見 [TUI 使用指南](TUI_USER_GUIDE.md)

---

## 首次設定

### 1. 建立管理員帳號

首次啟動時會提示建立管理員帳號：

- **使用者名稱**：登入帳號
- **電子郵件**：用於重設密碼
- **密碼**：至少 8 個字元（建議包含大小寫字母和數字）

### 2. 連接機器人（可選）

如果您有實體機器人：

1. 前往「機器人」頁面
2. 點擊「新增機器人」
3. 填寫資訊：
   - 名稱：識別名稱（例如：robot-001）
   - IP 地址：機器人網路位址
   - 埠號：通訊埠（預設：8080）
   - 協定：HTTP / MQTT / WebSocket
4. 測試連線後儲存

### 3. 配置 LLM（可選）

如需 AI 輔助功能：

1. 前往「設定」→「LLM 設定」
2. 選擇提供商：
   - **Ollama**（本地，免費）
   - **LM Studio**（本地，免費）
   - **OpenAI**（雲端，需 API 金鑰）
3. 配置連線資訊
4. 測試連線

---

## 常見問題

### Q: 無法啟動，顯示「埠號被佔用」

**A:** 預設埠號可能被其他程式使用。

**解決方法**：

```bash
# 檢查佔用的埠號
# Linux/macOS
lsof -i :5000
lsof -i :8000

# Windows
netstat -ano | findstr :5000

# 使用環境變數指定其他埠號
export FLASK_PORT=5001
export MCP_PORT=8001
export WEBUI_PORT=8081
```

### Q: macOS 提示「無法打開，因為來自未識別的開發者」

**A:** 這是 macOS Gatekeeper 的安全機制。

**解決步驟**：
1. 按住 `Control` 點擊應用程式
2. 選擇「打開」
3. 在彈出視窗點擊「打開」確認

或使用終端機：
```bash
sudo xattr -rd com.apple.quarantine /Applications/TinyEdgeApp.app
```

### Q: Linux 缺少依賴庫

**A:** 安裝必要的系統套件：

```bash
# Ubuntu/Debian
sudo apt-get install libxcb-xinerama0 libxcb-cursor0 libqt5webengine5

# Fedora
sudo dnf install xcb-util-cursor qt5-qtwebengine

# Arch
sudo pacman -S qt5-webengine
```

### Q: 如何更新到新版本？

**A:** 

**安裝包版本**：
1. 下載最新版本安裝包
2. 關閉舊版本
3. 安裝新版本（自動覆蓋）
4. 資料庫和設定自動保留

**原始碼版本**：
```bash
# 備份資料
cp -r data/ data.backup/

# 拉取最新程式碼
git pull origin main

# 更新依賴
npm install
pip install -r requirements.txt --upgrade

# 重新啟動
npm start  # 或對應的啟動指令
```

### Q: 支援哪些作業系統？

**A:** 

| 作業系統 | Heavy | Tiny | TUI |
|----------|-------|------|-----|
| **Windows 10/11** | ✅ | ✅ | ✅ |
| **macOS 12+** | ✅ | ✅ | ✅ |
| **Ubuntu 20.04+** | ✅ | ✅ | ✅ |
| **Debian 11+** | ✅ | ✅ | ✅ |
| **Fedora 35+** | ✅ | ✅ | ✅ |

**架構支援**：
- x64 (Intel/AMD) ✅
- ARM64 (Apple Silicon, Raspberry Pi) ✅

---

## 解除安裝

### Windows

1. 前往「設定」→「應用程式」
2. 搜尋應用程式名稱
3. 點擊「解除安裝」

### macOS

1. 開啟「應用程式」資料夾
2. 將應用程式拖曳至垃圾桶
3. 清空垃圾桶

### Linux

- **AppImage**：直接刪除檔案
- **從原始碼**：刪除克隆的目錄

---

## 取得協助

- **完整文件**：[用戶指南索引](USER_GUIDE_INDEX.md)
- **快速入門**：[QUICK_START.md](QUICK_START.md)
- **問題回報**：[GitHub Issues](https://github.com/ChengTingFung-2425/robot-command-console/issues)
- **社群討論**：[GitHub Discussions](https://github.com/ChengTingFung-2425/robot-command-console/discussions)

---

**下一步**：閱讀 [快速入門指南](QUICK_START.md) 開始使用

**最後更新**：2026-01-05
