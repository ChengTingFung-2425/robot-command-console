# Phase 1 User Profile System - Quick Start Guide

## What Was Built

A complete user engagement and gamification system for the Robot Command Console with:
- **User Profiles** with points, levels, and titles
- **Achievement System** for earning badges
- **Leaderboards** showing top users by various metrics
- **Profile Pages** displaying user stats and achievements
- **Automatic Point Awards** on user actions (registration, robot setup, commands, etc.)

## Getting Started

### 1. Database Setup

First, create and apply database migrations:

```bash
cd /workspaces/robot-command-console/WebUI

# Generate migration for new models
flask db migrate -m "Add user profile and achievement system"

# Apply the migration
flask db upgrade
```

### 2. Initialize Achievements

Start the Flask shell and seed the database with achievements:

```bash
cd /workspaces/robot-command-console/WebUI

flask shell
```

Then in the Python shell:

```python
from WebUI.app.engagement import initialize_achievements
initialize_achievements()
exit()
```

### 3. Start the Application

```bash
cd /workspaces/robot-command-console/WebUI
python microblog.py
```

Or with Flask development server:

```bash
flask --debug run --host=0.0.0.0 --port=5000
```

Then open http://localhost:5000 in your browser.

## Key Features

### User Registration
- When a user registers, they automatically get:
  - A `UserProfile` record
  - 10 registration points
  - Title: "新手探索者" (Novice Explorer)
  - Level 1

### User Profile Page
- **URL**: `/user/<username>`
- **Shows**:
  - Current level and points with progress bar
  - Current title/badge
  - Stats: commands executed, robots managed, advanced commands submitted
  - All earned achievements/badges

### Edit Profile
- **URL**: `/user/edit_profile` (requires login)
- **Allows changing**:
  - UI duration unit preference
  - Verification display settings

### Leaderboard
- **URL**: `/leaderboard`
- **Features**:
  - Sort by: Points, Level, Reputation, or Commands
  - Shows top 50 users
  - Medal emoji for top 3 (🥇 🥈 🥉)
  - Tier badges (Bronze/Silver/Gold/Platinum/Diamond)
  - Clickable rows linking to user profiles

### Navbar Integration
- When logged in, the navbar shows:
  - User's username with dropdown menu
  - Current level badge
  - Current points
  - Quick link to profile and settings
  - Link to leaderboard

## Points System

### How Points Are Awarded

| Action | Points | Event |
|--------|--------|-------|
| User Registration | +10 | One-time on signup |
| Robot Registration | +5 | Per robot added |
| Command Execution | +1 | Per command executed |
| Advanced Command Submission | +20 | Per submission to review |
| Advanced Command Approval | +50 | When admin/auditor approves |
| Advanced Command Usage | +5 | Each time another user uses it |
| Advanced Command Rating | +2 | Per 4+ star rating received |

### Level Ranges

| Tier | Levels | Points | Description |
|------|--------|--------|-------------|
| Bronze | L1-10 | 0-500 | Entry level |
| Silver | L11-20 | 501-2000 | Intermediate |
| Gold | L21-30 | 2001-5000 | Advanced |
| Platinum | L31-40 | 5001-10000 | Expert |
| Diamond | L41+ | 10000+ | Legendary |

## Code Examples

### Award Points for Custom Action

```python
from WebUI.app import create_app
from WebUI.app.engagement import award_points

app = create_app()
with app.app_context():
    # Award 100 points for a special achievement
    profile = award_points(user_id=123, reason="custom_bonus", amount=100)
    print(f"User now has {profile.points} points at level {profile.level}")
```

### Check User Progress

```python
from WebUI.app import create_app
from WebUI.app.models import User

app = create_app()
with app.app_context():
    user = User.query.filter_by(username="john_doe").first()
    profile = user.profile
    
    print(f"Points: {profile.points}")
    print(f"Level: {profile.level}")
    print(f"Title: {profile.title}")
    print(f"Tier: {profile.get_rank_tier()}")
    
    progress = profile.get_progress_to_next_level()
    print(f"Progress: {progress['percent']}%")
    print(f"Need {progress['needed']} more points for next level")
```

