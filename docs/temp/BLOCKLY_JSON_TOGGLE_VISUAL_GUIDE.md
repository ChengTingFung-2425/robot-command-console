# Blockly JSON Toggle - Visual Guide

## Interface Layout

### Default State (JSON Hidden)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 🧩 建立進階指令（程式積木編輯器）                                       │
│ 使用拖放式積木來組合機器人動作序列，無需手動編寫 JSON。                 │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────┬──────────────────────┬───────────────────────────────────┐
│              │                      │                                   │
│  📝 指令資訊  │  待驗證 (To verify)  │      🧩 積木工作區                │
│              │                      │                                   │
│  名稱: ____  │  ┌────────────────┐  │  ┌─────────────────────────────┐ │
│  類別: ____  │  │ 驗證指令按鈕    │  │  │  [Blockly Workspace]       │ │
│  描述: ____  │  │                │  │  │                             │ │
│  版本: ____  │  │ 驗證結果：     │  │  │  Drag blocks here...        │ │
│              │  │ 尚未驗證        │  │  │                             │ │
│  📊 統計資訊  │  └────────────────┘  │  │                             │ │
│  積木數量: 0  │                      │  │                             │ │
│  預估時間: 0s │                      │  │                             │ │
│              │                      │  └─────────────────────────────┘ │
│  [儲存指令]   │                      │                                   │
│  [🗑️ 清空]   │                      │  💡 提示：                        │
│  [💾 匯出]   │                      │  • 從左側工具箱拖曳積木            │
│  [📂 匯入]   │                      │  • 積木可自由組合、排序與刪除      │
│              │                      │  • 使用「重複」積木可循環執行動作  │
│  時間單位:    │                      │  • 使用「等待」積木可在動作間暫停  │
│  (•) 秒      │                      │  • 點擊下方按鈕可查看產生的 JSON   │
│  ( ) 毫秒    │                      │                                   │
│              │                      │  ┌───────────────────────────┐  │
└──────────────┴──────────────────────│  │  🔼 顯示 JSON              │  │
                                      │  └───────────────────────────┘  │
                                      └───────────────────────────────────┘
```

### JSON Visible State (After Clicking Toggle)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 🧩 建立進階指令（程式積木編輯器）                                       │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────┬──────────────────────┬───────────────────────────────────┐
│              │                      │                                   │
│  📝 指令資訊  │  待驗證 (To verify)  │      🧩 積木工作區                │
│              │                      │                                   │
│              │                      │  [Blockly Workspace with blocks]  │
│              │                      │                                   │
│              │                      │  ┌───────────────────────────────┐│
│              │                      │  │ 📄 JSON 預覽        [📋 複製]  ││
│              │                      │  ├───────────────────────────────┤│
│              │                      │  │ [                             ││
│              │                      │  │   {                           ││
│              │                      │  │     "command": "go_forward",  ││
│              │                      │  │     "duration_s": 2.0         ││
│              │                      │  │   },                          ││
│              │                      │  │   {                           ││
│              │                      │  │     "command": "turn_right",  ││
│              │                      │  │     "duration_s": 1.5         ││
│              │                      │  │   }                           ││
│              │                      │  │ ]                             ││
│              │                      │  └───────────────────────────────┘│
│              │                      │                                   │
│              │                      │  💡 提示：[...]                   │
│              │                      │                                   │
│              │                      │  ┌───────────────────────────┐  │
└──────────────┴──────────────────────│  │  🔽 隱藏 JSON              │  │
                                      │  └───────────────────────────┘  │
                                      └───────────────────────────────────┘
```

## Button States

### Toggle Button

**Hidden State:**
```
┌────────────────────────┐
│  🔼 顯示 JSON           │  ← Click to show
└────────────────────────┘
```

**Visible State:**
```
┌────────────────────────┐
│  🔽 隱藏 JSON           │  ← Click to hide
└────────────────────────┘
```

### Copy Button

**Normal State:**
```
┌──────────────────────────────────────┐
│ 📄 JSON 預覽              [📋 複製]  │
└──────────────────────────────────────┘
```

**After Click (Success Feedback):**
```
┌──────────────────────────────────────┐
│ 📄 JSON 預覽          [✅ 已複製！]  │ ← Green, 2 seconds
└──────────────────────────────────────┘
```

## Interaction Flow

### Showing JSON

```
User Action              System Response
───────────              ───────────────
1. Click "🔼 顯示 JSON"
                        → Panel slides down (display: block)
                        → Generate & format JSON
                        → Update panel content
                        → Button text → "🔽 隱藏 JSON"
                        → Save state to localStorage
```

### Hiding JSON

