# 專案記憶

> **用途**：此文件專門用於存儲 AI 助手在開發過程中學習到的經驗教訓、最佳實踐和重要發現。
>
> **使用方式**：
> - AI 助手在每次任務完成後應更新此文件，記錄新的經驗教訓
> - 開發者可參考此文件了解過去遇到的問題和解決方案
> - 此文件不應包含架構設計、規劃或功能說明（這些請放在其他專門文件中）
>
> **⚠️ 重要提醒**：
> - **`store_memory` 工具僅能在 review 模式下使用**
> - 在 agent 模式下，請直接編輯本文件（PROJECT_MEMORY.md）來記錄經驗
> - 遵循本文件既有的格式結構：
>   - 新增至「關鍵經驗精華」章節（標註使用頻率 ⭐）
>   - 或新增至「詳細經驗索引」對應的專題文件
>   - 更新「最近更新」章節記錄變更
>
> 📖 **其他文件**：[architecture.md](architecture.md)、[plans/](plans/)、[development/](development/)、[memory/](memory/)

---

## ⚠️ 常見錯誤提醒（AI 助手必讀）

### 🔐 資訊洩露防護（API Exception Handling）

**禁止在 API 回應中使用 `str(e)` 暴露例外細節：**

```python
# ❌ 危險：洩露 Python 例外類別名稱與內部路徑/邏輯
except InvalidRoleError as e:
    return jsonify({"message": str(e)}), 400  # Flask
raise HTTPException(status_code=500, detail=str(e))  # FastAPI

# ✅ 正確（Flask）
except InvalidRoleError:
    return jsonify({"error": "Bad Request", "message": "Invalid role specified"}), 400
except Exception:
    logger.exception("Failed to ...")
    return jsonify({"error": "Internal Server Error"}), 500

# ✅ 正確（FastAPI）
except Exception:
    logger.exception("...", exc_info=True)
    raise HTTPException(status_code=500, detail="Internal server error")

# ✅ 允許（後端日誌，不送給客戶端）
logger.error("...", extra={'error': str(e)}, exc_info=True)
```

| 例外類別 | 對客戶端的訊息 | HTTP 狀態碼 |
|----------|--------------|-------------|
| `UserNotFoundError` | User not found | 404 |
| `UserAlreadyExistsError` | User already exists | 409 |
| `InvalidRoleError` | Invalid role specified | 400 |
| `ValueError`（業務邏輯） | Data not exist / Invalid input value | 404 / 400 |
| 任何未預期例外 | Internal Server Error（不含細節） | 500 |

### 🔒 路徑穿越（Path Traversal）修復模式

**`startswith` 路徑檢查存在繞過漏洞，禁止使用：**

```python
# ❌ 危險：/tmp/storage_evil 會通過此檢查
if not str(path.resolve()).startswith(str(base.resolve())):
    raise ValueError("Path traversal detected")

# ✅ 首選：werkzeug.safe_join
from werkzeug.utils import safe_join
safe_path = safe_join(str(base_dir), user_input)
if safe_path is None:
    raise ValueError("Path traversal detected")
file_path = Path(safe_path)

# ✅ 備選：Python 3.9+ is_relative_to
if not path.resolve().is_relative_to(base.resolve()):
    raise ValueError("Path traversal detected")
```

### 🔍 Linting 錯誤（最常見）

```bash
# 使用 llm-helper 工具（推薦）
python llm-helper/check_lint.py

# 或手動執行
python3 -m flake8 src/ Edge/MCP/ --select=E,F,W --max-line-length=120

# 批次移除尾隨空格（W293）
find src/ Edge/MCP/ -name "*.py" -exec sed -i 's/[[:space:]]*$//' {} \;
```

---

## 🤖 llm-helper — AI Agent 工具包