### Get Leaderboard

```python
from WebUI.app import create_app
from WebUI.app.engagement import get_leaderboard

app = create_app()
with app.app_context():
    # Top 20 users by points
    top_users = get_leaderboard(limit=20, sort_by='points')
    
    for rank, (user, profile) in enumerate(top_users, 1):
        print(f"{rank}. {user.username}: {profile.points} points (L{profile.level})")
```

### Grant Achievement

```python
from WebUI.app import create_app
from WebUI.app.engagement import grant_achievement_by_name

app = create_app()
with app.app_context():
    result = grant_achievement_by_name(user_id=123, achievement_name="Platform Guru")
    if result:
        print("Achievement granted!")
    else:
        print("User already had this achievement")
```

## Testing the System

### Test User Registration with Profile
1. Go to http://localhost:5000/register
2. Create a new account (e.g., testuser)
3. Login with the new account
4. Check the navbar - should see level 1 and 10 points

### Test Profile View
1. Click on username in navbar → "我的檔案" (My Profile)
2. Should see:
   - Username, email, role
   - Points: 10
   - Level: 1
   - Title: "新手探索者"
   - Progress bar
   - Stats cards
   - Empty achievements message

### Test Robot Registration
1. Go to Dashboard
2. Register a robot
3. Return to profile
4. Points should increase to 15
5. Robots stat should be 1

### Test Leaderboard
1. Register multiple users with different activity levels
2. Go to /leaderboard
3. Users should be ranked by points
4. Click on a user row to see their full profile

## File Structure

```
WebUI/
├── app/
│   ├── models.py              # UserProfile, Achievement, UserAchievement
│   ├── routes.py              # Profile, leaderboard routes
│   ├── engagement.py           # Points & achievement utilities (NEW)
│   └── templates/
│       ├── base.html.j2        # Updated navbar with profile dropdown
│       ├── user.html.j2        # User profile page
│       ├── edit_profile.html.j2 # Profile settings
│       └── leaderboard.html.j2  # Leaderboard (NEW)
└── docs/
    └── phase1-implementation-summary.md  # Full documentation
```

## Common Tasks

### Manually Award Points to a User

```python
from WebUI.app import create_app
from WebUI.app.engagement import award_custom

app = create_app()
with app.app_context():
    profile = award_custom(user_id=123, amount=500, reason="Admin bonus")
    print(f"User now at {profile.points} points, level {profile.level}")
```

### Update User Statistics

```python
from WebUI.app import create_app
from WebUI.app.engagement import update_command_stats, update_robot_stats

app = create_app()
with app.app_context():
    # Force refresh of command count from database
    update_command_stats(user_id=123)
    
    # Update robot count
    update_robot_stats(user_id=123)
```

### See All Achievements a User Has

```python
from WebUI.app import create_app
from WebUI.app.engagement import get_user_achievements

app = create_app()
with app.app_context():
    achievements = get_user_achievements(user_id=123)
    for achievement in achievements:
        print(f"{achievement.emoji} {achievement.name}: {achievement.description}")
```

## Troubleshooting

### User profile not created after registration
**Solution**: Manually create profiles for existing users:
```python
from WebUI.app import create_app
from WebUI.app.models import User, UserProfile
from WebUI.app.engagement import get_or_create_user_profile

app = create_app()
with app.app_context():
    users = User.query.all()
    for user in users:
        get_or_create_user_profile(user)
```

### Points not updating
**Solution**: Check that `db.session.commit()` is being called after `award_points()`. The function should auto-commit, but verify in your code.

### Achievements not showing on profile
**Solution**: Make sure `initialize_achievements()` has been run in the Flask shell.

## Next Steps (Future Phases)

- [ ] Auto-grant achievements based on user actions
- [ ] Achievement notification system
- [ ] User-to-user comparisons
- [ ] Badges on comments/contributions
- [ ] Admin dashboard for engagement management
- [ ] Reputation system (like/dislike on advanced commands)
- [ ] Community challenges

---

For detailed architecture and design information, see:
- `docs/user-engagement-system.md` - Design specification
- `docs/phase1-implementation-summary.md` - Complete implementation guide
