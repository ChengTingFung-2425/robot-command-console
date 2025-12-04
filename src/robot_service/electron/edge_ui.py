"""
Edge UI Routes
提供本地 WebUI 功能的 Flask 藍圖

Edge 功能包括：
- 機器人儀表板
- 指令控制中心
- LLM 設定管理
- 用戶設定
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from flask import (
    Blueprint,
    g,
    jsonify,
    render_template,
    request,
)

logger = logging.getLogger(__name__)

# 建立 Edge UI 藍圖
edge_ui = Blueprint(
    'edge_ui',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/edge/static'
)

# ============================================================
# 配置常數（可透過環境變數覆蓋）
# ============================================================

# LLM 提供商端點配置
OLLAMA_ENDPOINT = os.environ.get('OLLAMA_ENDPOINT', 'http://127.0.0.1:11434')
LMSTUDIO_ENDPOINT = os.environ.get('LMSTUDIO_ENDPOINT', 'http://127.0.0.1:1234')
MCP_API_URL = os.environ.get('MCP_API_URL', 'http://localhost:8000')

# 預設設定值
DEFAULT_SETTINGS: Dict[str, Any] = {
    'duration_unit': 's',
    'theme': 'light',
    'llm_provider': None,
    'llm_model': None,
}


# ============================================================
# 本地機器人管理（Edge 功能）
# TODO: 遷移到 SQLite 持久化存儲（Phase 3.3）
# 目前使用記憶體存儲用於 POC 驗證
# ============================================================

# 本地機器人資料存儲（簡化版）
_local_robots: Dict[str, Dict[str, Any]] = {}


def get_local_robots() -> List[Dict[str, Any]]:
    """取得本地機器人列表"""
    return list(_local_robots.values())


def get_local_robot(robot_id: str) -> Optional[Dict[str, Any]]:
    """取得單一機器人資料"""
    return _local_robots.get(robot_id)


def register_local_robot(robot_data: Dict[str, Any]) -> Dict[str, Any]:
    """註冊本地機器人"""
    robot_id = robot_data.get('id') or f"robot_{len(_local_robots) + 1}"
    robot = {
        'id': robot_id,
        'name': robot_data.get('name', f'Robot {robot_id}'),
        'type': robot_data.get('type', 'humanoid'),
        'status': 'idle',
        'battery': 100,
        'location': robot_data.get('location'),
        'capabilities': robot_data.get('capabilities', [
            'go_forward', 'back_fast', 'turn_left', 'turn_right',
            'stand', 'bow', 'wave'
        ]),
        'connected': False,
    }
    _local_robots[robot_id] = robot
    logger.info(f'Registered local robot: {robot_id}')
    return robot


def update_robot_status(robot_id: str, status: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """更新機器人狀態"""
    if robot_id not in _local_robots:
        return None
    _local_robots[robot_id].update(status)
    return _local_robots[robot_id]


# ============================================================
# Edge UI 頁面路由
# ============================================================

@edge_ui.route('/ui')
@edge_ui.route('/ui/')
def ui_home():
    """Edge UI 首頁 - 統一啟動器"""
    return render_template('edge/home.html')


@edge_ui.route('/ui/dashboard')
def ui_dashboard():
    """機器人儀表板頁面"""
    robots = get_local_robots()
    return render_template('edge/dashboard.html', robots=robots)


@edge_ui.route('/ui/command-center')
def ui_command_center():
    """指令控制中心頁面"""
    robots = get_local_robots()
    return render_template('edge/command_center.html', robots=robots)


@edge_ui.route('/ui/llm-settings')
def ui_llm_settings():
    """LLM 設定頁面"""
    return render_template('edge/llm_settings.html')


@edge_ui.route('/ui/settings')
def ui_settings():
    """用戶設定頁面"""
    return render_template('edge/settings.html')


# ============================================================
# Edge API 端點
# ============================================================

@edge_ui.route('/api/edge/robots', methods=['GET'])
def api_get_robots():
    """取得本地機器人列表"""
    robots = get_local_robots()
    return jsonify({
        'robots': robots,
        'count': len(robots),
        'request_id': getattr(g, 'request_id', None),
    })


@edge_ui.route('/api/edge/robots', methods=['POST'])
def api_register_robot():
    """註冊本地機器人"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing request body'}), 400

    robot = register_local_robot(data)
    return jsonify({
        'success': True,
        'robot': robot,
        'request_id': getattr(g, 'request_id', None),
    }), 201


@edge_ui.route('/api/edge/robots/<robot_id>', methods=['GET'])
def api_get_robot(robot_id: str):
    """取得單一機器人資料"""
    robot = get_local_robot(robot_id)
    if not robot:
        return jsonify({'error': 'Robot not found'}), 404
    return jsonify({
        'robot': robot,
        'request_id': getattr(g, 'request_id', None),
    })


