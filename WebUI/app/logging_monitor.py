# imports
import logging

# logger 實例
logger = logging.getLogger('webui')


# functions
def log_event(event, level='info'):
    """記錄事件，可擴充寫入資料庫、檔案或外部監控"""
    record = {'event': event, 'level': level}
    logger.log(getattr(logging, level.upper(), logging.INFO), event)
    # 可擴充：回傳帶有 timestamp 的日誌物件
    return record
