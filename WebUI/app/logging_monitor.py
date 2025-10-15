import logging

logger = logging.getLogger('webui')

# 可擴充：將日誌寫入資料庫、檔案或外部監控系統

def log_event(event, level='info'):
    record = {'event': event, 'level': level}
    logger.log(getattr(logging, level.upper(), logging.INFO), event)
    # 可擴充：回傳帶有 timestamp 的日誌物件
    return record
