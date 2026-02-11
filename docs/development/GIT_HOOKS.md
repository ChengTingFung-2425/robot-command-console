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

# 跳過測試（只執行 linting、OpenAPI 和文檔檢查）
./scripts/pre-push.sh --skip-tests

# 顯示幫助訊息
./scripts/pre-push.sh --help
```

### 檢查模式

| 模式 | 檢查項目 | 執行時間 | 適用場景 |
|------|---------|---------|---------|
| **--quick** | Linting + 語法檢查 | < 1 分鐘 | 頻繁提交、快速驗證 |
| **--skip-tests** (預設) | Quick + OpenAPI + 文檔 | < 2 分鐘 | 日常開發、推送前檢查 |
| **--full** | 所有檢查 + 測試 | 5-10 分鐘 | 重要變更、PR 提交前 |

### 檢查項目詳細說明

#### Level 1: 快速檢查 (來自 ci.yml)

1. **Python Flake8 Linting**
   - 檢查主要 Python 檔案 (flask_service.py, run_service_cli.py)
   - 檢查 src/ 目錄
   - 檢查 MCP/ 目錄
   - 參數：`--max-line-length=120 --ignore=W503,E203`

2. **Node.js 語法檢查**
   - 檢查 electron-app/main.js
   - 檢查 electron-app/preload.js

#### Level 2: 中級檢查 (來自 ci.yml & api-validation.yml)

3. **OpenAPI 規範驗證**
   - 驗證 openapi.yaml 語法
   - 檢查必要欄位 (openapi, info, paths)
   - 驗證安全方案定義
   - 檢查健康檢查端點 (/health, /metrics)

4. **文檔完整性檢查**
   - docs/security/threat-model.md
   - docs/security/security-checklist.md
   - docs/features/observability-guide.md
   - docs/architecture.md
   - docs/proposal.md
   - openapi.yaml

### 跳過檢查

如果需要跳過 pre-push 檢查（不建議），可以使用：

```bash
git push --no-verify
```

### 輸出範例

```bash
$ ./scripts/pre-push.sh

═══════════════════════════════════════════════════════════
  Pre-Push 檢查 (模式: skip-tests)
═══════════════════════════════════════════════════════════

檢查模式: skip-tests
整合來源: ci.yml, api-validation.yml, test-rabbitmq.yml
排除項目: build.yml (打包流程)

說明: 標準檢查，跳過測試（適合日常開發）

═══════════════════════════════════════════════════════════
  Level 1: 快速檢查 (ci.yml)
═══════════════════════════════════════════════════════════

➤ [1] Python Flake8 Linting (ci.yml: python-lint)
  檢查主要 Python 檔案...
✓ 主要 Python 檔案檢查通過
  檢查 src/ 目錄...
✓ src/ 目錄檢查通過
  檢查 MCP/ 目錄...
✓ MCP/ 目錄檢查通過
✓ Python Flake8 Linting 完成

...

═══════════════════════════════════════════════════════════
  檢查完成
═══════════════════════════════════════════════════════════

統計資訊:
  總檢查數: 4
  通過: 4
  失敗: 0
  跳過: 0
  執行時間: 5 秒

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ 所有檢查通過！可以安全推送。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 疑難排解

**問題：Hook 沒有執行**
- 確認 `.git/hooks/pre-push` 檔案存在
- 確認檔案有執行權限：`chmod +x .git/hooks/pre-push`
- 確認檔案不是符號連結（Git hooks 不支援符號連結）

**問題：依賴未安裝**
- Python: `pip install flake8 pytest openapi-spec-validator pyyaml`
- Node.js: 確認已安裝 Node.js

**問題：檢查失敗**
1. 查看詳細錯誤訊息
2. 根據錯誤類型修正：
   - Linting 錯誤：修正程式碼風格
   - 測試失敗：修正測試或程式碼邏輯
   - 文檔缺失：補充必要文檔
3. 使用 `--quick` 模式進行快速驗證
4. 最後選擇：`git push --no-verify` 跳過（不建議）

### CI 一致性保證

Pre-push hook 的檢查項目與 CI workflows 完全一致：

```bash
# 本地檢查 = CI 檢查（排除 build.yml）
./scripts/pre-push.sh --full

# 等同於執行：
# - ci.yml 的 python-lint, node-lint, python-test, security-test, docs-check
# - api-validation.yml 的 validate-openapi, test-security, check-docs
# - test-rabbitmq.yml 的 unit-tests
```

這確保了：
- ✅ 本地推送前就能發現 CI 會檢測到的問題
- ✅ 減少 CI 失敗次數
- ✅ 加快開發迭代速度

## 團隊協作

### 推薦工作流程

1. **日常開發**：每次推送前自動執行標準檢查
   ```bash
   git push  # 自動執行 --skip-tests 模式
   ```

2. **頻繁提交**：使用快速模式進行驗證
   ```bash
   ./scripts/pre-push.sh --quick && git push --no-verify
   ```

3. **PR 提交前**：執行完整檢查
   ```bash
   ./scripts/pre-push.sh --full
   ```

### 安裝腳本

建議所有團隊成員執行以下命令來安裝 hook：

```bash
# 測試 hook 是否正常工作
./scripts/pre-push.sh --quick

# 安裝 hook
cp scripts/pre-push.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push

# 驗證安裝
.git/hooks/pre-push --help
```

### 團隊規範

1. **必須安裝 pre-push hook**：所有開發者都應安裝
2. **避免使用 --no-verify**：除非有充分理由
3. **PR 前執行完整檢查**：使用 `--full` 模式
4. **CI 失敗必須修復**：不要合併失敗的 PR

## 參考資源

- [Git Hooks 文件](https://git-scm.com/docs/githooks)
- [Flake8 文件](https://flake8.pycqa.org/)
- [OpenAPI Validator](https://pypi.org/project/openapi-spec-validator/)
- [Pytest 文件](https://docs.pytest.org/)

---

**最後更新**: 2026-02-11  
**版本**: 2.0（整合所有 CI 檢查，排除 build.yml）
