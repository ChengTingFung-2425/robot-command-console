# imports
from datetime import datetime
from typing import Dict, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class UserEngagementProfile(Base):
    """用戶參與激勵檔案

    記錄用戶在社群互動中的積分、等級、稱號與聲譽。
    """
    __tablename__ = 'user_engagement_profile'

    id = Column(Integer, primary_key=True)
    user_username = Column(String(64), nullable=False, unique=True, index=True)
    points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    title = Column(String(128), default='新手探索者')
    total_commands = Column(Integer, default=0)
    total_advanced_commands = Column(Integer, default=0)
    reputation = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    posts = relationship('Post', back_populates='author_profile', cascade='all, delete-orphan')

    def get_rank_tier(self) -> str:
        """回傳用戶等級段位名稱"""
        if self.level <= 10:
            return '青銅'
        elif self.level <= 20:
            return '白銀'
        elif self.level <= 30:
            return '黃金'
        elif self.level <= 40:
            return '鉑金'
        return '鑽石'

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'id': self.id,
            'user_username': self.user_username,
            'points': self.points,
            'level': self.level,
            'title': self.title,
            'total_commands': self.total_commands,
            'total_advanced_commands': self.total_advanced_commands,
            'reputation': self.reputation,
            'rank_tier': self.get_rank_tier(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f'<UserEngagementProfile {self.user_username} L{self.level} pts={self.points}>'


class Post(Base):
    """討論區貼文

    用戶在討論區發表的貼文，支援分類、點讚與評論。
    """
    __tablename__ = 'post'

    id = Column(Integer, primary_key=True)
    title = Column(String(256), nullable=False)
    body = Column(Text, nullable=False)
    category = Column(String(64), default='general', index=True)
    author_username = Column(
        String(64),
        ForeignKey('user_engagement_profile.user_username'),
        nullable=False,
        index=True
    )
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    author_profile = relationship('UserEngagementProfile', back_populates='posts')
    comments = relationship('PostComment', back_populates='post', cascade='all, delete-orphan')
    likes = relationship('PostLike', back_populates='post', cascade='all, delete-orphan')

    # 索引
    __table_args__ = (
        Index('idx_post_category_created', 'category', 'created_at'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'id': self.id,
            'title': self.title,
            'body': self.body,
            'category': self.category,
            'author_username': self.author_username,
            'like_count': self.like_count,
            'comment_count': self.comment_count,
            'is_pinned': self.is_pinned,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f'<Post {self.id} by {self.author_username}>'


class PostComment(Base):
    """貼文評論

    用戶對討論區貼文的評論，支援巢狀回覆。
    """
    __tablename__ = 'post_comment'

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('post.id'), nullable=False, index=True)
    author_username = Column(String(64), nullable=False, index=True)
    content = Column(Text, nullable=False)
    parent_comment_id = Column(Integer, ForeignKey('post_comment.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    post = relationship('Post', back_populates='comments')
    replies = relationship('PostComment', backref='parent', remote_side=[id])

    def to_dict(self, include_replies: bool = False) -> Dict[str, Any]:
        """轉換為字典格式"""
        result = {
            'id': self.id,
            'post_id': self.post_id,
            'author_username': self.author_username,
            'content': self.content,
            'parent_comment_id': self.parent_comment_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
        if include_replies:
            result['replies'] = [r.to_dict() for r in self.replies]
        return result

    def __repr__(self) -> str:
        return f'<PostComment post={self.post_id} by {self.author_username}>'


class PostLike(Base):
    """貼文點讚

    記錄用戶對貼文的點讚，每位用戶對每篇貼文只能點讚一次。
    """
    __tablename__ = 'post_like'

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey('post.id'), nullable=False, index=True)
    user_username = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 關聯
    post = relationship('Post', back_populates='likes')

    __table_args__ = (
        Index('idx_post_like_unique', 'post_id', 'user_username', unique=True),
    )

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'id': self.id,
            'post_id': self.post_id,
            'user_username': self.user_username,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f'<PostLike post={self.post_id} by {self.user_username}>'


class PointsLog(Base):
    """積分變動記錄

    記錄用戶積分的每次變動原因與數量。
    """
    __tablename__ = 'points_log'

    id = Column(Integer, primary_key=True)
    user_username = Column(String(64), nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    reason = Column(String(128), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'id': self.id,
            'user_username': self.user_username,
            'amount': self.amount,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f'<PointsLog {self.user_username} {self.amount:+d} ({self.reason})>'
