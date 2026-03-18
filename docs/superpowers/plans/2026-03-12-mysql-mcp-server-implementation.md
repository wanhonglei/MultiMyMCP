# MySQL MCP Server 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 TRAE SOLO IDE 实现一个标准 MCP 协议的 MySQL 多数据源管理服务器

**Architecture:** 基于 stdio 的 MCP 服务器，实现 JSON-RPC 2.0 协议，复用现有 MySQL 连接池和执行器代码，提供 4 个核心工具：query_database、list_datasources、execute_sql、get_schema

**Tech Stack:** Python 3.8+, JSON-RPC 2.0, stdio 通信, 现有 MySQL 连接池

---

## 文件结构

**新增文件：**
- `trae_mysql_mcp/mcp_protocol.py` - MCP 协议处理器，JSON-RPC 2.0 解析和响应构建
- `trae_mysql_mcp/mcp_tools.py` - MCP 工具实现，封装现有功能为 MCP 工具
- `trae_mysql_mcp/mcp_config_loader.py` - 全局配置加载器，支持多优先级配置加载
- `trae_mysql_mcp/mcp_server.py` - MCP 服务器主程序，处理 stdio 通信
- `tests/test_mcp_protocol.py` - MCP 协议测试
- `tests/test_mcp_tools.py` - MCP 工具测试
- `tests/test_mcp_config_loader.py` - 配置加载器测试

**修改文件：**
- `setup.py` - 添加 MCP 服务器入口点
- `README.md` - 更新文档，添加 MCP 使用说明

---

## Chunk 1: MCP 协议处理器

### Task 1: 实现 MCP 协议基础类

**Files:**
- Create: `trae_mysql_mcp/mcp_protocol.py`
- Test: `tests/test_mcp_protocol.py`

- [ ] **Step 1: Write the failing test for JSON-RPC request parsing**

```python
"""
MCP 协议处理器测试
"""

import pytest
from trae_mysql_mcp.mcp_protocol import MCPProtocol


def test_parse_valid_jsonrpc_request():
    """测试解析有效的 JSON-RPC 请求"""
    protocol = MCPProtocol()
    
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        }
    }
    
    parsed = protocol.parse_request(request)
    
    assert parsed["jsonrpc"] == "2.0"
    assert parsed["id"] == 1
    assert parsed["method"] == "initialize"
    assert "params" in parsed


def test_parse_invalid_jsonrpc_request():
    """测试解析无效的 JSON-RPC 请求"""
    protocol = MCPProtocol()
    
    request = {
        "jsonrpc": "1.0",  # 无效版本
        "id": 1,
        "method": "test"
    }
    
    with pytest.raises(ValueError, match="Invalid JSON-RPC version"):
        protocol.parse_request(request)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mcp_protocol.py::test_parse_valid_jsonrpc_request -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'trae_mysql_mcp.mcp_protocol'"

- [ ] **Step 3: Write minimal implementation for MCPProtocol**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mcp_protocol.py::test_parse_valid_jsonrpc_request -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add trae_mysql_mcp/mcp_protocol.py tests/test_mcp_protocol.py
git commit -m "feat: add MCP protocol handler with basic JSON-RPC support"
```

### Task 2: 实现 MCP 协议方法处理

**Files:**
- Modify: `trae_mysql_mcp/mcp_protocol.py`
- Modify: `tests/test_mcp_protocol.py`

- [ ] **Step 1: Write the failing test for initialize method**

```python
def test_handle_initialize_request():
    """测试处理 initialize 请求"""
    protocol = MCPProtocol()
    
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        }
    }
    
    response = protocol.handle_request(request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
    assert "protocolVersion" in response["result"]
    assert "capabilities" in response["result"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mcp_protocol.py::test_handle_initialize_request -v`
Expected: FAIL with "AttributeError: 'MCPProtocol' object has no attribute 'handle_request'"

- [ ] **Step 3: Implement handle_request method**

```python
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
            "name": "trae-mysql-mcp",
            "version": "1.0.0"
        }
    }
    
    return self.create_response(request_id, result=result)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mcp_protocol.py::test_handle_initialize_request -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add trae_mysql_mcp/mcp_protocol.py tests/test_mcp_protocol.py
git commit -m "feat: add initialize method handler to MCP protocol"
```

---

