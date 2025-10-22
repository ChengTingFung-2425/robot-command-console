# 🧩 Blockly 程式積木整合文件

## 📋 概述

本文件說明如何在 WebUI 進階指令建立器中使用 **Blockly 程式積木編輯器**，讓使用者透過拖放式積木介面來組合機器人動作，無需手動編寫 JSON 指令。

---

## 🎯 功能特色

### 1. 視覺化程式設計
- **拖放式操作**：從工具箱拖曳積木到工作區
- **即時預覽**：右側即時顯示產生的 JSON 程式碼
- **統計資訊**：自動計算積木數量與預估執行時間
- **錯誤防護**：無效的積木組合會自動阻止

### 2. 豐富的積木庫

#### 🤖 移動類積木（6 種）
- `前進` - 機器人向前移動（3.5 秒）
- `快速後退` - 機器人快速向後移動（4.5 秒）
- `左轉` - 機器人向左旋轉（4 秒）
- `右轉` - 機器人向右旋轉（4 秒）
- `快速左移` - 機器人快速向左移動（3 秒）
- `快速右移` - 機器人快速向右移動（3 秒）

#### 🧍 姿態類積木（6 種）
- `站立` - 機器人站立姿勢（1 秒）
- `鞠躬` - 機器人鞠躬（4 秒）
- `蹲下` - 機器人蹲下（1 秒）
- `從前方起身` - 從前方姿勢起身（5 秒）
- `從後方起身` - 從後方姿勢起身（5 秒）
- `揮手` - 機器人揮手（3.5 秒）

#### 🥋 戰鬥類積木（8 種）
- `左踢` - 左腳踢擊（2 秒）
- `右踢` - 右腳踢擊（2 秒）
- `功夫` - 功夫動作（2 秒）
- `詠春` - 詠春動作（2 秒）
- `左上勾拳` - 左手上勾拳（2 秒）
- `右上勾拳` - 右手上勾拳（2 秒）
- `快速左拳` - 快速左直拳（4 秒）
- `快速右拳` - 快速右直拳（4 秒）

#### 💃 舞蹈類積木（9 種）
- `跳舞` - 下拉選單選擇舞蹈二~舞蹈十（52-85 秒）

#### 💪 運動類積木（7 種）
- `伏地挺身` - 執行伏地挺身（9 秒）
- `仰臥起坐` - 執行仰臥起坐（12 秒）
- `胸部運動` - 胸部肌肉訓練（9 秒）
- `舉重` - 舉重動作（9 秒）
- `深蹲起立` - 深蹲後起立（6 秒）
- `扭轉` - 身體扭轉（4 秒）
- `踏步` - 原地踏步（3 秒）

#### 🔁 控制類積木（3 種）
- `重複 N 次` - 重複執行內部積木（可設定 1-10 次）
- `等待 N 毫秒` - 暫停指定時間（100-10000 毫秒）
- `停止` - 停止所有動作

---

## 🚀 使用方式

### 基本操作流程

1. **開啟建立頁面**
   - 訪問 `/advanced_commands/create`
   - 系統自動載入 Blockly 編輯器

2. **組合積木**
   ```
   步驟 1：點擊左側工具箱的類別（例如：移動 🤖）
   步驟 2：拖曳所需積木到中間的工作區
   步驟 3：積木會自動連接（上下連接）
   步驟 4：右側 JSON 預覽即時更新
   ```

3. **填寫指令資訊**
   - **指令名稱**：例如「巡邏路線 A」
   - **分類**：例如「巡邏」
   - **指令描述**：詳細說明指令用途

4. **查看統計資訊**
   - **積木數量**：自動統計已放置的積木
   - **預估時間**：根據每個動作的執行時間計算總時長

5. **提交指令**
   - 點擊「提交進階指令」按鈕
   - 系統自動驗證 JSON 格式與指令有效性
   - 提交後進入審核流程

---

## 📝 實作範例

### 範例 1：簡單巡邏路線

**目標**：機器人前進 → 左轉 → 前進 → 右轉 → 返回

**積木組合**：
```
[前進]
↓
[左轉]
↓
[前進]
↓
[右轉]
↓
[前進]
```

**產生的 JSON**：
```json
[
  {"command": "go_forward"},
  {"command": "turn_left"},
  {"command": "go_forward"},
  {"command": "turn_right"},
  {"command": "go_forward"}
]
```

**預估時間**：約 19 秒

---

### 範例 2：戰鬥組合技

**目標**：功夫 → 左上勾拳 → 右踢 → 詠春

**積木組合**：
```
[功夫]
↓
[左上勾拳]
↓
[右踢]
↓
[詠春]
```

