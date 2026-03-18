# 配置说明

## 配置文件格式

TraeMySQLMCP 支持两种配置方式：
1. 环境变量配置
2. JSON5 配置文件

### 环境变量配置

在 `.env` 文件中配置以下环境变量：

```dotenv
# 数据库连接信息
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=test_db

# 连接池配置
MYSQL_POOL_MIN_SIZE=2
MYSQL_POOL_MAX_SIZE=10
MYSQL_POOL_TIMEOUT=30
MYSQL_SQL_TIMEOUT=60

# 加密配置
MYSQL_ENCRYPTION_KEY=your_32_byte_encryption_key_here

# 安全配置
MYSQL_WHITELIST_ENABLED=false
MYSQL_BLACKLIST_ENABLED=true
MYSQL_BLACKLIST=DROP,TRUNCATE,ALTER,CREATE
```

### JSON5 配置文件

创建 `config.json5` 文件：

```json5
{
  "data_sources": {
    "default": {
      "host": "localhost",
      "port": 3306,
      "user": "root",
      "password": "encrypted_password",
      "database": "test_db",
      "pool_min_size": 2,
      "pool_max_size": 10,
      "pool_timeout": 30,
      "sql_timeout": 60,
      "charset": "utf8mb4",
      "autocommit": false,
      "encrypted": true
    },
    "secondary": {
      "host": "localhost",
      "port": 3306,
      "user": "root",
      "password": "encrypted_password",
      "database": "test_db2",
      "pool_min_size": 2,
      "pool_max_size": 5,
      "pool_timeout": 30,
      "sql_timeout": 60
    }
  },
  "security": {
    "whitelist_enabled": false,
    "blacklist_enabled": true,
    "whitelist": ["SELECT", "INSERT"],
    "blacklist": ["DROP", "TRUNCATE", "ALTER", "CREATE"]
  }
}
```

## 配置参数说明

### 数据源配置

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `name` | str | 数据源名称 | - |
| `host` | str | 数据库主机地址 | - |
| `port` | int | 数据库端口 | 3306 |
| `user` | str | 数据库用户名 | - |
| `password` | str | 数据库密码 | - |
| `database` | str | 数据库名称 | - |
| `pool_min_size` | int | 连接池最小连接数 | 2 |
| `pool_max_size` | int | 连接池最大连接数 | 10 |
| `pool_timeout` | int | 连接池超时时间(秒) | 30 |
| `sql_timeout` | int | SQL执行超时时间(秒) | 60 |
| `charset` | str | 字符集 | utf8mb4 |
| `autocommit` | bool | 是否自动提交 | false |
| `encrypted` | bool | 密码是否已加密 | false |

### 安全配置

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| `whitelist_enabled` | bool | 是否启用白名单 | false |
| `blacklist_enabled` | bool | 是否启用黑名单 | true |
| `whitelist` | list | SQL白名单列表 | [] |
| `blacklist` | list | SQL黑名单列表 | ["DROP", "TRUNCATE", "ALTER", "CREATE"] |

## 配置示例

### 基本配置

```python
from trae_mysql_mcp import TraeMySQLMCP, DataSourceConfig

# 方法1: 环境变量配置
mcp = TraeMySQLMCP()

# 方法2: 代码配置
config = DataSourceConfig(
    name="default",
    host="localhost",
    port=3306,
    user="root",
    password="password",
    database="test_db"
)
mcp.add_data_source(config)

# 方法3: 配置文件
mcp = TraeMySQLMCP(config_file='config.json5')
```

### 多数据源配置

```json5
{
  "data_sources": {
    "master": {
      "host": "master_db",
      "port": 3306,
      "user": "root",
      "password": "master_password",
      "database": "production",
      "pool_min_size": 5,
      "pool_max_size": 20
    },
    "slave": {
      "host": "slave_db",
      "port": 3306,
      "user": "readonly",
      "password": "slave_password",
      "database": "production",
      "pool_min_size": 10,
      "pool_max_size": 30
    }
  }
}
```

```python
# 使用主库
mcp.connect('master')
mcp.execute('INSERT INTO users VALUES (1, "user1")')

# 使用从库
mcp.connect('slave')
result = mcp.execute('SELECT * FROM users')
```

## 安全配置最佳实践

### 生产环境配置

```json5
{
  "security": {
    "whitelist_enabled": true,
    "blacklist_enabled": true,
    "whitelist": ["SELECT", "INSERT", "UPDATE", "DELETE"],
    "blacklist": [
      "DROP", "TRUNCATE", "ALTER", "CREATE",
      "GRANT", "REVOKE", "FLUSH", "RESET"
    ]
  }
}
```

### 开发环境配置

```json5
{
  "security": {
    "whitelist_enabled": false,
    "blacklist_enabled": false
  }
}
```

## 配置加密

TraeMySQLMCP 会自动加密存储密码，确保配置文件中的密码安全：

1. 首次添加数据源时，密码会被自动加密
2. 从配置文件加载时，密码会在运行时自动解密
3. 保存配置时，密码会以加密形式存储

## 注意事项

1. **加密密钥安全**：加密密钥应妥善保管，建议通过环境变量设置
2. **连接池大小**：根据服务器资源和并发需求调整连接池大小
3. **超时设置**：合理设置SQL执行超时时间，避免长时间阻塞
4. **安全配置**：生产环境建议启用SQL白名单和黑名单
5. **配置文件权限**：确保配置文件权限设置正确，避免敏感信息泄露
