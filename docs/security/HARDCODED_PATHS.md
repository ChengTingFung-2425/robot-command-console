# 硬編碼路徑設計文件

## 概述

為了最大程度地防止路徑穿越攻擊，Edge API 下載端點使用完全硬編碼的檔案路徑，不接受使用者提供的任何路徑資訊。

## 設計原則

### 1. 固定基礎目錄
所有檔案儲存在預定義的系統目錄：
```
/var/robot-command-console/
├── firmware/     # 韌體檔案
├── logs/         # 系統日誌
├── reports/      # 報告檔案
└── backups/      # 備份檔案
```

### 2. 檔案 ID 映射
使用者只能透過預定義的檔案 ID 存取檔案，無法指定任意路徑：

```python
ALLOWED_DOWNLOAD_FILES = {
    'firmware_latest': Path('/var/robot-command-console/firmware/latest.bin'),
    'system_log': Path('/var/robot-command-console/logs/system.log'),
    ...
}
```

### 3. API 端點變更

**舊端點（不安全）：**
```
GET /api/download/<path:filename>
```
使用者可以提供任意檔案路徑，即使有驗證仍存在風險。

**新端點（安全）：**
```
GET /api/download/<file_id>
```
使用者只能提供預定義的檔案 ID，完全消除路徑穿越風險。

## 使用範例

### 下載檔案

```bash
# 下載最新韌體
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/download/firmware_latest

# 下載系統日誌
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/download/system_log
```

### 列出可用檔案

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:5000/api/download/list
```

回應範例：
```json
{
  "files": [
    {
      "id": "firmware_latest",
      "filename": "latest.bin",
      "exists": true,
      "category": "firmware",
      "size": 1048576
    },
    {
      "id": "system_log",
      "filename": "system.log",
      "exists": true,
      "category": "logs",
      "size": 65536
    }
  ],
  "total": 2,
  "base_directory": "/var/robot-command-console"
}
```

## 可用的檔案 ID

### 系統日誌
- `system_log` - 系統日誌
- `error_log` - 錯誤日誌
- `access_log` - 存取日誌
- `debug_log` - 除錯日誌

### 報告
- `daily_report` - 每日報告
- `weekly_report` - 每週報告
- `monthly_report` - 每月報告
- `latest_report` - 最新報告

### 韌體
- `firmware_latest` - 最新韌體
- `firmware_stable` - 穩定版韌體
- `firmware_v1` - v1.0 韌體
- `firmware_v2` - v2.0 韌體

### 備份
- `config_backup` - 配置備份
- `database_backup` - 資料庫備份

## 新增檔案

要新增可下載的檔案，必須修改原始碼中的 `ALLOWED_DOWNLOAD_FILES` 字典：

```python
# 在 Edge/qtwebview-app/routes_api_tiny.py 中
ALLOWED_DOWNLOAD_FILES = {
    # ... 現有映射 ...
    'new_file_id': SOME_DIR / 'filename.ext',
}
```

**注意：**
1. 新檔案必須位於 `/var/robot-command-console/` 下的某個子目錄
2. 需要重新啟動服務才能生效
3. 不支援動態新增檔案（這是設計決策，確保安全性）

## 安全優勢

### 完全消除路徑穿越
- ❌ 舊方式：`/api/download/../../../etc/passwd` （可能繞過驗證）
- ✅ 新方式：只能使用預定義的檔案 ID，無法指定路徑

### 明確的存取控制
- 只有在程式碼中明確定義的檔案才能被下載
- 易於審計和追蹤可存取的檔案

### 深度防禦
即使檔案 ID 映射有錯誤，仍有額外檢查確保路徑在基礎目錄內：
```python
file_path.resolve().relative_to(BASE_DATA_DIR.resolve())
```

## 目錄設定

### 建立目錄結構

```bash
sudo mkdir -p /var/robot-command-console/{firmware,logs,reports,backups}
sudo chown -R robot-user:robot-group /var/robot-command-console
sudo chmod 755 /var/robot-command-console
sudo chmod 755 /var/robot-command-console/*
```

### 權限建議

```bash
# 基礎目錄：只有擁有者可寫
chmod 755 /var/robot-command-console

# 韌體目錄：只有系統可寫
chmod 755 /var/robot-command-console/firmware

# 日誌目錄：應用程式可寫
chmod 775 /var/robot-command-console/logs

# 報告目錄：應用程式可寫
chmod 775 /var/robot-command-console/reports

# 備份目錄：只有系統可寫
chmod 755 /var/robot-command-console/backups
```

## 遷移指南

### 從舊 API 遷移

如果您的應用程式使用舊的下載端點：

**舊程式碼：**
```python
url = f"/api/download/logs/system.log"
```

**新程式碼：**
```python
url = "/api/download/system_log"
```

### 找出對應的檔案 ID

1. 呼叫 `/api/download/list` 取得所有可用檔案
2. 根據 `filename` 或 `category` 找到對應的 `id`
3. 使用該 `id` 進行下載

## 維護

### 日誌輪轉

日誌檔案應該定期輪轉，建議使用 `logrotate`：

```bash
# /etc/logrotate.d/robot-command-console
/var/robot-command-console/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 robot-user robot-group
}
```

### 磁碟空間監控

定期檢查 `/var/robot-command-console` 的磁碟使用量：

```bash
du -sh /var/robot-command-console/*
```

## 故障排除

### 檔案不存在錯誤

如果 API 回傳 404 錯誤：
1. 確認目錄結構已建立
2. 確認檔案確實存在於對應路徑
3. 確認檔案權限正確

### 權限被拒絕

如果出現權限錯誤：
```bash
# 檢查檔案擁有者和權限
ls -la /var/robot-command-console/*/

# 修正權限
sudo chown -R robot-user:robot-group /var/robot-command-console
```

---

**版本**: 1.0.0  
**最後更新**: 2026-02-13  
**相關文件**: [CODE_REVIEW_FIXES.md](../implementation/CODE_REVIEW_FIXES.md)
