
# imports

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from time import time
import jwt
from flask import current_app
from WebUI.app import db, login


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


class Robot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    type = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(64), default='idle')
    battery = db.Column(db.Integer, default=100)  # 電池電量百分比 (0-100)
    location = db.Column(db.String(128))  # 機器人位置
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self) -> str:
        return f'<Robot {self.name}>'


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
    versions = db.relationship('AdvancedCommandVersion', backref='advanced_command', lazy='dynamic', cascade='all, delete-orphan')

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
