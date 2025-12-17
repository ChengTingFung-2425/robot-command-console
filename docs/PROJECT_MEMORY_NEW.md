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

## ⚠️ 常見錯誤提醒（AI 助手必讀）

### 🔍 Linting 錯誤（最常見）

**在每次代碼變更後，務必執行 linting 檢查**：

```bash
# 檢查 src/ 和 MCP/ 目錄（E/F/W 級別）
python3 -m flake8 src/ MCP/ --select=E,F,W --exclude=.venv,node_modules,__pycache__ --max-line-length=120
```

**常見 Linting 問題**：

1. **W293: 空白行含空格**
   - 最常見的錯誤，幾乎每次都會出現
   - 批次修正：`find src/ MCP/ -name "*.py" -exec sed -i 's/[[:space:]]*$//' {} \;`

2. **F401: 未使用的導入**
   - 導入了模組但未在代碼中使用
   - 特別注意：僅在註解或字串中提到的類型名稱不算使用

3. **E226: 運算符周圍缺少空格**
   - `i+1` 應寫為 `i + 1`
   - `"="*60` 應寫為 `"=" * 60`

4. **型別提示錯誤**
   - 使用小寫 `any` 而非 `typing.Any`
   - 使用 `Any` 而非具體類型（降低型別安全性）

**最佳實踐**：
- ✅ **提交前檢查**：每次代碼變更後立即運行 flake8
- ✅ **分級修正**：優先修正 E/F 級別，再處理 W 級別
- ✅ **自動化工具**：使用 sed 批次處理格式問題
- ✅ **持續驗證**：修正後運行測試確保無破壞

### 📝 其他常見錯誤

1. **測試驗證不足**
   - 修改代碼後務必運行相關測試
   - 確保 100% 測試通過率

2. **型別安全性降低**
   - 避免使用 `Any` 作為型別提示
   - 優先使用具體的型別（如 `BatchOptions`）

3. **重複計數邏輯**
   - 狀態更新時檢查舊狀態
   - 避免終止狀態間轉換時重複計數

---

## 📋 相關文件索引

| 類別 | 文件 |
|------|------|
| **架構** | [architecture.md](architecture.md) |
| **規劃** | [plans/MASTER_PLAN.md](plans/MASTER_PLAN.md) |
| **開發指南** | [development/](development/) |
| **安全文件** | [security/TOKEN_SECURITY.md](security/TOKEN_SECURITY.md) |
| **使用者指引** | [user_guide/](user_guide/) |
| **詳細經驗** | [memory/](memory/)（Phase 3, CLI, TUI, 安全性等） |

---

## 🎯 關鍵經驗精華（Top 15）

### 1. Python 時間處理（必記）⭐⭐⭐

```python
# ❌ 不要使用（Python 3.12+ 已棄用）
timestamp = datetime.utcnow()

# ✅ 應該使用
from src.common.datetime_utils import utc_now, utc_now_iso
timestamp = utc_now()
iso_string = utc_now_iso()
```

### 2. Linting 自動修正（每次都要用）⭐⭐⭐

```bash
# 移除所有尾隨空格（W293）
find src/ MCP/ -name "*.py" -exec sed -i 's/[[:space:]]*$//' {} \;

# 檢查代碼品質
python3 -m flake8 src/ MCP/ --select=E,F,W --max-line-length=120
```

### 3. 安全的 Token 生成⭐⭐⭐

```python
# ❌ 硬編碼預設 token
token = os.environ.get("APP_TOKEN", "dev-token")

# ✅ 使用安全的隨機 token
import secrets
token = os.environ.get("APP_TOKEN") or secrets.token_hex(32)
```

### 4. 型別提示正確使用⭐⭐

```python
# ❌ 降低型別安全性
def process(options: Any) -> None:
    pass

# ✅ 使用具體型別
def process(options: BatchOptions) -> None:
    pass
```

### 5. dataclass 與 datetime⭐⭐

```python
# ❌ 所有實例共享同一時間戳
@dataclass
class Status:
    updated_at: datetime = utc_now()  # 錯誤！

# ✅ 使用 field(default_factory=...)
@dataclass
class Status:
    updated_at: datetime = field(default_factory=utc_now)
```

### 6. 非重入鎖問題⭐⭐

```python
# ❌ 會造成死鎖
def method_a(self):
    with self._lock:
        self.method_b()  # method_b 也需要 _lock

# ✅ 使用可重入鎖或提取邏輯
self._lock = threading.RLock()  # 可重入鎖
```

### 7. HTTP 會話重用⭐

```python
# ❌ 每次建立新會話
async with aiohttp.ClientSession() as session:
    ...

# ✅ 重用會話
if self._session is None or self._session.closed:
    self._session = aiohttp.ClientSession()
```

### 8. 競態條件防護⭐

```python
# ❌ 直接存取可能為 None 的屬性
if self._process.poll() is not None:
    ...

# ✅ 先儲存引用
process = self._process
if process is None or process.poll() is not None:
    ...
```

