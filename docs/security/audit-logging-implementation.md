# 審計日誌系統實作文件

## 概述

本文件說明 Robot Command Console 系統的審計日誌功能實作，包含資料模型、記錄機制與查詢介面。

## 功能特性

### 1. 審計日誌資料模型

**檔案位置**：`WebUI/app/models.py`

`AuditLog` 模型遵循 `docs/contract/event_log.schema.json` 規範，包含以下欄位：

- **核心EventLog 欄位**：
  - `trace_id`: 請求追蹤 UUID
  - `timestamp`: 事件時間戳
  - `severity`: 嚴重性（INFO/WARN/ERROR）
  - `category`: 類別（auth/command/audit/robot/protocol）
  - `message`: 事件訊息
  - `context`: JSON 格式的上下文資料

- **增強審計欄位**：
  - `user_id`: 執行操作的使用者 ID
  - `action`: 操作類型（login_success, permission_denied 等）
  - `resource_type`: 受影響的資源類型
  - `resource_id`: 受影響的資源 ID
  - `ip_address`: 客戶端 IP 位址
  - `user_agent`: 客戶端 User Agent
  - `status`: 操作狀態（success/failure/denied）

**資料庫索引**：
- `idx_audit_timestamp_severity`: 時間戳 + 嚴重性
- `idx_audit_user_action`: 使用者 ID + 操作
- `idx_audit_category_timestamp`: 類別 + 時間戳
- 各主要欄位的單獨索引

### 2. 審計日誌記錄機制

**檔案位置**：`WebUI/app/audit.py`

#### 核心功能

**log_audit_event()**：通用審計日誌記錄函數
- 自動生成 trace_id（如未提供）
- 自動擷取當前使用者（如已登入）
- 自動記錄 IP 位址與 User Agent
- 支援自訂嚴重性、類別、狀態

**專用記錄函數**：
- `log_login_attempt()`: 登入嘗試（成功/失敗）
- `log_logout()`: 登出事件
- `log_registration()`: 使用者註冊
- `log_password_reset_request()`: 密碼重設請求
- `log_password_reset_complete()`: 密碼重設完成
- `log_permission_denied()`: 權限拒絕
- `log_command_execution()`: 指令執行
- `log_advanced_command_action()`: 進階指令操作
- `log_robot_action()`: 機器人管理操作

#### 操作類型定義

**認證相關**（AuditAction）：
- `LOGIN_SUCCESS / LOGIN_FAILURE`: 登入成功/失敗
- `LOGOUT`: 登出
- `REGISTER`: 註冊
- `PASSWORD_RESET_REQUEST / PASSWORD_RESET_COMPLETE`: 密碼重設
- `TOKEN_ROTATION`: Token 輪替

**授權相關**：
- `PERMISSION_DENIED`: 權限拒絕
- `ROLE_CHANGE`: 角色變更

**指令相關**：
- `COMMAND_CREATE / COMMAND_EXECUTE / COMMAND_CANCEL`: 指令操作
- `ADVANCED_COMMAND_*`: 進階指令操作

**機器人相關**：
- `ROBOT_REGISTER / ROBOT_UPDATE / ROBOT_DELETE`: 機器人管理
- `ROBOT_FIRMWARE_UPDATE`: 固件更新

**系統相關**：
- `CONFIG_CHANGE`: 配置變更
- `EMERGENCY_STOP`: 緊急停止

### 3. 審計日誌查詢介面

#### 路由端點

**審計日誌列表**：`GET /audit_logs`
- **權限**：僅 admin/auditor 角色
- **功能**：
  - 多維度過濾（嚴重性、類別、操作、使用者、時間範圍）
  - 關鍵字搜尋（訊息、trace_id）
  - 分頁顯示（每頁 50 筆）
  - 排序（最新在前）

**審計日誌詳情**：`GET /audit_logs/<id>`
- **權限**：僅 admin/auditor 角色
- **功能**：
  - 顯示完整審計資訊
  - 包含上下文資料（JSON 格式）
  - 顯示使用者資訊、IP 位址、User Agent

**CSV 匯出**：`GET /audit_logs/export`
- **權限**：僅 admin/auditor 角色
- **功能**：
  - 支援相同的過濾條件
  - 匯出最多 10000 筆記錄
  - 包含主要欄位（ID、時間戳、嚴重性、類別、操作、使用者等）

#### 模板檔案

- `WebUI/app/templates/audit_logs.html.j2`: 審計日誌列表頁面
- `WebUI/app/templates/audit_log_detail.html.j2`: 審計日誌詳情頁面

