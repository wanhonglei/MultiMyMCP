"""
连接池管理模块

基于DBUtils实现增强型连接池
支持动态扩容/缩容、连接监控、线程安全
"""

import time
import threading
from typing import Optional, Dict, Any
from datetime import datetime
import pymysql
from dbutils.pooled_db import PooledDB
from multimymcp.config import DataSourceConfig
from multimymcp.exceptions import ConnectionPoolError, ConnectionNotFoundError
from multimymcp.monitor import Monitor


class ConnectionWrapper:
    """
    连接包装器
    
    包装原始连接,记录使用时长和执行统计
    """
    
    def __init__(self, connection, connection_id: int, monitor: Monitor):
        """
        初始化连接包装器
        
        Args:
            connection: 原始数据库连接
            connection_id: 连接ID
            monitor: 监控器实例
        """
        self.connection = connection
        self.connection_id = connection_id
        self.monitor = monitor
        self.created_at = datetime.now()
        self.last_used_at = datetime.now()
        self.use_count = 0
        self._is_active = True
    
    def cursor(self, *args, **kwargs):
        """
        获取游标
        
        Returns:
            Cursor: 数据库游标
        """
        self.last_used_at = datetime.now()
        self.use_count += 1
        return self.connection.cursor(*args, **kwargs)
    
    def close(self):
        """
        关闭连接
        """
        if self._is_active:
            self._is_active = False
            self.connection.close()
    
    def is_active(self) -> bool:
        """
        检查连接是否活跃
        
        Returns:
            bool: 是否活跃
        """
        if not self._is_active:
            return False
        
        try:
            self.connection.ping(reconnect=True)
            return True
        except Exception:
            self._is_active = False
            return False
    
    def get_usage_duration(self) -> float:
        """
        获取连接使用时长(秒)
        
        Returns:
            float: 使用时长
        """
        return (datetime.now() - self.created_at).total_seconds()
    
    def get_idle_duration(self) -> float:
        """
        获取连接空闲时长(秒)
        
        Returns:
            float: 空闲时长
        """
        return (datetime.now() - self.last_used_at).total_seconds()