```bash
python llm-helper/check_lint.py                              # Python + JS lint（E/F 級別）
python llm-helper/run_tests.py specific --test-path tests/X  # 跑指定測試
python llm-helper/run_tests.py unit                          # 跑所有單元測試
python llm-helper/run_tests.py all --coverage                # CI 完整流程
```

> 根目錄 `check_lint.py` / `run_tests.py` 均為 **shim**，正本在 `llm-helper/`。
> 📖 詳見 [`llm-helper/README.md`](../llm-helper/README.md)

---

## 📋 相關文件索引

| 類別 | 文件 |
|------|------|
| 架構 | [architecture.md](architecture.md) |
| 規劃 | [plans/MASTER_PLAN.md](plans/MASTER_PLAN.md) |
| 開發指南 | [development/](development/) |
| 函式庫說明 | [development/LIBRARY_REFERENCE.md](development/LIBRARY_REFERENCE.md) |
| 安全文件 | [security/TOKEN_SECURITY.md](security/TOKEN_SECURITY.md) |
| 使用者指引 | [user_guide/USER_GUIDE_INDEX.md](user_guide/USER_GUIDE_INDEX.md) |
| 詳細經驗 | [memory/](memory/)（見下表） |

### 詳細經驗索引（memory/）

| 文件 | 主題 | 重點 |
|------|------|------|
| [phase3_lessons.md](memory/phase3_lessons.md) | Phase 3.1 完整經驗 | Python 時間處理、dataclass、非重入鎖、競態條件 |
| [phase3_2_lessons.md](memory/phase3_2_lessons.md) | **Phase 3.2 Qt 整合** | **不重造輪子、WIP 替換、CodeQL 修復、固件安全** |
| [security_lessons.md](memory/security_lessons.md) | 安全最佳實踐 | Token 生成、動作驗證、密碼處理、審計日誌 |
| [code_quality_lessons.md](memory/code_quality_lessons.md) | 程式碼品質 | Linting、型別提示、測試策略 |
| [cli_batch_lessons.md](memory/cli_batch_lessons.md) | CLI/批次操作 | TDD 流程、錯誤處理、重複計數防護 |
| [tui_llm_lessons.md](memory/tui_llm_lessons.md) | TUI 與 LLM | TUI 架構、LLM 整合、HTTP 會話重用 |
| [rabbitmq-sqs-lessons.md](memory/rabbitmq-sqs-lessons.md) | RabbitMQ & SQS | QueueInterface 設計、測試策略、效能比較 |
| [cloud-sync-ui-lessons.md](memory/cloud-sync-ui-lessons.md) | 雲端同步 UI | 狀態面板、雙頻率更新、漸進式實作 |
| [unified_launcher_playbook.md](memory/unified_launcher_playbook.md) | 統一啟動器 | 啟動流程、配置管理 |
| [device-binding-lessons.md](memory/device-binding-lessons.md) | 設備綁定 | 跨平台設備識別 |
| [step1~step5 lessons](memory/step1-device-id-generator-lessons.md) | Edge Token 系列 | UUID、加密、平台存儲、快取、整合測試 |

### 開發指南索引（development/）

| 文件 | 主題 |
|------|------|
| [CLOUD_SYNC_GUIDE.md](development/CLOUD_SYNC_GUIDE.md) | **雲端同步開發指南**：先後發送佇列、離線快取、API 認證 |
| [TUI_LLM_INTEGRATION_GUIDE.md](development/TUI_LLM_INTEGRATION_GUIDE.md) | TUI + LLM 整合 |
| [UNIFIED_LAUNCHER_GUIDE.md](development/UNIFIED_LAUNCHER_GUIDE.md) | 統一啟動器 |
| [PYTHON_LINT_GUIDE.md](development/PYTHON_LINT_GUIDE.md) | Python Linting 指南 |

**快速查找**：
- 開發新功能前 → `phase3_2_lessons.md §1`「不重造輪子原則」
- 安全問題修復 → `phase3_2_lessons.md §3`「CodeQL 安全修復模式」
- API 整合 → `phase3_2_lessons.md §4`「真實 API 整合架構」
- 固件更新 → `phase3_2_lessons.md §5`「固件更新安全流程」

