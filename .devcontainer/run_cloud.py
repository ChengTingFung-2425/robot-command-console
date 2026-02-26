#!/usr/bin/env python3
"""
Cloud API startup script for Codespace / devcontainer.

啟動 Cloud API 服務（port 8888），包含：
- Cloud 儲存 API（/api/cloud/）
- 共用指令 API（/api/cloud/shared_commands/）

使用方式：
    PYTHONPATH=/workspace/src:/workspace/Edge python .devcontainer/run_cloud.py
"""
import os
import sys

# 確保 /workspace 系列路徑在 sys.path 中（必須在其他 import 之前）
_ws = os.environ.get('GITHUB_WORKSPACE') or '/workspace'
for _p in (_ws, os.path.join(_ws, 'src'), os.path.join(_ws, 'Edge')):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from flask import Flask  # noqa: E402
from Cloud.api.routes import cloud_bp, init_cloud_services  # noqa: E402
from Cloud.shared_commands.api import (  # noqa: E402
    bp as shared_commands_bp,
    init_shared_commands_api,
)

DATABASE_URL = os.environ.get(
    'CLOUD_DATABASE_URL',
    'sqlite:////tmp/cloud_commands.db'
)
JWT_SECRET = os.environ.get('CLOUD_JWT_SECRET', 'dev-jwt-secret-change-in-production')
STORAGE_PATH = os.environ.get('CLOUD_STORAGE_PATH', '/tmp/cloud-storage')
PORT = int(os.environ.get('CLOUD_PORT', '8888'))
DEBUG = os.environ.get('CLOUD_DEBUG', 'false').lower() == 'true'

app = Flask('cloud')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
app.register_blueprint(cloud_bp)
app.register_blueprint(shared_commands_bp)

with app.app_context():
    init_cloud_services(JWT_SECRET, STORAGE_PATH)
    init_shared_commands_api(JWT_SECRET, DATABASE_URL, create_tables=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG, use_reloader=False)
