# 本地指令歷史與快取功能

> **建立日期**：2025-12-10  
> **狀態**：✅ 已實作  
> **Phase**：Phase 3.2

## 📋 概述

本地指令歷史與快取功能為 Edge 環境提供離線指令追蹤與效能優化能力。透過 SQLite 持久化存儲歷史記錄，並使用記憶體 LRU 快取加速查詢。

### 核心功能

- ✅ **指令歷史記錄**：持久化存儲所有指令執行記錄
- ✅ **指令結果快取**：記憶體快取常用查詢結果
- ✅ **彈性查詢**：支援多條件篩選與分頁
- ✅ **自動清理**：過期資料自動清理機制
- ✅ **統計分析**：快取命中率與歷史統計

## 🏗️ 架構設計

### 三層架構

```
┌──────────────────────────────────────────────────────────┐
│                    History API Layer                      │
│  Flask Blueprint providing HTTP endpoints                 │
│  • GET /api/commands/history                             │
│  • GET /api/commands/cache/stats                         │
│  • POST /api/commands/history/cleanup                    │
└──────────────────────────────────────────────────────────┘
                           │
                           ↓
┌──────────────────────────────────────────────────────────┐
│              CommandHistoryManager Layer                  │
│  Unified interface for history and cache management      │
│  • record_command()                                      │
│  • update_command_status()                               │
│  • get_command_result()                                  │
│  • get_command_history()                                 │
└──────────────────────────────────────────────────────────┘
                     │                │
           ┌─────────┘                └─────────┐
           ↓                                    ↓
┌─────────────────────────┐      ┌─────────────────────────┐
│  CommandHistoryStore    │      │  CommandResultCache     │
│  (SQLite persistence)   │      │  (In-memory LRU)        │
│  • add_record()         │      │  • set()                │
│  • get_record()         │      │  • get()                │
│  • query_records()      │      │  • cleanup_expired()    │
│  • delete_old_records() │      │  • get_stats()          │
└─────────────────────────┘      └─────────────────────────┘
```

## 📦 模組說明

### 1. CommandHistoryStore

**檔案位置**：`src/common/command_history.py`

**功能**：提供指令歷史的 SQLite 持久化存儲

**資料模型**：

```python
@dataclass
class CommandRecord:
    command_id: str              # 指令 ID
    trace_id: str                # 追蹤 ID
    robot_id: str                # 機器人 ID
    command_type: str            # 指令類型
    command_params: Dict         # 指令參數
    status: str                  # 狀態
    created_at: datetime         # 建立時間
    updated_at: datetime         # 更新時間
    completed_at: Optional[datetime]  # 完成時間
    result: Optional[Dict]       # 執行結果
    error: Optional[Dict]        # 錯誤資訊
    execution_time_ms: Optional[int]  # 執行時間
    actor_type: Optional[str]    # 執行者類型
    actor_id: Optional[str]      # 執行者 ID
    source: Optional[str]        # 來源
    labels: Optional[Dict]       # 標籤
```

**主要方法**：

```python
# 新增記錄
store.add_record(record)

# 取得記錄
record = store.get_record(command_id)

# 查詢記錄（支援多條件篩選）
records = store.query_records(
    robot_id='robot_7',
    status='succeeded',
    start_time=start,
    end_time=end,
    limit=100,
    offset=0
)

# 統計數量
count = store.count_records(robot_id='robot_7')

# 更新記錄
store.update_record(command_id, {'status': 'succeeded'})

# 刪除舊記錄
deleted = store.delete_old_records(before=datetime)
```

### 2. CommandCache

**檔案位置**：`src/common/command_cache.py`

**功能**：提供記憶體 LRU 快取與 TTL 過期機制

**特性**：

- **LRU 淘汰策略**：自動淘汰最少使用的項目
- **TTL 支援**：支援項目過期時間
- **執行緒安全**：使用 `threading.RLock` 保護
- **統計資訊**：追蹤命中率、淘汰次數等

**使用範例**：

```python
cache = CommandCache(max_size=1000, default_ttl_seconds=3600)

# 設定快取
cache.set('key1', {'data': 'value'}, ttl_seconds=1800)

# 取得快取
value = cache.get('key1')

# 刪除快取
cache.delete('key1')

# 取得統計
stats = cache.get_stats()
# {
#   'size': 100,
#   'max_size': 1000,
#   'hits': 450,
#   'misses': 50,
#   'hit_rate': 90.0,
#   'evictions': 10,
#   'expirations': 5
# }
```

### 3. CommandResultCache

**檔案位置**：`src/common/command_cache.py`

**功能**：特化的指令結果快取，支援 trace_id 查詢

**使用範例**：

