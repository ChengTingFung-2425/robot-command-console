# 進階指令共享功能

> **版本**: v1.0.0  
> **狀態**: ✅ Cloud/Edge 模組完成，待整合到 UI  
> **日期**: 2026-02-12  
> **Phase**: 3.3 Cloud 整合

## 功能概述

進階指令共享功能允許用戶將本地已批准的進階指令上傳到雲端，供社群瀏覽、下載、評分與討論。此功能是 Cloud/Server Layer 的核心組件，實現了 Edge-Cloud 協作的關鍵功能。

## 架構設計

### 三層架構

```
┌─────────────────────────────────────────┐
│         Cloud / Server Layer             │
│  ┌───────────────────────────────────┐  │
│  │  Shared Commands API & Service    │  │
│  │  • 指令上傳與存儲                 │  │
│  │  • 搜尋與篩選                     │  │
│  │  • 評分與排名                     │  │
│  │  • 留言與討論                     │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                    │
               HTTPS/WSS
                    │
┌─────────────────────────────────────────┐
│           Edge Layer                     │
│  ┌───────────────────────────────────┐  │
│  │  Cloud Sync Client & Service      │  │
│  │  • 本地指令上傳                   │  │
│  │  • 雲端指令瀏覽                   │  │
│  │  • 下載與導入                     │  │
│  │  • 健康檢查                       │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
                    │
          本地資料庫 & WebUI
                    │
┌─────────────────────────────────────────┐
│        本地進階指令管理                  │
│  • 建立與編輯                           │
│  • 審核流程                             │
│  • 執行與監控                           │
└─────────────────────────────────────────┘
```

## 核心組件

### 1. Cloud Layer (`Cloud/shared_commands/`)

#### 資料模型 (`models.py`)

- **SharedAdvancedCommand**: 雲端共享指令
  - 指令內容、版本、統計資訊
  - 作者資訊、來源 Edge ID
  - 下載次數、評分、精選狀態

- **CommandRating**: 評分記錄
  - 1-5 星評分
  - 評論內容
  - 每用戶每指令僅能評分一次

- **CommandComment**: 留言討論
  - 支援回覆（巢狀留言）
  - 時間戳記錄

- **SyncLog**: 同步日誌
  - 上傳/下載/更新記錄
  - 成功/失敗狀態
  - 錯誤訊息

#### 業務邏輯 (`service.py`)

```python
class SharedCommandService:
    def upload_command(...) -> SharedAdvancedCommand
    def search_commands(...) -> Tuple[List, int]
    def download_command(...) -> SharedAdvancedCommand
    def rate_command(...) -> CommandRating
    def add_comment(...) -> CommandComment
    def get_featured_commands(...) -> List
    def get_popular_commands(...) -> List
    def get_categories() -> List
```

#### REST API (`api.py`)

| 端點 | 方法 | 說明 |
|------|------|------|
| `/shared_commands/upload` | POST | 上傳指令 |
| `/shared_commands/search` | GET | 搜尋指令 |
| `/shared_commands/<id>` | GET | 取得指令詳情 |
| `/shared_commands/<id>/download` | POST | 下載指令 |
| `/shared_commands/<id>/rate` | POST | 評分指令 |
| `/shared_commands/<id>/ratings` | GET | 取得評分列表 |
| `/shared_commands/<id>/comments` | GET/POST | 留言討論 |
| `/shared_commands/featured` | GET | 精選指令 |
| `/shared_commands/popular` | GET | 熱門指令 |
| `/shared_commands/categories` | GET | 分類列表 |

### 2. Edge Layer (`Edge/cloud_sync/`)

#### 同步客戶端 (`client.py`)

```python
class CloudSyncClient:
    def upload_command(...) -> Dict
    def search_commands(...) -> Dict
    def download_command(...) -> Dict
    def rate_command(...) -> Dict
    def get_featured_commands(...) -> Dict
    def health_check() -> bool
```

#### 同步服務 (`sync_service.py`)

```python
class CloudSyncService:
    def sync_approved_commands(db_session) -> Dict
    def download_and_import_command(...) -> AdvancedCommand
    def browse_cloud_commands(...) -> List
    def get_cloud_status() -> Dict
```

## 使用流程

### 1. 上傳本地指令到雲端

```python
from Edge.cloud_sync.sync_service import CloudSyncService
from WebUI.app import db

# 初始化同步服務
sync_service = CloudSyncService(
    cloud_api_url='https://cloud.example.com/api/cloud',
    edge_id='edge-001',
    api_key='your-api-key'
)

# 同步所有已批准的指令
results = sync_service.sync_approved_commands(db.session)

# 結果統計
print(f"Total: {results['total']}")
print(f"Uploaded: {results['uploaded']}")
print(f"Failed: {results['failed']}")
```

### 2. 瀏覽雲端指令

```python
# 搜尋高評分的巡邏指令
commands = sync_service.browse_cloud_commands(
    category='patrol',
    min_rating=4.0,
    limit=20
)

for cmd in commands:
    print(f"{cmd['name']} - {cmd['average_rating']}⭐")
    print(f"Downloads: {cmd['download_count']}")
```

