from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

# 指令發送表單（如需 Web 表單介面）
class CommandForm(FlaskForm):
    robot_id = StringField('Robot ID', validators=[DataRequired()])
    command = StringField('Command', validators=[DataRequired()])
    submit = SubmitField('Send Command')