@edge_ui.route('/api/edge/robots/<robot_id>/status', methods=['PUT'])
def api_update_robot_status(robot_id: str):
    """更新機器人狀態"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing request body'}), 400

    robot = update_robot_status(robot_id, data)
    if not robot:
        return jsonify({'error': 'Robot not found'}), 404

    return jsonify({
        'success': True,
        'robot': robot,
        'request_id': getattr(g, 'request_id', None),
    })


@edge_ui.route('/api/edge/robots/<robot_id>/capabilities', methods=['GET'])
def api_get_robot_capabilities(robot_id: str):
    """取得機器人能力清單"""
    robot = get_local_robot(robot_id)
    if not robot:
        return jsonify({'error': 'Robot not found'}), 404

    return jsonify({
        'robot_id': robot_id,
        'capabilities': robot.get('capabilities', []),
        'request_id': getattr(g, 'request_id', None),
    })


# ============================================================
# LLM 狀態代理 API（轉發到 MCP）
# ============================================================

@edge_ui.route('/api/edge/llm/status', methods=['GET'])
def api_llm_status():
    """取得 LLM 連線狀態（代理到 MCP 或本地檢測）"""
    # 嘗試檢測本地 LLM 提供商
    local_providers = detect_local_llm_providers()

    return jsonify({
        'internet_available': check_internet_connection(),
        'local_llm_available': len(local_providers) > 0,
        'local_llm_providers': local_providers,
        'mcp_available': check_mcp_connection(),
        'request_id': getattr(g, 'request_id', None),
    })


@edge_ui.route('/api/edge/llm/providers', methods=['GET'])
def api_llm_providers():
    """取得可用的 LLM 提供商列表"""
    providers = detect_local_llm_providers()
    return jsonify({
        'providers': providers,
        'count': len(providers),
        'request_id': getattr(g, 'request_id', None),
    })


def detect_local_llm_providers() -> List[Dict[str, Any]]:
    """偵測本地 LLM 提供商
    
    使用環境變數配置的端點進行檢測：
    - OLLAMA_ENDPOINT: Ollama 服務端點
    - LMSTUDIO_ENDPOINT: LM Studio 服務端點
    """
    import urllib.request
    providers = []

    # 檢測 Ollama
    try:
        ollama_url = f'{OLLAMA_ENDPOINT}/api/tags'
        req = urllib.request.Request(ollama_url, method='GET')
        req.add_header('Accept', 'application/json')
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            models = data.get('models', [])
            providers.append({
                'name': 'ollama',
                'display_name': 'Ollama',
                'status': 'available',
                'endpoint': OLLAMA_ENDPOINT,
                'models': [m.get('name') for m in models],
            })
    except Exception as e:
        logger.debug(f'Failed to detect Ollama at {OLLAMA_ENDPOINT}: {e}')

    # 檢測 LM Studio
    try:
        lmstudio_url = f'{LMSTUDIO_ENDPOINT}/v1/models'
        req = urllib.request.Request(lmstudio_url, method='GET')
        req.add_header('Accept', 'application/json')
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            models = data.get('data', [])
            providers.append({
                'name': 'lmstudio',
                'display_name': 'LM Studio',
                'status': 'available',
                'endpoint': LMSTUDIO_ENDPOINT,
                'models': [m.get('id') for m in models],
            })
    except Exception as e:
        logger.debug(f'Failed to detect LM Studio at {LMSTUDIO_ENDPOINT}: {e}')

    return providers


def check_internet_connection() -> bool:
    """檢查網路連線（嘗試多個端點）"""
    check_urls = [
        'https://www.google.com',
        'https://www.cloudflare.com',
        'https://1.1.1.1'
    ]
    import urllib.request
    for url in check_urls:
        try:
            urllib.request.urlopen(url, timeout=3)
            return True
        except Exception:
            continue
    return False


def check_mcp_connection() -> bool:
    """檢查 MCP 服務連線"""
    try:
        import urllib.request
        urllib.request.urlopen(f'{MCP_API_URL}/health', timeout=2)
        return True
    except Exception:
        return False


# ============================================================
# 用戶設定 API（本地存儲）
# TODO: 遷移到持久化存儲（Phase 3.3）
# ============================================================

# 用戶設定（記憶體存儲，重啟後會重設）
_user_settings: Dict[str, Any] = DEFAULT_SETTINGS.copy()


@edge_ui.route('/api/edge/settings', methods=['GET'])
def api_get_settings():
    """取得用戶設定"""
    return jsonify({
        'settings': _user_settings,
        'request_id': getattr(g, 'request_id', None),
    })


@edge_ui.route('/api/edge/settings/defaults', methods=['GET'])
def api_get_settings_defaults():
    """取得預設設定值"""
    return jsonify({
        'settings': DEFAULT_SETTINGS,
        'request_id': getattr(g, 'request_id', None),
    })


@edge_ui.route('/api/edge/settings', methods=['PUT'])
def api_update_settings():
    """更新用戶設定"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing request body'}), 400

    # 更新設定
    for key in ['duration_unit', 'theme', 'llm_provider', 'llm_model']:
        if key in data:
            _user_settings[key] = data[key]

    return jsonify({
        'success': True,
        'settings': _user_settings,
        'request_id': getattr(g, 'request_id', None),
    })
