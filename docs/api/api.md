# API 文档

## 核心类

### TraeMySQLMCP

#### 初始化

```python
from trae_mysql_mcp import TraeMySQLMCP

# 基本初始化
mcp = TraeMySQLMCP()

# 从配置文件初始化
mcp = TraeMySQLMCP(config_file='config.json5')

# 自定义加密密钥
mcp = TraeMySQLMCP(encryption_key='your_32_byte_key')
```

#### 方法列表

| 方法名 | 描述 | 参数 | 返回值 |
|--------|------|------|--------|
| `connect(datasource_name='default')` | 连接数据源 | datasource_name: 数据源名称 | bool: 连接成功 |
| `disconnect(datasource_name=None)` | 断开连接 | datasource_name: 数据源名称(可选) | None |
| `disconnect_all()` | 断开所有连接 | 无 | None |
| `execute(sql, params=None, datasource=None, timeout=None)` | 执行SQL | sql: SQL语句<br>params: 参数<br>datasource: 数据源<br>timeout: 超时时间 | Dict: 执行结果 |
| `execute_many(sql, params_list, datasource=None, timeout=None)` | 批量执行SQL | sql: SQL语句<br>params_list: 参数列表<br>datasource: 数据源<br>timeout: 超时时间 | Dict: 执行结果 |
| `execute_in_transaction(sql_list, datasource=None)` | 事务执行 | sql_list: SQL列表<br>datasource: 数据源 | List: 执行结果列表 |
| `register_hook(hook_type, hook_func, datasource=None)` | 注册钩子 | hook_type: 钩子类型<br>hook_func: 钩子函数<br>datasource: 数据源 | None |
| `get_pool_status(datasource=None)` | 获取连接池状态 | datasource: 数据源 | Dict: 状态信息 |
| `get_health_status(datasource=None)` | 获取健康状态 | datasource: 数据源 | Dict: 健康状态 |
| `get_performance_report(datasource=None)` | 获取性能报告 | datasource: 数据源 | Dict: 性能报告 |
| `resize_pool(min_size, max_size, datasource=None)` | 调整连接池大小 | min_size: 最小连接数<br>max_size: 最大连接数<br>datasource: 数据源 | None |
| `add_data_source(config, encrypt=True)` | 添加数据源 | config: 数据源配置<br>encrypt: 是否加密 | None |
| `list_data_sources()` | 列出数据源 | 无 | List: 数据源列表 |
| `remove_data_source(name)` | 移除数据源 | name: 数据源名称 | None |
| `save_config(file_path)` | 保存配置 | file_path: 保存路径 | None |
| `load_config(file_path)` | 加载配置 | file_path: 配置路径 | None |
| `get_security_config()` | 获取安全配置 | 无 | SecurityConfig |
| `update_security_config(**kwargs)` | 更新安全配置 | **kwargs: 配置参数 | None |

## 配置类

### DataSourceConfig

```python
from trae_mysql_mcp import DataSourceConfig

config = DataSourceConfig(
    name="default",
    host="localhost",
    port=3306,
    user="root",
    password="password",
    database="test_db",
    pool_min_size=2,
    pool_max_size=10,
    pool_timeout=30,
    sql_timeout=60,
    charset="utf8mb4",
    autocommit=False
)
```

### SecurityConfig

```python
from trae_mysql_mcp.config import SecurityConfig

security_config = SecurityConfig(
    whitelist_enabled=False,
    blacklist_enabled=True,
    whitelist=["SELECT", "INSERT"],
    blacklist=["DROP", "TRUNCATE", "ALTER", "CREATE"]
)
```

## 异常类

| 异常类 | 描述 |
|--------|------|
| `TraeMCPError` | 基础异常 |
| `ConfigurationError` | 配置错误 |
| `ConnectionPoolError` | 连接池错误 |
| `SQLExecutionError` | SQL执行错误 |
| `TimeoutError` | 超时错误 |
| `SecurityError` | 安全错误 |
| `EncryptionError` | 加密错误 |
| `DataSourceNotFoundError` | 数据源未找到 |
| `ConnectionNotFoundError` | 连接未找到 |

## 钩子函数

### 支持的钩子类型

- `before_execute`: SQL执行前调用
- `after_execute`: SQL执行后调用
- `on_error`: SQL执行出错时调用

### 钩子函数格式

```python
def before_execute_hook(sql, params):
    print(f"执行SQL: {sql}")

def after_execute_hook(sql, params, result):
    print(f"执行结果: {result}")

def on_error_hook(sql, params, error):
    print(f"执行错误: {error}")

# 注册钩子
mcp.register_hook('before_execute', before_execute_hook)
mcp.register_hook('after_execute', after_execute_hook)
mcp.register_hook('on_error', on_error_hook)
```

## 上下文管理器

```python
with TraeMySQLMCP(config_file='config.json5') as mcp:
    mcp.connect('default')
    result = mcp.execute('SELECT * FROM users LIMIT 10')
    print(result)
# 自动断开所有连接
```

## 命令行接口

```bash
# 查看帮助
trae-mysql-mcp --help

# 连接数据源
trae-mysql-mcp connect default

# 执行SQL
trae-mysql-mcp execute "SELECT * FROM users"

# 查看状态
trae-mysql-mcp status

# 健康检查
trae-mysql-mcp health

# 性能报告
trae-mysql-mcp performance

# 列出数据源
trae-mysql-mcp list

# 调整连接池大小
trae-mysql-mcp resize 5 20

# 保存配置
trae-mysql-mcp save config.json5

# 加载配置
trae-mysql-mcp load config.json5
```
