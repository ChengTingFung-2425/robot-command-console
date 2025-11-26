# 跨平台 Edge 服務考量

> 此文件說明 Robot Command Console 在不同平台部署 Edge 服務的考量與最佳實踐。
> 
> **建立日期**：2025-11-26  
> **狀態**：Phase 2 文檔

---

## 目錄

1. [支援平台](#支援平台)
2. [Python 服務部署](#python-服務部署)
3. [Electron 應用打包](#electron-應用打包)
4. [服務管理](#服務管理)
5. [安全考量](#安全考量)
6. [效能優化](#效能優化)
7. [疑難排解](#疑難排解)

---

## 支援平台

### 主要支援平台

| 平台 | 架構 | 支援狀態 | 備註 |
|------|------|---------|------|
| **Ubuntu 20.04/22.04 LTS** | x86_64 | ✅ 完整支援 | 推薦用於生產環境 |
| **Debian 11/12** | x86_64 | ✅ 完整支援 | 穩定性優先 |
| **Windows 10/11** | x86_64 | ⚠️ 有限支援 | 見下方限制說明 |
| **macOS 12+** | x86_64/ARM64 | ⚠️ 有限支援 | 見下方限制說明 |

#### Windows/macOS 有限支援說明

**Windows 限制**：
- systemd 服務管理不可用，需使用 Windows Services 或 NSSM
- 部分 Python 套件可能需要手動編譯
- 路徑分隔符差異可能導致配置問題
- 建議僅用於開發和測試環境

**macOS 限制**：
- systemd 不可用，需使用 launchd
- Homebrew 安裝的 Python 路徑可能不一致
- 安全性限制可能阻止某些網路操作
- 建議僅用於開發和測試環境

**生產環境建議**：對於生產部署，強烈建議使用 Linux 平台（Ubuntu LTS 或 Debian）。

### 邊緣運算平台

| 平台 | 架構 | 支援狀態 | 備註 |
|------|------|---------|------|
| **Raspberry Pi OS 64-bit** | ARM64 | ✅ 支援 | Pi 4/5 推薦 |
| **NVIDIA JetPack 5.x** | ARM64 | ✅ 支援 | Jetson Nano/Xavier |
| **Ubuntu Server ARM64** | ARM64 | ✅ 支援 | 通用 ARM 設備 |

---

## Python 服務部署

### 相依性管理

#### 標準 Linux (x86_64)

```bash
# 建立虛擬環境
python3 -m venv .venv
source .venv/bin/activate

# 安裝相依性
pip install -r requirements.txt
```

#### ARM64 (Raspberry Pi / Jetson)

```bash
# 安裝系統相依性
sudo apt-get update
sudo apt-get install -y python3-dev python3-venv libffi-dev

# 建立虛擬環境
python3 -m venv .venv
source .venv/bin/activate

# ARM64 可能需要編譯某些套件
pip install --upgrade pip wheel
pip install -r requirements.txt
```

#### Windows

```powershell
# 建立虛擬環境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 安裝相依性
pip install -r requirements.txt
```

#### macOS

```bash
# 使用 Homebrew 安裝 Python
brew install python@3.11

# 建立虛擬環境
python3 -m venv .venv
source .venv/bin/activate

# 安裝相依性
pip install -r requirements.txt
```

### 服務啟動

#### 獨立 CLI 模式

```bash
# Linux/macOS
python3 run_service_cli.py --port 5000 --queue-size 1000 --workers 5

# Windows
python run_service_cli.py --port 5000 --queue-size 1000 --workers 5
```

#### Flask 服務模式

```bash
# 設定環境變數
export APP_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")
export PORT=5000

# 啟動服務
python3 flask_service.py
```

### 系統服務（systemd）

建立 `/etc/systemd/system/robot-console.service`：

```ini
[Unit]
Description=Robot Command Console Edge Service
After=network.target

[Service]
Type=simple
User=robot
WorkingDirectory=/opt/robot-console
Environment="APP_TOKEN=your-secure-token"
Environment="PORT=5000"
ExecStart=/opt/robot-console/.venv/bin/python flask_service.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

啟用服務：

```bash
sudo systemctl daemon-reload
sudo systemctl enable robot-console
sudo systemctl start robot-console
```

---

## Electron 應用打包

### Linux 打包

```bash
cd electron-app
npm install
npx electron-builder --linux

# 輸出格式
# - AppImage (推薦，可移植)
# - deb (Debian/Ubuntu)
# - rpm (RHEL/Fedora)
```

### Windows 打包

```powershell
cd electron-app
npm install
npx electron-builder --win

# 輸出格式
# - NSIS (安裝程式)
# - portable (可攜式)
```

### macOS 打包

```bash
cd electron-app
npm install
npx electron-builder --mac

# 輸出格式
# - DMG (磁碟映像)
# - pkg (安裝程式)
```

### 跨平台打包配置

在 `electron-app/package.json` 中設定：

```json
{
  "build": {
    "appId": "com.robotconsole.edge",
    "productName": "Robot Console Edge",
    "files": [
      "main.js",
      "preload.js",
      "renderer/**/*"
    ],
    "extraResources": [
      {
        "from": "../flask_service.py",
        "to": "py-service/flask_service.py"
      },
      {
        "from": "../src",
        "to": "py-service/src"
      }
    ],
    "linux": {
      "target": ["AppImage", "deb"],
      "category": "Utility"
    },
    "win": {
      "target": ["nsis", "portable"]
    },
    "mac": {
      "target": ["dmg", "pkg"],
      "category": "public.app-category.utilities"
    }
  }
}
```

---

## 服務管理

### 自動重啟機制

Phase 2 實作了以下自動重啟機制：

1. **進程退出重啟**：Python 服務異常退出時自動重啟（最多 3 次）
2. **健康檢查重啟**：連續 3 次健康檢查失敗時觸發重啟
3. **手動重啟**：透過 IPC 提供手動重啟 API

### 健康檢查

Electron 主進程每 30 秒執行一次健康檢查：

```javascript
// 定期健康檢查
setInterval(async () => {
  const healthy = await checkHealth();
  if (!healthy) {
    // 記錄失敗並可能觸發重啟
  }
}, 30000);
```

### 告警機制

當服務狀態異常時，系統會發送桌面通知：

- **服務重啟失敗**：嘗試重啟但失敗
- **服務故障**：達到最大重啟次數
- **健康狀態異常**：連續健康檢查失敗

---

## 安全考量

### 網路綁定

**重要**：Flask 服務僅綁定到 `127.0.0.1`，不接受外部連線：

```python
app.run(host='127.0.0.1', port=PORT, debug=False)
```

### Token 認證

所有 API 請求（除了 `/health` 和 `/metrics`）都需要 Bearer Token：

```bash
curl -H "Authorization: Bearer $APP_TOKEN" http://127.0.0.1:5000/api/ping
```

### 秘密管理

| 平台 | 推薦的秘密儲存 |
|------|---------------|
| Linux | 環境變數 / systemd credentials |
| macOS | Keychain |
| Windows | DPAPI / Windows Credential Manager |

### Context Isolation

Electron 使用 preload script 實現 Context Isolation：

```javascript
// preload.js
contextBridge.exposeInMainWorld('electronAPI', {
  getToken: () => ipcRenderer.invoke('get-token'),
  getHealthStatus: () => ipcRenderer.invoke('get-health-status')
});
```

---

## 效能優化

### 記憶體限制

| 平台 | 建議記憶體 | 最低記憶體 |
|------|-----------|-----------|
| x86_64 Linux | 4GB+ | 2GB |
| ARM64 | 4GB+ | 2GB |
| Raspberry Pi 4 | 4GB 版本 | - |

### 佇列配置

根據硬體資源調整佇列配置：

```python
# 低資源設備
ServiceManager(
    queue_max_size=500,
    max_workers=2,
    poll_interval=0.2
)

# 標準設備
ServiceManager(
    queue_max_size=1000,
    max_workers=5,
    poll_interval=0.1
)

# 高效能設備
ServiceManager(
    queue_max_size=5000,
    max_workers=10,
    poll_interval=0.05
)
```

### LLM 本地運行

若使用本地 LLM（Ollama），建議配置：

| 設備 | 模型建議 | 備註 |
|------|---------|------|
| 8GB RAM | Phi-2, TinyLlama | 小型模型 |
| 16GB RAM | Llama 2 7B, Mistral 7B | 標準模型 |
| GPU (8GB+ VRAM) | Llama 2 7B, Mistral 7B | CUDA 加速 |

---

## 疑難排解

### 常見問題

#### 1. Python 服務無法啟動

**症狀**：Electron 啟動後 Python 服務未運行

**解決方案**：

```bash
# 確認 Python 路徑
which python3

# 手動測試服務啟動
APP_TOKEN=test python3 flask_service.py

# 檢查相依性
pip list | grep Flask
```

#### 2. 健康檢查持續失敗

**症狀**：日誌顯示 `health_check_failed`

**解決方案**：

```bash
# 確認端口未被佔用
lsof -i :5000

# 手動測試健康端點
curl http://127.0.0.1:5000/health

# 檢查防火牆設定
sudo ufw status
```

#### 3. ARM64 套件安裝失敗

**症狀**：`pip install` 失敗，提示編譯錯誤

**解決方案**：

```bash
# 安裝編譯工具
sudo apt-get install -y build-essential python3-dev

# 使用 wheel 套件
pip install wheel
pip install --no-build-isolation -r requirements.txt
```

#### 4. Electron 打包失敗

**症狀**：`electron-builder` 報錯

**解決方案**：

```bash
# 清理快取
rm -rf node_modules
rm -rf dist

# 重新安裝
npm install

# 使用詳細輸出
DEBUG=electron-builder npx electron-builder --linux
```

### 日誌位置

| 平台 | 日誌位置 |
|------|---------|
| Linux | `~/.config/robot-console/logs/` |
| macOS | `~/Library/Logs/robot-console/` |
| Windows | `%APPDATA%\robot-console\logs\` |

### 診斷指令

```bash
# 查看服務狀態
curl http://127.0.0.1:5000/health | jq

# 查看 metrics
curl http://127.0.0.1:5000/metrics

# 查看佇列狀態
curl -H "Authorization: Bearer $APP_TOKEN" \
  http://127.0.0.1:5000/api/queue/stats | jq
```

---

## 參考文件

- [architecture.md](architecture.md) - 系統架構
- [observability.md](observability.md) - 可觀測性指南
- [security-checklist.md](security-checklist.md) - 安全檢查清單
- [Robot Service README](../src/robot_service/README.md) - Robot Service 說明

---

**文件維護者**：開發團隊  
**最後更新**：2025-11-26
