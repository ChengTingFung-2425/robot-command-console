"""
Tests for Robot Monitoring Dashboard API

Phase 3.2 - 機器人監控儀表板 API 測試
"""

import importlib
import pytest


def get_edge_ui_module():
    """取得 edge_ui 模組的直接參考"""
    return importlib.import_module('src.robot_service.electron.edge_ui')


def reset_robot_data():
    """重置機器人資料和計數器"""
    module = get_edge_ui_module()
    module._local_robots.clear()
    module._robot_health_history.clear()
    module._robot_id_counter = 0


class TestEdgeUIRobotManagement:
    """機器人管理相關 API 測試"""

    def test_register_local_robot(self):
        """測試註冊本地機器人"""
        from src.robot_service.electron.edge_ui import (
            register_local_robot,
            get_local_robots,
        )
        
        # 清空現有資料
        reset_robot_data()
        
        robot_data = {
            'name': 'Test Robot',
            'type': 'humanoid',
            'location': 'Lab A',
        }
        
        robot = register_local_robot(robot_data)
        
        assert robot['name'] == 'Test Robot'
        assert robot['type'] == 'humanoid'
        assert robot['type_display'] == '人形機器人'
        assert robot['icon'] == '🤖'
        assert robot['location'] == 'Lab A'
        assert robot['status'] == 'idle'
        assert robot['battery'] == 100
        assert robot['connected'] is False
        assert robot['health_status'] == 'unknown'
        assert 'created_at' in robot
        assert 'updated_at' in robot
        assert len(robot['capabilities']) > 0
        
        # 確認加入列表
        robots = get_local_robots()
        assert len(robots) == 1
        
    def test_register_robot_different_types(self):
        """測試不同類型機器人的註冊"""
        from src.robot_service.electron.edge_ui import (
            register_local_robot,
            ROBOT_TYPES,
        )
        
        reset_robot_data()
        
        test_cases = [
            ('agv', 'AGV 搬運車', '🚗'),
            ('arm', '機械手臂', '🦾'),
            ('drone', '無人機', '🚁'),
            ('other', '其他', '⚙️'),
        ]
        
        for robot_type, expected_display, expected_icon in test_cases:
            robot = register_local_robot({
                'name': f'Test {robot_type}',
                'type': robot_type,
            })
            
            assert robot['type'] == robot_type
            assert robot['type_display'] == expected_display
            assert robot['icon'] == expected_icon
            # 確認預設能力列表
            assert robot['capabilities'] == ROBOT_TYPES[robot_type]['default_capabilities']

    def test_get_local_robot(self):
        """測試取得單一機器人"""
        from src.robot_service.electron.edge_ui import (
            register_local_robot,
            get_local_robot,
        )
        
        reset_robot_data()
        
        robot = register_local_robot({'name': 'Test'})
        robot_id = robot['id']
        
        fetched = get_local_robot(robot_id)
        assert fetched is not None
        assert fetched['id'] == robot_id
        assert fetched['name'] == 'Test'
        
        # 測試不存在的機器人
        not_found = get_local_robot('non-existent')
        assert not_found is None

    def test_update_robot_status(self):
        """測試更新機器人狀態"""
        from src.robot_service.electron.edge_ui import (
            register_local_robot,
            update_robot_status,
        )
        
        reset_robot_data()
        
        robot = register_local_robot({'name': 'Test'})
        robot_id = robot['id']
        
        # 更新狀態
        updated = update_robot_status(robot_id, {
            'status': 'running',
            'battery': 75,
            'connected': True,
        })
        
        assert updated is not None
        assert updated['status'] == 'running'
        assert updated['battery'] == 75
        assert updated['connected'] is True
        assert 'updated_at' in updated
        assert updated['last_seen'] is not None
        
        # 測試更新不存在的機器人
        result = update_robot_status('non-existent', {'status': 'idle'})
        assert result is None

    def test_delete_local_robot(self):
        """測試刪除機器人"""
        from src.robot_service.electron.edge_ui import (
            register_local_robot,
            delete_local_robot,
            get_local_robot,
        )
        
        reset_robot_data()
        
        robot = register_local_robot({'name': 'Test'})
        robot_id = robot['id']
        
        # 確認存在
        assert get_local_robot(robot_id) is not None
        
        # 刪除
        result = delete_local_robot(robot_id)
        assert result is True
        
        # 確認已刪除
        assert get_local_robot(robot_id) is None
        
        # 再次刪除應該失敗
        result = delete_local_robot(robot_id)
        assert result is False


