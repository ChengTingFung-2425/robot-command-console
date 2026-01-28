# WIP 內容替換追蹤清單

> 目標：將所有 WIP/TODO/FIXME 標記替換為真實實作
> 創建時間：2026-01-21
> 更新時間：2026-01-21 10:20
> 狀態：Phase 1 完成

## 優先級分類

### P0 - 核心功能（立即處理）✅ 完成

#### 1. Qt WebView App - UI Widgets (qtwebview-app/main_window.py) ✅
- [x] Line 355: Dashboard - 從 API 載入實際機器人列表 → 使用 BackendAPIClient.list_robots()
- [x] Line 406: RobotControl - 實際發送指令到後端 → 使用 BackendAPIClient.send_robot_command()
- [x] Line 431: RobotControl - 執行快速指令 → 使用 BackendAPIClient.send_robot_command()
- [x] Line 526: CommandHistory - 從 API 載入實際歷史 → 使用 BackendAPIClient.get_command_history()
- [x] Line 834: FirmwareUpdate - 真實解密邏輯 → 使用 SecureConfigHandler.decrypt_config()
- [x] Line 895: FirmwareUpdate - 真實 WiFi 連接邏輯 → 使用 WiFiManager.connect()
- [x] Line 965: FirmwareUpdate - 真實固件上傳邏輯 → 使用 SSHClient + SCP
- [x] Line 1021: FirmwareUpdate - 安全刪除加密檔案 → 使用 secure_delete_file()

**狀態**: ✅ 完成 (8/8 items)
**依賴**: backend_client.py, firmware_utils.py (已完成)
**Commit**: 待提交

#### 2. Qt WebView App - API Routes (qtwebview-app/) ⏳
- [ ] routes_api_tiny.py:24 - JWT validation
- [ ] routes_api_tiny.py:41-42 - 實際 queue/database 狀態檢查
- [ ] routes_api_tiny.py:99 - 整合實際 queue service (消息發送)
- [ ] routes_api_tiny.py:141 - 整合實際 queue service (消息消費)
- [ ] routes_api_tiny.py:169 - 整合實際 queue service (通道創建)
- [ ] routes_firmware_tiny.py:22 - 實際 admin 檢查
- [ ] routes_firmware_tiny.py:45 - 從存儲獲取實際固件列表
- [ ] routes_firmware_tiny.py:82 - 實際文件上傳與驗證
- [ ] routes_firmware_tiny.py:138 - 獲取實際固件文件路徑
- [ ] routes_firmware_tiny.py:303 - 實際任務狀態追蹤
- [ ] routes_firmware_tiny.py:333 - 從存儲/緩存獲取機器人變數
- [ ] routes_firmware_tiny.py:354 - 存儲機器人變數

**狀態**: ⏳ 待處理 (0/12 items)
**依賴**: QueueService, PlatformStorage, AdminAuth
**下一步**: Phase 2

### P1 - 邊緣服務（次要）

#### 3. Robot Service - Action Consumer (src/robot_service/robot_action_consumer.py)
- [ ] Line 236: 實作結果回報機制
- [ ] Line 257: 實作錯誤回報機制
- [ ] Line 290: 實作實際的連接邏輯
- [ ] Line 318: 實作實際的指令發送

**狀態**: ⏳ 待處理 (0/4 items)
**依賴**: Robot-Console integration

#### 4. Robot Service - LLM Processor (src/robot_service/llm_command_processor.py)
- [ ] Line 371: 實作 Anthropic API 整合
- [ ] Line 391: 整合 LLMProviderManager
- [ ] Line 517: 整合語音辨識服務
- [ ] Line 532: 整合語音合成服務

**狀態**: ⏳ 待處理 (0/4 items)
**依賴**: LLMProviderManager (已有)

#### 5. Robot Service - Batch Executor (src/robot_service/batch/executor.py)
- [ ] Line 494: 實作真正的結果等待邏輯

**狀態**: ⏳ 待處理 (0/1 item)

#### 6. Robot Service - TUI (src/robot_service/tui/)
- [ ] app.py:523 - 與 OfflineQueueService 或 NetworkMonitor 整合
- [ ] app.py:545 - 與 LLMProviderManager 整合
- [ ] app.py:798 - 從共享狀態取得實際機器人清單
- [ ] command_sender.py:193 - 從 SharedStateManager 取得機器人列表

