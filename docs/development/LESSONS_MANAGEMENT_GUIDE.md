# 經驗教訓管理指南（Lessons Learned Management Guide）

> **用途**：說明如何使用標籤（Tag）系統、優先級（Priority）分類、搜尋工具與定期清理機制，有效管理 `docs/memory/` 中的經驗教訓。
>
> **相關文件**：[PROJECT_MEMORY.md](../PROJECT_MEMORY.md)、[memory/INDEX.md](../memory/INDEX.md)、[memory/TEMPLATE.md](../memory/TEMPLATE.md)

---

## 1. 標籤（Tag）系統

### 標準標籤庫

新增條目時，請從以下標準標籤中選擇。使用非標準標籤時，`lessons_search.py --list-tags` 會顯示 ⚠️ 警告。

| 類別 | 標籤 |
|------|------|
| **安全** | `security`, `auth`, `token`, `rbac`, `audit`, `firmware` |
| **架構** | `architecture`, `edge`, `cloud`, `cloud-sync`, `sync`, `api` |
| **程式碼品質** | `linting`, `testing`, `tdd`, `async`, `performance`, `dataclass`, `datetime` |
| **功能模組** | `cli`, `batch`, `ui`, `tui`, `llm`, `queue`, `database`, `migration`, `polling` |
| **框架** | `flask`, `fastapi`, `rabbitmq`, `sqs`, `javascript` |
| **維運** | `ops`, `launcher`, `playbook`, `device`, `platform` |
| **文件** | `template` |

### 標籤使用規則

1. **每個條目至少 1 個、建議 3-5 個**標籤
2. 優先使用標準標籤，如需新增請先更新 `STANDARD_TAGS`（在 `scripts/lessons_search.py`）並同步至本文件表格
3. 標籤以小寫英文書寫，多字詞用連字號（如 `cloud-sync`）

---

## 2. 優先級（Priority）分類

### 三級制說明

| 優先級 | 圖示 | 說明 | 範例 |
|--------|------|------|------|
| `high` | 🔴 | 核心安全/架構規則，幾乎每次開發都需要遵守 | 路徑穿越防護、Token 安全生成、Linting |
| `medium` | 🟡 | 特定功能開發時需要，中頻使用 | 批次操作、TUI 整合、雲端同步 |
| `low` | ⚪ | 特定場景才需要，低頻使用或已有替代方案 | 範本、特定框架版本差異 |

### 優先級評定原則

- **high**：違反此規則會導致安全漏洞、系統崩潰或重大品質問題
- **medium**：對特定功能開發有幫助，但不是每次都需要
- **low**：補充知識，違反不會立即造成問題

---

## 3. 搜尋工具（`scripts/lessons_search.py`）

### 安裝需求

此工具僅使用 Python 標準庫，無需額外安裝依賴。

### 基本用法

```bash
# 顯示完整說明
python scripts/lessons_search.py --help

# 依標籤搜尋
python scripts/lessons_search.py --tag security

# 依優先級篩選
python scripts/lessons_search.py --priority high

# 依關鍵字搜尋（搜尋標題、摘要、標籤，不分大小寫）
python scripts/lessons_search.py --keyword token

# 組合條件
python scripts/lessons_search.py --tag security --priority high --keyword token

# 列出所有使用的標籤及統計
python scripts/lessons_search.py --list-tags

# 列出 review_date 已過期的條目（需複查）
python scripts/lessons_search.py --stale-days 0

# 指定自訂索引路徑
python scripts/lessons_search.py --index path/to/INDEX.md --tag security
```

### 輸出格式範例

```
🔍 搜尋結果（tag=security, priority=high）
============================================================
  🔴 [HIGH] Security Best Practices
     📁 docs/memory/security_lessons.md
     🏷  security, token, auth, rbac, audit
     📅 2025-12-17  （複查：2026-06-17）
     📝 Token 生成、動作驗證、密碼處理、審計日誌。

共 1 筆
```

---

## 4. 定期清理機制

### 複查週期建議

| 優先級 | 建議複查週期 | review_date 設定方式 |
|--------|------------|---------------------|
| `high` | 每 6 個月 | 新增日期 + 6 個月 |
| `medium` | 每 6 個月 | 新增日期 + 6 個月 |
| `low` | 每 12 個月 | 新增日期 + 12 個月 |

### 手動清理流程（建議每季執行）

```bash
# 步驟 1：找出需複查的條目
python scripts/lessons_search.py --stale-days 0

# 步驟 2：逐一審視條目
# - 仍然適用 → 更新 review_date
# - 已過時 → 在條目 title 加上 [OUTDATED] 並考慮移除
# - 已有更好方案 → 更新摘要並加上參考連結

# 步驟 3：更新 INDEX.md 中的 review_date 欄位
```

### 過時條目標記規範

在 `docs/memory/INDEX.md` 中，對過時條目的 title 加上前綴：

```yaml
- title: "[OUTDATED] Flask 舊版 JSON 配置"
  ...
  summary: 已由 Flask 2.3+ 新 API 取代，詳見 #15 號條目。
```

---

## 5. 新增條目流程

```bash
# 步驟 1：複製範本
cp docs/memory/TEMPLATE.md docs/memory/your_topic_lessons.md

# 步驟 2：填寫內容（必填欄位）
# - Title, Author, Date, Priority, Tags, Summary, Review Date

# 步驟 3：新增至索引
# 在 docs/memory/INDEX.md 加入對應條目

# 步驟 4：更新 PROJECT_MEMORY.md（若為高頻經驗）
# 在「關鍵經驗精華」章節加入摘要

# 步驟 5：驗證標籤合規性
python scripts/lessons_search.py --list-tags
```

---

## 6. 相關測試

```bash
# 執行搜尋工具單元測試
python -m pytest tests/test_lessons_search.py -v

# 預期結果：42 個測試全數通過
```

---

**最後更新**：2026-03-04
