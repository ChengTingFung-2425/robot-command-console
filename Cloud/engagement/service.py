# imports
import logging
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
import bleach

from Cloud.engagement.models import (
    UserEngagementProfile,
    Post,
    PostComment,
    PostLike,
    PointsLog,
)

logger = logging.getLogger(__name__)

# 積分獎勵規則（與 engagement.py 中的 POINTS_AWARD 一致）
POINTS_AWARD = {
    'registration': 10,
    'robot_registration': 5,
    'command_execution': 1,
    'advanced_command_submission': 20,
    'advanced_command_approval': 50,
    'advanced_command_usage': 5,
    'advanced_command_rating': 2,
    'daily_task': 10,
    'post_created': 3,
    'comment_created': 1,
    'post_liked': 1,
}

# 等級門檻（累積積分）
LEVEL_THRESHOLDS = [
    0,     # Lv1
    50,    # Lv2
    120,   # Lv3
    220,   # Lv4
    360,   # Lv5
    550,   # Lv6
    800,   # Lv7
    1120,  # Lv8
    1520,  # Lv9
    2020,  # Lv10
    2620,  # Lv11
    3320,  # Lv12
    4120,  # Lv13
    5020,  # Lv14
    6020,  # Lv15
    7220,  # Lv16
    8620,  # Lv17
    10220,  # Lv18
    12020,  # Lv19
    14020,  # Lv20
]

# 稱號對照（依等級）
TITLE_BY_LEVEL = {
    1: '新手探索者',
    3: '機器人學徒',
    5: '指令入門者',
    8: '指令達人',
    12: '機器人專家',
    15: '創意貢獻者',
    18: '平台大師',
    20: '社群領袖',
}


def _sanitize(text: Optional[str]) -> Optional[str]:
    """清理 HTML 內容以防止 XSS 攻擊"""
    if text is None:
        return None
    return bleach.clean(text, tags=[], strip=True)


def _calculate_level(points: int) -> int:
    """根據積分計算用戶等級"""
    level = 1
    for i, threshold in enumerate(LEVEL_THRESHOLDS):
        if points >= threshold:
            level = i + 1
    return level


def _get_title_for_level(level: int) -> str:
    """根據等級取得對應稱號"""
    title = '新手探索者'
    for lvl, t in sorted(TITLE_BY_LEVEL.items()):
        if level >= lvl:
            title = t
    return title


