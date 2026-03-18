# MySQL MCP Server 设计文档

## 概述

为 TRAE SOLO IDE 开发一个基于标准 MCP 协议的 MySQL 多数据源管理工具，让 AI 能够通过 MCP 协议查询多个 MySQL 数据库。

## 目标

- 实现标准 MCP 协议（JSON-RPC 2.0 over stdio）
- 支持多个 MySQL 数据源管理
- 提供 AI 可调用的查询工具
- 完全复用现有代码
- 支持请求取消和超时控制
- 支持结果分页和大小限制

## 关键设计决策

### 1. 返回格式标准化

**查询结果返回 Markdown 表格（推荐）：**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text/markdown",
        "text": "| id | name  |\n|----|-------|\n| 1  | Alice |\n| 2  | Bob   |\n\n**元数据**\n- 影响行数: 2\n- 执行时间: 0.015s"
      }
    ]
  }
}
```

**或返回 JSON 格式（可选）：**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\": true, \"data\": [...], \"columns\": [...]}"
      }
    ]
  }
}
```

### 2. 异步模型

- 使用同步 I/O（当前实现）
- 未来可扩展为异步 I/O（asyncio + aiomysql）
- 连接池支持并发访问

### 3. 请求取消机制

- 支持 `$/cancelRequest` 方法
- 使用 threading.Event 实现取消信号
- SQL 执行超时自动取消

**取消请求示例：**
```json
{
  "jsonrpc": "2.0",
  "method": "$/cancelRequest",
  "params": {
    "id": 1
  }
}
```

**实现机制：**
```python
# 在 SQL 执行时检查取消信号
if cancel_event.is_set():
    raise CancelledError("Request cancelled by client")
```

### 4. 结果分页和大小限制

**默认限制：**
- 单次查询最大返回 1000 行
- 超过限制时返回警告信息
- 支持自定义 limit 参数

**分页示例：**
```json
{
  "datasource": "master",
  "sql": "SELECT * FROM large_table",
  "limit": 100,
  "offset": 0
}
```

### 5. 错误恢复机制

**连接失败自动重试：**
- 最大重试次数：3
- 重试间隔：指数退避（1s, 2s, 4s）
- 失败后返回详细错误信息

**超时处理：**
- 默认 SQL 执行超时：60 秒
- 可在配置文件中自定义
- 超时后自动释放连接

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────┐
│         TRAE SOLO IDE (AI Agent)        │
└────────────────┬────────────────────────┘
                 │ JSON-RPC 2.0 (stdio)
┌────────────────▼────────────────────────┐
│         MCP Server (Python)             │
│  ┌──────────────────────────────────┐  │
│  │   MCP Protocol Handler           │  │
│  │   - initialize                   │  │
│  │   - tools/list                   │  │
│  │   - tools/call                   │  │
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │   Tool Implementations           │  │
│  │   - query_database               │  │
│  │   - list_datasources             │  │
│  │   - execute_sql                  │  │
│  │   - get_schema                   │  │
│  └──────────────────────────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │   Existing MySQL Layer           │  │
│  │   - Connection Pool              │  │
│  │   - SQL Executor                 │  │
│  │   - Config Manager               │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### 数据流

```
1. AI 发起查询请求
   ↓
2. MCP Server 接收 JSON-RPC 请求
   ↓
3. 解析工具名称和参数
   ↓
4. 调用对应的工具处理器
   ↓
5. 工具处理器调用 MySQL 连接池
   ↓
6. 执行 SQL 查询
   ↓
7. 格式化查询结果
   ↓
8. 返回 JSON-RPC 响应
   ↓
9. AI 接收结果
```

## MCP 工具定义

### 工具 1: query_database

**描述：** 在指定的 MySQL 数据源上执行查询 SQL

**输入模式：**
```json
{
  "type": "object",
  "properties": {
    "datasource": {
      "type": "string",
      "description": "数据源名称"
    },
    "sql": {
      "type": "string",
      "description": "完整的 SELECT 查询语句"
    },
    "limit": {
      "type": "integer",
      "description": "返回结果最大行数（可选，默认 1000）",
      "default": 1000
    },
    "format": {
      "type": "string",
      "description": "返回格式：markdown 或 json（可选，默认 markdown）",
      "enum": ["markdown", "json"],
      "default": "markdown"
    }
  },
  "required": ["datasource", "sql"]
}
```

