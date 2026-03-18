"""
异常定义模块

定义所有自定义异常类
"""


class TraeMCPError(Exception):
    """TraeMCP基础异常类"""
    pass


class ConfigurationError(TraeMCPError):
    """配置错误异常"""
    pass


class ConnectionPoolError(TraeMCPError):
    """连接池错误异常"""
    pass


class SQLExecutionError(TraeMCPError):
    """SQL执行错误异常"""
    pass


class TimeoutError(TraeMCPError):
    """超时异常"""
    pass


class SecurityError(TraeMCPError):
    """安全异常"""
    pass


class EncryptionError(TraeMCPError):
    """加密异常"""
    pass


class DataSourceNotFoundError(TraeMCPError):
    """数据源未找到异常"""
    pass


class ConnectionNotFoundError(TraeMCPError):
    """连接未找到异常"""
    pass
