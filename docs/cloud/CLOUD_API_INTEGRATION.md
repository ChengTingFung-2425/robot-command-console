# Cloud API 整合文件

## 概述

雲服務 API 整合提供了完整的檔案上傳、下載、認證和 Edge-Cloud 同步功能。此實作基於 Server-Edge-Runner 三層架構設計。

## 架構

```
┌─────────────────────────────────────────────┐
│           Cloud Layer (Server)              │
│  ┌─────────────────────────────────────┐   │
│  │     Cloud API Services              │   │
│  │  • 認證服務 (CloudAuthService)       │   │
│  │  • 儲存服務 (CloudStorageService)    │   │
│  │  • Flask REST API (routes.py)       │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
                    │
              HTTPS/REST API
                    │
┌─────────────────────────────────────────────┐
│            Edge Layer (Client)              │
│  ┌─────────────────────────────────────┐   │
│  │   Edge Cloud Sync Client            │   │
│  │  • 同步客戶端 (CloudSyncClient)      │   │
│  │  • 本地快取                         │   │
│  │  • 離線支援                         │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

## 核心功能

### 1. 認證服務 (CloudAuthService)

提供 JWT Token 認證和密碼管理功能。

**功能：**
- 生成 JWT Token
- 驗證 JWT Token
- 密碼雜湊
- 密碼驗證

**使用範例：**
```python
from Cloud.api.auth import CloudAuthService

# 建立服務
auth_service = CloudAuthService(jwt_secret="your-secret-key")

# 生成 Token
token = auth_service.generate_token(
    user_id="user-123",
    username="test_user",
    role="user"
)

# 驗證 Token
payload = auth_service.verify_token(token)
```

### 2. 儲存服務 (CloudStorageService)

提供檔案上傳、下載、管理功能。

**功能：**
- 檔案上傳（支援多類別）
- 檔案下載
- 檔案刪除
- 列出檔案
- 儲存統計

**使用範例：**
```python
from Cloud.api.storage import CloudStorageService

# 建立服務
storage_service = CloudStorageService(
    storage_path="/var/cloud/storage",
    max_file_size=100 * 1024 * 1024  # 100MB
)

# 上傳檔案
with open("file.txt", "rb") as f:
    result = storage_service.upload_file(
        file_data=f,
        filename="file.txt",
        user_id="user-123",
        category="documents"
    )

# 下載檔案
content = storage_service.download_file(
    file_id=result["file_id"],
    user_id="user-123",
    category="documents"
)
```

### 3. REST API 端點 (routes.py)

提供完整的 HTTP REST API 介面。

**端點清單：**

| 端點 | 方法 | 認證 | 功能 |
|------|------|------|------|
| `/api/cloud/health` | GET | ❌ | 健康檢查 |
| `/api/cloud/auth/token` | POST | ❌ | 生成 Token |
| `/api/cloud/storage/upload` | POST | ✅ | 上傳檔案 |
| `/api/cloud/storage/download/<file_id>` | GET | ✅ | 下載檔案 |
| `/api/cloud/storage/files` | GET | ✅ | 列出檔案 |
| `/api/cloud/storage/files/<file_id>` | DELETE | ✅ | 刪除檔案 |
| `/api/cloud/storage/stats` | GET | ✅ | 儲存統計 |

**使用範例：**
```bash
# 生成 Token
curl -X POST http://localhost:5000/api/cloud/auth/token \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-123", "username": "test"}'

# 上傳檔案
curl -X POST http://localhost:5000/api/cloud/storage/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@test.txt" \
  -F "category=documents"

# 下載檔案
curl -X GET http://localhost:5000/api/cloud/storage/download/<file_id> \
  -H "Authorization: Bearer <token>" \
  -o downloaded_file.txt
```

### 4. Edge 同步客戶端 (CloudSyncClient)

提供 Edge 與 Cloud 之間的同步功能。

**功能：**
- 健康檢查
- 檔案上傳
- 檔案下載
- 列出檔案
- 刪除檔案
- 儲存統計
- 自動同步（雙向）

**使用範例：**
```python
from Edge.cloud_client.sync_client import CloudSyncClient

# 建立客戶端
client = CloudSyncClient(
    cloud_api_url="http://localhost:5000/api/cloud",
    token="your-jwt-token"
)

# 健康檢查
health = client.health_check()

# 上傳檔案
result = client.upload_file("/path/to/file.txt", category="documents")

# 同步目錄
sync_result = client.sync_files(
    local_dir="/path/to/local/dir",
    category="documents",
    direction="both"  # "upload", "download", or "both"
)
```

## 整合到 Flask 應用

```python
from flask import Flask
from Cloud.api.routes import cloud_bp, init_cloud_services

app = Flask(__name__)

# 初始化雲服務
init_cloud_services(
    jwt_secret="your-secret-key",
    storage_path="/var/cloud/storage"
)

# 註冊 Blueprint
app.register_blueprint(cloud_bp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

## 測試

運行測試套件：

```bash
# 運行所有測試
python3 -m unittest tests.test_cloud_api -v

# 運行特定測試類別
python3 -m unittest tests.test_cloud_api.TestCloudAuthService -v
python3 -m unittest tests.test_cloud_api.TestCloudStorageService -v
```

## 安全性考量

1. **JWT Token 安全**
   - 使用強密鑰（至少 32 位元組）
   - Token 有過期時間（預設 24 小時）
   - 生產環境必須使用 HTTPS

2. **檔案儲存安全**
   - 檔案大小限制（預設 100MB）
   - 使用 SHA-256 雜湊避免重複
   - 按使用者和類別隔離儲存

3. **密碼安全**
   - 使用 bcrypt 雜湊（強度可調整）
   - 永不儲存明文密碼

## 配置建議

### 開發環境
```python
JWT_SECRET = "dev-secret-key"
STORAGE_PATH = "/tmp/cloud_storage"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
```

### 生產環境
```python
JWT_SECRET = os.environ.get("JWT_SECRET")  # 從環境變數讀取
STORAGE_PATH = "/var/cloud/storage"
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
```

## 效能優化

1. **檔案儲存**
   - 使用內容雜湊去重
   - 分層目錄結構（類別/使用者）
   - 可擴展至 S3 相容儲存

2. **API 效能**
   - 支援串流下載
   - 檔案分塊上傳（可擴展）
   - 適當的逾時設定

## 未來擴展

- [ ] S3 相容物件儲存整合
- [ ] 檔案版本控制
- [ ] 檔案分享功能
- [ ] 批次操作 API
- [ ] WebSocket 即時同步
- [ ] 檔案加密
- [ ] 壓縮支援

## 相關文件

- [proposal.md](../proposal.md) - 權威規格
- [architecture.md](../architecture.md) - 架構說明
- [Cloud/README.md](../../Cloud/README.md) - Cloud 服務總覽
- [test_cloud_api.py](../../tests/test_cloud_api.py) - 測試範例

## 支援

如有問題或建議，請參閱專案文件或提交 Issue。

---

**版本**: 1.0.0  
**最後更新**: 2026-02-12  
**維護者**: Robot Command Console Team
