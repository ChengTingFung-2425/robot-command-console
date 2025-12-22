# RabbitMQ 部署指南

## 概覽

本文件說明如何在 Robot Command Console Edge 層部署與配置 RabbitMQ。

> 📖 **相關文件**:
> - [Queue Architecture](../features/queue-architecture.md) - 佇列架構設計
> - [測試執行指南](TEST_EXECUTION.md) - 如何執行測試
> - [從 MemoryQueue 遷移](MIGRATION_MEMORY_TO_RABBITMQ.md) - 遷移指南

## 為什麼選擇 RabbitMQ

### MemoryQueue vs RabbitMQ

| 特性 | MemoryQueue | RabbitMQ |
|------|-------------|----------|
| **部署場景** | 單機、開發、測試 | 分散式、生產環境 |
| **持久化** | ❌ 無（重啟遺失） | ✅ 訊息持久化 |
| **高可用** | ❌ 單點故障 | ✅ 叢集支援 |
| **效能** | 極快（記憶體） | 快（網路 + 持久化） |
| **擴展性** | ❌ 有限 | ✅ 水平擴展 |
| **可靠性** | 中（無保證） | 高（ACK + DLQ） |

## 本地開發環境

### 使用 Docker Compose

```bash
# 啟動 RabbitMQ
docker-compose -f docker-compose.test.yml up -d rabbitmq

# 檢查狀態
docker-compose ps

# RabbitMQ 管理介面
open http://localhost:15672  # guest/guest
```

### 配置 Edge 服務

設定環境變數：

```bash
export EDGE_QUEUE_TYPE=rabbitmq
export RABBITMQ_URL=amqp://guest:guest@localhost:5672/
export EDGE_MAX_WORKERS=5
```

使用配置：

```python
from src.robot_service.edge_queue_config import create_service_manager_from_env

async def main():
    manager = create_service_manager_from_env()
    await manager.start()
    
    # 提交指令
    msg_id = await manager.submit_command({
        "command": "move_forward",
        "distance": 10
    })
    
    await manager.stop()
```

## 生產環境部署

### Docker Compose 生產配置

```yaml
version: '3.8'

services:
  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    restart: unless-stopped
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASS}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "check_port_connectivity"]
      interval: 30s
      timeout: 10s
      retries: 5

  edge-service:
    build: .
    depends_on:
      rabbitmq:
        condition: service_healthy
    environment:
      EDGE_QUEUE_TYPE: rabbitmq
      RABBITMQ_URL: amqp://${RABBITMQ_USER}:${RABBITMQ_PASS}@rabbitmq:5672/
      EDGE_MAX_WORKERS: 10

volumes:
  rabbitmq_data:
```

## 配置選項

### 環境變數

```bash
# 佇列類型
EDGE_QUEUE_TYPE=rabbitmq          # memory | rabbitmq

# RabbitMQ 連線
RABBITMQ_URL=amqp://user:pass@host:5672/

# 拓撲配置
RABBITMQ_EXCHANGE_NAME=robot.edge.commands
RABBITMQ_QUEUE_NAME=robot.edge.queue
RABBITMQ_DLX_NAME=robot.edge.dlx
RABBITMQ_DLQ_NAME=robot.edge.dlq

# 效能調整
RABBITMQ_PREFETCH_COUNT=10        # QoS 預取數量
EDGE_MAX_WORKERS=5                # 並行工作數
```

### 效能調整建議

| 場景 | PREFETCH | MAX_WORKERS |
|------|----------|-------------|
| 輕量 | 5 | 3 |
| 中等 | 10 | 5 |
| 重量 | 20 | 10 |
| 高負載 | 50 | 20 |

## 監控與維護

### 健康檢查

```python
health = await manager.health_check()
# {
#   "status": "healthy",
#   "type": "rabbitmq",
#   "connected": True,
#   "queue_size": 42
# }
```

### RabbitMQ 管理介面

訪問 http://your-server:15672 查看：
- 連線數與 Channel 數
- 佇列深度與訊息速率
- 消費者狀態

## 故障排除

### 無法連線

1. 檢查 RabbitMQ 運行狀態
   ```bash
   docker ps | grep rabbitmq
   ```

2. 檢查防火牆
   ```bash
   sudo ufw allow 5672
   ```

### 訊息堆積

1. 增加消費者
   ```bash
   export EDGE_MAX_WORKERS=10
   ```

2. 檢查處理器效能

### 記憶體不足

1. 設定記憶體限制（rabbitmq.conf）
   ```conf
   vm_memory_high_watermark.relative = 0.6
   ```

2. 清理舊訊息

## 參考資料

- [RabbitMQ 官方文件](https://www.rabbitmq.com/documentation.html)
- [專案 Queue Architecture](../features/queue-architecture.md)
- [RabbitMQ Queue 實作](../../src/robot_service/queue/rabbitmq_queue.py)