### 3. 下載並導入指令

```python
# 下載指定的雲端指令
local_cmd = sync_service.download_and_import_command(
    command_id=123,
    db_session=db.session,
    user_id=current_user.id
)

if local_cmd:
    print(f"Successfully imported: {local_cmd.name}")
    flash(f'已成功導入進階指令「{local_cmd.name}」')
```

### 4. 評分與留言

```python
from Edge.cloud_sync.client import CloudSyncClient

client = CloudSyncClient(...)

# 評分
client.rate_command(
    command_id=123,
    user_username='user123',
    rating=5,
    comment='非常實用的巡邏指令'
)
```

## 安全性設計

### 認證機制

- **API Key 認證**: Bearer Token 方式
- **來源驗證**: Edge ID 綁定
- **權限檢查**: 僅已批准的指令可上傳

### 資料驗證

- **JSON 格式驗證**: 指令內容必須為有效 JSON
- **評分範圍檢查**: 1-5 星
- **重複評分防護**: 每用戶每指令僅能評分一次
- **XSS 防護**: 所有文字輸入需清理

### 速率限制

- 上傳頻率限制（防止濫用）
- API 請求速率限制
- 下載次數記錄

## 配置選項

### 環境變數

```bash
# 雲端服務配置
export CLOUD_API_URL=https://cloud.example.com/api/cloud
export CLOUD_API_KEY=your-api-key
export EDGE_ID=edge-001

# 同步選項
export AUTO_SYNC=false
export SYNC_INTERVAL=3600  # 秒
```

### 配置文件 (config.yaml)

```yaml
cloud_sync:
  enabled: true
  api_url: https://cloud.example.com/api/cloud
  edge_id: edge-001
  api_key: your-api-key
  auto_sync: false
  sync_interval: 3600
  
  features:
    upload: true
    download: true
    rating: true
    comments: true
```

## 監控與指標

### 關鍵指標

- **上傳成功率**: 成功上傳數 / 總上傳數
- **下載次數**: 各指令下載統計
- **平均評分**: 指令品質指標
- **同步頻率**: Edge 與 Cloud 同步次數
- **API 回應時間**: 雲端服務效能

### 日誌記錄

```python
# 同步日誌
logger.info(f"Uploaded command '{name}' to cloud (ID={id})")
logger.error(f"Failed to upload command: {error}")

# 下載日誌
logger.info(f"Downloaded command {id} from cloud")

# 健康檢查日誌
logger.warning("Cloud service unavailable")
```

## 測試覆蓋

### Cloud Layer 測試

```bash
python -m pytest tests/cloud/test_shared_commands_service.py -v
# 14/14 tests passed ✅
```

**測試項目**:
- 上傳新指令
- 更新現有指令
- 搜尋與篩選
- 下載指令
- 評分功能
- 留言討論
- 精選與熱門指令
- 分類統計

### Edge Layer 測試

```bash
python -m pytest tests/edge/test_cloud_sync_client.py -v
# 4/4 tests passed ✅
```

**測試項目**:
- 上傳指令成功
- 搜尋指令成功
- 健康檢查成功/失敗

## 未來擴展

### Phase 3.4+ 規劃

- [ ] **WebUI 整合**
  - 雲端指令瀏覽介面
  - 一鍵上傳/下載功能
  - 評分與留言 UI

- [ ] **自動同步**
  - 定時自動上傳新批准的指令
  - 自動檢查雲端更新
  - 衝突解決機制

- [ ] **進階功能**
  - 指令版本管理
  - 指令 Fork 功能
  - 指令相似度推薦
  - 標籤系統

- [ ] **分析與報表**
  - 用戶上傳統計
  - 熱門指令排行榜
  - 分類趨勢分析

- [ ] **社群功能**
  - 用戶信譽系統
  - 指令收藏功能
  - 關注作者功能

## 相關文件

- [Cloud Shared Commands API](../../Cloud/shared_commands/README.md)
- [Edge Cloud Sync](../../Edge/cloud_sync/README.md)
- [專案架構](../architecture.md)
- [Phase 3 規劃](../plans/PHASE3_EDGE_ALL_IN_ONE.md)
- [使用者參與系統](user-engagement-system.md)

## 疑難排解

### 上傳失敗

**問題**: 指令上傳失敗  
**可能原因**:
- 網路連線問題
- API 金鑰無效
- 指令格式錯誤
- 雲端服務停機

**解決方法**:
1. 檢查網路連線
2. 驗證 API 金鑰與權限
3. 查看日誌了解詳細錯誤
4. 檢查雲端服務狀態

### 下載失敗

**問題**: 無法下載雲端指令  
**可能原因**:
- 指令不存在或已刪除
- 指令不公開
- 網路問題

**解決方法**:
1. 確認指令 ID 正確
2. 檢查指令是否公開
3. 重試下載

### 同步衝突

**問題**: 本地與雲端指令衝突  
**處理方式**:
- 優先保留本地版本
- 提示用戶選擇
- 保存衝突記錄

---

**維護者**: Robot Command Console Team  
**聯絡**: [GitHub Issues](https://github.com/ChengTingFung-2425/robot-command-console/issues)
