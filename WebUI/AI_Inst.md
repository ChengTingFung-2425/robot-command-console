# Python 檔案格式化範本

請遵循以下順序與格式撰寫 Python 檔案：

1. imports（標準庫、第三方、專案內，分段）
2. class 
3. function 定義（依功能分組，加註 docstring）
4. main 區塊（如有，使用 if __name__ == '__main__':）

範例：

```python
# imports
import os
from threading import Thread
from flask_mail import Message
from WebUI.app import app, mail

# functions
def send_async_email(app, msg):
    """於 app context 下非同步發送郵件"""
    with app.app_context():
        mail.send(msg)

def send_email(subject, sender, recipients, text_body, html_body=None):
    """發送郵件，可選擇純文字與 HTML 內容"""
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    if html_body:
        msg.html = html_body
    Thread(target=send_async_email, args=(app, msg)).start()

# main（如有）
if __name__ == '__main__':
    # 測試或 CLI 入口
    pass
```

如無 main 區塊可省略。所有檔案請統一此結構，便於維護與自動化工具解析。
