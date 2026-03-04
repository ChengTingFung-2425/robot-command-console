# Memory Index

此索引列出 `docs/memory/` 內的重要操作手冊與經驗記錄，並提供標籤（tags）、優先級（priority）、作者與快速連結，方便搜尋與引用。

> **搜尋工具**：`python scripts/lessons_search.py --help`
> **清理提醒**：每季度檢視，將超過 6 個月未更新且不再適用的條目標記 `[OUTDATED]` 或移除。

---

- title: Unified Launcher Playbook
  path: docs/memory/unified_launcher_playbook.md
  tags: [launcher, ops, token, playbook]
  priority: medium
  author: Cheng Ting Fung
  date: 2025-12-17
  review_date: 2026-06-17
  summary: 操作與排障步驟、TokenIntegration 測試與常見故障排除。

- title: RabbitMQ & AWS SQS 佇列整合經驗
  path: docs/memory/rabbitmq-sqs-lessons.md
  tags: [rabbitmq, sqs, queue, performance, testing]
  priority: medium
  author: copilot
  date: 2026-01-05
  review_date: 2026-07-05
  summary: QueueInterface 設計、RabbitMQ/SQS Best Practices、效能比較、測試策略。

- title: 雲端同步 UI 狀態提示實作經驗
  path: docs/memory/cloud-sync-ui-lessons.md
  tags: [cloud-sync, ui, edge, polling, javascript, sync]
  priority: medium
  author: copilot
  date: 2026-02-11
  review_date: 2026-08-11
  summary: 雲端同步狀態面板、雙頻率更新策略、漸進式功能實作。

- title: Phase 3.1 經驗（時間處理、dataclass、鎖）
  path: docs/memory/phase3_lessons.md
  tags: [datetime, dataclass, async, architecture, testing]
  priority: high
  author: copilot
  date: 2025-12-01
  review_date: 2026-06-01
  summary: Python 時間處理（utc_now）、dataclass field default_factory、非重入鎖、競態條件防護。

- title: Phase 3.2 Qt WebView 整合經驗
  path: docs/memory/phase3_2_lessons.md
  tags: [architecture, security, ui, firmware, tui]
  priority: high
  author: copilot
  date: 2026-01-21
  review_date: 2026-07-21
  summary: 不重造輪子原則、WIP 替換流程、CodeQL 安全修復、固件更新安全流程。

- title: 安全最佳實踐
  path: docs/memory/security_lessons.md
  tags: [security, token, auth, rbac, audit]
  priority: high
  author: copilot
  date: 2025-12-17
  review_date: 2026-06-17
  summary: Token 生成、動作驗證、密碼處理、審計日誌。

- title: 程式碼品質（Linting、測試策略）
  path: docs/memory/code_quality_lessons.md
  tags: [linting, testing, tdd, api]
  priority: high
  author: copilot
  date: 2025-12-17
  review_date: 2026-06-17
  summary: Linting 修復策略、型別提示、TDD 流程、測試覆蓋率。

- title: CLI 批次操作經驗
  path: docs/memory/cli_batch_lessons.md
  tags: [cli, batch, testing, performance, async]
  priority: medium
  author: copilot
  date: 2025-12-17
  review_date: 2026-06-17
  summary: TDD 流程實踐、批次執行架構、錯誤處理、重複計數防護。

- title: TUI 與 LLM 整合經驗
  path: docs/memory/tui_llm_lessons.md
  tags: [tui, llm, async, api, performance]
  priority: medium
  author: copilot
  date: 2025-12-17
  review_date: 2026-06-17
  summary: TUI 架構設計、LLM 整合模式、HTTP 會話重用。

- title: Edge Token 系列（UUID、加密、快取、整合）
  path: docs/memory/step1-device-id-generator-lessons.md
  tags: [token, auth, edge, device, security]
  priority: high
  author: copilot
  date: 2025-12-17
  review_date: 2026-06-17
  summary: UUID 生成、Token 加密、平台存儲、快取策略、整合測試。

- title: 設備綁定跨平台識別
  path: docs/memory/device-binding-lessons.md
  tags: [device, edge, security, platform]
  priority: medium
  author: copilot
  date: 2025-12-17
  review_date: 2026-06-17
  summary: 跨平台設備識別策略、設備指紋綁定。

- title: (placeholder / template)
  path: docs/memory/TEMPLATE.md
  tags: [template]
  priority: low
  author: team
  date: 2025-12-17
  review_date: 2026-12-17
  summary: 記憶檔範本，用於新增其他記錄。

---

使用說明：
- 新增記憶檔時，請在此索引加入條目（title/path/tags/priority/author/date/review_date/summary）。
- `priority` 使用三級制：`high`（安全/架構核心）、`medium`（特定功能）、`low`（特定場景）。
- `review_date`：建議 3-6 個月後複查，過時條目標記 `[OUTDATED]` 或移除。
- 請盡量使用 `docs/memory/TEMPLATE.md` 的格式填寫新檔。
- 搜尋工具：`python scripts/lessons_search.py --tag security --priority high`