```python
cache = CommandResultCache(max_size=500, default_ttl_seconds=1800)

# 設定指令結果
cache.set_command_result(
    command_id='cmd-001',
    trace_id='trace-001',
    result={'status': 'succeeded'}
)

# 透過 command_id 取得
result = cache.get('cmd-001')

# 透過 trace_id 取得
result = cache.get_by_trace_id('trace-001')
```

### 4. CommandHistoryManager

**檔案位置**：`src/robot_service/command_history_manager.py`

**功能**：整合歷史與快取的統一管理介面

**使用範例**：

```python
manager = CommandHistoryManager(
    history_db_path='/path/to/history.db',
    cache_max_size=500,
    cache_ttl_seconds=1800
)

# 記錄指令
record = manager.record_command(
    robot_id='robot_7',
    command_type='robot.action',
    command_params={'action_name': 'go_forward'},
    actor_type='human',
    source='webui'
)

# 更新狀態
manager.update_command_status(
    command_id=record.command_id,
    status='succeeded',
    result={'position': {'x': 1.0}},
    execution_time_ms=2850
)

# 取得結果（優先從快取）
result = manager.get_command_result(command_id='cmd-001')

# 查詢歷史
records = manager.get_command_history(
    robot_id='robot_7',
    status='succeeded',
    limit=50
)

# 統計
count = manager.count_commands(robot_id='robot_7')

# 快取統計
stats = manager.get_cache_stats()

# 清理過期資料
manager.cleanup_expired_cache()
manager.cleanup_old_history(hours=720)  # 30 天
```

## 🌐 API 端點

### History API Blueprint

**檔案位置**：`src/robot_service/history_api.py`

**整合方式**：

```python
from flask import Flask
from src.robot_service.command_history_manager import CommandHistoryManager
from src.robot_service.history_api import create_history_api_blueprint

app = Flask(__name__)
manager = CommandHistoryManager()
history_bp = create_history_api_blueprint(manager)
app.register_blueprint(history_bp)
```

### 端點列表

#### 1. 取得指令歷史

```http
GET /api/commands/history?robot_id=robot_7&status=succeeded&limit=100&offset=0
```

**Query Parameters**:
- `robot_id` (可選): 機器人 ID
- `status` (可選): 狀態篩選
- `actor_type` (可選): 執行者類型
- `source` (可選): 來源篩選
- `start_time` (可選): 開始時間（ISO 格式）
- `end_time` (可選): 結束時間（ISO 格式）
- `limit` (可選): 返回記錄數上限，預設 100
- `offset` (可選): 查詢偏移量，預設 0

**Response**:

```json
{
  "status": "success",
  "data": {
    "records": [
      {
        "command_id": "cmd-001",
        "trace_id": "trace-001",
        "robot_id": "robot_7",
        "command_type": "robot.action",
        "status": "succeeded",
        "created_at": "2025-12-10T10:30:00Z",
        "execution_time_ms": 2850,
        "result": {"position": {"x": 1.0}}
      }
    ],
    "pagination": {
      "total": 250,
      "limit": 100,
      "offset": 0,
      "has_more": true
    }
  }
}
```

#### 2. 取得特定指令

```http
GET /api/commands/history/cmd-001
```

**Response**:

```json
{
  "status": "success",
  "data": {
    "command_id": "cmd-001",
    "trace_id": "trace-001",
    "status": "succeeded",
    ...
  }
}
```

#### 3. 取得快取統計

```http
GET /api/commands/cache/stats
```

**Response**:

```json
{
  "status": "success",
  "data": {
    "size": 450,
    "max_size": 500,
    "hits": 8520,
    "misses": 1240,
    "hit_rate": 87.3,
    "evictions": 150,
    "expirations": 85
  }
}
```

#### 4. 清空快取

```http
DELETE /api/commands/cache
```

#### 5. 清理過期快取

```http
POST /api/commands/cache/cleanup
```

#### 6. 清理舊歷史記錄

```http
POST /api/commands/history/cleanup
Content-Type: application/json

{
  "hours": 720
}
```

#### 7. 取得整體統計

```http
GET /api/commands/stats
```

**Response**:

```json
{
  "status": "success",
  "data": {
    "total_commands": 5420,
    "status_distribution": {
      "pending": 12,
      "running": 3,
      "succeeded": 5180,
      "failed": 225,
      "cancelled": 0
    },
    "cache": {
      "size": 450,
      "hit_rate": 87.3
    }
  }
}
```

## 🧪 測試

### 測試覆蓋

- ✅ `tests/core/test_command_history.py` (17 tests)
- ✅ `tests/core/test_command_cache.py` (25 tests)
- ✅ `tests/core/test_command_history_manager.py` (15 tests)

**總計**：57 個測試，100% 通過

### 執行測試

```bash
# 執行所有測試
python -m pytest tests/core/test_command_history.py -v
python -m pytest tests/core/test_command_cache.py -v
python -m pytest tests/core/test_command_history_manager.py -v

# 執行特定測試類別
python -m pytest tests/core/test_command_cache.py::TestCommandCache -v
```

