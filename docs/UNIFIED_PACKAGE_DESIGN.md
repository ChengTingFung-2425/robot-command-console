# 統一部署套件設計

> **建立日期**: 2025-12-10  
> **狀態**: 設計中  
> **目標**: 將 WebUI/MCP/Robot-Console 整合為單一部署套件

---

## 📦 統一套件概念

將三個模組整合為單一的 Edge App 部署套件，提供完整的本地機器人控制功能。

### 套件架構

```
unified-edge-app/
├── core/                      # 核心服務整合
│   ├── __init__.py
│   ├── launcher.py            # 統一啟動器
│   ├── config.py              # 統一配置
│   └── service_manager.py     # 服務生命週期管理
│
├── mcp/                       # MCP 服務（完整保留）
│   ├── api.py
│   ├── command_handler.py
│   ├── llm_processor.py
│   ├── plugin_manager.py
│   └── ...
│
├── robot_console/             # Robot-Console（完整保留）
│   ├── action_executor.py
│   ├── pubsub.py
│   └── tools.py
│
├── web_interface/             # Web 介面（精簡版）
│   ├── __init__.py
│   ├── app.py                 # Flask 應用
│   ├── routes/               # 路由模組
│   │   ├── dashboard.py      # 儀表板（保留）
│   │   ├── commands.py       # 指令控制（保留）
│   │   ├── advanced.py       # 進階指令（保留）
│   │   ├── robots.py         # 機器人管理（保留）
│   │   └── monitoring.py     # 監控（保留）
│   ├── templates/            # 精簡模板
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── commands.html
│   │   └── advanced.html
│   ├── static/               # 靜態資源
│   └── models.py             # 本地資料模型（SQLite）
│
├── shared/                    # 共用模組
│   ├── logging_utils.py
│   ├── datetime_utils.py
│   ├── service_types.py
│   └── shared_state.py
│
├── requirements.txt           # 統一依賴
├── setup.py                   # 套件安裝
└── README.md                  # 使用說明
```

---

## 🎯 模組選擇標準

### WebUI - 保留功能

✅ **Edge 本地功能（保留）**：
- 機器人儀表板（Dashboard）
- 指令控制中心（Command Center）
- 進階指令建立器（Advanced Command Builder）- 含 Blockly
- 執行監控面板（Execution Monitor）
- 機器人管理（Robot Management）
- 本地設定（Settings）
- 日誌查看（Logs Viewer）

❌ **雲端/社群功能（移除）**：
- 用戶註冊/登入系統（使用簡化的本地認證）
- 討論區功能（Engagement/Comments/Posts）
- 排行榜（Leaderboard）
- 固件更新倉庫（改為本地固件管理）
- 郵件通知（Email）
- 社交互動（Follow/Like）

### 精簡的資料模型

**保留**：
- `Robot`: 機器人資料
- `Command`: 指令記錄
- `Advanced_Command`: 進階指令
- 本地設定存儲

**移除**：
- `User` (簡化為單用戶或本地認證)
- `Post`, `Comment`, `Message`
- `Followers`, `Likes`
- `Notification`

---

## 🔧 技術實作

### 1. 統一啟動器

```python
# unified-edge-app/core/launcher.py
class UnifiedEdgeApp:
    """統一 Edge App 啟動器"""
    
    def __init__(self):
        self.mcp_service = None
        self.web_interface = None
        self.robot_console = None
        self.config = load_unified_config()
    
    def start(self):
        """啟動所有服務"""
        # 1. 啟動 MCP 服務
        self.mcp_service = start_mcp(self.config.mcp)
        
        # 2. 啟動 Robot-Console
        self.robot_console = start_robot_console(self.config.robot)
        
        # 3. 啟動 Web 介面
        self.web_interface = start_web_interface(self.config.web)
        
        # 4. 配置服務間通訊
        self.setup_inter_service_communication()
    
    def stop(self):
        """停止所有服務"""
        if self.web_interface:
            self.web_interface.stop()
        if self.robot_console:
            self.robot_console.stop()
        if self.mcp_service:
            self.mcp_service.stop()
```

### 2. 統一配置

```yaml
# unified-edge-app/config.yaml
app:
  name: "Robot Command Console - Edge"
  version: "1.0.0"
  mode: "edge"  # edge or cloud

mcp:
  host: "127.0.0.1"
  port: 8000
  enable_llm: true
  llm_provider: "ollama"  # ollama, lm-studio, cloud
  enable_plugins: true

robot_console:
  protocol: "mqtt"  # mqtt, http, serial
  mqtt:
    broker: "localhost"
    port: 1883
  safety:
    enable_emergency_stop: true
    max_command_rate: 10

web_interface:
  host: "127.0.0.1"
  port: 5000
  auth_mode: "local"  # local, none
  enable_blockly: true
  database: "sqlite:///edge_app.db"
  
logging:
  level: "INFO"
  format: "json"
  output: "console"  # console, file, both
```

### 3. 精簡的 Web 介面