---

## 🎯 關鍵經驗精華（Top 25）

> 按使用頻率排序，⭐⭐⭐ 最高頻。每個條目有 `### N.` 標題便於跳轉。

---

### ⭐⭐⭐ 高頻（幾乎每次開發都需要）

---

### 0. 用戶文件撰寫原則 ⭐⭐⭐

**使用頻率**：每次文件更新 | **相關**：[USER_DOCUMENTATION_GUIDE.md](development/USER_DOCUMENTATION_GUIDE.md)

- 使用者導向：按使用場景組織（不是按程式碼結構）
- 漸進式揭露：快速入門 → 功能概覽 → 完整參考
- 實例優先：可執行的範例勝過抽象描述

### 0.5. 路徑穿越防護：werkzeug.safe_join ⭐⭐⭐

**使用頻率**：每次處理使用者輸入路徑 | **修復**：2026-02-24/2026-02-26

```python
# ✅ 首選（Werkzeug 已在 requirements.txt）
from werkzeug.utils import safe_join
safe_path = safe_join(str(base_dir), user_input_a, user_input_b)
if safe_path is None:       # None = 路徑穿越被攔截
    raise ValueError("Path traversal detected")

# ❌ 禁止（startswith 繞過：/base_dir_evil 會通過）
if not str(path.resolve()).startswith(str(base.resolve())):
    ...
```

### 1. Linting 自動修正 ⭐⭐⭐

**使用頻率**：幾乎每次提交 | **相關**：[code_quality_lessons.md](memory/code_quality_lessons.md)

```bash
python llm-helper/check_lint.py
find src/ Edge/MCP/ -name "*.py" -exec sed -i 's/[[:space:]]*$//' {} \;
```

### 2. Python 時間處理（必記）⭐⭐⭐

**使用頻率**：高頻 | **相關**：[phase3_lessons.md](memory/phase3_lessons.md)

```python
# ❌ Python 3.12+ 已棄用
timestamp = datetime.utcnow()

# ✅ 應該使用
from src.common.datetime_utils import utc_now, utc_now_iso
timestamp = utc_now()
```

### 3. 測試驅動開發流程 ⭐⭐⭐

**使用頻率**：每個新功能 | **相關**：[cli_batch_lessons.md](memory/cli_batch_lessons.md)

```
撰寫測試 → 執行（失敗）→ 實作 → 執行（通過）→ 重構
```

### 4. 安全的 Token 生成 ⭐⭐⭐

**使用頻率**：所有認證相關功能 | **相關**：[security_lessons.md](memory/security_lessons.md)

```python
# ❌ 硬編碼預設 token
token = os.environ.get("APP_TOKEN", "dev-token")

# ✅ 使用安全的隨機 token
import secrets
token = os.environ.get("APP_TOKEN") or secrets.token_hex(32)
```

### 21. 零信任前端原則 ⭐⭐⭐

**使用頻率**：所有前後端互動 | **相關**：[security/threat-model.md](security/threat-model.md)

```python
# ✅ 後端強制驗證所有輸入
class UserCreateRequest(BaseModel):
    role: str

    @validator('role')
    def validate_role(cls, v):
        if v not in ['admin', 'operator', 'viewer', 'auditor']:
            raise ValueError('Invalid role')
        return v
```

### 22. Edge-Cloud 認證同步架構 ⭐⭐⭐

**使用頻率**：Edge 環境認證實作 | **相關**：[security/edge-cloud-auth-analysis.md](security/edge-cloud-auth-analysis.md)

- Access Token：15 分鐘（短期）+ Refresh Token：7 天（設備綁定）
- 加密儲存：Fernet 或 OS keychain
- Edge 端快取，登入仍在 Server 驗證

---

### ⭐⭐ 中頻（特定功能開發時）