**返回示例（Markdown 格式）：**
```json
{
  "success": true,
  "content": "| id | name  |\n|----|-------|\n| 1  | Alice |\n| 2  | Bob   |\n\n**元数据**\n- 影响行数: 2\n- 执行时间: 0.015s\n- 数据源: master"
}
```

### 工具 2: list_datasources

**描述：** 列出所有可用的 MySQL 数据源

**输入模式：**
```json
{
  "type": "object",
  "properties": {}
}
```

**返回示例：**
```json
{
  "datasources": [
    {
      "name": "master",
      "host": "localhost",
      "port": 3306,
      "database": "production",
      "status": "connected",
      "error": null,
      "last_used": "2026-03-12T10:30:00Z",
      "pool_size": 5
    },
    {
      "name": "slave",
      "host": "localhost",
      "port": 3307,
      "database": "production",
      "status": "error",
      "error": "Connection refused",
      "last_used": "2026-03-12T10:25:00Z",
      "pool_size": 0
    }
  ]
}
```

### 工具 3: execute_sql

**描述：** 执行 SQL 语句（INSERT/UPDATE/DELETE 等）

**输入模式：**
```json
{
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
```

**返回示例：**
```json
{
  "success": true,
  "affected_rows": 5,
  "execution_time": 0.023
}
```

### 工具 4: get_schema

**描述：** 获取指定数据源的表结构信息

**输入模式：**
```json
{
  "type": "object",
  "properties": {
    "datasource": {
      "type": "string",
      "description": "数据源名称"
    },
    "table": {
      "type": "string",
      "description": "表名（可选，不指定则返回所有表）"
    },
    "format": {
      "type": "string",
      "description": "返回格式：markdown 或 json（可选，默认 markdown）",
      "enum": ["markdown", "json"],
      "default": "markdown"
    }
  },
  "required": ["datasource"]
}
```

**返回示例（Markdown 格式）：**
```json
{
  "success": true,
  "content": "## 表: users\n\n| 列名 | 类型 | 可空 | 键 |\n|------|------|------|---|\n| id | int | NO | PRI |\n| name | varchar(255) | YES | |\n\n**索引**\n- PRIMARY KEY (id)\n\n**表信息**\n- 数据源: master\n- 数据库: production\n- 行数: 1234"
}
```

## 配置设计

### 全局配置文件位置

配置文件存放在用户主目录下：

- macOS/Linux: `~/.trae-mysql-mcp/mcp_config.json5`
- Windows: `C:\Users\<用户名>\.trae-mysql-mcp\mcp_config.json5`

### 配置文件结构

```json5
{
  "datasources": {
    "master": {
      "host": "localhost",
      "port": 3306,
      "user": "root",
      "password": "your_password",
      "database": "production",
      "pool_min_size": 2,
      "pool_max_size": 10
    },
    "slave": {
      "host": "localhost",
      "port": 3307,
      "user": "readonly",
      "password": "your_password",
      "database": "production",
      "pool_min_size": 5,
      "pool_max_size": 20
    }
  },
  "security": {
    "whitelist_enabled": false,
    "blacklist_enabled": true,
    "blacklist": ["DROP", "TRUNCATE", "ALTER", "CREATE"]
  }
}
```

### 配置加载优先级

1. 命令行参数 `--config`
2. 环境变量 `TRAE_MYSQL_MCP_CONFIG`
3. 全局配置文件 `~/.trae-mysql-mcp/mcp_config.json5`
4. 默认配置（如果都不存在）

## MCP 协议实现

### JSON-RPC 2.0 请求格式

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "query_database",
    "arguments": {
      "datasource": "master",
      "sql": "SELECT * FROM users LIMIT 10"
    }
  }
}
```

### JSON-RPC 2.0 响应格式

**成功响应：**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\": true, \"data\": [...]}"
      }
    ]
  }
}
```

