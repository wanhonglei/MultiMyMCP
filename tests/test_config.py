"""
配置管理测试
"""

import pytest
import tempfile
import os
from multimymcp.config import ConfigManager, DataSourceConfig
from multimymcp.exceptions import ConfigurationError


def test_config_basic():
    """测试基本配置管理"""
    config_manager = ConfigManager()
    
    # 添加数据源
    config = DataSourceConfig(
        name="test_ds",
        host="localhost",
        port=3306,
        user="test_user",
        password="test_password",
        database="test_db"
    )
    config_manager.add_data_source(config)
    
    # 获取数据源
    retrieved_config = config_manager.get_data_source("test_ds")
    assert retrieved_config is not None
    assert retrieved_config.name == "test_ds"
    assert retrieved_config.host == "localhost"


def test_config_file():
    """测试配置文件加载和保存"""
    config_manager = ConfigManager()
    
    # 添加数据源
    config = DataSourceConfig(
        name="test_ds",
        host="localhost",
        port=3306,
        user="test_user",
        password="test_password",
        database="test_db"
    )
    config_manager.add_data_source(config)
    
    # 保存到临时文件
    with tempfile.NamedTemporaryFile(suffix=".json5", delete=False) as f:
        temp_file = f.name
    
    try:
        config_manager.save_to_file(temp_file)
        
        # 重新加载
        new_config_manager = ConfigManager()
        new_config_manager.load_from_file(temp_file)
        
        assert "test_ds" in new_config_manager.list_data_sources()
        retrieved_config = new_config_manager.get_data_source("test_ds")
        assert retrieved_config is not None
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)


def test_config_security():
    """测试安全配置"""
    config_manager = ConfigManager()
    
    # 更新安全配置
    config_manager.update_security_config(
        whitelist_enabled=True,
        blacklist_enabled=True,
        whitelist=["SELECT", "INSERT"],
        blacklist=["DROP", "TRUNCATE"]
    )
    
    security_config = config_manager.get_security_config()
    assert security_config.whitelist_enabled is True
    assert security_config.blacklist_enabled is True
    assert "SELECT" in security_config.whitelist
    assert "DROP" in security_config.blacklist