**產生的 JSON**：
```json
[
  {"command": "kung_fu"},
  {"command": "left_uppercut"},
  {"command": "right_kick"},
  {"command": "wing_chun"}
]
```

**預估時間**：約 8 秒

---

### 範例 3：使用重複積木

**目標**：重複 3 次「前進 → 鞠躬」

**積木組合**：
```
[重複 3 次]
  ├─ [前進]
  └─ [鞠躬]
```

**產生的 JSON**：
```json
[
  {"command": "go_forward"},
  {"command": "bow"},
  {"command": "go_forward"},
  {"command": "bow"},
  {"command": "go_forward"},
  {"command": "bow"}
]
```

**預估時間**：約 22.5 秒

---

### 範例 4：加入等待時間

**目標**：站立 → 等待 2 秒 → 揮手 → 等待 1 秒 → 鞠躬

**積木組合**：
```
[站立]
↓
[等待 2000 毫秒]
↓
[揮手]
↓
[等待 1000 毫秒]
↓
[鞠躬]
```

**產生的 JSON**：
```json
[
  {"command": "stand"},
  {"command": "wait", "duration_ms": 2000},
  {"command": "wave"},
  {"command": "wait", "duration_ms": 1000},
  {"command": "bow"}
]
```

**預估時間**：約 11.5 秒

---

## 🛠️ 進階功能

### 1. 匯出積木工作區

點擊「💾 匯出積木」按鈕：
- 將當前工作區儲存為 `.xml` 檔案
- 可備份複雜的積木組合
- 方便分享給其他使用者

### 2. 匯入積木工作區

點擊「📂 匯入積木」按鈕：
- 選擇先前匯出的 `.xml` 檔案
- 自動重建積木組合
- 支援版本升級（向下相容）

### 3. 清空工作區

點擊「🗑️ 清空」按鈕：
- 刪除所有積木
- 二次確認防止誤操作
- 無法復原（建議先匯出備份）

---

## 🔍 技術實作細節

### 前端架構

```
create_advanced_command.html.j2
├── Blockly CDN 載入
├── robot_blocks.js（自定義積木定義）
├── blockly_workspace.css（樣式美化）
└── JavaScript 控制邏輯
    ├── 初始化工作區
    ├── 監聽積木變更
    ├── 產生 JSON 程式碼
    ├── 計算執行時間
    ├── 匯出/匯入功能
    └── 表單提交處理
```

### 積木定義結構

每個積木包含：
1. **視覺定義**（`Blockly.Blocks`）
   - 積木外觀（顏色、圖示、文字）
   - 連接點（上/下/內部）
   - 輸入欄位（下拉、數字等）

2. **程式碼產生器**（`Blockly.JavaScript`）
   - 將積木轉換為 JSON 物件
   - 處理特殊參數（如 wait 的 duration_ms）
   - 支援巢狀結構（如 loop 內部積木）

### 工具箱結構

```javascript
ROBOT_TOOLBOX = {
  "kind": "categoryToolbox",
  "contents": [
    { "name": "移動 🤖", "colour": 210, "contents": [...] },
    { "name": "姿態 🧍", "colour": 120, "contents": [...] },
    { "name": "戰鬥 🥋", "colour": 0, "contents": [...] },
    { "name": "舞蹈 💃", "colour": 290, "contents": [...] },
    { "name": "運動 💪", "colour": 160, "contents": [...] },
    { "name": "控制 🔁", "colour": 65, "contents": [...] }
  ]
}
```

---

## ✅ 驗證機制

### 前端驗證
- **即時語法檢查**：積木組合錯誤時無法連接
- **JSON 格式驗證**：產生的 JSON 必須可解析
- **空工作區檢查**：至少需要 1 個積木

### 後端驗證（forms.py）
```python
def validate_base_commands(self, field):
    # 1. JSON 格式驗證
    commands = json.loads(field.data)
    
    # 2. 陣列格式檢查
    if not isinstance(commands, list): raise ValidationError
    
    # 3. 至少一個指令
    if len(commands) == 0: raise ValidationError
    
    # 4. 每個指令必須有 command 欄位
    # 5. command 必須在有效動作清單中
    # 6. wait 指令必須有 duration_ms 參數
```

---

## 🎨 視覺設計

### 顏色編碼
- 🔵 **藍色（210）**：移動類
- 🟢 **綠色（120）**：姿態類
- 🔴 **紅色（0）**：戰鬥類
- 🟣 **紫色（290）**：舞蹈類
- 🔵 **青色（160）**：運動類
- 🟡 **黃色（65）**：控制類

