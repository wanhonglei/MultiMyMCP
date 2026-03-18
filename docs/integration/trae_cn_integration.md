# TRAE CN 集成指南

## 概述

本指南详细介绍如何在 TRAE CN IDE 环境中部署和使用 TraeMySQLMCP 工具。

## 安装步骤

### 1. 克隆代码

在 TRAE CN IDE 中打开终端，执行以下命令：

```bash
# 克隆代码到项目目录
git clone https://github.com/trae/trae-mysql-mcp.git
cd trae-mysql-mcp
```

### 2. 安装依赖

```bash
# 安装依赖
pip install -r requirements.txt

# 或者使用开发模式安装
pip install -e .
```

### 3. 配置环境变量

创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填写数据库连接信息：

```dotenv
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=test_db

MYSQL_POOL_MIN_SIZE=2
MYSQL_POOL_MAX_SIZE=10
MYSQL_POOL_TIMEOUT=30
MYSQL_SQL_TIMEOUT=60

MYSQL_ENCRYPTION_KEY=your_32_byte_encryption_key_here

MYSQL_WHITELIST_ENABLED=false
MYSQL_BLACKLIST_ENABLED=true
MYSQL_BLACKLIST=DROP,TRUNCATE,ALTER,CREATE
```

### 4. 测试安装

```bash
# 运行单元测试
pytest tests/ -v

# 检查命令行工具
python -m trae_mysql_mcp.cli --help
```

## 作为 TRAE CN 插件使用

### 1. 创建插件配置

在项目根目录创建 `trae-plugin.json` 文件：

```json
{
  "name": "trae-mysql-mcp",
  "version": "1.0.0",
  "description": "生产级 MySQL 多数据源 MCP 工具",
  "author": "TraeMCP Team",
  "dependencies": [
    "pymysql>=1.0.0",
    "DBUtils>=2.0.0",
    "python-dotenv>=0.19.0",
    "cryptography>=3.4.0",
    "psutil>=5.8.0",
    "json5>=0.9.0"
  ],
  "entry_points": {
    "cli": "trae-mysql-mcp=trae_mysql_mcp.cli:main"
  },
  "config_files": [
    ".env",
    "config.json5"
  ]
}
```

### 2. 打包插件

```bash
# 创建打包目录
mkdir -p dist

# 打包为 zip 文件
zip -r dist/trae-mysql-mcp-plugin.zip . -x "*.git*" "*.pyc" "__pycache__/" "dist/"
```

### 3. 在 TRAE CN 中安装插件

1. 打开 TRAE CN IDE
2. 点击左侧菜单栏的 "插件管理"
3. 点击 "上传插件"
4. 选择 `dist/trae-mysql-mcp-plugin.zip` 文件
5. 点击 "安装"
6. 等待安装完成后，点击 "启用"

## 在 TRAE CN 项目中使用

### 1. 基本使用

在 Python 代码中导入并使用：

```python
from trae_mysql_mcp import TraeMySQLMCP

# 初始化 MCP
mcp = TraeMySQLMCP()

# 连接数据源
mcp.connect('default')

# 执行 SQL
result = mcp.execute('SELECT * FROM users LIMIT 10')
print(result)

# 断开连接
mcp.disconnect()
```

### 2. 多数据源配置

```python
from trae_mysql_mcp import TraeMySQLMCP, DataSourceConfig

mcp = TraeMySQLMCP()

# 添加主库
master_config = DataSourceConfig(
    name="master",
    host="master_db",
    port=3306,
    user="root",
    password="master_password",
    database="production"
)
mcp.add_data_source(master_config)

# 添加从库
slave_config = DataSourceConfig(
    name="slave",
    host="slave_db",
    port=3306,
    user="readonly",
    password="slave_password",
    database="production"
)
mcp.add_data_source(slave_config)

# 使用主库写操作
mcp.connect('master')
mcp.execute('INSERT INTO users (name) VALUES ("test")')

# 使用从库读操作
mcp.connect('slave')
result = mcp.execute('SELECT * FROM users')
```

### 3. 事务使用

```python
from trae_mysql_mcp import TraeMySQLMCP

mcp = TraeMySQLMCP()
mcp.connect('default')

# 使用事务
try:
    # 开始事务
    mcp._executors['default'].begin_transaction()
    
    # 执行多个操作
    mcp.execute('INSERT INTO orders (user_id, amount) VALUES (1, 100)')
    mcp.execute('UPDATE users SET balance = balance - 100 WHERE id = 1')
    
    # 提交事务
    mcp._executors['default'].commit_transaction()
except Exception as e:
    # 回滚事务
    mcp._executors['default'].rollback_transaction()
    raise
```

## 调试技巧

### 1. 查看连接池状态

```python
from trae_mysql_mcp import TraeMySQLMCP

mcp = TraeMySQLMCP()
mcp.connect('default')

# 查看连接池状态
status = mcp.get_pool_status()
print("连接池状态:")
print(f"  最小连接数: {status['min_size']}")
print(f"  最大连接数: {status['max_size']}")
print(f"  当前连接数: {status['current_size']}")
print(f"  活跃连接数: {status['active_size']}")
print(f"  空闲连接数: {status['idle_size']}")
```

