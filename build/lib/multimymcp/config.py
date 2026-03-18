"""
配置管理模块

支持多数据源配置、环境变量配置、JSON5配置文件
配置加密存储,运行时解密
"""

import os
import json5
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv
from multimymcp.encryption import EncryptionUtil
from multimymcp.exceptions import ConfigurationError


@dataclass
class DataSourceConfig:
    """
    数据源配置类
    
    Attributes:
        name: 数据源名称
        host: 数据库主机地址
        port: 数据库端口
        user: 数据库用户名
        password: 数据库密码(加密存储)
        database: 数据库名称
        pool_min_size: 连接池最小连接数
        pool_max_size: 连接池最大连接数
        pool_timeout: 连接池超时时间(秒)
        sql_timeout: SQL执行超时时间(秒)
        charset: 字符集
        autocommit: 是否自动提交
        encrypted: 密码是否已加密
    """
    name: str
    host: str
    port: int
    user: str
    password: str
    database: str
    pool_min_size: int = 2
    pool_max_size: int = 10
    pool_timeout: int = 30
    sql_timeout: int = 60
    charset: str = "utf8mb4"
    autocommit: bool = False
    encrypted: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        return {
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "pool_min_size": self.pool_min_size,
            "pool_max_size": self.pool_max_size,
            "pool_timeout": self.pool_timeout,
            "sql_timeout": self.sql_timeout,
            "charset": self.charset,
            "autocommit": self.autocommit,
            "encrypted": self.encrypted,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataSourceConfig":
        """
        从字典创建配置对象
        
        Args:
            data: 配置字典
            
        Returns:
            DataSourceConfig: 配置对象
        """
        return cls(**data)


@dataclass
class SecurityConfig:
    """
    安全配置类
    
    Attributes:
        whitelist_enabled: 是否启用白名单
        blacklist_enabled: 是否启用黑名单
        whitelist: SQL白名单列表
        blacklist: SQL黑名单列表
    """
    whitelist_enabled: bool = False
    blacklist_enabled: bool = True
    whitelist: list = field(default_factory=list)
    blacklist: list = field(default_factory=lambda: ["DROP", "TRUNCATE", "ALTER", "CREATE"])
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            Dict[str, Any]: 配置字典
        """
        return {
            "whitelist_enabled": self.whitelist_enabled,
            "blacklist_enabled": self.blacklist_enabled,
            "whitelist": self.whitelist,
            "blacklist": self.blacklist,
        }


class ConfigManager:
    """
    配置管理器
    
    管理多数据源配置、安全配置、加密配置等
    支持从环境变量、JSON5文件加载配置
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            encryption_key: 加密密钥(可选,默认从环境变量读取)
        """
        load_dotenv()
        
        self.encryption_key = encryption_key or os.getenv("MYSQL_ENCRYPTION_KEY")
        if not self.encryption_key:
            self.encryption_key = EncryptionUtil.generate_key()
        
        self.encryption = EncryptionUtil(self.encryption_key)
        self.data_sources: Dict[str, DataSourceConfig] = {}
        self.security_config = SecurityConfig()
        self._load_from_env()
    
    def _load_from_env(self):
        """
        从环境变量加载配置
        """
        host = os.getenv("MYSQL_HOST")
        if host:
            config = DataSourceConfig(
                name="default",
                host=host,
                port=int(os.getenv("MYSQL_PORT", "3306")),
                user=os.getenv("MYSQL_USER", "root"),
                password=os.getenv("MYSQL_PASSWORD", ""),
                database=os.getenv("MYSQL_DATABASE", ""),
                pool_min_size=int(os.getenv("MYSQL_POOL_MIN_SIZE", "2")),
                pool_max_size=int(os.getenv("MYSQL_POOL_MAX_SIZE", "10")),
                pool_timeout=int(os.getenv("MYSQL_POOL_TIMEOUT", "30")),
                sql_timeout=int(os.getenv("MYSQL_SQL_TIMEOUT", "60")),
            )
            self.add_data_source(config)
        
        self.security_config.whitelist_enabled = (
            os.getenv("MYSQL_WHITELIST_ENABLED", "false").lower() == "true"
        )
        self.security_config.blacklist_enabled = (
            os.getenv("MYSQL_BLACKLIST_ENABLED", "true").lower() == "true"
        )
        
        blacklist_str = os.getenv("MYSQL_BLACKLIST", "")
        if blacklist_str:
            self.security_config.blacklist = blacklist_str.split(",")
    
    def load_from_file(self, file_path: str):
        """
        从JSON5文件加载配置
        
        Args:
            file_path: 配置文件路径
            
        Raises:
            ConfigurationError: 配置文件不存在或格式错误
        """
        path = Path(file_path)
        if not path.exists():
            raise ConfigurationError(f"配置文件不存在: {file_path}")
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                config_data = json5.load(f)
            
            if "data_sources" in config_data:
                for ds_name, ds_config in config_data["data_sources"].items():
                    ds_config["name"] = ds_name
                    config = DataSourceConfig.from_dict(ds_config)
                    self.add_data_source(config)
            
            if "security" in config_data:
                security_data = config_data["security"]
                self.security_config = SecurityConfig(**security_data)
                
        except Exception as e:
            raise ConfigurationError(f"配置文件解析失败: {str(e)}")
    
    def add_data_source(self, config: DataSourceConfig, encrypt: bool = True):
        """
        添加数据源配置
        
        Args:
            config: 数据源配置对象
            encrypt: 是否加密密码
        """
        if encrypt and not config.encrypted:
            config.password = self.encryption.encrypt(config.password)
            config.encrypted = True
        
        self.data_sources[config.name] = config
    
    def get_data_source(self, name: str) -> Optional[DataSourceConfig]:
        """
        获取数据源配置
        
        Args:
            name: 数据源名称
            
        Returns:
            Optional[DataSourceConfig]: 数据源配置对象
        """
        config = self.data_sources.get(name)
        if config and config.encrypted:
            config.password = self.encryption.decrypt(config.password)
            config.encrypted = False
        return config
    
    def remove_data_source(self, name: str) -> bool:
        """
        移除数据源配置
        
        Args:
            name: 数据源名称
            
        Returns:
            bool: 是否成功移除
        """
        if name in self.data_sources:
            del self.data_sources[name]
            return True
        return False
    
    def list_data_sources(self) -> list:
        """
        列出所有数据源名称
        
        Returns:
            list: 数据源名称列表
        """
        return list(self.data_sources.keys())
    
    def save_to_file(self, file_path: str):
        """
        保存配置到JSON5文件
        
        Args:
            file_path: 配置文件路径
        """
        config_data = {
            "data_sources": {
                name: config.to_dict() for name, config in self.data_sources.items()
            },
            "security": self.security_config.to_dict(),
        }
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json5.dump(config_data, f, indent=2, ensure_ascii=False)
    
    def get_security_config(self) -> SecurityConfig:
        """
        获取安全配置
        
        Returns:
            SecurityConfig: 安全配置对象
        """
        return self.security_config
    
    def update_security_config(self, **kwargs):
        """
        更新安全配置
        
        Args:
            **kwargs: 安全配置参数
        """
        for key, value in kwargs.items():
            if hasattr(self.security_config, key):
                setattr(self.security_config, key, value)
