# Git Hooks 使用指南

本專案使用 Git hooks 來確保程式碼品質，整合 CI workflows 的檢查到本地開發環境。

## Pre-Push Hook

Pre-push hook 會在 `git push` 之前自動執行，整合了 **ci.yml**、**api-validation.yml** 和 **test-rabbitmq.yml** 的所有檢查（排除 build.yml 的打包流程）。

### 整合的 CI 檢查

| CI Workflow | 整合檢查項目 | 狀態 |
|-------------|-------------|------|
| **ci.yml** | Python linting, Node.js 語法, 單元測試, 安全測試, 文檔檢查 | ✅ 已整合 |
| **api-validation.yml** | OpenAPI 規範驗證, 安全文檔檢查 | ✅ 已整合 |
| **test-rabbitmq.yml** | RabbitMQ 單元測試 | ✅ 已整合 |
| **build.yml** | 打包流程 | ❌ 排除（由 CI 處理） |

### 安裝

```bash
# 複製 hook 腳本到 .git/hooks/
cp scripts/pre-push.sh .git/hooks/pre-push

# 確保腳本可執行
chmod +x .git/hooks/pre-push
```

### 使用方式

```bash
# 執行標準檢查（預設模式，跳過測試）
./scripts/pre-push.sh

# 快速檢查（只執行 linting 和語法檢查）
./scripts/pre-push.sh --quick

# 完整檢查（包含所有測試）
./scripts/pre-push.sh --full

# 顯示幫助訊息
./scripts/pre-push.sh --help
```

### 檢查模式

| 模式 | 檢查項目 | 執行時間 | 適用場景 |
|------|---------|---------|---------|
| **--quick** | Linting + 語法檢查 | < 1 分鐘 | 頻繁提交、快速驗證 |
| **--skip-tests** (預設) | Quick + OpenAPI + 文檔 | < 2 分鐘 | 日常開發、推送前檢查 |
| **--full** | 所有檢查 + 測試 | 5-10 分鐘 | 重要變更、PR 提交前 |

### CI 一致性保證

Pre-push hook 的檢查項目與 CI workflows 完全一致，確保本地推送前就能發現 CI 會檢測到的問題。

## 參考資源

- [Git Hooks 文件](https://git-scm.com/docs/githooks)
- [Flake8 文件](https://flake8.pycqa.org/)
- [OpenAPI Validator](https://pypi.org/project/openapi-spec-validator/)

---

**最後更新**: 2026-02-11  
**版本**: 2.0（整合所有 CI 檢查，排除 build.yml）
