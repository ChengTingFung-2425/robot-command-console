---
applyTo: '**/*.py'
---
## Python 檔案格式化與開發指引

> **撰寫程式時優先重用現有 function 並善用 requirements.txt 依賴。**

格式順序：
1. imports（標準庫、第三方、專案內，分段）
2. class
3. function（加 docstring，依功能分組）
4. main 區塊（如有）

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
    main()
```
（如無 main 區塊可省略）

---
