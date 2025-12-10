"""
測試 CommandHistoryManager 功能
"""

import os
import tempfile
import time

import pytest

from src.robot_service.command_history_manager import CommandHistoryManager
from src.common.datetime_utils import utc_now


@pytest.fixture
def temp_db():
    """建立臨時資料庫"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def manager(temp_db):
    """建立測試用的 CommandHistoryManager"""
    return CommandHistoryManager(
        history_db_path=temp_db,
        cache_max_size=10,
        cache_ttl_seconds=5
    )


class TestCommandHistoryManager:
    """測試 CommandHistoryManager 功能"""
    
    def test_init(self, manager):
        """測試初始化"""
        assert manager.history_store is not None
        assert manager.result_cache is not None
        assert manager.auto_cleanup_hours == 720
    
    def test_record_command(self, manager):
        """測試記錄指令"""
        record = manager.record_command(
            robot_id='robot_7',
            command_type='robot.action',
            command_params={'action_name': 'go_forward'},
            actor_type='human',
            actor_id='user-123',
            source='webui'
        )
        
        assert record.command_id is not None
        assert record.trace_id is not None
        assert record.robot_id == 'robot_7'
        assert record.status == 'pending'
    
    def test_record_command_with_custom_ids(self, manager):
        """測試使用自訂 ID 記錄指令"""
        record = manager.record_command(
            command_id='cmd-001',
            trace_id='trace-001',
            robot_id='robot_7'
        )
        
        assert record.command_id == 'cmd-001'
        assert record.trace_id == 'trace-001'
    
    def test_update_command_status(self, manager):
        """測試更新指令狀態"""
        record = manager.record_command(
            command_id='cmd-001',
            robot_id='robot_7'
        )
        
        # 更新為 running
        success = manager.update_command_status(
            command_id='cmd-001',
            status='running'
        )
        assert success is True
        
        # 更新為 succeeded
        result = {'position': {'x': 1.0, 'y': 2.0}}
        success = manager.update_command_status(
            command_id='cmd-001',
            status='succeeded',
            result=result,
            execution_time_ms=2850
        )
        assert success is True
        
        # 驗證記錄已更新
        stored_record = manager.history_store.get_record('cmd-001')
        assert stored_record.status == 'succeeded'
        assert stored_record.result == result
        assert stored_record.execution_time_ms == 2850
        assert stored_record.completed_at is not None
    
    def test_cache_command_result(self, manager):
        """測試快取指令結果"""
        result = {'status': 'ok', 'data': 'test'}
        
        success = manager.cache_command_result(
            command_id='cmd-001',
            trace_id='trace-001',
            result=result
        )
        assert success is True
        
        # 驗證快取
        cached = manager.result_cache.get('cmd-001')
        assert cached == result
    
    def test_get_command_result_from_cache(self, manager):
        """測試從快取取得結果"""
        result = {'status': 'ok'}
        
        manager.cache_command_result(
            command_id='cmd-001',
            trace_id='trace-001',
            result=result
        )
        
        # 從快取取得
        retrieved = manager.get_command_result(command_id='cmd-001')
        assert retrieved == result
    
    def test_get_command_result_from_history(self, manager):
        """測試從歷史記錄取得結果"""
        # 記錄指令並更新結果
        manager.record_command(
            command_id='cmd-001',
            trace_id='trace-001',
            robot_id='robot_7'
        )
        
        result = {'status': 'ok'}
        manager.update_command_status(
            command_id='cmd-001',
            status='succeeded',
            result=result
        )
        
        # 清空快取以測試從歷史取得
        manager.clear_cache()
        
        # 從歷史取得（會自動加入快取）
        retrieved = manager.get_command_result(command_id='cmd-001')
        assert retrieved == result
        
        # 驗證已加入快取
        cached = manager.result_cache.get('cmd-001')
        assert cached == result
    
    def test_get_command_history(self, manager):
        """測試查詢指令歷史"""
        # 記錄多筆指令
        for i in range(5):
            manager.record_command(
                command_id=f'cmd-{i}',
                robot_id='robot_7' if i < 3 else 'robot_3'
            )
        
        # 查詢所有
        records = manager.get_command_history()
        assert len(records) >= 5
        
        # 按機器人 ID 查詢
        records = manager.get_command_history(robot_id='robot_7')
        assert len(records) == 3
        assert all(r.robot_id == 'robot_7' for r in records)
    
    def test_get_command_history_with_pagination(self, manager):
        """測試分頁查詢"""
        # 記錄 15 筆指令
        for i in range(15):
            manager.record_command(
                command_id=f'cmd-{i:02d}',
                robot_id='robot_7'
            )
        
        # 第一頁
        records = manager.get_command_history(limit=10, offset=0)
        assert len(records) == 10
        
        # 第二頁
        records = manager.get_command_history(limit=10, offset=10)
        assert len(records) == 5
    
    def test_count_commands(self, manager):
        """測試統計指令數量"""
        # 記錄指令
        for i in range(10):
            record = manager.record_command(
                command_id=f'cmd-{i}',
                robot_id='robot_7' if i < 6 else 'robot_3'
            )
            
            # 更新部分狀態
            if i % 2 == 0:
                manager.update_command_status(
                    command_id=f'cmd-{i}',
                    status='succeeded'
                )
        
        # 總數
        total = manager.count_commands()
        assert total == 10
        
        # 按機器人 ID
        count = manager.count_commands(robot_id='robot_7')
        assert count == 6
        
        # 按狀態
        count = manager.count_commands(status='succeeded')
        assert count == 5
    
    def test_get_cache_stats(self, manager):
        """測試取得快取統計"""
        # 新增一些快取項目
        for i in range(5):
            manager.cache_command_result(
                command_id=f'cmd-{i}',
                trace_id=f'trace-{i}',
                result={'index': i}
            )
        
        # 存取部分項目
        manager.get_command_result(command_id='cmd-0')
        manager.get_command_result(command_id='cmd-1')
        manager.get_command_result(command_id='nonexistent')
        
        stats = manager.get_cache_stats()
        
        assert stats['size'] == 5
        assert stats['hits'] == 2
        assert stats['misses'] == 1
        assert stats['sets'] == 5
    
    def test_cleanup_expired_cache(self, manager):
        """測試清理過期快取"""
        # 新增短 TTL 的項目
        manager.cache_command_result(
            command_id='cmd-001',
            trace_id='trace-001',
            result={'data': 'test'},
            ttl_seconds=1
        )
        
        # 等待過期
        time.sleep(1.1)
        
        count = manager.cleanup_expired_cache()
        assert count == 1
        
        # 驗證已清理
        result = manager.get_command_result(command_id='cmd-001', use_cache=True)
        assert result is None
    
    def test_cleanup_old_history(self, manager):
        """測試清理舊歷史記錄"""
        from datetime import timedelta
        
        # 記錄舊指令（模擬）
        old_time = utc_now() - timedelta(hours=800)
        
        # 由於 CommandRecord 的 created_at 是在建立時設定，
        # 這裡我們直接在資料庫中操作
        for i in range(3):
            record = manager.record_command(
                command_id=f'cmd-old-{i}',
                robot_id='robot_7'
            )
            # 直接更新資料庫中的時間
            manager.history_store.update_record(
                f'cmd-old-{i}',
                {'created_at': old_time}
            )
        
        # 記錄新指令
        for i in range(2):
            manager.record_command(
                command_id=f'cmd-new-{i}',
                robot_id='robot_7'
            )
        
        # 清理 720 小時（30 天）前的記錄
        count = manager.cleanup_old_history(hours=720)
        assert count == 3
        
        # 驗證剩餘記錄
        total = manager.count_commands()
        assert total == 2
    
    def test_clear_cache(self, manager):
        """測試清空快取"""
        # 新增快取項目
        manager.cache_command_result(
            command_id='cmd-001',
            trace_id='trace-001',
            result={'data': 'test'}
        )
        
        # 清空快取
        manager.clear_cache()
        
        # 驗證已清空
        result = manager.get_command_result(command_id='cmd-001', use_cache=True)
        assert result is None
    
    def test_clear_all_history(self, manager):
        """測試清空所有歷史"""
        # 記錄指令
        for i in range(5):
            manager.record_command(
                command_id=f'cmd-{i}',
                robot_id='robot_7'
            )
        
        # 清空
        success = manager.clear_all_history()
        assert success is True
        
        # 驗證已清空
        total = manager.count_commands()
        assert total == 0
