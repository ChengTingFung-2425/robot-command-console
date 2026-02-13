# imports
import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc

from Cloud.shared_commands.models import (
    SharedAdvancedCommand,
    CommandRating,
    CommandComment,
    SyncLog
)

logger = logging.getLogger(__name__)


class SharedCommandService:
    """進階指令共享服務

    提供進階指令的雲端共享功能核心業務邏輯。
    """

    def __init__(self, db_session: Session):
        """初始化服務

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def upload_command(
        self,
        name: str,
        description: str,
        category: str,
        content: str,
        author_username: str,
        author_email: str,
        edge_id: str,
        original_command_id: int,
        version: int = 1
    ) -> SharedAdvancedCommand:
        """上傳進階指令到雲端

        Args:
            name: 指令名稱
            description: 指令說明
            category: 指令分類
            content: 指令內容（JSON 格式）
            author_username: 作者用戶名
            author_email: 作者電子郵件
            edge_id: Edge 裝置 ID
            original_command_id: 原始指令 ID
            version: 版本號

        Returns:
            SharedAdvancedCommand: 建立的共享指令物件

        Raises:
            ValueError: 參數驗證失敗
        """
        # 驗證內容為有效 JSON
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"指令內容必須是有效的 JSON: {e}")

        # 檢查是否已存在相同名稱的指令
        existing = self.db.query(SharedAdvancedCommand).filter_by(
            name=name,
            author_username=author_username
        ).first()

        if existing:
            # 更新現有指令
            existing.description = description
            existing.category = category
            existing.content = content
            existing.version = version
            existing.updated_at = datetime.utcnow()
            self.db.commit()

            # 記錄同步日誌
            self._log_sync(edge_id, existing.id, 'update', 'success')

            logger.info(f"Updated shared command: {name} (v{version})")
            return existing

        # 建立新指令
        command = SharedAdvancedCommand(
            name=name,
            description=description,
            category=category,
            content=content,
            version=version,
            author_username=author_username,
            author_email=author_email,
            source_edge_id=edge_id,
            original_command_id=original_command_id
        )
        self.db.add(command)
        self.db.commit()

        # 記錄同步日誌
        self._log_sync(edge_id, command.id, 'upload', 'success')

        logger.info(f"Uploaded new shared command: {name} (ID={command.id})")
        return command

    def search_commands(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        author: Optional[str] = None,
        min_rating: Optional[float] = None,
        sort_by: str = 'rating',
        order: str = 'desc',
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[SharedAdvancedCommand], int]:
        """搜尋共享指令

        Args:
            query: 搜尋關鍵字（搜尋名稱與說明）
            category: 指令分類
            author: 作者用戶名
            min_rating: 最低評分
            sort_by: 排序欄位（rating/downloads/usage/created_at）
            order: 排序方向（asc/desc）
            limit: 每頁筆數
            offset: 分頁偏移量

        Returns:
            Tuple[List[SharedAdvancedCommand], int]: (指令列表, 總筆數)
        """
        # 基本查詢
        q = self.db.query(SharedAdvancedCommand).filter_by(is_public=True)

        # 應用篩選條件
        if query:
            search_pattern = f'%{query}%'
            q = q.filter(
                (SharedAdvancedCommand.name.ilike(search_pattern)) |
                (SharedAdvancedCommand.description.ilike(search_pattern))
            )

        if category:
            q = q.filter(SharedAdvancedCommand.category == category)

        if author:
            q = q.filter(SharedAdvancedCommand.author_username == author)

        if min_rating is not None:
            q = q.filter(SharedAdvancedCommand.average_rating >= min_rating)

        # 計算總筆數
        total = q.count()

        # 排序
        sort_field_map = {
            'rating': SharedAdvancedCommand.average_rating,
            'downloads': SharedAdvancedCommand.download_count,
            'usage': SharedAdvancedCommand.usage_count,
            'created_at': SharedAdvancedCommand.created_at,
        }
        sort_field = sort_field_map.get(sort_by, SharedAdvancedCommand.average_rating)

        if order == 'desc':
            q = q.order_by(desc(sort_field))
        else:
            q = q.order_by(asc(sort_field))

        # 分頁
        commands = q.limit(limit).offset(offset).all()

        logger.info(
            f"Search commands: query={query}, category={category}, "
            f"results={len(commands)}/{total}"
        )

        return commands, total

    def get_command(self, command_id: int) -> Optional[SharedAdvancedCommand]:
        """取得指定的共享指令

        Args:
            command_id: 指令 ID

        Returns:
            Optional[SharedAdvancedCommand]: 指令物件，若不存在則返回 None
        """
        return self.db.query(SharedAdvancedCommand).filter_by(
            id=command_id,
            is_public=True
        ).first()

    def download_command(self, command_id: int, edge_id: str) -> SharedAdvancedCommand:
        """下載共享指令

        Args:
            command_id: 指令 ID
            edge_id: Edge 裝置 ID

        Returns:
            SharedAdvancedCommand: 指令物件

        Raises:
            ValueError: 指令不存在
        """
        command = self.get_command(command_id)
        if not command:
            raise ValueError(f"指令不存在或不公開: {command_id}")

        # 增加下載次數
        command.download_count += 1
        self.db.commit()

        # 記錄同步日誌
        self._log_sync(edge_id, command_id, 'download', 'success')

        logger.info(f"Command downloaded: {command.name} (ID={command_id}) by edge={edge_id}")
        return command

    def rate_command(
        self,
        command_id: int,
        user_username: str,
        rating: int,
        comment: Optional[str] = None
    ) -> CommandRating:
        """對指令評分

        Args:
            command_id: 指令 ID
            user_username: 用戶名
            rating: 評分（1-5）
            comment: 評論

        Returns:
            CommandRating: 評分記錄

        Raises:
            ValueError: 參數驗證失敗或指令不存在
        """
        if not 1 <= rating <= 5:
            raise ValueError("評分必須在 1-5 之間")

        command = self.get_command(command_id)
        if not command:
            raise ValueError(f"指令不存在或不公開: {command_id}")

        # 檢查是否已評分
        existing_rating = self.db.query(CommandRating).filter_by(
            command_id=command_id,
            user_username=user_username
        ).first()

        if existing_rating:
            # 更新現有評分
            old_rating = existing_rating.rating
            existing_rating.rating = rating
            existing_rating.comment = comment
            existing_rating.updated_at = datetime.utcnow()

            # 更新平均評分（移除舊評分，加入新評分）
            total = command.average_rating * command.rating_count
            total = total - old_rating + rating
            command.average_rating = total / command.rating_count
            self.db.commit()

            logger.info(
                f"Updated rating for command {command_id}: "
                f"{old_rating} -> {rating} by {user_username}"
            )
            return existing_rating

        # 建立新評分
        new_rating = CommandRating(
            command_id=command_id,
            user_username=user_username,
            rating=rating,
            comment=comment
        )
        self.db.add(new_rating)

        # 更新平均評分
        total = command.average_rating * command.rating_count + rating
        command.rating_count += 1
        command.average_rating = total / command.rating_count
        self.db.commit()

        logger.info(
            f"New rating for command {command_id}: {rating}/5 by {user_username}"
        )
        return new_rating

    def get_ratings(
        self,
        command_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[CommandRating]:
        """取得指令的評分列表

        Args:
            command_id: 指令 ID
            limit: 每頁筆數
            offset: 分頁偏移量

        Returns:
            List[CommandRating]: 評分列表
        """
        return self.db.query(CommandRating).filter_by(
            command_id=command_id
        ).order_by(
            desc(CommandRating.created_at)
        ).limit(limit).offset(offset).all()

    def add_comment(
        self,
        command_id: int,
        user_username: str,
        content: str,
        parent_comment_id: Optional[int] = None
    ) -> CommandComment:
        """新增留言

        Args:
            command_id: 指令 ID
            user_username: 用戶名
            content: 留言內容
            parent_comment_id: 父留言 ID（回覆）

        Returns:
            CommandComment: 留言記錄

        Raises:
            ValueError: 指令不存在
        """
        command = self.get_command(command_id)
        if not command:
            raise ValueError(f"指令不存在或不公開: {command_id}")

        comment = CommandComment(
            command_id=command_id,
            user_username=user_username,
            content=content,
            parent_comment_id=parent_comment_id
        )
        self.db.add(comment)
        self.db.commit()

        logger.info(
            f"New comment on command {command_id} by {user_username}"
        )
        return comment

    def get_comments(
        self,
        command_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[CommandComment]:
        """取得指令的留言列表

        Args:
            command_id: 指令 ID
            limit: 每頁筆數
            offset: 分頁偏移量

        Returns:
            List[CommandComment]: 留言列表（僅頂層留言）
        """
        return self.db.query(CommandComment).filter_by(
            command_id=command_id,
            parent_comment_id=None  # 僅查詢頂層留言
        ).order_by(
            desc(CommandComment.created_at)
        ).limit(limit).offset(offset).all()

    def get_featured_commands(self, limit: int = 10) -> List[SharedAdvancedCommand]:
        """取得精選指令

        Args:
            limit: 筆數

        Returns:
            List[SharedAdvancedCommand]: 精選指令列表
        """
        return self.db.query(SharedAdvancedCommand).filter_by(
            is_public=True,
            is_featured=True
        ).order_by(
            desc(SharedAdvancedCommand.average_rating)
        ).limit(limit).all()

    def get_popular_commands(self, limit: int = 10) -> List[SharedAdvancedCommand]:
        """取得熱門指令（根據下載次數）

        Args:
            limit: 筆數

        Returns:
            List[SharedAdvancedCommand]: 熱門指令列表
        """
        return self.db.query(SharedAdvancedCommand).filter_by(
            is_public=True
        ).order_by(
            desc(SharedAdvancedCommand.download_count)
        ).limit(limit).all()

    def get_categories(self) -> List[Dict[str, Any]]:
        """取得所有分類及其指令數量

        Returns:
            List[Dict[str, Any]]: 分類列表
        """
        results = self.db.query(
            SharedAdvancedCommand.category,
            func.count(SharedAdvancedCommand.id).label('count')
        ).filter_by(
            is_public=True
        ).group_by(
            SharedAdvancedCommand.category
        ).all()

        return [
            {'category': cat, 'count': count}
            for cat, count in results
        ]

    def _log_sync(
        self,
        edge_id: str,
        command_id: int,
        action: str,
        status: str,
        error_message: Optional[str] = None
    ) -> None:
        """記錄同步日誌

        Args:
            edge_id: Edge 裝置 ID
            command_id: 指令 ID
            action: 動作（upload/download/update）
            status: 狀態（success/failed）
            error_message: 錯誤訊息
        """
        log = SyncLog(
            edge_id=edge_id,
            command_id=command_id,
            action=action,
            status=status,
            error_message=error_message
        )
        self.db.add(log)
        self.db.commit()
