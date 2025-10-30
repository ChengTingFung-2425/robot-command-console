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
---
applyTo: '**/*.py'
---
## Python 檔案格式化與開發指引

> **撰寫程式時優先重用現有 function 並善用 `requirements.txt` 依賴。**

格式順序：
1. imports（標準庫、第三方、專案內，分段）
2. class
3. function（加 docstring，依功能分組）
4. main 區塊（如有，例如 `if __name__ == '__main__'`）

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

---
**開發流程建議**：
- 分步進行：首先建立記錄本次更新內容的文件（例如在 `docs/`），接著根據這些文件撰寫對應的測試，最後實作程式碼以通過那些測試，確保所有測試都通過。
- 善用待辦事項清單：在記錄本次更新內容的文件中標記這些大步驟，並將其拆分為更小的任務，使用你的待辦事項工具標記它們。如果需要進一步拆分，重複此過程，直到你擁有可管理的任務。