---

### 5. 型別提示正確使用 ⭐⭐

```python
# ✅ 使用具體型別而非 Any
def process(options: BatchOptions) -> None: ...
```

### 6. 批次操作錯誤處理 ⭐⭐

```python
# ✅ 指數退避重試 + 超時控制
for attempt in range(max_retries):
    try:
        result = await execute_with_timeout(cmd, timeout_ms)
        return result
    except TimeoutError:
        if attempt < max_retries - 1:
            await asyncio.sleep(backoff_factor ** attempt)
```

### 7. dataclass 與 datetime ⭐⭐

```python
# ❌ 所有實例共享同一時間戳
@dataclass
class Status:
    updated_at: datetime = utc_now()  # 錯誤！

# ✅ 使用 field(default_factory=...)
    updated_at: datetime = field(default_factory=utc_now)
```

### 8. 動作驗證（安全性）⭐⭐

```python
# ✅ 驗證動作在有效清單中
if action_name not in VALID_ACTIONS:
    logger.warning(f"Invalid action: {action_name}")
    return error_response()
```

### 9. Async Fixtures 問題（pytest-asyncio）⭐⭐

```python
# ❌ pytest-asyncio 新版不支援 async fixture
@pytest.fixture
async def setup():
    return await create_resource()

# ✅ 直接在測試函數中建立
async def test_something():
    resource = await create_resource()
```

### 10. 非重入鎖問題 ⭐⭐

```python
# ❌ 會造成死鎖
def method_a(self):
    with self._lock:
        self.method_b()  # method_b 也需要 _lock

# ✅ 使用可重入鎖
self._lock = threading.RLock()
```

### 11. 狀態更新與事件通知一致性 ⭐⭐

```python
# ✅ 在同一處理中完成
async def update_status(self, robot_id, status):
    await self._state_store.set(key, status)
    await self._event_bus.publish(EventTopics.STATUS_UPDATED, {...})
```

### 16. 審計日誌記錄模式 ⭐⭐

**相關**：[security/audit-logging-implementation.md](security/audit-logging-implementation.md)

```python
from WebUI.app.audit import log_login_attempt, log_audit_event
log_login_attempt(username='user', success=True, user_id=user.id)
log_audit_event(action='custom_action', user_id=current_user.id,
                resource_type='robot', resource_id='123')
```

### 18. RBAC 權限檢查模式 ⭐⭐

```python
@bp.route('/admin_only')
@login_required
def admin_function():
    if current_user.role not in ['admin', 'auditor']:
        abort(403)
```

### 19. Flask 模板條件渲染 ⭐⭐

```jinja2
{% if current_user.is_authenticated and current_user.role in ['admin', 'auditor'] %}
    <a href="{{ url_for('webui.audit_logs') }}">審計日誌</a>
{% endif %}
```

### 23. Edge 環境安全約束 ⭐⭐

- 延遲敏感（<100ms）、記憶體受限（4-8GB）、物理安全弱、需離線降級策略
- **相關**：[security/edge-cloud-auth-analysis.md](security/edge-cloud-auth-analysis.md)

### 24. Token 安全實作模式 ⭐⭐

1. 短期 Access Token（15 分鐘）
2. Refresh Token rotation（單次使用）
3. 設備指紋綁定（Device ID）
4. Token 撤銷清單（Server 端）
5. 加密儲存（Fernet/OS keychain）

### 25. 離線模式權限控管 ⭐⭐

- ✅ 離線允許：查看狀態、執行基本指令、查看歷史
- ❌ 離線禁止：新增使用者、權限變更、系統配置

---

### ⭐ 低頻（特定場景）

---

### 12. 重複計數防護 ⭐

```python
# ✅ 檢查舊狀態避免重複計數
terminal_states = {SUCCESS, FAILED, TIMEOUT, CANCELLED}
if status in terminal_states and (old_status is None or old_status not in terminal_states):
    self.completed += 1
```

