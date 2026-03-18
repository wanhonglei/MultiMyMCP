"""
核心MCP接口模块

提供统一的MySQL多数据源管理接口
适配TRAE CN IDE环境
"""

import threading
from typing import Optional, Dict, Any, List, Callable
from multimymcp.config import ConfigManager, DataSourceConfig
from multimymcp.pool import ConnectionPool
from multimymcp.executor import SQLExecutor
from multimymcp.monitor import Monitor
from multimymcp.exceptions import (
    ConfigurationError,
    ConnectionPoolError,
    DataSourceNotFoundError,
    SQLExecutionError,
    SecurityError,
    TimeoutError,
)


class MultiMyMCP:
    """
    MultiMyMCP核心类
    
    提供多数据源管理、连接池管理、SQL执行等功能
    完全适配TRAE CN IDE环境
    """
    
    def __init__(self, config_file: Optional[str] = None, encryption_key: Optional[str] = None):
        """
        初始化MultiMyMCP
        
        Args:
            config_file: 配置文件路径(可选)
            encryption_key: 加密密钥(可选)
        """
        self._config_manager = ConfigManager(encryption_key)
        self._pools: Dict[str, ConnectionPool] = {}
        self._executors: Dict[str, SQLExecutor] = {}
        self._monitors: Dict[str, Monitor] = {}
        self._active_datasource: Optional[str] = None
        self._lock = threading.RLock()
        
        if config_file:
            self._config_manager.load_from_file(config_file)
    
    def connect(self, datasource_name: str = "default") -> bool:
        """
        连接到指定数据源
        
        Args:
            datasource_name: 数据源名称
            
        Returns:
            bool: 连接成功
            
        Raises:
            DataSourceNotFoundError: 数据源不存在
            ConnectionPoolError: 连接池创建失败
        """
        with self._lock:
            if datasource_name not in self._pools:
                config = self._config_manager.get_data_source(datasource_name)
                if not config:
                    raise DataSourceNotFoundError(f"数据源不存在: {datasource_name}")
                
                monitor = Monitor()
                pool = ConnectionPool(config, monitor)
                security_config = self._config_manager.get_security_config()
                executor = SQLExecutor(pool, security_config, monitor)
                
                self._pools[datasource_name] = pool
                self._executors[datasource_name] = executor
                self._monitors[datasource_name] = monitor
            
            self._active_datasource = datasource_name
            return True
    
    def disconnect(self, datasource_name: Optional[str] = None):
        """
        断开指定数据源连接
        
        Args:
            datasource_name: 数据源名称(可选,默认为当前活跃数据源)
        """
        with self._lock:
            target_ds = datasource_name or self._active_datasource
            if not target_ds:
                return
            
            if target_ds in self._pools:
                self._pools[target_ds].close_all()
                del self._pools[target_ds]
                del self._executors[target_ds]
                del self._monitors[target_ds]
            
            if self._active_datasource == target_ds:
                self._active_datasource = None
    
    def disconnect_all(self):
        """
        断开所有数据源连接
        """
        with self._lock:
            for datasource in list(self._pools.keys()):
                self.disconnect(datasource)
    
    def execute(
        self,
        sql: str,
        params: Optional[tuple] = None,
        datasource: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        执行SQL语句
        
        Args:
            sql: SQL语句
            params: 参数元组(可选)
            datasource: 数据源名称(可选,默认为当前活跃数据源)
            timeout: 超时时间(秒,可选)
            
        Returns:
            Dict[str, Any]: 执行结果
            
        Raises:
            SQLExecutionError: SQL执行失败
            SecurityError: SQL安全检查失败
            TimeoutError: 执行超时
        """
        target_ds = datasource or self._active_datasource
        if not target_ds:
            raise ConfigurationError("未选择数据源")
        
        if target_ds not in self._executors:
            self.connect(target_ds)
        
        executor = self._executors[target_ds]
        return executor.execute(sql, params, timeout)
    
    def execute_many(
        self,
        sql: str,
        params_list: List[tuple],
        datasource: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        批量执行SQL语句
        
        Args:
            sql: SQL语句
            params_list: 参数列表
            datasource: 数据源名称(可选,默认为当前活跃数据源)
            timeout: 超时时间(秒,可选)
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        target_ds = datasource or self._active_datasource
        if not target_ds:
            raise ConfigurationError("未选择数据源")
        
        if target_ds not in self._executors:
            self.connect(target_ds)
        
        executor = self._executors[target_ds]
        return executor.execute_many(sql, params_list, timeout)
    
    def execute_in_transaction(
        self,
        sql_list: List[tuple],
        datasource: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        在事务中执行多条SQL
        
        Args:
            sql_list: SQL列表,每项为(sql, params)元组
            datasource: 数据源名称(可选,默认为当前活跃数据源)
            
        Returns:
            List[Dict[str, Any]]: 执行结果列表
        """
        target_ds = datasource or self._active_datasource
        if not target_ds:
            raise ConfigurationError("未选择数据源")
        
        if target_ds not in self._executors:
            self.connect(target_ds)
        
        executor = self._executors[target_ds]
        return executor.execute_in_transaction(sql_list)
    
    def register_hook(
        self,
        hook_type: str,
        hook_func: Callable,
        datasource: Optional[str] = None,
    ):
        """
        注册钩子函数
        
        Args:
            hook_type: 钩子类型(before_execute, after_execute, on_error)
            hook_func: 钩子函数
            datasource: 数据源名称(可选,默认为当前活跃数据源)
        """
        target_ds = datasource or self._active_datasource
        if not target_ds:
            raise ConfigurationError("未选择数据源")
        
        if target_ds not in self._executors:
            self.connect(target_ds)
        
        executor = self._executors[target_ds]
        executor.register_hook(hook_type, hook_func)
    
    def get_pool_status(self, datasource: Optional[str] = None) -> Dict[str, Any]:
        """
        获取连接池状态
        
        Args:
            datasource: 数据源名称(可选,默认为当前活跃数据源)
            
        Returns:
            Dict[str, Any]: 连接池状态
        """
        target_ds = datasource or self._active_datasource
        if not target_ds:
            raise ConfigurationError("未选择数据源")
        
        if target_ds not in self._pools:
            self.connect(target_ds)
        
        pool = self._pools[target_ds]
        return pool.get_pool_status()
    
    def get_health_status(self, datasource: Optional[str] = None) -> Dict[str, Any]:
        """
        获取健康状态
        
        Args:
            datasource: 数据源名称(可选,默认为当前活跃数据源)
            
        Returns:
            Dict[str, Any]: 健康状态
        """
        target_ds = datasource or self._active_datasource
        if not target_ds:
            raise ConfigurationError("未选择数据源")
        
        if target_ds not in self._pools:
            self.connect(target_ds)
        
        pool = self._pools[target_ds]
        return pool.health_check()
    
    def get_performance_report(self, datasource: Optional[str] = None) -> Dict[str, Any]:
        """
        获取性能报告
        
        Args:
            datasource: 数据源名称(可选,默认为当前活跃数据源)
            
        Returns:
            Dict[str, Any]: 性能报告
        """
        target_ds = datasource or self._active_datasource
        if not target_ds:
            raise ConfigurationError("未选择数据源")
        
        if target_ds not in self._monitors:
            self.connect(target_ds)
        
        monitor = self._monitors[target_ds]
        return monitor.get_performance_report()
    
    def resize_pool(
        self,
        min_size: int,
        max_size: int,
        datasource: Optional[str] = None,
    ):
        """
        调整连接池大小
        
        Args:
            min_size: 最小连接数
            max_size: 最大连接数
            datasource: 数据源名称(可选,默认为当前活跃数据源)
        """
        target_ds = datasource or self._active_datasource
        if not target_ds:
            raise ConfigurationError("未选择数据源")
        
        if target_ds not in self._pools:
            self.connect(target_ds)
        
        pool = self._pools[target_ds]
        pool.resize_pool(min_size, max_size)
    
    def add_data_source(self, config: DataSourceConfig, encrypt: bool = True):
        """
        添加数据源
        
        Args:
            config: 数据源配置
            encrypt: 是否加密密码
        """
        self._config_manager.add_data_source(config, encrypt)
    
    def list_data_sources(self) -> List[str]:
        """
        列出所有数据源
        
        Returns:
            List[str]: 数据源名称列表
        """
        return self._config_manager.list_data_sources()
    
    def remove_data_source(self, name: str):
        """
        移除数据源
        
        Args:
            name: 数据源名称
        """
        self.disconnect(name)
        self._config_manager.remove_data_source(name)
    
    def save_config(self, file_path: str):
        """
        保存配置
        
        Args:
            file_path: 配置文件路径
        """
        self._config_manager.save_to_file(file_path)
    
    def load_config(self, file_path: str):
        """
        加载配置
        
        Args:
            file_path: 配置文件路径
        """
        self._config_manager.load_from_file(file_path)
    
    def get_security_config(self) -> Any:
        """
        获取安全配置
        
        Returns:
            Any: 安全配置
        """
        return self._config_manager.get_security_config()
    
    def update_security_config(self, **kwargs):
        """
        更新安全配置
        
        Args:
            **kwargs: 安全配置参数
        """
        self._config_manager.update_security_config(**kwargs)
    
    def __enter__(self):
        """
        上下文管理器入口
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器出口
        """
        self.disconnect_all()
