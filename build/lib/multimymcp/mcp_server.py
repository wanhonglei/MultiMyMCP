"""
MCP 服务器主程序

实现基于 stdio 的 MCP 服务器，处理 JSON-RPC 2.0 请求
"""

import sys
import json
import argparse
from typing import Dict, Any
from multimymcp import MultiMyMCP
from multimymcp.mcp_protocol import MCPProtocol
from multimymcp.mcp_tools import MCPTools
from multimymcp.mcp_config_loader import MCPConfigLoader


class MCPServer:
    """
    MCP 服务器
    
    处理 stdio 通信，实现 MCP 协议
    """
    
    def __init__(self, config_path: str = None):
        """
        初始化 MCP 服务器
        
        Args:
            config_path: 配置文件路径（可选）
        """
        loader = MCPConfigLoader()
        config = loader.load_config(config_path)
        
        self.mcp = MultiMyMCP()
        
        if "datasources" in config:
            for ds_name, ds_config in config["datasources"].items():
                from multimymcp import DataSourceConfig
                ds_config["name"] = ds_name
                ds = DataSourceConfig.from_dict(ds_config)
                self.mcp.add_data_source(ds)
        
        self.protocol = MCPProtocol()
        self.tools = MCPTools(self.mcp)
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理请求
        
        Args:
            request: JSON-RPC 请求
            
        Returns:
            Dict[str, Any]: JSON-RPC 响应
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        if method == "initialize":
            return self.protocol.handle_request(request)
        elif method == "tools/list":
            return self._handle_tools_list(request_id)
        elif method == "tools/call":
            return self._handle_tools_call(request_id, params)
        else:
            return self.protocol.create_error_response(
                request_id,
                -32601,
                f"Method not found: {method}"
            )
    
    def _handle_tools_list(self, request_id: Any) -> Dict[str, Any]:
        """
        处理 tools/list 请求
        
        Args:
            request_id: 请求 ID
            
        Returns:
            Dict[str, Any]: 工具列表响应
        """
        tools = self.tools.list_tools()
        
        result = {
            "tools": tools
        }
        
        return self.protocol.create_response(request_id, result=result)
    
    def _handle_tools_call(self, request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理 tools/call 请求
        
        Args:
            request_id: 请求 ID
            params: 请求参数
            
        Returns:
            Dict[str, Any]: 工具执行结果
        """
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            return self.protocol.create_error_response(
                request_id,
                -32602,
                "Missing tool name"
            )
        
        try:
            result = self.tools.execute_tool(tool_name, arguments)
            
            content = {
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False)
            }
            
            return self.protocol.create_response(
                request_id,
                result={"content": [content]}
            )
        except Exception as e:
            return self.protocol.create_error_response(
                request_id,
                -32603,
                f"Tool execution failed: {str(e)}"
            )
    
    def run(self):
        """
        运行 MCP 服务器
        
        从 stdin 读取请求，向 stdout 写入响应
        """
        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                response = self.handle_request(request)
                
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
            except json.JSONDecodeError as e:
                error_response = self.protocol.create_error_response(
                    None,
                    -32700,
                    f"Parse error: {str(e)}"
                )
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()
            except Exception as e:
                error_response = self.protocol.create_error_response(
                    None,
                    -32603,
                    f"Internal error: {str(e)}"
                )
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()


def main():
    """
    MCP 服务器入口函数
    """
    parser = argparse.ArgumentParser(description="MySQL MCP Server")
    parser.add_argument("--config", "-c", help="配置文件路径")
    
    args = parser.parse_args()
    
    server = MCPServer(config_path=args.config)
    server.run()


if __name__ == "__main__":
    main()
