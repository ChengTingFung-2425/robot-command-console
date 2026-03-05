# Memory Entry Template

請在新增 `docs/memory/` 記錄時複製此範本並填入內容。

---

**Title:**

**Author:**

**Date:**

**Priority:** `high` | `medium` | `low`

> **Priority 說明**：
> - `high`：核心安全/架構規則，幾乎每次開發都需要遵守
> - `medium`：特定功能開發時需要，中頻使用
> - `low`：特定場景才需要，低頻使用或已有替代方案

**Tags:** (從標準標籤庫選用，以逗號分隔)

> 完整標準標籤清單請參考 `scripts/lessons_search.py` 中的 `STANDARD_TAGS`，
> 或執行 `python scripts/lessons_search.py --list-tags` 查看目前使用中的標籤。
> 使用非標準標籤時工具會顯示 ⚠️ 警告，請儘量使用既有標籤或在 `STANDARD_TAGS` 中新增。

**Summary:**

**Background:**

**Problem / Symptoms:**

**Root Cause:**

**Resolution / Fix:**

**Step-by-step Repro / Runbook:**

```bash
# example commands
```

**Logs / Evidence:**

**Risk / Notes:**

**Review Date:** YYYY-MM-DD
> 建議每 3 個月檢視一次，過時條目請標記 `[OUTDATED]` 或移除。

**Related Files / PRs / Issues:**

**Change Log:**
- YYYY-MM-DD Author: small note

---

使用提醒：
- 不要在記憶檔中包含任何敏感金鑰或個資；若需包含日誌，請先 redact。
- 新增至 INDEX.md 時需同步填入 `priority` 與 `tags` 欄位。
- 搜尋工具：`python scripts/lessons_search.py --help`