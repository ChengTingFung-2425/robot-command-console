# JWT 認證整合指南

## 概述

進階指令共享 API 現在使用 JWT (JSON Web Token) 認證來保護敏感的 API 端點。這確保只有經過授權的使用者才能上傳、下載和評分指令。

## 架構

### 認證服務

**CloudAuthService** (`Cloud/api/auth.py`) 提供：
- JWT token 生成
- JWT token 驗證
- 密碼雜湊與驗證（使用 bcrypt）

### 受保護的端點

以下端點需要 JWT 認證：

| 端點 | 方法 | 功能 |
|------|------|------|
| `/api/cloud/shared_commands/upload` | POST | 上傳指令 |
| `/api/cloud/shared_commands/<id>/download` | POST | 下載指令 |
| `/api/cloud/shared_commands/<id>/rate` | POST | 評分指令 |
| `/api/cloud/shared_commands/<id>/comments` | POST | 新增留言 |

### 公開端點

以下端點不需要認證：

| 端點 | 方法 | 功能 |
|------|------|------|
| `/api/cloud/shared_commands/search` | GET | 搜尋指令 |
| `/api/cloud/shared_commands/<id>` | GET | 取得指令詳情 |
| `/api/cloud/shared_commands/<id>/comments` | GET | 取得留言 |
| `/api/cloud/shared_commands/<id>/ratings` | GET | 取得評分列表 |
| `/api/cloud/shared_commands/featured` | GET | 精選指令 |
| `/api/cloud/shared_commands/popular` | GET | 熱門指令 |
| `/api/cloud/shared_commands/categories` | GET | 分類列表 |

## 使用方式

### 1. 初始化認證服務

```python
from Cloud.shared_commands.api import init_shared_commands_auth

# 在應用啟動時初始化
JWT_SECRET = "your-secret-key-here"  # 應從環境變數或配置檔讀取
init_shared_commands_auth(JWT_SECRET)
```

### 2. 生成 JWT Token

```python
from Cloud.api.auth import CloudAuthService

auth_service = CloudAuthService(jwt_secret="your-secret-key")

# 生成 token
token = auth_service.generate_token(
    user_id="user-123",
    username="john_doe",
    role="user",
    expires_in=86400  # 24 小時
)

print(f"Token: {token}")
```

### 3. 使用 Token 呼叫 API

#### Python 範例

```python
import requests

# 設定 Authorization header
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

# 上傳指令
response = requests.post(
    'https://cloud.example.com/api/cloud/shared_commands/upload',
    json={
        'name': 'Patrol Command',
        'description': 'Advanced patrol routine',
        'category': 'patrol',
        'content': '[{"command": "go_forward", "params": {"distance": 100}}]',
        'author_username': 'john_doe',
        'author_email': 'john@example.com',
        'edge_id': 'edge-001',
        'original_command_id': 1,
        'version': 1
    },
    headers=headers
)

if response.status_code == 201:
    print("指令上傳成功！")
else:
    print(f"錯誤: {response.json()}")
```

#### curl 範例

```bash
# 上傳指令
curl -X POST https://cloud.example.com/api/cloud/shared_commands/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Command",
    "description": "A test command",
    "category": "test",
    "content": "[]",
    "author_username": "testuser",
    "author_email": "test@example.com",
    "edge_id": "edge-001",
    "original_command_id": 1
  }'
```

### 4. 使用 CloudSyncClient

CloudSyncClient 已更新以支援 JWT token：

```python
from Edge.cloud_sync.sync_service import CloudSyncService

# 使用 JWT token（推薦）
sync_service = CloudSyncService(
    cloud_api_url='https://cloud.example.com/api/cloud',
    edge_id='edge-001',
    jwt_token='your-jwt-token-here'
)

# 或使用舊的 api_key 參數（向後相容）
sync_service = CloudSyncService(
    cloud_api_url='https://cloud.example.com/api/cloud',
    edge_id='edge-001',
    api_key='your-api-key-here'  # 會自動轉換為 Bearer token
)

# 同步已批准的指令
results = sync_service.sync_approved_commands(db_session)
print(f"已上傳 {results['uploaded']} 個指令")
```

### 5. 更新 Token

```python
from Edge.cloud_sync.client import update_jwt_token

# 當 token 過期時，更新客戶端的 token
new_token = auth_service.generate_token(
    user_id="user-123",
    username="john_doe"
)

update_jwt_token(sync_service.client, new_token)
```

## 錯誤處理

### 常見錯誤

#### 401 Unauthorized - 缺少或無效的 token

```json
{
  "success": false,
  "error": "Unauthorized",
  "message": "Missing or invalid token"
}
```

**解決方式**：檢查 Authorization header 是否正確設定。

#### 401 Unauthorized - Token 過期

```json
{
  "success": false,
  "error": "Unauthorized",
  "message": "Invalid or expired token"
}
```

