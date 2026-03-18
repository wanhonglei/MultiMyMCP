"""
MultiMyMCP - 生产级 MySQL 多数据源 MCP 工具

版本: 1.0.0
作者: TraeMCP Team
适配环境: TRAE CN IDE

核心功能:
- 增强型连接池管理
- 数据源配置加密存储
- SQL 执行超时控制
- 连接池状态监控
- SQL 白名单/黑名单机制
"""

__version__ = "1.0.0"
__author__ = "TraeMCP Team"
__all__ = ["MultiMyMCP", "DataSourceConfig", "ConnectionPool", "SQLExecutor", "Monitor"]

from multimymcp.core import MultiMyMCP
from multimymcp.config import DataSourceConfig
from multimymcp.pool import ConnectionPool
from multimymcp.executor import SQLExecutor
from multimymcp.monitor import Monitor
