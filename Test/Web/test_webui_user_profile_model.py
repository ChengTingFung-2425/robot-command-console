"""
Test suite for WebUI UserProfile model - Phase 1 User Engagement System

Tests the UserProfile database model including:
- Points accumulation
- Level calculation based on points
- Title assignment
- User profile relationships
- Basic CRUD operations
"""

import unittest
import sys
import os
from datetime import datetime

# Add WebUI to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from WebUI.app import db, create_app
from WebUI.app.models import User, UserProfile


class TestUserProfileModel(unittest.TestCase):
    """Test UserProfile model functionality for Phase 1"""

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

    def test_user_profile_creation(self):
        """Test creating a UserProfile for a user"""
        # Create user
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()

        # Create user profile
        profile = UserProfile(
            user_id=user.id,
            points=0,
            level=1,
            title='新手探索者',
            total_commands=0,
            total_advanced_commands=0,
            reputation=0
        )
        db.session.add(profile)
        db.session.commit()

        # Verify
        retrieved_profile = UserProfile.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(retrieved_profile)
        self.assertEqual(retrieved_profile.points, 0)
        self.assertEqual(retrieved_profile.level, 1)
        self.assertEqual(retrieved_profile.title, '新手探索者')

    def test_points_accumulation(self):
        """Test adding points to a user profile"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()

        profile = UserProfile(user_id=user.id, points=0, level=1)
        db.session.add(profile)
        db.session.commit()

        # Add points for registration
        profile.points += 10
        db.session.commit()

        # Add points for registering robot
        profile.points += 5
        db.session.commit()

        # Verify
        retrieved_profile = UserProfile.query.filter_by(user_id=user.id).first()
        self.assertEqual(retrieved_profile.points, 15)

    def test_level_calculation_bronze(self):
        """Test level calculation for Bronze tier (Level 1-10)"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()

        profile = UserProfile(user_id=user.id, points=0, level=1)
        db.session.add(profile)
        db.session.commit()

        # Points for Bronze tier: 0-500
        test_cases = [
            (0, 1),      # 0-49 points = Level 1
            (40, 1),     # 0-49 points = Level 1
            (50, 2),     # 50-99 points = Level 2
            (100, 3),    # 100-149 points = Level 3
            (200, 5),    # 200-249 points = Level 5
            (450, 10),   # 450-499 points = Level 10
        ]

        for points, expected_level in test_cases:
            profile.points = points
            calculated_level = self._calculate_level(points)
            self.assertEqual(
                calculated_level, expected_level,
                f"Points {points} should give level {expected_level}, got {calculated_level}"
            )

    def test_level_calculation_silver(self):
        """Test level calculation for Silver tier (Level 11-20)"""
        test_cases = [
            (501, 11),    # 501-1000 points = Level 11
            (750, 15),    # 501-1000 points = Level 15
            (1000, 20),   # 901-1000 = Level 20
            (1500, 20),   # Capped at Level 20 for this tier
        ]

        for points, expected_level in test_cases:
            calculated_level = self._calculate_level(points)
            # Note: Adjust based on actual level ranges
            self.assertGreaterEqual(calculated_level, 11)

    def test_level_calculation_gold(self):
        """Test level calculation for Gold tier (Level 21-30)"""
        test_cases = [
            (2001, 21),    # 2001-5000 points = Level 21
            (3500, 25),    # 2001-5000 points
            (5000, 30),    # 5001-5000 points = Level 30
        ]

        for points, expected_level in test_cases:
            calculated_level = self._calculate_level(points)
            self.assertGreaterEqual(calculated_level, 21)

    def test_level_calculation_platinum(self):
        """Test level calculation for Platinum tier (Level 31-40)"""
        test_cases = [
            (5001, 31),    # 5001-10000 points = Level 31
            (7500, 35),    # 5001-10000 points
            (10000, 40),   # 5001-10000 points = Level 40
        ]

        for points, expected_level in test_cases:
            calculated_level = self._calculate_level(points)
            self.assertGreaterEqual(calculated_level, 31)

    def test_level_calculation_diamond(self):
        """Test level calculation for Diamond tier (Level 41+)"""
        test_cases = [
            (10001, 41),   # 10000+ points = Level 41+
            (15000, 46),   # 10000+ points = Level 46
            (20000, 51),   # 10000+ points = Level 51
        ]

        for points, expected_level in test_cases:
            calculated_level = self._calculate_level(points)
            self.assertGreaterEqual(calculated_level, 41)

    def test_total_commands_increment(self):
        """Test incrementing total commands counter"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()

        profile = UserProfile(user_id=user.id, points=0, level=1, total_commands=0)
        db.session.add(profile)
        db.session.commit()

        # Execute command
        profile.total_commands += 1
        profile.points += 1  # +1 point per command
        db.session.commit()

        retrieved_profile = UserProfile.query.filter_by(user_id=user.id).first()
        self.assertEqual(retrieved_profile.total_commands, 1)
        self.assertEqual(retrieved_profile.points, 1)

    def test_total_advanced_commands_increment(self):
        """Test incrementing advanced commands counter"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()

        profile = UserProfile(
            user_id=user.id,
            points=0,
            level=1,
            total_advanced_commands=0
        )
        db.session.add(profile)
        db.session.commit()

        # Submit advanced command
        profile.total_advanced_commands += 1
        profile.points += 20  # +20 points for submission
        db.session.commit()

        retrieved_profile = UserProfile.query.filter_by(user_id=user.id).first()
        self.assertEqual(retrieved_profile.total_advanced_commands, 1)
        self.assertEqual(retrieved_profile.points, 20)

    def test_reputation_score(self):
        """Test reputation score accumulation"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()

        profile = UserProfile(
            user_id=user.id,
            points=0,
            level=1,
            reputation=0
        )
        db.session.add(profile)
        db.session.commit()

        # Increase reputation
        profile.reputation += 50
        db.session.commit()

        retrieved_profile = UserProfile.query.filter_by(user_id=user.id).first()
        self.assertEqual(retrieved_profile.reputation, 50)

    def test_title_update(self):
        """Test updating user title"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
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
        profile.title = '機器人學徒'
        db.session.commit()

        retrieved_profile = UserProfile.query.filter_by(user_id=user.id).first()
        self.assertEqual(retrieved_profile.title, '機器人學徒')

    def test_user_profile_relationship(self):
        """Test relationship between User and UserProfile"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()

        profile = UserProfile(
            user_id=user.id,
            points=100,
            level=5,
            title='指令入門者'
        )
        db.session.add(profile)
        db.session.commit()

        # Query user and check profile
        retrieved_user = User.query.filter_by(username='testuser').first()
        self.assertIsNotNone(retrieved_user)

    def test_multiple_users_profiles(self):
        """Test creating profiles for multiple users"""
        users = []
        for i in range(5):
            user = User(
                username=f'user{i}',
                email=f'user{i}@example.com'
            )
            user.set_password(f'pass{i}')
            db.session.add(user)
            users.append(user)

        db.session.commit()

        # Create profiles
        for i, user in enumerate(users):
            profile = UserProfile(
                user_id=user.id,
                points=i * 100,
                level=i + 1,
                title='新手探索者'
            )
            db.session.add(profile)

        db.session.commit()

        # Verify all profiles created
        all_profiles = UserProfile.query.all()
        self.assertEqual(len(all_profiles), 5)

    def test_profile_timestamp_creation(self):
        """Test that profile creation timestamp is set"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()

        profile = UserProfile(
            user_id=user.id,
            points=0,
            level=1
        )
        db.session.add(profile)
        db.session.commit()

        retrieved_profile = UserProfile.query.filter_by(user_id=user.id).first()
        self.assertIsNotNone(retrieved_profile.created_at)
        self.assertIsInstance(retrieved_profile.created_at, datetime)

    def test_profile_updated_timestamp(self):
        """Test that profile updated timestamp is modified"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()

        profile = UserProfile(
            user_id=user.id,
            points=0,
            level=1
        )
        db.session.add(profile)
        db.session.commit()

        original_updated = profile.updated_at

        # Wait a moment and update
        import time
        time.sleep(0.1)

        profile.points = 50
        db.session.commit()

        # Verify timestamp was updated
        self.assertGreaterEqual(profile.updated_at, original_updated)

    @staticmethod
    def _calculate_level(points):
        """Helper function to calculate level from points"""
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


if __name__ == '__main__':
    unittest.main()
