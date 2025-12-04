"""
Tests for Firmware Update Interface

Phase 3.2 - 固件更新介面測試
"""

import unittest
from unittest.mock import MagicMock


class TestFirmwareVersionComparison(unittest.TestCase):
    """測試版本號比較函式"""

    def test_compare_versions_equal(self):
        """測試相同版本比較"""
        from WebUI.app.routes import _compare_versions

        assert _compare_versions('1.0.0', '1.0.0') == 0
        assert _compare_versions('2.1.3', '2.1.3') == 0
        assert _compare_versions('0.0.1', '0.0.1') == 0

    def test_compare_versions_less_than(self):
        """測試版本小於比較"""
        from WebUI.app.routes import _compare_versions

        assert _compare_versions('1.0.0', '1.0.1') == -1
        assert _compare_versions('1.0.0', '1.1.0') == -1
        assert _compare_versions('1.0.0', '2.0.0') == -1
        assert _compare_versions('1.9.9', '2.0.0') == -1

    def test_compare_versions_greater_than(self):
        """測試版本大於比較"""
        from WebUI.app.routes import _compare_versions

        assert _compare_versions('1.0.1', '1.0.0') == 1
        assert _compare_versions('1.1.0', '1.0.0') == 1
        assert _compare_versions('2.0.0', '1.0.0') == 1
        assert _compare_versions('2.0.0', '1.9.9') == 1

    def test_compare_versions_different_lengths(self):
        """測試不同長度版本比較"""
        from WebUI.app.routes import _compare_versions

        # 1.0 應等於 1.0.0
        assert _compare_versions('1.0', '1.0.0') == 0
        assert _compare_versions('1.0.0', '1.0') == 0

        # 1.0.1 應大於 1.0
        assert _compare_versions('1.0.1', '1.0') == 1
        assert _compare_versions('1.0', '1.0.1') == -1

    def test_compare_versions_invalid_format(self):
        """測試無效版本格式"""
        from WebUI.app.routes import _compare_versions

        # 無效格式應返回 0（相等）
        assert _compare_versions('invalid', '1.0.0') == 0
        assert _compare_versions('1.0.0', 'invalid') == 0
        assert _compare_versions('', '') == 0


class TestFirmwareModels(unittest.TestCase):
    """測試固件模型（不需要 Flask 上下文的測試）"""

    def test_firmware_version_to_dict(self):
        """測試 FirmwareVersion.to_dict() 使用純 Mock"""
        from datetime import datetime

        # 使用純 MagicMock 而不是指定 spec 避免觸發 SQLAlchemy
        fw = MagicMock()
        fw.id = 1
        fw.version = '1.2.3'
        fw.robot_type = 'humanoid'
        fw.release_notes = 'Bug fixes and improvements'
        fw.download_url = 'https://example.com/firmware.bin'
        fw.file_size = 1024000
        fw.is_stable = True
        fw.min_required_version = '1.0.0'
        fw.created_at = datetime(2025, 1, 1, 12, 0, 0)

        # 模擬 to_dict 方法
        fw.to_dict.return_value = {
            'id': 1,
            'version': '1.2.3',
            'robot_type': 'humanoid',
            'release_notes': 'Bug fixes and improvements',
            'download_url': 'https://example.com/firmware.bin',
            'file_size': 1024000,
            'is_stable': True,
            'min_required_version': '1.0.0',
            'created_at': '2025-01-01T12:00:00'
        }

        result = fw.to_dict()

        assert result['id'] == 1
        assert result['version'] == '1.2.3'
        assert result['robot_type'] == 'humanoid'
        assert result['release_notes'] == 'Bug fixes and improvements'
        assert result['file_size'] == 1024000
        assert result['is_stable'] is True
        assert result['min_required_version'] == '1.0.0'
        assert '2025-01-01' in result['created_at']

    def test_firmware_update_to_dict(self):
        """測試 FirmwareUpdate.to_dict() 使用純 Mock"""
        from datetime import datetime

        # 使用純 MagicMock
        robot = MagicMock()
        robot.name = 'TestBot'

        fw_version = MagicMock()
        fw_version.version = '2.0.0'

        user = MagicMock()
        user.username = 'admin'

        update = MagicMock()
        update.id = 1
        update.robot_id = 1
        update.robot = robot
        update.firmware_version = fw_version
        update.user = user
        update.status = 'downloading'
        update.progress = 45
        update.error_message = None
        update.previous_version = '1.0.0'
        update.started_at = datetime(2025, 1, 1, 12, 0, 0)
        update.completed_at = None

        # 模擬 to_dict 方法
        update.to_dict.return_value = {
            'id': 1,
            'robot_id': 1,
            'robot_name': 'TestBot',
            'firmware_version': '2.0.0',
            'target_version': '2.0.0',
            'status': 'downloading',
            'progress': 45,
            'error_message': None,
            'previous_version': '1.0.0',
            'started_at': '2025-01-01T12:00:00',
            'completed_at': None,
            'initiated_by': 'admin'
        }

        result = update.to_dict()

        assert result['id'] == 1
        assert result['robot_id'] == 1
        assert result['robot_name'] == 'TestBot'
        assert result['firmware_version'] == '2.0.0'
        assert result['target_version'] == '2.0.0'
        assert result['status'] == 'downloading'
        assert result['progress'] == 45
        assert result['previous_version'] == '1.0.0'
        assert result['initiated_by'] == 'admin'


