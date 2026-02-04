# Blockly JSON Toggle Feature

## Overview
Added functionality to hide JSON output by default but allow users to view it by clicking a toggle button in the Blockly interface.

## Implementation Date
2026-02-04

## Changes Made

### File: `Edge/WebUI/app/templates/create_advanced_command.html.j2`

#### 1. Updated `updateCodePreview()` Function
- Added JSON preview content update when workspace changes
- Pretty-prints JSON with indentation (2 spaces)
- Updates the `json-preview-content` element if visible

#### 2. Added `toggleJsonPanel()` Function
- Toggles visibility of JSON preview panel
- Updates button text: "🔼 顯示 JSON" ↔ "🔽 隱藏 JSON"
- Persists state in localStorage
- Auto-updates JSON content when panel is shown

#### 3. Added `copyJsonToClipboard()` Function
- Copies JSON content to clipboard using modern Clipboard API
- Shows success feedback (✅ 已複製！) for 2 seconds
- Graceful error handling

#### 4. Added JSON Preview Panel UI
- Card-based panel with header and content area
- Initially hidden by default (`display: none`)
- Pretty-printed JSON in `<pre>` element with scrolling
- Copy button in panel header
- Max height: 400px with scroll for long JSON

#### 5. Added Toggle Button
- Placed below the tips section
- Full-width button with info styling
- Clear icon and text: "🔼 顯示 JSON"

#### 6. State Persistence
- Saves/restores panel visibility in localStorage
- Key: `jsonPanelVisible` (1 = visible, 0 = hidden)
- Restored on page load

## User Experience

### Default State
- JSON preview panel is **hidden** by default
- Only Blockly workspace and verification panel are visible
- Clean, uncluttered interface

### Showing JSON
1. User clicks "🔼 顯示 JSON" button
2. JSON preview panel slides into view below workspace
3. Button text changes to "🔽 隱藏 JSON"
4. JSON content is auto-updated and pretty-printed
5. State saved in localStorage

### Hiding JSON
1. User clicks "🔽 隱藏 JSON" button
2. JSON preview panel is hidden
3. Button text changes back to "🔼 顯示 JSON"
4. State saved in localStorage

### Copying JSON
1. User clicks "📋 複製" button in JSON panel header
2. JSON content copied to clipboard
3. Button shows "✅ 已複製！" feedback for 2 seconds
4. Button returns to normal state

## Technical Details

### HTML Structure
```html
<div class="card mt-3" id="json-preview-panel" style="display: none;">
  <div class="card-header bg-secondary text-white">
    <h6>📄 JSON 預覽</h6>
    <button id="copy-json-btn" onclick="copyJsonToClipboard()">📋 複製</button>
  </div>
  <div class="card-body">
    <pre id="json-preview-content">[]</pre>
  </div>
</div>
```

### JavaScript Functions
```javascript
// Toggle panel visibility
toggleJsonPanel() {
  - Show/hide panel
  - Update button text
  - Save state to localStorage
  - Update JSON content if showing
}

// Copy to clipboard
copyJsonToClipboard() {
  - Get JSON text from preview
  - Use navigator.clipboard.writeText()
  - Show success feedback
  - Handle errors gracefully
}

// Update JSON display
updateCodePreview() {
  - Generate JSON from workspace
  - Pretty-print with JSON.stringify(parsed, null, 2)
  - Update preview content
}
```

### LocalStorage Keys
- `jsonPanelVisible`: "1" (visible) or "0" (hidden)

## Benefits

1. **Clean Interface**: JSON hidden by default reduces visual clutter
2. **On-Demand Access**: Users can view JSON when needed
3. **Easy Copying**: One-click copy to clipboard
4. **State Persistence**: Remembers user preference
5. **Auto-Update**: JSON updates automatically when blocks change
6. **Pretty Formatting**: Indented JSON for better readability

## Testing

### Manual Tests
1. ✅ Page loads with JSON panel hidden
2. ✅ Click toggle button shows JSON panel
3. ✅ JSON content displays correctly formatted
4. ✅ Click toggle button again hides JSON panel
5. ✅ State persists across page reloads
6. ✅ Copy button works and shows feedback
7. ✅ JSON updates when blocks change
8. ✅ Works with verify panel toggle

### Browser Compatibility
- Modern browsers with Clipboard API support
- localStorage support required
- Graceful fallback for older browsers

## Future Enhancements (Optional)

1. Add JSON syntax highlighting
2. Add JSON validation indicators
3. Add download JSON file option
4. Add JSON import from clipboard
5. Add JSON diff view for changes

## Related Files

- Template: `Edge/WebUI/app/templates/create_advanced_command.html.j2`
- JavaScript: Inline in template (could be extracted)
- CSS: Uses existing Bootstrap classes

## Notes

- Feature is completely optional and doesn't affect core functionality
- JSON is always generated and stored in hidden field for form submission
- Panel visibility state is per-browser (localStorage)
- No server-side changes required
- Backward compatible with existing functionality