class TestRobotHealthCheck:
    """機器人健康檢查測試"""

    def test_perform_health_check_disconnected(self):
        """測試未連線機器人的健康檢查"""
        module = get_edge_ui_module()
        from src.robot_service.electron.edge_ui import (
            register_local_robot,
            perform_robot_health_check,
        )
        
        reset_robot_data()
        
        robot = register_local_robot({'name': 'Test'})
        robot_id = robot['id']
        
        health = perform_robot_health_check(robot_id)
        
        assert health['robot_id'] == robot_id
        assert health['connected'] is False
        assert health['status'] == 'disconnected'
        assert health['response_time_ms'] is None
        assert health['checks']['connectivity'] is False
        
        # 確認機器人狀態更新
        assert module._local_robots[robot_id]['health_status'] == 'disconnected'

    def test_perform_health_check_connected_healthy(self):
        """測試已連線且健康的機器人"""
        module = get_edge_ui_module()
        from src.robot_service.electron.edge_ui import (
            register_local_robot,
            update_robot_status,
            perform_robot_health_check,
        )
        
        reset_robot_data()
        
        robot = register_local_robot({'name': 'Test'})
        robot_id = robot['id']
        
        # 設定為已連線且電量充足
        update_robot_status(robot_id, {
            'connected': True,
            'battery': 80,
            'error_count': 0,
        })
        
        health = perform_robot_health_check(robot_id)
        
        assert health['status'] == 'healthy'
        assert health['checks']['connectivity'] is True
        assert health['checks']['battery_ok'] is True
        assert health['checks']['no_errors'] is True
        assert health['response_time_ms'] == 50
        
        # 確認機器人狀態更新
        assert module._local_robots[robot_id]['health_status'] == 'healthy'

    def test_perform_health_check_connected_warning(self):
        """測試已連線但有警告的機器人"""
        module = get_edge_ui_module()
        from src.robot_service.electron.edge_ui import (
            register_local_robot,
            update_robot_status,
            perform_robot_health_check,
        )
        
        reset_robot_data()
        
        robot = register_local_robot({'name': 'Test'})
        robot_id = robot['id']
        
        # 設定為已連線但電量低
        update_robot_status(robot_id, {
            'connected': True,
            'battery': 15,  # 低於 20%
        })
        
        health = perform_robot_health_check(robot_id)
        
        assert health['checks']['battery_ok'] is False
        assert health['status'] == 'warning'
        
        # 確認機器人狀態更新為警告
        assert module._local_robots[robot_id]['health_status'] == 'warning'

    def test_health_check_not_found(self):
        """測試不存在的機器人健康檢查"""
        from src.robot_service.electron.edge_ui import (
            perform_robot_health_check,
        )
        
        reset_robot_data()
        
        health = perform_robot_health_check('non-existent')
        
        assert health['status'] == 'not_found'
        assert health['robot_id'] == 'non-existent'

    def test_health_history(self):
        """測試健康檢查歷史記錄"""
        from src.robot_service.electron.edge_ui import (
            register_local_robot,
            perform_robot_health_check,
            get_robot_health_history,
        )
        
        reset_robot_data()
        
        robot = register_local_robot({'name': 'Test'})
        robot_id = robot['id']
        
        # 執行多次健康檢查
        for _ in range(5):
            perform_robot_health_check(robot_id)
        
        # 取得歷史
        history = get_robot_health_history(robot_id, limit=3)
        
        assert len(history) == 3
        
        # 確認是最近 3 條
        full_history = get_robot_health_history(robot_id, limit=10)
        assert len(full_history) == 5


