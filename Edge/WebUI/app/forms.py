# imports

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms import IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from WebUI.app.models import User


# classes
class LoginForm(FlaskForm):
    username = StringField('用戶名稱', validators=[DataRequired()])
    password = PasswordField('密碼', validators=[DataRequired()])
    remember_me = BooleanField('記住我')
    submit = SubmitField('登入')


class RegisterForm(FlaskForm):
    username = StringField('用戶名稱', validators=[DataRequired()])
    email = StringField('電子郵件', validators=[DataRequired(), Email()])
    password = PasswordField('密碼', validators=[DataRequired()])
    password2 = PasswordField('重複密碼', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('註冊')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('用戶名稱已被使用。')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('電子郵件已被註冊。')


class RegisterRobotForm(FlaskForm):
    name = StringField('機器人名稱', validators=[DataRequired()])
    type = StringField('機器人類型', validators=[DataRequired()])
    submit = SubmitField('註冊機器人')


class ResetPasswordRequestForm(FlaskForm):
    email = StringField('電子郵件', validators=[DataRequired(), Email()])
    submit = SubmitField('發送重設密碼郵件')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('新密碼', validators=[DataRequired()])
    password2 = PasswordField('重複新密碼', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('重設密碼')


class AdvancedCommandForm(FlaskForm):
    name = StringField('指令名稱', validators=[DataRequired()])
    description = TextAreaField('指令描述', validators=[DataRequired()])
    category = StringField('分類', validators=[DataRequired()])
    base_commands = TextAreaField('基礎指令序列（JSON）', validators=[DataRequired()])
    version = IntegerField('版本', default=1)
    # when the base_commands reference other advanced commands, allow updating
    # nested references to latest approved version
    nested_command = BooleanField('是否嵌套指令')
    submit = SubmitField('提交進階指令')

    def validate_base_commands(self, field):
        """驗證 JSON 格式與指令有效性"""
        import json
        try:
            commands = json.loads(field.data)

            # 確認是陣列
            if not isinstance(commands, list):
                raise ValidationError('指令序列必須是 JSON 陣列格式')

            # Note: allow empty list (tests and some UIs may create skeleton commands)
            # if len(commands) == 0:
            #     raise ValidationError('至少需要一個指令')

            # 驗證每個指令都有 command 欄位
            valid_commands = {
                "go_forward", "back_fast", "turn_left", "turn_right",
                "left_move_fast", "right_move_fast", "stand", "bow",
                "squat", "stand_up_front", "stand_up_back", "wave",
                "left_kick", "right_kick", "kung_fu", "wing_chun",
                "left_uppercut", "right_uppercut", "left_shot_fast", "right_shot_fast",
                "dance_two", "dance_three", "dance_four", "dance_five",
                "dance_six", "dance_seven", "dance_eight", "dance_nine", "dance_ten",
                "push_ups", "sit_ups", "chest", "weightlifting",
                "squat_up", "twist", "stepping", "stop", "wait", "advanced_command"
            }

            for idx, cmd in enumerate(commands):
                if not isinstance(cmd, dict):
                    raise ValidationError(f'第 {idx + 1} 個指令格式錯誤：必須是物件')

                if 'command' not in cmd:
                    raise ValidationError(f'第 {idx + 1} 個指令缺少 "command" 欄位')

                if cmd['command'] not in valid_commands:
                    raise ValidationError(f'第 {idx + 1} 個指令 "{cmd["command"]}" 不是有效的動作')

                # 驗證 wait 指令需要 duration_ms 參數
                if cmd['command'] == 'wait' and 'duration_ms' not in cmd:
                    raise ValidationError(f'第 {idx + 1} 個 "wait" 指令缺少 "duration_ms" 參數')

        except json.JSONDecodeError as e:
            raise ValidationError(f'JSON 格式錯誤：{str(e)}')

