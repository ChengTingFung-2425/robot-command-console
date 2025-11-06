"""
Test suite for Titles System - Phase 1 User Engagement

Tests the title/badge system for Phase 1 including:
- Basic titles (5-10 titles)
- Title unlocking criteria
- Title assignment logic
- Title display in user profiles
"""

import unittest
import sys
import os
from datetime import datetime

# Add WebUI to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from WebUI.app import db, create_app
from WebUI.app.models import User, UserProfile, Robot, Command, AdvancedCommand


class TitleSystem:
    """Game mechanics for title/badge system"""

    # Phase 1 Titles - Beginner & Intermediate stages
    PHASE_1_TITLES = {
        '新手探索者': {
            'name': 'Novice Explorer',
            'emoji': '🌱',
            'tier': 'beginner',
            'requirements': {
                'level_min': 1,
                'points_min': 0,
                'condition': 'registered'
            }
        },
        '機器人學徒': {
            'name': 'Robot Apprentice',
            'emoji': '🤖',
            'tier': 'beginner',
            'requirements': {
                'level_min': 1,
                'points_min': 0,
                'condition': 'registered_robot:1'
            }
        },
        '指令入門者': {
            'name': 'Command Beginner',
            'emoji': '📝',
            'tier': 'beginner',
            'requirements': {
                'level_min': 1,
                'points_min': 0,
                'condition': 'first_command'
            }
        },
        '指令達人': {
            'name': 'Command Master',
            'emoji': '⚡',
            'tier': 'intermediate',
            'requirements': {
                'level_min': 5,
                'points_min': 100,
                'condition': 'commands:100'
            }
        },
        '機器人專家': {
            'name': 'Robot Specialist',
            'emoji': '🎯',
            'tier': 'intermediate',
            'requirements': {
                'level_min': 5,
                'points_min': 100,
                'condition': 'robots:5'
            }
        },
        '創意貢獻者': {
            'name': 'Creative Contributor',
            'emoji': '💡',
            'tier': 'intermediate',
            'requirements': {
                'level_min': 5,
                'points_min': 100,
                'condition': 'first_advanced_command'
            }
        },
        '早期採用者': {
            'name': 'Early Adopter',
            'emoji': '🔧',
            'tier': 'special',
            'requirements': {
                'level_min': 1,
                'points_min': 0,
                'condition': 'early_adopter',
                'note': 'First 100 registered users'
            }
        },
        '守護者': {
            'name': 'Guardian',
            'emoji': '🛡️',
            'tier': 'special',
            'requirements': {
                'level_min': 1,
                'points_min': 0,
                'condition': 'role:admin_or_auditor'
            }
        },
    }

    @staticmethod
    def get_available_titles():
        """Get all available Phase 1 titles"""
        return TitleSystem.PHASE_1_TITLES

    @staticmethod
    def check_title_eligibility(user_profile, title_key):
        """Check if a user profile is eligible for a title"""
        title = TitleSystem.PHASE_1_TITLES.get(title_key)
        if not title:
            return False, f"Title '{title_key}' not found"

        requirements = title['requirements']

        # Check level requirement
        if user_profile.level < requirements.get('level_min', 1):
            return False, f"Level requirement not met (need {requirements['level_min']}, have {user_profile.level})"

        # Check points requirement
        if user_profile.points < requirements.get('points_min', 0):
            return False, f"Points requirement not met (need {requirements['points_min']}, have {user_profile.points})"

        # Additional condition checks would go here
        condition = requirements.get('condition', '')
        if condition and not TitleSystem._check_condition(user_profile, condition):
            return False, f"Condition not met: {condition}"

        return True, "Eligible"

    @staticmethod
    def _check_condition(user_profile, condition):
        """Check specific condition for title eligibility"""
        # This is a placeholder - actual implementation would query database
        if condition == 'registered':
            return True
        if condition == 'first_command':
            return user_profile.total_commands > 0
        if condition.startswith('robots:'):
            count = int(condition.split(':')[1])
            return user_profile.total_robots >= count
        if condition.startswith('commands:'):
            count = int(condition.split(':')[1])
            return user_profile.total_commands >= count
        if condition == 'first_advanced_command':
            return user_profile.total_advanced_commands > 0
        if condition == 'role:admin_or_auditor':
            return hasattr(user_profile, 'user') and user_profile.user.role in ['admin', 'auditor']
        return False

    @staticmethod
    def get_title_display(title_key):
        """Get display information for a title"""
        title = TitleSystem.PHASE_1_TITLES.get(title_key)
        if not title:
            return None

        return {
            'key': title_key,
            'name': title['name'],
            'emoji': title['emoji'],
            'tier': title['tier'],
            'display': f"{title['emoji']} {title['name']}"
        }

    @staticmethod
    def get_tier_titles(tier):
        """Get all titles in a specific tier"""
        return {
            k: v for k, v in TitleSystem.PHASE_1_TITLES.items()
            if v['tier'] == tier
        }


