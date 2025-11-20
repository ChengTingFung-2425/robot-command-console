# Phase 2 遷移指南

本文件說明從 Phase 1 到 Phase 2 的目錄結構變更，以及開發者需要了解的遷移事項。

## 重大變更摘要

### 1. Electron 應用程序重新組織

**變更前：**
```
robot-command-console/
├── main.js
├── preload.js
├── renderer/
└── package.json
```

**變更後：**
```
robot-command-console/
├── electron-app/
│   ├── main.js
│   ├── preload.js
│   ├── renderer/
│   └── package.json
└── package.json (新增 - 根層級腳本)
```

**影響：**
- Electron 相關文件集中在 `electron-app/` 目錄
- 需要在 `electron-app/` 目錄下執行 `npm install`
- 或從根目錄執行 `npm run install:electron`

### 2. 測試目錄標準化

**變更前：**
```
Test/
├── test_auth_compliance.py
├── test_command_handler_compliance.py
└── ...
```

**變更後：**
```
tests/
├── test_auth_compliance.py
├── test_command_handler_compliance.py
└── ...
```

**影響：**
- 所有測試命令從 `Test/` 改為 `tests/`
- 符合 Python 社群慣例

### 3. 配置目錄新增

**新增：**
```
config/
└── README.md
```

**影響：**
- 新增配置集中管理的策略文檔
- `config.py` 保留在根目錄（向後相容）
- 未來配置文件建議放在此目錄

### 4. 文檔更新

**新增：**
- `docs/architecture.md` - 完整架構說明
- `config/README.md` - 配置策略文檔

**更新：**
- `README.md` - 反映新目錄結構
- 所有文檔中的 `Test/` 引用改為 `tests/`

## 遷移步驟

### 對於開發者

#### 1. 拉取最新代碼

```bash
git fetch origin
git checkout main  # 或你的分支
git pull origin main
```

#### 2. 安裝 Electron 依賴

```bash
# 方法 1: 從根目錄
npm run install:electron

# 方法 2: 進入 electron-app 目錄
cd electron-app
npm install
cd ..
```

#### 3. 更新測試命令

**舊命令：**
```bash
python3 -m pytest Test/ -v
```

**新命令：**
```bash
python3 -m pytest tests/ -v
# 或使用根層級 npm 腳本
npm test
```

#### 4. 更新啟動命令

**Electron 應用：**

舊命令（不再支援）：
```bash
npm start  # 在根目錄
```

新命令：
```bash
# 方法 1: 從根目錄（推薦）
npm start

# 方法 2: 從 electron-app 目錄
cd electron-app
npm start
```

**Flask 服務（無變更）：**
```bash
APP_TOKEN=xxx PORT=5000 python3 flask_service.py
```

**CLI 模式（無變更）：**
```bash
python3 run_service_cli.py --queue-size 1000 --workers 5
```

### 對於 CI/CD

#### GitHub Actions / GitLab CI

更新測試步驟：

**舊配置：**
```yaml
- name: Run tests
  run: python3 -m pytest Test/ -v
```

**新配置：**
```yaml
- name: Run tests
  run: python3 -m pytest tests/ -v
  # 或
  run: npm test
```

#### Docker

如果 Dockerfile 引用了舊路徑，需要更新：

**舊配置：**
```dockerfile
COPY main.js preload.js renderer/ ./
```

**新配置：**
```dockerfile
COPY electron-app/ ./electron-app/
```

### 對於文檔

如果你的分支或 PR 有自己的文檔變更：

1. 搜尋所有 `Test/` 引用並替換為 `tests/`：
   ```bash
   find . -name "*.md" -type f -exec sed -i 's/Test\//tests\//g' {} +
   ```

2. 檢查是否有引用 `main.js` 或 `renderer/` 的內容，更新為 `electron-app/main.js` 或 `electron-app/renderer/`

## 破壞性變更檢查清單

### ✅ 無破壞性變更

以下功能保持完全相容：

- [x] Python 服務 (`src/robot_service/`)
- [x] MCP 服務 (`MCP/`)
- [x] Robot-Console (`Robot-Console/`)
- [x] WebUI (`WebUI/`)
- [x] Flask 服務入口 (`flask_service.py`)
- [x] CLI 模式入口 (`run_service_cli.py`)
- [x] 配置文件 (`config.py`)
- [x] 所有 Python 導入路徑
- [x] 所有測試功能（71 個測試全部通過）

### ⚠️ 需要注意的變更

以下項目需要開發者手動調整：

1. **npm 腳本引用** - 如果你的腳本直接引用 `main.js`，需更新路徑
2. **測試命令** - 從 `Test/` 改為 `tests/`
3. **Electron 依賴安裝** - 需要在 `electron-app/` 目錄下執行 `npm install`
4. **文檔引用** - 如果你的文檔引用舊路徑，需要更新

## 常見問題

### Q1: 為什麼要進行這次重構？

A: 這次重構是為 Phase 2 打基礎，目標包括：
- 更清晰的模組劃分
- 符合社群最佳實踐（如 `tests/` 而非 `Test/`）
- 為未來擴展（分散式佇列、K8s 部署等）做準備
- 降低新開發者的學習曲線

### Q2: 舊分支如何處理？

A: 建議策略：
1. **進行中的 PR** - 合併此 PR 後，rebase 你的分支
2. **功能分支** - 根據需要選擇 merge 或 rebase
3. **長期維護分支** - 評估是否需要 backport 此變更

### Q3: 測試還能運行嗎？

A: 是的！所有 71 個測試在新結構下全部通過。只需要：
- 更新測試命令中的路徑（`Test/` → `tests/`）
- 其他測試邏輯完全不變

### Q4: Electron 應用還能正常啟動嗎？

A: 是的！啟動流程：
1. 確保安裝了依賴：`npm run install:electron` 或 `cd electron-app && npm install`
2. 從根目錄啟動：`npm start`
3. 或從 electron-app 目錄啟動：`cd electron-app && npm start`

### Q5: 需要更新 import 語句嗎？

A: **不需要**！所有 Python import 路徑保持不變：
```python
from MCP.auth_manager import AuthManager  # 仍然有效
from Robot-Console.action_executor import ActionExecutor  # 仍然有效
from robot_service.service_manager import ServiceManager  # 仍然有效
```

### Q6: 配置文件要放哪裡？

A: 配置策略：
1. **環境變數** - 開發和生產環境的首選方式
2. **config.py** - Flask 配置，保留在根目錄
3. **config/** 目錄 - 未來的配置文件建議放這裡
4. **.env** - 本地開發用（記得加入 .gitignore）

## 回滾指南

如果遇到問題需要回滾：

```bash
# 1. 切換到舊版本
git checkout <commit-before-refactor>

# 2. 或者反向合併
git revert <refactor-commit-sha>

# 3. 重新安裝依賴
npm install
pip install -r requirements.txt
```

## 獲取幫助

如果遇到遷移問題：

1. 查看 [architecture.md](architecture.md) 了解新結構
2. 查看 [README.md](../README.md) 了解啟動方式
3. 提交 Issue 描述你的問題
4. 在團隊頻道詢問

## 參考文檔

- [architecture.md](architecture.md) - 新架構詳解
- [README.md](../README.md) - 專案概覽
- [config/README.md](../config/README.md) - 配置策略
- [robot-service-migration.md](robot-service-migration.md) - Robot Service 遷移（Phase 1）

---

**最後更新：** 2025-11-20  
**適用版本：** Phase 2 (v1.0.0+)
