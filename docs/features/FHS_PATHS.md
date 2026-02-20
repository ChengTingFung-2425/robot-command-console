# FHS 標準路徑管理

## 概述

本專案採用 FHS (Filesystem Hierarchy Standard) 標準來管理同步日誌和快取資料的儲存路徑，確保跨平台相容性和安全性。

## 支援的作業系統

### Linux (FHS 標準)

遵循 FHS 2.3 標準：

| 類型 | 路徑 | 說明 |
|------|------|------|
| 快取資料 | `/var/cache/robot-command-console/` | 可重新生成的暫存資料 |
| 持久資料 | `/var/lib/robot-command-console/` | 應用程式持久性資料 |
| 日誌檔案 | `/var/log/robot-command-console/` | 系統日誌（需權限時降級到 cache） |

### Windows (AppData)

遵循 Windows 應用程式資料標準：

| 類型 | 路徑 | 說明 |
|------|------|------|
| 快取資料 | `%LOCALAPPDATA%\robot-command-console\cache\` | 本地快取資料 |
| 持久資料 | `%APPDATA%\robot-command-console\` | 漫遊應用程式資料 |
| 日誌檔案 | `%LOCALAPPDATA%\robot-command-console\logs\` | 應用程式日誌 |

範例路徑：
```
C:\Users\YourName\AppData\Local\robot-command-console\cache\
C:\Users\YourName\AppData\Roaming\robot-command-console\
C:\Users\YourName\AppData\Local\robot-command-console\logs\
```

### macOS (Library)

遵循 macOS 應用程式規範：

| 類型 | 路徑 | 說明 |
|------|------|------|
| 快取資料 | `~/Library/Caches/robot-command-console/` | 應用程式快取 |
| 持久資料 | `~/Library/Application Support/robot-command-console/` | 應用程式資料 |
| 日誌檔案 | `~/Library/Logs/robot-command-console/` | 應用程式日誌 |

## 路徑結構

### 同步日誌 (Sync Logs)

```
[日誌根目錄]/sync/
├── sync.log           # 主同步日誌 (JSON Lines 格式)
└── [其他日誌檔案]
```

**日誌格式**（JSON Lines）:
```json
{"timestamp": "2026-02-20T16:00:00Z", "edge_id": "edge-001", "command_id": 123, "action": "upload", "status": "success", "error_message": null}
{"timestamp": "2026-02-20T16:01:00Z", "edge_id": "edge-001", "command_id": 124, "action": "download", "status": "failed", "error_message": "Connection timeout"}
```

### 快取資料 (Cache)

```
[快取根目錄]/sync/
├── sync_result_edge-001_20260220_160000.json
├── sync_result_edge-001_20260220_160100.json
└── ... (保留最近 10 個檔案)
```

**快取格式**（JSON）:
```json
{
  "timestamp": "2026-02-20T16:00:00Z",
  "edge_id": "edge-001",
  "results": {
    "total": 5,
    "uploaded": 4,
    "updated": 0,
    "failed": 1,
    "errors": [...]
  }
}
```

## 使用方式

### 基本用法

```python
from src.common.fhs_paths import FHSPaths, get_sync_log_path, get_sync_cache_dir

# 取得同步日誌路徑
log_path = get_sync_log_path()
print(f"Sync log: {log_path}")

# 取得同步快取目錄
cache_dir = get_sync_cache_dir()
print(f"Sync cache: {cache_dir}")

# 取得其他類型的路徑
cache_dir = FHSPaths.get_cache_dir("custom_subdir")
data_dir = FHSPaths.get_data_dir("persistent_data")
log_dir = FHSPaths.get_log_dir("app_logs")
```

### 確保目錄存在

```python
from src.common.fhs_paths import FHSPaths

# 自動建立目錄（如果不存在）
cache_dir = FHSPaths.get_cache_dir("my_cache")
FHSPaths.ensure_dir(cache_dir)

# 或使用便捷函數（自動建立）
log_path = get_sync_log_path()  # 自動建立 sync 目錄
```

### 在 Cloud Sync Service 中使用

同步日誌會自動寫入 FHS 標準路徑：

```python
from Cloud.shared_commands.service import SharedCommandService

service = SharedCommandService(db_session)
service._log_sync(
    edge_id="edge-001",
    command_id=123,
    action="upload",
    status="success"
)
# 日誌同時記錄到：
# 1. 資料庫 (SyncLog 表)
# 2. 本地檔案 (FHS 標準路徑)
```

### 在 Edge Sync Service 中使用

同步結果會自動快取到 FHS 標準路徑：

```python
from Edge.cloud_sync.sync_service import CloudSyncService

service = CloudSyncService(
    cloud_api_url="https://cloud.example.com/api",
    edge_id="edge-001"
)

results = service.sync_approved_commands(db_session)
# 結果自動快取到 FHS cache 目錄
# 舊檔案自動清理（保留最近 10 個）
```

## 權限處理

### Linux 權限

如果應用程式無法寫入 `/var/log/`，會自動降級到快取目錄：

```python
# 嘗試 /var/log/robot-command-console/
# 失敗時降級到 /var/cache/robot-command-console/logs/
```

建議的權限設定：

```bash
# 建立目錄
sudo mkdir -p /var/cache/robot-command-console
sudo mkdir -p /var/lib/robot-command-console
sudo mkdir -p /var/log/robot-command-console

