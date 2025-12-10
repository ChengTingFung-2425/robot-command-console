"""
指令歷史 API 端點

提供 HTTP API 介面以查詢指令歷史與快取統計。
設計為可整合到 Flask 或 FastAPI 應用中。
"""

import logging
from datetime import datetime
from typing import Optional

from flask import Blueprint, jsonify, request

from .command_history_manager import CommandHistoryManager
from src.common.datetime_utils import parse_iso_datetime


logger = logging.getLogger(__name__)


def create_history_api_blueprint(
    history_manager: CommandHistoryManager,
    url_prefix: str = '/api/commands'
) -> Blueprint:
    """建立指令歷史 API Blueprint
    
    Args:
        history_manager: CommandHistoryManager 實例
        url_prefix: URL 前綴
        
    Returns:
        Flask Blueprint
    """
    bp = Blueprint('command_history_api', __name__, url_prefix=url_prefix)
    
    @bp.route('/history', methods=['GET'])
    def get_command_history():
        """取得指令歷史
        
        Query Parameters:
            robot_id: 機器人 ID（可選）
            status: 狀態篩選（可選）
            actor_type: 執行者類型篩選（可選）
            source: 來源篩選（可選）
            start_time: 開始時間 ISO 格式（可選）
            end_time: 結束時間 ISO 格式（可選）
            limit: 返回記錄數上限，預設 100
            offset: 查詢偏移量，預設 0
        
        Returns:
            JSON 格式的指令歷史列表
        """
        try:
            # 解析查詢參數
            robot_id = request.args.get('robot_id')
            status = request.args.get('status')
            actor_type = request.args.get('actor_type')
            source = request.args.get('source')
            limit = request.args.get('limit', 100, type=int)
            offset = request.args.get('offset', 0, type=int)
            
            # 解析時間範圍
            start_time: Optional[datetime] = None
            end_time: Optional[datetime] = None
            
            if request.args.get('start_time'):
                start_time = parse_iso_datetime(request.args.get('start_time'))
            
            if request.args.get('end_time'):
                end_time = parse_iso_datetime(request.args.get('end_time'))
            
            # 查詢歷史記錄
            records = history_manager.get_command_history(
                robot_id=robot_id,
                status=status,
                actor_type=actor_type,
                source=source,
                start_time=start_time,
                end_time=end_time,
                limit=min(limit, 1000),  # 限制最大值
                offset=max(offset, 0)
            )
            
            # 統計總數
            total = history_manager.count_commands(
                robot_id=robot_id,
                status=status,
                start_time=start_time,
                end_time=end_time
            )
            
            return jsonify({
                'status': 'success',
                'data': {
                    'records': [r.to_dict() for r in records],
                    'pagination': {
                        'total': total,
                        'limit': limit,
                        'offset': offset,
                        'has_more': (offset + len(records)) < total
                    }
                }
            })
        
        except Exception as e:
            logger.error(f"Error getting command history: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 'QUERY_ERROR',
                    'message': 'An internal error has occurred.'
                }
            }), 500
    
    @bp.route('/history/<command_id>', methods=['GET'])
    def get_command_by_id(command_id: str):
        """取得特定指令的詳細資訊
        
        Args:
            command_id: 指令 ID
        
        Returns:
            JSON 格式的指令記錄
        """
        try:
            # 直接從資料庫取得
            store = history_manager.history_store
            record = store.get_record(command_id)
            
            if record is None:
                return jsonify({
                    'status': 'error',
                    'error': {
                        'code': 'NOT_FOUND',
                        'message': f'Command not found: {command_id}'
                    }
                }), 404
            
            return jsonify({
                'status': 'success',
                'data': record.to_dict()
            })
        
        except Exception as e:
            logger.error(f"Error getting command: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 'QUERY_ERROR',
                    'message': 'An internal error has occurred.'
                }
            }), 500
    
    @bp.route('/cache/stats', methods=['GET'])
    def get_cache_stats():
        """取得快取統計資訊
        
        Returns:
            JSON 格式的快取統計
        """
        try:
            stats = history_manager.get_cache_stats()
            
            return jsonify({
                'status': 'success',
                'data': stats
            })
        
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 'STATS_ERROR',
                    'message': 'An internal error has occurred.'
                }
            }), 500
    
    @bp.route('/cache', methods=['DELETE'])
    def clear_cache():
        """清空快取
        
        Returns:
            操作結果
        """
        try:
            history_manager.clear_cache()
            
            return jsonify({
                'status': 'success',
                'message': 'Cache cleared successfully'
            })
        
        except Exception as e:
            logger.error(f"Error clearing cache: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 'CLEAR_ERROR',
                    'message': str(e)
                }
            }), 500
    
    @bp.route('/cache/cleanup', methods=['POST'])
    def cleanup_expired_cache():
        """清理過期快取
        
        Returns:
            清理結果
        """
        try:
            count = history_manager.cleanup_expired_cache()
            
            return jsonify({
                'status': 'success',
                'data': {
                    'cleaned_count': count
                }
            })
        
        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 'CLEANUP_ERROR',
                    'message': str(e)
                }
            }), 500
    
    @bp.route('/history/cleanup', methods=['POST'])
    def cleanup_old_history():
        """清理舊歷史記錄
        
        Request Body (JSON):
            hours: 清理超過此小時數的記錄（可選）
        
        Returns:
            清理結果
        """
        try:
            data = request.get_json() or {}
            hours = data.get('hours')
            
            count = history_manager.cleanup_old_history(hours=hours)
            
            return jsonify({
                'status': 'success',
                'data': {
                    'cleaned_count': count
                }
            })
        
        except Exception as e:
            logger.error(f"Error cleaning up history: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 'CLEANUP_ERROR',
                    'message': str(e)
                }
            }), 500
    
    @bp.route('/stats', methods=['GET'])
    def get_statistics():
        """取得整體統計資訊
        
        Returns:
            統計資訊
        """
        try:
            # 整體統計
            total_commands = history_manager.count_commands()
            
            # 按狀態統計
            status_stats = {}
            for status in ['pending', 'running', 'succeeded', 'failed', 'cancelled']:
                count = history_manager.count_commands(status=status)
                status_stats[status] = count
            
            # 快取統計
            cache_stats = history_manager.get_cache_stats()
            
            return jsonify({
                'status': 'success',
                'data': {
                    'total_commands': total_commands,
                    'status_distribution': status_stats,
                    'cache': cache_stats
                }
            })
        
        except Exception as e:
            logger.error(f"Error getting statistics: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 'STATS_ERROR',
                    'message': str(e)
                }
            }), 500
    
    return bp
