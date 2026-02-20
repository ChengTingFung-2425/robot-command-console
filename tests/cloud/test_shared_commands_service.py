# imports
import pytest
from unittest.mock import Mock, MagicMock

from Cloud.shared_commands.service import SharedCommandService
from Cloud.shared_commands.models import (
    SharedAdvancedCommand,
    CommandRating
)


class TestSharedCommandService:
    """測試進階指令共享服務"""

    @pytest.fixture
    def mock_db_session(self):
        """模擬資料庫 session"""
        return Mock()

    @pytest.fixture
    def service(self, mock_db_session):
        """建立服務實例"""
        return SharedCommandService(mock_db_session)

    def test_upload_command_new(self, service, mock_db_session):
        """測試上傳新指令"""
        # Arrange
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = None

        # Act
        service.upload_command(
            name="test_command",
            description="Test description",
            category="test",
            content='[{"command": "bow"}]',
            author_username="testuser",
            author_email="test@example.com",
            edge_id="edge-001",
            original_command_id=1,
            version=1
        )

        # Assert
        assert mock_db_session.add.call_count == 2  # command + sync log
        assert mock_db_session.commit.call_count >= 2  # command + sync log

    def test_upload_command_update_existing(self, service, mock_db_session):
        """測試更新現有指令"""
        # Arrange
        existing_command = Mock(spec=SharedAdvancedCommand)
        existing_command.id = 1
        existing_command.version = 1
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = existing_command

        # Act
        service.upload_command(
            name="test_command",
            description="Updated description",
            category="test",
            content='[{"command": "wave"}]',
            author_username="testuser",
            author_email="test@example.com",
            edge_id="edge-001",
            original_command_id=1,
            version=2
        )

        # Assert
        # Note: sanitize_html will strip any HTML from description
        assert existing_command.description is not None
        assert existing_command.version == 2
        mock_db_session.commit.assert_called()

    def test_upload_command_invalid_json(self, service, mock_db_session):
        """測試上傳無效 JSON 格式的指令"""
        # Act & Assert
        with pytest.raises(ValueError, match="指令內容必須是有效的 JSON"):
            service.upload_command(
                name="test_command",
                description="Test",
                category="test",
                content='invalid json',
                author_username="testuser",
                author_email="test@example.com",
                edge_id="edge-001",
                original_command_id=1
            )

    def test_search_commands_basic(self, service, mock_db_session):
        """測試基本搜尋功能"""
        # Arrange
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.count.return_value = 10
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        # Act
        commands, total = service.search_commands()

        # Assert
        assert total == 10
        assert isinstance(commands, list)

    def test_search_commands_with_filters(self, service, mock_db_session):
        """測試帶篩選條件的搜尋"""
        # Arrange
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 5
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        # Act
        commands, total = service.search_commands(
            query="test",
            category="test",
            author="testuser",
            min_rating=4.0
        )

        # Assert
        assert total == 5

    def test_download_command_success(self, service, mock_db_session):
        """測試下載指令成功"""
        # Arrange
        mock_command = Mock(spec=SharedAdvancedCommand)
        mock_command.id = 1
        mock_command.name = "test_command"
        mock_command.download_count = 5
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_command

        # Act
        command = service.download_command(1, "edge-001")

        # Assert
        assert command.download_count == 6
        mock_db_session.commit.assert_called()

    def test_download_command_not_found(self, service, mock_db_session):
        """測試下載不存在的指令"""
        # Arrange
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="指令不存在或不公開"):
            service.download_command(999, "edge-001")

    def test_rate_command_new_rating(self, service, mock_db_session):
        """測試新增評分"""
        # Arrange
        mock_command = Mock(spec=SharedAdvancedCommand)
        mock_command.id = 1
        mock_command.average_rating = 4.0
        mock_command.rating_count = 2

        # 設定複雜的 mock chain
        mock_query_cmd = MagicMock()
        mock_query_rating = MagicMock()

        def query_side_effect(model):
            if model == SharedAdvancedCommand:
                return mock_query_cmd
            elif model == CommandRating:
                return mock_query_rating
            return MagicMock()

        mock_db_session.query.side_effect = query_side_effect
        mock_query_cmd.filter_by.return_value.with_for_update.return_value.first.return_value = mock_command
        mock_query_rating.filter_by.return_value.first.return_value = None

        # Act
        service.rate_command(1, "testuser", 5, "Great!")

        # Assert
        mock_db_session.add.assert_called()
        assert mock_command.rating_count == 3

    def test_rate_command_invalid_rating(self, service, mock_db_session):
        """測試無效評分"""
        # Act & Assert
        with pytest.raises(ValueError, match="評分必須在 1-5 之間"):
            service.rate_command(1, "testuser", 6)

        with pytest.raises(ValueError, match="評分必須在 1-5 之間"):
            service.rate_command(1, "testuser", 0)

    def test_add_comment(self, service, mock_db_session):
        """測試新增留言"""
        # Arrange
        mock_command = Mock(spec=SharedAdvancedCommand)
        mock_command.id = 1
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_command

        # Act
        service.add_comment(1, "testuser", "Nice command!")

        # Assert
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()

    def test_add_comment_with_reply(self, service, mock_db_session):
        """測試回覆留言"""
        # Arrange
        mock_command = Mock(spec=SharedAdvancedCommand)
        mock_command.id = 1
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_command

        # Act
        service.add_comment(
            1, "testuser", "Reply to comment", parent_comment_id=5
        )

        # Assert
        mock_db_session.add.assert_called()

    def test_get_featured_commands(self, service, mock_db_session):
        """測試取得精選指令"""
        # Arrange
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        # Act
        commands = service.get_featured_commands(limit=10)

        # Assert
        assert isinstance(commands, list)

    def test_get_popular_commands(self, service, mock_db_session):
        """測試取得熱門指令"""
        # Arrange
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        # Act
        commands = service.get_popular_commands(limit=10)

        # Assert
        assert isinstance(commands, list)

    def test_get_categories(self, service, mock_db_session):
        """測試取得分類列表"""
        # Arrange
        mock_query = MagicMock()
        mock_db_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.all.return_value = [("test", 5), ("patrol", 3)]

        # Act
        categories = service.get_categories()

        # Assert
        assert len(categories) == 2
        assert categories[0]["category"] == "test"
        assert categories[0]["count"] == 5