**错误响应：**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": {
      "reason": "数据源 'unknown' 不存在",
      "available_datasources": ["master", "slave"]
    }
  }
}
```

### MCP 协议方法

| 方法 | 描述 |
|------|------|
| initialize | 初始化 MCP 服务器 |
| tools/list | 列出所有可用工具 |
| tools/call | 调用指定工具 |

## 文件结构

### 新增文件

```
TraeMysqlMCP/
├── trae_mysql_mcp/
│   ├── mcp_server.py          # MCP 服务器主程序
│   ├── mcp_protocol.py        # MCP 协议处理器
│   ├── mcp_tools.py           # MCP 工具实现
│   └── mcp_config_loader.py   # 全局配置加载器
├── tests/
│   ├── test_mcp_server.py     # MCP 服务器测试
│   ├── test_mcp_protocol.py   # 协议测试
│   └── test_mcp_tools.py      # 工具测试
└── setup.py                   # 更新入口点
```

### 模块职责

| 模块 | 职责 |
|------|------|
| mcp_server.py | MCP 服务器主程序，处理 stdio 通信 |
| mcp_protocol.py | JSON-RPC 2.0 协议解析和响应构建 |
| mcp_tools.py | 实现具体的 MCP 工具 |
| mcp_config_loader.py | 加载全局配置文件 |

## 启动方式

### 命令行启动

```bash
# 方式一：自动加载全局配置（推荐）
python -m trae_mysql_mcp.mcp_server

# 方式二：指定配置文件路径
python -m trae_mysql_mcp.mcp_server --config /path/to/mcp_config.json5

# 方式三：通过环境变量指定
export TRAE_MYSQL_MCP_CONFIG=/path/to/mcp_config.json5
python -m trae_mysql_mcp.mcp_server
```

### TRAE SOLO IDE 配置

在 IDE 的 MCP 设置中添加：

```json
{
  "mcpServers": {
    "trae-mysql-mcp": {
      "command": "python",
      "args": ["-m", "trae_mysql_mcp.mcp_server"]
    }
  }
}
```

## 错误处理

### 错误类型

| 错误代码 | 描述 |
|---------|------|
| -32700 | Parse error（解析错误） |
| -32600 | Invalid Request（无效请求） |
| -32601 | Method not found（方法未找到） |
| -32602 | Invalid params（无效参数） |
| -32603 | Internal error（内部错误） |

### 错误处理示例

```python
try:
    result = tool.execute(arguments)
except DataSourceNotFoundError as e:
    return error_response(-32602, f"数据源不存在: {e}")
except SQLExecutionError as e:
    return error_response(-32603, f"SQL 执行失败: {e}")
except Exception as e:
    return error_response(-32603, f"内部错误: {e}")
```

## 测试策略

### 单元测试

| 测试模块 | 测试内容 |
|---------|---------|
| test_mcp_protocol.py | JSON-RPC 请求/响应解析、错误处理 |
| test_mcp_tools.py | 各工具的正确性、边界条件 |
| test_mcp_config_loader.py | 配置加载、优先级、错误处理 |

### 集成测试

- 测试完整的 MCP 通信流程
- 测试多数据源切换
- 测试 SQL 执行和结果返回

### 手动测试

```bash
# 启动 MCP 服务器
python -m trae_mysql_mcp.mcp_server

# 发送测试请求
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | python -m trae_mysql_mcp.mcp_server
```

### 测试覆盖率目标

- MCP 协议处理：90%+
- MCP 工具实现：85%+
- 配置加载：80%+

## 开发计划

### 预估工作量

- 新增代码量：约 500-800 行
- 开发时间：约 2-3 天
- 测试时间：约 1 天

### 开发步骤

1. 实现 MCP 协议处理器（mcp_protocol.py）
2. 实现全局配置加载器（mcp_config_loader.py）
3. 实现 MCP 工具（mcp_tools.py）
4. 实现 MCP 服务器主程序（mcp_server.py）
5. 编写单元测试
6. 集成测试和调试
7. 更新文档

## 依赖

- Python 3.8+
- 现有依赖（pymysql, DBUtils, cryptography 等）
- 无需新增依赖

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| MCP 协议版本兼容性 | 中 | 严格遵循 MCP 标准，添加版本检查 |
| 配置文件权限问题 | 低 | 提供友好的错误提示和修复建议 |
| SQL 注入风险 | 高 | 使用参数化查询，启用安全检查 |
| 连接池耗尽 | 中 | 实现连接池监控和自动扩容 |

## 总结

本设计文档详细描述了 MySQL MCP Server 的实现方案，包括架构设计、工具定义、配置方式、协议实现、文件结构、测试策略等。该方案完全复用现有代码，符合 MCP 标准协议，能够满足 AI 查询多个 MySQL 数据源的需求。
