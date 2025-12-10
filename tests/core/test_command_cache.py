"""
測試 CommandCache 功能
"""

import time
from datetime import timedelta

import pytest

from src.common.command_cache import CommandCache, CommandResultCache, CacheEntry
from src.common.datetime_utils import utc_now


@pytest.fixture
def cache():
    """建立測試用的 CommandCache"""
    return CommandCache(max_size=5, default_ttl_seconds=10)


@pytest.fixture
def result_cache():
    """建立測試用的 CommandResultCache"""
    return CommandResultCache(max_size=3, default_ttl_seconds=5)


class TestCacheEntry:
    """測試 CacheEntry 資料模型"""
    
    def test_create_entry(self):
        """測試建立快取項目"""
        entry = CacheEntry(key='test', value={'data': 123})
        assert entry.key == 'test'
        assert entry.value == {'data': 123}
        assert entry.hit_count == 0
    
    def test_is_not_expired(self):
        """測試未過期項目"""
        entry = CacheEntry(
            key='test',
            value='data',
            expires_at=utc_now() + timedelta(seconds=60)
        )
        assert entry.is_expired() is False
    
    def test_is_expired(self):
        """測試已過期項目"""
        entry = CacheEntry(
            key='test',
            value='data',
            expires_at=utc_now() - timedelta(seconds=1)
        )
        assert entry.is_expired() is True
    
    def test_never_expires(self):
        """測試永不過期項目"""
        entry = CacheEntry(key='test', value='data', expires_at=None)
        assert entry.is_expired() is False
    
    def test_touch(self):
        """測試更新存取記錄"""
        entry = CacheEntry(key='test', value='data')
        initial_accessed = entry.accessed_at
        initial_hit_count = entry.hit_count
        
        time.sleep(0.01)
        entry.touch()
        
        assert entry.accessed_at > initial_accessed
        assert entry.hit_count == initial_hit_count + 1


class TestCommandCache:
    """測試 CommandCache 功能"""
    
    def test_init(self, cache):
        """測試快取初始化"""
        assert cache.max_size == 5
        assert cache.default_ttl_seconds == 10
        assert cache.enable_stats is True
    
    def test_set_and_get(self, cache):
        """測試設定與取得快取"""
        success = cache.set('key1', {'data': 'value1'})
        assert success is True
        
        value = cache.get('key1')
        assert value == {'data': 'value1'}
    
    def test_get_nonexistent(self, cache):
        """測試取得不存在的快取"""
        value = cache.get('nonexistent')
        assert value is None
    
    def test_set_with_custom_ttl(self, cache):
        """測試使用自訂 TTL"""
        cache.set('key1', 'value1', ttl_seconds=1)
        
        # 立即取得應該成功
        value = cache.get('key1')
        assert value == 'value1'
        
        # 等待過期
        time.sleep(1.1)
        value = cache.get('key1')
        assert value is None
    
    def test_set_no_expiry(self, cache):
        """測試永不過期的快取"""
        cache.set('key1', 'value1', ttl_seconds=0)
        
        # 等待預設 TTL 時間後仍應可取得
        time.sleep(0.5)
        value = cache.get('key1')
        assert value == 'value1'
    
    def test_overwrite_existing(self, cache):
        """測試覆寫現有快取"""
        cache.set('key1', 'value1')
        cache.set('key1', 'value2')
        
        value = cache.get('key1')
        assert value == 'value2'
    
    def test_delete(self, cache):
        """測試刪除快取"""
        cache.set('key1', 'value1')
        
        success = cache.delete('key1')
        assert success is True
        
        value = cache.get('key1')
        assert value is None
        
        # 刪除不存在的鍵
        success = cache.delete('nonexistent')
        assert success is False
    
    def test_clear(self, cache):
        """測試清空快取"""
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        
        cache.clear()
        
        assert cache.get('key1') is None
        assert cache.get('key2') is None
    
    def test_lru_eviction(self, cache):
        """測試 LRU 淘汰策略"""
        # 填滿快取（max_size=5）
        for i in range(5):
            cache.set(f'key{i}', f'value{i}')
        
        # 存取 key0（變成最近使用）
        cache.get('key0')
        
        # 新增第 6 個項目，應該淘汰 key1（最少使用）
        cache.set('key5', 'value5')
        
        assert cache.get('key0') == 'value0'  # 仍存在
        assert cache.get('key1') is None  # 被淘汰
        assert cache.get('key5') == 'value5'  # 新項目
    
    def test_cleanup_expired(self, cache):
        """測試清理過期項目"""
        # 新增短 TTL 的項目
        cache.set('key1', 'value1', ttl_seconds=1)
        cache.set('key2', 'value2', ttl_seconds=10)
        
        # 等待 key1 過期
        time.sleep(1.1)
        
        cleaned = cache.cleanup_expired()
        assert cleaned == 1
        
        assert cache.get('key1') is None
        assert cache.get('key2') == 'value2'
    
    def test_get_stats(self, cache):
        """測試統計資訊"""
        # 執行一些操作
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')
        cache.get('key1')  # hit
        cache.get('key1')  # hit
        cache.get('key3')  # miss
        cache.delete('key2')
        
        stats = cache.get_stats()
        
        assert stats['size'] == 1  # 只剩 key1
        assert stats['max_size'] == 5
        assert stats['hits'] == 2
        assert stats['misses'] == 1
        assert stats['sets'] == 2
        assert stats['deletes'] == 1
        assert stats['hit_rate'] > 0
    
    def test_reset_stats(self, cache):
        """測試重置統計資訊"""
        cache.set('key1', 'value1')
        cache.get('key1')
        
        stats_before = cache.get_stats()
        assert stats_before['hits'] > 0
        
        cache.reset_stats()
        
        stats_after = cache.get_stats()
        assert stats_after['hits'] == 0
        assert stats_after['misses'] == 0


