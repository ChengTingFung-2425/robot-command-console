"""
User Engagement & Gamification utilities.

Handles point awards, achievement tracking, and level management.
此模組提供積分獎勵的便利包裝函式，業務邏輯由 EngagementService 負責。
"""

# imports
from typing import Optional

from Cloud.engagement.service import POINTS_AWARD, EngagementService  # noqa: F401


def award_points(service: EngagementService, user_username: str, reason: str, amount: Optional[int] = None):
    """Give points to a user for a specific action.

    Args:
        service: EngagementService 實例（需已持有有效的 db session）
        user_username: 用戶名稱
        reason: 積分原因（對應 POINTS_AWARD 的 key 或自訂文字）
        amount: 積分數量（若不指定，使用 POINTS_AWARD 預設值）

    Returns:
        更新後的 UserEngagementProfile
    """
    return service.award_points(user_username, reason, amount)


def award_on_registration(service: EngagementService, user_username: str):
    """Award points when a user registers."""
    return service.award_points(user_username, 'registration')


def award_on_robot_registration(service: EngagementService, user_username: str):
    """Award points when a user registers a robot."""
    return service.award_points(user_username, 'robot_registration')


def award_on_command_execution(service: EngagementService, user_username: str):
    """Award points when a user executes a command."""
    return service.award_points(user_username, 'command_execution')


def award_on_advanced_command_submission(service: EngagementService, user_username: str):
    """Award points when a user submits an advanced command."""
    return service.award_points(user_username, 'advanced_command_submission')


def award_on_advanced_command_approval(service: EngagementService, user_username: str):
    """Award points when a user's advanced command is approved."""
    return service.award_points(user_username, 'advanced_command_approval')


def award_on_command_usage(service: EngagementService, user_username: str):
    """Award points when a user's advanced command is used."""
    return service.award_points(user_username, 'advanced_command_usage')


def award_on_command_rating(service: EngagementService, user_username: str):
    """Award points when a user's advanced command receives a good rating."""
    return service.award_points(user_username, 'advanced_command_rating')


def get_leaderboard(service: EngagementService, limit: int = 10, sort_by: str = 'points'):
    """Get leaderboard of top users.

    Args:
        service: EngagementService 實例
        limit: 回傳筆數
        sort_by: 排序欄位（points/level/reputation/commands）

    Returns:
        List[UserEngagementProfile]
    """
    return service.get_leaderboard(limit=limit, sort_by=sort_by)

