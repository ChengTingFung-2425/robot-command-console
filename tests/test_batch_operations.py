"""
Tests for Batch Operations Module

批次操作模組的單元測試。
"""

import pytest
import json
import tempfile
from pathlib import Path

from robot_service.batch import (
    BatchParser,
    BatchSpec,
    BatchCommand,
    BatchOptions,
    ExecutionMode,
    CommandStatus,
    BatchStatus,
    ProgressTracker,
    ResultExporter,
    BatchResult,
    CommandResult
)
from common.datetime_utils import utc_now


class TestBatchModels:
    """測試批次資料模型"""
    
    def test_batch_command_creation(self):
        """測試 BatchCommand 創建"""
        cmd = BatchCommand(
            robot_id="robot-001",
            action="stand",
            params={"duration_ms": 3000},
            priority="high",
            timeout_ms=5000
        )
        
        assert cmd.robot_id == "robot-001"
        assert cmd.action == "stand"
        assert cmd.params["duration_ms"] == 3000
        assert cmd.priority == "high"
        assert cmd.timeout_ms == 5000
    
    def test_batch_command_to_dict(self):
        """測試 BatchCommand 轉換為字典"""
        cmd = BatchCommand(
            robot_id="robot-001",
            action="wave",
            params={},
            priority="normal"
        )
        
        data = cmd.to_dict()
        assert isinstance(data, dict)
        assert data["robot_id"] == "robot-001"
        assert data["action"] == "wave"
    
    def test_batch_command_from_dict(self):
        """測試從字典創建 BatchCommand"""
        data = {
            "robot_id": "robot-002",
            "action": "bow",
            "params": {},
            "priority": "low",
            "timeout_ms": 8000
        }
        
        cmd = BatchCommand.from_dict(data)
        assert cmd.robot_id == "robot-002"
        assert cmd.action == "bow"
        assert cmd.priority == "low"
        assert cmd.timeout_ms == 8000
    
    def test_batch_options_defaults(self):
        """測試 BatchOptions 預設值"""
        opts = BatchOptions()
        
        assert opts.execution_mode == ExecutionMode.GROUPED
        assert opts.stop_on_error is False
        assert opts.retry_on_failure == 0
        assert opts.max_parallel == 10
        assert opts.dry_run is False
    
    def test_batch_spec_creation(self):
        """測試 BatchSpec 創建"""
        spec = BatchSpec(
            batch_id="test-001",
            description="Test batch",
            robots=["robot-001"],
            commands=[
                BatchCommand(robot_id="robot-001", action="stand")
            ]
        )
        
        assert spec.batch_id == "test-001"
        assert len(spec.commands) == 1
        assert len(spec.robots) == 1
    
    def test_batch_result_update_statistics(self):
        """測試 BatchResult 統計更新"""
        result = BatchResult(
            batch_id="test-001",
            status=BatchStatus.RUNNING,
            start_time=utc_now()
        )
        
        # 添加成功指令
        result.commands.append(CommandResult(
            command_id="cmd-1",
            trace_id="trace-1",
            robot_id="robot-001",
            action="stand",
            status=CommandStatus.SUCCESS,
            start_time=utc_now()
        ))
        
        # 添加失敗指令
        result.commands.append(CommandResult(
            command_id="cmd-2",
            trace_id="trace-2",
            robot_id="robot-001",
            action="wave",
            status=CommandStatus.FAILED,
            start_time=utc_now(),
            error="Test error"
        ))
        
        result.end_time = utc_now()
        result.update_statistics()
        
        assert result.total_commands == 2
        assert result.successful == 1
        assert result.failed == 1
        assert result.status == BatchStatus.COMPLETED_WITH_ERRORS


class TestBatchParser:
    """測試批次解析器"""
    
    def test_parse_json_file(self):
        """測試解析 JSON 檔案"""
        parser = BatchParser()
        batch = parser.parse_file("examples/batches/demo_sequence.json")
        
        assert batch.batch_id == "demo-001"
        assert len(batch.commands) == 5
        assert batch.options.execution_mode == ExecutionMode.GROUPED
    
    def test_parse_yaml_file(self):
        """測試解析 YAML 檔案"""
        parser = BatchParser()
        batch = parser.parse_file("examples/batches/test_basic.yaml")
        
        assert batch.batch_id == "test-basic-actions"
        assert len(batch.commands) == 5
        assert batch.options.execution_mode == ExecutionMode.SEQUENTIAL
    
    def test_parse_csv_file(self):
        """測試解析 CSV 檔案"""
        parser = BatchParser()
        batch = parser.parse_file("examples/batches/simple_batch.csv")
        
        assert batch.batch_id == "simple_batch"
        assert len(batch.commands) == 5
    
    def test_parse_json_string(self):
        """測試解析 JSON 字串"""
        parser = BatchParser()
        json_str = '''
        {
            "batch_id": "test-001",
            "commands": [
                {"robot_id": "robot-001", "action": "stand"}
            ]
        }
        '''
        
        batch = parser.parse_string(json_str, format="json")
        assert batch.batch_id == "test-001"
        assert len(batch.commands) == 1
    
    def test_validate_valid_batch(self):
        """測試驗證有效批次"""
        parser = BatchParser()
        batch = BatchSpec(
            batch_id="test-001",
            commands=[
                BatchCommand(robot_id="robot-001", action="stand")
            ]
        )
        
        # 應該不拋出異常
        assert parser.validate(batch) is True
    
    def test_validate_missing_batch_id(self):
        """測試驗證缺少 batch_id"""
        parser = BatchParser()
        batch = BatchSpec(
            batch_id="",
            commands=[
                BatchCommand(robot_id="robot-001", action="stand")
            ]
        )
        
        with pytest.raises(ValueError, match="batch_id is required"):
            parser.validate(batch)
    
    def test_validate_no_commands(self):
        """測試驗證無指令"""
        parser = BatchParser()
        batch = BatchSpec(
            batch_id="test-001",
            commands=[]
        )
        
        with pytest.raises(ValueError, match="At least one command is required"):
            parser.validate(batch)
    
    def test_validate_invalid_priority(self):
        """測試驗證無效優先級"""
        parser = BatchParser()
        batch = BatchSpec(
            batch_id="test-001",
            commands=[
                BatchCommand(
                    robot_id="robot-001",
                    action="stand",
                    priority="invalid"
                )
            ]
        )
        
        with pytest.raises(ValueError, match="priority must be one of"):
            parser.validate(batch)


