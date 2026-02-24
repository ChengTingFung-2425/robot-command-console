# 資料同步策略

> **Phase 3.3 功能**：Edge ↔ Cloud 資料同步  
> **建立日期**：2026-02-24  
> **狀態**：已實作

---

## 概覽

本文件描述 Edge 與 Cloud 之間的資料同步策略，涵蓋三種資料類型：

| 資料類型 | 同步方向 | 說明 |
|---------|---------|------|
| **用戶設定** | 雙向（Edge 主要，Cloud 備份） | 語言、主題、通知偏好等本地設定 |
| **進階指令** | 單向上傳（Edge → Cloud），按需下載（Cloud → Edge） | 已批准的自訂指令共享至社群 |
| **指令歷史** | 單向上傳（Edge → Cloud） | 執行記錄的雲端備份與分析 |

---

## 架構

```
┌─────────────────┐                     ┌─────────────────┐
│      Edge       │                     │     Cloud       │
│                 │                     │                 │
│  ┌───────────┐  │   上傳（批准後）    │  ┌───────────┐  │
│  │ 進階指令  │──┼────────────────────►│  │ 指令庫    │  │
│  │ 使用記錄  │  │                     │  │ 分析系統  │  │
│  └───────────┘  │   下載（按需）      │  └───────────┘  │
│                 │◄────────────────────┤                 │
│  ┌───────────┐  │                     │  ┌───────────┐  │
│  │ 本地快取  │  │                     │  │ 共享指令  │  │
│  └───────────┘  │                     │  └───────────┘  │
│                 │                     │                 │
│  ┌───────────┐  │   雙向同步          │  ┌───────────┐  │
│  │ 用戶設定  │◄─┼────────────────────►│  │ 用戶設定  │  │
│  │（本地主要）│  │                     │  │（雲端備份）│  │
│  └───────────┘  │                     │  └───────────┘  │
│                 │                     │                 │
│  ┌───────────┐  │   上傳（可選）      │  ┌───────────┐  │
│  │ 指令歷史  │──┼────────────────────►│  │ 歷史備份  │  │
│  └───────────┘  │                     │  └───────────┘  │
└─────────────────┘                     └─────────────────┘
```

---

## 模組結構

```
Edge/cloud_sync/
├── client.py           # CloudSyncClient：API 呼叫（進階指令 + 設定 + 歷史）
├── sync_service.py     # CloudSyncService：同步業務邏輯
└── README.md           # Edge 同步模組文件

Cloud/api/
├── data_sync.py        # Cloud 端資料同步 API（設定 + 歷史端點）
├── routes.py           # 一般文件存儲 API
└── auth.py             # JWT 認證服務
```

---

## Cloud API 整合方式

在 Flask 應用程式中註冊 Blueprint 並初始化：

```python
from flask import Flask
from Cloud.api.data_sync import data_sync_bp, init_data_sync_api

app = Flask(__name__)
app.register_blueprint(data_sync_bp)

init_data_sync_api(
    jwt_secret='your-secret-key',
    storage_path='/var/data/cloud_sync'
)
```

---

## Cloud API 端點

### 用戶設定同步

```
POST /api/cloud/data_sync/settings/{user_id}
```

上傳用戶設定到雲端備份。

**請求體**：
```json
{
  "settings": {
    "theme": "dark",
    "language": "zh-TW",
    "notification_enabled": true
  },
  "edge_id": "edge-001"
}
```

