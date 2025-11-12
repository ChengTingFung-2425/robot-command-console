import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI") or \
        'postgresql://postgres:postgres@postgresdb:5432/postgres'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or "mailhog"
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 1025)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['cywong@example.com']
    POSTS_PER_PAGE = 3
    LANGUAGES = ['en', 'es', 'zh']
    
    # MQTT 配置（用於發送指令到機器人）
    MQTT_ENABLED = os.environ.get('MQTT_ENABLED', 'false').lower() == 'true'
    MQTT_BROKER = os.environ.get('MQTT_BROKER') or 'a1qlex7vqi1791-ats.iot.us-east-1.amazonaws.com'
    MQTT_PORT = int(os.environ.get('MQTT_PORT') or 8883)
    MQTT_USE_TLS = os.environ.get('MQTT_USE_TLS', 'true').lower() == 'true'
    MQTT_CERT_PATH = os.environ.get('MQTT_CERT_PATH') or os.path.join(basedir, 'certificates')
    MQTT_CA_CERT = os.environ.get('MQTT_CA_CERT') or 'AmazonRootCA1.pem'
    MQTT_TIMEOUT = int(os.environ.get('MQTT_TIMEOUT') or 5)
