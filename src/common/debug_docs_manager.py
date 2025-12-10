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
        if os.environ.get('__ROBOT_INTERNAL_DEBUG__') == '1':
            return True
        if (self.project_root / '.robot_debug').exists():
            return True
        if os.environ.get('DEBUG_PORT') == '54321':
            return True
        return False
    
    def generate_debug_docs(self):
        if not self.is_debug_mode_active():
            return False
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        with open(self.debug_guide_path, 'w', encoding='utf-8') as f:
            f.write("""# Secret Debug Mode Guide

> **Only visible when debug mode is enabled**

## Enable Methods
1. `export __ROBOT_INTERNAL_DEBUG__=1`
2. `touch .robot_debug`
3. `export DEBUG_PORT=54321`

## Features
- Detailed service logs
- Health check results
- Performance metrics
- Error stack traces

## Services
- Flask API: http://127.0.0.1:5000
- MCP Service: http://127.0.0.1:8000
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