### 9. 狀態更新與事件通知一致性⭐⭐

```python
# ✅ 在同一處理中完成
async def update_status(self, robot_id, status):
    await self._state_store.set(key, status)
    await self._event_bus.publish(EventTopics.STATUS_UPDATED, {...})
```

### 10. Async Fixtures 問題（pytest-asyncio）⭐⭐

```python
# ❌ pytest-asyncio 新版不支援
@pytest.fixture
async def setup():
    return await create_resource()

# ✅ 直接在測試函數中建立
async def test_something():
    resource = await create_resource()
    # 或使用乾跑模式簡化
```

### 11. Flask 2.3+ JSON 配置⭐

```python
# ⚠️ 舊版本（已棄用）
app.config['JSON_AS_ASCII'] = False

# ✅ 新版本
app.json.ensure_ascii = False
```

### 12. 動作驗證（安全性）⭐⭐

```python
# ✅ 驗證動作在有效清單中
if action_name not in VALID_ACTIONS:
    logger.warning(f"Invalid action: {action_name}")
    return error_response()
```

### 13. 批次操作錯誤處理⭐⭐

```python
# ✅ 指數退避重試 + 超時控制
for attempt in range(max_retries):
    try:
        result = await execute_with_timeout(cmd, timeout_ms)
        return result
    except TimeoutError:
        if attempt < max_retries - 1:
            await asyncio.sleep(backoff_factor ** attempt)
        else:
            return timeout_result
```

### 14. 重複計數防護⭐

```python
# ✅ 檢查舊狀態避免重複計數
terminal_states = {SUCCESS, FAILED, TIMEOUT, CANCELLED}
if status in terminal_states and (old_status is None or old_status not in terminal_states):
    self.completed += 1
```

### 15. 測試驅動開發流程⭐⭐⭐

```
撰寫測試 → 執行（失敗）→ 實作 → 執行（通過）→ 重構
```

---

## 📚 詳細經驗索引

> 以下主題的詳細經驗教訓已移至專題文件，保持主檔案精簡易讀。

### Phase 3 系列經驗

- **[memory/phase3_lessons.md](memory/phase3_lessons.md)**
  - Phase 3.1: 服務協調器、共享狀態管理器（152 條經驗）
  - Phase 3.2: Tiny 版本、Edge UI 移植、固件更新（87 條經驗）
  - Phase 3.3: 統一整合與雲端分離（45 條經驗）
  - Code Review 與 CodeQL 安全修復（63 條經驗）

### CLI 批次操作經驗

- **[memory/cli_batch_lessons.md](memory/cli_batch_lessons.md)**
  - 批次操作架構設計
  - 多工調度策略（parallel, sequential, grouped）
  - 測試驅動開發（TDD）實踐
  - 代碼品質自動化

### TUI + LLM 整合經驗

- **[memory/tui_llm_lessons.md](memory/tui_llm_lessons.md)**
  - Textual TUI 框架使用
  - LLM 提供商整合（Ollama, LM Studio）
  - 自然語言指令處理
  - 提示工程與安全性

### 安全性經驗

- **[memory/security_lessons.md](memory/security_lessons.md)**
  - Token 安全管理與輪替
  - CodeQL 安全掃描修復
  - XSS 防護與輸入驗證
  - 認證授權最佳實踐

### 代碼品質經驗

- **[memory/code_quality_lessons.md](memory/code_quality_lessons.md)**
  - Linting 自動化（flake8）
  - 型別提示最佳實踐
  - 測試覆蓋策略
  - 持續整合優化

---

## 🔄 最近更新

### 2025-12-17: CLI 批次操作 + 代碼品質優化
- 新增 CLI 批次操作模組（36 個測試，100% 通過）
- 修正倉庫代碼品質問題（E/F/W 級別，15→0）
- 新增常見錯誤提醒章節
- 詳見：[memory/cli_batch_lessons.md](memory/cli_batch_lessons.md)

### 2025-12-11: TUI + LLM 整合
- 實作 Textual TUI 框架
- 整合 LLM 自然語言控制
- 詳見：[memory/tui_llm_lessons.md](memory/tui_llm_lessons.md)

### 2025-12-10: Phase 3 完成
- Phase 3.3 統一整合完成
- Tiny 版本發布
- Edge UI 移植完成
- 詳見：[memory/phase3_lessons.md](memory/phase3_lessons.md)

---

## 💡 開發流程提醒

1. **開始前**：閱讀 `⚠️ 常見錯誤提醒` 章節
2. **開發中**：參考相關專題文件（memory/*.md）
3. **提交前**：執行 linting 和測試
4. **完成後**：更新專案記憶（主檔案或專題文件）

---

**檔案精簡**：2,633 行 → 450 行（保留核心，詳細內容移至專題文件）
**最後更新**：2025-12-17
