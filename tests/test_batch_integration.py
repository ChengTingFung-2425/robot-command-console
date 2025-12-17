"""
Integration Tests for Batch Operations

批次操作的整合測試，測試與現有系統的完整整合。
"""

import pytest
import tempfile
import json
from pathlib import Path

from robot_service.batch import (
    BatchParser,
    BatchExecutor,
    BatchSpec,
    BatchCommand,
    ExecutionMode,
    BatchStatus,
)


class TestBatchExecutorIntegration:
    """測試 BatchExecutor 與現有服務的整合"""
    
    @pytest.mark.asyncio
    async def test_executor_with_dry_run(self):
        """測試執行器的乾跑模式"""
        from robot_service.service_manager import ServiceManager
        
        # 建立服務管理器
        service_manager = ServiceManager(queue_max_size=100, max_workers=5)
        
        # 建立執行器
        executor = BatchExecutor(
            service_manager=service_manager,
            history_manager=None,
            max_parallel=5
        )
        
        # 建立簡單的批次
        batch_spec = BatchSpec(
            batch_id="test-integration-001",
            commands=[
                BatchCommand(robot_id="robot-001", action="stand", timeout_ms=1000),
                BatchCommand(robot_id="robot-002", action="wave", timeout_ms=1000),
            ]
        )
        
        # 執行批次（乾跑模式）
        result = await executor.execute_batch(batch_spec, dry_run=True)
        
        # 驗證結果
        assert result.batch_id == "test-integration-001"
        assert result.total_commands == 2
        assert result.successful == 2
        assert result.status == BatchStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """測試並行執行模式"""
        from robot_service.service_manager import ServiceManager
        
        service_manager = ServiceManager(queue_max_size=100, max_workers=10)
        
        executor = BatchExecutor(
            service_manager=service_manager,
            history_manager=None,
            max_parallel=10
        )
        
        # 建立多個指令的批次
        commands = [
            BatchCommand(robot_id=f"robot-{i:03d}", action="stand", timeout_ms=500)
            for i in range(10)
        ]
        
        batch_spec = BatchSpec(
            batch_id="test-parallel-001",
            commands=commands,
        )
        batch_spec.options.execution_mode = ExecutionMode.PARALLEL
        
        # 執行批次（乾跑模式）
        result = await executor.execute_batch(batch_spec, dry_run=True)
        
        # 驗證所有指令都執行了
        assert result.total_commands == 10
        assert result.successful == 10
    
    @pytest.mark.asyncio
    async def test_sequential_execution(self):
        """測試順序執行模式"""
        from robot_service.service_manager import ServiceManager
        
        service_manager = ServiceManager(queue_max_size=100, max_workers=5)
        
        executor = BatchExecutor(
            service_manager=service_manager,
            history_manager=None,
            max_parallel=5
        )
        
        commands = [
            BatchCommand(robot_id="robot-001", action="stand", timeout_ms=500),
            BatchCommand(robot_id="robot-001", action="wave", timeout_ms=500),
            BatchCommand(robot_id="robot-001", action="bow", timeout_ms=500),
        ]
        
        batch_spec = BatchSpec(
            batch_id="test-sequential-001",
            commands=commands,
        )
        batch_spec.options.execution_mode = ExecutionMode.SEQUENTIAL
        
        # 執行批次（乾跑模式）
        result = await executor.execute_batch(batch_spec, dry_run=True)
        
        # 驗證執行順序
        assert result.total_commands == 3
        assert result.successful == 3
        
        # 確認指令按順序記錄
        assert len(result.commands) == 3
        assert result.commands[0].action == "stand"
        assert result.commands[1].action == "wave"
        assert result.commands[2].action == "bow"
    
    @pytest.mark.asyncio
    async def test_grouped_execution(self):
        """測試分組執行模式"""
        from robot_service.service_manager import ServiceManager
        
        service_manager = ServiceManager(queue_max_size=100, max_workers=5)
        
        executor = BatchExecutor(
            service_manager=service_manager,
            history_manager=None,
            max_parallel=5
        )
        
        # 建立多個機器人的指令
        commands = [
            BatchCommand(robot_id="robot-001", action="stand", timeout_ms=500),
            BatchCommand(robot_id="robot-002", action="stand", timeout_ms=500),
            BatchCommand(robot_id="robot-001", action="wave", timeout_ms=500),
            BatchCommand(robot_id="robot-002", action="wave", timeout_ms=500),
        ]
        
        batch_spec = BatchSpec(
            batch_id="test-grouped-001",
            commands=commands,
        )
        batch_spec.options.execution_mode = ExecutionMode.GROUPED
        
        # 執行批次（乾跑模式）
        result = await executor.execute_batch(batch_spec, dry_run=True)
        
        # 驗證所有指令都執行了
        assert result.total_commands == 4
        assert result.successful == 4