```python
# unified-edge-app/web_interface/app.py
from flask import Flask, render_template
from .routes import dashboard, commands, advanced, robots, monitoring

def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)
    
    # 註冊路由藍圖
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(commands.bp)
    app.register_blueprint(advanced.bp)
    app.register_blueprint(robots.bp)
    app.register_blueprint(monitoring.bp)
    
    # 簡化的本地認證（如需要）
    if config.AUTH_MODE == 'local':
        setup_local_auth(app)
    
    return app
```

### 4. 服務間通訊

```python
# unified-edge-app/core/service_manager.py
class ServiceCommunication:
    """管理服務間通訊"""
    
    def __init__(self, mcp, robot_console, web):
        self.mcp = mcp
        self.robot_console = robot_console
        self.web = web
    
    def setup(self):
        # Web → MCP: HTTP REST API
        self.web.set_mcp_url(f"http://{self.mcp.host}:{self.mcp.port}")
        
        # MCP → Robot-Console: 本地佇列
        queue = PriorityQueue()
        self.mcp.set_command_queue(queue)
        self.robot_console.set_command_queue(queue)
        
        # Robot-Console → MCP: 事件回報
        event_bus = EventBus()
        self.robot_console.set_event_bus(event_bus)
        self.mcp.subscribe_events(event_bus)
```

---

## 📦 打包與分發

### Electron 打包（Heavy 版本）

```json
{
  "name": "robot-command-console-edge",
  "version": "1.0.0",
  "main": "main.js",
  "scripts": {
    "start": "electron .",
    "build": "electron-builder"
  },
  "build": {
    "appId": "com.robot.command.console",
    "productName": "Robot Command Console",
    "files": [
      "electron-app/**/*",
      "unified-edge-app/**/*",
      "!**/*.pyc"
    ],
    "extraResources": [
      {
        "from": "unified-edge-app",
        "to": "unified-edge-app"
      }
    ]
  }
}
```

### PyQt 打包（Tiny 版本）

```python
# build_specs/unified_edge_app.spec
a = Analysis(
    ['unified-edge-app/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('unified-edge-app/web_interface/templates', 'web_interface/templates'),
        ('unified-edge-app/web_interface/static', 'web_interface/static'),
    ],
    hiddenimports=[
        'unified-edge-app.mcp',
        'unified-edge-app.robot_console',
        'unified-edge-app.web_interface',
    ],
)
```

---

## 🚀 使用方式

### 開發模式

```bash
# 1. 安裝依賴
pip install -r unified-edge-app/requirements.txt

# 2. 配置
cp unified-edge-app/config.example.yaml unified-edge-app/config.yaml
# 編輯 config.yaml

# 3. 啟動
python -m unified-edge-app.core.launcher
```

### 生產部署

```bash
# 方式 1: PyQt 單一執行檔
./RobotCommandConsole-Edge.exe  # Windows
./RobotCommandConsole-Edge  # Linux

# 方式 2: Electron App
# 雙擊應用圖示啟動

# 方式 3: Docker
docker run -p 5000:5000 -p 8000:8000 robot-edge-app:latest
```

---

## ✅ 遷移檢查清單

- [ ] **Step 1: 建立統一套件結構**
  - [ ] 創建 `unified-edge-app/` 目錄
  - [ ] 設定 `core/` 模組
  - [ ] 建立統一配置系統

- [ ] **Step 2: 整合 MCP**
  - [ ] 複製 MCP 核心模組
  - [ ] 移除雲端依賴
  - [ ] 配置本地 LLM 提供商

- [ ] **Step 3: 整合 Robot-Console**
  - [ ] 複製 ActionExecutor
  - [ ] 配置本地佇列連接
  - [ ] 整合協定適配器

- [ ] **Step 4: 精簡 WebUI**
  - [ ] 提取核心路由（dashboard, commands, advanced, robots）
  - [ ] 精簡資料模型（移除社群功能）
  - [ ] 簡化模板（保留功能頁面）
  - [ ] 配置 Blockly 編輯器
  - [ ] 設定本地認證（可選）

- [ ] **Step 5: 服務間通訊**
  - [ ] 實作統一啟動器
  - [ ] 配置服務間 API
  - [ ] 設定本地佇列
  - [ ] 實作事件總線

- [ ] **Step 6: 打包測試**
  - [ ] Electron 打包測試
  - [ ] PyQt 打包測試
  - [ ] Docker 映像測試
  - [ ] 跨平台驗證

---

## 📊 效益分析

| 指標 | 現狀（分散） | 統一套件 | 改善 |
|------|-------------|---------|------|
| 部署複雜度 | 需要啟動 3 個服務 | 一鍵啟動 | ↓ 70% |
| 安裝包大小 | ~200MB (Electron) | ~150MB | ↓ 25% |
| 配置文件數 | 3 個 | 1 個 | ↓ 67% |
| 啟動時間 | ~8 秒 | ~5 秒 | ↓ 37% |
| 使用者學習成本 | 高（需理解架構） | 低（單一應用） | ↓ 80% |

---

## 🔗 相關文件

- [整合指南](INTEGRATION_GUIDE.md)
- [架構說明](architecture.md)
- [權威規格](proposal.md)
- [WebUI 模組說明](../WebUI/Module.md)
- [MCP 模組說明](../MCP/Module.md)

---

**下一步**: 開始實作 Step 1 - 建立統一套件結構