### 13. 競態條件防護 ⭐

```python
# ✅ 先儲存引用，避免 None 競態
process = self._process
if process is None or process.poll() is not None:
    ...
```

### 14. HTTP 會話重用 ⭐

```python
# ✅ 重用 aiohttp 會話
if self._session is None or self._session.closed:
    self._session = aiohttp.ClientSession()
```

### 15. Flask 2.3+ JSON 配置 ⭐

```python
# ✅ 新版本（Flask 2.3+）
app.json.ensure_ascii = False
# ⚠️ 已棄用
# app.config['JSON_AS_ASCII'] = False
```

### 17. Flask-SQLAlchemy 資料庫遷移 ⭐

```python
# migrations/versions/<revision_id>_<description>.py
def upgrade():
    op.create_table('table_name', ...)
def downgrade():
    op.drop_table('table_name')
```

### 20. 審計日誌查詢過濾模式 ⭐

```python
query = AuditLog.query
if severity: query = query.filter(AuditLog.severity == severity)
if search:   query = query.filter(AuditLog.message.ilike(f'%{search}%'))
pagination = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=per_page)
```

---

## 💡 開發流程提醒

1. **開始前**：閱讀 `⚠️ 常見錯誤提醒` 章節
2. **開發中**：參考相關專題文件（`memory/*.md`）
3. **提交前**：`python llm-helper/check_lint.py` + `python llm-helper/run_tests.py unit`
4. **完成後**：更新本文件或在 `memory/` 建立專題文件

---

## 🔄 最近更新

### 2026-03-04: 文件與同步策略說明

- 更新 `Edge/cloud_sync/README.md`：補充 `sync_queue.py` 模組說明、離線佇列使用範例與 FIFO 特性表格
- 新增 `docs/development/CLOUD_SYNC_GUIDE.md`：整合開發者指南（同步策略一覽、先後發送設計、測試指南、設定參考）
- 更新 `docs/PROJECT_MEMORY.md`：新增開發指南索引表格與 `CLOUD_SYNC_GUIDE.md` 參考連結
- 詳見：[docs/development/CLOUD_SYNC_GUIDE.md](development/CLOUD_SYNC_GUIDE.md)

### 2026-03-04: 討論區與用戶社群互動功能（Cloud/engagement）

- 實作 `Cloud/engagement/` 模組，提供完整的討論區與社群互動功能
- 新增資料模型（`models.py`）：`UserEngagementProfile`、`Post`、`PostComment`、`PostLike`、`PointsLog`
- 新增 `service.py`（`EngagementService`）：貼文 CRUD、評論、點讚切換、積分/等級/稱號、排行榜
- 新增 `api.py`：Flask Blueprint REST API（`/api/cloud/engagement/*`，JWT 認證保護寫入操作）
- 更新 `engagement.py`：從 `NotImplementedError` 佔位符改為委派 `EngagementService` 的實作
- 新增 engagement service 單元測試並全數通過，Lint 零錯誤，CodeQL 零告警
- 所有文字輸入使用 `bleach.clean()` 防止 XSS；不暴露例外細節於 API 回應
- 
### 2026-03-04: 共享雲端 LLM 切換與混合（雲端優先/本地備援）

- 新增三大雲端 LLM 提供商：Azure OpenAI、GCP Gemini、Amazon Bedrock（aioboto3）
- 新增通用 OpenAI 相容雲端提供商 `CloudLLMProvider`
- `LLMProviderManager` 新增 `RoutingMode` 枚舉（CLOUD_FIRST/LOCAL_FIRST/CLOUD_ONLY/LOCAL_ONLY）
- 新增 `generate_with_routing()` 一站式生成方法（含即時健康檢查備援）
- 修復 `src/common/llm_manager.py` `Edge.llm_discovery` ImportError（try/except fallback）
- 49 個單元測試（100% 通過）、CodeQL 零警告
- 詳見：[docs/mcp/MCP_LLM_PROVIDERS.md](docs/mcp/MCP_LLM_PROVIDERS.md)

