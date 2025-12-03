# 專案記憶

> 此文件記錄開發過程中的經驗教訓與重要發現，作為 AI 助手的共享記憶庫。
> 
> 📖 **架構與規劃文件**：請參閱 [architecture.md](architecture.md) 和 [plans/](plans/)

---

## 📋 文件索引

| 類別 | 文件 |
|------|------|
| **架構** | [architecture.md](architecture.md) |
| **規劃** | [plans/MASTER_PLAN.md](plans/MASTER_PLAN.md)、[plans/PHASE3_EDGE_ALL_IN_ONE.md](plans/PHASE3_EDGE_ALL_IN_ONE.md) |
| **開發指南** | [development/](development/) |
| **功能文件** | [features/](features/) |

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

---

## 📝 開發流程提醒

1. **新增共用工具**：放在 `src/common/`
2. **環境區分**：使用 `ENV_TYPE=edge` 或 `ENV_TYPE=server`
3. **文檔位置**：規劃放 `docs/plans/`，技術放 `docs/`，開發指南放 `docs/development/`
4. **測試與文檔同步**：文檔路徑變更時需同步更新測試

---

**最後更新**：2025-12-03
