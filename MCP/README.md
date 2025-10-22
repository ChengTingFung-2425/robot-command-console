# MCP (Model Context Protocol) 服務模組

提供統一的 API 介面，管理機器人指令處理、路由、協定適配與可觀測性。

## 📚 設計文件

完整設計說明請參閱 [Module.md](Module.md)

## 🎯 核心功能

- ✅ **統一 API** - HTTP / WebSocket / MQTT 可插拔
- ✅ **指令處理** - 接收、驗證、排隊、路由、重試、超時
- ✅ **機器人路由** - 依 robot_id/robot_type 智慧路由
- ✅ **協定適配** - HTTP / MQTT / WebSocket 多協定支援
- ✅ **認證授權** - JWT / RBAC 權限管理
- ✅ **日誌監控** - 事件追蹤、審計、指標收集
- ✅ **上下文管理** - 狀態歷史與冪等性保證

## 🚀 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

```bash
export MCP_API_HOST="0.0.0.0"
export MCP_API_PORT="8000"
export MCP_JWT_SECRET="your-secret-key"
```

### 3. 啟動服務

```bash
python api.py
```

或使用 uvicorn：

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 4. API 文件

服務啟動後，訪問：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📖 API 端點

### 指令 API

- `POST /api/command` - 建立指令
- `GET /api/command/{command_id}` - 查詢指令狀態
- `DELETE /api/command/{command_id}` - 取消指令

### 機器人 API

- `POST /api/robots/register` - 註冊機器人
- `DELETE /api/robots/{robot_id}` - 取消註冊
- `POST /api/robots/heartbeat` - 更新心跳
- `GET /api/robots/{robot_id}` - 取得機器人資訊
- `GET /api/robots` - 列出所有機器人

### 事件 API

- `GET /api/events` - 查詢事件
- `WS /api/events/subscribe` - 訂閱事件（WebSocket）

### 認證 API

- `POST /api/auth/register` - 註冊使用者
- `POST /api/auth/login` - 登入取得 Token

### 其他

- `GET /health` - 健康檢查
- `GET /api/metrics` - 取得指標

## 📋 資料契約範例

### 指令請求

```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-10-22T10:30:00Z",
  "actor": {
    "type": "human",
    "id": "user_123"
  },
  "source": "webui",
  "command": {
    "id": "cmd-123",
    "type": "robot.move",
    "target": {
      "robot_id": "robot_7"
    },
    "params": {
      "action_name": "go_forward",
      "duration_ms": 3000
    },
    "timeout_ms": 10000,
    "priority": "normal"
  },
  "auth": {
    "token": "eyJ..."
  }
}
```

### 指令回應

```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-10-22T10:30:00.123Z",
  "command": {
    "id": "cmd-123",
    "status": "accepted"
  },
  "result": null,
  "error": null
}
```

## 🔧 設定選項

所有設定可透過環境變數覆寫：

| 環境變數 | 預設值 | 說明 |
|---------|--------|------|
| MCP_API_HOST | 0.0.0.0 | API 主機 |
| MCP_API_PORT | 8000 | API 埠號 |
| MCP_JWT_SECRET | (必須設定) | JWT 密鑰 |
| MCP_LOG_LEVEL | INFO | 日誌等級 |
| MCP_DATABASE_URL | sqlite:///./mcp.db | 資料庫 URL |
| MCP_REDIS_URL | redis://localhost:6379/0 | Redis URL |

## 📁 模組結構

```
MCP/
├── Module.md              # 完整設計文件
├── README.md             # 本文件
├── requirements.txt      # 依賴套件
├── __init__.py          # 模組初始化
├── config.py            # 設定管理
├── models.py            # 資料模型
├── api.py               # FastAPI 服務
├── command_handler.py   # 指令處理器
├── robot_router.py      # 機器人路由器
├── context_manager.py   # 上下文管理器
├── auth_manager.py      # 認證授權管理器
└── logging_monitor.py   # 日誌監控器
```

## 🔐 安全性

- JWT Token 驗證
- RBAC 角色權限控制
- 密碼雜湊儲存
- CORS 設定
- 請求驗證與清理

## 📊 可觀測性

- 結構化日誌記錄
- 事件追蹤（trace_id 貫穿）
- 指標收集（成功率、延遲、錯誤碼分佈）
- WebSocket 事件串流

## 🧪 測試

```bash
# 健康檢查
curl http://localhost:8000/health

# 查看 API 文件
open http://localhost:8000/docs
```

## 📝 授權

MIT License

---

**詳細設計文件請參閱 [Module.md](Module.md)**
