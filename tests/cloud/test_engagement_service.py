# imports
import pytest
from unittest.mock import Mock, MagicMock

from Cloud.engagement.service import EngagementService, POINTS_AWARD, _calculate_level, _get_title_for_level
from Cloud.engagement.models import (
    UserEngagementProfile,
    Post,
    PostComment,
    PostLike,
)


class TestEngagementServiceProfile:
    """測試用戶積分檔案功能"""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    @pytest.fixture
    def service(self, mock_db):
        return EngagementService(mock_db)

    def test_get_or_create_profile_existing(self, service, mock_db):
        """測試取得已存在的用戶積分檔案"""
        mock_profile = Mock(spec=UserEngagementProfile)
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_profile

        result = service.get_or_create_profile('testuser')
        assert result is mock_profile
        mock_db.add.assert_not_called()

    def test_get_or_create_profile_new(self, service, mock_db):
        """測試建立新用戶積分檔案"""
        mock_db.query.return_value.filter_by.return_value.first.return_value = None

        result = service.get_or_create_profile('newuser')
        mock_db.add.assert_called_once()
        assert isinstance(result, UserEngagementProfile)
        assert result.user_username == 'newuser'

    def test_get_profile_not_found(self, service, mock_db):
        """測試取得不存在的用戶積分檔案"""
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        result = service.get_profile('nobody')
        assert result is None

    def test_award_points_known_reason(self, service, mock_db):
        """測試使用已知原因給予積分"""
        mock_profile = Mock(spec=UserEngagementProfile)
        mock_profile.points = 0
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_profile

        service.award_points('testuser', 'registration')

        assert mock_profile.points == POINTS_AWARD['registration']

    def test_award_points_custom_amount(self, service, mock_db):
        """測試指定自訂積分數量"""
        mock_profile = Mock(spec=UserEngagementProfile)
        mock_profile.points = 100
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_profile

        service.award_points('testuser', 'custom_reason', amount=50)

        assert mock_profile.points == 150

    def test_award_points_unknown_reason_raises(self, service, mock_db):
        """測試使用未知原因且未提供 amount 時應拋出例外"""
        mock_db.query.return_value.filter_by.return_value.first.return_value = Mock()
        with pytest.raises(ValueError, match="未知的積分原因"):
            service.award_points('testuser', 'unknown_reason')

    def test_get_leaderboard(self, service, mock_db):
        """測試取得排行榜"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        result = service.get_leaderboard(limit=10, sort_by='points')
        assert isinstance(result, list)

    def test_get_leaderboard_limit_capped(self, service, mock_db):
        """測試排行榜筆數上限為 100"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        service.get_leaderboard(limit=500, sort_by='points')
        mock_query.limit.assert_called_with(100)


