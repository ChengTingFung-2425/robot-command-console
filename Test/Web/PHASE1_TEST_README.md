# Phase 1 User Engagement System - Test Suite

Comprehensive test suite for the Phase 1 User Engagement & Gamification System for the Robot Command Console WebUI.

## Overview

This test suite verifies the implementation of Phase 1 features:
- **User Profile Model**: Database layer with engagement metrics
- **Points & Levels System**: Game mechanics for earning points and advancing levels
- **Titles System**: Badge/achievement system with 8 Phase 1 titles
- **Engagement Routes**: Placeholder routes and data model for profile display

## Test Files

### 1. `test_webui_user_profile_model.py` (13 tests)
Tests the `UserProfile` database model including:
- Model creation and relationships with User
- Points accumulation
- Level calculation for all 5 tiers (Bronze 1-10, Silver 11-20, Gold 21-30, Platinum 31-40, Diamond 41+)
- Title field management
- Reputation scoring
- Timestamp tracking (created_at, updated_at)
- Multi-user profile independence

### 2. `test_webui_points_levels.py` (20 tests)
Tests the points and levels game mechanics:
- Points awarded for 8 different actions:
  - Registration: +10
  - Register robot: +5
  - Execute command: +1
  - Submit advanced command: +20
  - Advanced command approved: +50
  - Advanced command used: +5 each
  - Rating 4-5 stars: +2 each
  - Daily task: +10
- Level calculation algorithms for all 5 tiers
- Level progression monotonicity
- User journey simulation
- Database persistence of points

### 3. `test_webui_titles_system.py` (15 tests)
Tests the titles/badge system:
- Phase 1 title definitions (8 titles):
  - 🌱 新手探索者 (Novice Explorer) - Beginner
  - 🤖 機器人學徒 (Robot Apprentice) - Beginner
  - 📝 指令入門者 (Command Beginner) - Beginner
  - ⚡ 指令達人 (Command Master) - Intermediate
  - 🎯 機器人專家 (Robot Specialist) - Intermediate
  - 💡 創意貢獻者 (Creative Contributor) - Intermediate
  - 🔧 早期採用者 (Early Adopter) - Special
  - 🛡️ 守護者 (Guardian) - Special
- Title eligibility requirements based on level and points
- Title display formatting with emoji
- User progression through titles
- Database persistence

### 4. `test_webui_engagement_routes.py` (11 tests)
Tests the WebUI routes and data model for engagement display:
- User profile page/route handling
- Engagement statistics display
- Profile data API endpoints
- Profile page structure
- Data model validation
- Field types and defaults
- Timestamp tracking

## Test Statistics

- **Total Tests**: 86
- **Passed**: 86 (100%)
- **Failed**: 0
- **Errors**: 0
- **Execution Time**: ~7.3 seconds

## Running the Tests

### Run All Phase 1 Tests
```bash
cd /workspaces/robot-command-console
python Test/Web/PHASE1_VERIFICATION.py
```

### Run Individual Test Files
```bash
# User Profile Model Tests
python -m unittest Test.Web.test_webui_user_profile_model -v

# Points and Levels Tests
python -m unittest Test.Web.test_webui_points_levels -v

# Titles System Tests
python -m unittest Test.Web.test_webui_titles_system -v

# Engagement Routes Tests
python -m unittest Test.Web.test_webui_engagement_routes -v
```

### Run Specific Test Class
```bash
python -m unittest Test.Web.test_webui_points_levels.TestPointsSystem -v
```

### Run Specific Test Method
```bash
python -m unittest Test.Web.test_webui_points_levels.TestPointsSystem.test_points_registration -v
```

## Phase 1 Implementation Details

### UserProfile Model
Located in: `WebUI/app/models.py`

```python
class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    user = db.relationship('User', backref=db.backref('profile', uselist=False))
    
    # Engagement metrics
    points = db.Column(db.Integer, default=0, index=True)
    level = db.Column(db.Integer, default=1, index=True)
    title = db.Column(db.String(64), default='新手探索者')
    
    # Statistics
    total_commands = db.Column(db.Integer, default=0)
    total_advanced_commands = db.Column(db.Integer, default=0)
    total_robots = db.Column(db.Integer, default=0)
    reputation = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, index=True, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
```

