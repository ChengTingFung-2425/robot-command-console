# 裝置綁定 API 文件

## 概述

裝置綁定 API 允許 Edge 應用程式將裝置綁定到使用者的雲端帳號。每個使用者最多可以綁定 10 台活躍裝置。

## 認證

所有端點都需要 JWT Bearer Token 認證：

```
Authorization: Bearer <access_token>
```

## 端點

### 1. 註冊裝置

註冊並綁定新裝置到當前使用者帳號。

**端點**: `POST /api/auth/device/register`

**請求體**:
```json
{
  "device_id": "string (64 chars SHA-256 hex, required)",
  "device_name": "string (optional)",
  "device_type": "string (desktop/laptop/mobile/edge_device, optional)",
  "platform": "string (Windows/Linux/macOS, optional)",
  "hostname": "string (optional)",
  "ip_address": "string (optional)"
}
```

**回應** (201 Created):
```json
{
  "success": true,
  "device": {
    "id": 1,
    "device_id": "abc123...",
    "device_name": "My Laptop",
    "device_type": "laptop",
    "user_id": 1,
    "username": "john_doe",
    "bound_at": "2026-02-11T08:00:00Z",
    "last_seen_at": "2026-02-11T08:00:00Z",
    "is_active": true,
    "is_trusted": false,
    "platform": "Linux",
    "hostname": "mylaptop",
    "created_at": "2026-02-11T08:00:00Z"
  },
  "message": "Device registered and bound successfully"
}
```

**錯誤回應**:
- `400 Bad Request`: 無效的 device_id 格式（必須是 64 字元十六進位字串）
- `409 Conflict`: 裝置已綁定到其他使用者
- `429 Too Many Requests`: 超過裝置數量限制（10 台）

---

### 2. 列出裝置

列出當前使用者的所有綁定裝置。

**端點**: `GET /api/auth/devices`

**查詢參數**:
- `active_only` (boolean, optional): 僅顯示活躍裝置，預設 false

**回應** (200 OK):
```json
{
  "devices": [
    {
      "id": 1,
      "device_id": "abc123...",
      "device_name": "My Laptop",
      "device_type": "laptop",
      "user_id": 1,
      "username": "john_doe",
      "bound_at": "2026-02-11T08:00:00Z",
      "last_seen_at": "2026-02-11T08:30:00Z",
      "is_active": true,
      "is_trusted": false,
      "platform": "Linux",
      "hostname": "mylaptop",
      "created_at": "2026-02-11T08:00:00Z"
    }
  ],
  "total": 1
}
```

---

### 3. 查詢特定裝置

取得特定裝置的詳細資訊。

**端點**: `GET /api/auth/device/<device_id>`

**路徑參數**:
- `device_id` (integer): 裝置資料庫 ID

**回應** (200 OK):
```json
{
  "device": {
    "id": 1,
    "device_id": "abc123...",
    "device_name": "My Laptop",
    ...
  }
}
```

**錯誤回應**:
- `404 Not Found`: 裝置不存在或不屬於當前使用者

---

### 4. 更新裝置資訊

更新裝置名稱或信任狀態。

**端點**: `PUT /api/auth/device/<device_id>`

**路徑參數**:
- `device_id` (integer): 裝置資料庫 ID

**請求體**:
```json
{
  "device_name": "string (optional, 不可為空)",
  "is_trusted": boolean (optional)
}
```

**回應** (200 OK):
```json
{
  "success": true,
  "device": {
    "id": 1,
    "device_name": "Updated Name",
    "is_trusted": true,
    ...
  }
}
```

**錯誤回應**:
- `400 Bad Request`: device_name 為空或 is_trusted 格式無效
- `404 Not Found`: 裝置不存在

---

### 5. 解除裝置綁定

停用裝置（不會刪除）。

**端點**: `POST /api/auth/device/<device_id>/unbind`

**路徑參數**:
- `device_id` (integer): 裝置資料庫 ID

**回應** (200 OK):
```json
{
  "success": true,
  "message": "Device unbound successfully"
}
```

**錯誤回應**:
- `404 Not Found`: 裝置不存在

---

### 6. 刪除裝置（僅 Admin）

永久刪除裝置記錄。

**端點**: `DELETE /api/auth/device/<device_id>`

**路徑參數**:
- `device_id` (integer): 裝置資料庫 ID

**權限**: 僅限 Admin 角色

**回應** (200 OK):
```json
{
  "success": true,
  "message": "Device deleted successfully"
}
```

**錯誤回應**:
- `403 Forbidden`: 非 Admin 使用者
- `404 Not Found`: 裝置不存在

---

## 業務邏輯

### 裝置 ID 生成

裝置 ID 是基於機器特徵生成的 SHA-256 hash（64 字元十六進位字串）：
- MAC 地址
- 主機名稱
- 平台資訊
- CPU 資訊

### 裝置數量限制

每個使用者最多可以綁定 **10 台活躍裝置**。超過此限制時，註冊新裝置將返回 429 錯誤。

### 重複註冊處理

- 如果裝置已綁定到**同一使用者**且為活躍狀態，更新 `last_seen_at` 並返回 200
- 如果裝置已綁定到**同一使用者**但已解綁（`is_active=False`），自動重新啟用並更新 metadata
- 如果裝置已綁定到**其他使用者**，返回 409 錯誤

### 信任裝置

標記為信任的裝置可以跳過二次驗證（2FA）。預設新裝置為不信任。

### 審計日誌

所有裝置相關操作都會記錄到審計日誌（category='device'），包括：
- `device_register_success`: 成功註冊
- `device_register_existing`: 重複註冊
- `device_register_conflict`: 綁定衝突
- `device_register_limit_exceeded`: 超過數量限制
- `device_trust_changed`: 信任狀態變更
- `device_unbind`: 解除綁定
- `device_delete`: 刪除裝置

---

**版本**: 1.0  
**最後更新**: 2026-02-11  
**相關文件**:
- `docs/security/edge-cloud-auth-analysis.md`
- `docs/plans/phase-2-1-edge-token-cache.md`
- `Edge/WebUI/app/auth_api.py`
- `src/edge_app/auth/device_binding.py`