## Chunk 2: 全局配置加载器

### Task 3: 实现全局配置加载器

**Files:**
- Create: `trae_mysql_mcp/mcp_config_loader.py`
- Test: `tests/test_mcp_config_loader.py`

- [ ] **Step 1: Write the failing test for config loading**

```python
"""
配置加载器测试
"""

import pytest
import tempfile
import os
from pathlib import Path
from trae_mysql_mcp.mcp_config_loader import MCPConfigLoader


def test_load_config_from_file():
    """测试从文件加载配置"""
    config_content = """
    {
      "datasources": {
        "master": {
          "host": "localhost",
          "port": 3306,
          "user": "root",
          "password": "test_password",
          "database": "test_db"
        }
      }
    }
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json5', delete=False) as f:
        f.write(config_content)
        config_file = f.name
    
    try:
        loader = MCPConfigLoader()
        config = loader.load_config(config_file)
        
        assert "datasources" in config
        assert "master" in config["datasources"]
        assert config["datasources"]["master"]["host"] == "localhost"
        assert config["datasources"]["master"]["port"] == 3306
    finally:
        os.unlink(config_file)


def test_load_config_priority():
    """测试配置加载优先级"""
    loader = MCPConfigLoader()
    
    # 测试默认配置路径
    default_path = loader.get_default_config_path()
    assert ".trae-mysql-mcp" in str(default_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mcp_config_loader.py::test_load_config_from_file -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'trae_mysql_mcp.mcp_config_loader'"

- [ ] **Step 3: Implement MCPConfigLoader**

```python
"""
MCP 配置加载器

支持从多个位置加载配置文件，实现优先级机制
"""

import os
import json5
from pathlib import Path
from typing import Dict, Any, Optional


class MCPConfigLoader:
    """
    MCP 配置加载器
    
    支持从多个位置加载配置：
    1. 命令行参数 --config
    2. 环境变量 TRAE_MYSQL_MCP_CONFIG
    3. 全局配置文件 ~/.trae-mysql-mcp/mcp_config.json5
    4. 默认配置
    """
    
    def __init__(self):
        """初始化配置加载器"""
        self.home_dir = Path.home()
        self.config_dir = self.home_dir / ".trae-mysql-mcp"
        self.config_file = self.config_dir / "mcp_config.json5"
    
    def get_default_config_path(self) -> Path:
        """
        获取默认配置文件路径
        
        Returns:
            Path: 配置文件路径
        """
        return self.config_file
    
    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径（可选）
            
        Returns:
            Dict[str, Any]: 配置数据
            
        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置文件格式错误
        """
        # 确定配置文件路径
        if config_path:
            path = Path(config_path)
        elif os.getenv("TRAE_MYSQL_MCP_CONFIG"):
            path = Path(os.getenv("TRAE_MYSQL_MCP_CONFIG"))
        elif self.config_file.exists():
            path = self.config_file
        else:
            return self._get_default_config()
        
        # 加载配置文件
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json5.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse config file: {str(e)}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置
        
        Returns:
            Dict[str, Any]: 默认配置
        """
        return {
            "datasources": {},
            "security": {
                "whitelist_enabled": False,
                "blacklist_enabled": True,
                "blacklist": ["DROP", "TRUNCATE", "ALTER", "CREATE"]
            }
        }
    
    def ensure_config_dir(self):
        """
        确保配置目录存在
        """
        self.config_dir.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mcp_config_loader.py::test_load_config_from_file -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add trae_mysql_mcp/mcp_config_loader.py tests/test_mcp_config_loader.py
git commit -m "feat: add MCP config loader with priority support"
```

---

## Chunk 3: MCP 工具实现

### Task 4: 实现 MCP 工具基类

**Files:**
- Create: `trae_mysql_mcp/mcp_tools.py`
- Test: `tests/test_mcp_tools.py`

- [ ] **Step 1: Write the failing test for tool definition**

```python
"""
MCP 工具测试
"""

import pytest
from trae_mysql_mcp.mcp_tools import MCPTools


def test_list_tools():
    """测试列出所有工具"""
    tools = MCPTools()
    
    tool_list = tools.list_tools()
    
    assert len(tool_list) == 4
    tool_names = [tool["name"] for tool in tool_list]
    assert "query_database" in tool_names
    assert "list_datasources" in tool_names
    assert "execute_sql" in tool_names
    assert "get_schema" in tool_names