```
User Action              System Response
───────────              ───────────────
1. Click "🔽 隱藏 JSON"
                        → Panel disappears (display: none)
                        → Button text → "🔼 顯示 JSON"
                        → Save state to localStorage
```

### Copying JSON

```
User Action              System Response
───────────              ───────────────
1. Click "📋 複製"
                        → Get JSON text
                        → Copy to clipboard
                        → Button text → "✅ 已複製！"
                        → Button color → green
                        → Wait 2 seconds
                        → Button text → "📋 複製"
                        → Button color → normal
```

### Auto-Update on Block Change

```
User Action              System Response
───────────              ───────────────
1. Drag block to workspace
                        → Detect workspace change
                        → Generate new JSON
                        → If panel visible:
                          → Update preview content
                          → Pretty-print JSON
                        → Update hidden field
                        → Update statistics
```

## JSON Display Format

### Pretty-Printed Example

```json
[
  {
    "command": "go_forward",
    "duration_s": 2.0
  },
  {
    "command": "turn_right",
    "duration_s": 1.5
  },
  {
    "command": "stand"
  },
  {
    "command": "wait",
    "duration_ms": 1000
  },
  {
    "command": "wave"
  }
]
```

### Scrolling for Long JSON

```
┌──────────────────────────────┐
│ 📄 JSON 預覽     [📋 複製]   │
├──────────────────────────────┤
│ [                            │ ↑
│   { ... },                   │ │ Scrollable
│   { ... },                   │ │ Max height:
│   { ... },                   │ │ 400px
│   { ... },                   │ │
│   { ... },                   │ │
│   ...                        │ ↓
└──────────────────────────────┘
```

## Responsive Behavior

### Desktop View
- Full 3-column layout
- JSON panel appears below Blockly workspace
- Toggle button at bottom of middle column

### Tablet View
- 2-column layout (info + workspace)
- Verify panel may collapse
- JSON panel behavior unchanged

### Mobile View
- Single column stack
- JSON panel full width
- Toggle button remains accessible

## Color Scheme

### Panel Header
- Background: `bg-secondary` (Bootstrap gray)
- Text: White
- Copy button: Outlined light

### Panel Body
- Background: `#f8f9fa` (light gray)
- Text: Dark gray
- Border: Rounded (4px)

### Toggle Button
- Normal: `btn-outline-info` (blue outline)
- Hover: Filled blue
- Active: Pressed effect

### Copy Button Success
- Temporary: `btn-success` (green)
- Duration: 2 seconds
- Animation: Smooth transition

## Accessibility

### Keyboard Navigation
- Toggle button: Tab + Enter/Space
- Copy button: Tab + Enter/Space
- Panel content: Tab + Arrow keys for scrolling

### Screen Readers
- Button labels: Clear text descriptions
- Panel content: Structured JSON in `<pre>`
- Success feedback: Announced to screen readers

### High Contrast
- Uses Bootstrap standard colors
- Clear visual separation
- Good text contrast ratios

## Performance

### Optimization
- JSON generated only when workspace changes
- Panel content updated only when visible
- LocalStorage access minimized
- No unnecessary re-renders

### Memory Usage
- Minimal DOM elements
- No memory leaks
- Efficient event handlers
- Clean garbage collection

## Browser Support

✅ Chrome 63+ (Clipboard API)
✅ Firefox 53+ (Clipboard API)
✅ Safari 13.1+ (Clipboard API)
✅ Edge 79+ (Clipboard API)
⚠️ Older browsers: Graceful fallback (alert for copy errors)

## Testing Checklist

### Functional Tests
- [ ] Page loads with JSON hidden
- [ ] Click toggle shows JSON panel
- [ ] JSON displays correctly formatted
- [ ] Click toggle hides JSON panel
- [ ] Copy button copies to clipboard
- [ ] Success feedback appears for 2s
- [ ] State persists on page reload
- [ ] JSON updates when blocks change

### Visual Tests
- [ ] Panel aligns properly
- [ ] Buttons styled correctly
- [ ] Text readable and clear
- [ ] Scrolling works for long JSON
- [ ] Success animation smooth

### Edge Cases
- [ ] Empty workspace (shows [])
- [ ] Invalid JSON (shows error)
- [ ] Very long JSON (scrolls)
- [ ] Rapid toggling (no lag)
- [ ] Concurrent copy clicks (handled)

## Tips for Users

1. **Default Hidden**: Don't worry if you don't see JSON - it's working in the background
2. **Quick Toggle**: Use the button to quickly check your JSON output
3. **Copy Easily**: One click to copy entire JSON to clipboard
4. **Auto-Update**: JSON updates automatically as you work
5. **Persistent**: Your preference is remembered between sessions

Perfect for developers who want to see the code behind their blocks! 🎉
