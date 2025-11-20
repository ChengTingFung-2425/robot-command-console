# Queue Architecture - Robot Service

## 概覽

Robot Service 採用模組化佇列架構，提供清晰的 API 界限與可擴展的訊息處理機制。

## 架構圖

```
┌─────────────────────────────────────────────────────────┐
│                    Robot Service                         │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐         ┌──────────────┐             │
│  │   Electron   │         │  CLI Mode    │             │
│  │   Adapter    │         │   Runner     │             │
│  │  (Flask)     │         │              │             │
│  └───────┬──────┘         └──────┬───────┘             │
│          │                       │                       │
│          └───────────┬───────────┘                       │
│                      │                                   │
│              ┌───────▼────────┐                         │
│              │ ServiceManager │                         │
│              └───────┬────────┘                         │
│                      │                                   │
│        ┌─────────────┴─────────────┐                   │
│        │                             │                   │
│   ┌────▼─────┐              ┌───────▼────┐             │
│   │  Queue   │              │   Queue    │             │
│   │Interface │              │  Handler   │             │
│   └────┬─────┘              └───────┬────┘             │
│        │                             │                   │
│   ┌────▼─────────┐          ┌───────▼────────┐         │
│   │MemoryQueue  │          │   Processor    │         │
│   │(In-memory)  │          │   (Workers)    │         │
│   └─────────────┘          └────────────────┘         │
│                                                           │
│  Future Extensions:                                      │
│   ├─ RedisQueue  (Distributed)                          │
│   └─ KafkaQueue  (Event Streaming)                      │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## 核心元件

### 1. QueueInterface (抽象介面)

定義標準佇列操作介面：

```python
class QueueInterface(ABC):
    async def enqueue(message: Message) -> bool
    async def dequeue(timeout: Optional[float]) -> Optional[Message]
    async def peek() -> Optional[Message]
    async def ack(message_id: str) -> bool
    async def nack(message_id: str, requeue: bool) -> bool
    async def size() -> int
    async def clear() -> None
    async def health_check() -> Dict[str, Any]
```

### 2. Message (訊息合約)

標準訊息格式：

```python
@dataclass
class Message:
    id: str                           # 唯一識別碼
    payload: Dict[str, Any]           # 訊息內容
    priority: MessagePriority         # 優先權 (LOW/NORMAL/HIGH/URGENT)
    timestamp: datetime               # 時間戳記
    trace_id: Optional[str]           # 追蹤 ID (分散式追蹤)
    correlation_id: Optional[str]     # 關聯 ID (跨服務追蹤)
    retry_count: int                  # 重試次數
    max_retries: int                  # 最大重試次數
    timeout_seconds: Optional[int]    # 處理逾時
```

### 3. MemoryQueue (記憶體實作)

目前的實作，適用於：
- 單機部署
- 開發與測試
- 小規模生產環境

特性：
- 優先權佇列（4 個等級）
- 非同步操作
- 處理中訊息追蹤
- 重試機制
- 統計資訊

### 4. QueueHandler (佇列處理器)

負責訊息的消費與分派：
- 多工作協程並行處理
- 自動重試與錯誤處理
- 優雅關閉
- 可配置的工作數量與輪詢間隔

### 5. ServiceManager (服務管理器)

統一的服務入口：
- 初始化與管理佇列
- 啟動與停止處理器
- 提供 API 介面
- 健康檢查

## 訊息流程

### 1. 訊息提交流程

```
Client → ServiceManager.submit_command()
         ↓
    Create Message
         ↓
    Queue.enqueue()
         ↓
    Return message_id
```

### 2. 訊息處理流程

```
QueueHandler.worker
    ↓
Queue.dequeue()
    ↓
Processor(message)
    ↓
Success? → Queue.ack()
    ↓
Failure? → Queue.nack(requeue=True)
    ↓
Max retries? → Drop message
```

## 優先權處理

訊息優先權等級（高到低）：

1. **URGENT** - 緊急指令（例：緊急停止）
2. **HIGH** - 高優先權指令（例：安全相關）
3. **NORMAL** - 一般指令（預設）
4. **LOW** - 低優先權指令（例：統計、日誌）

處理器總是優先處理高優先權訊息。

## 訊息合約

### 指令訊息範例

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "payload": {
    "command": "move_forward",
    "robot_id": "robot-001",
    "parameters": {
      "distance": 1.0,
      "speed": 0.5
    }
  },
  "priority": 1,
  "timestamp": "2025-11-20T02:16:34.246Z",
  "trace_id": "trace-123",
  "correlation_id": "corr-456",
  "retry_count": 0,
  "max_retries": 3,
  "timeout_seconds": 30
}
```

### Payload 格式

Payload 內容依據使用場景而定，建議包含：

- `command`: 指令名稱
- `robot_id`: 目標機器人 ID
- `parameters`: 指令參數
- `metadata`: 額外的元數據

## 擴展點

### 1. Redis Queue (未來實作)

適用於：
- 分散式部署
- 多個服務實例
- 高可用性需求

特性：
- 持久化儲存
- 跨程序共享
- 分散式鎖
- Pub/Sub 支援

### 2. Kafka Queue (未來實作)

