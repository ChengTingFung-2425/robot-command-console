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
  "device_id": "string (64 chars SHA-256, required)",
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
- `400 Bad Request`: 無效的 device_id 格式
- `409 Conflict`: 裝置已綁定到其他使用者
- `429 Too Many Requests`: 超過裝置數量限制（10 台）

---

**版本**: 1.0  
**最後更新**: 2026-02-11  
**相關文件**:
- `docs/security/edge-cloud-auth-analysis.md`
- `docs/plans/phase-2-1-edge-token-cache.md`
- `Edge/WebUI/app/auth_api.py`
- `src/edge_app/auth/device_binding.py`
