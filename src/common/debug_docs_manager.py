"""
除錯文件管理器
只有在啟用秘密除錯模式時才會顯示/生成除錯文件
"""

import os
from pathlib import Path


class DebugDocsManager:
    def __init__(self, project_root=None):
        self.project_root = project_root or self._detect_project_root()
        self.docs_dir = self.project_root / "docs" / "developer"
        self.debug_guide_path = self.docs_dir / "DEBUG_MODE.md"
    
    def _detect_project_root(self):
        current = Path(__file__).parent
        for _ in range(5):
            if (current / "docs").exists():
                return current
            current = current.parent
        return Path(__file__).parent.parent.parent
    
    def is_debug_mode_active(self):
        """檢查秘密除錯模式是否啟用（必須三個條件同時滿足）"""
        has_env_var = os.environ.get('__ROBOT_INTERNAL_DEBUG__') == '1'
        has_debug_file = (self.project_root / '.robot_debug').exists()
        has_debug_port = os.environ.get('DEBUG_PORT') == '54321'
        return has_env_var and has_debug_file and has_debug_port
    
    def generate_debug_docs(self):
        if not self.is_debug_mode_active():
            return False
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        with open(self.debug_guide_path, 'w', encoding='utf-8') as f:
            f.write("""# 秘密除錯模式指南

> **此文件只在啟用秘密除錯模式後才可見**

## 啟用方式

⚠️ **重要**: 必須同時滿足以下三個條件才能啟用除錯模式：

### 1. 設定環境變數
```bash
export __ROBOT_INTERNAL_DEBUG__=1
```

### 2. 建立隱藏檔案標記
```bash
touch .robot_debug  # 在專案根目錄
```

### 3. 設定特殊埠號
```bash
export DEBUG_PORT=54321
```

### 完整啟用範例

```bash
# 必須同時執行以下三個步驟
export __ROBOT_INTERNAL_DEBUG__=1
touch .robot_debug
export DEBUG_PORT=54321

# 然後啟動應用程式
python3 qtwebview-app/main.py
# 或
npm start
```

## 除錯模式功能

啟用後可以看到：
- 詳細的服務啟動日誌
- 健康檢查結果
- 效能指標
- 錯誤堆疊追蹤
- Token 資訊（部分遮蔽）

## 服務資訊

- Flask API: http://127.0.0.1:5000
- MCP Service: http://127.0.0.1:8000

---

**此文件由除錯模式自動生成**
""")
        gitignore = self.docs_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*.md\n")
        return True


def ensure_debug_docs():
    manager = DebugDocsManager()
    if manager.is_debug_mode_active():
        manager.generate_debug_docs()
        return True
    return False