### 2. 查看性能报告

```python
# 查看性能报告
report = mcp.get_performance_report()
print("性能报告:")
print(f"  总执行次数: {report['summary']['total_sql_executions']}")
print(f"  成功率: {report['summary']['success_rate']:.2f}%")
print(f"  平均执行时间: {report['summary']['avg_execution_time']:.3f}s")
print(f"  慢查询数量: {report['performance_indicators']['slow_queries']}")
print(f"  错误率: {report['performance_indicators']['error_rate']:.2f}%")
```

### 3. 健康检查

```python
# 健康检查
health = mcp.get_health_status()
print("健康检查:")
print(f"  健康状态: {'健康' if health['healthy'] else '异常'}")
if not health['healthy']:
    print("  问题:")
    for issue in health['issues']:
        print(f"    - {issue}")
```

### 4. 日志查看

在 TRAE CN IDE 的日志面板中查看执行日志：

- 点击左侧菜单栏的 "日志"
- 选择 "应用日志"
- 查看 TraeMySQLMCP 相关的日志信息

### 5. 命令行工具

使用命令行工具进行管理：

```bash
# 列出数据源
trae-mysql-mcp list

# 查看状态
trae-mysql-mcp status

# 健康检查
trae-mysql-mcp health

# 性能报告
trae-mysql-mcp performance

# 执行 SQL
trae-mysql-mcp execute "SELECT * FROM users LIMIT 5"
```

## 常见问题解决

### 1. 连接失败

**症状**：连接池初始化失败

**解决方法**：
- 检查数据库连接信息是否正确
- 确认数据库服务是否运行
- 检查网络连接是否正常
- 查看 TRAE CN 环境的网络权限

### 2. 性能问题

**症状**：SQL 执行缓慢

**解决方法**：
- 检查 SQL 语句是否优化
- 调整连接池大小
- 检查数据库索引
- 查看慢查询日志

### 3. 内存溢出

**症状**：程序内存使用过高

**解决方法**：
- 限制结果集大小
- 调整连接池最大连接数
- 使用分页查询
- 及时释放连接

### 4. 安全错误

**症状**：SQL 执行被拒绝

**解决方法**：
- 检查 SQL 语句是否在白名单中
- 确认 SQL 语句不包含黑名单关键字
- 调整安全配置

## 最佳实践

### 1. 配置管理

- 使用环境变量管理敏感配置
- 定期备份配置文件
- 不同环境使用不同配置

### 2. 错误处理

- 实现统一的错误处理机制
- 记录详细的错误日志
- 实现重试机制

### 3. 监控与告警

- 定期监控连接池状态
- 设置性能指标告警
- 及时处理异常情况

### 4. 版本管理

- 定期更新版本
- 记录详细的更新日志
- 测试后再部署到生产环境

## 示例项目

### 完整示例

```python
"""
TraeMySQLMCP 示例项目
"""

from trae_mysql_mcp import TraeMySQLMCP, DataSourceConfig


def main():
    # 初始化 MCP
    mcp = TraeMySQLMCP()
    
    # 添加数据源
    config = DataSourceConfig(
        name="default",
        host="localhost",
        port=3306,
        user="root",
        password="password",
        database="test_db"
    )
    mcp.add_data_source(config)
    
    # 连接数据源
    mcp.connect('default')
    
    try:
        # 执行 SQL
        print("=== 执行 SQL 测试 ===")
        result = mcp.execute('SELECT 1 + 1 AS result')
        print(f"测试结果: {result['data']}")
        
        # 查看连接池状态
        print("\n=== 连接池状态 ===")
        status = mcp.get_pool_status()
        for key, value in status.items():
            print(f"{key}: {value}")
        
        # 查看性能报告
        print("\n=== 性能报告 ===")
        report = mcp.get_performance_report()
        print(f"总执行次数: {report['summary']['total_sql_executions']}")
        print(f"成功率: {report['summary']['success_rate']:.2f}%")
        print(f"平均执行时间: {report['summary']['avg_execution_time']:.3f}s")
        
        # 健康检查
        print("\n=== 健康检查 ===")
        health = mcp.get_health_status()
        print(f"健康状态: {'健康' if health['healthy'] else '异常'}")
        if not health['healthy']:
            print("问题:")
            for issue in health['issues']:
                print(f"  - {issue}")
                
    finally:
        # 断开连接
        mcp.disconnect_all()
        print("\n连接已断开")


if __name__ == '__main__':
    main()
```

## 总结

TraeMySQLMCP 是一个功能强大、性能优异的 MySQL 多数据源管理工具，完全适配 TRAE CN IDE 环境。通过本指南的配置和使用，您可以在 TRAE CN 项目中轻松集成和使用该工具，提高数据库操作的效率和安全性。

如有任何问题，请参考文档或联系技术支持。
