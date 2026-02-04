"""
Batch Executor

批次執行器，支援多工（mux）調度策略。
"""

import asyncio
import logging
import uuid
from typing import List, Dict, Optional, Any

from .models import (
    BatchSpec,
    BatchCommand,
    BatchResult,
    CommandResult,
    CommandStatus,
    BatchStatus,
    ExecutionMode,
    BatchOptions
)
from ..service_manager import ServiceManager
from ..command_history_manager import CommandHistoryManager
from ..queue import Message, MessagePriority
from common.datetime_utils import utc_now

logger = logging.getLogger(__name__)


class BatchExecutor:
    """
    批次執行器

    支援多種執行模式：
    - parallel: 所有指令並行執行
    - sequential: 所有指令順序執行
    - grouped: 按機器人分組，組內順序執行，組間並行
    """

    def __init__(
        self,
        service_manager: ServiceManager,
        history_manager: Optional[CommandHistoryManager] = None,
        max_parallel: int = 10
    ):
        """
        初始化批次執行器

        Args:
            service_manager: 服務管理器（用於發送指令到佇列）
            history_manager: 指令歷史管理器（可選）
            max_parallel: 最大並行數
        """
        self.service_manager = service_manager
        self.history_manager = history_manager
        self.max_parallel = max_parallel
        self._semaphore = asyncio.Semaphore(max_parallel)

    async def execute_batch(
        self,
        batch_spec: BatchSpec,
        dry_run: bool = False
    ) -> BatchResult:
        """
        執行批次

        Args:
            batch_spec: 批次規格
            dry_run: 乾跑模式（不實際執行）

        Returns:
            批次執行結果
        """
        logger.info(f"Executing batch: {batch_spec.batch_id}, "
                    f"mode={batch_spec.options.execution_mode.value}, "
                    f"dry_run={dry_run}")

        # 初始化批次結果
        batch_result = BatchResult(
            batch_id=batch_spec.batch_id,
            status=BatchStatus.RUNNING,
            start_time=utc_now(),
            metadata=batch_spec.metadata.copy()
        )

        # 為每個指令生成 ID
        for cmd in batch_spec.commands:
            if not cmd.command_id:
                cmd.command_id = f"cmd-{uuid.uuid4().hex[:8]}"
            if not cmd.trace_id:
                cmd.trace_id = f"trace-{uuid.uuid4().hex[:12]}"

        # 根據執行模式選擇策略
        mode = batch_spec.options.execution_mode

        try:
            if dry_run:
                results = await self._execute_dry_run(batch_spec.commands)
            elif mode == ExecutionMode.PARALLEL:
                results = await self._execute_parallel(
                    batch_spec.commands,
                    batch_spec.options
                )
            elif mode == ExecutionMode.SEQUENTIAL:
                results = await self._execute_sequential(
                    batch_spec.commands,
                    batch_spec.options
                )
            elif mode == ExecutionMode.GROUPED:
                results = await self._execute_grouped(
                    batch_spec.commands,
                    batch_spec.options
                )
            else:
                raise ValueError(f"Unknown execution mode: {mode}")

            batch_result.commands = results

        except Exception as e:
            logger.error(f"Batch execution failed: {e}", exc_info=True)
            batch_result.status = BatchStatus.FAILED
            batch_result.metadata["error"] = str(e)

        # 更新批次結束時間和統計
        batch_result.end_time = utc_now()
        batch_result.update_statistics()

        logger.info(f"Batch completed: {batch_spec.batch_id}, "
                    f"status={batch_result.status.value}, "
                    f"success={batch_result.successful}/{batch_result.total_commands}")

        return batch_result

    async def _execute_dry_run(
        self,
        commands: List[BatchCommand]
    ) -> List[CommandResult]:
        """
        乾跑模式（不實際執行，僅記錄）

        Args:
            commands: 指令列表

        Returns:
            模擬的指令結果列表
        """
        logger.info(f"Dry run: {len(commands)} commands")

        results = []
        for cmd in commands:
            result = CommandResult(
                command_id=cmd.command_id,
                trace_id=cmd.trace_id,
                robot_id=cmd.robot_id,
                action=cmd.action,
                status=CommandStatus.SUCCESS,
                start_time=utc_now(),
                end_time=utc_now(),
                duration_ms=0,
                result_data={"dry_run": True}
            )
            results.append(result)

        return results

    async def _execute_parallel(
        self,
        commands: List[BatchCommand],
        options: BatchOptions
    ) -> List[CommandResult]:
        """
        並行執行所有指令

        Args:
            commands: 指令列表
            options: 執行選項

        Returns:
            指令結果列表
        """
        logger.info(f"Parallel execution: {len(commands)} commands")

        tasks = [
            self._execute_single_command_with_limit(cmd, options)
            for cmd in commands
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 處理異常結果
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # 將異常轉換為失敗結果
                cmd = commands[i]
                result = CommandResult(
                    command_id=cmd.command_id,
                    trace_id=cmd.trace_id,
                    robot_id=cmd.robot_id,
                    action=cmd.action,
                    status=CommandStatus.FAILED,
                    start_time=utc_now(),
                    end_time=utc_now(),
                    error=str(result)
                )
            final_results.append(result)

        return final_results

    async def _execute_sequential(
        self,
        commands: List[BatchCommand],
        options: BatchOptions
    ) -> List[CommandResult]:
        """
        順序執行所有指令

        Args:
            commands: 指令列表
            options: 執行選項

        Returns:
            指令結果列表
        """
        logger.info(f"Sequential execution: {len(commands)} commands")

        results = []

        for cmd in commands:
            result = await self._execute_single_command(cmd, options)
            results.append(result)

            # 檢查是否需要停止
            if options.stop_on_error and result.status in [
                CommandStatus.FAILED,
                CommandStatus.TIMEOUT
            ]:
                logger.warning(f"Stopping due to error: {result.command_id}")
                # 將剩餘指令標記為已取消
                for remaining_cmd in commands[len(results):]:
                    cancelled_result = CommandResult(
                        command_id=remaining_cmd.command_id,
                        trace_id=remaining_cmd.trace_id,
                        robot_id=remaining_cmd.robot_id,
                        action=remaining_cmd.action,
                        status=CommandStatus.CANCELLED,
                        start_time=utc_now(),
                        end_time=utc_now(),
                        error="Cancelled due to previous error"
                    )
                    results.append(cancelled_result)
                break

            # 指令間延遲
            if options.delay_between_commands_ms > 0:
                await asyncio.sleep(options.delay_between_commands_ms / 1000.0)

        return results

    async def _execute_grouped(
        self,
        commands: List[BatchCommand],
        options: BatchOptions
    ) -> List[CommandResult]:
        """
        分組並行執行（組內順序執行，組間並行）

        按機器人 ID 分組，每組內的指令順序執行，不同組之間並行執行。

        Args:
            commands: 指令列表
            options: 執行選項

        Returns:
            指令結果列表
        """
        logger.info(f"Grouped execution: {len(commands)} commands")

        # 按機器人分組
        groups: Dict[str, List[BatchCommand]] = {}
        for cmd in commands:
            robot_id = cmd.robot_id
            if robot_id not in groups:
                groups[robot_id] = []
            groups[robot_id].append(cmd)

        logger.info(f"Grouped into {len(groups)} robot groups")

        # 每組順序執行，組間並行
        tasks = [
            self._execute_sequential(group_commands, options)
            for group_commands in groups.values()
        ]

        group_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合併結果
        all_results = []
        for group_result in group_results:
            if isinstance(group_result, Exception):
                logger.error(f"Group execution failed: {group_result}")
                continue
            all_results.extend(group_result)

        # 恢復原始順序（按 command_id）
        command_order = {cmd.command_id: i for i, cmd in enumerate(commands)}
        all_results.sort(key=lambda r: command_order.get(r.command_id, 999999))

        return all_results

    async def _execute_single_command_with_limit(
        self,
        command: BatchCommand,
        options: BatchOptions
    ) -> CommandResult:
        """
        使用信號量限制並行數執行單個指令

        Args:
            command: 批次指令
            options: 執行選項

        Returns:
            指令結果
        """
        async with self._semaphore:
            return await self._execute_single_command(command, options)

    async def _execute_single_command(
        self,
        command: BatchCommand,
        options: BatchOptions
    ) -> CommandResult:
        """
        執行單個指令（帶重試機制）

        Args:
            command: 批次指令
            options: 執行選項

        Returns:
            指令結果
        """
        start_time = utc_now()
        retry_count = 0
        last_error = None

        # 重試迴圈
        for attempt in range(options.retry_on_failure + 1):
            try:
                result = await self._dispatch_command(command)

                if result.status == CommandStatus.SUCCESS:
                    result.retry_count = retry_count
                    return result

                # 失敗但還有重試機會
                last_error = result.error

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Command execution error (attempt {attempt + 1}): {e}")

            # 還有重試機會
            if attempt < options.retry_on_failure:
                retry_count += 1
                delay = options.retry_backoff_factor ** attempt
                logger.info(f"Retrying command {command.command_id} "
                            f"in {delay:.2f}s (attempt {attempt + 2})")
                await asyncio.sleep(delay)

        # 所有重試都失敗
        return CommandResult(
            command_id=command.command_id,
            trace_id=command.trace_id,
            robot_id=command.robot_id,
            action=command.action,
            status=CommandStatus.FAILED,
            start_time=start_time,
            end_time=utc_now(),
            error=last_error or "Command failed after retries",
            retry_count=retry_count
        )

    async def _dispatch_command(
        self,
        command: BatchCommand
    ) -> CommandResult:
        """
        分派指令到佇列

        Args:
            command: 批次指令

        Returns:
            指令結果
        """
        start_time = utc_now()

        try:
            # 轉換優先級
            priority_map = {
                "low": MessagePriority.LOW,
                "normal": MessagePriority.NORMAL,
                "high": MessagePriority.HIGH,
            }
            priority = priority_map.get(command.priority, MessagePriority.NORMAL)

            # 構建訊息
            message = Message(
                id=command.command_id,
                payload={
                    "robot_id": command.robot_id,
                    "action": command.action,
                    "params": command.params,
                },
                priority=priority,
                trace_id=command.trace_id,
            )

            # 發送到佇列
            await self.service_manager.enqueue(message)

            # 記錄到歷史（如果有）
            if self.history_manager:
                self.history_manager.record_command(
                    command_id=command.command_id,
                    trace_id=command.trace_id,
                    robot_id=command.robot_id,
                    command_params={
                        "action_name": command.action,
                        **command.params
                    },
                    status="pending"
                )

            # 等待執行結果（使用超時）
            try:
                result = await asyncio.wait_for(
                    self._wait_for_result(command.command_id),
                    timeout=command.timeout_ms / 1000.0
                )

                end_time = utc_now()
                duration_ms = int((end_time - start_time).total_seconds() * 1000)

                return CommandResult(
                    command_id=command.command_id,
                    trace_id=command.trace_id,
                    robot_id=command.robot_id,
                    action=command.action,
                    status=CommandStatus.SUCCESS,
                    start_time=start_time,
                    end_time=end_time,
                    duration_ms=duration_ms,
                    result_data=result
                )

            except asyncio.TimeoutError:
                return CommandResult(
                    command_id=command.command_id,
                    trace_id=command.trace_id,
                    robot_id=command.robot_id,
                    action=command.action,
                    status=CommandStatus.TIMEOUT,
                    start_time=start_time,
                    end_time=utc_now(),
                    error=f"Command timeout after {command.timeout_ms}ms"
                )

        except Exception as e:
            logger.error(f"Error dispatching command {command.command_id}: {e}")
            return CommandResult(
                command_id=command.command_id,
                trace_id=command.trace_id,
                robot_id=command.robot_id,
                action=command.action,
                status=CommandStatus.FAILED,
                start_time=start_time,
                end_time=utc_now(),
                error=str(e)
            )

    async def _wait_for_result(self, command_id: str) -> Dict[str, Any]:
        """
        等待指令執行結果

        Args:
            command_id: 指令 ID

        Returns:
            執行結果資料
        """
        # 實作真正的結果等待邏輯
        # 從 SharedStateManager 輪詢指令狀態
        max_wait_time = 30  # 最長等待 30 秒
        poll_interval = 0.2  # 每 200ms 檢查一次
        elapsed_time = 0
        
        logger.debug(f"開始等待指令結果: {command_id}")
        
        while elapsed_time < max_wait_time:
            try:
                # 從 state_manager 檢查指令狀態
                if hasattr(self, 'state_manager') and self.state_manager:
                    command_key = f"command:{command_id}:result"
                    result = await self.state_manager.state_store.get(command_key)
                    
                    if result:
                        status = result.get("status")
                        if status in ["completed", "failed"]:
                            logger.info(f"指令 {command_id} 已完成: {status}")
                            return result
                
                # 未完成，繼續等待
                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval
                
            except Exception as e:
                logger.error(f"檢查指令狀態失敗: {e}")
                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval
        
        # 逾時
        logger.warning(f"指令 {command_id} 等待逾時 ({max_wait_time}s)")
        return {
            "status": "timeout",
            "command_id": command_id,
            "error": f"Command execution timeout after {max_wait_time}s"
        }
