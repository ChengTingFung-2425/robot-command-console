# 配置目錄

本目錄用於集中管理專案的各種配置文件。

## 配置文件

- 專案根目錄的 `config.py` - Flask WebUI 的主配置文件（保留在根目錄以確保向後相容）
- 環境變數 - 透過 `.env` 文件或環境變數設定（如 `APP_TOKEN`, `PORT`, `MQTT_ENABLED` 等）

## 環境變數配置

專案使用環境變數進行配置。以下是常用的環境變數：

### Flask Service
- `APP_TOKEN` - 應用程序安全令牌
- `PORT` - Flask 服務端口（默認：5000）

### WebUI
- `SECRET_KEY` - Flask 密鑰
- `SQLALCHEMY_DATABASE_URI` - 資料庫連接字串
- `MAIL_SERVER` - 郵件伺服器地址
- `MAIL_PORT` - 郵件伺服器端口
- `MQTT_ENABLED` - 是否啟用 MQTT（true/false）
- `MQTT_BROKER` - MQTT broker 地址

### MCP Service
- `MCP_API_HOST` - MCP API 主機地址（默認：0.0.0.0）
- `MCP_API_PORT` - MCP API 端口（默認：8000）
- `MCP_JWT_SECRET` - JWT 密鑰

## 配置策略

1. **開發環境** - 使用 `.env` 文件或環境變數
2. **生產環境** - 使用系統環境變數或配置管理系統
3. **測試環境** - 使用測試專用的配置或 mock

## 注意事項

- 不要將包含敏感信息的 `.env` 文件提交到版本控制
- 所有密鑰和令牌應該通過安全方式管理
- 在部署前確保所有必需的環境變數都已設定
