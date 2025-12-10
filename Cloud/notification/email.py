# 用於機器人狀態/異常通知的郵件發送
# 注意：此檔案已從 WebUI 移動到 Cloud 服務
# 需要在 Cloud 服務中建立獨立的 Flask app 和 mail 實例
# 或重構為接受 app 和 mail 作為參數的函式

from threading import Thread
from flask_mail import Message

# TODO: 此檔案需要在 Cloud 服務中重構
# 選項 1: 建立獨立的 Cloud Flask app 和 mail 實例
# 選項 2: 重構為接受 app 和 mail 作為參數的函式
# 暫時註解掉直接依賴 WebUI 的程式碼

# from WebUI.app import app, mail  # 已移除 - 造成循環依賴


def send_async_email(app, mail, msg):
    """於 app context 下非同步發送郵件
    
    Args:
        app: Flask application instance
        mail: Flask-Mail instance
        msg: Message instance
    """
    with app.app_context():
        mail.send(msg)


def send_email(subject, sender, recipients, text_body, html_body=None, app=None, mail=None):
    """發送郵件，可選擇純文字與 HTML 內容
    
    Args:
        subject: 郵件主旨
        sender: 寄件者
        recipients: 收件者列表
        text_body: 純文字內容
        html_body: HTML 內容（可選）
        app: Flask application instance（必填）
        mail: Flask-Mail instance（必填）
    """
    if app is None or mail is None:
        raise ValueError("此函式需要 Flask app 和 mail 實例。請在 Cloud 服務中提供這些實例。")
    
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    if html_body:
        msg.html = html_body
    Thread(target=send_async_email, args=(app, mail, msg)).start()