class TestDashboardSummary:
    """儀表板摘要測試"""

    def test_empty_summary(self):
        """測試空儀表板摘要"""
        from src.robot_service.electron.edge_ui import (
            get_dashboard_summary,
        )
        
        reset_robot_data()
        
        summary = get_dashboard_summary()
        
        assert summary['total_robots'] == 0
        assert summary['connected'] == 0
        assert summary['disconnected'] == 0
        assert summary['healthy'] == 0
        assert summary['warning'] == 0
        assert summary['low_battery'] == 0
        assert summary['needs_attention'] == 0

    def test_summary_with_robots(self):
        """測試有機器人的儀表板摘要"""
        from src.robot_service.electron.edge_ui import (
            register_local_robot,
            update_robot_status,
            get_dashboard_summary,
        )
        
        reset_robot_data()
        
        # 註冊多個機器人
        robot1 = register_local_robot({'name': 'Robot1', 'type': 'humanoid'})
        robot2 = register_local_robot({'name': 'Robot2', 'type': 'agv'})
        robot3 = register_local_robot({'name': 'Robot3', 'type': 'humanoid'})
        
        # 設定不同狀態
        update_robot_status(robot1['id'], {
            'connected': True,
            'health_status': 'healthy',
        })
        update_robot_status(robot2['id'], {
            'connected': True,
            'health_status': 'warning',
            'battery': 15,
        })
        update_robot_status(robot3['id'], {
            'connected': False,
            'health_status': 'disconnected',
        })
        
        summary = get_dashboard_summary()
        
        assert summary['total_robots'] == 3
        assert summary['connected'] == 2
        assert summary['disconnected'] == 1
        assert summary['healthy'] == 1
        assert summary['warning'] == 1
        assert summary['low_battery'] == 1
        # needs_attention 是不重複計數，robot2 同時是 warning 和 low_battery，只計 1 次
        assert summary['needs_attention'] == 1
        
        # 檢查類型統計
        assert summary['by_type']['humanoid'] == 2
        assert summary['by_type']['agv'] == 1


class TestRobotTypes:
    """機器人類型測試"""

    def test_robot_types_defined(self):
        """測試機器人類型定義"""
        from src.robot_service.electron.edge_ui import ROBOT_TYPES
        
        # 確認預定義類型存在
        assert 'humanoid' in ROBOT_TYPES
        assert 'agv' in ROBOT_TYPES
        assert 'arm' in ROBOT_TYPES
        assert 'drone' in ROBOT_TYPES
        assert 'other' in ROBOT_TYPES
        
        # 確認每個類型有必要屬性
        for robot_type, info in ROBOT_TYPES.items():
            assert 'display_name' in info
            assert 'icon' in info
            assert 'default_capabilities' in info
            assert isinstance(info['default_capabilities'], list)


