# 配置目錄

本目錄用於集中管理專案的各種配置文件。

> **🚀 架構演進** - 本專案將演進為 Server-Edge-Runner 架構，配置將按層級組織。

## 配置文件

- 專案根目錄的 `config.py` - Flask WebUI 的主配置文件（保留在根目錄以確保向後相容）
- `src/common/config.py` - 共用配置類別（EdgeConfig、ServerConfig）
- 環境變數 - 透過 `.env` 文件或環境變數設定

## Server-Edge-Runner 配置

### 環境類型

設定 `ENV_TYPE` 環境變數來指定環境類型：

```bash
# Server 環境
export ENV_TYPE=server

# Edge 環境
export ENV_TYPE=edge
```

### Server Layer 配置

```bash
# MCP API
export MCP_API_HOST=0.0.0.0
export MCP_API_PORT=8000
export MCP_JWT_SECRET=your-secret-key
export MCP_JWT_ALGORITHM=HS256
export MCP_JWT_EXPIRATION_HOURS=24

# WebUI
export SECRET_KEY=your-flask-secret
export SQLALCHEMY_DATABASE_URI=postgresql://user:pass@host/db

# CORS
export CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

### Edge Layer 配置

```bash
# Flask Service（Electron 用）
export APP_TOKEN=your-app-token
export PORT=5000
export FLASK_HOST=127.0.0.1

# 佇列設定
export QUEUE_MAX_SIZE=1000
export MAX_WORKERS=5
export POLL_INTERVAL=0.1

# MQTT
export MQTT_ENABLED=true
export MQTT_BROKER=localhost
```

### Runner Layer 配置

```bash
# Robot-Console
export ROBOT_PROTOCOL=mqtt  # mqtt, http, ros
export ROBOT_TIMEOUT=30
export EMERGENCY_STOP_ENABLED=true
```

## 共用配置

```bash
# 日誌
export LOG_LEVEL=INFO
export LOG_FORMAT=json  # json 或 text

# 服務識別
export SERVICE_NAME=robot-service
export SERVICE_VERSION=1.0.0

# 環境
export ENVIRONMENT=development  # development, testing, production
export DEBUG=false
```

## 配置策略

1. **開發環境** - 使用 `.env` 文件或環境變數
2. **生產環境** - 使用系統環境變數或配置管理系統（如 Vault）
3. **測試環境** - 使用測試專用的配置或 mock
4. **容器化** - 使用 Docker secrets 或 Kubernetes ConfigMaps

## 使用共用配置類別

```python
# Edge 環境
from src.common.config import EdgeConfig
config = EdgeConfig.from_env()

# Server 環境
from src.common.config import ServerConfig
config = ServerConfig.from_env()

# 自動偵測
from src.common.config import get_config
config = get_config()  # 根據 ENV_TYPE 自動選擇
```

## 注意事項

- 不要將包含敏感信息的 `.env` 文件提交到版本控制
- 所有密鑰和令牌應該通過安全方式管理
- 在部署前確保所有必需的環境變數都已設定
- Edge 和 Server 可以使用不同的配置來源
