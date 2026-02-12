# 進階指令共享模組

此模組提供進階指令的雲端共享功能，是 Cloud/Server Layer 的核心組件之一。

## 功能概覽

- ✅ 上傳本地已批准的進階指令到雲端
- ✅ 從雲端瀏覽與搜尋共享指令
- ✅ 下載雲端指令到本地 Edge
- ✅ 評分與排名系統
- ✅ 留言與討論功能
- ✅ 精選與熱門指令推薦
- ✅ 同步日誌記錄

## 架構設計

```
┌────────────────────────────────────────────────────────────┐
│                   Cloud / Server Layer                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Shared Commands API                      │  │
│  │  • Upload   - 上傳指令                                │  │
│  │  • Search   - 搜尋指令                                │  │
│  │  • Download - 下載指令                                │  │
│  │  • Rate     - 評分指令                                │  │
│  │  • Comment  - 留言討論                                │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                    SQLAlchemy ORM                           │
│                           │                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   Database                            │  │
│  │  • shared_advanced_command                            │  │
│  │  • command_rating                                     │  │
│  │  • command_comment                                    │  │
│  │  • sync_log                                           │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                           │
                      HTTPS/WSS
                           │
┌────────────────────────────────────────────────────────────┐
│                     Edge Applications                       │
│  • 上傳本地已批准指令到雲端                                  │
│  • 從雲端下載指令到本地                                     │
│  • 可選連接雲端服務                                        │
└────────────────────────────────────────────────────────────┘
```

## 模組結構

```
Cloud/shared_commands/
├── __init__.py       # 模組初始化
├── models.py         # 資料模型定義
├── service.py        # 業務邏輯層
├── api.py            # REST API 端點
└── README.md         # 本文件
```

## 資料模型

### SharedAdvancedCommand

雲端共享的進階指令。

**欄位**：
- `id`: 主鍵
- `name`: 指令名稱
- `description`: 指令說明
- `category`: 指令分類
- `content`: 指令內容（JSON 格式）
- `version`: 版本號
- `author_username`: 作者用戶名
- `author_email`: 作者電子郵件
- `source_edge_id`: 來源 Edge 裝置 ID
- `original_command_id`: 原始指令 ID（Edge 上的 ID）
- `download_count`: 下載次數
- `usage_count`: 使用次數
- `average_rating`: 平均評分
- `rating_count`: 評分人數
- `is_public`: 是否公開
- `is_featured`: 是否精選
- `created_at`: 建立時間
- `updated_at`: 更新時間

### CommandRating

指令評分記錄。

**欄位**：
- `id`: 主鍵
- `command_id`: 指令 ID（外鍵）
- `user_username`: 用戶名
- `rating`: 評分（1-5）
- `comment`: 評論
- `created_at`: 建立時間
- `updated_at`: 更新時間

**約束**：
- 每個用戶對每個指令只能評分一次（unique constraint）

### CommandComment

指令留言記錄。

**欄位**：
- `id`: 主鍵
- `command_id`: 指令 ID（外鍵）
- `user_username`: 用戶名
- `content`: 留言內容
- `parent_comment_id`: 父留言 ID（支援回覆）
- `created_at`: 建立時間
- `updated_at`: 更新時間

### SyncLog

同步日誌記錄。

**欄位**：
- `id`: 主鍵
- `edge_id`: Edge 裝置 ID
- `command_id`: 指令 ID（外鍵）
- `action`: 動作（upload/download/update）
- `status`: 狀態（success/failed）
- `error_message`: 錯誤訊息
- `created_at`: 建立時間

## API 端點

### 上傳指令

```
POST /api/cloud/shared_commands/upload
Content-Type: application/json

{
  "name": "巡邏例行程序",
  "description": "機器人自動巡邏",
  "category": "patrol",
  "content": "[{\"command\": \"go_forward\"}, {\"command\": \"turn_left\"}]",
  "author_username": "user123",
  "author_email": "user@example.com",
  "edge_id": "edge-001",
  "original_command_id": 1,
  "version": 1
}
```

### 搜尋指令

```
GET /api/cloud/shared_commands/search?
    query=巡邏&
    category=patrol&
    min_rating=4.0&
    sort_by=rating&
    order=desc&
    limit=50&
    offset=0
```

### 取得指令詳情

```
GET /api/cloud/shared_commands/{command_id}
```

### 下載指令

```
POST /api/cloud/shared_commands/{command_id}/download
Content-Type: application/json

{
  "edge_id": "edge-001"
}
```

### 對指令評分

```
POST /api/cloud/shared_commands/{command_id}/rate
Content-Type: application/json

{
  "user_username": "user123",
  "rating": 5,
  "comment": "非常實用的指令"
}
```

