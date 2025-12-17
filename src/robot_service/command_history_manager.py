"""
指令歷史管理器

整合 CommandHistoryStore 與 CommandResultCache，
為 Robot Service 提供統一的歷史記錄與快取介面。
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.common.command_history import CommandRecord, CommandHistoryStore
from src.common.command_cache import CommandResultCache
from src.common.datetime_utils import utc_now


logger = logging.getLogger(__name__)


class CommandHistoryManager:
    """指令歷史管理器

    提供指令歷史記錄與快取的統一管理介面，支援：
    - 自動記錄指令執行歷史
    - 快取指令執行結果
    - 查詢歷史記錄
    - 清理過期資料
    """

    def __init__(
        self,
        history_db_path: Optional[str] = None,
        cache_max_size: int = 500,
        cache_ttl_seconds: int = 1800,
        auto_cleanup_hours: int = 720  # 預設 30 天
    ):
        """初始化指令歷史管理器

        Args:
            history_db_path: 歷史資料庫路徑
            cache_max_size: 快取最大項目數
            cache_ttl_seconds: 快取 TTL（秒）
            auto_cleanup_hours: 自動清理超過此小時數的歷史記錄
        """
        self.history_store = CommandHistoryStore(db_path=history_db_path)
        self.result_cache = CommandResultCache(
            max_size=cache_max_size,
            default_ttl_seconds=cache_ttl_seconds
        )
        self.auto_cleanup_hours = auto_cleanup_hours

        logger.info(
            "CommandHistoryManager initialized",
            extra={
                "cache_max_size": cache_max_size,
                "cache_ttl_seconds": cache_ttl_seconds,
                "auto_cleanup_hours": auto_cleanup_hours
            }
        )

    def record_command(
        self,
        command_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        robot_id: str = 'default',
        command_type: str = 'robot.action',
        command_params: Optional[Dict[str, Any]] = None,
        actor_type: Optional[str] = None,
        actor_id: Optional[str] = None,
        source: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> CommandRecord:
        """記錄新指令

        Args:
            command_id: 指令 ID，若未提供則自動生成
            trace_id: 追蹤 ID，若未提供則自動生成
            robot_id: 機器人 ID
            command_type: 指令類型
            command_params: 指令參數
            actor_type: 執行者類型（human/ai/system）
            actor_id: 執行者 ID
            source: 來源（webui/api/cli）
            labels: 標籤

        Returns:
            建立的指令記錄
        """
        if command_id is None:
            command_id = f"cmd-{uuid.uuid4().hex[:12]}"
        if trace_id is None:
            trace_id = f"trace-{uuid.uuid4().hex[:12]}"
        if command_params is None:
            command_params = {}

        record = CommandRecord(
            command_id=command_id,
            trace_id=trace_id,
            robot_id=robot_id,
            command_type=command_type,
            command_params=command_params,
            status='pending',
            actor_type=actor_type,
            actor_id=actor_id,
            source=source,
            labels=labels
        )

        success = self.history_store.add_record(record)

        if success:
            logger.info(
                "Command recorded",
                extra={
                    "command_id": command_id,
                    "trace_id": trace_id,
                    "robot_id": robot_id
                }
            )
        else:
            logger.warning(
                "Failed to record command",
                extra={
                    "command_id": command_id,
                    "trace_id": trace_id
                }
            )

        return record

    def update_command_status(
        self,
        command_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[Dict[str, Any]] = None,
        execution_time_ms: Optional[int] = None
    ) -> bool:
        """更新指令狀態

        Args:
            command_id: 指令 ID
            status: 新狀態（running/succeeded/failed/cancelled）
            result: 執行結果
            error: 錯誤資訊
            execution_time_ms: 執行時間（毫秒）

        Returns:
            是否更新成功
        """
        updates = {'status': status}

        if result is not None:
            updates['result'] = result

        if error is not None:
            updates['error'] = error

        if execution_time_ms is not None:
            updates['execution_time_ms'] = execution_time_ms

        # 如果狀態為完成態，記錄完成時間
        if status in ['succeeded', 'failed', 'cancelled']:
            updates['completed_at'] = utc_now()

        success = self.history_store.update_record(command_id, updates)

        if success:
            logger.debug(
                "Command status updated",
                extra={
                    "command_id": command_id,
                    "status": status
                }
            )

            # 如果有結果，加入快取
            if result is not None and status == 'succeeded':
                record = self.history_store.get_record(command_id)
                if record:
                    self.cache_command_result(
                        command_id=command_id,
                        trace_id=record.trace_id,
                        result=result
                    )

        return success

    def cache_command_result(
        self,
        command_id: str,
        trace_id: str,
        result: Dict[str, Any],
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """快取指令結果

        Args:
            command_id: 指令 ID
            trace_id: 追蹤 ID
            result: 指令結果
            ttl_seconds: TTL（秒）

        Returns:
            是否快取成功
        """
        success = self.result_cache.set_command_result(
            command_id=command_id,
            trace_id=trace_id,
            result=result,
            ttl_seconds=ttl_seconds
        )

        if success:
            logger.debug(
                "Command result cached",
                extra={
                    "command_id": command_id,
                    "trace_id": trace_id
                }
            )

        return success

    def get_command_result(
        self,
        command_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """取得指令結果

        優先從快取取得，若快取未命中則從歷史記錄取得。

        Args:
            command_id: 指令 ID
            trace_id: 追蹤 ID（與 command_id 二選一）
            use_cache: 是否使用快取

        Returns:
            指令結果，若不存在則回傳 None
        """
        if command_id is None and trace_id is None:
            logger.warning("Either command_id or trace_id must be provided")
            return None

        # 嘗試從快取取得
        if use_cache:
            if command_id:
                cached = self.result_cache.get(command_id)
            else:
                cached = self.result_cache.get_by_trace_id(trace_id)

            if cached is not None:
                logger.debug(
                    "Command result cache hit",
                    extra={
                        "command_id": command_id,
                        "trace_id": trace_id
                    }
                )
                return cached

        # 從歷史記錄取得
        if command_id:
            record = self.history_store.get_record(command_id)
        else:
            # 透過 trace_id 查詢
            record = self.history_store.get_by_trace_id(trace_id)

        if record and record.result:
            # 將結果加入快取
            if use_cache:
                self.cache_command_result(
                    command_id=record.command_id,
                    trace_id=record.trace_id,
                    result=record.result
                )

            return record.result

        return None

    def get_command_history(
        self,
        robot_id: Optional[str] = None,
        status: Optional[str] = None,
        actor_type: Optional[str] = None,
        source: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[CommandRecord]:
        """查詢指令歷史

        Args:
            robot_id: 機器人 ID 篩選
            status: 狀態篩選
            actor_type: 執行者類型篩選
            source: 來源篩選
            start_time: 開始時間篩選
            end_time: 結束時間篩選
            limit: 返回記錄數上限
            offset: 查詢偏移量

        Returns:
            符合條件的指令記錄列表
        """
        return self.history_store.query_records(
            robot_id=robot_id,
            status=status,
            actor_type=actor_type,
            source=source,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset
        )

    def count_commands(
        self,
        robot_id: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        """統計指令數量

        Args:
            robot_id: 機器人 ID 篩選
            status: 狀態篩選
            start_time: 開始時間篩選
            end_time: 結束時間篩選

        Returns:
            符合條件的記錄數量
        """
        return self.history_store.count_records(
            robot_id=robot_id,
            status=status,
            start_time=start_time,
            end_time=end_time
        )

    def get_cache_stats(self) -> Dict[str, Any]:
        """取得快取統計資訊

        Returns:
            快取統計資訊字典
        """
        return self.result_cache.get_stats()

    def cleanup_expired_cache(self) -> int:
        """清理過期快取

        Returns:
            清理的項目數量
        """
        count = self.result_cache.cleanup_expired()
        if count > 0:
            logger.info(
                "Expired cache entries cleaned up",
                extra={"count": count}
            )
        return count

    def cleanup_old_history(self, hours: Optional[int] = None) -> int:
        """清理舊歷史記錄

        Args:
            hours: 清理超過此小時數的記錄，若未提供則使用預設值

        Returns:
            清理的記錄數量
        """
        if hours is None:
            hours = self.auto_cleanup_hours

        before = utc_now() - timedelta(hours=hours)
        count = self.history_store.delete_old_records(before)

        if count > 0:
            logger.info(
                "Old history records cleaned up",
                extra={
                    "count": count,
                    "hours": hours
                }
            )

        return count

    def clear_cache(self):
        """清空快取"""
        self.result_cache.clear()
        logger.info("Command result cache cleared")

    def clear_all_history(self) -> bool:
        """清空所有歷史記錄（謹慎使用）

        Returns:
            是否清空成功
        """
        success = self.history_store.clear_all()
        if success:
            logger.warning("All command history cleared")
        return success
