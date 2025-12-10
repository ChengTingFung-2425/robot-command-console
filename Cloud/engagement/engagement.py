"""
User Engagement & Gamification utilities.

Handles point awards, achievement tracking, and level management.

⚠️ 重要：此檔案已從 WebUI 移動到 Cloud 服務但尚未完成重構
==========================================

遷移狀態：已移動但功能不可用
需要完成的工作：
1. 在 Cloud/models.py 建立獨立的資料模型：
   - User
   - UserProfile
   - Achievement
   - UserAchievement
2. 建立獨立的資料庫連接（PostgreSQL）
3. 移除所有對 WebUI.app 的引用
4. 更新所有函式的型別提示
5. 建立 Cloud API 端點來暴露這些功能

目前此檔案中的函式因缺少依賴而無法運作。
"""

from typing import Optional, List

# TODO: 此檔案需要在 Cloud 服務中重構
# 需要建立獨立的 Cloud/models.py 和資料庫配置
# 暫時註解掉直接依賴 WebUI 的程式碼

# from WebUI.app import db  # 已移除 - 造成架構依賴問題
# from WebUI.app.models import User, UserProfile, Achievement, UserAchievement  # 已移除

# 注意：以下程式碼因缺少上述依賴而無法運作
# 這是一個佔位符，展示需要在 Cloud 服務中實作的功能

# Points award values (from design document)
POINTS_AWARD = {
    'registration': 10,
    'robot_registration': 5,
    'command_execution': 1,
    'advanced_command_submission': 20,
    'advanced_command_approval': 50,
    'advanced_command_usage': 5,
    'advanced_command_rating': 2,
    'daily_task': 10,
}


def get_or_create_user_profile(user):
    """Get or create a user profile for the given user.
    
    ⚠️ 尚未重構，待 Cloud 服務資料模型與資料庫完成後實作。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")


def award_points(user_id: int, reason: str, amount: Optional[int] = None):
    """
    Award points to a user for a specific action.
    
    ⚠️ 尚未重構，待 Cloud 服務資料模型與資料庫完成後實作。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")


def award_on_registration(user_id: int):
    """Award points when a user registers.
    
    ⚠️ 尚未重構，待 Cloud 服務重構完成。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")


def award_on_robot_registration(user_id: int):
    """Award points when a user registers a robot.
    
    ⚠️ 尚未重構，待 Cloud 服務重構完成。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")


def award_on_command_execution(user_id: int):
    """Award points when a user executes a command.
    
    ⚠️ 尚未重構，待 Cloud 服務重構完成。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")


def award_on_advanced_command_submission(user_id: int):
    """Award points when a user submits an advanced command.
    
    ⚠️ 尚未重構，待 Cloud 服務重構完成。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")


def award_on_advanced_command_approval(user_id: int):
    """Award points when a user's advanced command is approved.
    
    ⚠️ 尚未重構，待 Cloud 服務重構完成。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")


def award_on_command_usage(user_id: int):
    """Award points when a user's advanced command is used.
    
    ⚠️ 尚未重構，待 Cloud 服務重構完成。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")


def award_on_command_rating(user_id: int):
    """Award points when a user's advanced command receives a good rating.
    
    ⚠️ 尚未重構，待 Cloud 服務重構完成。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")


def award_custom(user_id: int, amount: int, reason: str = "Manual award"):
    """Award custom amount of points (for admin use).
    
    ⚠️ 尚未重構，待 Cloud 服務重構完成。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")


def update_command_stats(user_id: int, command_count: Optional[int] = None):
    """Update command execution statistics.
    
    ⚠️ 尚未重構，待 Cloud 服務重構完成。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")


def update_robot_stats(user_id: int):
    """Update robot management statistics.
    
    ⚠️ 尚未重構，待 Cloud 服務重構完成。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")


def update_advanced_command_stats(user_id: int):
    """Update advanced command contribution statistics.
    
    ⚠️ 尚未重構，待 Cloud 服務重構完成。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")


def grant_achievement(user_id: int, achievement_id: int):
    """
    Grant an achievement to a user.
    
    ⚠️ 尚未重構，待 Cloud 服務重構完成。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")


def grant_achievement_by_name(user_id: int, achievement_name: str):
    """Grant an achievement to a user by name.
    
    ⚠️ 尚未重構，待 Cloud 服務重構完成。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")


def get_user_achievements(user_id: int):
    """Get all achievements earned by a user.
    
    ⚠️ 尚未重構，待 Cloud 服務重構完成。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")


def get_available_achievements_for_user(user_id: int):
    """Get achievements not yet earned by a user.
    
    ⚠️ 尚未重構，待 Cloud 服務重構完成。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")


def initialize_achievements():
    """Initialize default achievements in the database.
    
    ⚠️ 尚未重構，待 Cloud 服務重構完成。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")


def get_leaderboard(limit: int = 10, sort_by: str = 'points'):
    """
    Get leaderboard of top users.
    
    ⚠️ 尚未重構，待 Cloud 服務重構完成。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")