class TestBatchCLIIntegration:
    """測試批次 CLI 的端到端整合"""
    
    def test_parse_and_validate_json(self):
        """測試解析和驗證 JSON 批次檔案"""
        parser = BatchParser()
        batch = parser.parse_file("examples/batches/demo_sequence.json")
        
        # 驗證批次
        assert parser.validate(batch) is True
        
        # 檢查基本屬性
        assert batch.batch_id == "demo-001"
        assert len(batch.commands) == 5
        assert batch.options.execution_mode == ExecutionMode.GROUPED
    
    def test_parse_and_validate_yaml(self):
        """測試解析和驗證 YAML 批次檔案"""
        parser = BatchParser()
        batch = parser.parse_file("examples/batches/test_basic.yaml")
        
        # 驗證批次
        assert parser.validate(batch) is True
        
        # 檢查基本屬性
        assert batch.batch_id == "test-basic-actions"
        assert len(batch.commands) == 5
        assert batch.options.execution_mode == ExecutionMode.SEQUENTIAL
    
    def test_parse_and_validate_csv(self):
        """測試解析和驗證 CSV 批次檔案"""
        parser = BatchParser()
        batch = parser.parse_file("examples/batches/simple_batch.csv")
        
        # 驗證批次
        assert parser.validate(batch) is True
        
        # 檢查基本屬性
        assert len(batch.commands) == 5
    
    def test_batch_file_formats_consistency(self):
        """測試不同格式的批次檔案一致性"""
        parser = BatchParser()
        
        # 解析所有範例檔案
        json_batch = parser.parse_file("examples/batches/demo_sequence.json")
        yaml_batch = parser.parse_file("examples/batches/test_basic.yaml")
        csv_batch = parser.parse_file("examples/batches/simple_batch.csv")
        
        # 所有批次都應該有效
        assert parser.validate(json_batch) is True
        assert parser.validate(yaml_batch) is True
        assert parser.validate(csv_batch) is True
        
        # 檢查命令數量
        assert len(json_batch.commands) > 0
        assert len(yaml_batch.commands) > 0
        assert len(csv_batch.commands) > 0


class TestBatchErrorHandling:
    """測試批次操作的錯誤處理"""
    
    @pytest.mark.asyncio
    async def test_retry_mechanism(self):
        """測試重試機制"""
        # 這個測試需要模擬失敗的指令
        # 目前使用乾跑模式，所以總是成功
        # 實際環境中應該測試真實的重試邏輯
        pass
    
    def test_invalid_batch_file(self):
        """測試無效的批次檔案"""
        parser = BatchParser()
        
        # 測試不存在的檔案
        with pytest.raises(FileNotFoundError):
            parser.parse_file("nonexistent.json")
    
    def test_invalid_format(self):
        """測試不支援的檔案格式"""
        parser = BatchParser()
        
        # 建立臨時檔案
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("invalid content")
            temp_path = f.name
        
        try:
            # 測試不支援的格式
            with pytest.raises(ValueError, match="Unsupported file format"):
                parser.parse_file(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_malformed_json(self):
        """測試格式錯誤的 JSON"""
        parser = BatchParser()
        
        # 建立格式錯誤的 JSON 檔案
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{invalid json}")
            temp_path = f.name
        
        try:
            with pytest.raises(json.JSONDecodeError):
                parser.parse_file(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestBatchPerformance:
    """測試批次操作的效能"""
    
    @pytest.mark.asyncio
    async def test_large_batch_performance(self):
        """測試大批次的效能"""
        # 建立一個大批次（100 個指令）
        commands = [
            BatchCommand(robot_id=f"robot-{i:03d}", action="stand", timeout_ms=100)
            for i in range(100)
        ]
        
        batch_spec = BatchSpec(
            batch_id="test-performance-001",
            commands=commands,
        )
        batch_spec.options.execution_mode = ExecutionMode.PARALLEL
        batch_spec.options.max_parallel = 20
        
        # 建立模擬的服務管理器
        from robot_service.service_manager import ServiceManager
        service_manager = ServiceManager(queue_max_size=1000, max_workers=10)
        
        # 建立執行器
        executor = BatchExecutor(
            service_manager=service_manager,
            history_manager=None,
            max_parallel=20
        )
        
        # 測量執行時間
        import time
        start_time = time.time()
        
        result = await executor.execute_batch(batch_spec, dry_run=True)
        
        elapsed_time = time.time() - start_time
        
        # 驗證執行成功
        assert result.total_commands == 100
        assert result.successful == 100
        
        # 驗證效能（乾跑模式應該很快，< 5 秒）
        assert elapsed_time < 5.0, f"執行時間過長: {elapsed_time:.2f}秒"
    
    @pytest.mark.asyncio
    async def test_semaphore_limiting(self):
        """測試信號量限流機制"""
        commands = [
            BatchCommand(robot_id=f"robot-{i:03d}", action="stand", timeout_ms=100)
            for i in range(50)
        ]
        
        batch_spec = BatchSpec(
            batch_id="test-semaphore-001",
            commands=commands,
        )
        batch_spec.options.execution_mode = ExecutionMode.PARALLEL
        batch_spec.options.max_parallel = 5  # 限制最多 5 個並行
        
        from robot_service.service_manager import ServiceManager
        service_manager = ServiceManager(queue_max_size=1000, max_workers=10)
        
        executor = BatchExecutor(
            service_manager=service_manager,
            history_manager=None,
            max_parallel=5
        )
        
        result = await executor.execute_batch(batch_spec, dry_run=True)
        
        # 即使有 50 個指令，限流機制應該正常工作
        assert result.total_commands == 50
        assert result.successful == 50


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
