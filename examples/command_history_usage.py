"""
本地指令歷史與快取使用範例

示範如何在實際應用中使用 CommandHistoryManager 與 History API。
"""

from datetime import timedelta
from flask import Flask

from src.robot_service.command_history_manager import CommandHistoryManager
from src.robot_service.history_api import create_history_api_blueprint
from src.common.datetime_utils import utc_now


# ====================
# 基本使用範例
# ====================

def basic_usage_example():
    """基本使用範例：記錄與查詢指令"""
    
    # 1. 建立 CommandHistoryManager
    manager = CommandHistoryManager(
        history_db_path='~/.robot-console/command_history.db',
        cache_max_size=500,
        cache_ttl_seconds=1800  # 30 分鐘
    )
    
    # 2. 記錄新指令
    record = manager.record_command(
        robot_id='robot_7',
        command_type='robot.action',
        command_params={
            'action_name': 'go_forward',
            'duration_ms': 3000,
            'speed': 'normal'
        },
        actor_type='human',
        actor_id='user-123',
        source='webui',
        labels={'project': 'demo-001', 'environment': 'production'}
    )
    
    print(f"✅ Command recorded: {record.command_id}")
    print(f"   Trace ID: {record.trace_id}")
    print(f"   Status: {record.status}")
    
    # 3. 更新指令狀態
    manager.update_command_status(
        command_id=record.command_id,
        status='running'
    )
    print(f"✅ Status updated to: running")
    
    # 4. 模擬指令完成
    manager.update_command_status(
        command_id=record.command_id,
        status='succeeded',
        result={
            'final_position': {'x': 1.2, 'y': 0.5},
            'distance_traveled': 3.5
        },
        execution_time_ms=2850
    )
    print(f"✅ Command completed successfully")
    
    # 5. 取得指令結果（從快取）
    result = manager.get_command_result(command_id=record.command_id)
    print(f"✅ Result retrieved: {result}")
    
    # 6. 查詢歷史記錄
    records = manager.get_command_history(
        robot_id='robot_7',
        status='succeeded',
        limit=10
    )
    print(f"✅ Found {len(records)} successful commands for robot_7")
    
    # 7. 取得快取統計
    stats = manager.get_cache_stats()
    print(f"✅ Cache stats:")
    print(f"   Size: {stats['size']}/{stats['max_size']}")
    print(f"   Hit rate: {stats['hit_rate']}%")
    print(f"   Hits: {stats['hits']}, Misses: {stats['misses']}")


# ====================
# 整合 Flask 應用範例
# ====================

def flask_integration_example():
    """Flask 整合範例：建立完整的 API 服務"""
    
    # 1. 建立 Flask 應用
    app = Flask(__name__)
    
    # 2. 建立 CommandHistoryManager
    manager = CommandHistoryManager()
    
    # 3. 註冊 History API Blueprint
    history_bp = create_history_api_blueprint(
        history_manager=manager,
        url_prefix='/api/commands'
    )
    app.register_blueprint(history_bp)
    
    # 4. 啟動應用
    # app.run(host='0.0.0.0', port=5001)
    
    print("✅ Flask app configured with History API")
    print("   Available endpoints:")
    print("   - GET  /api/commands/history")
    print("   - GET  /api/commands/history/<command_id>")
    print("   - GET  /api/commands/cache/stats")
    print("   - DELETE /api/commands/cache")
    print("   - POST /api/commands/cache/cleanup")
    print("   - POST /api/commands/history/cleanup")
    print("   - GET  /api/commands/stats")


# ====================
# 查詢與分析範例
# ====================

def query_and_analysis_example():
    """查詢與分析範例：歷史資料分析"""
    
    manager = CommandHistoryManager()
    
    # 1. 查詢最近 24 小時的指令
    now = utc_now()
    start_time = now - timedelta(hours=24)
    
    records = manager.get_command_history(
        start_time=start_time,
        limit=1000
    )
    
    print(f"✅ Found {len(records)} commands in last 24 hours")
    
    # 2. 按狀態統計
    status_counts = {}
    for record in records:
        status_counts[record.status] = status_counts.get(record.status, 0) + 1
    
    print(f"✅ Status distribution:")
    for status, count in status_counts.items():
        print(f"   {status}: {count}")
    
    # 3. 計算平均執行時間
    succeeded_records = [r for r in records if r.status == 'succeeded' and r.execution_time_ms]
    
    if succeeded_records:
        avg_time = sum(r.execution_time_ms for r in succeeded_records) / len(succeeded_records)
        print(f"✅ Average execution time: {avg_time:.2f}ms")
    
    # 4. 找出執行時間最長的指令
    if succeeded_records:
        slowest = max(succeeded_records, key=lambda r: r.execution_time_ms)
        print(f"✅ Slowest command:")
        print(f"   ID: {slowest.command_id}")
        print(f"   Time: {slowest.execution_time_ms}ms")
        print(f"   Action: {slowest.command_params.get('action_name')}")
    
    # 5. 按機器人統計
    robot_counts = {}
    for record in records:
        robot_counts[record.robot_id] = robot_counts.get(record.robot_id, 0) + 1
    
    print(f"✅ Commands by robot:")
    for robot_id, count in sorted(robot_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"   {robot_id}: {count} commands")