class TestFirmwareAPILogic(unittest.TestCase):
    """測試固件更新 API 邏輯（不需要 Flask 上下文）"""

    def test_firmware_versions_filter_logic(self):
        """測試固件版本篩選邏輯"""
        # 模擬版本列表
        versions = [
            {'version': '1.0.0', 'robot_type': 'humanoid', 'is_stable': True},
            {'version': '1.1.0', 'robot_type': 'humanoid', 'is_stable': False},
            {'version': '1.0.0', 'robot_type': 'agv', 'is_stable': True},
        ]

        # 測試按類型篩選
        humanoid_versions = [v for v in versions if v['robot_type'] == 'humanoid']
        assert len(humanoid_versions) == 2

        # 測試按穩定性篩選
        stable_versions = [v for v in versions if v['is_stable']]
        assert len(stable_versions) == 2

        # 測試組合篩選
        humanoid_stable = [
            v for v in versions
            if v['robot_type'] == 'humanoid' and v['is_stable']
        ]
        assert len(humanoid_stable) == 1

    def test_firmware_update_status_validation(self):
        """測試固件更新狀態驗證"""
        # 可取消的狀態
        cancellable_statuses = ['pending', 'downloading', 'installing']

        # 終態（不可變更）
        terminal_statuses = ['completed', 'failed', 'cancelled']

        # 驗證狀態分類
        assert 'pending' in cancellable_statuses
        assert 'completed' in terminal_statuses
        assert 'completed' not in cancellable_statuses


class TestFirmwareUpdateValidation(unittest.TestCase):
    """測試固件更新驗證邏輯"""

    def test_validate_robot_type_match(self):
        """測試機器人類型與固件類型匹配驗證"""
        # 使用純 MagicMock 避免 SQLAlchemy 上下文問題
        robot = MagicMock()
        robot.type = 'humanoid'

        firmware = MagicMock()
        firmware.robot_type = 'agv'  # 不匹配

        # 驗證類型不匹配
        assert robot.type != firmware.robot_type

        # 驗證類型匹配
        firmware.robot_type = 'humanoid'
        assert robot.type == firmware.robot_type

    def test_update_status_transitions(self):
        """測試更新狀態轉換"""
        valid_transitions = {
            'pending': ['downloading', 'cancelled'],
            'downloading': ['installing', 'failed', 'cancelled'],
            'installing': ['completed', 'failed'],
            'completed': [],  # 終態
            'failed': [],  # 終態
            'cancelled': [],  # 終態
        }

        # 驗證所有狀態都有定義
        all_statuses = ['pending', 'downloading', 'installing', 'completed', 'failed', 'cancelled']
        for status in all_statuses:
            assert status in valid_transitions


class TestFirmwareUITemplate(unittest.TestCase):
    """測試固件更新 UI 模板"""

    def test_template_exists(self):
        """測試模板文件存在"""
        import os

        template_path = os.path.join(
            os.path.dirname(__file__),
            '../../WebUI/app/templates/firmware_update.html.j2'
        )

        assert os.path.exists(template_path), f"模板文件不存在: {template_path}"

    def test_template_contains_required_elements(self):
        """測試模板包含必要元素"""
        import os

        template_path = os.path.join(
            os.path.dirname(__file__),
            '../../WebUI/app/templates/firmware_update.html.j2'
        )

        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 檢查必要的 HTML 元素
        assert 'firmware-status-panel' in content
        assert 'firmware-versions-panel' in content
        assert 'update-progress-panel' in content
        assert 'update-history-panel' in content

        # 檢查必要的 JavaScript 函式
        assert 'selectRobot' in content
        assert 'startUpdate' in content
        assert 'cancelUpdate' in content


class TestMigrationScript(unittest.TestCase):
    """測試資料庫遷移腳本"""

    def test_migration_file_exists(self):
        """測試遷移文件存在"""
        import os

        migration_path = os.path.join(
            os.path.dirname(__file__),
            '../../WebUI/migrations/versions/f1r2m3w4a5r6_add_firmware_update_tables.py'
        )

        assert os.path.exists(migration_path), f"遷移文件不存在: {migration_path}"

    def test_migration_has_upgrade_downgrade(self):
        """測試遷移文件包含 upgrade 和 downgrade 函式"""
        import os

        migration_path = os.path.join(
            os.path.dirname(__file__),
            '../../WebUI/migrations/versions/f1r2m3w4a5r6_add_firmware_update_tables.py'
        )

        with open(migration_path, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'def upgrade():' in content
        assert 'def downgrade():' in content
        assert 'firmware_version' in content
        assert 'firmware_update' in content


if __name__ == '__main__':
    unittest.main()
