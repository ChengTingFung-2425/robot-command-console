# imports
from datetime import datetime
from typing import Dict, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class SharedAdvancedCommand(Base):
    """雲端共享的進階指令

    存儲從 Edge 上傳的已批准進階指令，供社群瀏覽、下載與評分。
    """
    __tablename__ = 'shared_advanced_command'

    id = Column(Integer, primary_key=True)
    # 原始指令資訊
    name = Column(String(128), nullable=False, index=True)
    description = Column(Text)
    category = Column(String(64), index=True)
    content = Column(Text, nullable=False)  # JSON 格式的動作序列
    version = Column(Integer, default=1)

    # 作者資訊
    author_username = Column(String(64), nullable=False, index=True)
    author_email = Column(String(120))

    # 來源資訊
    source_edge_id = Column(String(64), index=True)  # Edge 裝置 ID
    original_command_id = Column(Integer)  # 原始 Edge 上的指令 ID

    # 統計資訊
    download_count = Column(Integer, default=0)
    usage_count = Column(Integer, default=0)
    average_rating = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)

    # 狀態與時間戳
    is_public = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)  # 精選指令
    created_at = Column(DateTime, index=True, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    ratings = relationship('CommandRating', back_populates='command', cascade='all, delete-orphan')
    comments = relationship('CommandComment', back_populates='command', cascade='all, delete-orphan')

    # 索引
    __table_args__ = (
        Index('idx_category_rating', 'category', 'average_rating'),
        Index('idx_downloads', 'download_count'),
        Index('idx_featured', 'is_featured', 'average_rating'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式
        
        注意：為保護隱私，author_email 不包含在輸出中
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'content': self.content,
            'version': self.version,
            'author_username': self.author_username,
            'download_count': self.download_count,
            'usage_count': self.usage_count,
            'average_rating': round(self.average_rating, 2),
            'rating_count': self.rating_count,
            'is_featured': self.is_featured,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f'<SharedAdvancedCommand {self.name} (v{self.version})>'


class CommandRating(Base):
    """指令評分

    用戶對共享指令的評分記錄。
    """
    __tablename__ = 'command_rating'

    id = Column(Integer, primary_key=True)
    command_id = Column(Integer, ForeignKey('shared_advanced_command.id'), nullable=False, index=True)
    user_username = Column(String(64), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text)
    created_at = Column(DateTime, index=True, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    command = relationship('SharedAdvancedCommand', back_populates='ratings')

    __table_args__ = (
        Index('idx_user_command', 'user_username', 'command_id', unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'id': self.id,
            'command_id': self.command_id,
            'user_username': self.user_username,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f'<CommandRating cmd={self.command_id} user={self.user_username} rating={self.rating}>'


class CommandComment(Base):
    """指令留言

    用戶對共享指令的留言記錄。
    """
    __tablename__ = 'command_comment'

    id = Column(Integer, primary_key=True)
    command_id = Column(Integer, ForeignKey('shared_advanced_command.id'), nullable=False, index=True)
    user_username = Column(String(64), nullable=False, index=True)
    content = Column(Text, nullable=False)
    parent_comment_id = Column(Integer, ForeignKey('command_comment.id'), nullable=True)  # 支援回覆
    created_at = Column(DateTime, index=True, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    command = relationship('SharedAdvancedCommand', back_populates='comments')
    replies = relationship('CommandComment', backref='parent', remote_side=[id])

    def to_dict(self, include_replies: bool = False) -> Dict[str, Any]:
        """轉換為字典格式"""
        result = {
            'id': self.id,
            'command_id': self.command_id,
            'user_username': self.user_username,
            'content': self.content,
            'parent_comment_id': self.parent_comment_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_replies:
            result['replies'] = [reply.to_dict() for reply in self.replies]
        return result

    def __repr__(self) -> str:
        return f'<CommandComment cmd={self.command_id} user={self.user_username}>'


class SyncLog(Base):
    """同步記錄

    記錄 Edge 與 Cloud 之間的指令同步歷史。
    """
    __tablename__ = 'sync_log'

    id = Column(Integer, primary_key=True)
    edge_id = Column(String(64), nullable=False, index=True)
    command_id = Column(Integer, ForeignKey('shared_advanced_command.id'), nullable=False)
    action = Column(String(32), nullable=False)  # upload/download/update
    status = Column(String(32), nullable=False)  # success/failed
    error_message = Column(Text)
    created_at = Column(DateTime, index=True, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'id': self.id,
            'edge_id': self.edge_id,
            'command_id': self.command_id,
            'action': self.action,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f'<SyncLog edge={self.edge_id} action={self.action} status={self.status}>'
