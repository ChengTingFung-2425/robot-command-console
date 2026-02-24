# Edge ↔ Cloud 同步模組

此模組提供 Edge 應用程式與 Cloud 雲端服務之間的資料同步功能。

## 功能概覽

### 進階指令同步
- ✅ 上傳本地已批准的進階指令到雲端
- ✅ 從雲端瀏覽與搜尋共享指令
- ✅ 下載雲端指令到本地
- ✅ 雲端服務健康檢查
- ✅ 批量同步功能
- ✅ 錯誤處理與重試

### 用戶設定同步
- ✅ 備份本地用戶設定到雲端
- ✅ 從雲端還原用戶設定
- ✅ 雙向同步（Edge 為主要來源，Cloud 為備份）

### 指令歷史同步
- ✅ 上傳指令執行歷史到雲端（分析與備份）
- ✅ 從雲端下載歷史記錄（分頁查詢）
- ✅ 自動去重（以 command_id 為依據）

## 模組結構

```
Edge/cloud_sync/
├── __init__.py       # 模組初始化
├── client.py         # 雲端 API 客戶端
├── sync_service.py   # 同步服務
└── README.md         # 本文件
```

## 使用方式

### 基本設定

```python
from Edge.cloud_sync.sync_service import CloudSyncService

# 初始化同步服務
sync_service = CloudSyncService(
    cloud_api_url='https://cloud.example.com/api/cloud',
    edge_id='edge-001',
    api_key='your-api-key',  # 可選
    auto_sync=False
)
```

### 同步本地指令到雲端

```python
from WebUI.app import db

# 同步所有已批准的指令
results = sync_service.sync_approved_commands(db.session)

print(f"Total: {results['total']}")
print(f"Uploaded: {results['uploaded']}")
print(f"Failed: {results['failed']}")
```

### 瀏覽雲端指令

```python
# 瀏覽高評分指令
commands = sync_service.browse_cloud_commands(
    category='patrol',
    min_rating=4.0,
    limit=20
)

for cmd in commands:
    print(f"{cmd['name']} - Rating: {cmd['average_rating']}")
```

### 下載雲端指令到本地

```python
# 下載並導入指令
local_cmd = sync_service.download_and_import_command(
    command_id=123,
    db_session=db.session,
    user_id=1
)

if local_cmd:
    print(f"Imported command: {local_cmd.name}")
```

### 檢查雲端服務狀態

```python
status = sync_service.get_cloud_status()

if status['available']:
    print("Cloud service is available")
    print(f"Categories: {len(status.get('categories', []))}")
else:
    print("Cloud service is unavailable")
```

### 同步用戶設定（備份）

```python
# 備份本地用戶設定到雲端
result = sync_service.sync_user_settings(
    user_id='user-123',
    settings={'theme': 'dark', 'language': 'zh-TW'}
)

if result.get('success'):
    print(f"Settings backed up at {result['updated_at']}")
```

### 還原用戶設定（從雲端備份）

```python
# 在新裝置或重置後從雲端還原設定
settings = sync_service.restore_user_settings(user_id='user-123')

if settings:
    print(f"Restored settings: {settings}")
else:
    print("No cloud backup found, using defaults")
```

### 同步指令執行歷史

```python
from Edge.robot_service.command_history_manager import CommandHistoryManager

history_manager = CommandHistoryManager()
records = history_manager.get_command_history(limit=500)

result = sync_service.sync_command_history(
    user_id='user-123',
    records=[r.to_dict() for r in records]
)

print(f"Synced {result.get('synced_count', 0)} history records")
```

## 配置選項

### 環境變數

```bash
# 雲端 API URL
export CLOUD_API_URL=https://cloud.example.com/api/cloud

# Edge 裝置 ID
export EDGE_ID=edge-001

# API 金鑰（可選）
export CLOUD_API_KEY=your-api-key

# 自動同步（可選）
export AUTO_SYNC=true
```

### 配置文件（config.yaml）

```yaml
cloud_sync:
  enabled: true
  api_url: https://cloud.example.com/api/cloud
  edge_id: edge-001
  api_key: your-api-key
  auto_sync: false
  sync_interval: 3600  # 秒
```

## CLI 命令

```bash
# 同步已批准的指令到雲端
python -m Edge.cloud_sync sync-approved

# 瀏覽雲端指令
python -m Edge.cloud_sync browse --category patrol --min-rating 4.0

# 下載指令
python -m Edge.cloud_sync download --command-id 123 --user-id 1

# 檢查雲端狀態
python -m Edge.cloud_sync status
```

## API 客戶端

`CloudSyncClient` 提供低階 API 呼叫功能：

```python
from Edge.cloud_sync.client import CloudSyncClient

client = CloudSyncClient(
    cloud_api_url='https://cloud.example.com/api/cloud',
    edge_id='edge-001',
    api_key='your-api-key'
)

# 上傳單一指令
response = client.upload_command(
    name="test_command",
    description="Test",
    category="test",
    content='[{"command": "bow"}]',
    author_username="user123",
    author_email="user@example.com",
    original_command_id=1,
    version=1
)

# 搜尋指令
response = client.search_commands(
    query="patrol",
    category="patrol",
    min_rating=4.0
)

# 下載指令
response = client.download_command(command_id=123)

# 評分
response = client.rate_command(
    command_id=123,
    user_username="user123",
    rating=5,
    comment="很好用"
)

# 取得精選指令
response = client.get_featured_commands(limit=10)

# 取得熱門指令
response = client.get_popular_commands(limit=10)

# 取得分類
response = client.get_categories()
```

## 錯誤處理

```python
import requests

try:
    response = client.upload_command(...)
    if response.get('success'):
        print("Upload successful")
    else:
        print(f"Upload failed: {response.get('error')}")
except requests.HTTPError as e:
    print(f"HTTP error: {e}")
except requests.RequestException as e:
    print(f"Request failed: {e}")
```

## 安全性考量

### 認證

- 使用 API 金鑰進行認證
- 金鑰應存儲於環境變數或加密配置文件中
- 不應將金鑰提交到版本控制

### HTTPS

- 生產環境必須使用 HTTPS
- 驗證 SSL 憑證

### 資料驗證

- 上傳前驗證指令內容為有效 JSON
- 下載後驗證指令格式正確
- 限制同步頻率以防止濫用

## 監控與日誌

### 關鍵指標

- 同步成功率
- 同步失敗次數
- API 回應時間
- 下載次數

### 日誌級別

```python
import logging

# 設定日誌級別
logging.getLogger('Edge.cloud_sync').setLevel(logging.INFO)
```

## 測試

### 單元測試

```bash
python -m pytest tests/edge/test_cloud_sync_client.py -v
```

### 整合測試

```bash
python -m pytest tests/edge/test_cloud_sync_service.py -v
```

## 疑難排解

### 連線失敗

- 檢查網路連線
- 驗證雲端 API URL 是否正確
- 檢查防火牆設定

### 認證失敗

- 驗證 API 金鑰是否正確
- 檢查金鑰是否過期

### 同步失敗

- 查看日誌了解詳細錯誤
- 檢查指令內容格式是否正確
- 驗證用戶權限

## 相關文件

- [Cloud Shared Commands API](../../Cloud/shared_commands/README.md)
- [專案架構](../../docs/architecture.md)
- [Phase 3 規劃](../../docs/plans/PHASE3_EDGE_ALL_IN_ONE.md)

---

**建立日期**: 2026-02-12  
**版本**: v1.0.0  
**狀態**: 初始實作完成  
**維護者**: Robot Command Console Team
