"""
FHS (Filesystem Hierarchy Standard) 路徑管理模組

提供符合 FHS 標準的路徑取得功能，支援：
- Linux: FHS 標準路徑
- Windows: AppData 路徑
- macOS: Application Support 路徑

用於同步日誌、快取資料等需要遵循標準路徑的場景。
"""

import os
import platform
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class FHSPaths:
    """FHS 路徑管理類別
    
    根據作業系統提供標準化的應用程式路徑。
    """
    
    APP_NAME = "robot-command-console"
    
    @classmethod
    def get_cache_dir(cls, subdir: Optional[str] = None) -> Path:
        """取得快取資料目錄
        
        Args:
            subdir: 子目錄名稱（可選）
            
        Returns:
            Path: 快取目錄路徑
            
        Examples:
            Linux: /var/cache/robot-command-console/
            Windows: %LOCALAPPDATA%\\robot-command-console\\cache\\
            macOS: ~/Library/Caches/robot-command-console/
        """
        system = platform.system()
        
        if system == "Linux":
            # FHS: /var/cache/<app>/
            base = Path("/var/cache") / cls.APP_NAME
        elif system == "Windows":
            # Windows: %LOCALAPPDATA%\<app>\cache\
            local_app_data = os.environ.get("LOCALAPPDATA")
            if not local_app_data:
                local_app_data = Path.home() / "AppData" / "Local"
            base = Path(local_app_data) / cls.APP_NAME / "cache"
        elif system == "Darwin":
            # macOS: ~/Library/Caches/<app>/
            base = Path.home() / "Library" / "Caches" / cls.APP_NAME
        else:
            # Fallback: 使用者家目錄下的 .cache
            base = Path.home() / ".cache" / cls.APP_NAME
            logger.warning(f"Unknown system {system}, using fallback cache path: {base}")
        
        if subdir:
            base = base / subdir
        
        return base
    
    @classmethod
    def get_data_dir(cls, subdir: Optional[str] = None) -> Path:
        """取得持久性資料目錄
        
        Args:
            subdir: 子目錄名稱（可選）
            
        Returns:
            Path: 資料目錄路徑
            
        Examples:
            Linux: /var/lib/robot-command-console/
            Windows: %APPDATA%\\robot-command-console\\
            macOS: ~/Library/Application Support/robot-command-console/
        """
        system = platform.system()
        
        if system == "Linux":
            # FHS: /var/lib/<app>/
            base = Path("/var/lib") / cls.APP_NAME
        elif system == "Windows":
            # Windows: %APPDATA%\<app>\
            app_data = os.environ.get("APPDATA")
            if not app_data:
                app_data = Path.home() / "AppData" / "Roaming"
            base = Path(app_data) / cls.APP_NAME
        elif system == "Darwin":
            # macOS: ~/Library/Application Support/<app>/
            base = Path.home() / "Library" / "Application Support" / cls.APP_NAME
        else:
            # Fallback: 使用者家目錄下的 .local/share
            base = Path.home() / ".local" / "share" / cls.APP_NAME
            logger.warning(f"Unknown system {system}, using fallback data path: {base}")
        
        if subdir:
            base = base / subdir
        
        return base
    
    @classmethod
    def get_log_dir(cls, subdir: Optional[str] = None) -> Path:
        """取得日誌目錄
        
        Args:
            subdir: 子目錄名稱（可選）
            
        Returns:
            Path: 日誌目錄路徑
            
        Examples:
            Linux: /var/log/robot-command-console/
            Windows: %LOCALAPPDATA%\\robot-command-console\\logs\\
            macOS: ~/Library/Logs/robot-command-console/
        """
        system = platform.system()
        
        if system == "Linux":
            # FHS: /var/log/<app>/
            # 但如果無權限則退回到 cache 目錄
            fhs_path = Path("/var/log") / cls.APP_NAME
            if os.access("/var/log", os.W_OK):
                base = fhs_path
            else:
                base = cls.get_cache_dir("logs")
                logger.info(f"No write permission to /var/log, using cache dir: {base}")
        elif system == "Windows":
            # Windows: %LOCALAPPDATA%\<app>\logs\
            local_app_data = os.environ.get("LOCALAPPDATA")
            if not local_app_data:
                local_app_data = Path.home() / "AppData" / "Local"
            base = Path(local_app_data) / cls.APP_NAME / "logs"
        elif system == "Darwin":
            # macOS: ~/Library/Logs/<app>/
            base = Path.home() / "Library" / "Logs" / cls.APP_NAME
        else:
            # Fallback: 使用快取目錄下的 logs
            base = cls.get_cache_dir("logs")
            logger.warning(f"Unknown system {system}, using fallback log path: {base}")
        
        if subdir:
            base = base / subdir
        
        return base
    
    @classmethod
    def ensure_dir(cls, path: Path) -> Path:
        """確保目錄存在
        
        Args:
            path: 目錄路徑
            
        Returns:
            Path: 建立後的目錄路徑
            
        Raises:
            PermissionError: 無權限建立目錄
            OSError: 其他系統錯誤
        """
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {path}")
            return path
        except PermissionError:
            logger.error(f"Permission denied creating directory: {path}")
            raise
        except OSError as err:
            logger.error(f"Failed to create directory {path}: {err}")
            raise
    
    @classmethod
    def get_sync_log_path(cls) -> Path:
        """取得同步日誌檔案路徑
        
        Returns:
            Path: 同步日誌檔案完整路徑
        """
        log_dir = cls.get_log_dir("sync")
        cls.ensure_dir(log_dir)
        return log_dir / "sync.log"
    
    @classmethod
    def get_sync_cache_dir(cls) -> Path:
        """取得同步快取目錄
        
        Returns:
            Path: 同步快取目錄路徑
        """
        cache_dir = cls.get_cache_dir("sync")
        cls.ensure_dir(cache_dir)
        return cache_dir


def get_sync_log_path() -> Path:
    """快捷函數：取得同步日誌路徑"""
    return FHSPaths.get_sync_log_path()


def get_sync_cache_dir() -> Path:
    """快捷函數：取得同步快取目錄"""
    return FHSPaths.get_sync_cache_dir()