class EngagementService:
    """社群參與服務

    提供討論區貼文、評論、點讚、積分與排行榜等核心業務邏輯。
    """

    def __init__(self, db_session: Session):
        """初始化服務

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    # ──────────────────────────────
    # 用戶積分檔案
    # ──────────────────────────────

    def get_or_create_profile(self, user_username: str) -> UserEngagementProfile:
        """取得或建立用戶積分檔案

        Args:
            user_username: 用戶名稱

        Returns:
            UserEngagementProfile 物件
        """
        profile = self.db.query(UserEngagementProfile).filter_by(
            user_username=user_username
        ).first()
        if profile is None:
            profile = UserEngagementProfile(user_username=user_username)
            self.db.add(profile)
            self.db.flush()
        return profile

    def award_points(self, user_username: str, reason: str, amount: Optional[int] = None) -> UserEngagementProfile:
        """給予用戶積分

        Args:
            user_username: 用戶名稱
            reason: 獲得原因（對應 POINTS_AWARD 的 key 或自訂文字）
            amount: 積分數量（若不指定，使用 POINTS_AWARD 中的預設值）

        Returns:
            更新後的 UserEngagementProfile

        Raises:
            ValueError: 若 reason 不在 POINTS_AWARD 且未提供 amount
        """
        if amount is None:
            amount = POINTS_AWARD.get(reason)
            if amount is None:
                raise ValueError(f"未知的積分原因: {reason}，請提供 amount 參數")

        profile = self.get_or_create_profile(user_username)
        profile.points += amount
        profile.level = _calculate_level(profile.points)
        profile.title = _get_title_for_level(profile.level)

        log = PointsLog(user_username=user_username, amount=amount, reason=reason)
        self.db.add(log)
        self.db.flush()

        logger.info(f"Awarded {amount:+d} pts to {user_username} for '{reason}' (total: {profile.points})")
        return profile

    def get_profile(self, user_username: str) -> Optional[UserEngagementProfile]:
        """取得用戶積分檔案

        Args:
            user_username: 用戶名稱

        Returns:
            UserEngagementProfile 或 None
        """
        return self.db.query(UserEngagementProfile).filter_by(
            user_username=user_username
        ).first()

    # ──────────────────────────────
    # 討論區貼文
    # ──────────────────────────────

    def create_post(
        self,
        author_username: str,
        title: str,
        body: str,
        category: str = 'general',
    ) -> Post:
        """建立討論區貼文

        Args:
            author_username: 作者用戶名
            title: 貼文標題
            body: 貼文內容
            category: 分類（預設 'general'）

        Returns:
            建立的 Post 物件

        Raises:
            ValueError: 標題或內容為空
        """
        title = _sanitize(title)
        body = _sanitize(body)

        if not title or not title.strip():
            raise ValueError("貼文標題不能為空")
        if not body or not body.strip():
            raise ValueError("貼文內容不能為空")

        # 確保用戶有積分檔案
        self.get_or_create_profile(author_username)

        category = _sanitize(category) or 'general'
        # 限制 category 長度符合欄位定義（64 字元）
        category = category[:64].strip() or 'general'

        post = Post(
            title=title.strip(),
            body=body.strip(),
            category=category,
            author_username=author_username,
        )
        self.db.add(post)
        self.db.flush()

        logger.info(f"Post created: id={post.id} by {author_username}")
        return post

    def get_post(self, post_id: int) -> Optional[Post]:
        """取得指定貼文

        Args:
            post_id: 貼文 ID

        Returns:
            Post 或 None
        """
        return self.db.query(Post).filter_by(id=post_id).first()

    def list_posts(
        self,
        category: Optional[str] = None,
        author_username: Optional[str] = None,
        sort_by: str = 'created_at',
        order: str = 'desc',
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Post], int]:
        """列出討論區貼文

        Args:
            category: 分類篩選
            author_username: 作者篩選
            sort_by: 排序欄位（created_at/like_count/comment_count）
            order: 排序方向（asc/desc）
            limit: 每頁筆數（最大 100）
            offset: 分頁偏移量

        Returns:
            Tuple[List[Post], int]: (貼文列表, 總筆數)
        """
        limit = min(limit, 100)
        offset = max(offset, 0)

        sort_order = (order or 'desc').lower()
        if sort_order not in ('asc', 'desc'):
            sort_order = 'desc'

        q = self.db.query(Post)

        if category:
            q = q.filter(Post.category == category)
        if author_username:
            q = q.filter(Post.author_username == author_username)

        total = q.count()

        sort_field_map = {
            'created_at': Post.created_at,
            'like_count': Post.like_count,
            'comment_count': Post.comment_count,
        }
        sort_field = sort_field_map.get(sort_by, Post.created_at)

        # 置頂貼文優先，再依排序欄位排序
        if sort_order == 'desc':
            q = q.order_by(desc(Post.is_pinned), desc(sort_field))
        else:
            q = q.order_by(desc(Post.is_pinned), asc(sort_field))

        posts = q.limit(limit).offset(offset).all()
        return posts, total

    def delete_post(self, post_id: int, requesting_username: str) -> bool:
        """刪除貼文（只有作者可刪除）

        Args:
            post_id: 貼文 ID
            requesting_username: 請求刪除的用戶名稱

        Returns:
            True 若成功刪除

        Raises:
            ValueError: 貼文不存在或無權限
        """
        post = self.get_post(post_id)
        if not post:
            raise ValueError(f"貼文不存在: {post_id}")
        if post.author_username != requesting_username:
            raise ValueError("無權限刪除此貼文")

        self.db.delete(post)
        self.db.flush()
        logger.info(f"Post deleted: id={post_id} by {requesting_username}")
        return True

    # ──────────────────────────────
    # 評論
    # ──────────────────────────────

    def add_comment(
        self,
        post_id: int,
        author_username: str,
        content: str,
        parent_comment_id: Optional[int] = None,
    ) -> PostComment:
        """新增貼文評論

        Args:
            post_id: 貼文 ID
            author_username: 評論者用戶名
            content: 評論內容
            parent_comment_id: 父評論 ID（回覆用）

        Returns:
            建立的 PostComment 物件

        Raises:
            ValueError: 貼文不存在或內容為空
        """
        content = _sanitize(content)
        if not content or not content.strip():
            raise ValueError("評論內容不能為空")

        post = self.get_post(post_id)
        if not post:
            raise ValueError(f"貼文不存在: {post_id}")

        comment = PostComment(
            post_id=post_id,
            author_username=author_username,
            content=content.strip(),
            parent_comment_id=parent_comment_id,
        )
        self.db.add(comment)

        # 更新貼文評論數
        post.comment_count += 1
        self.db.flush()

        logger.info(f"Comment added to post {post_id} by {author_username}")
        return comment

    def get_comments(
        self,
        post_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> List[PostComment]:
        """取得貼文的頂層評論列表

        Args:
            post_id: 貼文 ID
            limit: 每頁筆數
            offset: 分頁偏移量

        Returns:
            List[PostComment]
        """
        return self.db.query(PostComment).filter_by(
            post_id=post_id,
            parent_comment_id=None,
        ).order_by(
            asc(PostComment.created_at)
        ).limit(limit).offset(offset).all()

    # ──────────────────────────────
    # 點讚
    # ──────────────────────────────

    def like_post(self, post_id: int, user_username: str) -> Dict[str, Any]:
        """對貼文點讚或取消點讚（切換）

        Args:
            post_id: 貼文 ID
            user_username: 點讚用戶名

        Returns:
            {'liked': bool, 'like_count': int}

        Raises:
            ValueError: 貼文不存在
        """
        post = self.get_post(post_id)
        if not post:
            raise ValueError(f"貼文不存在: {post_id}")

        existing = self.db.query(PostLike).filter_by(
            post_id=post_id,
            user_username=user_username,
        ).first()

        if existing:
            # 取消點讚
            self.db.delete(existing)
            post.like_count = max(0, post.like_count - 1)
            self.db.flush()
            logger.info(f"Post {post_id} unliked by {user_username}")
            return {'liked': False, 'like_count': post.like_count}

        # 新增點讚
        like = PostLike(post_id=post_id, user_username=user_username)
        self.db.add(like)
        post.like_count += 1
        self.db.flush()
        logger.info(f"Post {post_id} liked by {user_username}")
        return {'liked': True, 'like_count': post.like_count}

    # ──────────────────────────────
    # 排行榜
    # ──────────────────────────────

    def get_leaderboard(
        self,
        limit: int = 10,
        sort_by: str = 'points',
    ) -> List[UserEngagementProfile]:
        """取得排行榜

        Args:
            limit: 筆數（最大 100）
            sort_by: 排序欄位（points/level/reputation/total_commands）

        Returns:
            List[UserEngagementProfile]
        """
        limit = min(limit, 100)

        sort_field_map = {
            'points': UserEngagementProfile.points,
            'level': UserEngagementProfile.level,
            'reputation': UserEngagementProfile.reputation,
            'commands': UserEngagementProfile.total_commands,
        }
        sort_field = sort_field_map.get(sort_by, UserEngagementProfile.points)

        return self.db.query(UserEngagementProfile).order_by(
            desc(sort_field)
        ).limit(limit).all()

    def get_points_log(
        self,
        user_username: str,
        limit: int = 20,
    ) -> List[PointsLog]:
        """取得用戶積分變動記錄

        Args:
            user_username: 用戶名稱
            limit: 筆數

        Returns:
            List[PointsLog]
        """
        return self.db.query(PointsLog).filter_by(
            user_username=user_username
        ).order_by(
            desc(PointsLog.created_at)
        ).limit(limit).all()
