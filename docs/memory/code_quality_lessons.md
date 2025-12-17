# Code Quality Lessons

此文件包含代碼品質優化的詳細經驗教訓。

包含：Linting 自動化、測試策略、重構經驗等。

---

## 🔧 倉庫代碼品質優化（2025-12-17）

### 優化目標

基於專案記憶中的經驗教訓，對整個倉庫進行代碼品質檢查和優化。

### 執行的優化

1. **代碼品質修正**
   - 修正 E226: 運算符周圍缺少空格（6 處）
   - 修正 E501: 行過長問題（1 處）
   - 移除 F401: 未使用的導入（8 處）

2. **修正文件清單**
   - `src/common/backend_service_manager.py`: 修正運算符空格
   - `src/llm_discovery/bridge.py`: 移除未使用導入
   - `src/llm_discovery/discovery_service.py`: 移除未使用導入
   - `src/llm_discovery/mcp_adapter.py`: 移除未使用導入
   - `src/llm_discovery/models.py`: 修正行長度和未使用導入
   - `src/robot_service/llm_command_processor.py`: 移除未使用導入

3. **驗證結果**
   - ✅ 所有 E/F 級別問題已修正（0 個錯誤）
   - ✅ 所有測試通過（36/36, 100%）
   - ✅ 功能完全正常

### 代碼品質改進統計

```
修正前：15 個 E/F 級別問題
修正後：0 個問題
改進率：100%
```

**詳細分類**：
- E226 (運算符空格): 6 個 → 0 個
- E501 (行過長): 1 個 → 0 個
- F401 (未使用導入): 8 個 → 0 個

### 經驗教訓

#### 14.1 運算符周圍空格（E226）

```python
# ❌ 錯誤寫法
print("="*60)
result = f"{i+1}/{max_retries}"

# ✅ 正確寫法
print("=" * 60)
result = f"{i + 1}/{max_retries}"
```

**原因**：PEP 8 要求運算符周圍有空格，提高可讀性

#### 14.2 未使用導入的檢測

```python
# ❌ 導入但未使用
import asyncio  # 若代碼中沒使用 asyncio
from .models import Skill  # 若只在字串中提到

# ✅ 正確做法
# 只導入實際使用的模組
import logging
from typing import Dict, Any
```

**經驗教訓**：
1. **IDE 提示**：使用 IDE 的未使用導入警告
2. **自動化檢查**：flake8 --select=F401 專門檢查
3. **字串引用**：在註解或字串中的類型名不算使用

#### 14.3 行長度限制（E501）

```python
# ❌ 過長的行（> 120 字元）
anti_decryption = AntiDecryptionConfig(**anti_decryption_data) if anti_decryption_data else AntiDecryptionConfig()

# ✅ 正確的多行寫法
anti_decryption = (AntiDecryptionConfig(**anti_decryption_data)
                   if anti_decryption_data
                   else AntiDecryptionConfig())
```

**經驗教訓**：
1. **合理斷行**：在邏輯單元處斷行
2. **括號對齊**：保持視覺上的對齊
3. **可讀性優先**：不要為了節省行數犧牲可讀性

#### 14.4 代碼品質自動化流程

```bash
# 1. 檢查整個專案
python3 -m flake8 src/ --select=E,F --exclude=.venv,node_modules

# 2. 查看統計
python3 -m flake8 src/ --statistics

# 3. 修正後驗證
python3 -m flake8 src/ --select=E,F

# 4. 運行測試確保無破壞
python3 -m pytest tests/ -v
```

**最佳實踐**：
1. **分級修正**：先修 E/F 級別，再考慮 W 級別
2. **小步提交**：每修正一類問題就提交
3. **持續驗證**：每次修正後運行測試
4. **文件更新**：在專案記憶中記錄經驗

#### 14.5 TODO 項目管理

**發現的 TODO 項目**：
```python
# src/robot_service/batch/executor.py:493
# TODO: 實作真正的結果等待邏輯

# src/robot_service/tui/app.py:523
# TODO: 與 OfflineQueueService 或 NetworkMonitor 整合

# src/robot_service/tui/app.py:545
# TODO: 與 LLMProviderManager 整合

# src/robot_service/llm_command_processor.py:372
# TODO: 實作 Anthropic API 整合
```

**管理策略**：
1. **分類 TODO**：緊急 vs 未來優化
2. **追蹤進度**：在 GitHub Issues 中追蹤
3. **定期檢視**：每個 Phase 結束時檢視
4. **文件記錄**：重要的 TODO 記錄在專案記憶

### 優化成果總結

**代碼品質**：
- ✅ E/F 級別問題：15 → 0
- ✅ 代碼風格一致性：100%
- ✅ 所有測試通過：36/36

**可維護性提升**：
- 更清晰的代碼結構
- 更好的可讀性
- 更少的技術債

**自動化檢查**：
- flake8 檢查通過
- pytest 測試通過
- 無警告和錯誤

---

**最後更新**：2025-12-17
