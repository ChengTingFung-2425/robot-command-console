# Phase 3.2 — QtWebView (PyQt) 輕量版本規劃

> **狀態**：📝 規劃中  
> **建立日期**：2025-12-10  
> **最後更新**：2025-12-10  
> **前置條件**：Phase 3.1 完成

---

## 目錄

1. [專案目標](#專案目標)
2. [雙版本策略](#雙版本策略)
3. [架構設計](#架構設計)
4. [技術選型](#技術選型)
5. [實作階段](#實作階段)
6. [打包與發布](#打包與發布)
7. [使用者指引](#使用者指引)
8. [完成定義](#完成定義)

---

## 專案目標

### 核心願景

建立一個基於 PyQt+QtWebView+Flask 的輕量版 Edge App (Tiny)，與現有 Electron+React 版本 (Heavy) 並行發布，讓使用者可根據需求選擇合適的版本。

### 主要目標

1. **降低資源需求**：Tiny 版本記憶體佔用 < 200MB，安裝包 < 50MB
2. **簡化部署**：單一執行檔，無需安裝 Node.js 或其他執行環境
3. **跨平台支援**：Windows/macOS/Linux 統一打包方案
4. **功能完整**：保留核心功能，與 Heavy 版本 API 相容
5. **雙版本並行**：使用者可自由選擇，不互相衝突

### 非目標

- ❌ 不替代 Heavy 版本（兩者並行）
- ❌ 不實作複雜的前端互動（保持簡單）
- ❌ 不引入新的後端依賴（重用現有 Flask 架構）

---

## 雙版本策略

### 版本對比

| 特性 | Heavy (Electron) | Tiny (PyQt) | 說明 |
|------|------------------|-------------|------|
| **安裝包大小** | ~150-300MB | ~40-60MB | Tiny 無需打包 Node.js 執行環境 |
| **記憶體佔用** | ~300-500MB | ~150-250MB | Tiny 使用系統原生 WebView |
| **啟動速度** | 2-5 秒 | 1-3 秒 | Tiny 啟動更快 |
| **前端框架** | React | Flask Jinja2 Templates | Tiny 使用伺服器端渲染 |
| **WebView** | Chromium (內嵌) | QtWebEngine (系統) | Tiny 重用系統 WebView |
| **熱重載** | ✅ 支援 | ❌ 不支援 | Heavy 更適合開發 |
| **進階 UI** | ✅ 豐富互動 | ⚠️ 基礎功能 | Heavy 提供更好的 UX |
| **開發工具** | ✅ DevTools | ⚠️ 有限 | Heavy 更適合除錯 |
| **更新機制** | ✅ 自動更新 | ✅ 自動更新 | 兩者皆支援 |
| **離線支援** | ✅ 完整 | ✅ 完整 | 兩者皆支援 |
| **適用場景** | 開發、進階使用者 | 生產、資源受限環境 | - |

### 使用者選擇指引

**選擇 Heavy (Electron) 版本如果：**
- ✅ 需要豐富的前端互動體驗
- ✅ 開發或測試環境
- ✅ 硬體資源充足（>4GB RAM）
- ✅ 需要完整的開發者工具

**選擇 Tiny (PyQt) 版本如果：**
- ✅ 資源受限環境（低記憶體設備）
- ✅ 生產環境部署
- ✅ 需要快速啟動
- ✅ 只需要核心功能

---

## 架構設計

### 系統架構

```
┌────────────────────────────────────────────────────────────────────┐
│                     Tiny Version (PyQt)                             │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │              PyQt6 主視窗 (Main Window)                       │ │
│  │  • 應用程式生命週期管理                                       │ │
│  │  • 系統托盤圖示                                               │ │
│  │  • 原生選單                                                   │ │
│  └────────────────────────┬─────────────────────────────────────┘ │
│                           │                                         │
│  ┌────────────────────────┴─────────────────────────────────────┐ │
│  │           QtWebEngineView (WebView)                           │ │
│  │  • 載入本地 Flask UI                                          │ │
│  │  • QWebChannel 橋接 (JS ↔ Python)                             │ │
│  │  • Cookie/LocalStorage 管理                                   │ │
│  └────────────────────────┬─────────────────────────────────────┘ │
│                           │ HTTP (127.0.0.1:dynamic_port)         │
│  ┌────────────────────────┴─────────────────────────────────────┐ │
│  │              Flask 本地服務 (內嵌)                             │ │
│  │  • WebUI Blueprint (簡化版)                                   │ │
│  │  • 靜態資源本地化                                             │ │
│  │  • API 端點 (與 Heavy 版本相容)                               │ │
│  └────────────────────────┬─────────────────────────────────────┘ │
│                           │                                         │
│  ┌────────────────────────┴─────────────────────────────────────┐ │
│  │          Robot Service / MCP Core (共用)                      │ │
│  │  • 指令處理                                                   │ │
│  │  • LLM 整合                                                   │ │
│  │  • 佇列管理                                                   │ │
│  └───────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

### 目錄結構

```
robot-command-console/
├── qtwebview-app/                # Tiny 版本專用目錄
│   ├── main.py                   # PyQt 主程式
│   ├── webview_window.py         # QtWebEngineView 封裝
│   ├── flask_manager.py          # Flask 服務管理器
│   ├── bridge.py                 # QWebChannel 橋接
│   ├── system_tray.py            # 系統托盤
│   ├── resources/                # 圖示與資源
│   │   ├── icon.png
│   │   └── icon.ico
│   ├── requirements.txt          # PyQt 專用依賴
│   └── build/                    # PyInstaller 配置
│       ├── build.py              # 打包腳本
│       ├── windows.spec          # Windows 配置
│       ├── macos.spec            # macOS 配置
│       └── linux.spec            # Linux 配置
│
├── WebUI/                        # 現有 Flask WebUI (共用)
│   ├── app/
│   │   ├── routes_tiny.py        # Tiny 版本專用路由 (NEW)
│   │   ├── static_local/         # 本地化靜態資源 (NEW)
│   │   └── templates_tiny/       # Tiny 版本模板 (NEW)
│   └── ...
│
├── src/                          # 共用後端服務
│   ├── common/
│   ├── robot_service/
│   └── ...
│
└── docs/
    ├── phase3/
    │   └── PHASE3_2_QTWEBVIEW_PLAN.md  # 本文件
    └── user_guide/
        ├── TINY_VS_HEAVY.md      # 版本選擇指引 (NEW)
        └── TINY_INSTALL_GUIDE.md # Tiny 安裝指引 (NEW)
```

---

## 技術選型

### PyQt vs PySide

| 特性 | PyQt6 | PySide6 |
|------|-------|---------|
| **授權** | GPL / 商業授權 | LGPL | 
| **效能** | 略優 | 相近 |
| **社群支援** | 成熟 | 成長中 |
| **Qt 版本** | Qt 6.x | Qt 6.x |

**選擇**：**PyQt6**
- ✅ 更成熟的社群支援
- ✅ 更完整的文檔
- ✅ 本專案為開源專案，GPL 授權可接受

### WebView 選擇

| 方案 | 說明 | 優缺點 |
|------|------|--------|
| **QtWebEngineView** | Qt 基於 Chromium 的 WebView | ✅ 功能完整<br>⚠️ 較大 |
| **QWebView** (Qt5) | 舊版 WebKit-based | ❌ Qt6 已棄用 |

**選擇**：**QtWebEngineView** (PyQt6.QtWebEngineWidgets)
- ✅ Qt 6 官方推薦
- ✅ 支援現代 Web 標準
- ✅ 與 Chromium 行為一致

### 打包工具

| 工具 | 說明 | 適用性 |
|------|------|--------|
| **PyInstaller** | 主流 Python 打包工具 | ✅ 跨平台支援佳 |
| **Nuitka** | 編譯為 C/C++ | ⚠️ 編譯慢 |
| **cx_Freeze** | 另一打包工具 | ⚠️ 社群較小 |

**選擇**：**PyInstaller**
- ✅ 跨平台支援完整
- ✅ 社群活躍
- ✅ 支援 PyQt/QtWebEngine

---

## 實作階段

### Stage 1: PyQt 基礎殼程序 (2-3 天)

**目標**：建立基礎 PyQt 應用，載入本地 Flask 服務

#### 1.1 PyQt 主視窗

**檔案**：`qtwebview-app/main.py`

```python
#!/usr/bin/env python3
"""
Tiny Edge App - PyQt6 + Flask
主程式入口
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QCoreApplication

from webview_window import WebViewWindow
from flask_manager import FlaskManager


def main():
    # 設定應用程式資訊
    QCoreApplication.setOrganizationName("RobotCommandConsole")
    QCoreApplication.setApplicationName("TinyEdgeApp")
    
    app = QApplication(sys.argv)
    
    # 啟動 Flask 服務
    flask_manager = FlaskManager()
    flask_manager.start()
    
    # 建立主視窗
    window = WebViewWindow(flask_manager)
    window.show()
    
    # 事件循環
    exit_code = app.exec()
    
    # 清理
    flask_manager.stop()
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
```

#### 1.2 Flask 服務管理器

**檔案**：`qtwebview-app/flask_manager.py`

**功能**：
- 啟動 Flask 於隨機可用埠
- 健康檢查機制
- 優雅關閉

#### 1.3 WebView 視窗

**檔案**：`qtwebview-app/webview_window.py`

**功能**：
- QtWebEngineView 封裝
- 載入本地 Flask UI
- 基礎導航控制

#### 驗收標準
- [ ] PyQt 視窗正常啟動
- [ ] Flask 服務自動啟動於動態埠
- [ ] WebView 正確載入 Flask 首頁
- [ ] 應用程式可正常關閉

---

### Stage 2: Flask Blueprint 調整 (3-4 天)

**目標**：調整 WebUI 以支援 Tiny 版本，靜態資源本地化

#### 2.1 統一 UI 路徑

**變更**：
```python
# 現有路由: /
# Tiny 路由: /ui/  (統一前綴)
```

**檔案**：`WebUI/app/routes_tiny.py`

```python
from flask import Blueprint

bp_tiny = Blueprint('tiny', __name__, url_prefix='/ui')

@bp_tiny.route('/')
def home():
    """Tiny 版本首頁"""
    return render_template('tiny/home.html.j2')

@bp_tiny.route('/robots')
def robots():
    """機器人列表"""
    return render_template('tiny/robots.html.j2')

# ... 其他路由
```

#### 2.2 靜態資源本地化

**目標**：移除 CDN 依賴，所有資源打包至應用內

**變更清單**：
- ❌ 移除：Bootstrap CDN
- ❌ 移除：jQuery CDN
- ❌ 移除：Font Awesome CDN
- ✅ 新增：本地 Bootstrap 5.3
- ✅ 新增：本地 jQuery 3.7
- ✅ 新增：本地 Font Awesome 6.x

**目錄**：`WebUI/app/static_local/`
```
static_local/
├── css/
│   ├── bootstrap.min.css
│   ├── fontawesome.min.css
│   └── app.css
├── js/
│   ├── bootstrap.bundle.min.js
│   ├── jquery.min.js
│   └── app.js
└── fonts/
    └── (Font Awesome fonts)
```

#### 2.3 模板簡化

**目標**：建立 Tiny 專用模板，移除複雜互動

**檔案**：`WebUI/app/templates_tiny/`
```
templates_tiny/
├── base.html.j2          # 基礎模板 (本地資源)
├── home.html.j2          # 首頁
├── robots.html.j2        # 機器人列表
├── commands.html.j2      # 指令介面
└── settings.html.j2      # 設定
```

#### 驗收標準
- [ ] 所有頁面可離線載入
- [ ] 無 CDN 請求
- [ ] UI 保持基礎功能
- [ ] 與 Heavy 版本 API 相容

---

### Stage 3: QWebChannel 橋接 (3-4 天)

**目標**：實作 JS-Python 通訊，提供原生功能

#### 3.1 QWebChannel 設定

**檔案**：`qtwebview-app/bridge.py`

```python
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal


class NativeBridge(QObject):
    """JS-Python 橋接物件"""
    
    # 信號 (Python → JS)
    notificationReceived = pyqtSignal(str, str)
    
    @pyqtSlot(str, str, result=str)
    def showFileDialog(self, mode, filter):
        """原生檔案對話框"""
        # mode: 'open' / 'save'
        # filter: '*.json'
        pass
    
    @pyqtSlot(str, str)
    def showNotification(self, title, message):
        """原生系統通知"""
        pass
    
    @pyqtSlot(result=str)
    def getAppVersion(self):
        """取得應用程式版本"""
        return "1.0.0"
```

#### 3.2 前端整合

**檔案**：`WebUI/app/static_local/js/bridge.js`

```javascript
// QWebChannel 初始化
new QWebChannel(qt.webChannelTransport, function(channel) {
    window.nativeBridge = channel.objects.nativeBridge;
    
    // 註冊信號監聽
    nativeBridge.notificationReceived.connect(function(title, message) {
        console.log('Notification:', title, message);
    });
});

// 使用範例
async function selectFile() {
    const path = await nativeBridge.showFileDialog('open', '*.json');
    console.log('Selected:', path);
}
```

#### 3.3 功能清單

| 功能 | JS API | Python 實作 |
|------|--------|-------------|
| 檔案對話框 | `nativeBridge.showFileDialog()` | `QFileDialog` |
| 系統通知 | `nativeBridge.showNotification()` | `QSystemTrayIcon` |
| 應用版本 | `nativeBridge.getAppVersion()` | 讀取 `__version__` |
| 開啟外部連結 | `nativeBridge.openExternal()` | `QDesktopServices.openUrl()` |

#### 驗收標準
- [ ] QWebChannel 正確初始化
- [ ] JS 可呼叫 Python 函式
- [ ] Python 可發送信號至 JS
- [ ] 檔案對話框正常運作
- [ ] 系統通知正常顯示

---

### Stage 4: 系統托盤與選單 (1-2 天)

**目標**：提供系統托盤圖示與快速操作選單

#### 4.1 系統托盤

**檔案**：`qtwebview-app/system_tray.py`

```python
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QAction, QIcon


class SystemTray(QSystemTrayIcon):
    """系統托盤圖示"""
    
    def __init__(self, parent=None):
        icon = QIcon("resources/icon.png")
        super().__init__(icon, parent)
        
        # 建立選單
        menu = QMenu()
        
        # 顯示/隱藏視窗
        show_action = QAction("顯示", self)
        show_action.triggered.connect(self.show_window)
        menu.addAction(show_action)
        
        # 關於
        about_action = QAction("關於", self)
        about_action.triggered.connect(self.show_about)
        menu.addAction(about_action)
        
        menu.addSeparator()
        
        # 退出
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)
        
        self.setContextMenu(menu)
        self.show()
```

#### 驗收標準
- [ ] 托盤圖示正常顯示
- [ ] 選單可正常開啟
- [ ] 最小化至托盤
- [ ] 雙擊托盤開啟視窗

---

### Stage 5: 健康檢查與自動恢復 (2 天)

**目標**：確保 Flask 服務穩定運行

#### 5.1 健康檢查

**檔案**：`qtwebview-app/flask_manager.py` (擴充)

```python
import requests
from PyQt6.QtCore import QTimer


class FlaskManager:
    def __init__(self):
        self.health_check_timer = QTimer()
        self.health_check_timer.timeout.connect(self.check_health)
        self.health_check_timer.start(5000)  # 每 5 秒檢查
    
    def check_health(self):
        """健康檢查"""
        try:
            response = requests.get(
                f"http://127.0.0.1:{self.port}/health",
                timeout=2
            )
            if response.status_code != 200:
                self.restart()
        except requests.RequestException:
            self.restart()
    
    def restart(self):
        """重啟服務"""
        self.stop()
        self.start()
```

#### 驗收標準
- [ ] 定期健康檢查
- [ ] 服務異常自動重啟
- [ ] 重啟時 UI 顯示載入中
- [ ] 最多重試 3 次

---

### Stage 6: 打包與跨平台測試 (4-5 天)

**目標**：使用 PyInstaller 打包，支援三大平台

#### 6.1 PyInstaller 配置

**檔案**：`qtwebview-app/build/build.py`

```python
#!/usr/bin/env python3
"""
跨平台打包腳本
"""
import os
import sys
import platform
import subprocess


def build():
    system = platform.system()
    
    if system == 'Windows':
        spec = 'windows.spec'
    elif system == 'Darwin':
        spec = 'macos.spec'
    else:
        spec = 'linux.spec'
    
    cmd = ['pyinstaller', '--clean', spec]
    subprocess.run(cmd, check=True)


if __name__ == '__main__':
    build()
```

#### 6.2 Windows 配置

**檔案**：`qtwebview-app/build/windows.spec`

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['../main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../resources', 'resources'),
        ('../../WebUI/app/static_local', 'WebUI/app/static_local'),
        ('../../WebUI/app/templates_tiny', 'WebUI/app/templates_tiny'),
    ],
    hiddenimports=[
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebChannel',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TinyEdgeApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../resources/icon.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TinyEdgeApp',
)
```

#### 6.3 macOS 配置

**檔案**：`qtwebview-app/build/macos.spec`

```python
# 類似 windows.spec，但產生 .app bundle
# 並使用 .icns 圖示
```

#### 6.4 Linux 配置

**檔案**：`qtwebview-app/build/linux.spec`

```python
# 類似 windows.spec，產生 AppImage
# 或 .deb / .rpm 套件
```

#### 6.5 跨平台測試矩陣

| 平台 | 架構 | 測試項目 |
|------|------|---------|
| Windows 10/11 | x64 | 安裝、啟動、核心功能 |
| macOS 12+ | x64/ARM64 | 安裝、啟動、核心功能 |
| Ubuntu 20.04/22.04 | x64 | 安裝、啟動、核心功能 |
| Raspberry Pi OS | ARM64 | 安裝、啟動、核心功能 |

#### 驗收標準
- [ ] Windows 可執行檔正常運作
- [ ] macOS .app 正常運作
- [ ] Linux AppImage 正常運作
- [ ] 安裝包大小 < 60MB
- [ ] 記憶體佔用 < 250MB

---

## 打包與發布

### 版本命名

```
Heavy 版本: robot-command-console-heavy-v1.0.0-{platform}
Tiny 版本:  robot-command-console-tiny-v1.0.0-{platform}
```

### 發布檔案

**Heavy (Electron)**:
- `robot-command-console-heavy-v1.0.0-win-x64.exe` (Windows)
- `robot-command-console-heavy-v1.0.0-mac-x64.dmg` (macOS Intel)
- `robot-command-console-heavy-v1.0.0-mac-arm64.dmg` (macOS Apple Silicon)
- `robot-command-console-heavy-v1.0.0-linux-x64.AppImage` (Linux)

**Tiny (PyQt)**:
- `robot-command-console-tiny-v1.0.0-win-x64.exe` (Windows)
- `robot-command-console-tiny-v1.0.0-mac-x64.dmg` (macOS Intel)
- `robot-command-console-tiny-v1.0.0-mac-arm64.dmg` (macOS Apple Silicon)
- `robot-command-console-tiny-v1.0.0-linux-x64.AppImage` (Linux)

### GitHub Release 範本

```markdown
## Robot Command Console v1.0.0

### 🎉 雙版本發布

本次發布提供 **Heavy** 和 **Tiny** 兩個版本，請根據需求選擇：

#### Heavy (Electron) 版本
適合：開發、進階使用者、需要豐富 UI 互動

- ✅ React 前端
- ✅ 完整開發工具
- ⚠️ 較大的安裝包 (~150MB)

**下載**：
- [Windows (x64)](...)
- [macOS (Intel)](...)
- [macOS (Apple Silicon)](...)
- [Linux (x64)](...)

#### Tiny (PyQt) 版本
適合：生產環境、資源受限設備、快速部署

- ✅ 輕量化 (~50MB)
- ✅ 快速啟動
- ✅ 低記憶體佔用
- ⚠️ 基礎 UI

**下載**：
- [Windows (x64)](...)
- [macOS (Intel)](...)
- [macOS (Apple Silicon)](...)
- [Linux (x64)](...)

### 📚 文件
- [版本選擇指引](docs/user_guide/TINY_VS_HEAVY.md)
- [Tiny 安裝指引](docs/user_guide/TINY_INSTALL_GUIDE.md)
- [Heavy 安裝指引](docs/user_guide/HEAVY_INSTALL_GUIDE.md)

### 🐛 回報問題
請在問題標題中標註 `[Tiny]` 或 `[Heavy]` 以便快速定位。
```

---

## 使用者指引

### 版本選擇流程圖

```
          使用者需求
               │
               ▼
    ┌──────────────────────┐
    │ 資源是否受限？        │
    │ (RAM < 4GB)          │
    └─────┬──────────┬─────┘
          │          │
    Yes   │          │   No
          ▼          ▼
    ┌─────────┐  ┌─────────┐
    │  Tiny   │  │ 需要豐富 │
    │         │  │ UI 互動？│
    └─────────┘  └────┬────┘
                      │
                 Yes  │  No
                      ▼    ▼
                 ┌────────┬─────┐
                 │ Heavy  │Tiny │
                 └────────┴─────┘
```

### 安裝指引文件

**檔案**：`docs/user_guide/TINY_INSTALL_GUIDE.md`

**內容大綱**：
1. 系統需求
2. 下載步驟
3. 安裝步驟 (各平台)
4. 首次設定
5. 常見問題

**檔案**：`docs/user_guide/TINY_VS_HEAVY.md`

**內容大綱**：
1. 版本差異對比表
2. 使用場景建議
3. 效能比較
4. 功能對照表
5. 遷移指引

---

## 完成定義

### Stage 1 完成標準
- [ ] PyQt 主視窗可啟動
- [ ] Flask 服務自動啟動
- [ ] WebView 載入 Flask 首頁
- [ ] 應用程式可正常關閉

### Stage 2 完成標準
- [ ] 所有靜態資源本地化
- [ ] Tiny Blueprint 實作完成
- [ ] UI 路徑統一為 `/ui/*`
- [ ] 無 CDN 依賴

### Stage 3 完成標準
- [ ] QWebChannel 正確設定
- [ ] 檔案對話框功能正常
- [ ] 系統通知功能正常
- [ ] JS-Python 雙向通訊正常

### Stage 4 完成標準
- [ ] 系統托盤圖示顯示
- [ ] 托盤選單功能完整
- [ ] 最小化至托盤
- [ ] 雙擊托盤開啟視窗

### Stage 5 完成標準
- [ ] 健康檢查機制實作
- [ ] 服務異常自動重啟
- [ ] 重啟最多 3 次
- [ ] UI 顯示服務狀態

### Stage 6 完成標準
- [ ] PyInstaller 配置完成
- [ ] Windows 打包成功
- [ ] macOS 打包成功
- [ ] Linux 打包成功
- [ ] 跨平台測試通過

### 整體完成標準
- [ ] 雙版本皆可正常運作
- [ ] 文件完整 (安裝、選擇、FAQ)
- [ ] GitHub Release 發布
- [ ] 官網更新版本說明
- [ ] 所有測試通過

---

## 附錄

### A. 依賴清單

**檔案**：`qtwebview-app/requirements.txt`

```
# PyQt6 核心
PyQt6>=6.6.0
PyQt6-WebEngine>=6.6.0

# 打包工具
pyinstaller>=6.0.0

# 現有 Flask 依賴 (繼承)
Flask>=2.2.5
Werkzeug<3.0
# ... (其他 WebUI 依賴)
```

### B. 開發環境設定

```bash
# 建立虛擬環境
python -m venv venv_tiny

# 啟動虛擬環境
# Windows:
venv_tiny\Scripts\activate
# Linux/macOS:
source venv_tiny/bin/activate

# 安裝依賴
pip install -r qtwebview-app/requirements.txt
pip install -r requirements.txt

# 執行 Tiny 版本
python qtwebview-app/main.py
```

### C. 除錯技巧

```python
# 啟用 QtWebEngine 除錯
os.environ['QTWEBENGINE_REMOTE_DEBUGGING'] = '9222'

# 啟用詳細日誌
os.environ['QT_LOGGING_RULES'] = 'qt.webenginecontext.debug=true'
```

### D. 效能優化

1. **減少啟動時間**：
   - 延遲載入非核心模組
   - 使用 QSplashScreen 顯示載入畫面

2. **降低記憶體佔用**：
   - 限制 WebEngine 快取大小
   - 定期清理未使用的資源

3. **優化打包大小**：
   - 排除未使用的 Qt 模組
   - 壓縮靜態資源

---

**最後更新**：2025-12-10  
**版本**：v1.0  
**狀態**：📝 規劃完成，待實作
