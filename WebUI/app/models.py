
# imports

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from time import time
import jwt
from flask import current_app
from WebUI.app import db, login

# classes

class User(UserMixin, db.Model):
    """用戶資料表"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(32), default='operator')  # viewer/operator/admin/auditor
    # UI preferences
    ui_duration_unit = db.Column(db.String(8), default='s')  # 's' or 'ms'
    ui_verify_collapsed = db.Column(db.Boolean, default=False)
    robots = db.relationship('Robot', backref='owner', lazy='dynamic')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if 'role' not in kwargs:
            self.role = 'operator'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role in ['admin', 'auditor']
    
    def get_reset_password_token(self, expires_in=600):
        """生成密碼重設 token (有效期 10 分鐘)"""
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256'
        )
    
    @staticmethod
    def verify_reset_password_token(token):
        """驗證密碼重設 token"""
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                          algorithms=['HS256'])['reset_password']
        except:
            return None
        return User.query.get(id)

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
