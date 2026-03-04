"""
雲端服務入口點

啟動 Flask 應用程式，註冊所有雲端服務 Blueprint，
包含：認證/儲存、資料同步、進階指令共享、社群互動、用戶管理。
"""

import logging
import os

from flask import Flask

from Cloud.api.auth import CloudAuthService
from Cloud.api.data_sync import data_sync_bp, init_data_sync_api
from Cloud.api.routes import cloud_bp, init_cloud_services
from Cloud.engagement.api import bp as engagement_bp, init_engagement_api
from Cloud.shared_commands.api import bp as shared_commands_bp, init_shared_commands_api
from Cloud.user_management.api import user_mgmt_bp, init_user_management
from Cloud.user_management.service import CloudUserService

logger = logging.getLogger(__name__)


def create_app(
    jwt_secret: str = None,
    storage_path: str = None,
    database_url: str = None,
    engagement_db_url: str = None,
) -> Flask:
    """建立並設定 Flask 應用程式

    Args:
        jwt_secret: JWT 密鑰（預設讀取環境變數 CLOUD_JWT_SECRET）
        storage_path: 檔案儲存根路徑（預設讀取環境變數 CLOUD_STORAGE_PATH）
        database_url: 進階指令共享資料庫 URL（預設讀取環境變數 CLOUD_DB_URL）
        engagement_db_url: 社群互動資料庫 URL（預設讀取環境變數 CLOUD_ENGAGEMENT_DB_URL）

    Returns:
        設定完成的 Flask 應用程式
    """
    app = Flask(__name__)

    # 讀取設定（優先使用參數，其次讀取環境變數，最後依環境決定是否允許預設值）
    jwt_secret = jwt_secret or os.environ.get('CLOUD_JWT_SECRET', '')
    if not jwt_secret:
        flask_env = os.environ.get('FLASK_ENV', '').lower()
        cloud_env = os.environ.get('CLOUD_ENV', '').lower()
        is_dev_mode = flask_env in {'development', 'dev'} or cloud_env in {'development', 'dev'}
        if not is_dev_mode:
            raise RuntimeError(
                'CLOUD_JWT_SECRET is not set. For security reasons, a JWT secret must be provided '
                'via the jwt_secret argument or the CLOUD_JWT_SECRET environment variable in '
                'non-development environments.'
            )
        logger.warning(
            "CLOUD_JWT_SECRET is not set. Using a built-in insecure default intended only for "
            "local development. Do NOT use this configuration in production."
        )
        jwt_secret = 'change-me-in-production'

    storage_path = storage_path or os.environ.get('CLOUD_STORAGE_PATH', '')
    if not storage_path:
        logger.warning(
            "CLOUD_STORAGE_PATH is not set. Falling back to /tmp/cloud_storage — "
            "this is insecure in production; set the environment variable to a dedicated path."
        )
        storage_path = '/tmp/cloud_storage'

    database_url = database_url or os.environ.get('CLOUD_DB_URL', 'sqlite:///cloud_commands.db')
    engagement_db_url = engagement_db_url or os.environ.get(
        'CLOUD_ENGAGEMENT_DB_URL', 'sqlite:///cloud_engagement.db'
    )

    # 1. 初始化並註冊核心雲端服務（認證 + 檔案儲存）
    app.register_blueprint(cloud_bp)
    init_cloud_services(jwt_secret=jwt_secret, storage_path=storage_path)

    # 2. 初始化並註冊資料同步服務
    app.register_blueprint(data_sync_bp)
    init_data_sync_api(jwt_secret=jwt_secret, storage_path=storage_path)

    # 3. 初始化並註冊進階指令共享服務
    app.register_blueprint(shared_commands_bp)
    init_shared_commands_api(
        jwt_secret=jwt_secret,
        database_url=database_url,
        create_tables=True,
    )

    # 4. 初始化並註冊社群互動服務
    app.register_blueprint(engagement_bp)
    init_engagement_api(
        jwt_secret=jwt_secret,
        database_url=engagement_db_url,
        create_tables=True,
    )

    # 5. 初始化並註冊用戶管理服務
    app.register_blueprint(user_mgmt_bp)
    auth_service = CloudAuthService(jwt_secret)
    user_service = CloudUserService(auth_service)
    init_user_management(service=user_service, auth_service=auth_service)

    logger.info("Cloud application created with all services registered")
    return app


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )

    host = os.environ.get('CLOUD_HOST', '0.0.0.0')
    port = int(os.environ.get('CLOUD_PORT', '5100'))
    debug = os.environ.get('CLOUD_DEBUG', 'false').lower() == 'true'

    flask_app = create_app()
    flask_app.run(host=host, port=port, debug=debug)