# 設定擁有者
sudo chown -R robot-user:robot-group /var/cache/robot-command-console
sudo chown -R robot-user:robot-group /var/lib/robot-command-console
sudo chown -R robot-user:robot-group /var/log/robot-command-console

# 設定權限
sudo chmod 755 /var/cache/robot-command-console
sudo chmod 755 /var/lib/robot-command-console
sudo chmod 755 /var/log/robot-command-console
```

### Windows 權限

Windows 使用者的 AppData 目錄通常具有完整權限，無需特殊設定。

### 錯誤處理

所有路徑操作都包含異常處理：

```python
try:
    log_path = get_sync_log_path()
    with open(log_path, 'a') as f:
        f.write(log_entry)
except PermissionError:
    logger.error("Permission denied")
except OSError as e:
    logger.error(f"Failed to write log: {e}")
```

## 快取管理

### 自動清理

Edge Sync Service 會自動清理舊的快取檔案：

- 保留最近 10 個同步結果檔案
- 按修改時間排序
- 刪除超過限制的舊檔案

### 手動清理

```bash
# Linux
rm -rf /var/cache/robot-command-console/sync/*

# Windows
del /Q %LOCALAPPDATA%\robot-command-console\cache\sync\*

# macOS
rm -rf ~/Library/Caches/robot-command-console/sync/*
```

## 遷移指南

### 從舊路徑遷移

如果您的應用程式使用自定義路徑，請遷移到 FHS 標準：

**舊程式碼**：
```python
log_file = "/tmp/sync.log"  # 不符合 FHS
cache_dir = "./cache"       # 相對路徑不安全
```

**新程式碼**：
```python
from src.common.fhs_paths import get_sync_log_path, get_sync_cache_dir

log_file = get_sync_log_path()
cache_dir = get_sync_cache_dir()
```

## 故障排除

### 日誌檔案找不到

**問題**：無法找到同步日誌檔案

**解決方案**：
1. 確認作業系統類型
2. 檢查對應的 FHS 路徑
3. 驗證目錄權限

```bash
# Linux
ls -la /var/log/robot-command-console/sync/
# 或
ls -la /var/cache/robot-command-console/logs/sync/

# Windows (PowerShell)
Get-ChildItem "$env:LOCALAPPDATA\robot-command-console\logs\sync\"

# macOS
ls -la ~/Library/Logs/robot-command-console/sync/
```

### 權限被拒絕

**問題**：無法建立或寫入目錄

**Linux 解決方案**：
```bash
# 檢查當前使用者
whoami

# 檢查目錄權限
ls -la /var/log/ | grep robot-command-console

# 修正權限
sudo chown -R $USER:$USER /var/log/robot-command-console
```

**Windows 解決方案**：
- 確保以正確的使用者帳戶執行
- 檢查 AppData 目錄存取權限

### 磁碟空間不足

**問題**：快取或日誌佔用過多磁碟空間

**解決方案**：

1. 檢查磁碟使用量：
```bash
# Linux
du -sh /var/cache/robot-command-console/
du -sh /var/log/robot-command-console/

# Windows (PowerShell)
Get-ChildItem "$env:LOCALAPPDATA\robot-command-console" -Recurse | 
  Measure-Object -Property Length -Sum
```

2. 手動清理舊檔案：
```bash
# 刪除 7 天前的日誌
find /var/log/robot-command-console/ -name "*.log" -mtime +7 -delete

# 刪除 3 天前的快取
find /var/cache/robot-command-console/ -name "*.json" -mtime +3 -delete
```

3. 設定 logrotate（Linux）：
```
# /etc/logrotate.d/robot-command-console
/var/log/robot-command-console/sync/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 robot-user robot-group
}
```

## API 參考

### FHSPaths 類別

#### 方法

- `get_cache_dir(subdir: Optional[str] = None) -> Path`
  - 取得快取資料目錄

- `get_data_dir(subdir: Optional[str] = None) -> Path`
  - 取得持久性資料目錄

- `get_log_dir(subdir: Optional[str] = None) -> Path`
  - 取得日誌目錄

- `ensure_dir(path: Path) -> Path`
  - 確保目錄存在

- `get_sync_log_path() -> Path`
  - 取得同步日誌檔案路徑

- `get_sync_cache_dir() -> Path`
  - 取得同步快取目錄

### 便捷函數

- `get_sync_log_path() -> Path`
  - 直接取得同步日誌路徑

- `get_sync_cache_dir() -> Path`
  - 直接取得同步快取目錄

## 相關文件

- [硬編碼路徑設計](../security/HARDCODED_PATHS.md)
- [進階指令共享功能](./advanced-command-sharing.md)
- [專案架構](../architecture.md)

---

**版本**: v1.0.0  
**最後更新**: 2026-02-20  
**維護者**: Robot Command Console Team
