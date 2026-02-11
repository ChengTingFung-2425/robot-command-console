# DevContainer 設定指南

本文件說明專案的 DevContainer 配置和設定。

## 概述

DevContainer 提供了一個完整的開發環境，包含所有必要的依賴和工具。

## 檔案結構

```
.devcontainer/
├── Dockerfile           # 容器映像定義
├── devcontainer.json    # VS Code DevContainer 配置
└── docker-compose.yml   # 多容器編排
```

## 修復說明（2026-02-11）

### 問題
1. **pip 安裝失敗**：Python 3.11+ 引入 PEP 668，限制系統級套件安裝
2. **工作目錄未設定**：導致路徑問題
3. **開發工具缺失**：flake8 等工具未預先安裝

### 解決方案

#### 1. Dockerfile 改進

**使用 `--break-system-packages` 標誌**：
```dockerfile
RUN python3 -m pip install --disable-pip-version-check --no-cache-dir \
    --break-system-packages -r /tmp/pip-tmp/requirements.txt
```

**設定工作目錄**：
```dockerfile
WORKDIR /workspace
```

**預先安裝開發工具**：
```dockerfile
RUN python3 -m pip install --disable-pip-version-check --no-cache-dir \
    --break-system-packages \
    flake8>=7.0.0 \
    pytest>=7.4.0 \
    pytest-cov>=4.1.0 \
    openapi-spec-validator>=0.7.1 \
    bandit>=1.7.5 \
    pyyaml>=6.0
```

#### 2. devcontainer.json 改進

**明確設定工作目錄**：
```json
"workspaceFolder": "/workspace"
```

**修正 postCreateCommand 路徑**：
```json
"postCreateCommand": "cd /workspace/WebUI && flask --debug run --host=0.0.0.0 --port=5000 & "
```

#### 3. requirements.txt 改進

添加開發工具區塊：
```txt
# Development and Testing Tools
# Linting and code quality
flake8>=7.0.0
bandit>=1.7.5

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-asyncio>=0.21.0

# OpenAPI validation
openapi-spec-validator>=0.7.1
pyyaml>=6.0
```

## 使用方式

### 1. 在 VS Code 中開啟

1. 安裝 "Dev Containers" 擴展
2. 打開命令面板（Ctrl/Cmd+Shift+P）
3. 選擇 "Dev Containers: Reopen in Container"
4. 等待容器構建完成

### 2. 使用 Docker Compose

```bash
cd .devcontainer
docker-compose up -d
docker-compose exec app bash
```

### 3. 重建容器

```bash
# 在 VS Code 中
# 命令面板 -> "Dev Containers: Rebuild Container"

# 或使用命令列
cd .devcontainer
docker-compose down
docker-compose up --build -d
```

## 可用服務

| 服務 | 端口 | 說明 |
|------|------|------|
| Flask App | 5000 | 主應用程式 |
| Flask App (Debug) | 5001 | 調試模式 |
| PostgreSQL | 5432 | 資料庫 |
| pgAdmin | 5050 | 資料庫管理介面 |
| MailHog | 8025 | 郵件測試介面 |
| MailHog SMTP | 1025 | SMTP 伺服器 |

## 預先安裝的工具

- **Python 3.x**（來自基礎映像）
- **pip**（Python 套件管理器）
- **flake8**（Python linting）
- **pytest**（測試框架）
- **bandit**（安全掃描）
- **openapi-spec-validator**（OpenAPI 驗證）

## 疑難排解

### pip 安裝失敗

**錯誤訊息**：
```
error: externally-managed-environment
```

**解決方案**：
使用 `--break-system-packages` 或 `--user` 標誌：
```bash
python3 -m pip install --user package-name
# 或
python3 -m pip install --break-system-packages package-name
```

### 工作目錄問題

**症狀**：找不到檔案或模組

**檢查**：
```bash
pwd  # 應顯示 /workspace
```

**解決**：
確保 devcontainer.json 中設定了：
```json
"workspaceFolder": "/workspace"
```

### 容器啟動緩慢

**原因**：首次構建需要下載所有依賴

**加速**：
1. 使用預構建的映像
2. 使用 Docker 層緩存
3. 本地快取依賴

## 自訂配置

### 添加新的 Python 套件

1. 更新 `requirements.txt`
2. 重建容器或手動安裝：
```bash
python3 -m pip install --break-system-packages package-name
```

### 添加新的系統套件

修改 `Dockerfile`：
```dockerfile
RUN apt-get update && apt-get install -y \
    your-package-name \
    && rm -rf /var/lib/apt/lists/*
```

### 添加新的 VS Code 擴展

修改 `devcontainer.json`：
```json
"extensions": [
    "existing.extension",
    "new.extension"
]
```

## 最佳實踐

1. **定期更新基礎映像**：保持安全性和相容性
2. **最小化層數**：合併 RUN 命令減少映像大小
3. **使用 .dockerignore**：排除不必要的檔案
4. **版本固定**：在 requirements.txt 中固定版本號
5. **清理快取**：使用 `--no-cache-dir` 和清理 apt 快取

## 相關文件

- [Docker 官方文件](https://docs.docker.com/)
- [VS Code DevContainers](https://code.visualstudio.com/docs/devcontainers/containers)
- [Python PEP 668](https://peps.python.org/pep-0668/)

## 更新記錄

- **2026-02-11**: 修復 pip 安裝問題，添加開發工具，設定工作目錄
- 初始版本：基礎 DevContainer 配置