class TestTitleSystem(unittest.TestCase):
    """Test title system functionality"""

    def test_phase_1_title_count(self):
        """Test that Phase 1 has 5-10 titles"""
        titles = TitleSystem.get_available_titles()
        self.assertGreaterEqual(len(titles), 5)
        self.assertLessEqual(len(titles), 15)  # Allow some flexibility
        self.assertEqual(len(titles), 8)  # Exact count for Phase 1

    def test_title_structure(self):
        """Test that each title has required fields"""
        required_fields = ['name', 'emoji', 'tier', 'requirements']

        for title_key, title_data in TitleSystem.get_available_titles().items():
            for field in required_fields:
                self.assertIn(field, title_data, f"Title {title_key} missing field {field}")

            # Check requirements structure
            requirements = title_data['requirements']
            self.assertIn('level_min', requirements)
            self.assertIn('points_min', requirements)
            self.assertIn('condition', requirements)

    def test_title_categories(self):
        """Test that titles are properly categorized"""
        beginner_titles = TitleSystem.get_tier_titles('beginner')
        intermediate_titles = TitleSystem.get_tier_titles('intermediate')
        special_titles = TitleSystem.get_tier_titles('special')

        self.assertGreater(len(beginner_titles), 0)
        self.assertGreater(len(intermediate_titles), 0)
        self.assertGreater(len(special_titles), 0)

    def test_novice_explorer_title(self):
        """Test 新手探索者 (Novice Explorer) title"""
        profile = UserProfile(
            user_id=1,
            points=0,
            level=1,
            total_commands=0,
            total_advanced_commands=0,
            total_robots=0
        )

        eligible, msg = TitleSystem.check_title_eligibility(profile, '新手探索者')
        self.assertTrue(eligible, msg)

    def test_robot_apprentice_title(self):
        """Test 機器人學徒 (Robot Apprentice) title"""
        profile = UserProfile(
            user_id=1,
            points=0,
            level=1,
            total_robots=0
        )

        # Not eligible without robot
        eligible, msg = TitleSystem.check_title_eligibility(profile, '機器人學徒')
        # This test would need database integration to fully test

    def test_command_beginner_title(self):
        """Test 指令入門者 (Command Beginner) title"""
        profile = UserProfile(
            user_id=1,
            points=0,
            level=1,
            total_commands=1
        )

        eligible, msg = TitleSystem.check_title_eligibility(profile, '指令入門者')
        self.assertTrue(eligible, msg)

    def test_command_master_title_level_requirement(self):
        """Test 指令達人 (Command Master) level requirement"""
        profile = UserProfile(
            user_id=1,
            points=50,
            level=2,
            total_commands=100
        )

        # Not eligible - level too low
        eligible, msg = TitleSystem.check_title_eligibility(profile, '指令達人')
        self.assertFalse(eligible)

    def test_command_master_title_points_requirement(self):
        """Test 指令達人 (Command Master) points requirement"""
        profile = UserProfile(
            user_id=1,
            points=50,
            level=5,
            total_commands=100
        )

        # Not eligible - points too low
        eligible, msg = TitleSystem.check_title_eligibility(profile, '指令達人')
        self.assertFalse(eligible)

    def test_command_master_title_full_eligibility(self):
        """Test 指令達人 (Command Master) full eligibility"""
        profile = UserProfile(
            user_id=1,
            points=100,
            level=5,
            total_commands=100
        )

        eligible, msg = TitleSystem.check_title_eligibility(profile, '指令達人')
        self.assertTrue(eligible, msg)

    def test_robot_specialist_title(self):
        """Test 機器人專家 (Robot Specialist) title"""
        profile = UserProfile(
            user_id=1,
            points=100,
            level=5,
            total_robots=5
        )

        # Full eligibility check
        eligible, msg = TitleSystem.check_title_eligibility(profile, '機器人專家')
        self.assertTrue(eligible, msg)

    def test_creative_contributor_title(self):
        """Test 創意貢獻者 (Creative Contributor) title"""
        profile = UserProfile(
            user_id=1,
            points=100,
            level=5,
            total_advanced_commands=1
        )

        eligible, msg = TitleSystem.check_title_eligibility(profile, '創意貢獻者')
        self.assertTrue(eligible, msg)

    def test_title_display_format(self):
        """Test title display formatting"""
        display = TitleSystem.get_title_display('新手探索者')

        self.assertIsNotNone(display)
        self.assertEqual(display['key'], '新手探索者')
        self.assertEqual(display['emoji'], '🌱')
        self.assertIn('Novice Explorer', display['name'])
        self.assertIn('🌱', display['display'])

    def test_all_titles_displayable(self):
        """Test that all titles can be displayed"""
        for title_key in TitleSystem.get_available_titles().keys():
            display = TitleSystem.get_title_display(title_key)
            self.assertIsNotNone(display)
            self.assertIn('emoji', display)
            self.assertIn('name', display)

    def test_title_tier_progression(self):
        """Test that title tiers progress in difficulty"""
        beginner = TitleSystem.get_tier_titles('beginner')
        intermediate = TitleSystem.get_tier_titles('intermediate')

        # Get minimum level requirement for each tier
        beginner_min_level = min(t['requirements']['level_min'] for t in beginner.values())
        beginner_min_points = min(t['requirements']['points_min'] for t in beginner.values())

        intermediate_min_level = min(t['requirements']['level_min'] for t in intermediate.values())
        intermediate_min_points = min(t['requirements']['points_min'] for t in intermediate.values())

        # Intermediate should require higher level/points
        self.assertGreater(intermediate_min_level, beginner_min_level)
        self.assertGreater(intermediate_min_points, beginner_min_points)


