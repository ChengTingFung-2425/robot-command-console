# RabbitMQ & AWS SQS 佇列整合經驗（2026-01-05）

## 概述

本文件記錄整合 RabbitMQ 與 AWS SQS 佇列的實作決策、踩坑經驗與最佳實踐。

---

## 實作成果

- 新增 `RabbitMQ Queue`（450+ 行，完整實作 `QueueInterface`）
- 新增 `AWS SQS Queue`（470+ 行，支援 Standard/FIFO 佇列）
- 新增 配置匯出與注入工具（300+ 行，支援多種格式）
- 更新 `ServiceManager` 支援動態佇列選擇（memory/rabbitmq/sqs）
- 完成 1,150+ 行測試代碼（單元、整合、比較測試）
- 完成 CI/CD Pipeline（GitHub Actions，多 Python 版本）

**相關檔案**：
- [`src/robot_service/queue/rabbitmq_queue.py`](../../src/robot_service/queue/rabbitmq_queue.py)
- [`src/robot_service/queue/sqs_queue.py`](../../src/robot_service/queue/sqs_queue.py)
- [`src/robot_service/config_injection.py`](../../src/robot_service/config_injection.py)
- [`docs/deployment/RABBITMQ_DEPLOYMENT.md`](../deployment/RABBITMQ_DEPLOYMENT.md)

---

## 關鍵設計決策

### 1. QueueInterface 抽象介面設計

```python
# ✅ 抽象介面統一三種實作
class QueueInterface(ABC):
    @abstractmethod
    async def enqueue(self, item: dict, priority: int = 0) -> str: ...
    @abstractmethod
    async def dequeue(self) -> Optional[dict]: ...
    @abstractmethod
    async def peek(self) -> Optional[dict]: ...
```

- 抽象介面確保 Memory/RabbitMQ/SQS 行為一致
- 參數化測試跨三種實作驗證行為一致性
- 便於未來擴展（Kafka、Redis 等）

### 2. RabbitMQ Best Practices

```python
# ✅ Topic Exchange + Priority Queue
channel.exchange_declare(
    exchange='robot_commands',
    exchange_type='topic',
    durable=True
)
channel.queue_declare(
    queue='commands.high',
    arguments={'x-max-priority': 10, 'x-dead-letter-exchange': 'robot_commands_dlx'}
)
```

- 使用 **Topic Exchange + Priority Queue**
- **DLX/DLQ** 處理失敗訊息
- 連線池與 Channel 池提升效能
- **Publisher confirms** 確保訊息不遺失

### 3. AWS SQS 整合要點

- **長輪詢**（WaitTimeSeconds=20）減少空請求成本
- **FIFO vs Standard**：順序要求選 FIFO，高吞吐量選 Standard
- **IAM Role 優於 Access Key**（安全性）
- CloudWatch 監控訊息流量

### 4. 配置管理策略

```python
# ✅ 多格式匯出
exporter = ConfigExporter(queue_config)
exporter.to_shell_script('/tmp/rabbitmq.env.sh')
exporter.to_docker_env('/tmp/.env')
exporter.to_k8s_configmap('/tmp/configmap.yaml')
```

- 環境變數驅動配置（17+ 環境變數）
- 支援匯出格式：Shell Script、Docker `.env`、K8s ConfigMap
- `ConfigInjector` 工具統一注入

### 5. 測試策略

```python
# ✅ pytest 參數化支援多種實作
@pytest.fixture(params=['memory', 'rabbitmq', 'sqs'])
async def queue(request, ...):
    ...
```

- 使用 `TEST_WITH_RABBITMQ` 環境變數控制測試執行（避免無 RabbitMQ 服務時失敗）
- Docker Compose 提供測試環境
- 行為一致性測試確保介面合規

---

## 踩坑記錄

| 問題 | 解決方案 |
|------|----------|
| `pytest-asyncio` fixture 標記問題 | 明確標記 `@pytest.fixture` 和 `@pytest.mark.asyncio` |
| RabbitMQ 沒有原生 `peek` 支援 | 使用 `get + nack(requeue=True)` 模擬 |
| SQS 訊息優先權模擬 | 用 Message Attributes 儲存優先權資訊 |
| 配置注入的靈活性 | 建立 `ConfigExporter` 和 `ConfigInjector` 工具類 |

---

## 效能數據

| 佇列 | 延遲 | 吞吐量 | 月費（1M 訊息） |
|------|------|--------|----------------|
| MemoryQueue | < 1ms | 100K+ msg/s | ~$0 |
| RabbitMQ（自建） | 1–10ms | 10K–50K msg/s | $30–200 |
| AWS SQS Standard | 10–100ms | 無限制 | $0.50–2 |
| AWS SQS FIFO | 10–100ms | 3K msg/s | $0.50–2 |

---

## 相關文件

- [docs/deployment/RABBITMQ_DEPLOYMENT.md](../deployment/RABBITMQ_DEPLOYMENT.md)
- [docs/deployment/TEST_EXECUTION.md](../deployment/TEST_EXECUTION.md)
- [docs/features/queue-architecture.md](../features/queue-architecture.md)