# ====================
# 維護任務範例
# ====================

def maintenance_tasks_example():
    """維護任務範例：定期清理與優化"""
    
    manager = CommandHistoryManager()
    
    # 1. 清理過期快取
    print("🔧 Cleaning expired cache entries...")
    cache_cleaned = manager.cleanup_expired_cache()
    print(f"✅ Cleaned {cache_cleaned} expired cache entries")
    
    # 2. 清理 30 天前的歷史記錄
    print("🔧 Cleaning old history records...")
    history_cleaned = manager.cleanup_old_history(hours=720)  # 30 days
    print(f"✅ Cleaned {history_cleaned} old history records")
    
    # 3. 取得統計資訊
    print("📊 Current statistics:")
    
    total = manager.count_commands()
    print(f"   Total commands: {total}")
    
    for status in ['pending', 'running', 'succeeded', 'failed', 'cancelled']:
        count = manager.count_commands(status=status)
        if count > 0:
            print(f"   {status}: {count}")
    
    cache_stats = manager.get_cache_stats()
    print(f"   Cache: {cache_stats['size']}/{cache_stats['max_size']} items")
    print(f"   Hit rate: {cache_stats['hit_rate']}%")


# ====================
# 錯誤處理範例
# ====================

def error_handling_example():
    """錯誤處理範例：優雅處理異常情況"""
    
    manager = CommandHistoryManager()
    
    # 1. 處理不存在的指令
    try:
        result = manager.get_command_result(command_id='nonexistent-cmd')
        if result is None:
            print("⚠️  Command not found, using default value")
            default_result = {'status': 'unknown'}
            print(f"   Using default result: {default_result}")
    except Exception as e:
        print(f"❌ Error getting command result: {e}")
    
    # 2. 處理查詢錯誤
    try:
        records = manager.get_command_history(
            robot_id='robot_7',
            limit=100
        )
        print(f"✅ Successfully queried {len(records)} records")
    except Exception as e:
        print(f"❌ Query failed: {e}")
    
    # 3. 監控快取命中率
    stats = manager.get_cache_stats()
    
    if stats['hit_rate'] < 50:
        print(f"⚠️  Low cache hit rate: {stats['hit_rate']}%")
        print("   Consider increasing cache size or TTL")
    else:
        print(f"✅ Good cache hit rate: {stats['hit_rate']}%")


# ====================
# 離線使用範例
# ====================

def offline_usage_example():
    """離線使用範例：Edge 環境離線記錄"""
    
    manager = CommandHistoryManager()
    
    print("🌐 Simulating offline Edge environment...")
    
    # 1. 離線時記錄指令
    offline_commands = []
    
    for i in range(5):
        record = manager.record_command(
            command_id=f'offline-cmd-{i}',
            robot_id='robot_7',
            command_params={'action': f'action_{i}'},
            source='edge_ui',
            labels={'mode': 'offline'}
        )
        offline_commands.append(record)
        print(f"✅ Offline command recorded: {record.command_id}")
    
    # 2. 更新執行結果
    for i, record in enumerate(offline_commands):
        manager.update_command_status(
            command_id=record.command_id,
            status='succeeded',
            execution_time_ms=1000 + i * 100
        )
    
    print(f"✅ {len(offline_commands)} offline commands recorded")
    
    # 3. 查詢離線記錄
    offline_records = manager.get_command_history(
        source='edge_ui',
        limit=100
    )
    
    print(f"✅ Found {len(offline_records)} offline commands in history")
    
    # 4. 模擬恢復連線後同步（實際實作需要額外的同步邏輯）
    print("🌐 Connection restored, history ready for sync")


# ====================
# 主程式
# ====================

if __name__ == '__main__':
    print("=" * 60)
    print("本地指令歷史與快取使用範例")
    print("=" * 60)
    print()
    
    print("1️⃣  基本使用範例")
    print("-" * 60)
    basic_usage_example()
    print()
    
    print("2️⃣  Flask 整合範例")
    print("-" * 60)
    flask_integration_example()
    print()
    
    print("3️⃣  查詢與分析範例")
    print("-" * 60)
    query_and_analysis_example()
    print()
    
    print("4️⃣  維護任務範例")
    print("-" * 60)
    maintenance_tasks_example()
    print()
    
    print("5️⃣  錯誤處理範例")
    print("-" * 60)
    error_handling_example()
    print()
    
    print("6️⃣  離線使用範例")
    print("-" * 60)
    offline_usage_example()
    print()
    
    print("=" * 60)
    print("✅ 所有範例執行完成！")
    print("=" * 60)
