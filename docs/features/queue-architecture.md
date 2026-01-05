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
│  實作佇列:                                               │
│   ├─ MemoryQueue    (In-memory, 單機)                  │
│   ├─ RabbitMQQueue  (分散式, 自建) ✅ 已實作          │
│   └─ SQSQueue       (雲端託管, AWS) ✅ 已實作          │
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

### 4. RabbitMQQueue (分散式實作) ✅

**適用場景**：
- 分散式部署
- 自建基礎設施
- 需要完全控制
- 複雜路由需求

**特性**：
- Topic Exchange（靈活路由）
- Priority Queue（0-10 優先權）
- Dead Letter Exchange/Queue（DLX/DLQ）
- 持久化訊息（survive broker restart）
- 連線池與 Channel 池
- Publisher confirms（確保訊息送達）
- Prefetch QoS（控制並發）
- 自動重連機制

**拓撲結構**：
```
Exchange (robot.edge.commands)
    │
    ├─ routing_key: command.urgent   (Priority 10)
    ├─ routing_key: command.high     (Priority 8)
    ├─ routing_key: command.normal   (Priority 5)
    └─ routing_key: command.low      (Priority 2)
         │
         ▼
    Queue (robot.edge.queue)
      │ (on failure, max_retries exceeded)
      ▼
    DLX (robot.edge.dlx)
      │
      ▼
    DLQ (robot.edge.dlq)
```

**環境變數配置**：
```bash
EDGE_QUEUE_TYPE=rabbitmq
RABBITMQ_URL=amqp://user:pass@localhost:5672/
RABBITMQ_EXCHANGE_NAME=robot.edge.commands
RABBITMQ_QUEUE_NAME=robot.edge.queue
RABBITMQ_DLX_NAME=robot.edge.dlx
RABBITMQ_DLQ_NAME=robot.edge.dlq
RABBITMQ_PREFETCH_COUNT=10
RABBITMQ_CONN_POOL_SIZE=2
RABBITMQ_CHANNEL_POOL_SIZE=10
```

**使用範例**：
```python
from src.robot_service.edge_queue_config import create_service_manager_from_env

# 從環境變數建立
manager = create_service_manager_from_env()
await manager.start()

# 提交指令
msg_id = await manager.submit_command(
    payload={"command": "move_forward", "distance": 10},
    priority=MessagePriority.HIGH
)
```

**參考文件**：
- [RabbitMQ 部署指南](../deployment/RABBITMQ_DEPLOYMENT.md)
- [RabbitMQ Queue 實作](../../src/robot_service/queue/rabbitmq_queue.py)

### 5. SQSQueue (雲端託管實作) ✅

**適用場景**：
- AWS 雲端環境
- 完全託管服務
- 不想管理基礎設施
- 需要自動擴展

**特性**：
- Standard 或 FIFO 佇列
- 長輪詢（Long polling）
- 訊息可見性超時（Visibility timeout）
- Dead Letter Queue（DLQ）
- IAM role 或 Access Key 認證
- 自動擴展與高可用
- 與 AWS 生態系統整合

**架構**：
```
Client → SQS Queue (Standard/FIFO)
           │
           │ (visibility timeout expired or nack)
           ↓
        Worker processes message
           │
           ├─ Success → Delete message
           │
           └─ Failure → Return to queue
                │ (after max_retries)
                ▼
              DLQ (Dead Letter Queue)
```

**Standard vs FIFO**：

| 特性 | Standard Queue | FIFO Queue |
|------|----------------|------------|
| 順序保證 | ❌ 不保證 | ✅ 嚴格順序 |
| 唯一性 | ❌ 至少一次 | ✅ 恰好一次 |
| 吞吐量 | 無限制 | 3000 msg/s (batch) |
| 使用場景 | 高吞吐量、順序不重要 | 需要順序、去重 |

**環境變數配置**：
```bash
EDGE_QUEUE_TYPE=sqs
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456/robot-commands
SQS_QUEUE_NAME=robot-edge-commands-queue
SQS_DLQ_NAME=robot-edge-commands-dlq
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE  # 或使用 IAM role
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCY
SQS_VISIBILITY_TIMEOUT=30
SQS_WAIT_TIME_SECONDS=20  # 長輪詢最大值，減少成本
SQS_MAX_MESSAGES=10
SQS_USE_FIFO=false
```

**使用範例**：
```python
from src.robot_service.config_injection import create_sqs_env, inject_and_create_manager

# 建立 SQS 配置
sqs_env = create_sqs_env(
    region="us-west-2",
    queue_name="production-robot-commands",
    use_fifo=True
)

# 注入並建立 ServiceManager
manager = inject_and_create_manager(sqs_env)
await manager.start()
```

**參考文件**：
- [配置注入工具](../../src/robot_service/config_injection.py)
- [SQS Queue 實作](../../src/robot_service/queue/sqs_queue.py)

### 6. QueueHandler (佇列處理器)

負責訊息的消費與分派：
- 多工作協程並行處理
- 自動重試與錯誤處理
- 優雅關閉
- 可配置的工作數量與輪詢間隔