class TestProgressTracker:
    """測試進度追蹤器"""
    
    def test_start_batch(self):
        """測試開始追蹤批次"""
        tracker = ProgressTracker()
        tracker.start_batch("test-001", 10)
        
        assert tracker.batch_id == "test-001"
        assert tracker.total_commands == 10
        assert tracker.completed == 0
    
    def test_update_progress(self):
        """測試更新進度"""
        tracker = ProgressTracker()
        tracker.start_batch("test-001", 5)
        
        tracker.update_progress("cmd-1", CommandStatus.SUCCESS)
        tracker.update_progress("cmd-2", CommandStatus.FAILED)
        tracker.update_progress("cmd-3", CommandStatus.SUCCESS)
        
        assert tracker.completed == 3
        assert tracker.successful == 2
        assert tracker.failed == 1
    
    def test_get_summary(self):
        """測試取得摘要"""
        tracker = ProgressTracker()
        tracker.start_batch("test-001", 10)
        
        tracker.update_progress("cmd-1", CommandStatus.SUCCESS)
        tracker.update_progress("cmd-2", CommandStatus.SUCCESS)
        
        summary = tracker.get_summary()
        
        assert summary["batch_id"] == "test-001"
        assert summary["total_commands"] == 10
        assert summary["completed"] == 2
        assert summary["successful"] == 2
        assert summary["pending"] == 8
        assert summary["progress_percentage"] == 20
    
    def test_render_progress_bar(self):
        """測試渲染進度條"""
        tracker = ProgressTracker()
        tracker.start_batch("test-001", 10)
        
        # 完成 5 個指令
        for i in range(5):
            tracker.update_progress(f"cmd-{i}", CommandStatus.SUCCESS)
        
        bar = tracker.render_progress_bar(width=20)
        
        assert "[" in bar
        assert "]" in bar
        assert "50%" in bar
    
    def test_is_complete(self):
        """測試是否完成"""
        tracker = ProgressTracker()
        tracker.start_batch("test-001", 3)
        
        assert tracker.is_complete() is False
        
        tracker.update_progress("cmd-1", CommandStatus.SUCCESS)
        tracker.update_progress("cmd-2", CommandStatus.SUCCESS)
        
        assert tracker.is_complete() is False
        
        tracker.update_progress("cmd-3", CommandStatus.SUCCESS)
        
        assert tracker.is_complete() is True


class TestResultExporter:
    """測試結果輸出器"""
    
    def test_export_json(self):
        """測試輸出 JSON"""
        exporter = ResultExporter()
        
        result = BatchResult(
            batch_id="test-001",
            status=BatchStatus.COMPLETED,
            start_time=utc_now(),
            end_time=utc_now()
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name
        
        try:
            exporter.export_json(result, output_path)
            
            # 驗證檔案存在且可讀取
            with open(output_path, 'r') as f:
                data = json.load(f)
            
            assert data["batch_id"] == "test-001"
            assert data["status"] == "completed"
        finally:
            Path(output_path).unlink(missing_ok=True)
    
    def test_export_csv(self):
        """測試輸出 CSV"""
        exporter = ResultExporter()
        
        result = BatchResult(
            batch_id="test-001",
            status=BatchStatus.COMPLETED,
            start_time=utc_now(),
            end_time=utc_now(),
            commands=[
                CommandResult(
                    command_id="cmd-1",
                    trace_id="trace-1",
                    robot_id="robot-001",
                    action="stand",
                    status=CommandStatus.SUCCESS,
                    start_time=utc_now()
                )
            ]
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_path = f.name
        
        try:
            exporter.export_csv(result, output_path)
            
            # 驗證檔案存在且可讀取
            with open(output_path, 'r') as f:
                content = f.read()
            
            assert "command_id" in content
            assert "cmd-1" in content
            assert "robot-001" in content
        finally:
            Path(output_path).unlink(missing_ok=True)
    
    def test_export_text(self):
        """測試輸出文字報告"""
        exporter = ResultExporter()
        
        result = BatchResult(
            batch_id="test-001",
            status=BatchStatus.COMPLETED,
            start_time=utc_now(),
            end_time=utc_now()
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            output_path = f.name
        
        try:
            exporter.export_text(result, output_path)
            
            # 驗證檔案存在且可讀取
            with open(output_path, 'r') as f:
                content = f.read()
            
            assert "Batch Execution Report" in content
            assert "test-001" in content
        finally:
            Path(output_path).unlink(missing_ok=True)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
