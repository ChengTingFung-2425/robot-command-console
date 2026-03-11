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
# 1) 依環境安裝對應模組依賴
pip install -r Cloud/requirements.txt
pip install -r Edge/requirements.txt
pip install -r Executor/requirements.txt

# 2) 驗證指令（本次執行）
python -m pytest -q
```

---

## ✅/⚠️ 驗證結果

| 驗證項目 | 指令 | 結果 | 備註 |
|----------|------|------|------|
| 依賴安裝 | `pip install -r <submodule>/requirements.txt` | ✅ 成功 | 各環境改由對應子模組依賴管理 |
| 測試收集 | `python -m pytest -q` | ⚠️ 失敗（24 個收集錯誤） | 缺少模組與套件，細節如下 |

### 主要阻塞原因

1. **模組路徑未解析**：`MCP`, `robot_service`, `common` 等模組因未設定 `PYTHONPATH` 或缺少對應封裝而導致 `ModuleNotFoundError`。  
2. **環境需安裝對應子模組依賴**：測試載入 `MCP` / Edge 模組時需要 `pydantic`、`paramiko` 等套件；這些套件已列在 `Edge/requirements.txt`，應由 Edge 環境自行安裝。  

### 建議後續處理

- 若要執行完整測試，先依執行範圍安裝對應的 `Cloud/requirements.txt`、`Edge/requirements.txt`、`Executor/requirements.txt`。  
- 在本地或 CI 執行測試前，加入路徑設定：`export PYTHONPATH="src:Edge:."`（或建立對應封裝/安裝腳本）。  
- 若僅需部分測試，可先以 `python -m pytest tests/<target>::<case> -q` 逐步驗證，並確認路徑/依賴完整後再跑全套。  

---

## 📌 總結

- **目前各子模組依賴可獨立安裝，較符合 package-by-package 建置需求。**  
- **測試執行仍受模組路徑與特定環境依賴是否已安裝影響，需補充 `PYTHONPATH` 設定後再進行。**  
- 後續可在此文件下方持續追加新的驗證批次與結果，以建立可追溯的安裝/測試紀錄。  
