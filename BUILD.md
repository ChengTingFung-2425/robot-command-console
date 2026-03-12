# 構建指南

本文件說明如何從原始碼構建 Robot Command Console。

## 系統需求

### 開發環境

- **Python**: 3.11 或更高版本
- **Node.js**: 18 LTS 或更高版本（如需 Electron 版本）
- **Git**: 最新版本

### 作業系統

- **Linux**: Ubuntu 22.04+ 或其他現代 Linux 發行版
- **Windows**: Windows 10/11
- **macOS**: macOS 12 (Monterey) 或更高版本

## 快速開始

### 1. 取得原始碼

```bash
git clone https://github.com/ChengTingFung-2425/robot-command-console.git
cd robot-command-console
```

### 2. 建立 Python 虛擬環境

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate     # Windows
```

### 3. 安裝依賴

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install pyinstaller pillow  # 打包工具
```

### 4. 執行測試

```bash
# 設定 PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"  # Linux/macOS
# 或
set PYTHONPATH=%PYTHONPATH%;%CD%\src         # Windows

# 執行測試
python -m pytest tests/ -v
```

### 5. 開發模式執行

```bash
# 執行 Tiny Edge App
python Edge/qtwebview-app/main.py

# 或執行 Flask 服務
python flask_service.py
```

## 打包應用程式

### Linux 快速打包（推薦）

使用 `scripts/build-linux.sh` 可一鍵完成兩種 Linux 打包格式：

```bash
# 打包所有格式（AppImage + Binary tar.gz）
./scripts/build-linux.sh

# 僅打包 Electron AppImage
./scripts/build-linux.sh --appimage

# 僅打包 PyInstaller Binary tar.gz
./scripts/build-linux.sh --binary

# 顯示幫助
./scripts/build-linux.sh --help
```

**輸出檔案：**

| 檔案 | 說明 |
|------|------|
| `dist/RobotConsole-linux.AppImage` | Electron 應用，支援大多數 Linux 發行版，無需安裝 |
| `dist/RobotConsole-linux.tar.gz` | PyQt6 應用二進位包，解壓後直接執行 |

**前置需求：**
- AppImage：Node.js >= 18、npm
- Binary tar.gz：Python >= 3.11、pip

---

### Windows 快速打包（推薦）

