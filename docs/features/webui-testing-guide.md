# 測試指南

## 測試密碼重設功能

### 前置條件
1. 確保 Flask 應用程式正在運行
2. 確保 PostgreSQL 資料庫已啟動
3. 確保 MailHog 正在運行（用於接收郵件）

### 測試步驟

#### 1. 啟動服務
```bash
# 終端 1: 啟動 Flask 應用
cd /workspaces/robot-command-console
python app.py

# 終端 2: 確認 MailHog 已啟動
# 訪問 http://localhost:8025 查看 MailHog 介面
```

#### 2. 創建測試用戶
```bash
# 方法 1: 通過 Web 介面註冊
# 訪問 http://localhost:5000/register

# 方法 2: 通過 Python shell
cd /workspaces/robot-command-console/WebUI
PYTHONPATH=/workspaces/robot-command-console:$PYTHONPATH flask shell

>>> from app.models import User
>>> from app import db
>>> user = User(username='testuser', email='test@example.com')
>>> user.set_password('password123')
>>> db.session.add(user)
>>> db.session.commit()
>>> exit()
```

#### 3. 測試密碼重設流程

##### 步驟 3.1: 請求密碼重設
1. 訪問 http://localhost:5000/login
2. 點擊「忘記密碼？」連結（如有）或直接訪問 http://localhost:5000/reset_password_request
3. 輸入註冊的電子郵件（例如：test@example.com）
4. 點擊「發送重設密碼郵件」
5. 應該看到訊息：「密碼重設郵件已發送至您的信箱，請查收。」

##### 步驟 3.2: 查看郵件
1. 訪問 MailHog 介面：http://localhost:8025
2. 應該看到一封主旨為「[Robot Console] 重設您的密碼」的郵件
3. 點擊郵件查看內容
4. 複製重設密碼連結（格式：http://localhost:5000/reset_password/<token>）

##### 步驟 3.3: 重設密碼
1. 將連結貼到瀏覽器網址列
2. 應該看到密碼重設表單
3. 輸入新密碼（例如：newpassword456）
4. 再次輸入確認新密碼
5. 點擊「重設密碼」
6. 應該看到訊息：「您的密碼已重設成功，請登入。」
7. 重導向至登入頁面

##### 步驟 3.4: 驗證新密碼
1. 使用新密碼登入
2. 應該能成功登入

#### 4. 測試錯誤情況

##### 測試 4.1: 不存在的電子郵件
1. 訪問 http://localhost:5000/reset_password_request
2. 輸入未註冊的電子郵件
3. 應該看到訊息：「該電子郵件尚未註冊。」

##### 測試 4.2: 過期的 Token
1. 等待 10 分鐘後再使用舊的重設連結
2. 應該看到訊息：「無效或過期的重設連結。」

##### 測試 4.3: 無效的 Token
1. 手動修改 URL 中的 token
2. 訪問修改後的連結
3. 應該看到訊息：「無效或過期的重設連結。」

## 測試進階指令篩選與排序

### 前置條件
1. 至少有一個 Admin 或 Auditor 角色的用戶
2. 資料庫中有多個進階指令（不同狀態）

### 測試步驟

#### 1. 創建測試資料

```bash
cd /workspaces/robot-command-console/WebUI
PYTHONPATH=/workspaces/robot-command-console:$PYTHONPATH flask shell

>>> from app.models import User, AdvancedCommand
>>> from app import db
>>> 
>>> # 創建 Admin 用戶
>>> admin = User(username='admin', email='admin@example.com', role='admin')
>>> admin.set_password('admin123')
>>> db.session.add(admin)
>>> db.session.commit()
>>> 
>>> # 創建測試指令
>>> cmd1 = AdvancedCommand(name='指令A', description='測試指令A', category='導航', 
...                        base_commands='["forward", "turn_left"]', 
...                        status='pending', author_id=admin.id)
>>> cmd2 = AdvancedCommand(name='指令B', description='測試指令B', category='清潔', 
...                        base_commands='["clean", "return"]', 
...                        status='approved', author_id=admin.id)
>>> cmd3 = AdvancedCommand(name='指令C', description='測試指令C', category='導航', 
...                        base_commands='["forward", "turn_right"]', 
...                        status='rejected', author_id=admin.id)
>>> db.session.add_all([cmd1, cmd2, cmd3])
>>> db.session.commit()
>>> exit()
```

#### 2. 測試篩選功能

##### 測試 2.1: Admin 查看所有指令
1. 以 Admin 身份登入
2. 訪問 http://localhost:5000/advanced_commands
3. 應該能看到所有狀態的指令
4. 應該看到狀態篩選下拉選單

##### 測試 2.2: 篩選待審核指令
1. 在狀態下拉選單選擇「待審核」
2. 頁面應自動重新載入
3. 僅顯示 status='pending' 的指令
4. 狀態下拉選單應保持「待審核」選項被選中

##### 測試 2.3: 篩選已批准指令
1. 在狀態下拉選單選擇「已批准」
2. 僅顯示 status='approved' 的指令