適用於：
- 高吞吐量場景
- 事件串流處理
- 長期事件儲存
- 複雜事件處理

特性：
- 分散式日誌
- 持久化與重播
- 分區與擴展
- 多消費者群組

## 使用範例

### Electron 整合模式

```python
from robot_service.electron import create_flask_app
from robot_service.service_manager import ServiceManager

# 建立服務管理器
service_manager = ServiceManager(
    queue_max_size=1000,
    max_workers=5,
)

# 啟動服務
await service_manager.start()

# 建立 Flask 應用
app = create_flask_app(service_manager=service_manager)

# 執行應用
app.run(host='127.0.0.1', port=5000)
```

### 獨立 CLI 模式

```bash
# 使用預設設定
python3 run_service_cli.py

# 自訂配置
python3 run_service_cli.py \
  --queue-size 2000 \
  --workers 10 \
  --poll-interval 0.05 \
  --log-level DEBUG
```

### 提交指令

```python
# 透過 ServiceManager
message_id = await service_manager.submit_command(
    payload={
        "command": "move_forward",
        "robot_id": "robot-001",
    },
    priority=MessagePriority.HIGH,
    trace_id="trace-123",
)
```

### 自訂處理器

```python
async def custom_processor(message: Message) -> bool:
    """自訂訊息處理器"""
    try:
        # 處理訊息
        command = message.payload.get("command")
        robot_id = message.payload.get("robot_id")
        
        # 執行指令邏輯
        result = await execute_command(command, robot_id)
        
        return result.success
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return False

# 使用自訂處理器啟動服務
await service_manager.start(processor=custom_processor)
```

## 監控與觀測

### 健康檢查

```python
# 服務健康檢查
health = await service_manager.health_check()

# 佇列統計
stats = await service_manager.get_queue_stats()
```

### Metrics

Flask Adapter 提供 Prometheus metrics 端點：

```
GET /metrics
```

包含：
- 佇列大小
- 訊息吞吐量
- 處理延遲
- 錯誤率

### 日誌

所有元件使用結構化 JSON 日誌：

```json
{
  "timestamp": "2025-11-20T02:16:34.246Z",
  "level": "INFO",
  "event": "robot_service.queue",
  "message": "Message enqueued",
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "priority": "NORMAL",
  "trace_id": "trace-123"
}
```

## 測試策略

### 單元測試

測試個別元件：
- Message 序列化/反序列化
- MemoryQueue 操作
- QueueHandler 處理邏輯

### 整合測試

測試元件互動：
- 訊息流程端到端
- 重試機制
- 錯誤處理

### 負載測試

測試效能與穩定性：
- 高並發訊息提交
- 佇列滿載處理
- 長時間運行穩定性

## 最佳實踐

1. **優先權使用**
   - 只在真正需要時使用 URGENT/HIGH
   - 大部分指令使用 NORMAL
   - 避免所有訊息都設為高優先權

2. **Trace ID 追蹤**
   - 始終提供 trace_id 以便追蹤
   - 在分散式場景中使用 correlation_id

3. **錯誤處理**
   - 在處理器中妥善處理異常
   - 設定合理的 max_retries
   - 記錄詳細的錯誤日誌

4. **效能調整**
   - 根據負載調整 max_workers
   - 設定合適的 queue_max_size
   - 監控佇列深度與處理延遲

5. **優雅關閉**
   - 使用 stop() 方法正確關閉服務
   - 設定足夠的 timeout 以完成處理中的訊息
   - 在 SIGTERM 時觸發關閉

## 故障排除

### 佇列滿載

**症狀**: enqueue() 返回 False

**解決方案**:
- 增加 queue_max_size
- 增加 max_workers
- 優化處理器效能
- 檢查處理器是否卡住

### 訊息處理緩慢

**症狀**: 訊息堆積，延遲增加

**解決方案**:
- 增加 max_workers
- 減少 poll_interval
- 優化處理器邏輯
- 檢查是否有阻塞操作

### 記憶體不足

**症狀**: OOM 錯誤

**解決方案**:
- 減少 queue_max_size
- 清理處理完的訊息
- 考慮使用 Redis/Kafka

## 遷移指南

### 從舊有架構遷移

1. **評估現有流量**: 確定佇列大小與工作數
2. **部署新版本**: 使用 Electron 模式保持相容
3. **監控運行**: 檢查 metrics 與日誌
4. **逐步遷移**: 將處理邏輯遷移到新處理器
5. **切換模式**: 可選擇切換到 CLI 模式

### 擴展到 Redis/Kafka

1. **實作新 QueueInterface**: 繼承並實作介面
2. **配置連線**: 設定 Redis/Kafka 連線
3. **測試相容性**: 確保行為一致
4. **逐步切換**: 先在測試環境驗證
5. **監控遷移**: 密切監控新後端表現

## 參考

- [Queue Interface 原始碼](../src/robot_service/queue/interface.py)
- [Memory Queue 實作](../src/robot_service/queue/memory_queue.py)
- [Queue Handler](../src/robot_service/queue/handler.py)
- [Service Manager](../src/robot_service/service_manager.py)
- [Flask Adapter](../src/robot_service/electron/flask_adapter.py)
- [CLI Runner](../src/robot_service/cli/runner.py)
