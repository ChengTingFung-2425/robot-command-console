# Phase 4 — 封裝、簽署與發佈管線

> **建立日期**: 2026-02-04  
> **狀態**: 📋 規劃中  
> **預估時間**: 1–4 週  
> **前置條件**: Phase 3.2 完成

---

## 📋 總覽

Phase 4 的目標是建立可重複的打包與發佈流程，支援跨平台部署（Windows、macOS、Linux）。

### 核心目標

1. **自動化 CI/CD**: GitHub Actions 工作流程自動化構建、測試、打包
2. **跨平台打包**: 為每個平台生成可安裝的發佈包
3. **程式碼簽署**: macOS 和 Windows 平台的程式碼簽署
4. **版本管理**: 自動化版本號管理和 release notes 生成
5. **發佈流程**: 自動上傳至 GitHub Releases

---

## 📦 待辦事項清單

### 1. CI/CD 基礎設施 (10 項)

#### GitHub Actions 工作流程
- [ ] 建立 `build.yml` - 主要構建工作流程
- [ ] 建立 `release.yml` - 發佈工作流程
- [ ] 建立 `package.yml` - 打包工作流程
- [ ] 設定跨平台構建矩陣（Windows/macOS/Linux）
- [ ] 配置 Python 3.11+ 環境
- [ ] 配置 Node.js LTS 環境（如需要）

#### 自動化測試
- [ ] 整合單元測試到 CI
- [ ] 整合整合測試到 CI
- [ ] 設定測試覆蓋率報告
- [ ] 配置測試失敗時的通知機制

### 2. 打包配置 (15 項)

#### PyQt6 應用打包 (Tiny Version)
- [ ] 完善 PyInstaller 配置 (`Edge/qtwebview-app/build.spec`)
- [ ] 配置 Windows 打包（.exe + NSIS 安裝程式）
- [ ] 配置 macOS 打包（.app bundle + DMG）
- [ ] 配置 Linux 打包（AppImage）
- [ ] 優化打包大小（排除不必要的依賴）
- [ ] 配置圖示和資源檔案
- [ ] 測試打包後的應用程式

#### Docker 映像
- [ ] 完善 Dockerfile（生產環境版本）
- [ ] 配置 Docker Compose（多服務編排）
- [ ] 建立 Docker Hub / GitHub Container Registry 發佈流程
- [ ] 優化映像大小（multi-stage build）
- [ ] 添加健康檢查和日誌配置

#### Electron 應用打包 (Heavy Version，如適用)
- [ ] 配置 electron-builder
- [ ] 配置 Windows 打包
- [ ] 配置 macOS 打包
- [ ] 配置 Linux 打包

### 3. 程式碼簽署 (8 項)

#### macOS 簽署
- [ ] 申請 Apple Developer ID
- [ ] 配置 Xcode 命令列工具
- [ ] 設定 codesign 簽署流程
- [ ] 設定 notarization（公證）流程
- [ ] 測試簽署後的應用程式

#### Windows 簽署
- [ ] 申請 EV Code Signing Certificate
- [ ] 配置 SignTool
- [ ] 設定簽署流程
- [ ] 測試簽署後的應用程式

### 4. 版本管理 (6 項)

- [ ] 統一版本號管理機制（`version.py`）
- [ ] 設定語義化版本控制（Semantic Versioning）
- [ ] 配置自動版本號遞增
- [ ] 建立 CHANGELOG.md 自動生成
- [ ] 建立 Release Notes 模板
- [ ] 配置 Git tags 自動建立

### 5. 發佈流程 (8 項)

#### GitHub Releases
- [ ] 配置自動發佈到 GitHub Releases
- [ ] 上傳各平台打包檔案
- [ ] 自動生成 release notes
- [ ] 設定 pre-release 和 stable release 標記

#### 套件管理器（可選）
- [ ] Windows: Chocolatey / Winget
- [ ] macOS: Homebrew
- [ ] Linux: PPA / Snap / Flatpak
- [ ] Python: PyPI（如適用）

### 6. 文件與指南 (8 項)

- [ ] 撰寫構建指南（BUILD.md）
- [ ] 撰寫發佈流程文件（RELEASE.md）
- [ ] 撰寫貢獻者指南（CONTRIBUTING.md）
- [ ] 更新安裝說明（各平台）
- [ ] 建立故障排除指南
- [ ] 建立簽署憑證取得指南
- [ ] 建立 CI/CD 維護文件
- [ ] 更新 README.md 添加安裝徽章

### 7. 品質保證 (6 項)