使用 `scripts/build-windows.ps1` 可一鍵完成 Windows 打包（需安裝 [NSIS 3.x](https://nsis.sourceforge.io/)）：

```powershell
# 打包所有格式（PyInstaller NSIS + Electron NSIS）
.\scripts\build-windows.ps1

# 只打包 PyInstaller NSIS 安裝程式
.\scripts\build-windows.ps1 -Target nsis

# 只打包 Electron NSIS 安裝程式
.\scripts\build-windows.ps1 -Target electron

# 顯示幫助
.\scripts\build-windows.ps1 -Help
```

**輸出檔案：**

| 檔案 | 說明 |
|------|------|
| `dist\RobotConsole-Setup-3.2.0.exe` | PyQt6 應用 NSIS 安裝程式（建議使用） |
| `dist\RobotConsole-Electron-Setup-*.exe` | Electron 應用 NSIS 安裝程式 |

**前置需求：**
- NSIS Installer：[NSIS 3.x](https://nsis.sourceforge.io/)、Python >= 3.11、pip
- Electron NSIS：Node.js >= 18、npm

---

### PyQt6 應用（Tiny版本）

#### 前置準備

1. 建立啟動畫面圖片：
```bash
python Edge/qtwebview-app/resources/images/create_splash_image.py
```

2. 檢查版本資訊：
```bash
python src/common/version.py
```

#### 執行打包

```bash
pyinstaller Edge/qtwebview-app/build.spec
```

打包完成後，可執行檔位於 `dist/RobotConsole/` 目錄。

#### 平台特定說明

**Linux:**
```bash
# 安裝系統依賴
sudo apt-get install -y \
    libxcb-xinerama0 libxcb-cursor0 libxkbcommon-x11-0 \
    libgl1-mesa-glx libdbus-1-3 libegl1

# 打包
pyinstaller Edge/qtwebview-app/build.spec

# 建立 tarball
cd dist
tar -czf RobotConsole-linux.tar.gz RobotConsole/
```

**Windows:**
```powershell
# 打包
pyinstaller Edge/qtwebview-app/build.spec

# 建立 NSIS 安裝程式（需安裝 NSIS 3.x）
# 下載：https://nsis.sourceforge.io/
Push-Location Edge\qtwebview-app
makensis installer.nsi
Pop-Location
# 輸出：dist\RobotConsole-Setup-3.2.0.exe

# 或建立 ZIP（不需 NSIS）
cd dist
Compress-Archive -Path 'RobotConsole' -DestinationPath 'RobotConsole-windows.zip' -Force
```

#### Windows 一鍵打包腳本

```powershell
# 同時打包 PyInstaller NSIS 和 Electron NSIS
.\scripts\build-windows.ps1

# 只打包 PyInstaller NSIS 安裝程式
.\scripts\build-windows.ps1 -Target nsis

# 只打包 Electron NSIS 安裝程式
.\scripts\build-windows.ps1 -Target electron
```

**輸出檔案：**

| 檔案 | 說明 |
|------|------|
| `dist\RobotConsole-Setup-3.2.0.exe` | PyQt6 應用 NSIS 安裝程式（建議使用） |
| `dist\RobotConsole-windows.zip` | PyQt6 應用 ZIP（免安裝） |
| `dist\RobotConsole-Electron-Setup-*.exe` | Electron 應用 NSIS 安裝程式 |

**macOS:**
```bash
# 打包
pyinstaller Edge/qtwebview-app/build.spec

# 建立 tarball
cd dist
tar -czf RobotConsole-macos.tar.gz RobotConsole.app/
```

### 驗證打包結果

```bash
# 檢查檔案大小
ls -lh dist/RobotConsole/

# 執行打包後的應用（Linux/macOS）
./dist/RobotConsole/RobotConsole

# 執行打包後的應用（Windows）
.\dist\RobotConsole\RobotConsole.exe
```

## Docker 構建

### 構建映像

```bash
docker build -t robot-console:latest .
```

### 執行容器

```bash
docker-compose up -d
```

## 自動化構建（CI/CD）

專案使用 GitHub Actions 進行自動化構建：

- **build.yml**: 每次 push 或 PR 時自動重用 `scripts/build-linux.sh`、`scripts/build-windows.ps1`、`scripts/build-macos.sh` 進行跨平台打包
- **release.yml**: 標籤觸發時自動重用相同腳本建立 Release 資產

### CI/CD 打包輸出

| 平台 | CI/CD 腳本 | 主要輸出 |
|------|-----------|----------|
| Linux | `scripts/build-linux.sh` | `dist/RobotConsole-linux.AppImage`、`dist/RobotConsole-linux.tar.gz` |
| Windows | `scripts/build-windows.ps1` | `dist/RobotConsole-Setup-*.exe`、`dist/RobotConsole-Electron-Setup-*.exe` |
| macOS | `scripts/build-macos.sh` | `dist/RobotConsole-macos.tar.gz` |

如需在本地驗證 CI/CD 打包腳本與 workflow 設定，可執行：

```bash
PYTHONPATH="${PWD}/src" python -m pytest \
  tests/edge/test_edge_packaging.py \
  tests/edge/test_windows_installer.py \
  tests/edge/test_macos_packaging.py \
  tests/edge/test_packaging_workflows.py -q
```

> 此指令用於跨平台打包設定驗證；若只需驗證單一平台，可比照 `build.yml` 僅執行對應的測試檔。

### 觸發構建

```bash
# 本地測試構建工作流程
act -j build  # 需要安裝 act 工具
```

### 建立 Release

```bash
# 1. 更新版本號
vim src/common/version.py

# 2. 更新 CHANGELOG
vim CHANGELOG.md

# 3. 建立並推送標籤
git tag -a v3.2.0 -m "Release v3.2.0"
git push origin v3.2.0
```

## 優化建議

### 減小打包大小

1. **排除不必要的模組**（已在 build.spec 配置）：
   - matplotlib, scipy, numpy
   - tensorflow, torch
   - tkinter, wx

2. **使用 UPX 壓縮**（已啟用）

3. **移除偵錯符號**：
   ```python
   strip=True  # 在 build.spec 中設定
   ```

### 提升啟動速度

1. **使用 OneDirBuild**（目前配置）
2. **優化導入**：移除不必要的全域導入
3. **延遲載入**：僅在需要時導入大型模組

## 疑難排解

### 常見問題

**Q: PyInstaller 找不到模組**
```bash
# 確認 PYTHONPATH 設定正確
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"

# 清理快取重新打包
rm -rf build/ dist/
pyinstaller --clean Edge/qtwebview-app/build.spec
```

**Q: 打包後執行失敗**
```bash
# 查看詳細錯誤訊息
./dist/RobotConsole/RobotConsole --debug

# 檢查依賴
ldd ./dist/RobotConsole/RobotConsole  # Linux
otool -L ./dist/RobotConsole.app/Contents/MacOS/RobotConsole  # macOS
```

**Q: 圖片或資源檔案遺失**
```bash
# 確認 datas 配置正確（build.spec）
# 手動複製資源檔案到 dist/
cp -r Edge/qtwebview-app/resources dist/RobotConsole/
```

### 取得協助

- 檢查 [FAQ](docs/FAQ.md)
- 回報 [Issue](https://github.com/ChengTingFung-2425/robot-command-console/issues)
- 查看 [疑難排解指南](docs/TROUBLESHOOTING.md)

## 延伸閱讀

- [PyInstaller 官方文件](https://pyinstaller.readthedocs.io/)
- [Phase 4 計劃](docs/plans/PHASE4_PACKAGING_PLAN.md)
- [架構文件](docs/architecture.md)
- [開發指南](docs/development/)

---

**最後更新**: 2026-02-04  
**維護者**: Robot Command Console Team