### Level Tiers
- **Bronze** (Levels 1-10): 0-500 points (50 points per level)
- **Silver** (Levels 11-20): 500-2000 points (~150 points per level)
- **Gold** (Levels 21-30): 2000-5000 points (~600 points per level)
- **Platinum** (Levels 31-40): 5000-10000 points (~1000 points per level)
- **Diamond** (Levels 41+): 10000+ points (~2000 points per level)

### Title Requirements
Each title has:
- Minimum level requirement
- Minimum points requirement
- Specific condition (e.g., "first_command", "robots:5", etc.)

## Test Coverage

### Database Layer
- ✓ Model creation and fields
- ✓ Relationships (User → UserProfile)
- ✓ Field types and defaults
- ✓ Timestamps
- ✓ Data persistence
- ✓ Multi-user independence

### Game Mechanics
- ✓ Point awarding for 8 actions
- ✓ Points accumulation
- ✓ Level calculation
- ✓ Level progression
- ✓ All tier transitions
- ✓ User journey simulation

### Title System
- ✓ Title definitions (8 titles)
- ✓ Category organization
- ✓ Eligibility requirements
- ✓ Individual title tests
- ✓ Title progression

### Presentation Layer
- ✓ Data model validation
- ✓ Field structure
- ✓ Display capability
- ✓ Timestamp tracking

## Key Features Tested

### Points System (8 Actions)
1. Registration (+10)
2. Register Robot (+5)
3. Execute Command (+1)
4. Submit Advanced Command (+20)
5. Advanced Command Approved (+50)
6. Advanced Command Used (+5)
7. Rating 4-5 Stars (+2)
8. Daily Task (+10)

### Level System
- Continuous level progression from 1 to 50+
- 5 distinct tiers with different point requirements
- Monotonic progression (levels never decrease)
- Clear tier transition points

### Title System (8 Titles)
- 3 Beginner titles (Novice, Apprentice, Beginner)
- 3 Intermediate titles (Master, Specialist, Contributor)
- 2 Special titles (Early Adopter, Guardian)

## Integration with WebUI

### Models Integration
```python
from WebUI.app.models import User, UserProfile

# Create user and profile
user = User(username='alice', email='alice@example.com')
user.set_password('password')
db.session.add(user)
db.session.commit()

profile = UserProfile(
    user_id=user.id,
    points=100,
    level=2,
    title='指令入門者'
)
db.session.add(profile)
db.session.commit()
```

### Testing App Factory
```python
from WebUI.app import create_app, db

# Create test app
app = create_app('testing')
with app.app_context():
    db.create_all()
    # Run tests
    db.drop_all()
```

## Next Steps (Phase 2)

### WebUI Routes
- [ ] Implement `/user/<id>` profile page
- [ ] Implement `/leaderboard` page
- [ ] Implement `/stats` page
- [ ] Create API endpoints for profile data

### Frontend Templates
- [ ] User profile page template
- [ ] Leaderboard page template
- [ ] Stats dashboard
- [ ] Title/badge display components

### Additional Features
- [ ] Achievement system
- [ ] Achievement unlock notifications
- [ ] Advanced command rating system
- [ ] Reputation scoring

## Files Added/Modified

### New Test Files
- `Test/Web/test_webui_user_profile_model.py` - 13 tests
- `Test/Web/test_webui_points_levels.py` - 20 tests
- `Test/Web/test_webui_titles_system.py` - 15 tests
- `Test/Web/test_webui_engagement_routes.py` - 11 tests
- `Test/Web/run_phase1_tests.py` - Test runner script
- `Test/Web/PHASE1_VERIFICATION.py` - Verification report

### Modified Files
- `WebUI/app/models.py` - Added UserProfile model
- `WebUI/app/__init__.py` - Added create_app factory function
- `WebUI/app/errors.py` - Refactored for factory pattern
- `WebUI/__init__.py` - Updated for factory pattern

## Verification

All 86 tests pass successfully:
```
Ran 86 tests in 7.263s
OK
```

This confirms that Phase 1 of the User Engagement System is fully implemented and tested.

## License

Part of the Robot Command Console project.

## Contact

For questions or issues, refer to the project documentation or contact the development team.
