
# imports

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from WebUI.app import db, login

# classes

class User(UserMixin, db.Model):
    """用戶資料表"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(32), default='operator')  # viewer/operator/admin/auditor
    robots = db.relationship('Robot', backref='owner', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role in ['admin', 'auditor']

    def __repr__(self):
        return f'<User {self.username}>'

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Robot(db.Model):
    """機器人資料表"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    type = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(64), default='idle')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f'<Robot {self.name}>'

class Command(db.Model):
    """指令資料表"""
    id = db.Column(db.Integer, primary_key=True)
    robot_id = db.Column(db.Integer, db.ForeignKey('robot.id'))
    command = db.Column(db.String(128), nullable=False)
    status = db.Column(db.String(64), default='pending')
    timestamp = db.Column(db.DateTime, index=True)

    def __repr__(self):
        return f'<Command {self.command} to robot {self.robot_id}>'

class AdvancedCommand(db.Model):
    """進階指令資料表"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    description = db.Column(db.Text)
    category = db.Column(db.String(64), index=True)
    base_commands = db.Column(db.Text, nullable=False)  # JSON 格式的基礎指令序列
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User', backref='advanced_commands')
    status = db.Column(db.String(32), default='pending')  # pending/approved/rejected
    created_at = db.Column(db.DateTime, index=True, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())

    def __repr__(self):
        return f'<AdvancedCommand {self.name}>'