#### 導航整合

在 `base.html.j2` 導航選單中新增「審計日誌」連結，僅對 admin/auditor 角色顯示。

### 4. 整合點

審計日誌已整合至以下關鍵操作點（`WebUI/app/routes.py`）：

- **登入**：`/login` - 記錄成功/失敗的登入嘗試
- **登出**：`/logout` - 記錄登出事件
- **註冊**：`/register` - 記錄新使用者註冊
- **密碼重設請求**：`/reset_password_request` - 記錄重設請求
- **密碼重設完成**：`/reset_password/<token>` - 記錄重設完成

**未來整合點**（待實作）：
- 指令執行
- 進階指令審核
- 機器人註冊/更新/刪除
- 固件更新操作
- 權限變更
- 系統配置變更

## 使用範例

### 記錄審計事件

```python
from WebUI.app.audit import log_audit_event, AuditAction, AuditSeverity, AuditCategory

# 記錄自訂審計事件
log_audit_event(
    action='custom_action',
    message='執行了某個操作',
    severity=AuditSeverity.INFO,
    category=AuditCategory.AUDIT,
    user_id=current_user.id,
    resource_type='robot',
    resource_id='123',
    context={'detail': 'additional info'}
)

# 使用專用函數記錄登入
from WebUI.app.audit import log_login_attempt
log_login_attempt(username='testuser', success=True, user_id=user.id)
```

### 查詢審計日誌

```python
from WebUI.app.models import AuditLog
from datetime import datetime, timedelta

# 查詢最近 24 小時的失敗登入
yesterday = datetime.utcnow() - timedelta(days=1)
failed_logins = AuditLog.query.filter(
    AuditLog.action == 'login_failure',
    AuditLog.timestamp >= yesterday
).all()

# 查詢特定使用者的所有操作
user_logs = AuditLog.query.filter_by(user_id=user_id).order_by(AuditLog.timestamp.desc()).all()

# 查詢特定 trace_id 的所有事件
trace_logs = AuditLog.query.filter_by(trace_id='some-uuid').all()
```

## 資料庫遷移

**遷移檔案**：`WebUI/migrations/versions/a1u2d3i4t5l6_add_audit_log_table.py`

執行遷移：
```bash
cd WebUI
flask db upgrade
```

回滾遷移：
```bash
cd WebUI
flask db downgrade
```

## 測試

**測試檔案**：`tests/test_audit_logging.py`

執行測試：
```bash
python3 -m pytest tests/test_audit_logging.py -v
```

測試涵蓋：
- 審計日誌建立
- 各類事件記錄
- 權限控管
- 查詢與過濾
- CSV 匯出
- 整合測試（登入/登出/註冊流程）

## 安全考量

1. **不可修改性**：審計日誌一旦建立即不可修改或刪除
2. **權限控管**：僅 admin 和 auditor 角色可查看審計日誌
3. **資料完整性**：所有敏感操作必須記錄審計日誌
4. **隱私保護**：密碼等敏感資訊不會記錄到日誌中
5. **IP 追蹤**：記錄客戶端 IP 位址以利追查異常活動

## 效能優化

1. **索引優化**：在常用查詢欄位上建立索引
2. **分頁載入**：審計日誌列表使用分頁避免一次載入過多資料
3. **匯出限制**：CSV 匯出限制最多 10000 筆以避免記憶體問題
4. **TTL 政策**（建議）：定期歸檔或刪除舊的審計日誌（如保留 90 天）

## 未來增強

1. **即時告警**：當檢測到異常活動時發送通知
2. **登入失敗鎖定**：連續失敗 N 次後鎖定帳號
3. **日誌完整性驗證**：使用雜湊鏈確保日誌未被篡改
4. **集中式日誌管理**：整合 ELK Stack 或類似系統
5. **進階分析**：異常行為檢測、安全趨勢分析
6. **合規報表**：自動生成 ISO 27001/SOC 2 等合規報表

## 參考文件

- [security-checklist.md](../security/security-checklist.md) - 安全檢查清單
- [threat-model.md](../security/threat-model.md) - 威脅模型
- [event_log.schema.json](../contract/event_log.schema.json) - EventLog 資料契約
- [proposal.md](../proposal.md) - 專案規格

## 變更歷史

| 日期 | 版本 | 變更說明 |
|------|------|----------|
| 2025-12-17 | 1.0 | 初始實作：資料模型、記錄機制、查詢介面 |

---

**維護者**：Robot Command Console Team
**最後更新**：2025-12-17