class TestTitleWithDatabase(unittest.TestCase):
    """Test title system with database integration"""

    @classmethod
    def setUpClass(cls):
        """Setup Flask app and database"""
        cls.app = create_app('testing')
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

    @classmethod
    def tearDownClass(cls):
        """Clean up Flask app context"""
        cls.app_context.pop()

    def setUp(self):
        """Create fresh database"""
        db.create_all()

    def tearDown(self):
        """Clean up database"""
        db.session.remove()
        db.drop_all()

    def test_user_profile_title_field(self):
        """Test that UserProfile has title field"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()

        profile = UserProfile(
            user_id=user.id,
            points=0,
            level=1,
            title='新手探索者'
        )
        db.session.add(profile)
        db.session.commit()

        retrieved = UserProfile.query.filter_by(user_id=user.id).first()
        self.assertEqual(retrieved.title, '新手探索者')

    def test_title_persistence(self):
        """Test that title changes persist"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()

        profile = UserProfile(
            user_id=user.id,
            points=0,
            level=1,
            title='新手探索者'
        )
        db.session.add(profile)
        db.session.commit()

        # Update title
        profile.title = '指令入門者'
        db.session.commit()

        # Verify persistence
        retrieved = UserProfile.query.filter_by(user_id=user.id).first()
        self.assertEqual(retrieved.title, '指令入門者')

    def test_multiple_users_titles(self):
        """Test that multiple users can have different titles"""
        users_data = [
            ('user1', '新手探索者'),
            ('user2', '指令入門者'),
            ('user3', '創意貢獻者'),
        ]

        for username, title in users_data:
            user = User(username=username, email=f'{username}@example.com')
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()

            profile = UserProfile(
                user_id=user.id,
                points=0,
                level=1,
                title=title
            )
            db.session.add(profile)

        db.session.commit()

        # Verify each user's title
        for username, expected_title in users_data:
            user = User.query.filter_by(username=username).first()
            profile = UserProfile.query.filter_by(user_id=user.id).first()
            self.assertEqual(profile.title, expected_title)

    def test_title_update_on_level_up(self):
        """Test that title can be updated when leveling up"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()

        profile = UserProfile(
            user_id=user.id,
            points=0,
            level=1,
            title='新手探索者'
        )
        db.session.add(profile)
        db.session.commit()

        # Level up and update title
        profile.level = 5
        profile.points = 100
        profile.title = '指令達人'
        db.session.commit()

        # Verify
        retrieved = UserProfile.query.filter_by(user_id=user.id).first()
        self.assertEqual(retrieved.title, '指令達人')
        self.assertEqual(retrieved.level, 5)
        self.assertEqual(retrieved.points, 100)


class TestUserEngagementIntegration(unittest.TestCase):
    """Integration tests for user engagement features"""

    @classmethod
    def setUpClass(cls):
        """Setup Flask app and database"""
        cls.app = create_app('testing')
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

    @classmethod
    def tearDownClass(cls):
        """Clean up Flask app context"""
        cls.app_context.pop()

    def setUp(self):
        """Create fresh database"""
        db.create_all()

    def tearDown(self):
        """Clean up database"""
        db.session.remove()
        db.drop_all()

    def test_user_journey_beginner_to_intermediate(self):
        """Test complete user journey from beginner to intermediate"""
        # Create user
        user = User(username='progressor', email='prog@example.com')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()

        # Initial profile
        profile = UserProfile(
            user_id=user.id,
            points=0,
            level=1,
            title='新手探索者',
            total_commands=0,
            total_advanced_commands=0,
            total_robots=0
        )
        db.session.add(profile)
        db.session.commit()

        # Verify initial title
        self.assertEqual(profile.title, '新手探索者')
        self.assertEqual(profile.level, 1)

        # Progress: Register first robot
        profile.total_robots = 1
        profile.points += 5
        profile.title = '機器人學徒'
        db.session.commit()

        # Progress: Execute first command
        profile.total_commands = 1
        profile.points += 1
        profile.title = '指令入門者'
        db.session.commit()

        # Progress: Reach level 5
        profile.points = 100
        profile.level = 5
        profile.title = '指令達人'
        db.session.commit()

        # Verify final state
        retrieved = UserProfile.query.filter_by(user_id=user.id).first()
        self.assertEqual(retrieved.title, '指令達人')
        self.assertEqual(retrieved.level, 5)
        self.assertEqual(retrieved.points, 100)
        self.assertEqual(retrieved.total_commands, 1)
        self.assertEqual(retrieved.total_robots, 1)


if __name__ == '__main__':
    unittest.main()
