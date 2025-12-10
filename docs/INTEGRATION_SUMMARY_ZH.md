# WebUI/MCP/Robot-Console 完整整合摘要

> **最後更新**: 2025-12-10  
> **版本**: v1.0

---

## 整合架構

本專案實現了 WebUI、MCP 和 Robot-Console 三大模組的完整整合，透過統一的後端服務管理器（BackendServiceManager）自動管理所有服務的生命週期。

### 統一後端服務管理器

**BackendServiceManager** 負責：
- 自動啟動 Flask API、MCP Service、WebUI 等後端服務
- 自動偵測專案根目錄、分配埠號
- 執行健康檢查
- 管理 Token 安全性
- 提供秘密除錯模式

### 使用者體驗

**一般模式**（預設）：
- 使用者透過 Electron 或 PyQt 應用啟動
- 完全隱藏底層進程細節
- 只顯示簡潔的訊息：
  ```
  Starting application...
  Application ready
  ```
- 無技術術語、無日誌輸出
- 日誌級別：WARNING（僅顯示警告和錯誤）

**秘密除錯模式**（開發者專用）：
- 詳細的服務啟動日誌
- 健康檢查結果
- Token 資訊（部分遮蔽）
- 埠號和配置
- 錯誤堆疊追蹤
- 自動生成除錯文件（`docs/developer/DEBUG_MODE.md`）
- 日誌級別：DEBUG（顯示所有資訊）

---

## 秘密除錯模式啟用方式

### ⚠️ 重要：必須同時滿足三個條件

秘密除錯模式需要**同時**啟用以下三個隱蔽條件，缺一不可：

#### 條件 1：設定特殊環境變數
```bash
export __ROBOT_INTERNAL_DEBUG__=1
```

#### 條件 2：建立隱藏檔案標記
```bash
touch .robot_debug  # 在專案根目錄建立此檔案
```

#### 條件 3：設定特殊埠號
```bash
export DEBUG_PORT=54321
```

### 完整啟用範例

#### Linux / macOS

```bash
# 步驟 1: 設定環境變數
export __ROBOT_INTERNAL_DEBUG__=1
export DEBUG_PORT=54321

# 步驟 2: 建立隱藏檔案
touch .robot_debug

# 步驟 3: 啟動應用程式
python3 qtwebview-app/main.py
# 或
npm start
```

#### Windows (PowerShell)

```powershell
# 步驟 1: 設定環境變數
$env:__ROBOT_INTERNAL_DEBUG__="1"
$env:DEBUG_PORT="54321"

# 步驟 2: 建立隱藏檔案
New-Item -ItemType File -Path .robot_debug -Force

# 步驟 3: 啟動應用程式
python qtwebview-app/main.py
# 或
npm start
```

### 除錯模式輸出範例

啟用後，你會看到：

```
Internal diagnostics enabled
Debug documentation generated at docs/developer/
2025-12-10 10:30:00,123 - backend_service_manager - DEBUG - 正在啟動 Flask API...
2025-12-10 10:30:00,124 - backend_service_manager - DEBUG - 使用埠號: 5000
2025-12-10 10:30:00,125 - backend_service_manager - DEBUG - Token 已生成: a1b2c3d4...
2025-12-10 10:30:03,200 - backend_service_manager - DEBUG - Flask API 啟動成功並通過健康檢查
2025-12-10 10:30:03,201 - backend_service_manager - DEBUG - 正在啟動 MCP Service...
2025-12-10 10:30:08,300 - backend_service_manager - DEBUG - MCP Service 啟動成功並通過健康檢查
2025-12-10 10:30:08,301 - backend_service_manager - INFO - 服務啟動完成: 2/2 成功
```

### 自動生成的除錯文件

啟用除錯模式後，系統會自動生成：

```
docs/
└── developer/          # 只在除錯模式下可見
    ├── .gitignore      # 防止意外提交
    └── DEBUG_MODE.md   # 完整除錯指南
```

---

## 應用程式整合

### PyQt (Tiny 版本)

