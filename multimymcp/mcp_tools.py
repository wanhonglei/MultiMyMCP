"""
MCP 工具实现

实现 MCP 协议定义的工具，封装现有 MySQL 功能
"""

import json
from typing import Dict, Any, List
from multimymcp import MultiMyMCP


class MCPTools:
    """
    MCP 工具集合
    
    提供 4 个核心工具：
    - query_database: 查询数据库
    - list_datasources: 列出数据源
    - execute_sql: 执行 SQL
    - get_schema: 获取表结构
    """
    
    def __init__(self, mcp: MultiMyMCP):
        """
        初始化MCP工具
        
        Args:
            mcp: MultiMyMCP 实例
        """
        self.mcp = mcp
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        列出所有可用工具
        
        Returns:
            List[Dict[str, Any]]: 工具列表
        """
        return [
            {
                "name": "query_database",
                "description": "在指定的 MySQL 数据源上执行查询 SQL",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "datasource": {
                            "type": "string",
                            "description": "数据源名称"
                        },
                        "sql": {
                            "type": "string",
                            "description": "完整的 SELECT 查询语句"
                        }
                    },
                    "required": ["datasource", "sql"]
                }
            },
            {
                "name": "list_datasources",
                "description": "列出所有可用的 MySQL 数据源",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "execute_sql",
                "description": "执行 SQL 语句（INSERT/UPDATE/DELETE 等）",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "datasource": {
                            "type": "string",
                            "description": "数据源名称"
                        },
                        "sql": {
                            "type": "string",
                            "description": "完整的 SQL 语句"
                        }
                    },
                    "required": ["datasource", "sql"]
                }
            },
            {
                "name": "get_schema",
                "description": "获取指定数据源的表结构信息",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "datasource": {
                            "type": "string",
                            "description": "数据源名称"
                        },
                        "table": {
                            "type": "string",
                            "description": "表名（可选，不指定则返回所有表）"
                        }
                    },
                    "required": ["datasource"]
                }
            }
        ]
    
    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行指定工具
        
        Args:
            name: 工具名称
            arguments: 工具参数
            
        Returns:
            Dict[str, Any]: 执行结果
            
        Raises:
            ValueError: 工具不存在或参数无效
        """
        if name == "query_database":
            return self._query_database(arguments)
        elif name == "list_datasources":
            return self._list_datasources()
        elif name == "execute_sql":
            return self._execute_sql(arguments)
        elif name == "get_schema":
            return self._get_schema(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    def _query_database(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行数据库查询
        
        Args:
            arguments: 工具参数
            
        Returns:
            Dict[str, Any]: 查询结果
        """
        datasource = arguments.get("datasource")
        sql = arguments.get("sql")
        
        if not datasource or not sql:
            raise ValueError("Missing required parameters: datasource or sql")
        
        self.mcp.connect(datasource)
        
        result = self.mcp.execute(sql, datasource=datasource)
        
        return result
    
    def _list_datasources(self) -> Dict[str, Any]:
        """
        列出所有数据源
        
        Returns:
            Dict[str, Any]: 数据源列表
        """
        datasources = self.mcp.list_data_sources()
        
        return {
            "datasources": [
                {"name": ds} for ds in datasources
            ]
        }
    
    def _execute_sql(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 SQL 语句
        
        Args:
            arguments: 工具参数
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        datasource = arguments.get("datasource")
        sql = arguments.get("sql")
        
        if not datasource or not sql:
            raise ValueError("Missing required parameters: datasource or sql")
        
        self.mcp.connect(datasource)
        
        result = self.mcp.execute(sql, datasource=datasource)
        
        return result
    
    def _get_schema(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取表结构
        
        Args:
            arguments: 工具参数
            
        Returns:
            Dict[str, Any]: 表结构信息
        """
        datasource = arguments.get("datasource")
        table = arguments.get("table")
        
        if not datasource:
            raise ValueError("Missing required parameter: datasource")
        
        self.mcp.connect(datasource)
        
        if table:
            sql = f"DESCRIBE {table}"
        else:
            sql = "SHOW TABLES"
        
        result = self.mcp.execute(sql, datasource=datasource)
        
        return result
