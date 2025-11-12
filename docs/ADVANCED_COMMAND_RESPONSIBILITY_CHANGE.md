# 進階指令職責變更說明

## 概述

此文件說明進階指令解碼職責從 Robot-Console 轉移到 WebUI 的重大變更。

## 變更摘要

### 之前的架構

```
WebUI/前端
    ↓ 發送進階指令
Robot-Console (pubsub.py)
    ↓ 使用 AdvancedDecoder 解碼
    ↓ 展開為基礎動作列表
ActionExecutor
    ↓ 執行動作
機器人硬體
```

### 新的架構

```
WebUI/前端
    ↓ 展開進階指令為基礎動作列表
    ↓ 發送 {"actions": ["action1", "action2", ...]}
Robot-Console (pubsub.py)
    ↓ 直接接收動作列表
ActionExecutor
    ↓ 執行動作
機器人硬體
```

## 主要變更

### 1. pubsub.py 的變更

**新的處理優先順序**：

1. **優先**：處理 `actions` 陣列（新格式）
   ```json
   {"actions": ["go_forward", "turn_left", "stand"]}
   ```

2. **次要**：使用舊解碼器（如果啟用）
   - 需要在 `settings.yaml` 中設定 `enable_legacy_decoder: true`
   - 用於向後相容舊式進階指令格式

3. **最後**：處理 `toolName`（向後相容）
   ```json
   {"toolName": "bow"}
   ```

**程式碼變更**：

```python
# 之前：總是使用 decoder
self.decoder = AdvancedDecoder(mcp_base_url=mcp_base)
decoded = self.decoder.decode(payload)

# 現在：優先處理 actions 陣列，decoder 為可選
self.decoder = AdvancedDecoder(mcp_base_url=mcp_base) if settings.get("enable_legacy_decoder", False) else None

if "actions" in payload:
    # 直接使用預先解碼的動作列表
    self.executor.add_actions_to_queue(payload["actions"])
```

### 2. advanced_decoder.py 的變更

- 添加 **⚠️ DEPRECATED** 警告
- 保留僅用於向後相容
- 在初始化時記錄警告訊息

### 3. 文檔更新

#### Robot-Console/module.md
- 添加重要變更通知到文件開頭
- 更新第 2 節（檔案說明）標記 `advanced_decoder.py` 為已棄用
- 重寫第 13 節說明新的職責劃分

#### Robot-Console/README.md
- 添加變更通知和新功能

#### Robot-Console/MIGRATION_GUIDE.md（新建）
- 完整的遷移指南
- WebUI 實作範例
- 測試方法
- 故障排除

## 優點

### 1. 更簡單的後端邏輯
- Robot-Console 只需處理基礎動作列表
- 減少複雜度和潛在錯誤
- 更易於維護和測試

### 2. 更靈活的前端 UX
- WebUI 可以提供更好的使用者介面來建立命令序列
- 即時預覽和編輯進階指令
- 更好的錯誤提示和驗證

### 3. 更清晰的職責劃分
- WebUI：使用者互動、指令建立、展開
- Robot-Console：動作執行、硬體控制
- 各模組專注於自己的核心職責

### 4. 更好的擴充性
- 在 WebUI 中添加新的進階指令功能更容易
- 不需要修改 Robot-Console 的核心邏輯
- 可以支援更複雜的指令組合和條件邏輯

## 向後相容性

### 完全支援

以下格式繼續無縫支援：

1. **單一動作**：`{"toolName": "bow"}`
2. **新格式動作列表**：`{"actions": ["bow", "wave"]}`

### 需要設定啟用

舊式進階指令格式需要在 `settings.yaml` 中啟用：

```yaml
enable_legacy_decoder: true
mcp_base_url: http://your-mcp-server:5000  # 可選
```

然後可以繼續使用：

```json
{
  "type": "sequence",
  "steps": [
    {"action": "go_forward"},
    {"action": "turn_left"}
  ]
}
```

## 遷移步驟

### WebUI/前端開發者

