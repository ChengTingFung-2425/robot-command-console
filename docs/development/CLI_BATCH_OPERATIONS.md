# CLI 批次操作功能設計

## 概述

CLI 批次操作模式專注於無頭部署環境中的批次指令執行，與 TUI（終端互動介面）形成互補：

- **TUI**：互動式操作、即時監控、人工介入
- **CLI**：批次操作、自動化腳本、無人值守

## 設計原則

### 1. 重用現有模組

- **ServiceCoordinator**: 服務生命週期管理
- **ServiceManager**: 佇列與指令處理
- **CommandProcessor**: 動作驗證與分派
- **CommandHistoryManager**: 指令歷史記錄
- **OfflineQueueService**: 離線緩衝支援

### 2. 多工（Mux）架構

支援同時處理多個機器人的批次指令：

```
批次檔案 → 批次解析器 → 多工調度器 → 佇列系統 → 多個機器人
                              ↓
                         執行追蹤器 → 結果輸出
```

### 3. 輸入格式支援

- **JSON**: 結構化指令序列
- **YAML**: 人類可讀的配置格式
- **CSV**: 簡單的表格式指令

## 核心功能

### 1. 批次檔案格式

#### JSON 格式

```json
{
  "batch_id": "batch-001",
  "description": "晨間例行動作",
  "robots": ["robot-001", "robot-002"],
  "commands": [
    {
      "robot_id": "robot-001",
      "action": "stand",
      "params": {},
      "priority": "normal",
      "timeout_ms": 5000
    },
    {
      "robot_id": "all",
      "action": "wave",
      "params": {"duration_ms": 3000},
      "priority": "normal"
    }
  ],
  "options": {
    "parallel": true,
    "stop_on_error": false,
    "retry_on_failure": 3,
    "delay_between_commands_ms": 500
  }
}
```

#### YAML 格式

```yaml
batch_id: batch-001
description: 晨間例行動作
robots:
  - robot-001
  - robot-002

commands:
  - robot_id: robot-001
    action: stand
    priority: normal
    timeout_ms: 5000
  
  - robot_id: all
    action: wave
    params:
      duration_ms: 3000

options:
  parallel: true
  stop_on_error: false
  retry_on_failure: 3
  delay_between_commands_ms: 500
```

#### CSV 格式

```csv
robot_id,action,params_json,priority,timeout_ms
robot-001,stand,{},normal,5000
robot-002,wave,"{\"duration_ms\": 3000}",normal,5000
all,stop,{},high,3000
```

### 2. CLI 指令

```bash
# 基本用法
python3 run_batch_cli.py --file batch.json

# 指定輸出格式
python3 run_batch_cli.py --file batch.yaml --output results.json

# 乾跑模式（dry-run）
python3 run_batch_cli.py --file batch.json --dry-run

# 並行度控制
python3 run_batch_cli.py --file batch.json --max-parallel 5

# 詳細日誌
python3 run_batch_cli.py --file batch.json --log-level DEBUG

# 監控模式（顯示進度）
python3 run_batch_cli.py --file batch.json --monitor

# 從標準輸入讀取
cat batch.json | python3 run_batch_cli.py --stdin

# 指定服務端點
python3 run_batch_cli.py --file batch.json --service-url http://localhost:5000
```

### 3. 多工調度策略

#### 並行執行

```python
# 同時發送指令到多個機器人
async def parallel_dispatch(commands: List[Command]) -> List[Result]:
    tasks = [
        dispatch_command(cmd)
        for cmd in commands
    ]
    return await asyncio.gather(*tasks, return_exceptions=True)
```

#### 順序執行

```python
# 按順序執行指令（一個完成後執行下一個）
async def sequential_dispatch(commands: List[Command]) -> List[Result]:
    results = []
    for cmd in commands:
        result = await dispatch_command(cmd)
        results.append(result)
        if result.status == "failed" and stop_on_error:
            break
    return results
```

#### 分組並行

```python
# 按機器人分組，組內順序執行，組間並行
async def grouped_dispatch(commands: List[Command]) -> List[Result]:
    groups = group_by_robot(commands)
    tasks = [
        sequential_dispatch(group_commands)
        for group_commands in groups.values()
    ]
    return await asyncio.gather(*tasks)
```

### 4. 執行追蹤與報告

#### 追蹤資訊

