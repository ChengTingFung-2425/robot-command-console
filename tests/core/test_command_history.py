"""
測試 CommandHistoryStore 功能
"""

import os
import tempfile
from datetime import datetime, timedelta

import pytest

from src.common.command_history import CommandRecord, CommandHistoryStore
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
def history_store(temp_db):
    """建立測試用的 CommandHistoryStore"""
    return CommandHistoryStore(db_path=temp_db)


@pytest.fixture
def sample_record():
    """建立測試用的 CommandRecord"""
    return CommandRecord(
        command_id='cmd-001',
        trace_id='trace-001',
        robot_id='robot_7',
        command_type='robot.action',
        command_params={'action_name': 'go_forward', 'duration_ms': 3000},
        status='pending',
        actor_type='human',
        actor_id='user-123',
        source='webui',
        labels={'project': 'test'}
    )


class TestCommandRecord:
    """測試 CommandRecord 資料模型"""
    
    def test_create_record(self, sample_record):
        """測試建立記錄"""
        assert sample_record.command_id == 'cmd-001'
        assert sample_record.robot_id == 'robot_7'
        assert sample_record.status == 'pending'
        assert isinstance(sample_record.created_at, datetime)
    
    def test_to_dict(self, sample_record):
        """測試轉換為字典"""
        data = sample_record.to_dict()
        assert data['command_id'] == 'cmd-001'
        assert isinstance(data['created_at'], str)
        assert 'command_params' in data
    
    def test_from_dict(self, sample_record):
        """測試從字典建立"""
        data = sample_record.to_dict()
        record = CommandRecord.from_dict(data)
        assert record.command_id == sample_record.command_id
        assert isinstance(record.created_at, datetime)


