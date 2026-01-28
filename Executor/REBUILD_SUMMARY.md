# Robot-Console 模組重建摘要

## 📅 重建日期
2025-10-22

## 🎯 重建目標
根據 `module.md` 設計文件完整重建 Robot-Console 模組

## ✅ 已完成的核心檔案

### 1. **action_executor.py** (原有，已保留)
- 動作執行引擎
- 佇列管理與排程
- 並行下發到本地與遠端控制器
- 支援緊急停止

### 2. **pubsub.py** (原有，已保留)
- AWS IoT Core MQTT 用戶端
- 支援 mTLS 與 WebSocket 雙模式
- 自動重連與容錯機制
- 訊息發佈與訂閱

### 3. **tools.py** (原有，已保留)
- 38+ 預定義動作定義
- AI/LLM 整合工具清單
- JSON Schema 定義
- 參數驗證功能

### 4. **settings.yaml** (原有，已保留)
- 機器人名稱設定
- AWS IoT Core 設定（端點、憑證）
- 遠端模擬器設定
- 本地控制器設定
- 執行器與日誌設定

### 5. **requirements.txt** (原有，已保留)
- awsiotsdk
- PyYAML
- requests
- jsonschema
- python-dateutil

### 6. **create_virtual_env.sh** (原有，已保留)
- 建立虛擬環境腳本
- 自動安裝依賴

### 7. **create_deploy_package.sh** (原有，已保留)
- 建立部署套件
- 排除 venv 與快取檔案

### 8. **module.md** (原有，已保留)
- 完整模組設計說明文件
- 包含所有架構與契約定義

### 9. **README.md** (新建)
- 模組簡介
- 快速開始指南
- 連結到詳細文件

## 📋 設計原則對齊

### 與 module.md 的對齊狀態
- ✅ 統一的機器人指令抽象
- ✅ 支援多種機器人類型
- ✅ 多協定支援（MQTT/HTTP）
- ✅ 非同步執行引擎
- ✅ 緊急停止機制
- ✅ 標準化契約（對齊 `docs/contract/*.schema.json`）
- ✅ 可靠性保證（超時、重試）
- ✅ 可觀測性（trace_id 追蹤）

### 支援的動作類別
1. **移動類** (6): go_forward, back_fast, left_move_fast, right_move_fast, turn_left, turn_right
2. **控制類** (4): stop, stand, stand_up_front, stand_up_back
3. **手勢類** (3): bow, wave, twist
4. **運動類** (7): push_ups, sit_ups, squat, squat_up, chest, weightlifting, stepping
5. **格鬥類** (8): kung_fu, wing_chun, left_kick, right_kick, left_uppercut, right_uppercut, left_shot_fast, right_shot_fast
6. **舞蹈類** (9): dance_two ~ dance_ten

**總計: 37 個動作**

## 🔧 技術特色

### action_executor.py
- 基於 `queue.PriorityQueue` 的優先權排程
- `CommandStatus` 狀態機（idle → accepted → running → succeeded/failed/cancelled）
- 支援緊急停止（清空佇列、中止當前、下發停止指令）
- 並行呼叫本地 (localhost:9030) 與遠端控制器
- 完整錯誤處理與超時控制

### pubsub.py
- AWS IoT SDK 整合
- 自動 mTLS → WebSocket 降級
- 連線中斷自動重連
- 主題訂閱與訊息驗證
- 狀態與事件發佈

### tools.py
- 每個動作的完整 JSON Schema
- 參數類型與範圍驗證
- 依類別分組查詢
- 支援 AI/LLM 工具調用

## 📝 使用範例

```bash
# 安裝依賴
cd Robot-Console
./create_virtual_env.sh
source venv/bin/activate

# 編輯設定
vi settings.yaml

# 測試執行器
python action_executor.py

# 測試 MQTT
python pubsub.py

# 測試工具
python tools.py
```

## 🔗 與其他模組的關係

```
MCP 服務層
    ↓ (發送標準化指令)
Robot-Console (本模組)
    ↓ (轉換為機器人特定格式)
協定適配器 (HTTP/MQTT/WS)
    ↓ (實際通訊)
機器人硬體/模擬器
```

## 📚 重要文件

1. **module.md** - 完整設計說明（必讀）
2. **README.md** - 快速入門
3. **settings.yaml** - 設定範例
4. **docs/contract/*.schema.json** - 標準化契約定義

## ⚠️ 注意事項

1. 實際使用前需設定有效的 AWS IoT 憑證
2. 本地控制器需在 localhost:9030 運行
3. 遠端模擬器需設定有效的 URL 與 session_key
4. 緊急停止功能需要完整的端到端測試

## 🎯 後續工作

- [ ] 完整的單元測試
- [ ] 整合測試（與 MCP 層）
- [ ] 硬體測試（實體機器人）
- [ ] 性能測試與優化
- [ ] 監控與告警整合

## 📞 聯絡資訊

如有問題請參閱 module.md 或聯絡專案維護者。
