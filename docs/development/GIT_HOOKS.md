# Git Hooks 設置指南

本專案使用 Git hooks 來自動化程式碼品質檢查。

## Pre-Push Hook

在推送程式碼到遠端前自動執行 linting 檢查。

### 自動安裝

執行以下命令安裝 pre-push hook：

```bash
chmod +x scripts/pre-push.sh
cp scripts/pre-push.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

### 功能

Pre-push hook 會在每次 `git push` 前自動執行：

1. **Python Linting**: 使用 flake8 檢查 Python 程式碼
   - 僅檢查關鍵錯誤（E 和 F 級別）
   - 自動排除 migrations 和第三方檔案
   - 最多顯示前 20 個錯誤

2. **JavaScript 語法檢查**: 使用 node --check 驗證 JS 語法
   - 檢查所有非壓縮的 JavaScript 檔案
   - 自動排除 node_modules

### 輸出範例

```
🔍 Running pre-push linting checks...

📝 Checking Python linting...
✓ Python linting passed (0 critical errors)

📝 Checking JavaScript syntax...
✓ JavaScript syntax check passed

═══════════════════════════════════════════════════
✓ All linting checks passed! Pushing code...
═══════════════════════════════════════════════════
```

### 跳過檢查

如果需要跳過 linting 檢查（不建議），可以使用：

```bash
git push --no-verify
```

### 手動測試

測試 hook 是否正常工作：

```bash
# 執行 hook 腳本
./scripts/pre-push.sh

# 或直接執行 hook
.git/hooks/pre-push
```

## 其他 Hooks

### Pre-Commit Hook（未來可添加）

可以添加 pre-commit hook 來在提交前自動格式化程式碼：

```bash
#!/bin/bash
# 自動修復空白行空格
find . -name "*.py" -not -path "*/.venv/*" -exec sed -i 's/[[:space:]]*$//' {} +
```

### Commit-Msg Hook（未來可添加）

驗證提交訊息格式：

```bash
#!/bin/bash
# 檢查提交訊息是否符合規範
COMMIT_MSG=$(cat $1)
if ! echo "$COMMIT_MSG" | grep -qE "^(feat|fix|docs|style|refactor|test|chore):"; then
    echo "錯誤：提交訊息必須以類型前綴開頭"
    exit 1
fi
```

## 疑難排解

### Hook 沒有執行

1. 檢查檔案權限：
```bash
ls -la .git/hooks/pre-push
# 應該顯示 -rwxr-xr-x
```

2. 確保 hook 檔案存在：
```bash
test -f .git/hooks/pre-push && echo "Hook 存在" || echo "Hook 不存在"
```

3. 手動執行測試：
```bash
bash .git/hooks/pre-push
```

### Python 模組找不到

確保已安裝 flake8：

```bash
pip install flake8
```

### Node.js 找不到

確保已安裝 Node.js：

```bash
node --version
```

## 團隊協作

建議團隊成員都安裝相同的 hooks：

1. Clone 專案後執行安裝腳本
2. 保持 hooks 同步更新
3. 在 CI/CD 中執行相同的檢查

## 相關檔案

- `scripts/pre-push.sh` - Pre-push hook 腳本
- `check_lint.py` - 綜合 linting 檢查工具
- `.flake8` - Flake8 配置檔案（如存在）

---

**最後更新**: 2026-02-11
