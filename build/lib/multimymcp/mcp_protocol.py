"""
MCP 协议处理器

实现 JSON-RPC 2.0 协议的解析和响应构建
"""

import json
from typing import Dict, Any, Optional


class MCPProtocol:
    """
    MCP 协议处理器
    
    处理 JSON-RPC 2.0 请求和响应
    """
    
    def __init__(self):
        """初始化协议处理器"""
        self.jsonrpc_version = "2.0"
    
    def parse_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析 JSON-RPC 请求
        
        Args:
            request: JSON-RPC 请求字典
            
        Returns:
            Dict[str, Any]: 解析后的请求
            
        Raises:
            ValueError: 请求格式无效
        """
        if request.get("jsonrpc") != "2.0":
            raise ValueError("Invalid JSON-RPC version")
        
        if "method" not in request:
            raise ValueError("Missing method field")
        
        return request
    
    def create_response(
        self,
        request_id: Any,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        创建 JSON-RPC 响应
        
        Args:
            request_id: 请求 ID
            result: 结果数据
            error: 错误信息
            
        Returns:
            Dict[str, Any]: JSON-RPC 响应
        """
        response = {
            "jsonrpc": "2.0",
            "id": request_id
        }
        
        if error:
            response["error"] = error
        else:
            response["result"] = result
        
        return response
    
    def create_error_response(
        self,
        request_id: Any,
        code: int,
        message: str,
        data: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        创建错误响应
        
        Args:
            request_id: 请求 ID
            code: 错误代码
            message: 错误消息
            data: 错误数据
            
        Returns:
            Dict[str, Any]: 错误响应
        """
        error = {
            "code": code,
            "message": message
        }
        
        if data is not None:
            error["data"] = data
        
        return self.create_response(request_id, error=error)
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理 JSON-RPC 请求
        
        Args:
            request: JSON-RPC 请求
            
        Returns:
            Dict[str, Any]: JSON-RPC 响应
        """
        try:
            parsed = self.parse_request(request)
            method = parsed["method"]
            params = parsed.get("params", {})
            request_id = parsed.get("id")
            
            if method == "initialize":
                return self._handle_initialize(request_id, params)
            elif method == "tools/list":
                return self._handle_tools_list(request_id)
            elif method == "tools/call":
                return self._handle_tools_call(request_id, params)
            else:
                return self.create_error_response(
                    request_id,
                    -32601,
                    f"Method not found: {method}"
                )
        except ValueError as e:
            return self.create_error_response(
                request.get("id"),
                -32600,
                str(e)
            )
        except Exception as e:
            return self.create_error_response(
                request.get("id"),
                -32603,
                f"Internal error: {str(e)}"
            )
    
    def _handle_initialize(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理 initialize 请求
        
        Args:
            request_id: 请求 ID
            params: 请求参数
            
        Returns:
            Dict[str, Any]: 响应
        """
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "multimymcp",
                "version": "1.0.0"
            }
        }
        
        return self.create_response(request_id, result=result)
    
    def _handle_tools_list(self, request_id: Any) -> Dict[str, Any]:
        """
        处理 tools/list 请求（占位符，由 MCPServer 实现）
        
        Args:
            request_id: 请求 ID
            
        Returns:
            Dict[str, Any]: 响应
        """
        return self.create_error_response(
            request_id,
            -32601,
            "Method not implemented in protocol layer"
        )
    
    def _handle_tools_call(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理 tools/call 请求（占位符，由 MCPServer 实现）
        
        Args:
            request_id: 请求 ID
            params: 请求参数
            
        Returns:
            Dict[str, Any]: 响应
        """
        return self.create_error_response(
            request_id,
            -32601,
            "Method not implemented in protocol layer"
        )