### 7. ServiceManager (服務管理器)

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

---

## 佇列實作比較

### 功能比較表

| 特性 | MemoryQueue | RabbitMQ | AWS SQS |
|------|-------------|----------|---------|
| **部署場景** | 單機、開發、測試 | 分散式、自建 | 雲端、託管 |
| **基礎設施** | 無需管理 | 需要管理 | 完全託管 |
| **持久化** | ❌ 重啟遺失 | ✅ 磁碟持久化 | ✅ 分散式儲存 |
| **高可用** | ❌ 單點故障 | ✅ 叢集支援 | ✅ 多 AZ 複製 |
| **擴展性** | ❌ 單機限制 | ✅ 手動擴展 | ✅ 自動擴展 |
| **順序保證** | ✅ 嚴格順序 | ❌ 不保證 | ✅ FIFO 可選 |
| **優先權** | ✅ 4 個等級 | ✅ 0-10 等級 | ❌ 需模擬 |
| **DLQ 支援** | ❌ | ✅ 原生支援 | ✅ 原生支援 |
| **訊息大小** | 無限制 | 128 MB | 256 KB |
| **吞吐量** | 極高（記憶體） | 高（萬級/秒） | 中（Standard 無限，FIFO 3K/s） |
| **延遲** | 極低（微秒） | 低（毫秒） | 中（長輪詢） |
| **成本** | 免費 | 基礎設施成本 | 按使用付費 |
| **複雜度** | 極低 | 中 | 低 |
| **監控** | 基本統計 | Prometheus、UI | CloudWatch |
| **整合性** | N/A | 獨立 | AWS 生態 |

### 使用場景建議

#### 使用 MemoryQueue
✅ **適合**：
- 單機部署
- 開發與測試環境
- 原型驗證
- 訊息可以遺失的場景
- 追求最快速度

❌ **不適合**：
- 生產環境（除非小規模且可接受遺失）
- 需要持久化
- 分散式部署
- 需要高可用

#### 使用 RabbitMQ
✅ **適合**：
- 自建分散式系統
- 需要完全控制基礎設施
- 複雜的路由需求
- 不想綁定雲端供應商
- 已有 RabbitMQ 經驗
- 需要複雜的訊息模式（pub/sub、routing）

❌ **不適合**：
- 不想管理基礎設施
- 團隊無 RabbitMQ 經驗
- 小團隊（維護成本高）
- 需要無限擴展

#### 使用 AWS SQS
✅ **適合**：
- 已使用 AWS 生態系統
- 需要完全託管服務
- 不想管理基礎設施
- 需要自動擴展
- 成本可預測（按使用付費）
- 與其他 AWS 服務整合（Lambda、SNS、EventBridge）

❌ **不適合**：
- 不想綁定 AWS
- 需要複雜路由
- 需要低延遲（微秒級）
- 訊息超過 256 KB
- 預算非常有限（小規模時成本可能高於自建）

## 遷移指南

### 從 MemoryQueue 遷移到 RabbitMQ

1. **準備工作**
   ```bash
   # 安裝 RabbitMQ
   docker run -d --name rabbitmq \
     -p 5672:5672 -p 15672:15672 \
     rabbitmq:3.12-management-alpine
   ```

2. **更新環境變數**
   ```bash
   export EDGE_QUEUE_TYPE=rabbitmq
   export RABBITMQ_URL=amqp://guest:guest@localhost:5672/
   ```

3. **重啟服務**
   - 服務會自動使用 RabbitMQ

4. **驗證**
   - 訪問 http://localhost:15672 查看管理介面
   - 檢查佇列是否正常建立
   - 提交測試指令驗證功能

### 從 MemoryQueue 遷移到 AWS SQS

1. **建立 SQS 佇列**
   ```bash
   aws sqs create-queue --queue-name robot-edge-commands-queue
   aws sqs create-queue --queue-name robot-edge-commands-dlq
   ```

2. **配置環境變數**
   ```bash
   export EDGE_QUEUE_TYPE=sqs
   export AWS_REGION=us-east-1
   export SQS_QUEUE_NAME=robot-edge-commands-queue
   # 使用 IAM Role（推薦）或 Access Key
   ```

3. **重啟服務**
   - 服務會自動使用 SQS

4. **驗證**
   - AWS Console 檢查佇列
   - CloudWatch 監控訊息流量
   - 提交測試指令驗證功能

## 相關文件

- [RabbitMQ 部署指南](../deployment/RABBITMQ_DEPLOYMENT.md)
- [測試執行指南](../deployment/TEST_EXECUTION.md)
- [RabbitMQ Queue 實作](../../src/robot_service/queue/rabbitmq_queue.py)
- [SQS Queue 實作](../../src/robot_service/queue/sqs_queue.py)
- [配置注入工具](../../src/robot_service/config_injection.py)
- [Edge Queue 配置](../../src/robot_service/edge_queue_config.py)

---

**最後更新**：2026-01-05  
**版本**：v2.0 - 新增 RabbitMQ 與 AWS SQS 支援