class TestCommandHistoryStore:
    """測試 CommandHistoryStore 功能"""
    
    def test_init_db(self, temp_db):
        """測試資料庫初始化"""
        _ = CommandHistoryStore(db_path=temp_db)
        assert os.path.exists(temp_db)
    
    def test_add_record(self, history_store, sample_record):
        """測試新增記錄"""
        success = history_store.add_record(sample_record)
        assert success is True
        
        # 測試重複新增
        success = history_store.add_record(sample_record)
        assert success is False
    
    def test_get_record(self, history_store, sample_record):
        """測試取得記錄"""
        history_store.add_record(sample_record)
        
        record = history_store.get_record('cmd-001')
        assert record is not None
        assert record.command_id == 'cmd-001'
        assert record.robot_id == 'robot_7'
        
        # 測試取得不存在的記錄
        record = history_store.get_record('cmd-999')
        assert record is None
    
    def test_update_record(self, history_store, sample_record):
        """測試更新記錄"""
        history_store.add_record(sample_record)
        
        updates = {
            'status': 'running',
            'execution_time_ms': 150
        }
        success = history_store.update_record('cmd-001', updates)
        assert success is True
        
        record = history_store.get_record('cmd-001')
        assert record.status == 'running'
        assert record.execution_time_ms == 150
    
    def test_update_with_result(self, history_store, sample_record):
        """測試更新記錄包含結果"""
        history_store.add_record(sample_record)
        
        updates = {
            'status': 'succeeded',
            'completed_at': utc_now(),
            'result': {'position': {'x': 1.0, 'y': 2.0}},
            'execution_time_ms': 2850
        }
        success = history_store.update_record('cmd-001', updates)
        assert success is True
        
        record = history_store.get_record('cmd-001')
        assert record.status == 'succeeded'
        assert record.result is not None
        assert record.result['position']['x'] == 1.0
    
    def test_query_records_by_robot_id(self, history_store):
        """測試按機器人 ID 查詢"""
        # 新增多筆記錄
        for i in range(5):
            record = CommandRecord(
                command_id=f'cmd-{i}',
                trace_id=f'trace-{i}',
                robot_id='robot_7' if i < 3 else 'robot_3',
                command_type='robot.action',
                command_params={'action': 'test'},
                status='pending'
            )
            history_store.add_record(record)
        
        # 查詢 robot_7 的記錄
        records = history_store.query_records(robot_id='robot_7')
        assert len(records) == 3
        assert all(r.robot_id == 'robot_7' for r in records)
    
    def test_query_records_by_status(self, history_store):
        """測試按狀態查詢"""
        statuses = ['pending', 'running', 'succeeded', 'failed']
        
        for i, status in enumerate(statuses):
            record = CommandRecord(
                command_id=f'cmd-{i}',
                trace_id=f'trace-{i}',
                robot_id='robot_7',
                command_type='robot.action',
                command_params={'action': 'test'},
                status=status
            )
            history_store.add_record(record)
        
        # 查詢 succeeded 狀態
        records = history_store.query_records(status='succeeded')
        assert len(records) == 1
        assert records[0].status == 'succeeded'
    
    def test_query_records_by_time_range(self, history_store):
        """測試按時間範圍查詢"""
        now = utc_now()
        
        # 新增不同時間的記錄
        for i in range(3):
            record = CommandRecord(
                command_id=f'cmd-{i}',
                trace_id=f'trace-{i}',
                robot_id='robot_7',
                command_type='robot.action',
                command_params={'action': 'test'},
                status='pending',
                created_at=now - timedelta(hours=i)
            )
            history_store.add_record(record)
        
        # 查詢最近 1 小時的記錄
        start_time = now - timedelta(hours=1)
        records = history_store.query_records(start_time=start_time)
        assert len(records) == 2
    
    def test_query_records_pagination(self, history_store):
        """測試分頁查詢"""
        # 新增 15 筆記錄
        for i in range(15):
            record = CommandRecord(
                command_id=f'cmd-{i:02d}',
                trace_id=f'trace-{i}',
                robot_id='robot_7',
                command_type='robot.action',
                command_params={'action': 'test'},
                status='pending'
            )
            history_store.add_record(record)
        
        # 第一頁（10 筆）
        records = history_store.query_records(limit=10, offset=0)
        assert len(records) == 10
        
        # 第二頁（5 筆）
        records = history_store.query_records(limit=10, offset=10)
        assert len(records) == 5
    
    def test_query_records_ordering(self, history_store):
        """測試排序查詢"""
        now = utc_now()
        
        for i in range(3):
            record = CommandRecord(
                command_id=f'cmd-{i}',
                trace_id=f'trace-{i}',
                robot_id='robot_7',
                command_type='robot.action',
                command_params={'action': 'test'},
                status='pending',
                created_at=now - timedelta(minutes=i)
            )
            history_store.add_record(record)
        
        # 降序（最新在前）
        records = history_store.query_records(order_by='created_at', order_desc=True)
        assert records[0].command_id == 'cmd-0'
        
        # 升序（最舊在前）
        records = history_store.query_records(order_by='created_at', order_desc=False)
        assert records[0].command_id == 'cmd-2'
    
    def test_count_records(self, history_store):
        """測試統計記錄數量"""
        # 新增記錄
        for i in range(10):
            record = CommandRecord(
                command_id=f'cmd-{i}',
                trace_id=f'trace-{i}',
                robot_id='robot_7' if i < 6 else 'robot_3',
                command_type='robot.action',
                command_params={'action': 'test'},
                status='succeeded' if i % 2 == 0 else 'failed'
            )
            history_store.add_record(record)
        
        # 總數
        total = history_store.count_records()
        assert total == 10
        
        # 按機器人 ID
        count = history_store.count_records(robot_id='robot_7')
        assert count == 6
        
        # 按狀態
        count = history_store.count_records(status='succeeded')
        assert count == 5
    
    def test_delete_record(self, history_store, sample_record):
        """測試刪除記錄"""
        history_store.add_record(sample_record)
        
        success = history_store.delete_record('cmd-001')
        assert success is True
        
        record = history_store.get_record('cmd-001')
        assert record is None
    
    def test_delete_old_records(self, history_store):
        """測試刪除舊記錄"""
        now = utc_now()
        
        # 新增舊記錄
        for i in range(5):
            record = CommandRecord(
                command_id=f'cmd-old-{i}',
                trace_id=f'trace-{i}',
                robot_id='robot_7',
                command_type='robot.action',
                command_params={'action': 'test'},
                status='pending',
                created_at=now - timedelta(days=10)
            )
            history_store.add_record(record)
        
        # 新增新記錄
        for i in range(3):
            record = CommandRecord(
                command_id=f'cmd-new-{i}',
                trace_id=f'trace-new-{i}',
                robot_id='robot_7',
                command_type='robot.action',
                command_params={'action': 'test'},
                status='pending',
                created_at=now
            )
            history_store.add_record(record)
        
        # 刪除 7 天前的記錄
        deleted = history_store.delete_old_records(now - timedelta(days=7))
        assert deleted == 5
        
        # 確認剩餘記錄
        total = history_store.count_records()
        assert total == 3
    
    def test_clear_all(self, history_store):
        """測試清空所有記錄"""
        # 新增記錄
        for i in range(5):
            record = CommandRecord(
                command_id=f'cmd-{i}',
                trace_id=f'trace-{i}',
                robot_id='robot_7',
                command_type='robot.action',
                command_params={'action': 'test'},
                status='pending'
            )
            history_store.add_record(record)
        
        # 清空
        success = history_store.clear_all()
        assert success is True
        
        # 確認已清空
        total = history_store.count_records()
        assert total == 0
