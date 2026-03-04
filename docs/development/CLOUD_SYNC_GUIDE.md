# 雲端同步開發指南（Cloud Sync Guide）

> **建立日期**：2026-03-04
> **版本**：v1.0.0
> **狀態**：✅ 完成（Phase 3.3）
> **相關功能**：Edge ↔ Cloud 資料同步

---

## 概述

本指南說明 Edge 與 Cloud 之間的**資料同步策略**，供開發者了解架構設計、實作細節，以及如何在新功能中正確使用同步模組。

詳細的功能規格請參閱 [docs/features/data-sync-strategy.md](../features/data-sync-strategy.md)。

---

## 同步策略一覽

| 資料類型 | 同步方向 | 策略 |
|---------|---------|------|
| **用戶設定** | 雙向（Edge 主要，Cloud 備份） | 先試 API，失敗自動入佇列 |
| **進階指令** | 單向上傳（Edge → Cloud），按需下載 | 批准後上傳，社群共享 |
| **指令歷史** | 單向上傳（Edge → Cloud） | 可選上傳，雲端分析備份 |

---

## 模組結構

```
Edge/cloud_sync/
├── client.py           # CloudSyncClient：低階 API 呼叫
├── sync_queue.py       # CloudSyncQueue：SQLite FIFO 離線佇列
├── sync_service.py     # CloudSyncService：高階業務邏輯（整合佇列）
└── README.md           # 模組使用說明

Cloud/api/
├── data_sync.py        # Cloud 端資料同步 API（設定 + 歷史端點）
├── routes.py           # 一般文件存儲 API
└── auth.py             # JWT 認證服務
```

---

## 核心設計：先後發送（FIFO 離線佇列）

### 設計原則

**寫入操作**（`sync_user_settings`、`sync_command_history`）採用「先試後快取」策略：

```
呼叫 sync_user_settings() 或 sync_command_history()
         │
         ▼
    try 直接 API 呼叫
         │
    成功  ├──────────────► 完成（同步時間記錄到回應）
         │
    失敗  └──────────────► CloudSyncQueue.enqueue()
                                │
                                ▼
                          持久化到 SQLite（資料不遺失）
                                │
                    雲端恢復後呼叫 flush_queue()
                                │
                                ▼
                          按 seq 升序補發（FIFO）
```

### 使用 CloudSyncService

```python
from Edge.cloud_sync.sync_service import CloudSyncService

sync_service = CloudSyncService(
    cloud_api_url='https://cloud.example.com/api/cloud',
    edge_id='edge-001',
    jwt_token='your-jwt-token'
)

# 同步用戶設定（在線時直接寫入，離線時自動快取）
result = sync_service.sync_user_settings(
    user_id='user-123',
    settings={'theme': 'dark', 'language': 'zh-TW'}
)

if result.get('success'):
    print(f"已同步：{result['updated_at']}")
elif result.get('queued'):
    print(f"已快取（op_id={result['op_id']}），待補發")
```

### 雲端恢復後補發

```python
# 標記雲端已恢復
sync_service.set_cloud_available(True)

# 補發所有待處理的快取項目（FIFO 順序）
flush_result = sync_service.flush_queue()
print(f"補發完成：sent={flush_result['sent']}, remaining={flush_result['remaining']}")

# 查詢佇列狀態
stats = sync_service.get_queue_statistics()
print(f"佇列統計：{stats}")
```

---

## 開發新功能時的注意事項

### 1. 優先使用 CloudSyncService（高階介面）

`CloudSyncService` 已整合佇列邏輯，開發新同步功能時：
- ✅ 使用 `CloudSyncService` 的方法，自動獲得離線支援
- ❌ 避免直接呼叫 `CloudSyncClient`，除非確定不需要離線能力

### 2. 佇列操作的執行緒安全

`CloudSyncQueue` 使用 `threading.RLock` 保護所有 SQLite 操作。若需直接存取佇列：

```python
from Edge.cloud_sync.sync_queue import CloudSyncQueue

queue = CloudSyncQueue(db_path='/path/to/queue.db')

# 入隊（thread-safe）
op_id = queue.enqueue(
    operation_type='user_settings',
    user_id='user-123',
    data={'theme': 'dark'}
)

# 批次取出待處理項目（FIFO）
items = queue.dequeue_batch(batch_size=20)

# 標記完成
queue.mark_completed(op_id)

# 標記失敗（保留重試）
queue.mark_failed(op_id)
```

### 3. Cloud API 認證

所有 Cloud 端點需要 JWT Bearer token：

```python
# CloudSyncClient 自動附帶認證 header
client = CloudSyncClient(
    cloud_api_url='https://cloud.example.com/api/cloud',
    edge_id='edge-001',
    jwt_token=os.environ['CLOUD_JWT_TOKEN']  # 從環境變數讀取，勿硬編碼
)
```

### 4. 資料隔離（授權）

Cloud API 在驗證 JWT 後，會比對 token 中的 `user_id` 與 URL 路徑中的 `user_id`：
- **一般用戶**：只能存取自己的資料
- **Admin 角色**：可存取任意用戶資料

---

## 測試指南

### 單元測試

```bash
# 測試離線佇列
python -m pytest tests/edge/test_sync_queue.py -v

# 測試同步服務
python -m pytest tests/edge/test_cloud_sync_service.py -v

# 測試 Cloud API
python -m pytest tests/cloud/test_data_sync.py -v
```

### 模擬離線場景

```python
# 測試時可強制設定離線狀態
sync_service.set_cloud_available(False)

result = sync_service.sync_user_settings(
    user_id='test-user',
    settings={'theme': 'light'}
)
assert result.get('queued') is True

# 驗證資料已持久化
stats = sync_service.get_queue_statistics()
assert stats['pending'] >= 1
```

---

## 設定參考

```yaml
# config.yaml
cloud_sync:
  enabled: true
  api_url: https://cloud.example.com/api/cloud
  edge_id: edge-001
  jwt_token: your-jwt-token          # 建議從環境變數注入

  # 同步策略
  sync_settings: true                # 是否同步用戶設定（預設開啟）
  sync_history: false                # 是否同步指令歷史（隱私考量，預設關閉）
  local_history_days: 90             # 本地歷史保留天數
  auto_sync: false                   # 是否自動同步進階指令

  # 佇列設定
  queue_db_path: /var/data/sync_queue.db  # SQLite 佇列路徑
  queue_batch_size: 20               # 每批補發數量
  queue_max_retry: 3                 # 最大重試次數
```

---

## 相關文件

| 文件 | 說明 |
|------|------|
| [docs/features/data-sync-strategy.md](../features/data-sync-strategy.md) | 功能規格與 API 端點完整說明 |
| [Edge/cloud_sync/README.md](../../Edge/cloud_sync/README.md) | 模組使用說明與範例 |
| [Cloud/README.md](../../Cloud/README.md) | 雲端服務架構說明 |
| [docs/features/advanced-command-sharing.md](../features/advanced-command-sharing.md) | 進階指令共享功能 |
| [docs/memory/cloud-sync-ui-lessons.md](../memory/cloud-sync-ui-lessons.md) | 雲端同步 UI 開發經驗 |

---

**建立日期**：2026-03-04
**版本**：v1.0.0
**狀態**：✅ Phase 3.3 完成
