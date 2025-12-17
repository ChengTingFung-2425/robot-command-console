"""
MCP 協定適配器

處理 MCP (Model Context Protocol) 協定的編碼/解碼
支援 JSON-RPC 2.0 格式
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MCPAdapter:
    """
    MCP 協定適配器
    
    處理 MCP 協定的編碼/解碼：
    - 請求格式化（JSON-RPC 2.0）
    - 回應解析
    - 錯誤處理
    """
    
    @staticmethod
    def encode_request(
        method: str,
        params: Dict[str, Any],
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        編碼 MCP 請求（JSON-RPC 2.0 格式）
        
        Args:
            method: 方法名稱
            params: 參數
            request_id: 請求 ID（若未指定則自動生成）
        
        Returns:
            JSON-RPC 2.0 請求物件
        """
        if request_id is None:
            request_id = f"req-{datetime.now().timestamp()}"
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
    
    @staticmethod
    def decode_response(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        解碼 MCP 回應（JSON-RPC 2.0 格式）
        
        Args:
            response: JSON-RPC 2.0 回應物件
        
        Returns:
            標準化結果
                {
                    "success": bool,
                    "result": Any,
                    "error": Optional[str]
                }
        """
        # 檢查是否為 JSON-RPC 2.0 格式
        if response.get("jsonrpc") != "2.0":
            logger.warning("回應不是 JSON-RPC 2.0 格式")
        
        # 檢查是否有錯誤
        if "error" in response:
            error = response["error"]
            return {
                "success": False,
                "result": None,
                "error": error.get("message", str(error))
            }
        
        # 成功回應
        return {
            "success": True,
            "result": response.get("result"),
            "error": None
        }
    
    @staticmethod
    def encode_error(
        code: int,
        message: str,
        data: Optional[Any] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        編碼錯誤回應（JSON-RPC 2.0 格式）
        
        Args:
            code: 錯誤代碼
            message: 錯誤訊息
            data: 額外資料
            request_id: 請求 ID
        
        Returns:
            JSON-RPC 2.0 錯誤回應
        """
        error_obj = {
            "code": code,
            "message": message
        }
        
        if data is not None:
            error_obj["data"] = data
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": error_obj
        }
    
    @staticmethod
    def encode_success(
        result: Any,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        編碼成功回應（JSON-RPC 2.0 格式）
        
        Args:
            result: 結果資料
            request_id: 請求 ID
        
        Returns:
            JSON-RPC 2.0 成功回應
        """
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
    
    @staticmethod
    def validate_request(request: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        驗證請求格式
        
        Args:
            request: 請求物件
        
        Returns:
            (是否有效, 錯誤訊息)
        """
        # 檢查 JSON-RPC 版本
        if request.get("jsonrpc") != "2.0":
            return False, "Missing or invalid 'jsonrpc' field (must be '2.0')"
        
        # 檢查方法名稱
        if "method" not in request:
            return False, "Missing 'method' field"
        
        if not isinstance(request.get("method"), str):
            return False, "'method' must be a string"
        
        # 檢查參數（可選）
        if "params" in request:
            params = request["params"]
            if not isinstance(params, (dict, list)):
                return False, "'params' must be an object or array"
        
        return True, None
    
    @staticmethod
    def validate_response(response: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        驗證回應格式
        
        Args:
            response: 回應物件
        
        Returns:
            (是否有效, 錯誤訊息)
        """
        # 檢查 JSON-RPC 版本
        if response.get("jsonrpc") != "2.0":
            return False, "Missing or invalid 'jsonrpc' field (must be '2.0')"
        
        # 必須包含 result 或 error（但不能同時包含）
        has_result = "result" in response
        has_error = "error" in response
        
        if not has_result and not has_error:
            return False, "Response must contain either 'result' or 'error'"
        
        if has_result and has_error:
            return False, "Response must not contain both 'result' and 'error'"
        
        # 如果有錯誤，檢查錯誤格式
        if has_error:
            error = response["error"]
            if not isinstance(error, dict):
                return False, "'error' must be an object"
            
            if "code" not in error or "message" not in error:
                return False, "Error must contain 'code' and 'message' fields"
        
        return True, None


# MCP 錯誤代碼常數
class MCPErrorCode:
    """JSON-RPC 2.0 標準錯誤代碼"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # 自訂錯誤代碼（-32000 到 -32099）
    SKILL_NOT_FOUND = -32001
    PROVIDER_NOT_FOUND = -32002
    PROVIDER_UNHEALTHY = -32003
    EXECUTION_TIMEOUT = -32004
    EXECUTION_FAILED = -32005
