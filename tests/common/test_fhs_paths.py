"""
測試 FHS 路徑管理模組
"""

import pytest
import platform
from pathlib import Path
from unittest.mock import patch
from src.common.fhs_paths import FHSPaths, get_sync_log_path, get_sync_cache_dir


class TestFHSPaths:
    """測試 FHSPaths 類別"""
    
    def test_get_cache_dir_linux(self):
        """測試 Linux 快取目錄"""
        with patch('platform.system', return_value='Linux'):
            cache_dir = FHSPaths.get_cache_dir()
            assert cache_dir == Path("/var/cache/robot-command-console")
    
    def test_get_cache_dir_windows(self):
        """測試 Windows 快取目錄"""
        with patch('platform.system', return_value='Windows'):
            with patch.dict('os.environ', {'LOCALAPPDATA': 'C:\\Users\\Test\\AppData\\Local'}):
                cache_dir = FHSPaths.get_cache_dir()
                assert str(cache_dir).replace('/', '\\').endswith("robot-command-console\\cache")
    
    def test_get_cache_dir_macos(self):
        """測試 macOS 快取目錄"""
        with patch('platform.system', return_value='Darwin'):
            cache_dir = FHSPaths.get_cache_dir()
            assert "Library/Caches/robot-command-console" in str(cache_dir)
    
    def test_get_cache_dir_with_subdir(self):
        """測試帶子目錄的快取目錄"""
        with patch('platform.system', return_value='Linux'):
            cache_dir = FHSPaths.get_cache_dir("sync")
            assert cache_dir == Path("/var/cache/robot-command-console/sync")
    
    def test_get_data_dir_linux(self):
        """測試 Linux 資料目錄"""
        with patch('platform.system', return_value='Linux'):
            data_dir = FHSPaths.get_data_dir()
            assert data_dir == Path("/var/lib/robot-command-console")
    
    def test_get_data_dir_windows(self):
        """測試 Windows 資料目錄"""
        with patch('platform.system', return_value='Windows'):
            with patch.dict('os.environ', {'APPDATA': 'C:\\Users\\Test\\AppData\\Roaming'}):
                data_dir = FHSPaths.get_data_dir()
                assert str(data_dir).replace('/', '\\').endswith("robot-command-console")
    
    def test_get_log_dir_linux_with_permission(self):
        """測試 Linux 日誌目錄（有權限）"""
        with patch('platform.system', return_value='Linux'):
            with patch('os.access', return_value=True):
                log_dir = FHSPaths.get_log_dir()
                assert log_dir == Path("/var/log/robot-command-console")
    
    def test_get_log_dir_linux_without_permission(self):
        """測試 Linux 日誌目錄（無權限，退回快取）"""
        with patch('platform.system', return_value='Linux'):
            with patch('os.access', return_value=False):
                log_dir = FHSPaths.get_log_dir()
                assert log_dir == Path("/var/cache/robot-command-console/logs")
    
    def test_get_log_dir_windows(self):
        """測試 Windows 日誌目錄"""
        with patch('platform.system', return_value='Windows'):
            with patch.dict('os.environ', {'LOCALAPPDATA': 'C:\\Users\\Test\\AppData\\Local'}):
                log_dir = FHSPaths.get_log_dir()
                assert str(log_dir).replace('/', '\\').endswith("robot-command-console\\logs")
    
    def test_get_sync_log_path(self):
        """測試同步日誌路徑"""
        with patch('platform.system', return_value='Linux'):
            with patch('os.access', return_value=False):
                with patch.object(FHSPaths, 'ensure_dir', return_value=Path("/tmp/logs/sync")):
                    log_path = FHSPaths.get_sync_log_path()
                    assert "sync.log" in str(log_path)
    
    def test_get_sync_cache_dir(self):
        """測試同步快取目錄"""
        with patch('platform.system', return_value='Linux'):
            with patch.object(FHSPaths, 'ensure_dir', return_value=Path("/tmp/cache/sync")):
                cache_dir = FHSPaths.get_sync_cache_dir()
                assert "sync" in str(cache_dir)
    
    def test_fallback_for_unknown_system(self):
        """測試未知系統的退回路徑"""
        with patch('platform.system', return_value='UnknownOS'):
            cache_dir = FHSPaths.get_cache_dir()
            # 應該退回到使用者家目錄下的 .cache
            assert ".cache/robot-command-console" in str(cache_dir)


class TestHelperFunctions:
    """測試輔助函數"""
    
    def test_get_sync_log_path_function(self):
        """測試 get_sync_log_path 輔助函數"""
        with patch('platform.system', return_value='Linux'):
            with patch('os.access', return_value=False):
                with patch.object(FHSPaths, 'ensure_dir', return_value=Path("/tmp/logs/sync")):
                    log_path = get_sync_log_path()
                    assert isinstance(log_path, Path)
                    assert "sync.log" in str(log_path)
    
    def test_get_sync_cache_dir_function(self):
        """測試 get_sync_cache_dir 輔助函數"""
        with patch('platform.system', return_value='Linux'):
            with patch.object(FHSPaths, 'ensure_dir', return_value=Path("/tmp/cache/sync")):
                cache_dir = get_sync_cache_dir()
                assert isinstance(cache_dir, Path)
