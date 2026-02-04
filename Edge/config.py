import os
from aio_pika import logger
import toml
import platform
from src.common.config import BaseConfig

basedir = os.path.abspath(os.path.dirname(__file__))
# Determine the appropriate configuration directory based on the OS
if platform.system() == "Linux":
    config_dir = "/etc/robot-command-console"
elif platform.system() == "Windows":
    config_dir = os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "robot-command-console")
else:
    config_dir = basedir  # Fallback to the current directory
# Check if the configuration file exists in the determined directory
if not os.path.exists(config_dir):
    logger.warning(f"Configuration file not found in {config_dir}. Falling back to local directory.")
    config_dir = basedir
config_path = os.path.join(config_dir, 'config.toml')
# Check if the configuration file exists in the determined directory
if not os.path.exists(config_path):
    logger.warning(f"Configuration file not found in {config_path}. Creating a default configuration file.")
    default_config = {
        "SECRET_KEY": "you-will-never-guess",
        "SQLALCHEMY_DATABASE_URI": "postgresql://postgres:postgres@postgresdb:5432/postgres",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "MAIL_SERVER": "mailhog",
        "MAIL_PORT": 1025,
        "MAIL_USE_TLS": False,
        "MAIL_USERNAME": "",
        "MAIL_PASSWORD": "",
        "ADMINS": ["cywong@example.com"],
        "POSTS_PER_PAGE": 3,
        "LANGUAGES": ["en", "es", "zh"],
        "MQTT_ENABLED": False,
        "MQTT_BROKER": "a1qlex7vqi1791-ats.iot.us-east-1.amazonaws.com",
        "MQTT_PORT": 8883,
        "MQTT_USE_TLS": True,
        "MQTT_CERT_PATH": os.path.join(basedir, 'certificates'),
        "MQTT_CA_CERT": "AmazonRootCA1.pem",
        "MQTT_TIMEOUT": 5,
        "DOWNLOAD_DIR": "/tmp/downloads"
    }
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w') as config_file:
        toml.dump(default_config, config_file)

# Load configuration from the final path
config_data = toml.load(config_path)

class Config(BaseConfig):
    SECRET_KEY = config_data.get("SECRET_KEY", "you-will-never-guess")
    SQLALCHEMY_DATABASE_URI = config_data.get("SQLALCHEMY_DATABASE_URI", 'postgresql://postgres:postgres@postgresdb:5432/postgres')
    SQLALCHEMY_TRACK_MODIFICATIONS = config_data.get("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    MAIL_SERVER = config_data.get("MAIL_SERVER", "mailhog")
    MAIL_PORT = int(config_data.get("MAIL_PORT", 1025))
    MAIL_USE_TLS = config_data.get("MAIL_USE_TLS", False)
    MAIL_USERNAME = config_data.get("MAIL_USERNAME")
    MAIL_PASSWORD = config_data.get("MAIL_PASSWORD")
    ADMINS = config_data.get("ADMINS", ['cywong@example.com'])
    POSTS_PER_PAGE = config_data.get("POSTS_PER_PAGE", 3)
    LANGUAGES = config_data.get("LANGUAGES", ['en', 'es', 'zh'])

    # MQTT 配置（用於發送指令到機器人）
    MQTT_ENABLED = config_data.get("MQTT_ENABLED", False)
    MQTT_BROKER = config_data.get("MQTT_BROKER", 'a1qlex7vqi1791-ats.iot.us-east-1.amazonaws.com')
    MQTT_PORT = int(config_data.get("MQTT_PORT", 8883))
    MQTT_USE_TLS = config_data.get("MQTT_USE_TLS", True)
    MQTT_CERT_PATH = config_data.get("MQTT_CERT_PATH", os.path.join(basedir, 'certificates'))
    MQTT_CA_CERT = config_data.get("MQTT_CA_CERT", 'AmazonRootCA1.pem')
    MQTT_TIMEOUT = int(config_data.get("MQTT_TIMEOUT", 5))
    DOWNLOAD_DIR = config_data.get("DOWNLOAD_DIR", '/tmp/downloads')

class EdgeConfig(Config):
    # Extend the base configuration with Edge-specific settings
    EDGE_SERVICE_TIMEOUT = 300
    EDGE_HEALTH_CHECK_INTERVAL = 60