class TestFlaskAPIEndpoints:
    """Flask API 端點測試"""

    @pytest.fixture
    def client(self):
        """建立測試客戶端"""
        from prometheus_client import REGISTRY
        from src.robot_service.electron.edge_ui import _local_robots, _robot_health_history
        
        # 清空資料
        _local_robots.clear()
        _robot_health_history.clear()
        
        # 清理 Prometheus 指標（避免重複註冊錯誤）
        collectors_to_remove = []
        for collector in REGISTRY._names_to_collectors.values():
            collectors_to_remove.append(collector)
        for collector in collectors_to_remove:
            try:
                REGISTRY.unregister(collector)
            except (ValueError, KeyError):
                # ValueError: collector 尚未註冊時拋出
                # KeyError: collector 名稱不存在時拋出
                # 這是預期情境，可安全忽略
                pass
        
        from src.robot_service.electron.flask_adapter import create_flask_app
        from src.robot_service.service_manager import ServiceManager
        
        # 建立 Flask 應用
        service_manager = ServiceManager()
        app = create_flask_app(
            service_manager=service_manager,
            app_token='test-token',
            enable_edge_ui=True,
        )
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            yield client

    def test_get_robots_empty(self, client):
        """測試取得空機器人列表"""
        response = client.get('/api/edge/robots')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['robots'] == []
        assert data['count'] == 0

    def test_register_robot_api(self, client):
        """測試註冊機器人 API"""
        response = client.post('/api/edge/robots', json={
            'name': 'Test Robot',
            'type': 'humanoid',
            'location': 'Lab A',
        })
        
        assert response.status_code == 201
        
        data = response.get_json()
        assert data['success'] is True
        assert data['robot']['name'] == 'Test Robot'
        assert data['robot']['type'] == 'humanoid'

    def test_get_robot_api(self, client):
        """測試取得單一機器人 API"""
        # 先註冊
        reg_response = client.post('/api/edge/robots', json={
            'name': 'Test Robot',
        })
        robot_id = reg_response.get_json()['robot']['id']
        
        # 取得
        response = client.get(f'/api/edge/robots/{robot_id}')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['robot']['id'] == robot_id
        
        # 測試不存在的機器人
        response = client.get('/api/edge/robots/non-existent')
        assert response.status_code == 404

    def test_delete_robot_api(self, client):
        """測試刪除機器人 API"""
        # 先註冊
        reg_response = client.post('/api/edge/robots', json={
            'name': 'Test Robot',
        })
        robot_id = reg_response.get_json()['robot']['id']
        
        # 刪除
        response = client.delete(f'/api/edge/robots/{robot_id}')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        
        # 確認已刪除
        response = client.get(f'/api/edge/robots/{robot_id}')
        assert response.status_code == 404

    def test_robot_health_api(self, client):
        """測試機器人健康檢查 API"""
        # 先註冊
        reg_response = client.post('/api/edge/robots', json={
            'name': 'Test Robot',
        })
        robot_id = reg_response.get_json()['robot']['id']
        
        # 健康檢查
        response = client.get(f'/api/edge/robots/{robot_id}/health')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'health' in data
        assert data['health']['robot_id'] == robot_id

    def test_robot_health_history_api(self, client):
        """測試機器人健康歷史 API"""
        # 先註冊
        reg_response = client.post('/api/edge/robots', json={
            'name': 'Test Robot',
        })
        robot_id = reg_response.get_json()['robot']['id']
        
        # 執行幾次健康檢查
        for _ in range(3):
            client.get(f'/api/edge/robots/{robot_id}/health')
        
        # 取得歷史
        response = client.get(f'/api/edge/robots/{robot_id}/health/history?limit=2')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['robot_id'] == robot_id
        assert len(data['history']) == 2

    def test_robot_health_history_api_limit_validation(self, client):
        """測試機器人健康歷史 API 的 limit 參數驗證"""
        # 先註冊
        reg_response = client.post('/api/edge/robots', json={
            'name': 'Test Robot',
        })
        robot_id = reg_response.get_json()['robot']['id']
        
        # 測試負數 limit
        response = client.get(f'/api/edge/robots/{robot_id}/health/history?limit=-1')
        assert response.status_code == 400
        assert 'error' in response.get_json()
        
        # 測試超大 limit（應該被截斷）
        response = client.get(f'/api/edge/robots/{robot_id}/health/history?limit=1000')
        assert response.status_code == 200

    def test_dashboard_summary_api(self, client):
        """測試儀表板摘要 API"""
        # 先註冊幾個機器人
        client.post('/api/edge/robots', json={'name': 'Robot1'})
        client.post('/api/edge/robots', json={'name': 'Robot2'})
        
        response = client.get('/api/edge/dashboard/summary')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'summary' in data
        assert data['summary']['total_robots'] == 2

    def test_robot_types_api(self, client):
        """測試機器人類型 API"""
        response = client.get('/api/edge/robot-types')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'types' in data
        assert data['count'] == 5  # 5 種類型
        
        # 確認類型資料正確
        humanoid = next(t for t in data['types'] if t['id'] == 'humanoid')
        assert humanoid['display_name'] == '人形機器人'
        assert humanoid['icon'] == '🤖'

    def test_update_robot_status_api(self, client):
        """測試更新機器人狀態 API"""
        # 先註冊
        reg_response = client.post('/api/edge/robots', json={
            'name': 'Test Robot',
        })
        robot_id = reg_response.get_json()['robot']['id']
        
        # 更新狀態
        response = client.put(f'/api/edge/robots/{robot_id}/status', json={
            'status': 'running',
            'battery': 50,
            'connected': True,
        })
        
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert data['robot']['status'] == 'running'
        assert data['robot']['battery'] == 50
        assert data['robot']['connected'] is True

    def test_robot_capabilities_api(self, client):
        """測試機器人能力 API"""
        # 先註冊
        reg_response = client.post('/api/edge/robots', json={
            'name': 'Test Robot',
            'type': 'humanoid',
        })
        robot_id = reg_response.get_json()['robot']['id']
        
        # 取得能力
        response = client.get(f'/api/edge/robots/{robot_id}/capabilities')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['robot_id'] == robot_id
        assert len(data['capabilities']) > 0
        assert 'go_forward' in data['capabilities']