### 圖示說明
每個積木前綴 emoji 圖示，提升可讀性：
- 🤖 移動
- 🧍 姿態
- 🥋 戰鬥
- 💃 舞蹈
- 💪 運動
- 🔁 控制

---

## 📊 與現有系統整合

### 資料流程
```
使用者操作積木
    ↓
JavaScript 產生 JSON
    ↓
填入隱藏的 base_commands 欄位
    ↓
Flask 表單驗證（forms.py）
    ↓
儲存到 AdvancedCommand 模型
    ↓
進入審核流程
    ↓
批准後可在指令分享區使用
```

### 資料庫欄位

```python
class AdvancedCommand(db.Model):
    name = db.Column(db.String(128))           # 指令名稱
    description = db.Column(db.Text)           # 指令描述
    category = db.Column(db.String(64))        # 分類
    base_commands = db.Column(db.Text)         # JSON 指令序列
    status = db.Column(db.String(32))          # pending/approved/rejected
    author_id = db.Column(db.Integer)          # 作者 ID
    created_at = db.Column(db.DateTime)        # 建立時間
```

---

## 🐛 故障排除

### 問題 1：積木無法載入
**症狀**：頁面顯示空白或「載入中...」
**原因**：Blockly CDN 載入失敗或網路問題
**解決**：
```bash
# 檢查瀏覽器開發者工具的 Console
# 確認 Blockly 腳本載入成功
# 必要時改用本地 Blockly 庫
```

### 問題 2：JSON 格式錯誤
**症狀**：提交時顯示「JSON 格式錯誤」
**原因**：積木產生的 JSON 語法有誤
**解決**：
```javascript
// 檢查 robot_blocks.js 的程式碼產生器
// 確保每個積木都返回正確格式
// 範例：{"command": "go_forward"},
```

### 問題 3：預估時間不準確
**症狀**：顯示的執行時間與實際不符
**原因**：`actionTimes` 對應表與 Robot-Console/tools.py 不一致
**解決**：
```javascript
// 更新 create_advanced_command.html.j2 中的 actionTimes 字典
// 確保與 Robot-Console/tools.py 的 ACTIONS 同步
```

---

## 🔒 安全考量

### 1. XSS 防護
- Blockly 產生的程式碼不直接執行
- JSON 經過伺服器端驗證
- 使用 Jinja2 自動跳脫輸出

### 2. CSRF 防護
- Flask-WTF 自動產生 CSRF Token
- 表單提交需包含 `{{ form.hidden_tag() }}`

### 3. 指令白名單
- 後端嚴格驗證指令名稱
- 僅允許預定義的 37 種動作
- 拒絕未知或惡意指令

---

## 📈 未來擴展

### 計畫中的功能
- [ ] 條件分支積木（if-else）
- [ ] 變數與參數傳遞
- [ ] 子程式積木（自定義函數）
- [ ] 從 JSON 反向載入積木
- [ ] 積木動畫預覽（3D 模擬器）
- [ ] 多語言支援（英文/中文切換）
- [ ] 積木市集（分享與下載社群積木）

---

## 📚 參考資源

- **Blockly 官方文件**：https://developers.google.com/blockly
- **Robot-Console 動作定義**：`/Robot-Console/tools.py`
- **MCP 指令契約**：`/docs/contract/command_request.schema.json`
- **WebUI 模組設計**：`/WebUI/Module.md`

---

## ✅ 驗證清單

- [x] 所有 37 種機器人動作都有對應積木
- [x] 積木產生的 JSON 格式正確
- [x] 前後端驗證邏輯一致
- [x] 預估時間計算準確
- [x] 匯出/匯入功能正常
- [x] 響應式設計（支援手機/平板）
- [x] 錯誤訊息清晰易懂
- [x] 與現有審核流程整合
- [x] 樣式與整體 UI 一致
- [x] 無障礙設計（鍵盤操作）

---

**文件版本**：1.0  
**最後更新**：2025-10-22  
**維護者**：GitHub Copilot

---

## 修正紀錄（2025-10-22）

小幅更新內容：

- 新增 `robot_start` 起始積木，作為工作區的根節點，預設放置並設為不可刪除/不可移動。
- 右側即時 JSON 視覺區改為「待驗證 (To verify)」面板，提供前端驗證按鈕，避免直接暴露 JSON。
- 加入 `ensureStarterExists()`，在初始化、匯入、或變更時自動補回被移除的起始積木。

請參考 `WebUI/BLOCKLY_VERIFICATION.md` 的「修正紀錄」章節，有更完整的測試步驟與說明。