class ConnectionPool:
    """
    连接池管理类
    
    基于DBUtils实现,支持动态扩容/缩容
    线程安全,提供连接监控功能
    """
    
    def __init__(self, config: DataSourceConfig, monitor: Optional[Monitor] = None):
        """
        初始化连接池
        
        Args:
            config: 数据源配置
            monitor: 监控器实例(可选)
        """
        self.config = config
        self.monitor = monitor or Monitor()
        self._pool: Optional[PooledDB] = None
        self._connections: Dict[int, ConnectionWrapper] = {}
        self._connection_counter = 0
        self._lock = threading.RLock()
        self._initialized = False
        self._current_size = 0
        
        self._initialize_pool()
    
    def _initialize_pool(self):
        """
        初始化连接池
        
        Raises:
            ConnectionPoolError: 连接池初始化失败
        """
        try:
            self._pool = PooledDB(
                creator=pymysql,
                mincached=self.config.pool_min_size,
                maxcached=self.config.pool_max_size,
                maxconnections=self.config.pool_max_size,
                blocking=True,
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                charset=self.config.charset,
                autocommit=self.config.autocommit,
                connect_timeout=self.config.pool_timeout,
                read_timeout=self.config.sql_timeout,
                write_timeout=self.config.sql_timeout,
            )
            self._initialized = True
            self._current_size = self.config.pool_min_size
            self.monitor.record_pool_event("initialized", {
                "min_size": self.config.pool_min_size,
                "max_size": self.config.pool_max_size,
            })
        except Exception as e:
            raise ConnectionPoolError(f"连接池初始化失败: {str(e)}")
    
    def get_connection(self) -> ConnectionWrapper:
        """
        获取连接
        
        Returns:
            ConnectionWrapper: 连接包装器
            
        Raises:
            ConnectionPoolError: 获取连接失败
        """
        if not self._initialized:
            raise ConnectionPoolError("连接池未初始化")
        
        with self._lock:
            try:
                raw_connection = self._pool.connection()
                self._connection_counter += 1
                connection_id = self._connection_counter
                
                wrapper = ConnectionWrapper(raw_connection, connection_id, self.monitor)
                self._connections[connection_id] = wrapper
                
                self.monitor.record_pool_event("connection_acquired", {
                    "connection_id": connection_id,
                    "current_size": len(self._connections),
                })
                
                return wrapper
            except Exception as e:
                raise ConnectionPoolError(f"获取连接失败: {str(e)}")
    
    def release_connection(self, connection_id: int):
        """
        释放连接
        
        Args:
            connection_id: 连接ID
            
        Raises:
            ConnectionNotFoundError: 连接不存在
        """
        with self._lock:
            if connection_id not in self._connections:
                raise ConnectionNotFoundError(f"连接不存在: {connection_id}")
            
            wrapper = self._connections[connection_id]
            wrapper.close()
            del self._connections[connection_id]
            
            self.monitor.record_pool_event("connection_released", {
                "connection_id": connection_id,
                "use_count": wrapper.use_count,
                "usage_duration": wrapper.get_usage_duration(),
                "current_size": len(self._connections),
            })
    
    def resize_pool(self, min_size: int, max_size: int):
        """
        调整连接池大小(动态扩容/缩容)
        
        Args:
            min_size: 最小连接数
            max_size: 最大连接数
            
        Raises:
            ConnectionPoolError: 调整失败
        """
        if min_size < 1 or max_size < min_size:
            raise ConnectionPoolError("无效的连接池大小配置")
        
        with self._lock:
            old_min = self.config.pool_min_size
            old_max = self.config.pool_max_size
            
            self.config.pool_min_size = min_size
            self.config.pool_max_size = max_size
            
            self._initialize_pool()
            
            self.monitor.record_pool_event("pool_resized", {
                "old_min": old_min,
                "old_max": old_max,
                "new_min": min_size,
                "new_max": max_size,
            })
    
    def get_pool_status(self) -> Dict[str, Any]:
        """
        获取连接池状态
        
        Returns:
            Dict[str, Any]: 连接池状态信息
        """
        with self._lock:
            active_connections = [
                conn for conn in self._connections.values() if conn.is_active()
            ]
            
            return {
                "initialized": self._initialized,
                "min_size": self.config.pool_min_size,
                "max_size": self.config.pool_max_size,
                "current_size": len(self._connections),
                "active_size": len(active_connections),
                "idle_size": len(self._connections) - len(active_connections),
                "total_use_count": sum(conn.use_count for conn in self._connections.values()),
            }
    
    def cleanup_idle_connections(self, max_idle_time: int = 300):
        """
        清理空闲连接
        
        Args:
            max_idle_time: 最大空闲时间(秒)
        """
        with self._lock:
            idle_connection_ids = [
                conn_id for conn_id, conn in self._connections.items()
                if conn.get_idle_duration() > max_idle_time and len(self._connections) > self.config.pool_min_size
            ]
            
            for conn_id in idle_connection_ids:
                self.release_connection(conn_id)
            
            if idle_connection_ids:
                self.monitor.record_pool_event("idle_connections_cleaned", {
                    "count": len(idle_connection_ids),
                })
    
    def close_all(self):
        """
        关闭所有连接
        """
        with self._lock:
            for connection_id in list(self._connections.keys()):
                try:
                    self.release_connection(connection_id)
                except Exception:
                    pass
            
            if self._pool:
                self._pool.close()
            
            self._initialized = False
            self.monitor.record_pool_event("pool_closed", {})
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            Dict[str, Any]: 健康检查结果
        """
        status = self.get_pool_status()
        
        health_status = {
            "healthy": True,
            "status": status,
            "issues": [],
        }
        
        if not status["initialized"]:
            health_status["healthy"] = False
            health_status["issues"].append("连接池未初始化")
        
        if status["current_size"] >= status["max_size"]:
            health_status["issues"].append("连接池已满")
        
        active_ratio = status["active_size"] / max(status["current_size"], 1)
        if active_ratio > 0.9:
            health_status["issues"].append("连接使用率过高")
        
        if health_status["issues"]:
            health_status["healthy"] = False
        
        return health_status
