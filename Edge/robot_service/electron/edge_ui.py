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
import time
from datetime import datetime, timezone
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

# 雲端同步狀態快取（避免頻繁檢查造成阻塞）
_sync_status_cache: Dict[str, Any] = {
    'data': None,
    'timestamp': 0,
    'cache_duration': 5,  # 快取 5 秒
}


# ============================================================
# 本地機器人管理（Edge 功能）
# TODO: 遷移到 SQLite 持久化存儲（Phase 3.3）
# 目前使用記憶體存儲用於 POC 驗證
#
# ⚠️ 並發安全說明：
# 以下全域變數（_local_robots、_robot_health_history、_robot_id_counter）
# 未使用執行緒鎖保護，僅適用於單執行緒開發環境。
# 在生產環境使用 WSGI 伺服器時，應遷移到 SQLite 或使用適當的同步機制。
# ============================================================

# 配置常數
MAX_HEALTH_HISTORY_SIZE = 20  # 每個機器人保留的最大健康歷史記錄數

# 本地機器人資料存儲（簡化版，單執行緒環境專用）
_local_robots: Dict[str, Dict[str, Any]] = {}

# 機器人健康檢查記錄（單執行緒環境專用）
_robot_health_history: Dict[str, List[Dict[str, Any]]] = {}

# 機器人 ID 計數器（避免刪除後的 ID 衝突，單執行緒環境專用）
_robot_id_counter: int = 0

# 機器人類型定義（用於圖示和能力）
ROBOT_TYPES: Dict[str, Dict[str, Any]] = {
    'humanoid': {
        'display_name': '人形機器人',
        'icon': '🤖',
        'default_capabilities': [
            'go_forward', 'back_fast', 'turn_left', 'turn_right',
            'stand', 'bow', 'wave', 'squat', 'dance_two'
        ],
    },
    'agv': {
        'display_name': 'AGV 搬運車',
        'icon': '🚗',
        'default_capabilities': [
            'go_forward', 'back_fast', 'turn_left', 'turn_right',
            'stop', 'pause', 'resume'
        ],
    },
    'arm': {
        'display_name': '機械手臂',
        'icon': '🦾',
        'default_capabilities': [
            'grab', 'release', 'rotate', 'extend', 'retract'
        ],
    },
    'drone': {
        'display_name': '無人機',
        'icon': '🚁',
        'default_capabilities': [
            'takeoff', 'land', 'hover', 'fly_forward', 'fly_back'
        ],
    },
    'other': {
        'display_name': '其他',
        'icon': '⚙️',
        'default_capabilities': ['stop'],
    },
}


def get_local_robots() -> List[Dict[str, Any]]:
    """取得本地機器人列表"""
    return list(_local_robots.values())


def get_local_robot(robot_id: str) -> Optional[Dict[str, Any]]:
    """取得單一機器人資料"""
    return _local_robots.get(robot_id)


def register_local_robot(robot_data: Dict[str, Any]) -> Dict[str, Any]:
    """註冊本地機器人"""
    global _robot_id_counter

    # 使用計數器生成唯一 ID，避免刪除後的 ID 衝突
    if robot_data.get('id'):
        robot_id = robot_data['id']
    else:
        _robot_id_counter += 1
        robot_id = f"robot_{_robot_id_counter}"

    robot_type = robot_data.get('type', 'humanoid')
    type_info = ROBOT_TYPES.get(robot_type, ROBOT_TYPES['other'])

    now = datetime.now(timezone.utc).isoformat()
    robot = {
        'id': robot_id,
        'name': robot_data.get('name', f'Robot {robot_id}'),
        'type': robot_type,
        'type_display': type_info['display_name'],
        'icon': type_info['icon'],
        'status': 'idle',
        'battery': 100,
        'location': robot_data.get('location'),
        'capabilities': robot_data.get('capabilities', type_info['default_capabilities']),
        'connected': False,
        'last_seen': None,
        'health_status': 'unknown',
        'error_count': 0,
        'command_count': 0,
        'created_at': now,
        'updated_at': now,
    }
    _local_robots[robot_id] = robot
    _robot_health_history[robot_id] = []
    logger.info(f'Registered local robot: {robot_id}')
    return robot