```json
{
  "batch_id": "batch-001",
  "start_time": "2025-12-11T04:00:00Z",
  "end_time": "2025-12-11T04:05:23Z",
  "duration_ms": 323000,
  "total_commands": 50,
  "successful": 48,
  "failed": 2,
  "status": "completed_with_errors",
  "commands": [
    {
      "command_id": "cmd-001",
      "robot_id": "robot-001",
      "action": "stand",
      "status": "success",
      "start_time": "2025-12-11T04:00:00Z",
      "end_time": "2025-12-11T04:00:02Z",
      "duration_ms": 2000,
      "trace_id": "trace-abc123"
    },
    {
      "command_id": "cmd-002",
      "robot_id": "robot-002",
      "action": "wave",
      "status": "failed",
      "error": "Robot offline",
      "start_time": "2025-12-11T04:00:02Z",
      "end_time": "2025-12-11T04:00:07Z",
      "duration_ms": 5000,
      "trace_id": "trace-def456",
      "retry_count": 3
    }
  ]
}
```

#### 輸出格式

**JSON 輸出** (預設)：
```bash
python3 run_batch_cli.py --file batch.json --output results.json
```

**CSV 輸出**（適合 Excel）：
```bash
python3 run_batch_cli.py --file batch.json --output results.csv --format csv
```

**終端輸出**（適合監控）：
```bash
python3 run_batch_cli.py --file batch.json --monitor

# 輸出示例：
Batch: batch-001 - 晨間例行動作
Progress: [████████░░] 80% (40/50 commands)
Success: 38 | Failed: 2 | Pending: 10
Estimated time remaining: 00:01:23
```

## 模組設計

### 1. 批次解析器 (BatchParser)

```python
class BatchParser:
    """解析批次檔案（JSON/YAML/CSV）"""
    
    def parse_json(self, file_path: str) -> BatchSpec
    def parse_yaml(self, file_path: str) -> BatchSpec
    def parse_csv(self, file_path: str) -> BatchSpec
    def validate(self, batch_spec: BatchSpec) -> bool
```

### 2. 批次執行器 (BatchExecutor)

```python
class BatchExecutor:
    """執行批次指令"""
    
    def __init__(
        self,
        service_manager: ServiceManager,
        history_manager: CommandHistoryManager,
        max_parallel: int = 10
    )
    
    async def execute_batch(
        self,
        batch_spec: BatchSpec,
        dry_run: bool = False
    ) -> BatchResult
    
    async def execute_parallel(self, commands: List[Command]) -> List[Result]
    async def execute_sequential(self, commands: List[Command]) -> List[Result]
    async def execute_grouped(self, commands: List[Command]) -> List[Result]
```

### 3. 進度追蹤器 (ProgressTracker)

```python
class ProgressTracker:
    """追蹤批次執行進度"""
    
    def start_batch(self, batch_id: str, total_commands: int)
    def update_progress(self, command_id: str, status: str)
    def get_summary(self) -> Dict[str, Any]
    def render_progress_bar(self) -> str
```

### 4. 結果輸出器 (ResultExporter)

```python
class ResultExporter:
    """輸出執行結果"""
    
    def export_json(self, result: BatchResult, file_path: str)
    def export_csv(self, result: BatchResult, file_path: str)
    def export_text(self, result: BatchResult, file_path: str)
    def print_summary(self, result: BatchResult)
```

## 錯誤處理

### 1. 重試機制

```python
async def execute_with_retry(
    command: Command,
    max_retries: int = 3,
    backoff_factor: float = 1.5
) -> Result:
    """指數退避重試"""
    for attempt in range(max_retries + 1):
        try:
            result = await execute_command(command)
            if result.status == "success":
                return result
        except Exception as e:
            if attempt == max_retries:
                return Result(status="failed", error=str(e))
            await asyncio.sleep(backoff_factor ** attempt)
```

### 2. 錯誤策略

- **stop_on_error**: 遇到錯誤立即停止
- **continue_on_error**: 忽略錯誤繼續執行
- **skip_robot_on_error**: 跳過失敗的機器人，繼續其他機器人

## 整合現有系統

### 1. 與 ServiceCoordinator 整合

