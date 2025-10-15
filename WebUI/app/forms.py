
# imports
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

# classes
class CommandForm(FlaskForm):
    """指令發送表單（如需 Web 表單介面）"""
    robot_id = StringField('Robot ID', validators=[DataRequired()])
    command = StringField('Command', validators=[DataRequired()])
    submit = SubmitField('Send Command')
