"""
Backend API Client
提供與 Flask backend 通訊的客戶端類別
"""
import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class BackendAPIClient:
    """Flask Backend API 客戶端"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """
        初始化 API 客戶端
        
        Args:
            base_url: Flask backend 的基礎 URL
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'QtWebView-EdgeApp/1.0'
        })
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        發送 HTTP 請求的通用方法
        
        Args:
            method: HTTP 方法 (GET, POST, PUT, DELETE)
            endpoint: API 端點
            **kwargs: requests 的其他參數
            
        Returns:
            API 回應的 JSON 數據
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=10, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {method} {url} - {e}")
            return {"error": str(e), "success": False}
    
    # ==================== Health Check ====================
    
    def check_health(self) -> Dict[str, Any]:
        """檢查後端服務健康狀態"""
        return self._make_request('GET', '/api/health')
    
    # ==================== Dashboard APIs ====================
    
    def get_system_status(self) -> Dict[str, Any]:
        """獲取系統狀態"""
        return self._make_request('GET', '/api/system/status')
    
    def get_robot_stats(self) -> Dict[str, Any]:
        """獲取機器人統計資訊"""
        return self._make_request('GET', '/api/robots/stats')
    
    def get_command_stats(self) -> Dict[str, Any]:
        """獲取指令統計資訊"""
        return self._make_request('GET', '/api/commands/stats')
    
    def get_recent_activity(self, limit: int = 10) -> List[Dict[str, Any]]:
        """獲取最近活動"""
        result = self._make_request('GET', f'/api/activity/recent?limit={limit}')
        return result.get('activities', []) if isinstance(result, dict) else []
    
    # ==================== Robot Control APIs ====================
    
    def list_robots(self) -> List[Dict[str, Any]]:
        """列出所有機器人"""
        result = self._make_request('GET', '/api/robots')
        return result.get('robots', []) if isinstance(result, dict) else []
    
    def get_robot_info(self, robot_id: str) -> Dict[str, Any]:
        """獲取機器人詳細資訊"""
        return self._make_request('GET', f'/api/robots/{robot_id}')
    
    def send_command(self, robot_id: str, command: str) -> Dict[str, Any]:
        """
        發送指令到機器人
        
        Args:
            robot_id: 機器人 ID
            command: 要執行的指令
            
        Returns:
            指令執行結果
        """
        return self._make_request('POST', f'/api/robots/{robot_id}/command', 
                                 json={'command': command})
    
    def get_robot_status(self, robot_id: str) -> Dict[str, Any]:
        """獲取機器人即時狀態"""
        return self._make_request('GET', f'/api/robots/{robot_id}/status')
    
    # ==================== Command History APIs ====================
    
    def get_command_history(self, limit: int = 100, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        獲取指令歷史記錄
        
        Args:
            limit: 返回記錄數量上限
            status: 篩選狀態 (success, failed, running, None=all)
            
        Returns:
            指令歷史記錄列表
        """
        params = {'limit': limit}
        if status:
            params['status'] = status
        result = self._make_request('GET', '/api/commands/history', params=params)
        return result.get('commands', []) if isinstance(result, dict) else []
    
    def get_command_details(self, command_id: str) -> Dict[str, Any]:
        """獲取指令詳細資訊"""
        return self._make_request('GET', f'/api/commands/{command_id}')
    
    # ==================== Firmware Update APIs ====================
    
    def upload_firmware(self, robot_id: str, firmware_path: str, 
                       progress_callback=None) -> Dict[str, Any]:
        """
        上傳固件到機器人
        
        Args:
            robot_id: 機器人 ID
            firmware_path: 固件檔案路徑
            progress_callback: 進度回調函式 (optional)
            
        Returns:
            上傳結果
        """
        try:
            with open(firmware_path, 'rb') as f:
                files = {'firmware': f}
                # Note: 如果需要進度追蹤，需要使用 requests-toolbelt
                response = self.session.post(
                    f"{self.base_url}/firmware/upload/{robot_id}",
                    files=files,
                    timeout=300  # 5 分鐘超時
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Firmware upload failed: {e}")
            return {"error": str(e), "success": False}
    
    def verify_firmware(self, robot_id: str, checksum: str) -> Dict[str, Any]:
        """驗證固件 checksum"""
        return self._make_request('POST', f'/firmware/verify/{robot_id}',
                                 json={'checksum': checksum})
    
    def install_firmware(self, robot_id: str) -> Dict[str, Any]:
        """執行固件安裝"""
        return self._make_request('POST', f'/firmware/install/{robot_id}')
    
    # ==================== Queue Channel APIs ====================
    
    def send_message(self, channel: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """發送訊息到佇列通道"""
        return self._make_request('POST', '/api/queue/channel',
                                 json={'channel': channel, 'message': message})
    
    def consume_messages(self, channel: str, limit: int = 10) -> List[Dict[str, Any]]:
        """從佇列通道消費訊息"""
        result = self._make_request('GET', f'/api/queue/channel?channel={channel}&limit={limit}')
        return result.get('messages', []) if isinstance(result, dict) else []
    
    # ==================== Download APIs ====================
    
    def download_file(self, filename: str, save_path: str) -> bool:
        """
        下載檔案
        
        Args:
            filename: 要下載的檔案名稱
            save_path: 儲存路徑
            
        Returns:
            是否成功下載
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/download/{filename}",
                stream=True,
                timeout=60
            )
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            logger.error(f"File download failed: {e}")
            return False
