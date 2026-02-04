# Unified Edge App

> **統一 Edge 應用程式** - 整合 WebUI/MCP/Robot-Console 為單一部署套件

---

## 📦 簡介

Unified Edge App 將三個核心模組整合為單一的本地應用程式：

- **MCP Service**: 指令處理、LLM 整合、插件系統
- **Robot-Console**: 動作執行、協定適配
- **Web Interface**: 本地管理介面（精簡版）

### 特點

✅ **一鍵啟動**: 單一命令啟動所有服務  
✅ **統一配置**: 單一配置檔案管理所有設定  
✅ **本地優先**: 完全本地運行，無需雲端依賴  
✅ **精簡高效**: 移除社群功能，專注機器人控制  
✅ **跨平台**: 支援 Windows、macOS、Linux  

---

## 🚀 快速開始

### 方式 1: Python 直接運行

```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 啟動應用
python -m unified-edge-app.core.launcher

# 或使用簡化命令
python run_unified_app.py
```

### 方式 2: Electron App (Heavy)

```bash
# 啟動 Electron 應用（自動啟動統一套件）
npm start
```

### 方式 3: PyQt App (Tiny)

```bash
# 啟動 PyQt 應用（自動啟動統一套件）
python qtwebview-app/main.py
```

---

## ⚙️ 配置

### 使用預設配置

無需額外配置即可啟動，使用預設設定：

- Flask API: `http://127.0.0.1:5000`
- MCP Service: `http://127.0.0.1:8000`
- 資料庫: SQLite（本地檔案）
- LLM Provider: Ollama（本地）

### 自訂配置

創建 `config.yaml` 檔案：

```yaml
app:
  name: "My Robot Console"
  mode: "edge"

mcp:
  host: "127.0.0.1"
  port: 8000
  enable_llm: true
  llm_provider: "ollama"  # ollama, lm-studio, cloud
  enable_plugins: true

robot_console:
  protocol: "queue"  # queue, mqtt, http
  enable_safety: true

web_interface:
  host: "127.0.0.1"
  port: 5000
  auth_mode: "local"  # local, none
  enable_blockly: true
  database: "sqlite:///my_edge_app.db"

logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  format: "json"
  output: "console"
```

啟動時指定配置：

```bash
python -m unified-edge-app.core.launcher --config config.yaml
```

### 環境變數

也可以使用環境變數覆寫配置：

```bash
export MCP_PORT=8001
export WEB_PORT=5001
export LOG_LEVEL=DEBUG

python -m unified-edge-app.core.launcher
```

---

## 🏗️ 架構

```
unified-edge-app/
├── core/                    # 核心啟動與配置
│   ├── launcher.py          # 統一啟動器
│   ├── config.py            # 配置管理
│   └── service_manager.py   # 服務協調
│
├── mcp/                     # MCP 服務（符號連結）
├── robot_console/           # Robot-Console（符號連結）
├── web_interface/           # Web 介面（精簡版）
└── shared/                  # 共用模組（符號連結）
```

### 服務整合方式

1. **MCP Service**: 複用現有 MCP 模組，透過本地埠號提供 API
2. **Robot-Console**: 複用現有執行器，透過本地佇列接收指令
3. **Web Interface**: 精簡版 WebUI，移除社群功能，保留核心控制

### 服務間通訊

```
Web Interface (Flask:5000)
         │
         │ HTTP REST API
         ↓
    MCP Service (FastAPI:8000)
         │
         │ 本地佇列
         ↓
    Robot-Console
         │
         │ 硬體介面
         ↓
      機器人
```

---

## 📚 Web Interface 功能

### 保留功能

✅ **機器人儀表板**: 查看所有機器人狀態  
✅ **指令控制中心**: 發送基本指令  
✅ **進階指令建立器**: 使用 Blockly 建立複雜指令序列  
✅ **執行監控**: 即時監控指令執行狀態  
✅ **機器人管理**: 註冊、配置機器人  
✅ **日誌查看**: 查看執行日誌  

### 移除功能

❌ 用戶註冊/登入系統（改為簡化的本地認證）  
❌ 討論區（Posts/Comments/Likes）  
❌ 排行榜  
❌ 社交互動（Follow/Followers）  
❌ 郵件通知  
❌ 雲端固件倉庫  

---

## 🔧 開發指南

### 專案結構

```
unified-edge-app/
├── __init__.py
├── README.md
├── requirements.txt
├── config.example.yaml
├── core/
│   ├── __init__.py
│   ├── launcher.py
│   ├── config.py
│   └── service_manager.py
├── mcp/ -> ../MCP/          # 符號連結
├── robot_console/ -> ../Robot-Console/
├── web_interface/
│   ├── __init__.py
│   ├── app.py
│   ├── routes/
│   │   ├── dashboard.py
│   │   ├── commands.py
│   │   ├── advanced.py
│   │   └── robots.py
│   └── templates/
└── shared/ -> ../src/common/
```

### 新增功能

1. **新增 Web 路由**: 在 `web_interface/routes/` 新增模組
2. **擴充 MCP 功能**: 在 `mcp/` 新增插件或處理器
3. **新增機器人協定**: 在 `robot_console/` 擴充適配器

### 測試

```bash
# 運行測試
python -m pytest tests/unified_edge_app/

# 整合測試
python -m pytest tests/test_e2e_integration.py
```

---

## 📦 打包與分發

### PyInstaller (單一執行檔)

```bash
# 安裝 PyInstaller
pip install pyinstaller

# 打包
pyinstaller unified_edge_app.spec

# 執行
dist/UnifiedEdgeApp/UnifiedEdgeApp
```

### Electron (桌面應用)

```bash
# 打包 Electron App
npm run build

# 輸出在 dist/ 目錄
```

### Docker

```bash
# 建立映像
docker build -t unified-edge-app:latest -f Dockerfile .

# 運行
docker run -p 5000:5000 -p 8000:8000 unified-edge-app:latest
```

---

## 🐛 疑難排解

### 服務啟動失敗

**問題**: "Failed to start any backend services"

**解決方式**:
1. 檢查埠號是否被佔用：`lsof -i :5000` 和 `lsof -i :8000`
2. 檢查依賴是否完整安裝：`pip install -r requirements.txt`
3. 查看詳細錯誤日誌

### 無法連接 MCP

**問題**: Web Interface 無法連接到 MCP

**解決方式**:
1. 確認 MCP 服務已啟動：`curl http://127.0.0.1:8000/health`
2. 檢查防火牆設定
3. 確認配置中的 MCP URL 正確

### LLM 提供商錯誤

**問題**: "LLM provider not available"

**解決方式**:
1. 確認 Ollama 已安裝並運行：`ollama list`
2. 或配置使用其他提供商（LM Studio、雲端服務）
3. 在配置中停用 LLM：`enable_llm: false`

---

## 📖 相關文件

- [統一套件設計](../docs/UNIFIED_PACKAGE_DESIGN.md)
- [整合指南](../docs/INTEGRATION_GUIDE.md)
- [中文整合摘要](../docs/INTEGRATION_SUMMARY_ZH.md)
- [架構說明](../docs/architecture.md)

---

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request！

---

## 📄 授權

與主專案相同

---

**版本**: 1.0.0  
**最後更新**: 2025-12-10  
**維護者**: Robot Command Console Team