class TestEngagementServicePosts:
    """測試討論區貼文功能"""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    @pytest.fixture
    def service(self, mock_db):
        return EngagementService(mock_db)

    def test_create_post_success(self, service, mock_db):
        """測試成功建立貼文"""
        mock_db.query.return_value.filter_by.return_value.first.return_value = Mock(spec=UserEngagementProfile)

        post = service.create_post('testuser', 'Test Title', 'Test body', 'general')

        assert isinstance(post, Post)
        assert post.title == 'Test Title'
        assert post.author_username == 'testuser'
        mock_db.add.assert_called()

    def test_create_post_empty_title_raises(self, service, mock_db):
        """測試標題為空時應拋出例外"""
        mock_db.query.return_value.filter_by.return_value.first.return_value = Mock(spec=UserEngagementProfile)
        with pytest.raises(ValueError, match="貼文標題不能為空"):
            service.create_post('testuser', '', 'body')

    def test_create_post_empty_body_raises(self, service, mock_db):
        """測試內容為空時應拋出例外"""
        mock_db.query.return_value.filter_by.return_value.first.return_value = Mock(spec=UserEngagementProfile)
        with pytest.raises(ValueError, match="貼文內容不能為空"):
            service.create_post('testuser', 'Title', '')

    def test_create_post_strips_html(self, service, mock_db):
        """測試建立貼文時會清除 HTML 標籤（XSS 防護）"""
        mock_db.query.return_value.filter_by.return_value.first.return_value = Mock(spec=UserEngagementProfile)
        post = service.create_post('testuser', '<b>Title</b>', '<script>alert(1)</script>body')

        assert '<b>' not in post.title
        assert '<script>' not in post.body

    def test_get_post_not_found(self, service, mock_db):
        """測試取得不存在的貼文"""
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        result = service.get_post(999)
        assert result is None

    def test_list_posts(self, service, mock_db):
        """測試列出貼文"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.count.return_value = 3
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        posts, total = service.list_posts()
        assert total == 3

    def test_delete_post_success(self, service, mock_db):
        """測試成功刪除貼文"""
        mock_post = Mock(spec=Post)
        mock_post.author_username = 'testuser'
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_post

        result = service.delete_post(1, 'testuser')
        assert result is True
        mock_db.delete.assert_called_with(mock_post)

    def test_delete_post_not_owner_raises(self, service, mock_db):
        """測試非作者刪除貼文應拋出例外"""
        mock_post = Mock(spec=Post)
        mock_post.author_username = 'owner'
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_post

        with pytest.raises(ValueError, match="無權限刪除"):
            service.delete_post(1, 'other_user')

    def test_delete_post_not_found_raises(self, service, mock_db):
        """測試刪除不存在的貼文應拋出例外"""
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        with pytest.raises(ValueError, match="貼文不存在"):
            service.delete_post(999, 'testuser')


class TestEngagementServiceComments:
    """測試評論功能"""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    @pytest.fixture
    def service(self, mock_db):
        return EngagementService(mock_db)

    def test_add_comment_success(self, service, mock_db):
        """測試成功新增評論"""
        mock_post = Mock(spec=Post)
        mock_post.id = 1
        mock_post.comment_count = 0
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_post

        comment = service.add_comment(1, 'testuser', 'Great post!')
        assert isinstance(comment, PostComment)
        assert comment.content == 'Great post!'
        assert mock_post.comment_count == 1

    def test_add_comment_empty_content_raises(self, service, mock_db):
        """測試評論內容為空時應拋出例外"""
        mock_post = Mock(spec=Post)
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_post

        with pytest.raises(ValueError, match="評論內容不能為空"):
            service.add_comment(1, 'testuser', '')

    def test_add_comment_post_not_found_raises(self, service, mock_db):
        """測試貼文不存在時應拋出例外"""
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        with pytest.raises(ValueError, match="貼文不存在"):
            service.add_comment(999, 'testuser', 'content')

    def test_add_comment_with_reply(self, service, mock_db):
        """測試新增回覆評論"""
        mock_post = Mock(spec=Post)
        mock_post.id = 1
        mock_post.comment_count = 2
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_post

        comment = service.add_comment(1, 'testuser', 'Reply!', parent_comment_id=5)
        assert comment.parent_comment_id == 5

    def test_get_comments(self, service, mock_db):
        """測試取得評論列表"""
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        result = service.get_comments(1)
        assert isinstance(result, list)


class TestEngagementServiceLikes:
    """測試點讚功能"""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    @pytest.fixture
    def service(self, mock_db):
        return EngagementService(mock_db)

    def test_like_post_new(self, service, mock_db):
        """測試對貼文新增點讚"""
        mock_post = Mock(spec=Post)
        mock_post.id = 1
        mock_post.like_count = 5

        mock_query_post = MagicMock()
        mock_query_like = MagicMock()

        def query_side_effect(model):
            if model == Post:
                return mock_query_post
            elif model == PostLike:
                return mock_query_like
            return MagicMock()

        mock_db.query.side_effect = query_side_effect
        mock_query_post.filter_by.return_value.first.return_value = mock_post
        mock_query_like.filter_by.return_value.first.return_value = None

        result = service.like_post(1, 'testuser')
        assert result['liked'] is True
        assert result['like_count'] == 6

    def test_like_post_toggle_off(self, service, mock_db):
        """測試取消已點讚的貼文"""
        mock_post = Mock(spec=Post)
        mock_post.id = 1
        mock_post.like_count = 5
        mock_existing_like = Mock(spec=PostLike)

        mock_query_post = MagicMock()
        mock_query_like = MagicMock()

        def query_side_effect(model):
            if model == Post:
                return mock_query_post
            elif model == PostLike:
                return mock_query_like
            return MagicMock()

        mock_db.query.side_effect = query_side_effect
        mock_query_post.filter_by.return_value.first.return_value = mock_post
        mock_query_like.filter_by.return_value.first.return_value = mock_existing_like

        result = service.like_post(1, 'testuser')
        assert result['liked'] is False
        assert result['like_count'] == 4
        mock_db.delete.assert_called_with(mock_existing_like)

    def test_like_post_not_found_raises(self, service, mock_db):
        """測試對不存在的貼文點讚應拋出例外"""
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        with pytest.raises(ValueError, match="貼文不存在"):
            service.like_post(999, 'testuser')


class TestLevelCalculation:
    """測試等級計算邏輯"""

    def test_level_1_at_zero_points(self):
        """0 積分應為等級 1"""
        assert _calculate_level(0) == 1

    def test_level_increases_with_points(self):
        """積分增加應提升等級"""
        assert _calculate_level(50) >= 2
        assert _calculate_level(120) >= 3

    def test_title_for_level_1(self):
        """等級 1 應有預設稱號"""
        title = _get_title_for_level(1)
        assert isinstance(title, str)
        assert len(title) > 0

    def test_title_changes_with_level(self):
        """高等級應有不同稱號"""
        title_lv1 = _get_title_for_level(1)
        title_lv20 = _get_title_for_level(20)
        assert title_lv1 != title_lv20