**解決方式**：生成新的 token 並重試。

#### 503 Service Unavailable - 服務未初始化

```json
{
  "success": false,
  "error": "Service Unavailable",
  "message": "Auth service not initialized"
}
```

**解決方式**：確保在應用啟動時呼叫 `init_shared_commands_auth()`。

## 安全性最佳實踐

### 1. 保護 JWT Secret

```python
import os

# 從環境變數讀取
JWT_SECRET = os.getenv('JWT_SECRET')

if not JWT_SECRET:
    raise ValueError("JWT_SECRET environment variable not set")

# 或從配置檔讀取
from configparser import ConfigParser

config = ConfigParser()
config.read('config.ini')
JWT_SECRET = config.get('security', 'jwt_secret')
```

### 2. 設定適當的過期時間

```python
# 短期 token（1 小時）- 用於一般操作
short_token = auth_service.generate_token(
    user_id="user-123",
    username="john_doe",
    expires_in=3600  # 1 小時
)

# 長期 token（7 天）- 用於裝置認證
long_token = auth_service.generate_token(
    user_id="edge-001",
    username="edge_device",
    role="device",
    expires_in=7 * 24 * 3600  # 7 天
)
```

### 3. Token 刷新機制

實作 token 刷新邏輯以避免服務中斷：

```python
def get_valid_token():
    """取得有效的 token，必要時刷新"""
    global current_token
    
    # 檢查 token 是否即將過期
    payload = auth_service.verify_token(current_token)
    if not payload:
        # Token 無效或過期，生成新的
        current_token = auth_service.generate_token(
            user_id="user-123",
            username="john_doe"
        )
    
    return current_token
```

### 4. HTTPS 傳輸

**生產環境必須使用 HTTPS** 來傳輸 JWT token，防止 token 被攔截。

```python
# 確保使用 HTTPS
CLOUD_API_URL = "https://cloud.example.com/api/cloud"  # ✅ 正確
# CLOUD_API_URL = "http://cloud.example.com/api/cloud"  # ❌ 不安全
```

## 測試

### 單元測試

```python
import unittest
from Cloud.api.auth import CloudAuthService

class TestJWTAuth(unittest.TestCase):
    def setUp(self):
        self.auth_service = CloudAuthService("test-secret")
    
    def test_generate_and_verify_token(self):
        token = self.auth_service.generate_token(
            user_id="test-user",
            username="testuser"
        )
        
        payload = self.auth_service.verify_token(token)
        
        self.assertIsNotNone(payload)
        self.assertEqual(payload["user_id"], "test-user")
        self.assertEqual(payload["username"], "testuser")
```

### 整合測試

執行完整的認證測試：

```bash
python -m unittest tests.cloud.test_shared_commands_auth -v
```

## 遷移指南

### 從 API Key 遷移到 JWT

#### 舊版（API Key）

```python
client = CloudSyncClient(
    cloud_api_url='https://cloud.example.com/api/cloud',
    edge_id='edge-001',
    api_key='static-api-key-123'
)
```

#### 新版（JWT Token）

```python
# 1. 生成 JWT token
auth_service = CloudAuthService(jwt_secret="your-secret")
token = auth_service.generate_token(
    user_id='edge-001',
    username='edge-device-001'
)

# 2. 使用 JWT token
client = CloudSyncClient(
    cloud_api_url='https://cloud.example.com/api/cloud',
    edge_id='edge-001',
    jwt_token=token
)
```

**注意**：舊的 `api_key` 參數仍然可用，但會被視為 JWT token。建議更新到新的參數名稱。

## 疑難排解

### Q: 為什麼我的 token 一直顯示過期？

**A**: 檢查伺服器和客戶端的時間是否同步。JWT 使用 UTC 時間戳，時間不同步會導致驗證失敗。

### Q: 如何檢查 token 的內容？

**A**: 可以使用 [jwt.io](https://jwt.io/) 解碼 token（注意：不要在公開網站上貼上生產環境的 token）。

```python
import jwt

# 解碼 token（不驗證簽名）
payload = jwt.decode(token, options={"verify_signature": False})
print(payload)
```

### Q: 可以撤銷已發出的 token 嗎？

**A**: 目前的實作不支援 token 撤銷。如需此功能，需要實作 token 黑名單機制或使用短期 token + refresh token 模式。

## 未來改進

- [ ] 實作 refresh token 機制
- [ ] 新增 token 撤銷支援
- [ ] 整合 OAuth2/OIDC
- [ ] 實作 role-based access control (RBAC)
- [ ] 新增 token 使用率限制

## 相關文件

- [Cloud API 文件](../Cloud/shared_commands/README.md)
- [Edge Sync 文件](../Edge/cloud_sync/README.md)
- [進階指令共享功能](./advanced-command-sharing.md)
- [安全性最佳實踐](../security/)

---

**最後更新**: 2026-02-24  
**版本**: v1.0.0
