# MCP (Model Context Protocol) 服務模組

提供統一的 API 介面，管理機器人指令處理、路由、協定適配與可觀測性。

## 📚 設計文件

完整設計說明請參閱 [Module.md](Module.md)

## 🎯 核心功能

- ✅ **統一 API** - HTTP / WebSocket / MQTT 可插拔
# MCP (Model Context Protocol) 服務模組

子系統摘要：MCP 是本專案的指令中介層，負責接收、驗證與路由來自 WebUI / API / 其他系統的指令，並協調機器人執行與事件記錄。

## 設計文件

完整設計請參考 `Module.md`。

## 核心功能（概覽）

- 統一 API（HTTP / WebSocket / MQTT）
- 指令處理：接收、驗證、排隊、重試、超時
- 機器人路由：依 robot_id / robot_type 做智慧路由
- 認證與授權（JWT / RBAC）
- 日誌與指標收集（trace_id 貫穿）
- 上下文管理與冪等性保證

## 快速啟動（開發）

1. 安裝依賴：

```bash
pip install -r requirements.txt
```

2. 設定（範例）：

```bash
export MCP_API_HOST=0.0.0.0
export MCP_API_PORT=8000
export MCP_JWT_SECRET="your-secret-key"
```

3. 啟動：

```bash
python api.py
# 或： uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

啟動後可使用 `/docs` 或 `/redoc` 檢視 API 文件（若服務支援）。

## 重要端點（摘要）

- POST /api/command — 建立指令
- GET /api/command/{command_id} — 查詢指令狀態
- POST /api/robots/register — 註冊機器人
- GET /health — 健康檢查
- GET /metrics — Prometheus metrics 端點（可觀測性）

完整 API 列表請參考程式碼路由或 Module.md。

## 可觀測性（Observability）

MCP 服務已整合 Prometheus metrics 和結構化 JSON 日誌：

### Metrics
訪問 `http://localhost:8000/metrics` 取得即時指標，包括：
- 請求計數和延遲
- 指令處理統計
- 機器人註冊數量
- WebSocket 連線數
- 錯誤率統計

### 結構化日誌
所有日誌以 JSON 格式輸出，包含：
- timestamp（ISO 8601 格式）
- level（DEBUG, INFO, WARN, ERROR）
- trace_id（用於分散式追蹤）
- correlation_id（跨服務追蹤）
- 詳細的上下文資訊

詳細說明請參閱專案根目錄的 [可觀測性指南](../docs/features/observability-guide.md)。

## 設定選項（環境變數）

- MCP_API_HOST, MCP_API_PORT, MCP_JWT_SECRET（必要）
- MCP_LOG_LEVEL, MCP_DATABASE_URL, MCP_REDIS_URL, MCP_SSL_VERIFY

## 核心檔案

- Module.md — 完整設計文件
- api.py — 服務入口 (FastAPI)
- command_handler.py — 指令處理邏輯
- robot_router.py — 路由器
- context_manager.py — 上下文管理
- auth_manager.py — 認證/授權
- logging_monitor.py — 日誌/監控

## 測試與驗證

- 健康檢查：curl http://localhost:8000/health
- 檢視 API 文件：/docs 或 /redoc

## 授權

MIT License

---

詳細設計請參考 `Module.md`。
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
