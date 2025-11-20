# Robot Service 模組化遷移指南

## 概覽

本指南說明如何從舊版 `flask_service.py` 遷移至新的模組化 `robot_service` 架構。

## 主要變更

### 架構變更

**舊版**：
```
flask_service.py (單一檔案，所有邏輯混在一起)
```

**新版**：
```
src/robot_service/
├── queue/              # 佇列系統
├── electron/           # Electron 整合
├── cli/               # CLI 模式
└── service_manager.py # 服務管理
```

### 新增功能

1. **模組化架構**
   - 清晰的職責分離
   - 可測試的元件
   - 可擴展的設計

2. **本地佇列系統**
   - 記憶體內實作（目前）
   - 優先權佇列（4 個等級）
   - 可擴展至 Redis/Kafka

3. **雙模式運行**
   - Electron 整合模式（向後相容）
   - 獨立 CLI 模式（新增）

4. **更好的可觀測性**
   - 結構化日誌
   - 佇列統計端點
   - Prometheus metrics

## 向後相容性

✅ **Electron 整合完全相容**

新版 `flask_service.py` 維持與 Electron 的完全相容性：

- 相同的環境變數（`APP_TOKEN`, `PORT`）
- 相同的 API 端點（`/health`, `/api/ping`, `/metrics`）
- 相同的認證機制（Bearer token）
- 相同的回應格式

## 遷移步驟

### 1. 無需變更（Electron 模式）

如果使用 Electron 整合模式，**無需任何變更**：

```bash
# Electron 會自動啟動新版服務
npm start
```

### 2. 使用新的 CLI 模式（可選）

如果想使用獨立 CLI 模式：

```bash
# 啟動 Robot Service
python3 run_service_cli.py --queue-size 1000 --workers 5
```

### 3. 整合新的佇列系統（可選）

如果想在自己的程式碼中使用佇列系統：

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from robot_service.service_manager import ServiceManager
from robot_service.queue import MessagePriority

# 建立服務管理器
service_manager = ServiceManager(
    queue_max_size=1000,
    max_workers=5,
)

# 啟動服務
await service_manager.start()

# 提交指令
message_id = await service_manager.submit_command(
    payload={"command": "move_forward", "robot_id": "robot-001"},
    priority=MessagePriority.NORMAL,
    trace_id="trace-123",
)

# 停止服務
await service_manager.stop()
```

## API 變更

### 新增端點

#### POST /api/command

提交指令到佇列：

```bash
curl -X POST http://127.0.0.1:5000/api/command \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "move_forward",
    "robot_id": "robot-001",
    "priority": "NORMAL",
    "trace_id": "trace-123"
  }'
```

回應：
```json
{
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "request_id": "..."
}
```

#### GET /api/queue/stats

取得佇列統計：

```bash
curl -H "Authorization: Bearer <token>" \
  http://127.0.0.1:5000/api/queue/stats
```

回應：
```json
{
  "status": "healthy",
  "type": "memory",
  "queue_sizes": {
    "URGENT": 0,
    "HIGH": 0,
    "NORMAL": 2,
    "LOW": 0
  },
  "total_size": 2,
  "statistics": {
    "total_enqueued": 10,
    "total_dequeued": 8,
    "total_acked": 8,
    "total_nacked": 0
  }
}
```

### 既有端點

所有既有端點保持不變：

- ✅ `GET /health` - 健康檢查
- ✅ `GET /metrics` - Prometheus metrics
- ✅ `GET|POST /api/ping` - 測試端點

## 配置變更

### 環境變數

舊版與新版使用相同的環境變數：

- `APP_TOKEN` - 認證 token（必要）
- `PORT` - 服務埠號（預設：5000）

### CLI 模式配置

CLI 模式支援額外的命令列參數：

```bash
python3 run_service_cli.py --help

Options:
  --queue-size INT      Maximum queue size (default: 1000)
  --workers INT         Number of worker threads (default: 5)
  --poll-interval FLOAT Queue poll interval in seconds (default: 0.1)
  --log-level LEVEL     Logging level (default: INFO)
```

## 測試

### 執行測試

```bash
# 執行所有測試（包含新的佇列測試）
python3 -m pytest Test/ -v

# 只執行佇列測試
python3 -m pytest Test/test_queue_system.py -v
```

### 驗證 Electron 整合

```bash
# 啟動 Electron（應該正常運作）
npm start

# 測試健康檢查
curl http://127.0.0.1:5000/health

# 測試認證端點
curl -H "Authorization: Bearer <token>" \
  http://127.0.0.1:5000/api/ping
```

## 疑難排解

### 問題：模組找不到

**錯誤**：`ModuleNotFoundError: No module named 'robot_service'`

**解決方案**：確保 `src/` 在 Python 路徑中：

```python
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
```

### 問題：Flask 服務無法啟動

**錯誤**：`ERROR: APP_TOKEN environment variable not set`

**解決方案**：設定環境變數：

```bash
export APP_TOKEN=your-token-here
python3 flask_service.py
```

### 問題：佇列測試失敗

**可能原因**：
1. 依賴套件未安裝
2. Python 版本不相容（需要 3.8+）

**解決方案**：

```bash
# 重新安裝依賴
pip install -r requirements.txt
pip install -r MCP/requirements.txt

# 檢查 Python 版本
python3 --version
```

## 效能考量

### 記憶體使用

新版服務使用記憶體佇列，預設最大 1000 個訊息：

```python
# 調整佇列大小
service_manager = ServiceManager(queue_max_size=5000)
```

### 工作數量

預設 5 個工作協程並行處理：

```python
# 調整工作數量
service_manager = ServiceManager(max_workers=10)
```

### 輪詢間隔

預設 0.1 秒輪詢間隔：

```python
# 調整輪詢間隔（秒）
service_manager = ServiceManager(poll_interval=0.05)
```

## 未來擴展

### Redis 佇列（規劃中）

```python
from robot_service.queue import RedisQueue

queue = RedisQueue(
    host='localhost',
    port=6379,
    db=0,
)

service_manager = ServiceManager(queue=queue)
```

### Kafka 佇列（規劃中）

```python
from robot_service.queue import KafkaQueue

queue = KafkaQueue(
    bootstrap_servers=['localhost:9092'],
    topic='robot-commands',
)

service_manager = ServiceManager(queue=queue)
```

## 相關文件

- [Robot Service README](../src/robot_service/README.md) - 模組使用說明
- [Queue Architecture](queue-architecture.md) - 佇列架構說明
- [測試](../Test/test_queue_system.py) - 佇列系統測試

## 支援

如有問題或建議，請提交 issue 或 PR。

## 更新日誌

### v1.0.0 (2025-11-20)

- ✅ 重構為模組化架構
- ✅ 新增本地佇列系統
- ✅ 支援 Electron 與 CLI 雙模式
- ✅ 完整的測試覆蓋
- ✅ 詳細的文件
- ✅ 向後相容 Electron 整合