## 📊 效能指標

### 快取效能

| 操作 | 時間複雜度 | 空間複雜度 |
|------|-----------|-----------|
| get() | O(1) | - |
| set() | O(1) | O(n) |
| delete() | O(1) | - |
| cleanup_expired() | O(n) | - |

### 資料庫效能

| 操作 | 時間複雜度 | 備註 |
|------|-----------|------|
| add_record() | O(1) | 有索引 |
| get_record() | O(1) | 主鍵查詢 |
| query_records() | O(log n) | 有索引 |
| count_records() | O(log n) | 有索引 |

### 建議配置

**開發環境**：
- `cache_max_size`: 100-500
- `cache_ttl_seconds`: 1800 (30 分鐘)
- `auto_cleanup_hours`: 168 (7 天)

**生產環境**：
- `cache_max_size`: 500-1000
- `cache_ttl_seconds`: 3600 (1 小時)
- `auto_cleanup_hours`: 720 (30 天)

## 🔧 使用場景

### 1. 離線指令追蹤

Edge 環境離線時仍可記錄指令執行歷史：

```python
manager = CommandHistoryManager()

# 記錄離線指令
record = manager.record_command(
    robot_id='robot_7',
    command_params={'action': 'go_forward'},
    source='edge_ui'
)

# 更新執行結果
manager.update_command_status(
    command_id=record.command_id,
    status='succeeded',
    execution_time_ms=2850
)
```

### 2. 快速查詢常用結果

減少重複計算，提升響應速度：

```python
# 檢查快取
result = manager.get_command_result(command_id='cmd-001')

if result is None:
    # 快取未命中，執行指令
    result = execute_command()
    
    # 快取結果
    manager.cache_command_result(
        command_id='cmd-001',
        trace_id='trace-001',
        result=result
    )
```

### 3. 歷史分析與報表

查詢歷史記錄進行分析：

```python
from datetime import timedelta

# 查詢最近 24 小時的成功指令
now = utc_now()
start_time = now - timedelta(hours=24)

records = manager.get_command_history(
    status='succeeded',
    start_time=start_time,
    limit=1000
)

# 統計執行時間
avg_time = sum(r.execution_time_ms for r in records) / len(records)
print(f"Average execution time: {avg_time}ms")
```

### 4. 定期清理維護

```python
import schedule

def cleanup_task():
    # 清理過期快取
    cache_cleaned = manager.cleanup_expired_cache()
    
    # 清理 30 天前的歷史
    history_cleaned = manager.cleanup_old_history(hours=720)
    
    print(f"Cleaned {cache_cleaned} cache entries, {history_cleaned} history records")

# 每天凌晨 2 點執行
schedule.every().day.at("02:00").do(cleanup_task)
```

## 🎯 最佳實踐

### 1. 合理設定快取大小

根據系統記憶體與查詢頻率調整：

```python
# 記憶體充足且查詢頻繁
manager = CommandHistoryManager(cache_max_size=1000)

# 記憶體受限
manager = CommandHistoryManager(cache_max_size=200)
```

### 2. 使用適當的 TTL

根據資料更新頻率設定：

```python
# 頻繁更新的資料（短 TTL）
manager.cache_command_result(cmd_id, trace_id, result, ttl_seconds=300)

# 穩定資料（長 TTL）
manager.cache_command_result(cmd_id, trace_id, result, ttl_seconds=7200)
```

### 3. 定期監控統計

```python
stats = manager.get_cache_stats()

# 命中率過低時考慮調整快取策略
if stats['hit_rate'] < 50:
    logger.warning(f"Low cache hit rate: {stats['hit_rate']}%")
    # 增加快取大小或調整 TTL
```

### 4. 錯誤處理

```python
try:
    result = manager.get_command_result(command_id='cmd-001')
except Exception as e:
    logger.error(f"Failed to get command result: {e}")
    # 回退到預設值或重新執行
```

## 🚀 未來擴展

- [ ] 支援 Redis 作為分散式快取
- [ ] 指令執行時間預測（基於歷史）
- [ ] 異常模式偵測與告警
- [ ] 資料匯出與匯入功能
- [ ] 更細緻的查詢條件（如正規表達式）
- [ ] 歷史資料壓縮存檔

## 📚 相關文件

- [architecture.md](../architecture.md) - 系統架構說明
- [proposal.md](../proposal.md) - 專案規格
- [Phase 3 規劃](../plans/PHASE3_EDGE_ALL_IN_ONE.md)
- [PROJECT_MEMORY.md](../PROJECT_MEMORY.md) - 專案記憶

---

**最後更新**：2025-12-10  
**維護者**：Robot Command Console Team