```python
# CLI 使用 ServiceCoordinator 管理服務生命週期
coordinator = ServiceCoordinator()
queue_service = QueueService(...)
coordinator.register_service(queue_service)
await coordinator.start()

# 執行批次
executor = BatchExecutor(
    service_manager=queue_service.service_manager,
    history_manager=history_manager
)
result = await executor.execute_batch(batch_spec)
```

### 2. 與 CommandHistoryManager 整合

```python
# 批次執行的每個指令都記錄到歷史
for command in batch_spec.commands:
    history_manager.record_command(
        command_id=command.id,
        trace_id=command.trace_id,
        robot_id=command.robot_id,
        command_params=command.params,
        status="pending"
    )
```

### 3. 與 Queue 系統整合

```python
# 使用現有的優先權佇列系統
for command in batch_spec.commands:
    message = Message(
        id=command.id,
        payload=command.to_dict(),
        priority=command.priority,
        trace_id=command.trace_id
    )
    await service_manager.enqueue(message)
```

## 使用場景

### 1. 自動化測試

```yaml
# test_scenarios.yaml
batch_id: test-001
description: 自動化測試場景
robots: [robot-001]

commands:
  - action: stand
    timeout_ms: 3000
  - action: go_forward
    params: {duration_ms: 2000}
  - action: turn_left
    params: {duration_ms: 1000}
  - action: stop
```

### 2. 批次演示

```yaml
# demo_sequence.yaml
batch_id: demo-001
description: 機器人演示序列
robots: [robot-001, robot-002, robot-003]

commands:
  - robot_id: all
    action: stand
  - robot_id: all
    action: wave
    params: {duration_ms: 3000}
  - robot_id: robot-001
    action: dance_five
  - robot_id: all
    action: bow
```

### 3. 排程任務

```bash
# 使用 cron 排程批次任務
# 每天早上 8:00 執行晨間例行動作
0 8 * * * cd /path/to/project && python3 run_batch_cli.py --file morning_routine.json
```

## 效能考量

### 1. 並行度控制

```python
# 限制同時執行的指令數量，避免資源耗盡
MAX_PARALLEL = 10
semaphore = asyncio.Semaphore(MAX_PARALLEL)

async def dispatch_with_limit(command: Command):
    async with semaphore:
        return await dispatch_command(command)
```

### 2. 記憶體管理

```python
# 大批次檔案使用流式處理
async def process_large_batch(file_path: str):
    async for command in stream_parse_csv(file_path):
        await dispatch_command(command)
        # 避免一次性載入所有指令
```

### 3. 超時控制

```python
# 為每個指令設定超時
async def execute_with_timeout(command: Command):
    try:
        return await asyncio.wait_for(
            execute_command(command),
            timeout=command.timeout_ms / 1000
        )
    except asyncio.TimeoutError:
        return Result(status="timeout", error="Command timeout")
```

## 測試策略

### 1. 單元測試

```python
# tests/test_batch_parser.py
def test_parse_json_batch():
    parser = BatchParser()
    batch_spec = parser.parse_json("test_batch.json")
    assert batch_spec.batch_id == "test-001"
    assert len(batch_spec.commands) == 5
```

### 2. 整合測試

```python
# tests/test_batch_executor.py
async def test_execute_batch_parallel():
    executor = BatchExecutor(...)
    result = await executor.execute_batch(batch_spec)
    assert result.successful == 5
    assert result.failed == 0
```

### 3. 端到端測試

```bash
# 測試完整的批次執行流程
python3 run_batch_cli.py --file tests/fixtures/test_batch.json --dry-run
```

## 未來擴展

- [ ] 支援條件執行（if-then-else）
- [ ] 支援迴圈指令（repeat N times）
- [ ] 支援變數替換（參數化批次檔案）
- [ ] 支援分散式執行（多節點）
- [ ] 支援即時調整（熱更新批次參數）
- [ ] 支援視覺化進度（Web UI）
- [ ] 支援批次排程（定時執行）
- [ ] 支援批次範本（可重用配置）

## 相關文件

- [TUI 使用者指南](../user_guide/TUI_USER_GUIDE.md)
- [指令歷史功能](CLI_BATCH_OPERATIONS.md)
- [佇列系統架構](../features/queue-architecture.md)
- [服務協調器設計](../phase3/SERVICE_COORDINATOR.md)

---

**最後更新**: 2025-12-11
**狀態**: Phase 3.2 - 設計階段