class TestCommandResultCache:
    """測試 CommandResultCache 功能"""
    
    def test_set_command_result(self, result_cache):
        """測試設定指令結果"""
        result = {
            'status': 'succeeded',
            'execution_time_ms': 2850
        }
        
        success = result_cache.set_command_result(
            command_id='cmd-001',
            trace_id='trace-001',
            result=result
        )
        assert success is True
        
        # 透過 command_id 取得
        cached = result_cache.get('cmd-001')
        assert cached == result
    
    def test_get_by_trace_id(self, result_cache):
        """測試透過 trace_id 取得結果"""
        result = {'status': 'succeeded'}
        
        result_cache.set_command_result(
            command_id='cmd-001',
            trace_id='trace-001',
            result=result
        )
        
        cached = result_cache.get_by_trace_id('trace-001')
        assert cached == result
    
    def test_get_by_trace_id_nonexistent(self, result_cache):
        """測試取得不存在的 trace_id"""
        cached = result_cache.get_by_trace_id('nonexistent')
        assert cached is None
    
    def test_delete_by_trace_id(self, result_cache):
        """測試透過 trace_id 刪除結果"""
        result_cache.set_command_result(
            command_id='cmd-001',
            trace_id='trace-001',
            result={'status': 'succeeded'}
        )
        
        success = result_cache.delete_by_trace_id('trace-001')
        assert success is True
        
        # 確認已刪除
        assert result_cache.get('cmd-001') is None
        assert result_cache.get_by_trace_id('trace-001') is None
    
    def test_multiple_commands(self, result_cache):
        """測試多個指令結果"""
        for i in range(3):
            result_cache.set_command_result(
                command_id=f'cmd-{i}',
                trace_id=f'trace-{i}',
                result={'index': i}
            )
        
        # 驗證所有結果都可取得
        for i in range(3):
            cached = result_cache.get_by_trace_id(f'trace-{i}')
            assert cached == {'index': i}
    
    def test_lru_with_trace_mapping(self, result_cache):
        """測試 LRU 淘汰是否影響 trace_id 對應"""
        # 填滿快取（max_size=3）
        for i in range(3):
            result_cache.set_command_result(
                command_id=f'cmd-{i}',
                trace_id=f'trace-{i}',
                result={'index': i}
            )
        
        # 新增第 4 個，應淘汰 cmd-0
        result_cache.set_command_result(
            command_id='cmd-3',
            trace_id='trace-3',
            result={'index': 3}
        )
        
        # cmd-0 應被淘汰
        assert result_cache.get('cmd-0') is None
        assert result_cache.get_by_trace_id('trace-0') is None
        
        # 其他應仍存在
        assert result_cache.get_by_trace_id('trace-3') == {'index': 3}
    
    def test_clear_with_trace_mapping(self, result_cache):
        """測試清空快取是否清除 trace_id 對應"""
        result_cache.set_command_result(
            command_id='cmd-001',
            trace_id='trace-001',
            result={'status': 'succeeded'}
        )
        
        result_cache.clear()
        
        assert result_cache.get_by_trace_id('trace-001') is None
    
    def test_ttl_expiration(self, result_cache):
        """測試 TTL 過期機制"""
        result_cache.set_command_result(
            command_id='cmd-001',
            trace_id='trace-001',
            result={'status': 'succeeded'},
            ttl_seconds=1
        )
        
        # 立即取得應成功
        cached = result_cache.get_by_trace_id('trace-001')
        assert cached is not None
        
        # 等待過期
        time.sleep(1.1)
        cached = result_cache.get_by_trace_id('trace-001')
        assert cached is None