1. **實作進階指令展開邏輯**
   - 在 WebUI 中解析進階指令定義
   - 展開為基礎動作序列
   - 驗證所有動作都是有效的

2. **更新發送格式**
   - 使用新格式：`{"actions": ["action1", "action2", ...]}`
   - 移除對舊式進階指令格式的依賴

3. **測試**
   - 測試各種進階指令組合
   - 驗證錯誤處理
   - 確保動作按順序執行

### Robot-Console 維護者

1. **無需變更**
   - Robot-Console 已更新為優先處理新格式
   - 向後相容性已內建

2. **可選：停用舊解碼器**
   - 當所有客戶端都已遷移後
   - 移除 `settings.yaml` 中的 `enable_legacy_decoder` 設定
   - 未來版本可能完全移除 `advanced_decoder.py`

## 測試

已新增完整的測試套件 `Test/test_pubsub_actions_array.py`：

- ✅ 測試 actions 陣列處理
- ✅ 測試向後相容性（toolName）
- ✅ 測試錯誤處理（無效格式）
- ✅ 測試優先順序（actions 優先於其他格式）
- ✅ 測試空陣列處理
- ✅ 測試舊解碼器可選啟用
- ✅ 測試舊式 sequence 格式

所有 8 個測試通過 ✅

## 範例

### WebUI 發送新格式

```python
# 在 WebUI 中展開進階指令
def send_advanced_command_to_robot(robot_id, advanced_command_id):
    # 1. 載入進階指令定義
    cmd = AdvancedCommand.query.get(advanced_command_id)
    
    # 2. 展開為基礎動作列表
    actions = []
    for step in cmd.base_commands:
        if 'action' in step:
            actions.append(step['action'])
    
    # 3. 驗證動作
    for action in actions:
        if action not in VALID_ACTIONS:
            raise ValueError(f"Invalid action: {action}")
    
    # 4. 發送新格式
    payload = {"actions": actions}
    mqtt_client.publish(f"{robot_id}/topic", json.dumps(payload))
```

### Robot-Console 接收和處理

```python
# 在 pubsub.py 中自動處理
def on_publish_received(self, publish_packet_data):
    payload = json.loads(publish_packet.payload)
    
    # 自動識別新格式並處理
    if "actions" in payload:
        logging.info("Processing pre-decoded actions list: %s", payload["actions"])
        self.executor.add_actions_to_queue(payload["actions"])
    # ... 向後相容邏輯
```

## 常見問題

### Q: 舊的進階指令還能用嗎？

A: 可以，但需要在 `settings.yaml` 中設定 `enable_legacy_decoder: true`。建議遷移到新格式以獲得更好的性能和維護性。

### Q: 如何測試新格式？

A: 參考 `MIGRATION_GUIDE.md` 中的測試方法，或使用 MQTT 測試工具發送格式化的負載。

### Q: WebUI 還沒準備好，可以繼續使用舊方式嗎？

A: 可以。啟用 `enable_legacy_decoder` 後，所有舊格式都繼續工作。

### Q: 新格式有什麼限制？

A: actions 陣列必須是字串列表，每個字串必須是有效的基礎動作名稱。

**效能考量**：
- 建議單次發送的 actions 陣列大小不超過 100 個動作
- 超過此限制的陣列仍會被處理，但可能導致效能問題
- 對於大量動作序列，建議分批發送以獲得最佳效能和錯誤處理

### Q: 如何知道動作列表是否有效？

A: 參考 `Robot-Console/action_executor.py` 中的 `actions` 字典，或查看 `tools.py` 中的 `TOOL_LIST`。

## 參考資料

- [Robot-Console/module.md](../Robot-Console/module.md) - 完整模組設計說明
- [Robot-Console/MIGRATION_GUIDE.md](../Robot-Console/MIGRATION_GUIDE.md) - 詳細遷移指南
- [Test/test_pubsub_actions_array.py](../Test/test_pubsub_actions_array.py) - 測試範例

## 變更歷史

- **2025-11-12**: 初始實作，將進階指令解碼職責轉移到 WebUI
