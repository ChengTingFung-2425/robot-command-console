# 專案記憶

> **用途**：此文件專門用於存儲 AI 助手（如 GitHub Copilot）在開發過程中學習到的經驗教訓、最佳實踐和重要發現。
> 
> **使用方式**：
> - AI 助手在每次任務完成後應更新此文件，記錄新的經驗教訓
> - 開發者可參考此文件了解過去遇到的問題和解決方案
> - 此文件不應包含架構設計、規劃或功能說明（這些請放在其他專門文件中）
> 
> 📖 **其他文件**：[architecture.md](architecture.md)、[plans/](plans/)、[development/](development/)

---

## 📋 相關文件索引

| 類別 | 文件 |
|------|------|
| **架構** | [architecture.md](architecture.md) |
| **規劃** | [plans/MASTER_PLAN.md](plans/MASTER_PLAN.md)、[plans/PHASE3_EDGE_ALL_IN_ONE.md](plans/PHASE3_EDGE_ALL_IN_ONE.md) |
| **開發指南** | [development/](development/) |
| **功能文件** | [features/](features/) |
| **安全文件** | [security/TOKEN_SECURITY.md](security/TOKEN_SECURITY.md) |
| **Phase 3 文件** | [phase3/PHASE3_1_STATUS_REPORT.md](phase3/PHASE3_1_STATUS_REPORT.md)、[phase3/TEST_PLAN_PHASE3_1.md](phase3/TEST_PLAN_PHASE3_1.md) |

---

## 💡 經驗教訓

### Python 時間處理

```python
# ❌ 不要使用（Python 3.12+ 已棄用）
timestamp = datetime.utcnow()

# ✅ 應該使用
timestamp = datetime.now(timezone.utc)
```

**原因**：`datetime.utcnow()` 在 Python 3.12+ 中已被棄用。

### ISO 時間格式

```python
# ❌ 不要這樣（會產生 +00:00Z 格式錯誤）
timestamp = datetime.now(timezone.utc).isoformat() + "Z"

# ✅ 直接使用 isoformat（已包含 +00:00）
timestamp = datetime.now(timezone.utc).isoformat()
```

### 共用模組使用

```python
# ❌ 不要在各模組重複定義
class CustomJsonFormatter(jsonlogger.JsonFormatter):
    ...

# ✅ 使用共用模組
from .utils import setup_json_logging
logger = setup_json_logging(__name__, service_name='mcp-api')
```

**原因**：消除代碼重複，統一日誌格式。

### Pydantic V2 遷移

```python
# ⚠️ 即將棄用
data = model.dict()

# ✅ Pydantic V2 建議
data = model.model_dump()
```

### HTTP 會話重用

```python
# ❌ 每次都建立新會話
async with aiohttp.ClientSession() as session:
    ...

# ✅ 重用會話
async def _get_http_session(self):
    if self._http_session is None or self._http_session.closed:
        self._http_session = aiohttp.ClientSession()
    return self._http_session
```

**原因**：每次建立新的 HTTP 會話有額外開銷。

### 競態條件防護

```python
# ❌ 直接存取可能為 None 的屬性
if self._process.poll() is not None:
    ...

# ✅ 先儲存引用再檢查
process = self._process
if process is None or process.poll() is not None:
    ...
```

**原因**：在非同步環境中，屬性可能被其他協程修改。

### 安全的 Token 生成

```python
# ❌ 使用硬編碼預設 token
token = os.environ.get("APP_TOKEN", "dev-token")

# ✅ 使用安全的隨機 token
import secrets
token = os.environ.get("APP_TOKEN") or secrets.token_hex(32)
```

**原因**：硬編碼的預設 token 是安全風險。

### 服務啟動異常恢復

> 📖 **詳細指南**：[development/STARTUP_RECOVERY_GUIDE.md](development/STARTUP_RECOVERY_GUIDE.md)

