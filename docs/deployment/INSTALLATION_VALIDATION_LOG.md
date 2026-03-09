# 安裝測試與環境驗證紀錄

> **建立日期**：2026-03-09  
> **目的**：記錄本輪在 CI/雲端環境執行的安裝步驟與驗證結果，讓後續開發者能快速重現環境、追蹤缺失依賴並補強測試前置設定。

---

## 🖥️ 測試環境

- 作業系統：Ubuntu 24.04 (kernel 6.14.0-1017-azure, x86_64)
- Python：3.12.3（系統預設）
- pip：24.0
- 執行位置：倉庫根目錄 `/home/runner/work/robot-command-console/robot-command-console`

---

## 📦 安裝步驟

```bash
# 1) 安裝核心依賴
pip install -r requirements.txt

# 2) 預期（未安裝）：Edge Tiny 依賴
#    若需 Tiny 版本，需另外安裝 Edge/qtwebview-app 所需套件

# 3) 驗證指令（本次執行）
python -m pytest -q
```

---

## ✅/⚠️ 驗證結果

| 驗證項目 | 指令 | 結果 | 備註 |
|----------|------|------|------|
| 依賴安裝 | `pip install -r requirements.txt` | ✅ 成功 | 核心依賴可順利安裝 |
| 測試收集 | `python -m pytest -q` | ⚠️ 失敗（24 個收集錯誤） | 缺少模組與套件，細節如下 |

### 主要阻塞原因

1. **模組路徑未解析**：`MCP`, `robot_service`, `common` 等模組因未設定 `PYTHONPATH` 或缺少對應封裝而導致 `ModuleNotFoundError`。  
2. **缺失依賴**：測試載入時需要但未安裝的套件（例如 `pydantic`, `paramiko`）。  

### 建議後續處理

- 在本地或 CI 執行測試前，加入路徑設定：`export PYTHONPATH="src:Edge:."`（或建立對應封裝/安裝腳本）。  
- 將缺失依賴補入安裝流程（如 `pydantic`, `paramiko`，以及 Tiny 版本需要的額外 Qt 相關套件）。  
- 若僅需部分測試，可先以 `python -m pytest tests/<target>::<case> -q` 逐步驗證，並確認路徑/依賴完整後再跑全套。  

---

## 📌 總結

- **目前安裝步驟可成功完成核心依賴安裝。**  
- **測試執行仍受模組路徑與缺失依賴阻塞，需補充 `PYTHONPATH` 設定與安裝額外套件後再進行。**  
- 後續可在此文件下方持續追加新的驗證批次與結果，以建立可追溯的安裝/測試紀錄。  
