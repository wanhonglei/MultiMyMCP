# 性能优化指南

## 连接池优化

### 连接池大小调优

连接池大小应根据服务器资源和并发需求进行调整：

- **最小连接数**：设置为应用的基础并发数，建议 2-5 个
- **最大连接数**：根据服务器 CPU 核心数和内存情况，建议不超过 20 个
- **超时设置**：根据业务特点设置合理的超时时间

```python
# 推荐配置
config = DataSourceConfig(
    # 其他配置...
    pool_min_size=5,      # 基础并发数
    pool_max_size=15,     # 最大并发数
    pool_timeout=30,      # 连接池超时(秒)
    sql_timeout=60        # SQL执行超时(秒)
)
```

### 动态调整连接池

根据系统负载动态调整连接池大小：

```python
import psutil

# 监控系统负载
def adjust_pool_size(mcp, datasource):
    cpu_usage = psutil.cpu_percent()
    memory_usage = psutil.virtual_memory().percent
    
    if cpu_usage > 80 or memory_usage > 80:
        # 高负载时减少连接数
        mcp.resize_pool(5, 10, datasource)
    elif cpu_usage < 30 and memory_usage < 30:
        # 低负载时增加连接数
        mcp.resize_pool(5, 20, datasource)
```

## SQL 执行优化

### 1. 使用参数化查询

避免 SQL 注入，提高执行效率：

```python
# 推荐
result = mcp.execute(
    "SELECT * FROM users WHERE id = %s",
    (user_id,)
)

# 不推荐
result = mcp.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

### 2. 批量执行

对于批量操作，使用 `execute_many` 提高性能：

```python
# 批量插入
params_list = [(1, "user1"), (2, "user2"), (3, "user3")]
result = mcp.execute_many(
    "INSERT INTO users (id, name) VALUES (%s, %s)",
    params_list
)
```

### 3. 事务优化

对于多个相关操作，使用事务减少网络开销：

```python
# 使用事务
sql_list = [
    ("INSERT INTO orders (user_id, amount) VALUES (%s, %s)", (1, 100)),
    ("UPDATE users SET balance = balance - %s WHERE id = %s", (100, 1)),
]
results = mcp.execute_in_transaction(sql_list)

# 或使用上下文管理器
with mcp._executors['default'].transaction():
    mcp.execute("INSERT INTO orders (user_id, amount) VALUES (1, 100)")
    mcp.execute("UPDATE users SET balance = balance - 100 WHERE id = 1")
```

### 4. 索引优化

确保 SQL 查询使用正确的索引：

- 为频繁查询的列创建索引
- 避免在 WHERE 子句中使用函数
- 合理使用复合索引

### 5. 结果集大小控制

限制返回结果集大小，避免内存溢出：

```python
# 分页查询
page_size = 100
page = 1
offset = (page - 1) * page_size

result = mcp.execute(
    "SELECT * FROM users LIMIT %s OFFSET %s",
    (page_size, offset)
)
```

## 监控与调优

### 1. 监控连接池状态

定期监控连接池状态，及时发现问题：

```python
status = mcp.get_pool_status()
print(f"当前连接数: {status['current_size']}")
print(f"活跃连接数: {status['active_size']}")
print(f"空闲连接数: {status['idle_size']}")
```

### 2. 性能报告分析

定期生成性能报告，分析 SQL 执行情况：

```python
report = mcp.get_performance_report()
print(f"总执行次数: {report['summary']['total_sql_executions']}")
print(f"成功率: {report['summary']['success_rate']:.2f}%")
print(f"平均执行时间: {report['summary']['avg_execution_time']:.3f}s")

# 分析慢查询
slow_queries = report['performance_indicators']['slow_queries']
print(f"慢查询数量: {slow_queries}")
```

### 3. 健康检查

定期进行健康检查，确保系统正常运行：

```python
health = mcp.get_health_status()
if health['healthy']:
    print("系统健康状态良好")
else:
    print("系统存在问题:")
    for issue in health['issues']:
        print(f"- {issue}")
```

## 高并发场景优化

### 1. 连接池隔离

为不同业务场景创建独立的连接池：

```python
# 为读操作创建专用连接池
read_config = DataSourceConfig(
    name="read_pool",
    host="read_db",
    port=3306,
    user="readonly",
    password="password",
    database="test_db",
    pool_min_size=10,
    pool_max_size=30
)

