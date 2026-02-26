# llm-helper — AI Agent 工具包

> 此目錄存放 AI Agent（GitHub Copilot、Claude 等）在開發流程中常用的輔助腳本。
> 根目錄的 `check_lint.py` 與 `run_tests.py` 均為指向本目錄的 shim，
> **此目錄才是唯一的維護地點**。

---

## 📦 目錄內容

| 檔案 | 用途 |
|------|------|
| `check_lint.py` | Python 與 JavaScript 靜態分析，可一鍵回報或自動修正問題 |
| `run_tests.py` | 統一測試入口：單元測試、整合測試、覆蓋率報告 |
| `README.md` | 本文件 |

---

## 🔍 check_lint.py — 靜態分析工具

### 用途

對整個 repo 執行 flake8（Python）與 Node.js 語法檢查（JavaScript），輸出摘要報告。

### 使用方式

```bash
# 從專案根目錄執行（使用 shim）
python check_lint.py

# 直接執行本目錄的正本
python llm-helper/check_lint.py
```

### 主要功能

| 函式 | 說明 |
|------|------|
| `check_python_lint()` | 執行 `flake8 --select=E,F`，只回報 Error / Fatal 級別 |
| `check_javascript_syntax()` | 以 `node --check` 驗證所有 `.js` 檔案語法 |
| `get_lint_summary()` | 回報 E/F/W 全量問題統計 |
| `fix_trailing_whitespace()` | 自動移除 Python 檔案尾端空白（需手動開啟） |

### Lint 規則摘要

```
--select=E,F          # 僅報告 E（錯誤）和 F（Fatal）
--max-line-length=120 # 行寬上限 120
--exclude=.venv,node_modules,__pycache__,Edge/electron-app,...
```

### 回傳值

- `0` — 全部通過
- 非 `0` — 存在問題，詳見 stdout

### AI Agent 工作流程建議

```
1. 修改程式碼後立即執行：  python llm-helper/check_lint.py
2. 若有 E/F 錯誤，修正後再次執行確認
3. 確認通過後再呼叫 report_progress 提交
```

---

## 🧪 run_tests.py — 測試執行工具

### 用途

統一測試入口，支援多種模式：單元測試、整合測試（含 RabbitMQ）、覆蓋率報告、特定測試。

### 使用方式

```bash
# 從專案根目錄執行（使用 shim）
python run_tests.py <mode> [options]

# 直接執行本目錄的正本
python llm-helper/run_tests.py <mode> [options]
```

### 測試模式

| 模式 | 指令範例 | 說明 |
|------|---------|------|
| `unit` | `python run_tests.py unit` | 單元測試，跳過 `@pytest.mark.integration` |
| `unit` + 覆蓋率 | `python run_tests.py unit --coverage` | 單元測試 + HTML/term 覆蓋率報告 |
| `integration` | `python run_tests.py integration` | 整合測試（模擬 RabbitMQ） |
| `integration` + RabbitMQ | `python run_tests.py integration --with-rabbitmq` | 需要真實 RabbitMQ 服務 |
| `all` | `python run_tests.py all` | 所有測試 |
| `all` + RabbitMQ + 覆蓋率 | `python run_tests.py all --with-rabbitmq --coverage` | CI 完整執行 |
| `specific` | `python run_tests.py specific --test-path tests/test_cloud_api.py` | 指定測試路徑 |
| `lint` | `python run_tests.py lint` | 對核心 src 執行 flake8 |

### 完整選項

```
positional arguments:
  {unit,integration,all,specific,lint}  測試模式

optional arguments:
  --with-rabbitmq    啟用 RabbitMQ 整合測試（需 RABBITMQ_URL 環境變數）
  --coverage         生成覆蓋率報告（htmlcov/、coverage.xml）
  --test-path PATH   特定測試路徑（僅用於 specific 模式）
  --check-rabbitmq   執行前先確認 RabbitMQ 是否可用
  -v, --verbose      詳細模式，印出完整指令
```

### 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | RabbitMQ 連線 URL |
| `TEST_WITH_RABBITMQ` | — | 由 `--with-rabbitmq` 自動設定 |

### AI Agent 工作流程建議

```
1. 實作新功能或修復後，先跑相關測試：
      python llm-helper/run_tests.py specific --test-path tests/path/to/test.py

2. 若特定測試通過，再跑完整單元測試確認無回歸：
      python llm-helper/run_tests.py unit

3. 修改涉及 RabbitMQ 的模組時：
      python llm-helper/run_tests.py integration

4. CI 完整流程（與 GitHub Actions 相同）：
      python llm-helper/run_tests.py all --coverage
```

---

## 🔧 CI 整合

以下工作流程直接使用這些工具（透過根目錄 shim）：

| 工作流程 | 相關腳本 |
|---------|---------|
| `.github/workflows/test-rabbitmq.yml` | `run_tests.py unit/integration/all` |
| `docker-compose.test.yml` | `run_tests.py all --with-rabbitmq --coverage` |

若需修改 lint 規則或測試行為，**請修改 `llm-helper/` 內的正本**，shim 會自動反映。

---

## 📝 新增工具

若需新增 AI Agent 輔助腳本，請：

1. 在 `llm-helper/` 建立新 `.py` 檔案
2. 若需要從根目錄呼叫，在根目錄建立 shim：
   ```python
   #!/usr/bin/env python3
   """Shim — delegates to llm-helper/<script>.py"""
   import os, runpy
   _here = os.path.dirname(os.path.abspath(__file__))
   runpy.run_path(os.path.join(_here, 'llm-helper', '<script>.py'), run_name='__main__')
   ```
3. 在本 README 的「目錄內容」表格中登記新工具
4. 在 `docs/PROJECT_MEMORY.md` 的 `llm-helper/` 段落補充說明

---

> 最後更新：2026-02-26 ｜ 維護者：AI Agent（GitHub Copilot）
