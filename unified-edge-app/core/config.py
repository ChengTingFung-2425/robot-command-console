"""
Unified Configuration
統一配置管理
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class UnifiedConfig:
    """統一配置類別"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        載入配置
        
        Args:
            config_path: 配置檔案路徑（YAML 格式）
        """
        self.version = "1.0.0"
        self.project_root = self._detect_project_root()
        
        # 預設配置
        self._config = self._default_config()
        
        # 從檔案載入（如果存在）
        if config_path and config_path.exists():
            self._load_from_file(config_path)
        
        # 環境變數覆寫
        self._load_from_env()
    
    def _detect_project_root(self) -> Path:
        """偵測專案根目錄"""
        current = Path(__file__).parent
        for _ in range(5):
            if (current / "MCP").exists() and (current / "WebUI").exists():
                return current
            current = current.parent
        return Path(__file__).parent.parent.parent
    
    def _default_config(self) -> Dict[str, Any]:
        """預設配置"""
        return {
            "app": {
                "name": "Robot Command Console - Edge",
                "version": self.version,
                "mode": "edge"
            },
            "mcp": {
                "host": "127.0.0.1",
                "port": 8000,
                "enable_llm": True,
                "llm_provider": "ollama",
                "enable_plugins": True
            },
            "robot_console": {
                "protocol": "queue",  # queue, mqtt, http
                "enable_safety": True
            },
            "web_interface": {
                "host": "127.0.0.1",
                "port": 5000,
                "auth_mode": "local",
                "enable_blockly": True,
                "database": "sqlite:///unified_edge_app.db"
            },
            "logging": {
                "level": "INFO",
                "format": "json",
                "output": "console"
            }
        }
    
    def _load_from_file(self, path: Path):
        """從 YAML 檔案載入配置"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f)
                self._merge_config(file_config)
        except Exception as e:
            print(f"Warning: Failed to load config from {path}: {e}")
    
    def _load_from_env(self):
        """從環境變數載入配置"""
        # MCP 配置
        if os.environ.get('MCP_HOST'):
            self._config['mcp']['host'] = os.environ['MCP_HOST']
        if os.environ.get('MCP_PORT'):
            self._config['mcp']['port'] = int(os.environ['MCP_PORT'])
        
        # Web Interface 配置
        if os.environ.get('WEB_HOST'):
            self._config['web_interface']['host'] = os.environ['WEB_HOST']
        if os.environ.get('WEB_PORT'):
            self._config['web_interface']['port'] = int(os.environ['WEB_PORT'])
        
        # 日誌配置
        if os.environ.get('LOG_LEVEL'):
            self._config['logging']['level'] = os.environ['LOG_LEVEL']
    
    def _merge_config(self, new_config: Dict[str, Any]):
        """合併配置"""
        def merge_dict(base: Dict, update: Dict):
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge_dict(base[key], value)
                else:
                    base[key] = value
        
        merge_dict(self._config, new_config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """取得配置值（支援點號路徑）"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    @property
    def mcp_host(self) -> str:
        return self.get('mcp.host')
    
    @property
    def mcp_port(self) -> int:
        return self.get('mcp.port')
    
    @property
    def web_host(self) -> str:
        return self.get('web_interface.host')
    
    @property
    def web_port(self) -> int:
        return self.get('web_interface.port')
    
    @property
    def log_level(self) -> str:
        return self.get('logging.level')
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return self._config.copy()