**經驗教訓**：
1. 啟動成功時不要重置 `startup_retry_count`，以便追蹤重試次數
2. 使用告警機制通知每次重試和最終失敗
3. 將實際啟動邏輯分離到 `_do_start_service()` 以便重試

### 指令處理器設計

```python
# ✅ 使用分派器模式解耦指令處理和執行
processor = CommandProcessor(action_dispatcher=my_dispatcher)
```

**原因**：分派器模式允許在不同環境中靈活配置執行邏輯。

### 動作驗證

```python
# ✅ 驗證動作在有效清單中
if action_name not in VALID_ACTIONS:
    logger.warning(f"Invalid action: {action_name}")
```

**原因**：防止無效動作導致執行錯誤。

### Token 安全比較

```python
# ❌ 直接使用 hmac.compare_digest（可能拋出異常）
if hmac.compare_digest(token, valid_token):
    return True

# ✅ 先檢查長度再進行比較
if len(token) == len(valid_token) and \
   hmac.compare_digest(token, valid_token):
    return True
```

**原因**：`hmac.compare_digest` 在比較不同長度的字串時可能拋出 `TypeError`。同時先檢查長度可以避免不必要的時序洩漏。

### 執行緒鎖與方法呼叫

```python
# ❌ 在持有鎖的情況下呼叫也需要獲取鎖的方法（會造成死鎖）
def rotate_token(self):
    with self._lock:
        # generate_token 也會嘗試獲取 self._lock
        new_token, new_info = self.generate_token()

# ✅ 提取內部邏輯避免重複獲取鎖
def rotate_token(self):
    with self._lock:
        self._archive_current_token()
        # 直接執行 token 生成邏輯
        token = secrets.token_hex(self._token_length)
        ...
```

**原因**：Python 的 `threading.Lock` 是非重入鎖，同一執行緒重複獲取會造成死鎖。使用 `threading.RLock`（可重入鎖）或提取內部邏輯可解決此問題。

### Token 輪替設計

> 📖 **詳細指南**：[security/TOKEN_SECURITY.md](security/TOKEN_SECURITY.md)

**經驗教訓**：
1. Token 輪替時應保留舊 Token 的寬限期，避免服務中斷
2. 使用雜湊存儲舊 Token 以避免明文儲存
3. 定期清理過期的舊 Token 以防止記憶體洩漏
4. 輪替事件應通知所有相關訂閱者

### Flask 配置遷移（2.3+）

```python
# ⚠️ Flask 2.3 已棄用
app.config['JSON_AS_ASCII'] = False

# ✅ Flask 2.3+ 建議
app.json.ensure_ascii = False
```

**原因**：Flask 2.3 更新了 JSON 配置方式。

### SQLAlchemy 2.0 遷移

```python
# ⚠️ SQLAlchemy 1.x 風格（將棄用）
user = User.query.get(user_id)

# ✅ SQLAlchemy 2.0 風格
user = db.session.get(User, user_id)
```

**原因**：`Query.get()` 在 SQLAlchemy 2.0 中已被標記為遺留 API。

### datetime_utils 使用統一化

```python
# ❌ 直接使用 datetime.now(timezone.utc)
timestamp = datetime.now(timezone.utc).isoformat()

# ✅ 使用共用 datetime_utils
from src.common.datetime_utils import utc_now_iso
timestamp = utc_now_iso()
```

**原因**：統一時間處理，減少代碼重複，便於未來維護。

---

## 📝 開發流程提醒

1. **新增共用工具**：放在 `src/common/`
2. **環境區分**：使用 `ENV_TYPE=edge` 或 `ENV_TYPE=server`
3. **文檔位置**：規劃放 `docs/plans/`，技術放 `docs/`，開發指南放 `docs/development/`，安全相關放 `docs/security/`
4. **測試與文檔同步**：文檔路徑變更時需同步更新測試
5. **任務完成後**：更新 `PROJECT_MEMORY.md` 記錄經驗教訓

---

**最後更新**：2025-12-03
