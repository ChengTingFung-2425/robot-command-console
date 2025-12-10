"""
本地指令歷史記錄模組

提供指令歷史的持久化存儲、查詢與管理功能。
支援 Edge 環境離線使用與歷史追蹤。
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from .datetime_utils import utc_now, parse_iso_datetime


logger = logging.getLogger(__name__)


@dataclass
class CommandRecord:
    """指令記錄資料模型"""
    
    command_id: str
    trace_id: str
    robot_id: str
    command_type: str
    command_params: Dict[str, Any]
    status: str  # pending/running/succeeded/failed/cancelled
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[int] = None
    actor_type: Optional[str] = None  # human/ai/system
    actor_id: Optional[str] = None
    source: Optional[str] = None  # webui/api/cli
    labels: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        data = asdict(self)
        # 轉換 datetime 為 ISO 格式
        if isinstance(data.get('created_at'), datetime):
            data['created_at'] = data['created_at'].isoformat()
        if isinstance(data.get('updated_at'), datetime):
            data['updated_at'] = data['updated_at'].isoformat()
        if isinstance(data.get('completed_at'), datetime):
            data['completed_at'] = data['completed_at'].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommandRecord':
        """從字典建立實例"""
        # 解析 datetime 欄位
        if isinstance(data.get('created_at'), str):
            data['created_at'] = parse_iso_datetime(data['created_at'])
        if isinstance(data.get('updated_at'), str):
            data['updated_at'] = parse_iso_datetime(data['updated_at'])
        if data.get('completed_at') and isinstance(data['completed_at'], str):
            data['completed_at'] = parse_iso_datetime(data['completed_at'])
        return cls(**data)


class CommandHistoryStore:
    """本地指令歷史存儲
    
    使用 SQLite 提供持久化指令歷史記錄，支援：
    - 指令記錄的 CRUD 操作
    - 按時間、狀態、機器人 ID 等條件查詢
    - 分頁查詢支援
    - 自動清理過期記錄
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """初始化指令歷史存儲
        
        Args:
            db_path: 資料庫檔案路徑，預設為 ~/.robot-console/command_history.db
        """
        if db_path is None:
            db_path = str(Path.home() / '.robot-console' / 'command_history.db')
        
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
        logger.info(f"CommandHistoryStore initialized at {db_path}")
    
    def _init_db(self):
        """初始化資料庫 schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS command_history (
                command_id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                robot_id TEXT NOT NULL,
                command_type TEXT NOT NULL,
                command_params TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                result TEXT,
                error TEXT,
                execution_time_ms INTEGER,
                actor_type TEXT,
                actor_id TEXT,
                source TEXT,
                labels TEXT
            )
        ''')
        
        # 建立索引以提升查詢效能
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_command_history_trace_id 
            ON command_history(trace_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_command_history_robot_id 
            ON command_history(robot_id)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_command_history_status 
            ON command_history(status)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_command_history_created_at 
            ON command_history(created_at)
        ''')
        
        conn.commit()
        conn.close()
    
    def add_record(self, record: CommandRecord) -> bool:
        """新增指令記錄
        
        Args:
            record: 指令記錄
            
        Returns:
            是否新增成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO command_history (
                    command_id, trace_id, robot_id, command_type, command_params,
                    status, created_at, updated_at, completed_at, result, error,
                    execution_time_ms, actor_type, actor_id, source, labels
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                record.command_id,
                record.trace_id,
                record.robot_id,
                record.command_type,
                json.dumps(record.command_params),
                record.status,
                record.created_at.isoformat(),
                record.updated_at.isoformat(),
                record.completed_at.isoformat() if record.completed_at else None,
                json.dumps(record.result) if record.result else None,
                json.dumps(record.error) if record.error else None,
                record.execution_time_ms,
                record.actor_type,
                record.actor_id,
                record.source,
                json.dumps(record.labels) if record.labels else None
            ))
            
            conn.commit()
            conn.close()
            logger.debug(f"Added command record: {record.command_id}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Command record already exists: {record.command_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to add command record: {e}")
            return False
    
    def update_record(self, command_id: str, updates: Dict[str, Any]) -> bool:
        """更新指令記錄
        
        Args:
            command_id: 指令 ID
            updates: 要更新的欄位字典
            
        Returns:
            是否更新成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 自動更新 updated_at
            updates['updated_at'] = utc_now().isoformat()
            
            # 建構 SQL UPDATE 語句
            set_clauses = []
            values = []
            for key, value in updates.items():
                set_clauses.append(f"{key} = ?")
                if key in ['command_params', 'result', 'error', 'labels'] and value is not None:
                    values.append(json.dumps(value))
                elif isinstance(value, datetime):
                    values.append(value.isoformat())
                else:
                    values.append(value)
            
            values.append(command_id)
            
            cursor.execute(f'''
                UPDATE command_history
                SET {', '.join(set_clauses)}
                WHERE command_id = ?
            ''', values)
            
            conn.commit()
            conn.close()
            logger.debug(f"Updated command record: {command_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update command record: {e}")
            return False
    
    def get_record(self, command_id: str) -> Optional[CommandRecord]:
        """取得指令記錄
        
        Args:
            command_id: 指令 ID
            
        Returns:
            指令記錄，若不存在則回傳 None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM command_history WHERE command_id = ?
            ''', (command_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self._row_to_record(row)
            return None
        except Exception as e:
            logger.error(f"Failed to get command record: {e}")
            return None
    
    def get_by_trace_id(self, trace_id: str) -> Optional[CommandRecord]:
        """透過 trace_id 取得指令記錄
        
        Args:
            trace_id: 追蹤 ID
            
        Returns:
            指令記錄，若不存在則回傳 None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM command_history WHERE trace_id = ? LIMIT 1
            ''', (trace_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self._row_to_record(row)
            return None
        except Exception as e:
            logger.error(f"Failed to get command record by trace_id: {e}")
            return None
    
    def query_records(
        self,
        robot_id: Optional[str] = None,
        status: Optional[str] = None,
        actor_type: Optional[str] = None,
        source: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = 'created_at',
        order_desc: bool = True
    ) -> List[CommandRecord]:
        """查詢指令記錄
        
        Args:
            robot_id: 機器人 ID 篩選
            status: 狀態篩選
            actor_type: 執行者類型篩選
            source: 來源篩選
            start_time: 開始時間篩選
            end_time: 結束時間篩選
            limit: 返回記錄數上限
            offset: 查詢偏移量（用於分頁）
            order_by: 排序欄位
            order_desc: 是否降序排列
            
        Returns:
            符合條件的指令記錄列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # 建構查詢條件
            conditions = []
            params = []
            
            if robot_id:
                conditions.append("robot_id = ?")
                params.append(robot_id)
            
            if status:
                conditions.append("status = ?")
                params.append(status)
            
            if actor_type:
                conditions.append("actor_type = ?")
                params.append(actor_type)
            
            if source:
                conditions.append("source = ?")
                params.append(source)
            
            if start_time:
                conditions.append("created_at >= ?")
                params.append(start_time.isoformat())
            
            if end_time:
                conditions.append("created_at <= ?")
                params.append(end_time.isoformat())
            
            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            order_clause = f"ORDER BY {order_by} {'DESC' if order_desc else 'ASC'}"
            
            cursor.execute(f'''
                SELECT * FROM command_history
                {where_clause}
                {order_clause}
                LIMIT ? OFFSET ?
            ''', params + [limit, offset])
            
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_record(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to query command records: {e}")
            return []
    
    def count_records(
        self,
        robot_id: Optional[str] = None,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        """統計指令記錄數量
        
        Args:
            robot_id: 機器人 ID 篩選
            status: 狀態篩選
            start_time: 開始時間篩選
            end_time: 結束時間篩選
            
        Returns:
            符合條件的記錄數量
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            conditions = []
            params = []
            
            if robot_id:
                conditions.append("robot_id = ?")
                params.append(robot_id)
            
            if status:
                conditions.append("status = ?")
                params.append(status)
            
            if start_time:
                conditions.append("created_at >= ?")
                params.append(start_time.isoformat())
            
            if end_time:
                conditions.append("created_at <= ?")
                params.append(end_time.isoformat())
            
            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            
            cursor.execute(f'''
                SELECT COUNT(*) FROM command_history {where_clause}
            ''', params)
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count
        except Exception as e:
            logger.error(f"Failed to count command records: {e}")
            return 0
    
    def delete_record(self, command_id: str) -> bool:
        """刪除指令記錄
        
        Args:
            command_id: 指令 ID
            
        Returns:
            是否刪除成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM command_history WHERE command_id = ?
            ''', (command_id,))
            
            conn.commit()
            conn.close()
            logger.debug(f"Deleted command record: {command_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete command record: {e}")
            return False
    
    def delete_old_records(self, before: datetime) -> int:
        """刪除指定時間之前的記錄
        
        Args:
            before: 刪除此時間之前的記錄
            
        Returns:
            刪除的記錄數量
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM command_history WHERE created_at < ?
            ''', (before.isoformat(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            logger.info(f"Deleted {deleted_count} old command records")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete old command records: {e}")
            return 0
    
    def clear_all(self) -> bool:
        """清空所有記錄（謹慎使用）
        
        Returns:
            是否清空成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM command_history')
            
            conn.commit()
            conn.close()
            logger.warning("Cleared all command history records")
            return True
        except Exception as e:
            logger.error(f"Failed to clear command history: {e}")
            return False
    
    def _row_to_record(self, row: sqlite3.Row) -> CommandRecord:
        """將資料庫 row 轉換為 CommandRecord"""
        return CommandRecord(
            command_id=row['command_id'],
            trace_id=row['trace_id'],
            robot_id=row['robot_id'],
            command_type=row['command_type'],
            command_params=json.loads(row['command_params']),
            status=row['status'],
            created_at=parse_iso_datetime(row['created_at']),
            updated_at=parse_iso_datetime(row['updated_at']),
            completed_at=parse_iso_datetime(row['completed_at']) if row['completed_at'] else None,
            result=json.loads(row['result']) if row['result'] else None,
            error=json.loads(row['error']) if row['error'] else None,
            execution_time_ms=row['execution_time_ms'],
            actor_type=row['actor_type'],
            actor_id=row['actor_id'],
            source=row['source'],
            labels=json.loads(row['labels']) if row['labels'] else None
        )