def test_query_database_tool_definition():
    """测试 query_database 工具定义"""
    tools = MCPTools()
    
    tool_list = tools.list_tools()
    query_tool = next(t for t in tool_list if t["name"] == "query_database")
    
    assert "inputSchema" in query_tool
    assert "datasource" in query_tool["inputSchema"]["properties"]
    assert "sql" in query_tool["inputSchema"]["properties"]
    assert query_tool["inputSchema"]["required"] == ["datasource", "sql"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mcp_tools.py::test_list_tools -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'trae_mysql_mcp.mcp_tools'"

- [ ] **Step 3: Implement MCPTools base**

```python
"""
MCP 工具实现

实现 MCP 协议定义的工具，封装现有 MySQL 功能
"""

from typing import Dict, Any, List
from trae_mysql_mcp import TraeMySQLMCP


class MCPTools:
    """
    MCP 工具集合
    
    提供 4 个核心工具：
    - query_database: 查询数据库
    - list_datasources: 列出数据源
    - execute_sql: 执行 SQL
    - get_schema: 获取表结构
    """
    
    def __init__(self, mcp: TraeMySQLMCP):
        """
        初始化工具集合
        
        Args:
            mcp: TraeMySQLMCP 实例
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mcp_tools.py::test_list_tools -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add trae_mysql_mcp/mcp_tools.py tests/test_mcp_tools.py
git commit -m "feat: add MCP tools base with tool definitions"
```

### Task 5: 实现 query_database 工具

**Files:**
- Modify: `trae_mysql_mcp/mcp_tools.py`
- Modify: `tests/test_mcp_tools.py`

- [ ] **Step 1: Write the failing test for query_database**

```python
def test_execute_query_database_tool():
    """测试执行 query_database 工具"""
    from trae_mysql_mcp import TraeMySQLMCP, DataSourceConfig
    
    # 创建 MCP 实例
    mcp = TraeMySQLMCP()
    
    # 添加测试数据源（使用模拟配置）
    config = DataSourceConfig(
        name="test_ds",
        host="localhost",
        port=3306,
        user="test_user",
        password="test_password",
        database="test_db"
    )
    mcp.add_data_source(config)
    
    tools = MCPTools(mcp)
    
    # 测试工具执行（这里会失败，因为没有真实数据库）
    with pytest.raises(Exception):  # 预期会抛出连接错误
        tools.execute_tool("query_database", {
            "datasource": "test_ds",
            "sql": "SELECT 1"
        })
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mcp_tools.py::test_execute_query_database_tool -v`
Expected: FAIL with "AttributeError: 'MCPTools' object has no attribute 'execute_tool'"

- [ ] **Step 3: Implement execute_tool method**

```python
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
    
    # 连接数据源
    self.mcp.connect(datasource)
    
    # 执行查询
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
    
    # 连接数据源
    self.mcp.connect(datasource)
    
    # 执行 SQL
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
    
    # 连接数据源
    self.mcp.connect(datasource)
    
    # 查询表结构
    if table:
        sql = f"DESCRIBE {table}"
    else:
        sql = "SHOW TABLES"
    
    result = self.mcp.execute(sql, datasource=datasource)
    
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mcp_tools.py::test_execute_query_database_tool -v`
Expected: PASS (with expected exception)

- [ ] **Step 5: Commit**

```bash
git add trae_mysql_mcp/mcp_tools.py tests/test_mcp_tools.py
git commit -m "feat: implement MCP tools execution methods"
```

---

## Chunk 4: MCP 服务器主程序

### Task 6: 实现 MCP 服务器

**Files:**
- Create: `trae_mysql_mcp/mcp_server.py`
- Test: `tests/test_mcp_server.py`

- [ ] **Step 1: Write the failing test for MCP server**

```python
"""
MCP 服务器测试
"""

import pytest
from trae_mysql_mcp.mcp_server import MCPServer


def test_mcp_server_initialization():
    """测试 MCP 服务器初始化"""
    server = MCPServer()
    
    assert server is not None
    assert server.protocol is not None
    assert server.tools is not None


def test_mcp_server_handle_initialize():
    """测试处理 initialize 请求"""
    server = MCPServer()
    
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "1.0"}
        }
    }
    
    response = server.handle_request(request)
    
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert "result" in response
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_mcp_server.py::test_mcp_server_initialization -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'trae_mysql_mcp.mcp_server'"

- [ ] **Step 3: Implement MCPServer**

```python
"""
MCP 服务器主程序

实现基于 stdio 的 MCP 服务器，处理 JSON-RPC 2.0 请求
"""

import sys
import json
import argparse
from typing import Dict, Any
from trae_mysql_mcp import TraeMySQLMCP
from trae_mysql_mcp.mcp_protocol import MCPProtocol
from trae_mysql_mcp.mcp_tools import MCPTools
from trae_mysql_mcp.mcp_config_loader import MCPConfigLoader


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
        # 加载配置
        loader = MCPConfigLoader()
        config = loader.load_config(config_path)
        
        # 初始化 MCP
        self.mcp = TraeMySQLMCP()
        
        # 添加数据源
        if "datasources" in config:
            for ds_name, ds_config in config["datasources"].items():
                from trae_mysql_mcp import DataSourceConfig
                ds_config["name"] = ds_name
                ds = DataSourceConfig.from_dict(ds_config)
                self.mcp.add_data_source(ds)
        
        # 初始化协议和工具
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
            
            # 包装结果为 MCP 格式
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
                
                # 写入响应
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_mcp_server.py::test_mcp_server_initialization -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add trae_mysql_mcp/mcp_server.py tests/test_mcp_server.py
git commit -m "feat: implement MCP server with stdio communication"
```

---

## Chunk 5: 更新配置和文档

### Task 7: 更新 setup.py

**Files:**
- Modify: `setup.py`

- [ ] **Step 1: Update setup.py with MCP entry point**

```python
entry_points={
    "console_scripts": [
        "trae-mysql-mcp=trae_mysql_mcp.cli:main",
        "trae-mysql-mcp-server=trae_mysql_mcp.mcp_server:main",
    ],
}
```

- [ ] **Step 2: Test entry point**

Run: `python -m trae_mysql_mcp.mcp_server --help`
Expected: Shows help message

- [ ] **Step 3: Commit**

```bash
git add setup.py
git commit -m "feat: add MCP server entry point to setup.py"
```

### Task 8: 更新 README 文档

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add MCP usage section to README**

在 README.md 中添加 MCP 使用说明：

```markdown
## MCP 服务器使用

### 1. 配置数据源

创建全局配置文件 `~/.trae-mysql-mcp/mcp_config.json5`：

\`\`\`json5
{
  "datasources": {
    "master": {
      "host": "localhost",
      "port": 3306,
      "user": "root",
      "password": "your_password",
      "database": "production"
    }
  }
}
\`\`\`

### 2. 启动 MCP 服务器

\`\`\`bash
python -m trae_mysql_mcp.mcp_server
\`\`\`

### 3. TRAE SOLO IDE 配置

在 IDE 的 MCP 设置中添加：

\`\`\`json
{
  "mcpServers": {
    "trae-mysql-mcp": {
      "command": "python",
      "args": ["-m", "trae_mysql_mcp.mcp_server"]
    }
  }
}
\`\`\`

### 4. 可用工具

- **query_database**: 查询数据库
- **list_datasources**: 列出数据源
- **execute_sql**: 执行 SQL
- **get_schema**: 获取表结构
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add MCP server usage documentation"
```

---

## 验证和测试

### Task 9: 运行完整测试套件

- [ ] **Step 1: Run all tests**

Run: `pytest tests/ -v --cov=trae_mysql_mcp`
Expected: All tests pass with coverage > 80%

- [ ] **Step 2: Test MCP server manually**

```bash
# 启动服务器
python -m trae_mysql_mcp.mcp_server

# 在另一个终端发送测试请求
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | python -m trae_mysql_mcp.mcp_server
```

Expected: Returns valid JSON-RPC response

- [ ] **Step 3: Final commit**

```bash
git add .
git commit -m "feat: complete MySQL MCP server implementation"
```

---

## 完成标准

- ✅ 所有单元测试通过
- ✅ MCP 协议完整实现
- ✅ 4 个核心工具可用
- ✅ 全局配置支持
- ✅ 文档更新完成
- ✅ 可以在 TRAE SOLO IDE 中使用