```python
from src.common.backend_service_manager import BackendServiceManagerSync

# 自動檢測秘密除錯模式並啟動所有後端服務
backend_manager = BackendServiceManagerSync()
success_count, total_count = backend_manager.start_all()

# 取得服務 URL
flask_url = backend_manager.get_service_url('flask')
mcp_url = backend_manager.get_service_url('mcp')
```

### Electron (Heavy 版本)

```javascript
const BackendLauncher = require('./backend-launcher');

// 自動檢測秘密除錯模式並啟動
const launcher = new BackendLauncher();
const result = await launcher.start();

// result.flask_url: http://127.0.0.1:5000
// result.mcp_url: http://127.0.0.1:8000
```

---

## 整合驗證

### 驗證腳本

```bash
# 快速驗證（檢查檔案和目錄）
python3 verify_integration.py --quick

# 完整驗證（包含依賴和模組）
python3 verify_integration.py

# 輸出報告
python3 verify_integration.py --output report.json
```

### 驗證結果

✅ **30/30 項檢查通過**：
- 9 個目錄結構檢查
- 15 個關鍵檔案檢查
- 6 個整合文件完整性檢查

---

## 整合點摘要

### WebUI ↔ MCP

- **通訊方式**: HTTP REST API
- **端點**: `http://localhost:8000/api`
- **範例**:
  ```python
  response = requests.get(f'{MCP_API_URL}/llm/providers')
  ```

### MCP ↔ Robot-Console

- **方式 1**: 本地佇列（推薦）
  ```python
  message = Message(id=uuid4(), payload={"actions": ["go_forward"]})
  await queue.enqueue(message)
  ```

- **方式 2**: MQTT（分散式環境）
  ```python
  mqtt_client.publish("robot/commands", json.dumps({"actions": ["go_forward"]}))
  ```

---

## 安全注意事項

### 秘密除錯模式的安全性

1. **三重認證機制**: 必須同時滿足三個條件，大幅提高啟用門檻
2. **隱藏檔案**: `.robot_debug` 已加入 `.gitignore`，不會被提交
3. **特殊命名**: 環境變數使用 `__ROBOT_INTERNAL_DEBUG__`，避免與其他工具衝突
4. **特殊埠號**: `54321` 不是常用埠號，降低意外啟用的可能性

### 最佳實踐

✅ **應該**：
- 只在開發環境使用除錯模式
- 使用後刪除 `.robot_debug` 檔案
- 分享日誌前移除敏感資訊

❌ **不應該**：
- 在生產環境啟用除錯模式
- 將 `.robot_debug` 提交到版本控制
- 分享含有完整 Token 的日誌

---

## 相關文件

- [完整整合指南](INTEGRATION_GUIDE.md) - 詳細的資料流向、整合點、配置說明
- [系統架構](architecture.md) - Server-Edge-Runner 三層架構
- [權威規格](proposal.md) - 資料契約、API 端點定義
- [端到端測試](../tests/test_e2e_integration.py) - 8 個整合測試場景

---

## 常見問題

### Q: 為什麼需要三個條件同時滿足？

A: 這是一個安全機制，確保只有真正的開發者能啟用除錯模式。單一條件容易被意外觸發，三個條件同時滿足則幾乎不可能意外發生。

### Q: 如果忘記關閉除錯模式會怎樣？

A: `.robot_debug` 檔案已加入 `.gitignore`，不會被提交。但建議使用後立即刪除：
```bash
rm .robot_debug
unset __ROBOT_INTERNAL_DEBUG__
unset DEBUG_PORT
```

### Q: 除錯模式會影響效能嗎？

A: 會，除錯模式會產生大量日誌輸出，可能略微降低效能。因此不建議在生產環境使用。

### Q: 如何關閉除錯模式？

A: 移除任一條件即可關閉：
```bash
# 移除檔案
rm .robot_debug

# 或取消環境變數
unset __ROBOT_INTERNAL_DEBUG__
# 或
unset DEBUG_PORT
```

---

**文件版本**: 1.0  
**最後更新**: 2025-12-10  
**維護者**: 開發團隊