### 取得評分列表

```
GET /api/cloud/shared_commands/{command_id}/ratings?limit=50&offset=0
```

### 新增留言

```
POST /api/cloud/shared_commands/{command_id}/comments
Content-Type: application/json

{
  "user_username": "user123",
  "content": "這個指令很好用",
  "parent_comment_id": null  # 可選，用於回覆
}
```

### 取得留言列表

```
GET /api/cloud/shared_commands/{command_id}/comments?limit=50&offset=0
```

### 取得精選指令

```
GET /api/cloud/shared_commands/featured?limit=10
```

### 取得熱門指令

```
GET /api/cloud/shared_commands/popular?limit=10
```

### 取得分類列表

```
GET /api/cloud/shared_commands/categories
```

## 使用方式

### 初始化資料庫

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from Cloud.shared_commands.models import Base

# 建立資料庫引擎
engine = create_engine('postgresql://user:pass@localhost/dbname')

# 建立資料表
Base.metadata.create_all(engine)

# 建立 session
Session = sessionmaker(bind=engine)
session = Session()
```

### 使用服務層

```python
from Cloud.shared_commands.service import SharedCommandService

# 建立服務實例
service = SharedCommandService(session)

# 上傳指令
command = service.upload_command(
    name="測試指令",
    description="這是一個測試",
    category="test",
    content='[{"command": "bow"}]',
    author_username="testuser",
    author_email="test@example.com",
    edge_id="edge-001",
    original_command_id=1
)

# 搜尋指令
commands, total = service.search_commands(
    query="測試",
    category="test",
    sort_by="rating"
)

# 下載指令
command = service.download_command(command_id=1, edge_id="edge-002")

# 評分
rating = service.rate_command(
    command_id=1,
    user_username="testuser",
    rating=5,
    comment="很好用"
)
```

### 整合 API 到 Flask 應用

```python
from flask import Flask
from Cloud.shared_commands.api import bp as shared_commands_bp

app = Flask(__name__)

# 註冊 blueprint
app.register_blueprint(shared_commands_bp)

if __name__ == '__main__':
    app.run(debug=True)
```

## 安全性考量

### 認證與授權

- **上傳指令**：需要驗證用戶身份與 Edge 裝置所有權
- **評分與留言**：需要登入用戶
- **下載指令**：公開指令可自由下載，私有指令需授權
- **管理功能**：設定精選指令需要 Admin 權限

### 輸入驗證

- 指令內容必須是有效的 JSON
- 評分必須在 1-5 之間
- 所有文字輸入需進行 XSS 防護
- 限制上傳頻率以防止濫用

### 資料隱私

- 用戶可選擇上傳時是否公開指令
- 不公開用戶的電子郵件地址
- 支援指令刪除請求
- 遵守 GDPR/CCPA 等隱私法規

## 效能優化

### 索引設計

- `category + average_rating`: 支援分類排序查詢
- `download_count`: 支援熱門指令查詢
- `is_featured + average_rating`: 支援精選指令查詢
- `user_username + command_id`: 防止重複評分

### 快取策略

- 精選指令與熱門指令使用 Redis 快取（TTL: 5 分鐘）
- 分類列表使用 Redis 快取（TTL: 10 分鐘）
- 指令詳情使用 CDN 快取

### 分頁

- 所有列表查詢都支援分頁（limit/offset）
- 預設每頁 50 筆，最大 100 筆

## 監控與日誌

### 關鍵指標

- 上傳成功率
- 下載次數統計
- 平均評分分布
- API 回應時間

### 日誌記錄

- 所有同步操作記錄到 `sync_log` 表
- 錯誤訊息記錄完整堆疊追蹤
- 使用 trace_id 追蹤完整請求鏈路

## 測試

### 單元測試

```bash
# 執行單元測試
python -m pytest tests/cloud/test_shared_commands_service.py -v
```

### 整合測試

```bash
# 執行整合測試
python -m pytest tests/cloud/test_shared_commands_api.py -v
```

## 未來擴展

- [ ] 指令版本管理與回退
- [ ] 指令標籤系統
- [ ] 指令收藏功能
- [ ] 指令 Fork 功能
- [ ] 指令相似度推薦
- [ ] 用戶信譽系統整合
- [ ] 指令執行統計分析
- [ ] 多語言支援

## 相關文件

- [專案架構](../../docs/architecture.md)
- [權威規格](../../docs/proposal.md)
- [Cloud Layer README](../README.md)
- [Phase 3 規劃](../../docs/plans/PHASE3_EDGE_ALL_IN_ONE.md)

---

**建立日期**: 2026-02-12  
**版本**: v1.0.0  
**狀態**: 初始實作完成  
**維護者**: Robot Command Console Team