# 为写操作创建专用连接池
write_config = DataSourceConfig(
    name="write_pool",
    host="write_db",
    port=3306,
    user="root",
    password="password",
    database="test_db",
    pool_min_size=5,
    pool_max_size=15
)

mcp.add_data_source(read_config)
mcp.add_data_source(write_config)
```

### 2. 异步执行

对于非关键操作，使用异步执行提高并发性能：

```python
import threading

def async_execute(mcp, sql, params):
    def _execute():
        try:
            mcp.execute(sql, params)
        except Exception as e:
            print(f"异步执行失败: {e}")
    
    thread = threading.Thread(target=_execute)
    thread.daemon = True
    thread.start()

# 异步执行非关键操作
async_execute(mcp, "INSERT INTO logs (message) VALUES (%s)", ("操作日志",))
```

### 3. 缓存策略

对于频繁查询的数据，使用缓存减少数据库访问：

```python
import functools
import time

def cached(timeout=300):
    def decorator(func):
        cache = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            now = time.time()
            
            if key in cache and now - cache[key]['time'] < timeout:
                return cache[key]['value']
            
            result = func(*args, **kwargs)
            cache[key] = {'value': result, 'time': now}
            return result
        
        return wrapper
    return decorator

@cached(timeout=60)
def get_user_info(mcp, user_id):
    result = mcp.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return result['data']
```

## 错误处理与重试

### 1. 连接失败重试

实现连接失败自动重试机制：

```python
def execute_with_retry(mcp, sql, params, max_retries=3, delay=1):
    for attempt in range(max_retries):
        try:
            return mcp.execute(sql, params)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(delay * (2 ** attempt))  # 指数退避
            continue
```

### 2. 超时处理

合理设置超时时间，避免长时间阻塞：

```python
# 为不同操作设置不同的超时时间
try:
    # 简单查询，短超时
    result = mcp.execute("SELECT * FROM users LIMIT 10", timeout=10)
except TimeoutError:
    print("查询超时")

try:
    # 复杂查询，较长超时
    result = mcp.execute("SELECT * FROM large_table", timeout=60)
except TimeoutError:
    print("查询超时")
```

## 资源管理

### 1. 连接释放

确保及时释放连接，避免连接泄漏：

```python
# 使用上下文管理器
with TraeMySQLMCP() as mcp:
    mcp.connect('default')
    result = mcp.execute('SELECT * FROM users')
# 自动释放连接

# 手动释放
mcp = TraeMySQLMCP()
try:
    mcp.connect('default')
    result = mcp.execute('SELECT * FROM users')
finally:
    mcp.disconnect_all()
```

### 2. 资源监控

监控系统资源使用情况：

```python
import psutil

def monitor_resources():
    while True:
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        print(f"CPU: {cpu}% | 内存: {memory}% | 磁盘: {disk}%")
        time.sleep(10)

# 启动监控线程
threading.Thread(target=monitor_resources, daemon=True).start()
```

## TRAE CN 环境优化

### 1. 适配 TRAE CN 资源限制

- **连接池大小**：根据 TRAE CN 分配的资源调整，建议最大连接数不超过 10
- **超时设置**：TRAE CN 环境中建议 SQL 执行超时不超过 30 秒
- **内存使用**：控制结果集大小，避免内存溢出

### 2. 日志配置

适配 TRAE CN 日志面板：

```python
import logging

# 配置日志
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

setup_logging()
```

### 3. 性能测试

在 TRAE CN 环境中进行性能测试：

```python
def performance_test(mcp, iterations=1000):
    start_time = time.time()
    success_count = 0
    
    for i in range(iterations):
        try:
            mcp.execute("SELECT 1")
            success_count += 1
        except Exception:
            pass
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"执行 {iterations} 次查询")
    print(f"成功: {success_count}")
    print(f"失败: {iterations - success_count}")
    print(f"总耗时: {duration:.2f}s")
    print(f"平均耗时: {duration / iterations:.4f}s")

# 运行性能测试
performance_test(mcp)
```

## 最佳实践总结

1. **连接池配置**：根据实际需求调整连接池大小
2. **SQL 优化**：使用参数化查询，批量执行，事务优化
3. **监控**：定期监控连接池状态和性能指标
4. **缓存**：合理使用缓存减少数据库访问
5. **错误处理**：实现重试机制和超时处理
6. **资源管理**：及时释放连接，监控系统资源
7. **TRA ECN 适配**：根据环境资源限制调整配置

通过以上优化措施，可以显著提高 TraeMySQLMCP 在 TRAE CN 环境中的性能和稳定性。