**狀態**: ⏳ 待處理 (0/4 items)
**依賴**: SharedStateManager, OfflineQueueService

#### 7. Robot Service - Electron UI (src/robot_service/electron/edge_ui.py)
- [ ] Line 57: 遷移到 SQLite 持久化存儲（Phase 3.3）
- [ ] Line 588: 遷移到持久化存儲（Phase 3.3）

**狀態**: ⏳ 待處理 (Phase 3.3)
**備註**: Phase 3.3 任務，低優先級

### P2 - MCP 服務（可延後）

#### 8. MCP - Robot Router (MCP/robot_router.py)
- [ ] Line 295: 實作 MQTT 指令下發
- [ ] Line 313: 實作 WebSocket 指令下發

**狀態**: ⏳ 待處理 (0/2 items)

#### 9. MCP - LLM Processor (MCP/llm_processor.py)
- [ ] Line 174: 實作實際的 HTTP/IPC 呼叫

**狀態**: ⏳ 待處理 (0/1 item)

### P3 - UI 增強（低優先級）

#### 10. Qt WebView App - Main (qtwebview-app/main.py)
- [ ] Line 34: 添加實際的啟動畫面圖片

**狀態**: ⏳ 待處理 (0/1 item)
**備註**: UI 美化，非關鍵功能

#### 11. Qt WebView App - MainWindow (qtwebview-app/main_window.py)
- [ ] Line 1149: 添加更多工具欄動作

**狀態**: ⏳ 待處理 (0/1 item)
**備註**: UI 增強，非關鍵功能

## 實作策略

### Phase 1: Core Widget Integration (P0-1) ✅ 完成
1. ✅ 完成 backend_client.py
2. ✅ 完成 firmware_utils.py
3. ✅ 替換 main_window.py 中的 TODO (8 items) - 已完成
4. ⏳ 替換 routes_api_tiny.py 中的 TODO (6 items) - 下一步
5. ⏳ 替換 routes_firmware_tiny.py 中的 TODO (6 items) - 下一步

### Phase 2: Edge Service Integration (P1)
1. Robot Action Consumer (4 items)
2. LLM Processor (4 items)
3. Batch Executor (1 item)
4. TUI Integration (4 items)

### Phase 3: MCP Integration (P2)
1. Robot Router (2 items)
2. LLM Processor (1 item)

### Phase 4: UI Polish (P3)
1. Splash screen
2. Additional toolbar actions

## 進度追蹤

- **總計**: ~47 items
- **已完成**: 10 items (backend_client + firmware_utils + main_window 8 items)
- **進行中**: 0 items
- **待處理**: 37 items
- **完成率**: 21% (Phase 1 P0-1: 100%)

## 變更摘要 (Phase 1)

### main_window.py 替換詳情

1. **DashboardWidget**: 已使用 BackendAPIClient，無需修改
2. **RobotControlWidget**:
   - 添加 `api_client` 屬性
   - `_load_robots()`: 使用 `api_client.list_robots()` 獲取真實機器人列表
   - `_send_command()`: 使用 `api_client.send_robot_command()` 發送指令
   - `_quick_command()`: 使用 `api_client.send_robot_command()` 執行快速指令

3. **CommandHistoryWidget**:
   - 添加 `api_client` 屬性
   - `_load_history()`: 使用 `api_client.get_command_history()` 獲取真實歷史

4. **FirmwareUpdateWidget**:
   - 添加 `config_handler`, `wifi_manager`, `ssh_client` 屬性
   - `_decrypt_config()`: 使用 `SecureConfigHandler.decrypt_config()` 真實解密
   - `_connect_wifi()`: 使用 `WiFiManager.connect()` 真實 WiFi 連接
   - `_upload_firmware()`: 使用 `SSHClient` + SCP 真實上傳，包含：
     * SSH 連接
     * Checksum 計算與驗證
     * 進度追蹤
     * 遠端指令執行
   - `_finish_upload()`: 使用 `secure_delete_file()` 安全刪除配置檔案

## 下一步行動

1. **立即**: 提交 Phase 1 變更 (main_window.py)
2. **次要**: 完成 routes_api_tiny.py 和 routes_firmware_tiny.py 的 TODO (Phase 2)
3. **延後**: 處理 Edge Service 和 MCP 的 TODO (Phase 3-4)

---

**備註**: 此文件用於追蹤 WIP 替換進度，完成後可刪除。
