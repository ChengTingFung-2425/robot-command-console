# imports

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from time import time
import jwt
from flask import current_app
from WebUI.app import db, login

# Constants
DEFAULT_FIRMWARE_VERSION = '1.0.0'


class User(UserMixin, db.Model):
    """User account model."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False, index=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(32), default='operator')  # viewer/operator/admin/auditor
    # UI preferences
    ui_duration_unit = db.Column(db.String(8), default='s')  # 's' or 'ms'
    ui_verify_collapsed = db.Column(db.Boolean, default=False)
    # LLM preferences
    llm_provider = db.Column(db.String(64), nullable=True)  # preferred LLM provider (e.g., 'ollama', 'lmstudio')
    llm_model = db.Column(db.String(128), nullable=True)  # preferred LLM model (e.g., 'llama2:latest')
    robots = db.relationship('Robot', backref='owner', lazy='dynamic')

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def is_admin(self) -> bool:
        return self.role in ['admin', 'auditor']

    def get_reset_password_token(self, expires_in: int = 600) -> str:
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256'
        )

    @staticmethod
    def verify_reset_password_token(token: str):
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            return User.query.get(data.get('reset_password'))
        except Exception:
            return None

    def __repr__(self) -> str:
        return f'<User {self.username}>'


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class UserProfile(db.Model):
    """User engagement and gamification profile.

    Stores user engagement metrics including:
    - Points: accumulated through various actions
    - Level: calculated based on points
    - Title: current badge/title for the user
    - Statistics: total commands, advanced commands, robots, reputation
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True, index=True)
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

    @staticmethod
    def get_level_from_points(points: int) -> int:
        """Calculate level based on points.

        Level ranges:
        - Bronze (L1-10): 0-500 points
        - Silver (L11-20): 501-2000 points
        - Gold (L21-30): 2001-5000 points
        - Platinum (L31-40): 5001-10000 points
        - Diamond (L41+): 10000+ points
        """
        if points < 0:
            return 1
        elif points < 50:
            return 1
        elif points < 100:
            return 2
        elif points < 150:
            return 3
        elif points < 200:
            return 4
        elif points < 300:
            return 5
        elif points < 400:
            return 6
        elif points < 500:
            return 7
        elif points < 700:
            return 8
        elif points < 1000:
            return 9
        elif points < 1300:
            return 10  # Bronze complete
        elif points < 1600:
            return 11
        elif points < 2000:
            return 12
        elif points < 2500:
            return 13
        elif points < 3000:
            return 14
        elif points < 3500:
            return 15
        elif points < 4000:
            return 16
        elif points < 4500:
            return 17
        elif points < 5000:
            return 18
        elif points < 5500:
            return 19
        elif points < 6000:
            return 20  # Silver complete
        elif points < 7000:
            return 21
        elif points < 8000:
            return 22
        elif points < 9000:
            return 23
        elif points < 10000:
            return 24
        else:
            # Diamond tier: 1 level per 1000 points after 10000
            return min(40 + (points - 10000) // 1000, 99)

    def add_points(self, amount: int) -> None:
        """Add points to user profile and update level if needed."""
        if amount <= 0:
            return
        self.points += amount
        new_level = self.get_level_from_points(self.points)
        if new_level != self.level:
            self.level = new_level
        self.updated_at = db.func.now()

    def get_rank_tier(self) -> str:
        """Get rank tier name based on level."""
        if self.level <= 10:
            return 'Bronze (青銅)'
        elif self.level <= 20:
            return 'Silver (白銀)'
        elif self.level <= 30:
            return 'Gold (黃金)'
        elif self.level <= 40:
            return 'Platinum (鉑金)'
        else:
            return 'Diamond (鑽石)'

    def get_points_for_next_level(self) -> int:
        """Get points needed to reach next level."""
        points_for_next = [
            50, 100, 150, 200, 300, 400, 500, 700, 1000, 1300,  # L1-10
            1600, 2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000,  # L11-20
            7000, 8000, 9000, 10000, 11000, 12000, 13000, 14000, 15000, 16000,  # L21-30
            17000, 18000, 19000, 20000, 21000, 22000, 23000, 24000, 25000, 26000  # L31-40
        ]
        if self.level - 1 < len(points_for_next):
            return points_for_next[self.level - 1]
        return 26000 + (self.level - 40) * 1000

    def get_progress_to_next_level(self) -> dict:
        """Get progress info to next level."""
        current_points = self.points
        next_level_points = self.get_points_for_next_level()

        # Get previous level points
        if self.level == 1:
            prev_points = 0
        else:
            points_for_levels = [
                0, 50, 100, 150, 200, 300, 400, 500, 700, 1000, 1300,  # L0-10
                1600, 2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000,  # L11-20
                7000, 8000, 9000, 10000, 11000, 12000, 13000, 14000, 15000, 16000,  # L21-30
                17000, 18000, 19000, 20000, 21000, 22000, 23000, 24000, 25000, 26000  # L31-40
            ]
            prev_points = (
                points_for_levels[self.level - 1]
                if self.level - 1 < len(points_for_levels)
                else 26000 + (self.level - 41) * 1000
            )

        progress = current_points - prev_points
        needed = next_level_points - prev_points
        percent = int((progress / needed * 100)) if needed > 0 else 100

        return {
            'current': current_points,
            'next_level_required': next_level_points,
            'progress': progress,
            'needed': needed,
            'percent': min(percent, 100)
        }

    def __repr__(self) -> str:
        return f'<UserProfile user_id={self.user_id} level={self.level} points={self.points}>'


class Robot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    type = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(64), default='idle')
    battery = db.Column(db.Integer, default=100)  # 電池電量百分比 (0-100)
    location = db.Column(db.String(128))  # 機器人位置
    firmware_version = db.Column(
        db.String(32),
        default=DEFAULT_FIRMWARE_VERSION
    )  # 目前固件版本
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self) -> str:
        return f'<Robot {self.name}>'

    def set_battery(self, value: int) -> None:
        """設定電池電量，確保值在 0-100 範圍內"""
        if value < 0:
            self.battery = 0
        elif value > 100:
            self.battery = 100
        else:
            self.battery = value


