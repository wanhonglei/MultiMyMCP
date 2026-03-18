"""
核心MCP接口测试
"""

import pytest
import tempfile
import os
from multimymcp import MultiMyMCP, DataSourceConfig
from multimymcp.exceptions import DataSourceNotFoundError, ConfigurationError


def test_mcp_basic():
    """测试MCP基本功能"""
    mcp = MultiMyMCP()
    
    # 添加数据源
    config = DataSourceConfig(
        name="test_ds",
        host="localhost",
        port=3306,
        user="test_user",
        password="test_password",
        database="test_db"
    )
    mcp.add_data_source(config)
    
    # 列出数据源
    datasources = mcp.list_data_sources()
    assert "test_ds" in datasources


def test_mcp_config_file():
    """测试配置文件功能"""
    mcp = MultiMyMCP()
    
    # 添加数据源
    config = DataSourceConfig(
        name="test_ds",
        host="localhost",
        port=3306,
        user="test_user",
        password="test_password",
        database="test_db"
    )
    mcp.add_data_source(config)
    
    # 保存到临时文件
    with tempfile.NamedTemporaryFile(suffix=".json5", delete=False) as f:
        temp_file = f.name
    
    try:
        mcp.save_config(temp_file)
        
        # 重新加载
        new_mcp = MultiMyMCP(temp_file)
        datasources = new_mcp.list_data_sources()
        assert "test_ds" in datasources
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)


def test_mcp_context_manager():
    """测试上下文管理器"""
    with MultiMyMCP() as mcp:
        # 添加数据源
        config = DataSourceConfig(
            name="test_ds",
            host="localhost",
            port=3306,
            user="test_user",
            password="test_password",
            database="test_db"
        )
        mcp.add_data_source(config)
        
        # 上下文退出时会自动断开连接
        pass


def test_mcp_error_handling():
    """测试错误处理"""
    mcp = MultiMyMCP()
    
    # 尝试连接不存在的数据源
    with pytest.raises(DataSourceNotFoundError):
        mcp.connect("non_existent")
    
    # 未选择数据源时执行SQL
    with pytest.raises(ConfigurationError):
        mcp.execute("SELECT * FROM users")