- [ ] 各平台安裝測試（手動）
- [ ] 應用程式啟動測試
- [ ] 基本功能冒煙測試
- [ ] 驗證簽署和憑證
- [ ] 驗證打包大小符合目標
- [ ] 驗證相依性正確包含

---

## 🎯 驗收標準

### 必須達成

1. ✅ **自動化 CI/CD**
   - GitHub Actions 自動構建、測試、打包
   - 測試覆蓋率報告可見
   - 構建失敗時有通知

2. ✅ **跨平台打包**
   - Windows: 可執行的 .exe 和 NSIS 安裝程式
   - macOS: .app bundle 和 DMG
   - Linux: AppImage（至少）
   - 所有打包檔案 < 100MB（Tiny版本 < 60MB）

3. ✅ **程式碼簽署**（至少 macOS 或 Windows 其中之一）
   - macOS: 簽署和公證完成
   - Windows: 使用有效的 EV 憑證簽署

4. ✅ **版本管理**
   - 版本號自動遞增
   - CHANGELOG.md 自動生成
   - Git tags 正確建立

5. ✅ **發佈流程**
   - 自動上傳至 GitHub Releases
   - Release notes 完整
   - 各平台下載連結可用

### 效能目標

- CI/CD 構建時間 < 15 分鐘
- 打包時間 < 5 分鐘/平台
- 打包大小:
  - Tiny版本: < 60MB
  - Heavy版本: < 150MB
  - Docker映像: < 200MB (壓縮後)

---

## 🛠️ 技術規格

### PyInstaller 配置範例

```python
# build.spec
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('static', 'static'),
    ],
    hiddenimports=[
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebChannel',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'numpy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)
```

### electron-builder 配置範例

```json
{
  "build": {
    "appId": "com.robotconsole.edge",
    "productName": "Robot Command Console",
    "directories": {
      "output": "dist"
    },
    "files": [
      "dist/**",
      "py-service/**"
    ],
    "mac": {
      "category": "public.app-category.developer-tools",
      "target": ["dmg", "zip"],
      "icon": "resources/icon.icns"
    },
    "win": {
      "target": ["nsis", "portable"],
      "icon": "resources/icon.ico"
    },
    "linux": {
      "target": ["AppImage", "deb"],
      "category": "Development"
    }
  }
}
```

### GitHub Actions 工作流程範例

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    
    runs-on: ${{ matrix.os }}
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pyinstaller
      
      - name: Build application
        run: pyinstaller build.spec
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: ${{ matrix.os }}-build
          path: dist/
```

---

## 📊 實作順序建議

### Week 1: CI/CD 基礎
- 建立 GitHub Actions 工作流程
- 整合測試
- 設定跨平台構建矩陣

### Week 2: 打包配置
- 完善 PyInstaller 配置
- 配置各平台打包
- 優化打包大小

### Week 3: 簽署與發佈
- 申請憑證
- 配置簽署流程
- 建立發佈流程

### Week 4: 測試與文件
- 各平台測試
- 撰寫文件
- 完成驗收

---

## 🔗 相關資源

### 工具文件
- [PyInstaller 文件](https://pyinstaller.readthedocs.io/)
- [electron-builder 文件](https://www.electron.build/)
- [GitHub Actions 文件](https://docs.github.com/actions)
- [Apple Code Signing Guide](https://developer.apple.com/support/code-signing/)
- [Windows Code Signing](https://docs.microsoft.com/en-us/windows/win32/seccrypto/cryptography-tools)

### 專案文件
- [MASTER_PLAN.md](MASTER_PLAN.md) - 總體計劃
- [Phase 3.2 計劃](../phase3/PHASE3_2_QTWEBVIEW_PLAN.md) - 前置 Phase
- [architecture.md](../architecture.md) - 架構文件

---

## 📝 備註

### 憑證申請

**macOS:**
- 需要加入 Apple Developer Program（年費 $99 USD）
- 申請需時 1-3 個工作天
- 公證流程需要額外設定

**Windows:**
- EV Code Signing Certificate 費用約 $200-$500 USD/年
- 申請需要企業驗證（2-7 個工作天）
- 需要 USB Token 或 HSM

### 替代方案

如果無法取得簽署憑證：
1. 提供未簽署版本，並註明安全說明
2. 使用開源簽署服務（如 SignPath）
3. 先發佈 Linux 版本（不需簽署）
4. 使用 Docker 發佈（不需簽署）

---

**最後更新**: 2026-02-04  
**負責人**: DevOps Team  
**審閱者**: TBD