##### 測試 2.4: 會話持久化
1. 選擇「待審核」篩選
2. 訪問其他頁面（例如 Dashboard）
3. 再次返回進階指令頁面
4. 應該仍然顯示「待審核」篩選

#### 3. 測試排序功能

##### 測試 3.1: 按名稱排序
1. 在排序下拉選單選擇「名稱」
2. 指令應按名稱字母順序排列

##### 測試 3.2: 按建立時間排序（降序）
1. 選擇排序「建立時間」，順序「降序」
2. 最新建立的指令應出現在最上方

##### 測試 3.3: 多重篩選與排序
1. 狀態選擇「待審核」
2. 排序選擇「名稱」，順序「升序」
3. 應該僅顯示待審核的指令，並按名稱升序排列

#### 4. 測試一般用戶權限

##### 測試 4.1: 一般用戶僅見已批准指令
1. 建立或登入一個 operator 角色的用戶
2. 訪問 http://localhost:5000/advanced_commands
3. 應該僅看到 status='approved' 的指令
4. 不應該看到篩選與排序控制
5. 不應該看到審核按鈕

## 測試審核功能

### 測試步驟

#### 1. 審核進階指令
1. 以 Admin 身份登入
2. 訪問進階指令頁面
3. 展開一個待審核的指令
4. 點擊「批准」按鈕
5. 應該看到訊息：「進階指令「XXX」已批准。」
6. 指令狀態標籤應變為綠色「已批准」

#### 2. 拒絕進階指令
1. 展開另一個待審核的指令
2. 點擊「拒絕」按鈕
3. 應該看到訊息：「進階指令「XXX」已拒絕。」
4. 指令狀態標籤應變為紅色「已拒絕」

## 自動化測試（建議）

### 單元測試範例

```python
# tests/Web/test_password_reset.py
import unittest
from WebUI.app import app, db
from WebUI.app.models import User
import time

class PasswordResetTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        with app.app_context():
            db.create_all()
    
    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_token_generation(self):
        """測試 token 生成"""
        with app.app_context():
            user = User(username='test', email='test@example.com')
            db.session.add(user)
            db.session.commit()
            
            token = user.get_reset_password_token()
            self.assertIsNotNone(token)
            self.assertIsInstance(token, str)
    
    def test_token_verification(self):
        """測試 token 驗證"""
        with app.app_context():
            user = User(username='test', email='test@example.com')
            db.session.add(user)
            db.session.commit()
            
            token = user.get_reset_password_token()
            verified_user = User.verify_reset_password_token(token)
            
            self.assertIsNotNone(verified_user)
            self.assertEqual(verified_user.id, user.id)
    
    def test_expired_token(self):
        """測試過期 token"""
        with app.app_context():
            user = User(username='test', email='test@example.com')
            db.session.add(user)
            db.session.commit()
            
            # 生成 1 秒有效期的 token
            token = user.get_reset_password_token(expires_in=1)
            time.sleep(2)  # 等待 token 過期
            
            verified_user = User.verify_reset_password_token(token)
            self.assertIsNone(verified_user)
    
    def test_invalid_token(self):
        """測試無效 token"""
        with app.app_context():
            verified_user = User.verify_reset_password_token('invalid_token')
            self.assertIsNone(verified_user)

if __name__ == '__main__':
    unittest.main()
```

### 執行測試

```bash
cd /workspaces/robot-command-console
python -m pytest tests/Web/test_password_reset.py -v
```

## 除錯技巧

### 1. 檢查郵件發送
```bash
# 查看 Flask 應用程式日誌
tail -f /workspaces/robot-command-console/WebUI/logs/microblog.log

# 確認 MailHog 正在運行
docker ps | grep mailhog
```

### 2. 檢查 Token
```python
# 在 Flask shell 中解碼 token
import jwt
from flask import current_app

token = "your_token_here"
try:
    data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
    print(data)
except Exception as e:
    print(f"Error: {e}")
```

### 3. 檢查資料庫狀態
```bash
cd /workspaces/robot-command-console/WebUI
PYTHONPATH=/workspaces/robot-command-console:$PYTHONPATH flask shell

>>> from app.models import User, AdvancedCommand
>>> User.query.all()  # 查看所有用戶
>>> AdvancedCommand.query.all()  # 查看所有進階指令
>>> AdvancedCommand.query.filter_by(status='pending').all()  # 查看待審核指令
```

## 常見問題

### Q1: 收不到郵件
**A**: 檢查 MailHog 是否正在運行，訪問 http://localhost:8025

### Q2: Token 無效
**A**: 檢查 SECRET_KEY 是否正確配置，確認 token 未過期

### Q3: 篩選不生效
**A**: 檢查瀏覽器的 Cookie 設定，確保 Session 正常運作

### Q4: 權限檢查失敗
**A**: 確認用戶的 role 欄位正確設定為 'admin' 或 'auditor'

---

**測試完成後，請確保所有功能正常運作！**
