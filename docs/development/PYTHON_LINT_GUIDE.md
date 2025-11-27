# Python Lint 指南

本文件記錄專案中 Python 程式碼的 lint 規範與最佳實踐，基於實際開發經驗總結。

## 快速開始

```bash
# 安裝 lint 工具
pip install flake8 autopep8

# 檢查所有 E 和 F 級別問題（必須修復）
flake8 src/ MCP/ --max-line-length=120 --select=E,F

# 檢查所有問題
flake8 src/ MCP/ --max-line-length=120

# 自動修復格式問題
autopep8 --in-place --select=W291,W293 --recursive src/ MCP/
```

## 常見問題分類

### 嚴重問題（必須修復）

| 代碼 | 說明 | 修復方式 |
|------|------|----------|
| `F401` | 匯入但未使用 | 移除未使用的 import |
| `F541` | f-string 缺少變數 | 改用普通字串或加入變數 |
| `F821` | 使用未定義的名稱 | 加入正確的 import |
| `F841` | 變數賦值但未使用 | 移除或使用 `_` 前綴 |
| `E722` | 使用裸 except | 改用 `except Exception:` |
| `E501` | 行太長 | 拆分為多行 |

### 中等問題（必須修復）

| 代碼 | 說明 | 修復方式 |
|------|------|----------|
| `E127` | 續行過度縮排 | 調整縮排對齊開括號 |
| `E128` | 續行縮排不足 | 調整縮排對齊開括號 |
| `E261` | 行內註解前缺少兩個空格 | 加入兩個空格 |
| `E305` | 類別/函式後缺少空行 | 加入兩個空行 |
| `E226` | 運算子周圍缺少空格 | 加入空格 |
| `E402` | import 不在檔案頂部 | 重新組織或加 `# noqa: E402` |

### 輕微問題（可自動修復）

| 代碼 | 說明 | 修復方式 |
|------|------|----------|
| `W291` | 行尾空白 | `autopep8 --select=W291` |
| `W293` | 空白行包含空格 | `autopep8 --select=W293` |
| `W503` | 二元運算子前換行 | 可忽略（與 W504 互斥） |
| `W504` | 二元運算子後換行 | 調整換行位置 |

## 修復策略選項

### Option 1: 僅修復嚴重問題（最小範圍）

**優點：**
- 最小變更範圍，降低回歸風險
- 只修復會導致執行錯誤的問題
- 保持與現有程式碼風格一致

**缺點：**
- 不解決格式問題
- CI/CD 可能仍會報告警告

**適用場景：** 緊急修復、小型 PR

---

### Option 2: 修復嚴重 + 中等問題

**優點：**
- 修復所有可能影響程式碼品質的問題
- 改善程式碼可讀性
- 為未來 lint 檢查打基礎

**缺點：**
- 需要更多變更
- 可能影響 git blame 歷史

**適用場景：** 功能開發 PR

---

### Option 3: 完整清理

**優點：**
- 完全符合 PEP 8 標準
- CI/CD lint 檢查通過
- 統一程式碼風格

**缺點：**
- 大量變更
- 較高回歸風險
- 影響大量 git blame

**適用場景：** 專門的程式碼清理 PR

---

### Option 4: 自動修復 + 手動修復嚴重問題（推薦 ✅）

**優點：**
- 使用 autopep8 自動修復格式問題
- 手動修復關鍵問題
- 平衡效率與安全性
- 減少人為錯誤

**缺點：**
- 需要兩步驟執行
- 格式化工具可能改變非必要的程式碼

**適用場景：** 大多數 PR

## 實際案例（Lessons Learned）

### 案例 1: 未使用的 import (F401)

```python
# 錯誤
from typing import Any, Dict, List, Optional  # List 未使用

# 正確
from typing import Any, Dict, Optional
```

### 案例 2: 裸 except (E722)

```python
# 錯誤
try:
    do_something()
except:
    pass

# 正確
try:
    do_something()
except Exception:
    # 說明為何忽略此例外
    pass
```

### 案例 3: f-string 缺少變數 (F541)

```python
# 錯誤
logger.info(f"初始化完成")  # f-string 無變數

# 正確
logger.info("初始化完成")
# 或
logger.info(f"初始化完成: {component_name}")
```

### 案例 4: 變數賦值但未使用 (F841)

```python
# 錯誤
except Exception as e:  # e 未使用
    logger.error("Error occurred", exc_info=True)

# 正確
except Exception:
    logger.error("Error occurred", exc_info=True)
```

### 案例 5: 直接修改輸入參數

```python
# 錯誤 - 會影響呼叫者
def update_status(status: dict):
    status["updated_at"] = now()  # 直接修改輸入
    return status

# 正確 - 建立副本
def update_status(status: dict):
    return {**status, "updated_at": now()}
```

### 案例 6: 行太長 (E501)

```python
# 錯誤 - 超過 120 字元
if request.url.path in public_paths or request.url.path.startswith('/docs') or request.url.path.startswith('/openapi'):

# 正確 - 拆分多行
if (request.url.path in public_paths or
        request.url.path.startswith('/docs') or
        request.url.path.startswith('/openapi')):
```

### 案例 7: 續行縮排 (E127/E128)

```python
# 錯誤 - 縮排不對齊
logger.info(f"Configuration: queue_size={args.queue_size}, "
           f"workers={args.workers}")  # 縮排不足

# 正確 - 對齊開括號
logger.info(f"Configuration: queue_size={args.queue_size}, "
            f"workers={args.workers}")
```

### 案例 8: 運算子周圍空格 (E226)

```python
# 錯誤
response_text += f"{i+1}. {result.get('message')}\n"

# 正確
response_text += f"{i + 1}. {result.get('message')}\n"
```

### 案例 9: import 不在檔案頂部 (E402)

當 import 必須在 `sys.path` 修改後才能執行時，使用 `# noqa: E402`：

```python
import sys
import os

# 修改路徑
sys.path.insert(0, os.path.dirname(__file__))

# 這些 import 必須在路徑修改後
from mymodule import MyClass  # noqa: E402
```

### 案例 10: 長 import 語句

```python
# 錯誤 - 超過 120 字元
from common.datetime_utils import utc_now, utc_now_iso, parse_iso_datetime, format_timestamp, seconds_since  # noqa: E402

# 正確 - 使用多行 import
from common.datetime_utils import (  # noqa: E402
    utc_now, utc_now_iso, parse_iso_datetime, format_timestamp, seconds_since
)
```

### 案例 11: 類別定義後缺少空行 (E305)

```python
# 錯誤
class MyFormatter:
    def format(self):
        pass
# 配置區塊  <-- 只有一個空行
config = {}

# 正確
class MyFormatter:
    def format(self):
        pass


# 配置區塊  <-- 兩個空行
config = {}
```

## 專案特定配置

建議在專案根目錄建立 `.flake8`：

```ini
[flake8]
max-line-length = 120
exclude = .git, __pycache__, .venv, build, dist
# 不建議 ignore，應該修復所有問題
```

## 相關資源

- [PEP 8 -- Python 程式碼風格指南](https://peps.python.org/pep-0008/)
- [Flake8 文件](https://flake8.pycqa.org/)
- [autopep8 文件](https://pypi.org/project/autopep8/)

## 版本歷史

- **2025-11-27 v1.1** - 新增 E501, E127, E226, E402 案例，更新為不忽略任何 E 級別問題
- **2025-11-27 v1.0** - 初始版本，基於 PR #122 經驗總結
