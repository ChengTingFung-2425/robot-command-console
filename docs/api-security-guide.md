# API 與安全性使用指南

本文件介紹 Robot Command Console 的 API 規範和安全功能使用方法。

## 目錄

- [API 版本控制](#api-版本控制)
- [認證與授權](#認證與授權)
- [OpenAPI 規範](#openapi-規範)
- [秘密管理](#秘密管理)
- [安全最佳實踐](#安全最佳實踐)
- [常見問題](#常見問題)

## API 版本控制

### 版本策略

API 使用路徑前綴進行版本控制：
- **當前版本**: `v1`
- **端點格式**: `/v1/{resource}`
- **向後相容**: 舊的 `/api/` 前綴仍然支援

### 範例

```bash
# v1 API（推薦）
curl http://localhost:8000/v1/command

# 舊格式（向後相容）
curl http://localhost:8000/api/command
```

### 版本變更政策

- 次要版本變更（例如新增端點）不會影響現有功能
- 主要版本變更會在新路徑前綴下發布（例如 `/v2/`）
- 舊版本會在宣布棄用後至少維護 6 個月

## 認證與授權

### 認證流程

#### 1. 註冊使用者

```bash
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "username": "myuser",
    "password": "securepass123",
    "role": "operator"
  }'
```

**回應：**
```json
{
  "message": "註冊成功",
  "user_id": "user123"
}
```

#### 2. 登入獲取 Token

```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "myuser",
    "password": "securepass123"
  }'
```

**回應：**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user_id": "user123",
  "role": "operator",
  "expires_at": "2025-11-21T03:31:20.213Z"
}
```

#### 3. 使用 Token 存取 API

```bash
curl -X GET http://localhost:8000/v1/robots \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### 4. Token 輪替

```bash
curl -X POST http://localhost:8000/v1/auth/rotate \
  -H "Authorization: Bearer <current_token>"
```

**回應：**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2025-11-21T03:31:20.213Z"
}
```

### 角色與權限

#### 角色定義

| 角色 | 權限 | 說明 |
|------|------|------|
| **admin** | `*`（所有權限） | 系統管理員，可執行所有操作 |
| **operator** | `robot.*`, `command.*` | 操作員，可控制機器人和管理指令 |
| **viewer** | `robot.status`, `command.view` | 觀察者，只能查看狀態 |

#### 權限檢查

系統會在每個操作前檢查使用者權限。如果權限不足，會返回 403 Forbidden 錯誤。

### Token 配置

Token 過期時間可通過環境變數配置：

```bash
# 設定 token 有效期為 12 小時
export MCP_JWT_EXPIRATION_HOURS=12

# 設定 JWT secret（生產環境必須使用強健的隨機字串）
export MCP_JWT_SECRET="your-very-secure-secret-key-at-least-32-chars"
```

### 公開端點

以下端點不需要認證：
- `/health` - 健康檢查
- `/metrics` - Prometheus metrics
- `/v1/auth/login` - 登入

## OpenAPI 規範

### 查看 API 文件

OpenAPI 規範檔案位於專案根目錄：
```
openapi.yaml
```

### 使用 Swagger UI

1. **在線查看器**：
   - 訪問 [Swagger Editor](https://editor.swagger.io/)
   - 複製 `openapi.yaml` 內容並貼上

2. **本地查看**：
   ```bash
   # 安裝 swagger-ui
   npm install -g swagger-ui-watcher
   
   # 啟動查看器
   swagger-ui-watcher openapi.yaml
   ```

### API 合約測試

使用 OpenAPI 規範進行合約測試：

```python
import yaml
from openapi_spec_validator import validate_spec

# 驗證規範
with open('openapi.yaml', 'r') as f:
    spec = yaml.safe_load(f)
    validate_spec(spec)
```

### 請求驗證

所有請求都會根據 OpenAPI 規範中的 schema 進行驗證。無效請求會返回 400 Bad Request 錯誤，並附帶詳細的驗證錯誤訊息。

## 秘密管理

### 秘密儲存後端

系統提供可插拔的秘密儲存後端：

#### 1. 環境變數儲存（預設，唯讀）

```bash
export MCP_JWT_SECRET="my-secret"
export APP_TOKEN="my-app-token"
```

#### 2. 檔案儲存（可讀寫）

```bash
# 使用預設路徑 ~/.robot-console/secrets.json
export MCP_SECRET_STORAGE_BACKEND=file

# 使用自訂路徑
export MCP_SECRET_STORAGE_FILE_PATH=/secure/path/secrets.json
```

#### 3. 鏈式儲存（預設）

結合環境變數和檔案儲存，按優先級讀取：

```bash
export MCP_SECRET_STORAGE_BACKEND=chained
```

讀取順序：
1. 環境變數
2. 檔案儲存

寫入：只會寫入到檔案儲存（環境變數儲存不支援寫入）

#### 4. Keychain 儲存（macOS，需要額外套件）

```bash
export MCP_SECRET_STORAGE_BACKEND=keychain
pip install keyring
```

#### 5. DPAPI 儲存（Windows，需要額外套件）

```bash
export MCP_SECRET_STORAGE_BACKEND=dpapi
pip install pywin32
```

### 程式化使用秘密儲存

```python
from MCP.config import MCPConfig

# 獲取秘密儲存實例
storage = MCPConfig.get_secret_storage()

# 設定秘密
storage.set_secret("API_KEY", "my-api-key")

# 讀取秘密
api_key = storage.get_secret("API_KEY")

# 刪除秘密
storage.delete_secret("API_KEY")

# 列出所有秘密鍵
keys = storage.list_secrets()
```

### 秘密輪替

建議定期輪替秘密：

```bash
# 1. 生成新的 JWT secret
NEW_SECRET=$(openssl rand -hex 32)

# 2. 更新環境變數或秘密儲存
export MCP_JWT_SECRET=$NEW_SECRET

# 3. 重啟服務
# 4. 所有使用者需要重新登入獲取新 token
```

## 安全最佳實踐

### 開發環境

1. **使用環境變數**：
   ```bash
   export MCP_JWT_SECRET="dev-secret-not-for-production"
   export APP_TOKEN="dev-token-$(date +%s)"
   ```

2. **使用短期 token**：
   ```bash
   export MCP_JWT_EXPIRATION_HOURS=1
   ```

3. **啟用詳細日誌**：
   ```bash
   export MCP_LOG_LEVEL=DEBUG
   ```

### 生產環境

1. **強健的秘密**：
   ```bash
   # 使用至少 32 字元的隨機字串
   MCP_JWT_SECRET=$(openssl rand -hex 32)
   APP_TOKEN=$(openssl rand -hex 32)
   ```

2. **使用外部秘密管理**：
   - AWS Secrets Manager
   - HashiCorp Vault
   - Azure Key Vault
   - Google Secret Manager

3. **強制 HTTPS**：
   ```bash
   # 在反向代理（nginx, HAProxy）中配置 HTTPS
   # 並重定向所有 HTTP 請求到 HTTPS
   ```

4. **限制 CORS**：
   ```bash
   export MCP_CORS_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
   ```

5. **實施速率限制**：
   ```bash
   # 在反向代理層級實施
   # 例如 nginx:
   limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
   ```

6. **監控和警報**：
   - 監控認證失敗率
   - 監控異常請求模式
   - 設定 Prometheus 警報規則

### Docker 部署

```dockerfile
# Dockerfile 範例
FROM python:3.12-slim

WORKDIR /app

# 安裝依賴
COPY requirements.txt MCP/requirements.txt ./
RUN pip install -r requirements.txt -r MCP/requirements.txt

# 複製程式碼
COPY . .

# 非 root 使用者運行
RUN useradd -m -u 1000 robot && chown -R robot:robot /app
USER robot

# 暴露端口
EXPOSE 8000

# 啟動服務
CMD ["python3", "-m", "uvicorn", "MCP.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# 運行 Docker 容器
docker run -d \
  -p 8000:8000 \
  -e MCP_JWT_SECRET="$(openssl rand -hex 32)" \
  -e MCP_JWT_EXPIRATION_HOURS=24 \
  -v /secure/secrets:/app/.robot-console:ro \
  robot-command-console
```

## 常見問題

### Q: Token 過期後會發生什麼？

A: Token 過期後，API 會返回 401 Unauthorized 錯誤。使用者需要重新登入或使用 token rotation 端點獲取新 token。

```json
{
  "error": "UNAUTHORIZED",
  "message": "Invalid or expired token",
  "trace_id": "trace-123",
  "timestamp": "2025-11-20T03:31:20.213Z"
}
```

### Q: 如何處理 token rotation？

A: 使用 `/v1/auth/rotate` 端點：

```python
import requests

# 使用當前 token 獲取新 token
response = requests.post(
    'http://localhost:8000/v1/auth/rotate',
    headers={'Authorization': f'Bearer {current_token}'}
)

if response.status_code == 200:
    new_token = response.json()['token']
    # 使用新 token 進行後續請求
```

### Q: 如何在多個服務之間共享秘密？

A: 使用集中式秘密管理服務或共享的秘密儲存後端：

1. **檔案儲存**（簡單，適用於單機或共享檔案系統）：
   ```bash
   export MCP_SECRET_STORAGE_FILE_PATH=/shared/secrets/robot-console.json
   ```

2. **外部秘密管理**（推薦用於生產環境）：
   ```bash
   # AWS Secrets Manager 範例
   aws secretsmanager get-secret-value --secret-id robot-console/jwt-secret
   ```

### Q: 如何實施密碼政策？

A: 在註冊端點前添加驗證：

```python
import re

def validate_password(password: str) -> bool:
    """
    驗證密碼強度：
    - 至少 8 字元
    - 包含大寫字母
    - 包含小寫字母
    - 包含數字
    - 包含特殊字元
    """
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True
```

### Q: 如何除錯認證問題？

A: 啟用 DEBUG 日誌級別：

```bash
export MCP_LOG_LEVEL=DEBUG
python3 MCP/start.py
```

檢查日誌中的認證事件：
- Token 驗證成功/失敗
- 權限檢查結果
- 審計事件

### Q: 如何測試 API？

A: 使用 curl、Postman 或 Python requests：

```bash
# 測試健康檢查
curl http://localhost:8000/health

# 測試登入
TOKEN=$(curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"testpass"}' \
  | jq -r '.token')

# 測試認證端點
curl http://localhost:8000/v1/robots \
  -H "Authorization: Bearer $TOKEN"
```

## 參考資源

- [OpenAPI 規範](../openapi.yaml)
- [威脅模型](threat-model.md)
- [安全檢查清單](security-checklist.md)
- [可觀測性指南](observability.md)
- [測試指南](testing-guide.md)

## 獲取幫助

如果遇到問題：

1. 檢查 [安全檢查清單](security-checklist.md)
2. 查看日誌（啟用 DEBUG 級別）
3. 運行測試：`python3 -m pytest tests/test_security_features.py -v`
4. 提交 issue 到 GitHub 倉庫
