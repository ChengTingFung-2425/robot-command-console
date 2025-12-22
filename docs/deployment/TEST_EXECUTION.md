# 測試執行指南

## 概覽

本文件說明如何執行 Robot Command Console 的各類測試，包括單元測試、整合測試與自動化測試。

## 快速開始

### 執行所有測試（不含 RabbitMQ）

```bash
python3 run_tests.py unit
```

### 執行所有測試（含 RabbitMQ）

```bash
# 1. 啟動 RabbitMQ
docker-compose -f docker-compose.test.yml up -d rabbitmq

# 2. 執行測試
python3 run_tests.py all --with-rabbitmq --coverage

# 3. 停止 RabbitMQ
docker-compose -f docker-compose.test.yml down
```

## 測試類型

### 1. 單元測試

測試個別元件功能，不需要外部依賴。

```bash
# 執行所有單元測試
python3 run_tests.py unit

# 執行特定單元測試
python3 run_tests.py specific --test-path tests/test_rabbitmq_queue.py::TestMessage

# 帶覆蓋率報告
python3 run_tests.py unit --coverage
```

### 2. 整合測試

測試元件間互動，需要 RabbitMQ。

```bash
# 執行整合測試（需要 RabbitMQ）
python3 run_tests.py integration --with-rabbitmq

# 執行 Edge 整合測試
python3 -m pytest tests/test_edge_rabbitmq_integration.py -v
```

### 3. Queue 比較測試

比較 MemoryQueue 與 RabbitMQ 行為一致性。

```bash
# 只測試 MemoryQueue
python3 -m pytest tests/test_queue_comparison.py -v

# 測試所有實作（需要 RabbitMQ）
TEST_WITH_RABBITMQ=1 python3 -m pytest tests/test_queue_comparison.py -v
```

### 4. 程式碼品質檢查

```bash
# 執行 linting
python3 run_tests.py lint

# 手動檢查
python3 -m flake8 src/ MCP/ --select=E,F,W --max-line-length=120
```

## 使用 Docker 執行測試

### 使用 Docker Compose

```bash
# 執行完整測試套件
docker-compose -f docker-compose.test.yml run --rm test-runner

# 自訂測試命令
docker-compose -f docker-compose.test.yml run --rm test-runner \
    python3 run_tests.py integration --with-rabbitmq
```

### 建立測試映像

```bash
# 建立
docker build -f Dockerfile.test -t robot-service-test .

# 執行
docker run --rm \
    -e TEST_WITH_RABBITMQ=1 \
    -e RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/ \
    robot-service-test
```

## CI/CD

### GitHub Actions

專案包含 `.github/workflows/test-rabbitmq.yml` 自動化 CI 流程：

- **單元測試**：多 Python 版本（3.10、3.11、3.12）
- **整合測試**：包含 RabbitMQ service
- **覆蓋率報告**：自動上傳到 Codecov

觸發條件：
- Push to main/develop/copilot/**
- Pull Request to main/develop

### 本地模擬 CI

```bash
# 模擬 CI 環境
export TEST_WITH_RABBITMQ=1
export RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# 執行完整測試
python3 run_tests.py all --with-rabbitmq --coverage
```

## 測試覆蓋率

### 生成覆蓋率報告

```bash
# HTML 報告
python3 run_tests.py all --coverage
open htmlcov/index.html

# XML 報告（用於 CI）
python3 -m pytest tests/ --cov=src --cov-report=xml
```

### 查看覆蓋率

```bash
# 終端輸出
python3 -m pytest tests/ --cov=src --cov-report=term-missing

# 指定模組
python3 -m pytest tests/ --cov=src/robot_service/queue --cov-report=term
```

## 測試選項說明

### run_tests.py 參數

```bash
# 測試模式
python3 run_tests.py <mode> [options]

Modes:
  unit          - 單元測試（不需要 RabbitMQ）
  integration   - 整合測試
  all           - 所有測試
  specific      - 特定測試（需要 --test-path）
  lint          - 程式碼檢查

Options:
  --with-rabbitmq     - 啟用 RabbitMQ 測試
  --coverage          - 生成覆蓋率報告
  --check-rabbitmq    - 檢查 RabbitMQ 可用性
  --test-path PATH    - 特定測試路徑
  -v, --verbose       - 詳細輸出
```

### pytest 參數

```bash
# 詳細輸出
python3 -m pytest tests/ -v

# 顯示標準輸出
python3 -m pytest tests/ -v -s

# 失敗時停止
python3 -m pytest tests/ -x

# 重新執行失敗的測試
python3 -m pytest tests/ --lf

# 只執行特定標記
python3 -m pytest tests/ -m "not integration"
```

## 常見問題

### Q: RabbitMQ 測試被跳過

**A**: 設定環境變數 `TEST_WITH_RABBITMQ=1`

```bash
export TEST_WITH_RABBITMQ=1
python3 -m pytest tests/test_rabbitmq_queue.py
```

### Q: 測試失敗："No module named 'aio_pika'"

**A**: 安裝依賴

```bash
pip install -r requirements.txt
```

### Q: RabbitMQ 連線失敗

**A**: 確認 RabbitMQ 運行中

```bash
# 啟動 RabbitMQ
docker-compose -f docker-compose.test.yml up -d rabbitmq

# 檢查狀態
docker-compose ps

# 檢查可用性
python3 run_tests.py integration --check-rabbitmq
```

### Q: 測試很慢

**A**: 使用並行執行

```bash
# 安裝 pytest-xdist
pip install pytest-xdist

# 並行執行
python3 -m pytest tests/ -n auto
```

### Q: 如何只測試特定功能

**A**: 使用測試路徑或標記

```bash
# 特定類別
python3 -m pytest tests/test_edge_rabbitmq_integration.py::TestEdgeQueueConfig

# 特定測試
python3 -m pytest tests/test_rabbitmq_queue.py::TestMessage::test_create_message

# 使用關鍵字
python3 -m pytest tests/ -k "rabbitmq"
```

## 最佳實踐

### 1. 測試前準備

```bash
# 1. 確保依賴已安裝
pip install -r requirements.txt

# 2. 檢查 linting
python3 run_tests.py lint

# 3. 啟動 RabbitMQ（如需要）
docker-compose -f docker-compose.test.yml up -d rabbitmq
```

### 2. 執行測試

```bash
# 先執行快速測試
python3 run_tests.py unit

# 再執行完整測試
python3 run_tests.py all --with-rabbitmq --coverage
```

### 3. 查看結果

```bash
# 查看覆蓋率報告
open htmlcov/index.html

# 查看失敗原因
python3 -m pytest tests/ --tb=long
```

### 4. 清理

```bash
# 停止 RabbitMQ
docker-compose -f docker-compose.test.yml down

# 清理臨時文件
rm -rf .pytest_cache htmlcov .coverage
```

## 參考資料

- [pytest 文件](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [RabbitMQ 部署指南](RABBITMQ_DEPLOYMENT.md)
- [專案 PROJECT_MEMORY.md](../PROJECT_MEMORY.md)
