# Tiny Edge App (PyQt + QtWebView + Flask)

輕量版機器人指令控制台 - 基於 PyQt6 + QtWebEngine + Flask

## 專案目標

提供一個輕量、快速啟動的桌面應用程式，適合資源受限的邊緣設備。

## 與 Heavy 版本對比

| 特性 | Heavy (Electron) | Tiny (PyQt) |
|------|------------------|-------------|
| 安裝包大小 | ~150-300MB | ~40-60MB |
| 記憶體佔用 | ~300-500MB | ~150-250MB |
| 啟動速度 | 2-5 秒 | 1-3 秒 |
| UI 框架 | React | Jinja2 Templates |

## 快速開始

### 安裝依賴

```bash
# 安裝 PyQt 依賴
pip install -r qtwebview-app/requirements.txt

# 安裝主專案依賴
pip install -r requirements.txt
```

### 執行應用

```bash
python qtwebview-app/main.py
```

### 打包應用

```bash
cd qtwebview-app/build
python build.py
```

## 目錄結構

```
qtwebview-app/
├── main.py                 # 主程式入口
├── webview_window.py       # QtWebEngineView 封裝
├── flask_manager.py        # Flask 服務管理器
├── bridge.py               # QWebChannel JS-Python 橋接
├── system_tray.py          # 系統托盤
├── resources/              # 圖示與資源
├── requirements.txt        # PyQt 依賴
└── build/                  # 打包配置
    ├── build.py
    ├── windows.spec
    ├── macos.spec
    └── linux.spec
```

## 開發指引

詳見：[PHASE3_2_QTWEBVIEW_PLAN.md](../docs/phase3/PHASE3_2_QTWEBVIEW_PLAN.md)

## 授權

與主專案相同
