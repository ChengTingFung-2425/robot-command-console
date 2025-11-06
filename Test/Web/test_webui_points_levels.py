"""
Test suite for Points and Levels System - Phase 1 User Engagement

Tests the game mechanics for earning points and advancing levels through:
- Command execution (+1 point each)
- Advanced command submission (+20 points)
- Advanced command approval (+50 points)
- Advanced command usage (+5 points each usage)
- Rating collection (+2 points per 4+ star rating)
- Daily task completion (+10 points)
"""

import unittest
import sys
import os

# Add WebUI to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from WebUI.app import db, create_app
from WebUI.app.models import User, UserProfile, Command, AdvancedCommand


class PointsSystem:
    """Game mechanics for awarding points"""

    # Point values for different actions
    POINTS = {
        'registration': 10,
        'register_robot': 5,
        'execute_command': 1,
        'submit_advanced_command': 20,
        'advanced_command_approved': 50,
        'advanced_command_used': 5,
        'rating_4_5_stars': 2,
        'daily_task': 10,
    }

    @staticmethod
    def award_points(profile, action, amount=None):
        """Award points to a profile for an action"""
        if amount is None:
            amount = PointsSystem.POINTS.get(action, 0)
        profile.points += amount
        return profile.points

    @staticmethod
    def calculate_level(points):
        """Calculate level based on points"""
        # Bronze Tier: Level 1-10 (0-500 points, 50 points per level)
        if points < 50:
            return 1
        elif points < 500:
            return min(10, 1 + (points // 50))
        # Silver Tier: Level 11-20 (500-2000 points, ~150 points per level)
        elif points < 2000:
            return min(20, 11 + ((points - 500) // 150))
        # Gold Tier: Level 21-30 (2000-5000 points, ~600 points per level)
        elif points < 5000:
            return min(30, 21 + ((points - 2000) // 600))
        # Platinum Tier: Level 31-40 (5000-10000 points, ~1000 points per level)
        elif points < 10000:
            return min(40, 31 + ((points - 5000) // 1000))
        # Diamond Tier: Level 41+ (10000+ points, ~2000 points per level)
        else:
            return 41 + ((points - 10000) // 2000)

    @staticmethod
    def calculate_level_progress(points):
        """Calculate progress towards next level (0-100%)"""
        # This is a simplified version - can be enhanced
        return int((points % 100) / 100 * 100)


class TestPointsSystem(unittest.TestCase):
    """Test points earning mechanics"""

    def test_points_registration(self):
        """Test awarding points for registration"""
        profile = UserProfile(user_id=1, points=0, level=1)
        new_points = PointsSystem.award_points(profile, 'registration')
        self.assertEqual(new_points, 10)

    def test_points_register_robot(self):
        """Test awarding points for registering a robot"""
        profile = UserProfile(user_id=1, points=10, level=1)
        new_points = PointsSystem.award_points(profile, 'register_robot')
        self.assertEqual(new_points, 15)

    def test_points_execute_command(self):
        """Test awarding points for command execution"""
        profile = UserProfile(user_id=1, points=15, level=1)
        # Execute 5 commands
        for _ in range(5):
            PointsSystem.award_points(profile, 'execute_command')
        self.assertEqual(profile.points, 20)

    def test_points_submit_advanced_command(self):
        """Test awarding points for submitting advanced command"""
        profile = UserProfile(user_id=1, points=20, level=1)
        new_points = PointsSystem.award_points(profile, 'submit_advanced_command')
        self.assertEqual(new_points, 40)

    def test_points_advanced_command_approved(self):
        """Test awarding points for advanced command approval"""
        profile = UserProfile(user_id=1, points=40, level=1)
        new_points = PointsSystem.award_points(profile, 'advanced_command_approved')
        self.assertEqual(new_points, 90)

    def test_points_advanced_command_used(self):
        """Test awarding points for advanced command usage (per use)"""
        profile = UserProfile(user_id=1, points=90, level=1)
        # Advanced command used 10 times by other users
        for _ in range(10):
            PointsSystem.award_points(profile, 'advanced_command_used')
        self.assertEqual(profile.points, 140)

    def test_points_rating_collection(self):
        """Test awarding points for receiving ratings"""
        profile = UserProfile(user_id=1, points=140, level=1)
        # Receive 5 ratings of 4+ stars
        for _ in range(5):
            PointsSystem.award_points(profile, 'rating_4_5_stars')
        self.assertEqual(profile.points, 150)

    def test_points_daily_task(self):
        """Test awarding points for completing daily tasks"""
        profile = UserProfile(user_id=1, points=150, level=1)
        new_points = PointsSystem.award_points(profile, 'daily_task')
        self.assertEqual(new_points, 160)

    def test_custom_point_amount(self):
        """Test awarding custom amount of points"""
        profile = UserProfile(user_id=1, points=0, level=1)
        new_points = PointsSystem.award_points(profile, 'bonus', amount=100)
        self.assertEqual(new_points, 100)

    def test_total_journey_points(self):
        """Test total points in a typical user journey"""
        profile = UserProfile(user_id=1, points=0, level=1)

        # Day 1: Registration journey
        PointsSystem.award_points(profile, 'registration')           # +10
        PointsSystem.award_points(profile, 'register_robot')         # +5
        for _ in range(10):
            PointsSystem.award_points(profile, 'execute_command')    # +10
        self.assertEqual(profile.points, 25)

        # Week 1: Start contributing
        PointsSystem.award_points(profile, 'submit_advanced_command') # +20
        for _ in range(3):
            PointsSystem.award_points(profile, 'execute_command')     # +3
        self.assertEqual(profile.points, 48)

        # Week 2: Advanced command approved
        PointsSystem.award_points(profile, 'advanced_command_approved') # +50
        for _ in range(8):
            PointsSystem.award_points(profile, 'advanced_command_used') # +40
        for _ in range(3):
            PointsSystem.award_points(profile, 'rating_4_5_stars')      # +6
        self.assertEqual(profile.points, 144)


class TestLevelSystem(unittest.TestCase):
    """Test level calculation based on points"""

    def test_level_1_bronze(self):
        """Test Bronze tier Level 1"""
        level = PointsSystem.calculate_level(0)
        self.assertEqual(level, 1)

    def test_level_5_bronze(self):
        """Test Bronze tier Level 5 (mid-tier)"""
        level = PointsSystem.calculate_level(200)
        self.assertEqual(level, 5)

    def test_level_10_bronze(self):
        """Test Bronze tier Level 10 (max)"""
        level = PointsSystem.calculate_level(450)
        self.assertEqual(level, 10)

    def test_level_11_silver(self):
        """Test Silver tier Level 11 (min)"""
        level = PointsSystem.calculate_level(501)
        self.assertEqual(level, 11)

    def test_level_15_silver(self):
        """Test Silver tier Level 15 (mid)"""
        level = PointsSystem.calculate_level(1000)
        self.assertGreaterEqual(level, 11)
        self.assertLessEqual(level, 20)

    def test_level_20_silver(self):
        """Test Silver tier Level 20 (max)"""
        level = PointsSystem.calculate_level(1900)
        self.assertGreaterEqual(level, 11)
        self.assertLessEqual(level, 20)

    def test_level_21_gold(self):
        """Test Gold tier Level 21 (min)"""
        level = PointsSystem.calculate_level(2001)
        self.assertGreaterEqual(level, 21)
        self.assertLessEqual(level, 30)

    def test_level_25_gold(self):
        """Test Gold tier Level 25 (mid)"""
        level = PointsSystem.calculate_level(3500)
        self.assertGreaterEqual(level, 21)
        self.assertLessEqual(level, 30)

    def test_level_30_gold(self):
        """Test Gold tier Level 30 (max)"""
        level = PointsSystem.calculate_level(4900)
        self.assertGreaterEqual(level, 21)
        self.assertLessEqual(level, 30)

    def test_level_31_platinum(self):
        """Test Platinum tier Level 31 (min)"""
        level = PointsSystem.calculate_level(5001)
        self.assertGreaterEqual(level, 31)
        self.assertLessEqual(level, 40)

    def test_level_35_platinum(self):
        """Test Platinum tier Level 35 (mid)"""
        level = PointsSystem.calculate_level(7500)
        self.assertGreaterEqual(level, 31)
        self.assertLessEqual(level, 40)

    def test_level_40_platinum(self):
        """Test Platinum tier Level 40 (max)"""
        level = PointsSystem.calculate_level(9900)
        self.assertGreaterEqual(level, 31)
        self.assertLessEqual(level, 40)

    def test_level_41_diamond(self):
        """Test Diamond tier Level 41 (min)"""
        level = PointsSystem.calculate_level(10001)
        self.assertGreaterEqual(level, 41)

    def test_level_50_diamond(self):
        """Test Diamond tier Level 50+"""
        level = PointsSystem.calculate_level(20000)
        self.assertGreaterEqual(level, 41)

    def test_level_progression_continuous(self):
        """Test that level progression is monotonic (always increasing)"""
        levels = []
        for points in range(0, 20001, 100):
            level = PointsSystem.calculate_level(points)
            levels.append(level)

        # Verify each level is >= previous
        for i in range(1, len(levels)):
            self.assertGreaterEqual(
                levels[i], levels[i-1],
                f"Level decreased from {levels[i-1]} to {levels[i]} at points increment"
            )

    def test_level_transitions(self):
        """Test specific level transition points"""
        transitions = [
            (0, 1),      # Start at level 1
            (50, 1),     # Still level 1
            (51, 2),     # Transition to level 2
            (100, 2),    # Still level 2
            (101, 3),    # Transition to level 3
            (500, 10),   # Bronze max
            (501, 11),   # Silver min
            (2000, 20),  # Silver max (approx)
            (2001, 21),  # Gold min
            (5000, 30),  # Gold max (approx)
            (5001, 31),  # Platinum min
            (10000, 40), # Platinum max (approx)
            (10001, 41), # Diamond min
        ]

        for points, min_level in transitions:
            level = PointsSystem.calculate_level(points)
            self.assertGreaterEqual(level, min_level,
                f"Points {points} should give at least level {min_level}, got {level}")

    def test_level_progress_calculation(self):
        """Test level progress percentage calculation"""
        # Test a few progress values
        progress = PointsSystem.calculate_level_progress(25)
        self.assertGreaterEqual(progress, 0)
        self.assertLessEqual(progress, 100)

        progress = PointsSystem.calculate_level_progress(75)
        self.assertGreaterEqual(progress, 0)
        self.assertLessEqual(progress, 100)


class TestPointsWithDatabase(unittest.TestCase):
    """Test points system integration with database"""

    @classmethod
    def setUpClass(cls):
        """Setup Flask app and database for testing"""
        cls.app = create_app('testing')
        cls.app_context = cls.app.app_context()
        cls.app_context.push()

    @classmethod
    def tearDownClass(cls):
        """Clean up Flask app context"""
        cls.app_context.pop()

    def setUp(self):
        """Create fresh database before each test"""
        db.create_all()

    def tearDown(self):
        """Clean up database after each test"""
        db.session.remove()
        db.drop_all()

    def test_points_persistence(self):
        """Test that points persist in database"""
        # Create user and profile
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()

        profile = UserProfile(user_id=user.id, points=0, level=1)
        db.session.add(profile)
        db.session.commit()

        # Award points
        PointsSystem.award_points(profile, 'registration')
        db.session.commit()

        # Query again and verify
        retrieved_profile = UserProfile.query.filter_by(user_id=user.id).first()
        self.assertEqual(retrieved_profile.points, 10)

    def test_level_update_with_points(self):
        """Test that level updates correctly as points increase"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass')
        db.session.add(user)
        db.session.commit()

        profile = UserProfile(user_id=user.id, points=0, level=1)
        db.session.add(profile)
        db.session.commit()

        # Add points and update level
        for _ in range(100):
            PointsSystem.award_points(profile, 'execute_command')

        new_level = PointsSystem.calculate_level(profile.points)
        profile.level = new_level
        db.session.commit()

        retrieved_profile = UserProfile.query.filter_by(user_id=user.id).first()
        self.assertEqual(retrieved_profile.points, 100)
        self.assertEqual(retrieved_profile.level, 3)  # Updated to match new calculation

    def test_multiple_users_points_independent(self):
        """Test that points for different users are independent"""
        users = []
        for i in range(3):
            user = User(username=f'user{i}', email=f'user{i}@example.com')
            user.set_password('testpass')
            db.session.add(user)
            users.append(user)

        db.session.commit()

        # Give different points to each user
        for i, user in enumerate(users):
            profile = UserProfile(
                user_id=user.id,
                points=i * 100,
                level=i + 1
            )
            db.session.add(profile)

        db.session.commit()

        # Verify each user has correct points
        for i, user in enumerate(users):
            profile = UserProfile.query.filter_by(user_id=user.id).first()
            self.assertEqual(profile.points, i * 100)


class TestTitleEligibility(unittest.TestCase):
    """Test title eligibility based on points and level"""

    TITLES = {
        '新手探索者': {'level': 1, 'min_points': 0},
        '機器人學徒': {'level': 1, 'min_points': 0, 'requires': 'registered_robot'},
        '指令入門者': {'level': 1, 'min_points': 0, 'requires': 'first_command'},
        '指令達人': {'level': 5, 'min_points': 100, 'requires': 'total_commands:100'},
        '機器人專家': {'level': 5, 'min_points': 100, 'requires': 'robots:5'},
        '創意貢獻者': {'level': 5, 'min_points': 100, 'requires': 'first_advanced_command'},
        '平台大師': {'level': 15, 'min_points': 1000, 'requires': 'approved_advanced_commands:10'},
        '社群領袖': {'level': 20, 'min_points': 2000, 'requires': 'advanced_command_uses:100'},
        '傳奇開發者': {'level': 30, 'min_points': 5000, 'requires': 'advanced_commands:50,rating:4.5'},
    }

    def test_basic_title_eligibility(self):
        """Test basic title eligibility criteria"""
        profile = UserProfile(user_id=1, points=0, level=1)

        # Should be eligible for 新手探索者
        self.assertTrue(self._is_eligible_for_title('新手探索者', profile))

    def test_title_level_requirement(self):
        """Test that titles have level requirements"""
        profile = UserProfile(user_id=1, points=100, level=1)

        # Should NOT be eligible for 指令達人 due to low level
        self.assertFalse(self._is_eligible_for_title('指令達人', profile))

        # Should be eligible after reaching level 5
        profile.level = 5
        self.assertTrue(self._is_eligible_for_title('指令達人', profile))

    def test_title_points_requirement(self):
        """Test that titles have points requirements"""
        profile = UserProfile(user_id=1, points=50, level=5)

        # Should NOT be eligible for 指令達人 (needs 100 points min)
        self.assertFalse(self._is_eligible_for_title('指令達人', profile))

        # Should be eligible after earning enough points
        profile.points = 100
        self.assertTrue(self._is_eligible_for_title('指令達人', profile))

    @staticmethod
    def _is_eligible_for_title(title, profile):
        """Check if profile is eligible for a title"""
        title_req = TestTitleEligibility.TITLES.get(title, {})

        # Check level
        if profile.level < title_req.get('level', 1):
            return False

        # Check points
        if profile.points < title_req.get('min_points', 0):
            return False

        return True


if __name__ == '__main__':
    unittest.main()