def update_robot_status(robot_id: str, status: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """更新機器人狀態"""
    if robot_id not in _local_robots:
        return None

    # 更新時間戳
    status['updated_at'] = datetime.now(timezone.utc).isoformat()

    # 如果連線狀態變更，記錄 last_seen
    if status.get('connected'):
        status['last_seen'] = status['updated_at']

    _local_robots[robot_id].update(status)
    return _local_robots[robot_id]


def delete_local_robot(robot_id: str) -> bool:
    """刪除本地機器人"""
    if robot_id not in _local_robots:
        return False
    del _local_robots[robot_id]
    if robot_id in _robot_health_history:
        del _robot_health_history[robot_id]
    logger.info(f'Deleted local robot: {robot_id}')
    return True


def perform_robot_health_check(robot_id: str) -> Dict[str, Any]:
    """執行機器人健康檢查"""
    robot = _local_robots.get(robot_id)
    if not robot:
        return {'status': 'not_found', 'robot_id': robot_id}

    now = datetime.now(timezone.utc).isoformat()

    # 執行各項健康檢查
    checks = {
        'connectivity': robot.get('connected', False),
        'battery_ok': robot.get('battery', 0) > 20,
        'no_errors': robot.get('error_count', 0) == 0,
    }

    # 根據所有檢查結果決定健康狀態
    if not checks['connectivity']:
        health_status = 'disconnected'
    elif all(checks.values()):
        health_status = 'healthy'
    else:
        health_status = 'warning'

    # 模擬健康檢查結果（在實際環境中會連接機器人）
    health_result = {
        'timestamp': now,
        'robot_id': robot_id,
        'connected': robot.get('connected', False),
        'battery': robot.get('battery', 0),
        'status': health_status,
        'response_time_ms': 50 if robot.get('connected') else None,
        'checks': checks,
    }

    # 更新機器人健康狀態
    _local_robots[robot_id]['health_status'] = health_status

    # 記錄健康檢查歷史
    if robot_id not in _robot_health_history:
        _robot_health_history[robot_id] = []
    _robot_health_history[robot_id].append(health_result)
    # 使用常數限制歷史記錄大小
    _robot_health_history[robot_id] = _robot_health_history[robot_id][-MAX_HEALTH_HISTORY_SIZE:]

    return health_result


def get_robot_health_history(robot_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """取得機器人健康檢查歷史"""
    history = _robot_health_history.get(robot_id, [])
    return history[-limit:] if limit else history


def get_dashboard_summary() -> Dict[str, Any]:
    """取得儀表板摘要資料"""
    robots = list(_local_robots.values())
    total = len(robots)
    connected = sum(1 for r in robots if r.get('connected'))
    healthy = sum(1 for r in robots if r.get('health_status') == 'healthy')
    warning = sum(1 for r in robots if r.get('health_status') == 'warning')
    low_battery = sum(1 for r in robots if (r.get('battery') or 100) < 20)

    # 計算需要關注的機器人（避免重複計數）
    # 一個機器人如果是 warning 或 low_battery，只計算一次
    needs_attention = sum(
        1 for r in robots
        if r.get('health_status') == 'warning' or (r.get('battery') or 100) < 20
    )

    return {
        'total_robots': total,
        'connected': connected,
        'disconnected': total - connected,
        'healthy': healthy,
        'warning': warning,
        'low_battery': low_battery,
        'needs_attention': needs_attention,
        'by_type': _count_by_type(robots),
        'by_status': _count_by_status(robots),
    }


def _count_by_type(robots: List[Dict[str, Any]]) -> Dict[str, int]:
    """按類型統計機器人數量"""
    counts: Dict[str, int] = {}
    for robot in robots:
        robot_type = robot.get('type', 'other')
        counts[robot_type] = counts.get(robot_type, 0) + 1
    return counts


def _count_by_status(robots: List[Dict[str, Any]]) -> Dict[str, int]:
    """按狀態統計機器人數量"""
    counts: Dict[str, int] = {}
    for robot in robots:
        status = robot.get('status', 'unknown')
        counts[status] = counts.get(status, 0) + 1
    return counts


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


@edge_ui.route('/api/edge/robots/<robot_id>', methods=['DELETE'])
def api_delete_robot(robot_id: str):
    """刪除機器人"""
    success = delete_local_robot(robot_id)
    if not success:
        return jsonify({'error': 'Robot not found'}), 404

    return jsonify({
        'success': True,
        'message': f'Robot {robot_id} deleted',
        'request_id': getattr(g, 'request_id', None),
    })


@edge_ui.route('/api/edge/robots/<robot_id>/health', methods=['GET'])
def api_robot_health_check(robot_id: str):
    """執行機器人健康檢查"""
    robot = get_local_robot(robot_id)
    if not robot:
        return jsonify({'error': 'Robot not found'}), 404

    health_result = perform_robot_health_check(robot_id)
    return jsonify({
        'health': health_result,
        'request_id': getattr(g, 'request_id', None),
    })


@edge_ui.route('/api/edge/robots/<robot_id>/health/history', methods=['GET'])
def api_robot_health_history(robot_id: str):
    """取得機器人健康檢查歷史"""
    robot = get_local_robot(robot_id)
    if not robot:
        return jsonify({'error': 'Robot not found'}), 404

    limit = request.args.get('limit', 10, type=int)
    # 驗證 limit 範圍
    if limit < 0:
        return jsonify({'error': 'Limit must be non-negative'}), 400
    if limit > MAX_HEALTH_HISTORY_SIZE:
        limit = MAX_HEALTH_HISTORY_SIZE

    history = get_robot_health_history(robot_id, limit)
    return jsonify({
        'robot_id': robot_id,
        'history': history,
        'count': len(history),
        'request_id': getattr(g, 'request_id', None),
    })


@edge_ui.route('/api/edge/dashboard/summary', methods=['GET'])
def api_dashboard_summary():
    """取得儀表板摘要資料"""
    summary = get_dashboard_summary()
    return jsonify({
        'summary': summary,
        'request_id': getattr(g, 'request_id', None),
    })


@edge_ui.route('/api/edge/robot-types', methods=['GET'])
def api_robot_types():
    """取得支援的機器人類型列表"""
    types_list = [
        {'id': key, **value}
        for key, value in ROBOT_TYPES.items()
    ]
    return jsonify({
        'types': types_list,
        'count': len(types_list),
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


# ============================================================
# 雲端同步狀態 API
# ============================================================

@edge_ui.route('/api/edge/sync/status', methods=['GET'])
def api_sync_status():
    """
    取得雲端同步狀態

    返回 JSON 結構：
    - network: 網路連線狀態（online/offline）
    - services.mcp: MCP 服務狀態（available/unavailable）
    - services.queue: 佇列服務狀態（available/unavailable）
    - buffers.command: 指令緩衝區統計（pending, failed, total_buffered, total_sent）
    - buffers.sync: 雲端同步緩衝區統計（pending, failed, total_buffered, total_sent）
    - sync_enabled: 是否啟用雲端同步
    - last_checked: 最後一次檢查時間（ISO 8601，UTC）
    - request_id: 請求追蹤 ID（如有）

    注意：目前為基礎實作，僅檢查網路與 MCP 連線狀態。
    buffers 統計目前固定回傳 0，未來將整合 OfflineQueueService 提供完整統計。
    使用 5 秒快取避免頻繁檢查造成阻塞。
    """
    # 檢查快取是否有效
    current_time = time.time()
    if (_sync_status_cache['data'] is not None and
        current_time - _sync_status_cache['timestamp'] < _sync_status_cache['cache_duration']):
        # 使用快取資料，但更新 request_id
        cached_data = _sync_status_cache['data'].copy()
        cached_data['request_id'] = getattr(g, 'request_id', None)
        return jsonify(cached_data)

    # 檢查網路連線
    network_online = check_internet_connection()

    # 檢查 MCP 服務連線
    mcp_available = check_mcp_connection()

    # 基礎狀態（未來可從 OfflineQueueService 獲取真實資料）
    status_data = {
        'network': {
            'online': network_online,
            'status': 'online' if network_online else 'offline',
        },
        'services': {
            'mcp': {
                'available': mcp_available,
                'status': 'available' if mcp_available else 'unavailable',
            },
            'queue': {
                'available': network_online and mcp_available,
                'status': 'available' if (network_online and mcp_available) else 'unavailable',
            },
        },
        'buffers': {
            'command': {
                'pending': 0,
                'failed': 0,
                'total_buffered': 0,
                'total_sent': 0,
            },
            'sync': {
                'pending': 0,
                'failed': 0,
                'total_buffered': 0,
                'total_sent': 0,
            },
        },
        'sync_enabled': True,
        'last_checked': datetime.now(timezone.utc).isoformat(),
        'request_id': getattr(g, 'request_id', None),
    }

    # 更新快取
    _sync_status_cache['data'] = {k: v for k, v in status_data.items() if k != 'request_id'}
    _sync_status_cache['timestamp'] = current_time

    return jsonify(status_data)
