# 可觀測性指南（Observability Guide）

本文件說明如何使用 Robot Command Console 的可觀測性功能，包括 Prometheus metrics 和結構化 JSON 日誌。

## 目錄

- [概述](#概述)
- [Prometheus Metrics](#prometheus-metrics)
- [結構化 JSON 日誌](#結構化-json-日誌)
- [設定與部署](#設定與部署)
- [監控最佳實踐](#監控最佳實踐)

## 概述

本系統實作了全面的可觀測性功能，包括：

1. **Prometheus Metrics** - 提供即時指標收集，用於監控系統健康狀況和效能
2. **結構化 JSON 日誌** - 所有服務都使用統一的 JSON 格式記錄日誌，包含 correlation ID 和 trace ID
3. **健康檢查** - 定期監控服務狀態並記錄狀態轉換

## Prometheus Metrics

### Flask Service (port 5000)

Flask 服務提供以下 metrics 端點：

```
http://127.0.0.1:5000/metrics
```

#### 可用的 Metrics

| Metric 名稱 | 類型 | 說明 | 標籤 |
|------------|------|------|------|
| `flask_request_count_total` | Counter | 總請求數 | `method`, `endpoint`, `status` |
| `flask_request_latency_seconds` | Histogram | 請求延遲時間（秒） | `method`, `endpoint` |
| `flask_error_count_total` | Counter | 總錯誤數 | `endpoint`, `error_type` |
| `flask_active_connections` | Gauge | 活躍連線數 | - |

#### 範例查詢

```bash
# 取得所有 metrics
curl http://127.0.0.1:5000/metrics

# 使用 Prometheus 查詢語言（PromQL）範例
# 每秒請求率
rate(flask_request_count_total[5m])

# 95% 請求延遲
histogram_quantile(0.95, rate(flask_request_latency_seconds_bucket[5m]))

# 錯誤率
rate(flask_error_count_total[5m])
```

### MCP Service (FastAPI)

MCP 服務提供以下 metrics 端點：

```
http://localhost:8000/metrics
```

#### 可用的 Metrics

| Metric 名稱 | 類型 | 說明 | 標籤 |
|------------|------|------|------|
| `mcp_request_count_total` | Counter | 總請求數 | `method`, `endpoint`, `status` |
| `mcp_request_latency_seconds` | Histogram | 請求延遲時間（秒） | `method`, `endpoint` |
| `mcp_command_count_total` | Counter | 已處理的指令總數 | `status` |
| `mcp_robot_count` | Gauge | 已註冊的機器人數量 | `status` |
| `mcp_error_count_total` | Counter | 總錯誤數 | `endpoint`, `error_type` |
| `mcp_active_websockets` | Gauge | 活躍的 WebSocket 連線數 | - |

#### 範例查詢

```bash
# 取得所有 metrics
curl http://localhost:8000/metrics

# PromQL 範例
# 指令成功率
rate(mcp_command_count_total{status="success"}[5m]) / rate(mcp_command_count_total[5m])

# 活躍機器人數量
mcp_robot_count{status="active"}

# WebSocket 連線數
mcp_active_websockets
```

## 結構化 JSON 日誌

所有服務都使用統一的 JSON 日誌格式，便於日誌收集和分析。

### 日誌格式

每條日誌都包含以下欄位：

```json
{
  "timestamp": "2025-11-19T04:30:00.123456+00:00",
  "level": "INFO",
  "event": "module.name",
  "message": "Human-readable message",
  "service": "service-name",
  "request_id": "uuid-v4",
  "correlation_id": "uuid-v4",
  "trace_id": "uuid-v4",
  "additional_context": "..."
}
```

### 欄位說明

- **timestamp**: ISO 8601 格式的 UTC 時間戳
- **level**: 日誌等級（DEBUG, INFO, WARN, ERROR）
- **event**: 事件類型/模組名稱
- **message**: 人類可讀的訊息
- **service**: 服務名稱（electron-main, flask-service, mcp-api）
- **request_id**: 單一請求的唯一 ID
- **correlation_id**: 跨服務追蹤的關聯 ID
- **trace_id**: 分散式追蹤 ID（用於 MCP 服務）

### Flask Service 日誌範例

#### 請求開始
```json
{
  "timestamp": "2025-11-19T04:30:00.123456+00:00",
  "level": "INFO",
  "event": "__main__",
  "message": "Request started",
  "service": "flask-service",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "correlation_id": "x1y2z3a4-b5c6-d7e8-f9ab-cd1234567890",
  "method": "POST",
  "path": "/api/ping",
  "remote_addr": "127.0.0.1",
  "user_agent": "Mozilla/5.0..."
}
```

#### 請求完成
```json
{
  "timestamp": "2025-11-19T04:30:00.456789+00:00",
  "level": "INFO",
  "event": "__main__",
  "message": "Request completed",
  "service": "flask-service",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "correlation_id": "x1y2z3a4-b5c6-d7e8-f9ab-cd1234567890",
  "method": "POST",
  "path": "/api/ping",
  "status": 200,
  "duration_seconds": 0.333333
}
```

#### 錯誤日誌
```json
{
  "timestamp": "2025-11-19T04:30:00.789012+00:00",
  "level": "ERROR",
  "event": "__main__",
  "message": "Internal server error",
  "service": "flask-service",
  "request_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "path": "/api/command",
  "error": "Database connection failed"
}
```

### MCP Service 日誌範例

#### 指令處理
```json
{
  "timestamp": "2025-11-19T04:30:01.123456+00:00",
  "level": "INFO",
  "event": "MCP.api",
  "message": "Command received",
  "service": "mcp-api",
  "trace_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "robot_id": "robot-001",
  "action": "move_forward"
}
```

#### 機器人註冊
```json
{
  "timestamp": "2025-11-19T04:30:02.123456+00:00",
  "level": "INFO",
  "event": "MCP.api",
  "message": "Robot registered successfully",
  "service": "mcp-api",
  "robot_id": "robot-001",
  "robot_type": "mobile"
}
```

### Electron Main 日誌範例

#### 應用啟動
```json
{
  "timestamp": "2025-11-19T04:30:00.000000+00:00",
  "level": "INFO",
  "event": "app_ready",
  "message": "Electron app ready, initializing services",
  "service": "electron-main"
}
```

#### 健康檢查狀態轉換
```json
{
  "timestamp": "2025-11-19T04:30:05.123456+00:00",
  "level": "INFO",
  "event": "health_status_transition",
  "message": "Health status changed",
  "service": "electron-main",
  "previous_status": "unknown",
  "new_status": "healthy",
  "attempt": 3
}
```

#### Python 服務啟動
```json
{
  "timestamp": "2025-11-19T04:30:01.000000+00:00",
  "level": "INFO",
  "event": "python_service_start",
  "message": "Starting Python service",
  "service": "electron-main",
  "script": "/path/to/flask_service.py",
  "token_prefix": "abcd1234"
}
```

## 設定與部署

### 1. 安裝依賴

確保已安裝所有必要的依賴：

```bash
# Flask Service
pip install -r requirements.txt

# MCP Service
cd MCP
pip install -r requirements.txt
```

### 2. 環境變數配置

#### Flask Service
```bash
export APP_TOKEN="your-secure-token"
export PORT=5000
```

#### MCP Service
```bash
export MCP_API_HOST="0.0.0.0"
export MCP_API_PORT=8000
export MCP_JWT_SECRET="your-jwt-secret"
export MCP_LOG_LEVEL="INFO"
```

### 3. 啟動服務

#### Flask Service
```bash
python3 flask_service.py
```

#### MCP Service
```bash
cd MCP
python api.py
# 或使用 uvicorn
uvicorn api:app --host 0.0.0.0 --port 8000
```

#### Electron Application
```bash
npm start
# 或開發模式
npm run start:dev
```

### 4. 整合 Prometheus

在 Prometheus 配置文件中添加以下 scrape 配置：

```yaml
scrape_configs:
  - job_name: 'flask-service'
    static_configs:
      - targets: ['127.0.0.1:5000']
    metrics_path: '/metrics'
    scrape_interval: 15s

  - job_name: 'mcp-service'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### 5. 日誌收集

使用 ELK Stack、Fluentd 或其他日誌聚合工具收集 JSON 日誌：

#### Fluentd 配置範例
```xml
<source>
  @type tail
  path /var/log/robot-console/*.log
  pos_file /var/log/td-agent/robot-console.pos
  tag robot.console
  <parse>
    @type json
    time_key timestamp
    time_format %Y-%m-%dT%H:%M:%S.%L%z
  </parse>
</source>

<match robot.console>
  @type elasticsearch
  host localhost
  port 9200
  index_name robot-console
  type_name log
</match>
```

#### Docker Compose 範例
```yaml
version: '3'
services:
  flask-service:
    build: .
    ports:
      - "5000:5000"
    environment:
      - APP_TOKEN=${APP_TOKEN}
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 監控最佳實踐

### 1. 設定告警

#### Prometheus 告警規則範例

```yaml
groups:
  - name: robot_console_alerts
    rules:
      # 高錯誤率告警
      - alert: HighErrorRate
        expr: rate(flask_error_count_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors/sec"

      # 服務不健康告警
      - alert: ServiceDown
        expr: up{job="flask-service"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Flask service is down"

      # 高延遲告警
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(flask_request_latency_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High request latency"
          description: "95th percentile latency is {{ $value }}s"
```

### 2. 儀表板

#### Grafana 儀表板建議

建立以下面板：

1. **服務健康狀況**
   - 服務可用性（up/down）
   - 活躍連線數
   - 錯誤率

2. **效能指標**
   - 請求率（requests/sec）
   - 延遲分佈（P50, P95, P99）
   - 吞吐量

3. **業務指標**
   - 指令處理速率
   - 成功/失敗比率
   - 機器人註冊數量
   - WebSocket 連線數

4. **系統資源**
   - CPU 使用率
   - 記憶體使用率
   - 網路 I/O

### 3. 日誌查詢

#### 使用 Elasticsearch/Kibana

```json
// 查詢特定 trace_id 的所有日誌
{
  "query": {
    "match": {
      "trace_id": "c3d4e5f6-a7b8-9012-cdef-123456789012"
    }
  }
}

// 查詢錯誤日誌
{
  "query": {
    "match": {
      "level": "ERROR"
    }
  },
  "sort": [
    { "timestamp": "desc" }
  ]
}

// 查詢特定時間範圍的請求
{
  "query": {
    "bool": {
      "must": [
        { "match": { "event": "Request completed" } }
      ],
      "filter": [
        {
          "range": {
            "timestamp": {
              "gte": "2025-11-19T00:00:00",
              "lte": "2025-11-19T23:59:59"
            }
          }
        }
      ]
    }
  }
}
```

### 4. 追蹤請求

使用 correlation_id 和 trace_id 追蹤跨服務的請求：

1. Electron 發起請求時生成 correlation_id
2. Flask Service 接收並傳遞 correlation_id
3. MCP Service 使用 trace_id 追蹤指令處理
4. 所有服務在日誌中記錄這些 ID

範例追蹤流程：
```
Electron (correlation_id: xyz) 
  -> Flask Service (request_id: abc, correlation_id: xyz)
    -> MCP Service (trace_id: def, correlation_id: xyz)
      -> Robot (trace_id: def)
```

### 5. 效能調校

基於 metrics 進行效能調校：

1. **識別瓶頸**
   - 查看高延遲端點
   - 分析慢查詢
   - 檢查資源使用

2. **優化配置**
   - 調整工作執行緒數
   - 配置連線池大小
   - 設定快取策略

3. **容量規劃**
   - 監控資源使用趨勢
   - 預測未來需求
   - 設定自動擴展規則

## 疑難排解

### 常見問題

#### 1. Metrics 端點無法訪問

檢查服務是否正在運行：
```bash
curl http://127.0.0.1:5000/health
curl http://localhost:8000/health
```

確認防火牆設定允許訪問這些端口。

#### 2. 日誌未產生 JSON 格式

確保已安裝 `python-json-logger`：
```bash
pip install python-json-logger
```

檢查日誌處理器配置是否正確。

#### 3. 高記憶體使用

日誌和 metrics 會占用記憶體。考慮：
- 限制保存的事件數量
- 定期清理舊日誌
- 使用外部日誌收集系統

#### 4. Prometheus 無法 scrape metrics

檢查：
- Prometheus 配置中的目標地址
- 網路連線
- metrics 端點是否正確回應

## 相關資源

- [Prometheus 官方文件](https://prometheus.io/docs/)
- [Grafana 儀表板設計](https://grafana.com/docs/)
- [ELK Stack 指南](https://www.elastic.co/guide/)
- [python-json-logger](https://github.com/madzak/python-json-logger)
- [prometheus_client Python 函式庫](https://github.com/prometheus/client_python)

## 總結

本系統的可觀測性功能提供：

✅ **Prometheus Metrics** - 即時監控系統健康和效能  
✅ **結構化 JSON 日誌** - 統一格式，便於搜尋和分析  
✅ **Correlation Tracking** - 跨服務請求追蹤  
✅ **健康檢查** - 自動監控服務狀態  
✅ **錯誤追蹤** - 詳細的錯誤日誌和 metrics

透過這些功能，您可以有效地監控、除錯和優化 Robot Command Console 系統。