class Command(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    robot_id = db.Column(db.Integer, db.ForeignKey('robot.id'))
    command = db.Column(db.String(128), nullable=False)
    status = db.Column(db.String(64), default='pending')
    timestamp = db.Column(db.DateTime, index=True, default=db.func.now())
    nested_command = db.Column(db.Boolean, default=False)

    def __repr__(self) -> str:
        return f'<Command {self.command} to robot {self.robot_id}>'


# --- Advanced command split into three parts ---
class AdvCommand(db.Model):
    """Stores the actual JSON/text content of a command (the 'command itself').

    This isolates the potentially large JSON payload from version metadata.
    """
    __tablename__ = 'adv_command'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, index=True, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    def __repr__(self) -> str:
        return f'<AdvCommand {self.id}>'


class AdvancedCommandVersion(db.Model):
    """Represents a single version of an AdvancedCommand."""
    __tablename__ = 'advanced_command_version'
    id = db.Column(db.Integer, primary_key=True)
    advanced_command_id = db.Column(db.Integer, db.ForeignKey('advanced_command.id'))
    adv_command_id = db.Column(db.Integer, db.ForeignKey('adv_command.id'))
    version = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(32), default='pending')  # pending/approved/rejected
    created_at = db.Column(db.DateTime, index=True, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    adv_command = db.relationship('AdvCommand', backref=db.backref('versions', lazy='dynamic'), uselist=False)

    def __repr__(self) -> str:
        return f'<AdvancedCommandVersion cmd_id={self.advanced_command_id} v={self.version}>'


class AdvancedCommand(db.Model):
    """Overall advanced command metadata. Holds human-facing fields and
    a relationship to version records (AdvancedCommandVersion). For backward
    compatibility we keep legacy columns (base_commands, version, status) and
    provide helpers to create/sync versions.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    description = db.Column(db.Text)
    category = db.Column(db.String(64), index=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User', backref='advanced_commands')

    # legacy compatibility fields (kept in-table for existing code/tests)
    base_commands = db.Column(db.Text, nullable=False, default='[]')
    version = db.Column(db.Integer, default=1)
    status = db.Column(db.String(32), default='pending')  # pending/approved/rejected

    created_at = db.Column(db.DateTime, index=True, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    # relationship to versions (the canonical source for historical versions)
    versions = db.relationship(
        'AdvancedCommandVersion', backref='advanced_command',
        lazy='dynamic', cascade='all, delete-orphan'
    )

    def add_version(self, content: str, status: str = 'pending', bump: bool = True) -> AdvancedCommandVersion:
        """Create a new AdvCommand + AdvancedCommandVersion and sync legacy fields.

        If bump is True the AdvancedCommand.version will be incremented, otherwise
        the provided version number will be used.
        """
        # create content row
        adv = AdvCommand(content=content)
        db.session.add(adv)
        db.session.flush()  # ensure adv.id

        # determine version number
        new_version = (self.version or 1) + 1 if bump else (self.version or 1)

        ver = AdvancedCommandVersion(advanced_command=self, adv_command=adv, version=new_version, status=status)
        db.session.add(ver)

        # sync legacy fields
        self.base_commands = content
        self.version = new_version
        self.status = status
        self.updated_at = db.func.now()

        return ver

    def latest_version(self):
        return self.versions.order_by(AdvancedCommandVersion.version.desc()).first()

    def current_base_commands(self) -> str:
        v = self.latest_version()
        if v and v.adv_command:
            return v.adv_command.content
        return self.base_commands

    def __repr__(self) -> str:
        return f'<AdvancedCommand {self.name}>'


class Achievement(db.Model):
    """Achievement/Badge template that users can earn.

    Stores the definition of achievements/badges available in the system.
    Each achievement has specific criteria for earning (handled in business logic).
    """
    __tablename__ = 'achievement'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True, index=True)
    emoji = db.Column(db.String(8), default='🏆')  # Unicode emoji for badge
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(32), nullable=False)  # exploration/contribution/social/challenge
    points_required = db.Column(db.Integer, default=0)  # points threshold for automatic awarding
    is_title = db.Column(db.Boolean, default=False)  # True if this is a title/badge level

    created_at = db.Column(db.DateTime, index=True, default=db.func.now())

    def __repr__(self) -> str:
        return f'<Achievement {self.name}>'


class UserAchievement(db.Model):
    """Tracks which achievements a user has earned and when.

    Junction table between User and Achievement.
    """
    __tablename__ = 'user_achievement'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False, index=True)
    earned_at = db.Column(db.DateTime, index=True, default=db.func.now())

    user = db.relationship(
        'User',
        backref=db.backref('earned_achievements', lazy='dynamic', cascade='all, delete-orphan')
    )
    achievement = db.relationship('Achievement', backref=db.backref('earned_by_users', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('user_id', 'achievement_id', name='uq_user_achievement'),)

    def __repr__(self) -> str:
        return f'<UserAchievement user_id={self.user_id} achievement_id={self.achievement_id}>'


class FirmwareVersion(db.Model):
    """Available firmware versions for robots.

    Stores information about available firmware versions that can be installed
    on different robot types.
    """
    __tablename__ = 'firmware_version'
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(32), nullable=False, index=True)  # e.g., '1.2.3'
    robot_type = db.Column(db.String(64), nullable=False, index=True)  # e.g., 'humanoid', 'agv'
    release_notes = db.Column(db.Text)  # Changelog/release notes
    download_url = db.Column(db.String(512))  # URL to download firmware file
    checksum = db.Column(db.String(128))  # SHA256 checksum for integrity verification
    file_size = db.Column(db.Integer)  # File size in bytes
    is_stable = db.Column(db.Boolean, default=True)  # True for stable releases
    min_required_version = db.Column(db.String(32))  # Minimum version required to upgrade

    created_at = db.Column(db.DateTime, index=True, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    # Unique constraint: only one version per robot type
    __table_args__ = (
        db.UniqueConstraint('version', 'robot_type', name='uq_firmware_version_type'),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'version': self.version,
            'robot_type': self.robot_type,
            'release_notes': self.release_notes,
            'download_url': self.download_url,
            'file_size': self.file_size,
            'is_stable': self.is_stable,
            'min_required_version': self.min_required_version,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self) -> str:
        return f'<FirmwareVersion {self.version} for {self.robot_type}>'


class FirmwareUpdate(db.Model):
    """Tracks firmware update operations for robots.

    Records the history of firmware updates including status, progress,
    and any errors that occurred during the update process.
    """
    __tablename__ = 'firmware_update'
    id = db.Column(db.Integer, primary_key=True)
    robot_id = db.Column(db.Integer, db.ForeignKey('robot.id'), nullable=False, index=True)
    firmware_version_id = db.Column(
        db.Integer,
        db.ForeignKey('firmware_version.id'),
        nullable=False
    )
    initiated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Update status: pending, downloading, installing, completed, failed, cancelled
    status = db.Column(db.String(32), default='pending', index=True)
    progress = db.Column(db.Integer, default=0)  # Progress percentage (0-100)
    error_message = db.Column(db.Text)  # Error details if failed
    previous_version = db.Column(db.String(32))  # Version before update

    started_at = db.Column(db.DateTime, default=db.func.now())
    completed_at = db.Column(db.DateTime)

    # Relationships
    robot = db.relationship('Robot', backref=db.backref('firmware_updates', lazy='dynamic'))
    firmware_version = db.relationship('FirmwareVersion', backref='updates')
    user = db.relationship('User', backref=db.backref('initiated_updates', lazy='dynamic'))

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'robot_id': self.robot_id,
            'robot_name': self.robot.name if self.robot else None,
            'firmware_version': self.firmware_version.version if self.firmware_version else None,
            'target_version': self.firmware_version.version if self.firmware_version else None,
            'status': self.status,
            'progress': self.progress,
            'error_message': self.error_message,
            'previous_version': self.previous_version,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'initiated_by': self.user.username if self.user else None
        }

    def __repr__(self) -> str:
        return f'<FirmwareUpdate robot={self.robot_id} version={self.firmware_version_id} status={self.status}>'


class Device(db.Model):
    """Device registration and binding model.

    Tracks devices that are bound to user accounts for Edge App access.
    Each device is identified by a unique device_id and can be bound to a user.
    """
    __tablename__ = 'device'
    id = db.Column(db.Integer, primary_key=True)

    # Device identification
    device_id = db.Column(db.String(64), nullable=False, unique=True, index=True)  # SHA-256 hash
    device_name = db.Column(db.String(128))  # User-friendly name (e.g., "My Laptop")
    device_type = db.Column(db.String(32), default='unknown')  # desktop, laptop, mobile, edge_device

    # Device binding
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    bound_at = db.Column(db.DateTime, nullable=False, default=db.func.now())
    last_seen_at = db.Column(db.DateTime, default=db.func.now())

    # Device status
    is_active = db.Column(db.Boolean, default=True, index=True)  # Can be deactivated by user
    is_trusted = db.Column(db.Boolean, default=False)  # Trusted devices skip 2FA

    # Device metadata
    platform = db.Column(db.String(32))  # Windows, Linux, macOS
    hostname = db.Column(db.String(128))
    ip_address = db.Column(db.String(64))  # Last known IP
    user_agent = db.Column(db.String(512))

    # Timestamps
    created_at = db.Column(db.DateTime, index=True, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    # Relationships
    user = db.relationship('User', backref=db.backref('devices', lazy='dynamic'))

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'device_name': self.device_name or f'{self.platform} Device',
            'device_type': self.device_type,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'bound_at': self.bound_at.isoformat() if self.bound_at else None,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
            'is_active': self.is_active,
            'is_trusted': self.is_trusted,
            'platform': self.platform,
            'hostname': self.hostname,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self) -> str:
        return f'<Device {self.device_id[:8]}... user={self.user_id}>'


class AuditLog(db.Model):
    """Audit log for security and compliance tracking.

    Records all security-sensitive operations including authentication,
    authorization, data access, and configuration changes.
    Follows the EventLog schema from docs/contract/event_log.schema.json.
    """
    __tablename__ = 'audit_log'
    id = db.Column(db.Integer, primary_key=True)

    # Core EventLog fields
    trace_id = db.Column(db.String(64), nullable=False, index=True)  # UUID for request tracking
    timestamp = db.Column(db.DateTime, nullable=False, index=True, default=db.func.now())
    severity = db.Column(db.String(16), nullable=False, index=True)  # INFO, WARN, ERROR
    category = db.Column(db.String(32), nullable=False, index=True)  # auth, command, audit, etc.
    message = db.Column(db.Text, nullable=False)

    # Context data (stored as JSON)
    context = db.Column(db.JSON)  # Additional context data

    # Enhanced audit fields
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)  # User who performed the action
    action = db.Column(db.String(64), index=True)  # Action type (login, logout, command_execute, etc.)
    resource_type = db.Column(db.String(64))  # Type of resource affected (user, robot, command, etc.)
    resource_id = db.Column(db.String(64))  # ID of affected resource
    ip_address = db.Column(db.String(64))  # Client IP address
    user_agent = db.Column(db.String(512))  # Client user agent
    status = db.Column(db.String(32))  # success, failure, denied

    # Relationships
    user = db.relationship('User', backref=db.backref('audit_logs', lazy='dynamic'))

    # Indexes for common queries
    __table_args__ = (
        db.Index('idx_audit_timestamp_severity', 'timestamp', 'severity'),
        db.Index('idx_audit_user_action', 'user_id', 'action'),
        db.Index('idx_audit_category_timestamp', 'category', 'timestamp'),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            'id': self.id,
            'trace_id': self.trace_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'severity': self.severity,
            'category': self.category,
            'message': self.message,
            'context': self.context,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'ip_address': self.ip_address,
            'status': self.status
        }

    def __repr__(self) -> str:
        return f'<AuditLog {self.id} {self.action} by user={self.user_id}>'
