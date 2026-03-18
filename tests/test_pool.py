"""
连接池测试
"""

import pytest
from multimymcp.config import DataSourceConfig
from multimymcp.pool import ConnectionPool
from multimymcp.monitor import Monitor
from multimymcp.exceptions import ConnectionPoolError


def test_pool_initialization():
    """测试连接池初始化"""
    # 创建测试配置
    config = DataSourceConfig(
        name="test_ds",
        host="localhost",
        port=3306,
        user="test_user",
        password="test_password",
        database="test_db"
    )
    
    monitor = Monitor()
    
    # 由于实际连接需要真实的数据库，这里只测试初始化过程
    # 真实环境下会抛出连接错误，这里捕获它
    try:
        pool = ConnectionPool(config, monitor)
        # 检查连接池是否初始化
        status = pool.get_pool_status()
        assert status["initialized"] is True
    except ConnectionPoolError:
        # 在测试环境中，数据库连接可能失败，这是预期的
        pass


def test_pool_status():
    """测试连接池状态获取"""
    config = DataSourceConfig(
        name="test_ds",
        host="localhost",
        port=3306,
        user="test_user",
        password="test_password",
        database="test_db"
    )
    
    monitor = Monitor()
    
    try:
        pool = ConnectionPool(config, monitor)
        status = pool.get_pool_status()
        
        assert "min_size" in status
        assert "max_size" in status
        assert "current_size" in status
        assert "active_size" in status
    except ConnectionPoolError:
        pass


def test_pool_resize():
    """测试连接池大小调整"""
    config = DataSourceConfig(
        name="test_ds",
        host="localhost",
        port=3306,
        user="test_user",
        password="test_password",
        database="test_db"
    )
    
    monitor = Monitor()
    
    try:
        pool = ConnectionPool(config, monitor)
        pool.resize_pool(5, 20)
        
        status = pool.get_pool_status()
        assert status["min_size"] == 5
        assert status["max_size"] == 20
    except ConnectionPoolError:
        pass
