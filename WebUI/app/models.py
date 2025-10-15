
# imports
from WebUI.app import db

# classes
class Robot(db.Model):
    """機器人資料表"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    type = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(64), default='idle')

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