### 2026-02-26: 雲端同步異常處理測試 + 啟動修復 + Codespace 模板

- 新增 59 個雲端同步異常處理測試（48 → 107 → 139 after review fixes）
- 修復 Flask-Babel 3.x breaking change（`@babel.localeselector` → `locale_selector=get_locale`）
- 修復 `setup_json_logging` 函式名稱、`requirements.txt` 依賴版本升級
- 修復 Codespace devcontainer 路徑、埠號（8080/8888）、Flask debug mode 啟動
- 修復 CWE-22 路徑穿越（`Cloud/api/storage.py` `get_storage_stats`、`Edge/qtwebview-app/routes_firmware_tiny.py` 兩個部署路由）
- 建立 `llm-helper/` AI Agent 工具包（`check_lint.py`、`run_tests.py`、`README.md`）

### 2026-02-24: 雲端同步佇列（先後發送機制）

- 新增 `Edge/cloud_sync/sync_queue.py`（SQLite-backed FIFO，`seq` 整數確保順序）
- `CloudSyncService` 整合佇列：雲端不可用時自動入隊，`flush_queue` 補發
- 19 個單元測試（100% 通過）
- 詳見：[docs/features/data-sync-strategy.md](features/data-sync-strategy.md)

### 2026-02-11: 雲端同步 UI 狀態面板

- Edge UI 首頁新增「☁️ 雲端同步狀態」面板（4 個狀態卡片）
- `GET /api/edge/sync/status` 端點
- 詳見：[memory/cloud-sync-ui-lessons.md](memory/cloud-sync-ui-lessons.md)

### 2026-01-21: Phase 3.2 Qt WebView 完整移植

- 47 個 WIP 項目，Phase 1 完成 10 個（21%）
- CodeQL 安全修復（路徑穿越 + 資訊洩露）
- Qt 原生 Widgets 減少 75% 記憶體使用
- 詳見：[memory/phase3_2_lessons.md](memory/phase3_2_lessons.md)

### 2026-01-05: RabbitMQ & AWS SQS 佇列整合

- QueueInterface 抽象介面統一三種實作（Memory/RabbitMQ/SQS）
- 1,150+ 行測試，CI/CD Pipeline
- 效能：MemoryQueue <1ms、RabbitMQ 1-10ms、SQS 10-100ms
- 詳見：[memory/rabbitmq-sqs-lessons.md](memory/rabbitmq-sqs-lessons.md)

### 2025-12-17: Edge Token 快取、離線同步、Unified Launcher

- `src/robot_service/edge_token_cache.py`：加密本地儲存、TTL、記憶體快取
- `src/robot_service/edge_token_sync.py`：加密佇列、重試/指數退避
- `src/robot_service/token_integration.py`：TokenManager 輪替事件綁定
- 詳見：[development/UNIFIED_LAUNCHER.md](development/UNIFIED_LAUNCHER.md)

### 2025-12-17: 審計日誌系統 + Edge-Cloud 認證架構分析

- 完整審計日誌系統（AuditLog 模型、21 個測試）
- Edge-Cloud 認證架構分析文件，推薦 Token 快取同步方案
- 詳見：[security/audit-logging-summary.md](security/audit-logging-summary.md)、[security/edge-cloud-auth-analysis.md](security/edge-cloud-auth-analysis.md)

### 2025-12-17: CLI 批次操作 + 代碼品質優化

- 新增 CLI 批次操作模組（36 個測試）
- 修正 flake8 E/F/W 問題 15 → 0
- 詳見：[memory/cli_batch_lessons.md](memory/cli_batch_lessons.md)

---

**原始行數**：1,293 行 → **整理後**：~500 行（重組於使用頻率，長篇內容移至 `memory/`）
**最後更新**：2026-03-04