**回應**：
```json
{
  "success": true,
  "message": "Settings synced",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

---

```
GET /api/cloud/data_sync/settings/{user_id}
```

從雲端下載用戶設定備份。

**回應**：
```json
{
  "success": true,
  "data": {
    "user_id": "user-123",
    "settings": { "theme": "dark", "language": "zh-TW" },
    "edge_id": "edge-001",
    "updated_at": "2026-01-01T00:00:00Z"
  }
}
```

### 指令歷史同步

```
POST /api/cloud/data_sync/history/{user_id}
```

批次上傳指令執行歷史到雲端。雲端自動以 `command_id` 去重。

**請求體**：
```json
{
  "records": [
    {
      "command_id": "cmd-001",
      "trace_id": "trace-abc",
      "robot_id": "robot-1",
      "command_type": "robot.action",
      "status": "succeeded",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "edge_id": "edge-001"
}
```

**回應**：
```json
{
  "success": true,
  "synced_count": 1,
  "total": 42
}
```

---

```
GET /api/cloud/data_sync/history/{user_id}?limit=100&offset=0
```

從雲端查詢指令歷史。

**回應**：
```json
{
  "success": true,
  "data": {
    "records": [...],
    "total": 42
  }
}
```

---

## Edge 使用範例

### 初始化同步服務

```python
from Edge.cloud_sync.sync_service import CloudSyncService

sync_service = CloudSyncService(
    cloud_api_url='https://cloud.example.com/api/cloud',
    edge_id='edge-001',
    jwt_token='your-jwt-token'
)
```

### 同步用戶設定（備份）

```python
# 使用者更新設定後同步到雲端
result = sync_service.sync_user_settings(
    user_id='user-123',
    settings={
        'theme': 'dark',
        'language': 'zh-TW',
        'notification_enabled': True
    }
)

if result.get('success'):
    print(f"設定已同步，時間：{result['updated_at']}")
```

### 還原用戶設定（從備份）

```python
# 新裝置初始化或設定重置後還原
settings = sync_service.restore_user_settings(user_id='user-123')

if settings:
    print(f"已還原設定：{settings}")
    # 套用到本地 SharedStateManager
    await shared_state.update_user_settings(settings)
else:
    print("雲端無備份，使用預設設定")
```

### 同步指令歷史

```python
from Edge.robot_service.command_history_manager import CommandHistoryManager

history_manager = CommandHistoryManager()

# 取得最近 7 天的指令歷史
from datetime import datetime, timedelta, timezone
since = datetime.now(timezone.utc) - timedelta(days=7)
records = history_manager.get_command_history(start_time=since)

# 同步到雲端
result = sync_service.sync_command_history(
    user_id='user-123',
    records=[r.to_dict() for r in records]
)

print(f"已同步 {result.get('synced_count', 0)} 筆歷史記錄")
```

### 同步進階指令（已有功能）

```python
# 同步已批准的進階指令到雲端
from WebUI.app import db
results = sync_service.sync_approved_commands(db.session)
print(f"已上傳 {results['uploaded']} 個進階指令")

# 從雲端下載指令
commands = sync_service.browse_cloud_commands(
    category='patrol',
    min_rating=4.0,
    limit=20
)

# 下載並導入到本地
local_cmd = sync_service.download_and_import_command(
    command_id=123,
    db_session=db.session,
    user_id=1
)
```

---

## 安全性

### 認證
所有 Cloud API 端點需要 JWT token（`Authorization: Bearer <token>`）。

### 授權（資料隔離）
每個端點在驗證 JWT token 後，會進一步比對 token 中的 `user_id` 與 URL 路徑中的 `user_id`：
- **一般用戶**：只能存取自己的設定與歷史（`token.user_id == path.user_id`）
- **Admin 角色**：可以存取任意用戶的資料（用於管理用途）
- 不符合條件時返回 `403 Forbidden`

```python
# 認證通過後的授權邏輯示意
if token.role != 'admin' and token.user_id != path_user_id:
    return 403 Forbidden
```

### 路徑安全
`user_id` 參數只允許 `A-Za-z0-9_-` 字元且長度 1-64，防止路徑穿越攻擊。點號（`.`）等特殊字元會被拒絕。

### 併發安全
歷史記錄的讀寫操作使用執行緒鎖（threading.Lock），防止同一用戶的歷史檔案在高併發情境下發生競態條件。

---

## 設定（config.yaml）

```yaml
cloud_sync:
  enabled: true
  api_url: https://cloud.example.com/api/cloud
  edge_id: edge-001
  jwt_token: your-jwt-token

  # 同步策略
  sync_settings: true         # 是否同步用戶設定
  sync_history: false         # 是否同步指令歷史（隱私考量，預設關閉）
  local_history_days: 90      # 本地歷史保留天數
  auto_sync: false            # 是否自動同步進階指令
```

---

## 相關文件

- [Edge/cloud_sync/README.md](../../Edge/cloud_sync/README.md) - Edge 同步模組詳細說明
- [Cloud/README.md](../../Cloud/README.md) - 雲端服務架構
- [docs/features/advanced-command-sharing.md](advanced-command-sharing.md) - 進階指令共享功能
- [docs/plans/PHASE3_EDGE_ALL_IN_ONE.md](../plans/PHASE3_EDGE_ALL_IN_ONE.md) - Phase 3 規劃

---

**建立日期**：2026-02-24  
**版本**：v1.0.0  
**狀態**：已實作（Phase 3.3）
