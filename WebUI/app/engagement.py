"""
User Engagement & Gamification utilities.

Handles point awards, achievement tracking, and level management.
"""

from typing import Optional, List
from WebUI.app import db
from WebUI.app.models import User, UserProfile, Achievement, UserAchievement


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


def get_or_create_user_profile(user: User) -> UserProfile:
    """Get or create a user profile for the given user."""
    profile = user.profile
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
    return profile


def award_points(user_id: int, reason: str, amount: Optional[int] = None) -> UserProfile:
    """
    Award points to a user for a specific action.

    Args:
        user_id: The ID of the user to award points to
        reason: The reason for awarding points (e.g., 'registration', 'command_execution')
        amount: Optional custom amount; if not provided, uses POINTS_AWARD[reason]

    Returns:
        Updated UserProfile instance
    """
    user = User.query.get(user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found")

    profile = get_or_create_user_profile(user)

    # Determine points to award
    if amount is None:
        if reason not in POINTS_AWARD:
            raise ValueError(f"Unknown reason: {reason}. Valid reasons: {list(POINTS_AWARD.keys())}")
        amount = POINTS_AWARD[reason]

    if amount <= 0:
        return profile

    profile.add_points(amount)
    db.session.commit()

    return profile


def award_on_registration(user_id: int) -> UserProfile:
    """Award points when a user registers."""
    return award_points(user_id, 'registration')


def award_on_robot_registration(user_id: int) -> UserProfile:
    """Award points when a user registers a robot."""
    profile = award_points(user_id, 'robot_registration')
    # Update stats
    profile.total_robots = User.query.get(user_id).robots.count()
    db.session.commit()
    return profile


def award_on_command_execution(user_id: int) -> UserProfile:
    """Award points when a user executes a command."""
    return award_points(user_id, 'command_execution')


def award_on_advanced_command_submission(user_id: int) -> UserProfile:
    """Award points when a user submits an advanced command."""
    profile = award_points(user_id, 'advanced_command_submission')
    # Update stats
    from WebUI.app.models import AdvancedCommand
    profile.total_advanced_commands = AdvancedCommand.query.filter_by(author_id=user_id).count()
    db.session.commit()
    return profile


def award_on_advanced_command_approval(user_id: int) -> UserProfile:
    """Award points when a user's advanced command is approved."""
    return award_points(user_id, 'advanced_command_approval')


def award_on_command_usage(user_id: int) -> UserProfile:
    """Award points when a user's advanced command is used."""
    return award_points(user_id, 'advanced_command_usage')


def award_on_command_rating(user_id: int) -> UserProfile:
    """Award points when a user's advanced command receives a good rating."""
    return award_points(user_id, 'advanced_command_rating')


def award_custom(user_id: int, amount: int, reason: str = "Manual award") -> UserProfile:
    """Award custom amount of points (for admin use)."""
    return award_points(user_id, f"custom_{reason}", amount=amount)


def update_command_stats(user_id: int, command_count: Optional[int] = None) -> Optional[UserProfile]:
    """Update command execution statistics."""
    user = User.query.get(user_id)
    if not user:
        return None

    profile = get_or_create_user_profile(user)

    if command_count is not None:
        profile.total_commands = command_count
    else:
        # Count from database
        from WebUI.app.models import Command
        profile.total_commands = Command.query.filter_by(user_id=user_id).count()

    db.session.commit()
    return profile


def update_robot_stats(user_id: int) -> Optional[UserProfile]:
    """Update robot management statistics."""
    user = User.query.get(user_id)
    if not user:
        return None

    profile = get_or_create_user_profile(user)
    profile.total_robots = user.robots.count()
    db.session.commit()
    return profile


def update_advanced_command_stats(user_id: int) -> Optional[UserProfile]:
    """Update advanced command contribution statistics."""
    from WebUI.app.models import AdvancedCommand
    user = User.query.get(user_id)
    if not user:
        return None

    profile = get_or_create_user_profile(user)
    profile.total_advanced_commands = AdvancedCommand.query.filter_by(author_id=user_id).count()
    db.session.commit()
    return profile


def grant_achievement(user_id: int, achievement_id: int) -> Optional[UserAchievement]:
    """
    Grant an achievement to a user.

    Returns:
        UserAchievement instance if newly granted, or None if already had it
    """
    user = User.query.get(user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found")

    achievement = Achievement.query.get(achievement_id)
    if not achievement:
        raise ValueError(f"Achievement with ID {achievement_id} not found")

    # Check if user already has this achievement
    existing = UserAchievement.query.filter_by(
        user_id=user_id,
        achievement_id=achievement_id
    ).first()

    if existing:
        return None  # Already has this achievement

    user_achievement = UserAchievement(user_id=user_id, achievement_id=achievement_id)
    db.session.add(user_achievement)
    db.session.commit()

    return user_achievement


def grant_achievement_by_name(user_id: int, achievement_name: str) -> UserAchievement:
    """Grant an achievement to a user by name."""
    achievement = Achievement.query.filter_by(name=achievement_name).first()
    if not achievement:
        raise ValueError(f"Achievement '{achievement_name}' not found")

    return grant_achievement(user_id, achievement.id)


def get_user_achievements(user_id: int) -> list:
    """Get all achievements earned by a user."""
    achievements = db.session.query(Achievement).join(
        UserAchievement
    ).filter(
        UserAchievement.user_id == user_id
    ).all()
    return achievements


def get_available_achievements_for_user(user_id: int) -> list:
    """Get achievements not yet earned by a user."""
    earned_ids = db.session.query(UserAchievement.achievement_id).filter(
        UserAchievement.user_id == user_id
    ).all()
    earned_ids = [aid[0] for aid in earned_ids]

    available = Achievement.query.filter(
        ~Achievement.id.in_(earned_ids)
    ).all()

    return available


def initialize_achievements():
    """Initialize default achievements in the database."""
    default_achievements = [
        # Exploration achievements
        Achievement(
            name='Novice Explorer',
            emoji='🌱',
            description='Register and complete first login',
            category='exploration',
            points_required=0,
            is_title=True
        ),
        Achievement(
            name='Robot Apprentice',
            emoji='🤖',
            description='Register your first robot',
            category='exploration',
            points_required=0,
            is_title=True
        ),
        Achievement(
            name='Command Beginner',
            emoji='📝',
            description='Execute your first command',
            category='exploration',
            points_required=0,
            is_title=True
        ),
        # Intermediate achievements
        Achievement(
            name='Command Master',
            emoji='⚡',
            description='Execute 100+ commands',
            category='exploration',
            points_required=100,
            is_title=True
        ),
        Achievement(
            name='Robot Specialist',
            emoji='🎯',
            description='Manage 5+ robots',
            category='exploration',
            points_required=150,
            is_title=True
        ),
        Achievement(
            name='Creative Contributor',
            emoji='💡',
            description='Submit your first advanced command',
            category='contribution',
            points_required=0,
            is_title=True
        ),
        # Expert achievements
        Achievement(
            name='Platform Guru',
            emoji='🏆',
            description='10+ approved advanced commands',
            category='contribution',
            points_required=500,
            is_title=True
        ),
        Achievement(
            name='Community Leader',
            emoji='🌟',
            description='Advanced commands used 100+ times',
            category='contribution',
            points_required=750,
            is_title=True
        ),
        Achievement(
            name='Legendary Developer',
            emoji='👑',
            description='50+ contributed advanced commands with 4.5+ rating',
            category='contribution',
            points_required=1000,
            is_title=True
        ),
        # Special achievements
        Achievement(
            name='Guardian',
            emoji='🛡️',
            description='Admin or Auditor role',
            category='special',
            points_required=0,
            is_title=True
        ),
        Achievement(
            name='Helpful Soul',
            emoji='🤝',
            description='Receive 50+ thanks from community',
            category='social',
            points_required=200,
            is_title=False
        ),
        Achievement(
            name='Active Discussant',
            emoji='💬',
            description='Leave 100+ comments on advanced commands',
            category='social',
            points_required=150,
            is_title=False
        ),
        Achievement(
            name='Efficiency Master',
            emoji='⏱️',
            description='Execute 100+ commands in a single day',
            category='challenge',
            points_required=50,
            is_title=False
        ),
    ]

    for achievement_data in default_achievements:
        # Check if achievement already exists
        existing = Achievement.query.filter_by(name=achievement_data.name).first()
        if not existing:
            db.session.add(achievement_data)

    db.session.commit()


def get_leaderboard(limit: int = 10, sort_by: str = 'points') -> List[tuple]:
    """
    Get leaderboard of top users.

    Args:
        limit: Number of top users to return
        sort_by: Sort criteria ('points', 'level', 'reputation', 'commands')

    Returns:
        List of (User, UserProfile) tuples
    """
    query = db.session.query(User, UserProfile).filter(User.id == UserProfile.user_id)

    if sort_by == 'points':
        query = query.order_by(UserProfile.points.desc())  # type: ignore
    elif sort_by == 'level':
        query = query.order_by(UserProfile.level.desc(), UserProfile.points.desc())  # type: ignore
    elif sort_by == 'reputation':
        query = query.order_by(UserProfile.reputation.desc())  # type: ignore
    elif sort_by == 'commands':
        query = query.order_by(UserProfile.total_commands.desc())  # type: ignore
    else:
        query = query.order_by(UserProfile.points.desc())  # type: ignore

    return query.limit(limit).all()

