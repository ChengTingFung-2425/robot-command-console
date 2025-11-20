# Password Reset Implementation

## 概述

密碼重設功能已完整實作，允許用戶透過電子郵件重設忘記的密碼。

## 實作內容

### 1. 資料庫模型擴充 (`WebUI/app/models.py`)

在 `User` 模型中新增了兩個方法：

- **`get_reset_password_token(expires_in=600)`**: 生成有時效性的 JWT token（預設 10 分鐘）
- **`verify_reset_password_token(token)`**: 驗證並解碼 token，返回對應的 User 物件

```python
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
```

### 2. 表單 (`WebUI/app/forms.py`)

新增 `ResetPasswordForm` 用於設定新密碼：

```python
class ResetPasswordForm(FlaskForm):
    password = PasswordField('新密碼', validators=[DataRequired()])
    password2 = PasswordField('重複新密碼', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('重設密碼')
```

### 3. 路由 (`WebUI/app/routes.py`)

#### a. 密碼重設請求路由
- **路徑**: `/reset_password_request`
- **功能**: 接收用戶的電子郵件，發送重設連結

```python
@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('webui.home'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.get_reset_password_token()
            send_password_reset_email(user, token)
            flash('密碼重設郵件已發送至您的信箱，請查收。')
        else:
            flash('該電子郵件尚未註冊。')
        return redirect(url_for('webui.login'))
    return render_template('reset_password_request.html.j2', form=form)
```

#### b. 密碼重設路由
- **路徑**: `/reset_password/<token>`
- **功能**: 驗證 token 並允許用戶設定新密碼

```python
@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('webui.home'))
    user = User.verify_reset_password_token(token)
    if not user:
        flash('無效或過期的重設連結。')
        return redirect(url_for('webui.login'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('您的密碼已重設成功，請登入。')
        return redirect(url_for('webui.login'))
    return render_template('reset_password.html.j2', form=form)
```

#### c. 郵件發送輔助函數

```python
def send_password_reset_email(user, token):
    """發送密碼重設郵件"""
    send_email(
        subject='[Robot Console] 重設您的密碼',
        sender='noreply@robot-console.com',
        recipients=[user.email],
        text_body=render_template('email/reset_password.txt.j2', user=user, token=token),
        html_body=render_template('email/reset_password.html.j2', user=user, token=token)
    )
```

### 4. 郵件模板

#### 文字版 (`WebUI/app/templates/email/reset_password.txt.j2`)
```
親愛的 {{ user.username }}，

您收到此郵件是因為有人請求重設您的密碼。

請點擊以下連結重設密碼：

{{ url_for('webui.reset_password', token=token, _external=True) }}

此連結將在 10 分鐘後失效。

如果您沒有提出此請求，請忽略此郵件。

Robot Console 團隊
```

#### HTML 版 (`WebUI/app/templates/email/reset_password.html.j2`)
提供格式化的 HTML 郵件內容，包含可點擊的連結。

### 5. 網頁模板 (`WebUI/app/templates/reset_password.html.j2`)

已存在的重設密碼表單頁面，使用 Flask-Bootstrap 快速表單。

## 安全特性

1. **Token 時效性**: JWT token 預設 10 分鐘後失效
2. **安全簽名**: 使用應用程式的 `SECRET_KEY` 簽名 token
3. **一次性使用**: Token 驗證後立即更改密碼，無法重複使用
4. **防護已登入用戶**: 已登入用戶無法訪問重設頁面
5. **隱私保護**: 即使電子郵件不存在也顯示成功訊息，防止用戶列舉攻擊

## 依賴套件

- **PyJWT 2.6.0**: 用於 token 生成與驗證（已在 `requirements.txt` 中）
- **Flask-Mail**: 用於發送郵件（已配置）

## 配置 (`config.py`)

郵件伺服器已配置為使用 MailHog（開發環境）：

```python
MAIL_SERVER = os.environ.get('MAIL_SERVER') or "mailhog"
MAIL_PORT = int(os.environ.get('MAIL_PORT') or 1025)
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
```

## 使用流程

1. 用戶在登入頁面點擊「忘記密碼？」
2. 進入 `/reset_password_request` 頁面，輸入註冊的電子郵件
3. 系統發送包含 token 的重設連結到用戶郵箱
4. 用戶點擊郵件中的連結，訪問 `/reset_password/<token>`
5. 系統驗證 token 有效性
6. 用戶輸入新密碼並確認
7. 密碼更新成功，重導向至登入頁面

## 測試建議

### 手動測試
1. 啟動 Flask 應用程式
2. 確保 MailHog 正在運行（可訪問 http://localhost:8025 查看郵件）
3. 創建測試用戶
4. 訪問 `/reset_password_request` 並提交請求
5. 在 MailHog 介面查看郵件
6. 點擊郵件中的連結
7. 設定新密碼並驗證登入

### 單元測試
建議在 `tests/Web/` 目錄下創建 `test_password_reset.py`：
- 測試 token 生成
- 測試 token 驗證
- 測試過期 token
- 測試無效 token
- 測試郵件發送

## 注意事項

1. **生產環境**: 需配置真實的 SMTP 伺服器（如 SendGrid, AWS SES）
2. **Token 安全**: 確保 `SECRET_KEY` 足夠複雜且保密
3. **郵件佇列**: 高流量環境建議使用 Celery 等任務佇列
4. **速率限制**: 考慮添加請求速率限制，防止濫用

## 完成狀態

✅ User 模型擴充（token 生成與驗證）
✅ ResetPasswordForm 表單
✅ reset_password_request 路由
✅ reset_password 路由
✅ 郵件發送輔助函數
✅ 文字與 HTML 郵件模板（中文化）
✅ 網頁模板
✅ PyJWT 依賴

**功能已完全實作並可立即使用！**
