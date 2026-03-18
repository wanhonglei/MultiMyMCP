"""
SQL执行器模块

提供SQL执行、超时控制、事务管理、安全检查功能
"""

import re
import time
import signal
import threading
from datetime import datetime, date, time as time_type, timedelta
from decimal import Decimal
from uuid import UUID
from typing import Optional, List, Dict, Any, Tuple, Callable
from contextlib import contextmanager
import pymysql
from multimymcp.pool import ConnectionPool, ConnectionWrapper
from multimymcp.config import SecurityConfig
from multimymcp.exceptions import SQLExecutionError, TimeoutError, SecurityError
from multimymcp.monitor import Monitor


def _serialize_value(value: Any) -> Any:
    """
    将值转换为 JSON 可序列化的格式
    
    Args:
        value: 原始值
        
    Returns:
        Any: 可序列化的值
    """
    if value is None:
        return None
    if isinstance(value, (datetime, date, time_type)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.decode('utf-8', errors='replace')
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (set, frozenset)):
        return list(value)
    return value


def _serialize_row(row: Tuple) -> List:
    """
    将行数据转换为 JSON 可序列化的格式
    
    Args:
        row: 原始行数据
        
    Returns:
        List: 可序列化的行数据
    """
    if row is None:
        return None
    return [_serialize_value(value) for value in row]


def _serialize_result(result: List[Tuple]) -> List[List]:
    """
    将查询结果转换为 JSON 可序列化的格式
    
    Args:
        result: 原始查询结果
        
    Returns:
        List[List]: 可序列化的结果
    """
    if result is None:
        return None
    return [_serialize_row(row) for row in result]


class SQLExecutor:
    """
    SQL执行器
    
    提供安全的SQL执行功能
    支持超时控制、事务管理、SQL安全检查
    """
    
    def __init__(
        self,
        connection_pool: ConnectionPool,
        security_config: SecurityConfig,
        monitor: Optional[Monitor] = None,
    ):
        """
        初始化SQL执行器
        
        Args:
            connection_pool: 连接池实例
            security_config: 安全配置
            monitor: 监控器实例(可选)
        """
        self.pool = connection_pool
        self.security_config = security_config
        self.monitor = monitor or Monitor()
        self._connection: Optional[ConnectionWrapper] = None
        self._in_transaction = False
        self._hooks: Dict[str, List[Callable]] = {
            "before_execute": [],
            "after_execute": [],
            "on_error": [],
        }
    
    def register_hook(self, hook_type: str, hook_func: Callable):
        """
        注册钩子函数
        
        Args:
            hook_type: 钩子类型(before_execute, after_execute, on_error)
            hook_func: 钩子函数
        """
        if hook_type in self._hooks:
            self._hooks[hook_type].append(hook_func)
    
    def _execute_hooks(self, hook_type: str, *args, **kwargs):
        """
        执行钩子函数
        
        Args:
            hook_type: 钩子类型
            *args: 位置参数
            **kwargs: 关键字参数
        """
        for hook_func in self._hooks.get(hook_type, []):
            try:
                hook_func(*args, **kwargs)
            except Exception as e:
                self.monitor.logger.error(f"钩子函数执行失败: {str(e)}")
    
    def _check_sql_security(self, sql: str) -> Tuple[bool, str]:
        """
        检查SQL安全性
        
        Args:
            sql: SQL语句
            
        Returns:
            Tuple[bool, str]: (是否通过, 错误信息)
        """
        sql_stripped = sql.strip()
        sql_upper = sql_stripped.upper()
        
        sql_no_comments = re.sub(r'--[^\n]*|/\*.*?\*/', '', sql_upper, flags=re.DOTALL)
        
        if self.security_config.blacklist_enabled:
            for keyword in self.security_config.blacklist:
                keyword_upper = keyword.upper()
                pattern = r'\b' + re.escape(keyword_upper) + r'\b'
                if re.search(pattern, sql_no_comments):
                    return False, f"SQL包含黑名单关键字: {keyword}"
        
        if self.security_config.whitelist_enabled:
            allowed = False
            for keyword in self.security_config.whitelist:
                keyword_upper = keyword.upper()
                pattern = r'\b' + re.escape(keyword_upper) + r'\b'
                if re.search(pattern, sql_no_comments):
                    allowed = True
                    break
            
            if not allowed:
                return False, "SQL不在白名单中"
        
        return True, ""
    
    @contextmanager
    def _timeout_context(self, timeout: int):
        """
        超时上下文管理器
        
        注意：超时控制主要通过 pymysql 的 read_timeout 和 write_timeout 参数实现
        此上下文管理器仅用于主线程的额外超时保护
        
        Args:
            timeout: 超时时间(秒)
        """
        def timeout_handler(signum, frame):
            raise TimeoutError(f"SQL执行超时: {timeout}秒")
        
        if threading.current_thread() is threading.main_thread():
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)
            try:
                yield
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        else:
            yield
    
    def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        执行SQL语句
        
        Args:
            sql: SQL语句
            params: 参数元组(可选)
            timeout: 超时时间(秒,可选)
            
        Returns:
            Dict[str, Any]: 执行结果
            
        Raises:
            SecurityError: SQL安全检查失败
            TimeoutError: 执行超时
            SQLExecutionError: 执行失败
        """
        is_safe, error_msg = self._check_sql_security(sql)
        if not is_safe:
            raise SecurityError(error_msg)
        
        self._execute_hooks("before_execute", sql, params)
        
        timeout = timeout or self.pool.config.sql_timeout
        connection = None
        cursor = None
        
        try:
            with self._timeout_context(timeout):
                start_time = time.time()
                
                connection = self.pool.get_connection()
                cursor = connection.cursor()
                
                cursor.execute(sql, params)
                
                if cursor.description is not None:
                    result = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    affected_rows = len(result)
                else:
                    result = None
                    columns = []
                    affected_rows = cursor.rowcount
                
                if not self._in_transaction:
                    connection.connection.commit()
                
                execution_time = time.time() - start_time
                
                self.monitor.record_sql_execution(sql, execution_time, True)
                
                self._execute_hooks("after_execute", sql, params, result)
                
                return {
                    "success": True,
                    "data": _serialize_result(result),
                    "columns": columns,
                    "affected_rows": affected_rows,
                    "execution_time": execution_time,
                }
        
        except TimeoutError as e:
            self.monitor.record_sql_execution(sql, 0, False, str(e))
            self._execute_hooks("on_error", sql, params, e)
            raise
        
        except Exception as e:
            if connection and not self._in_transaction:
                connection.connection.rollback()
            
            self.monitor.record_sql_execution(sql, 0, False, str(e))
            self._execute_hooks("on_error", sql, params, e)
            
            raise SQLExecutionError(f"SQL执行失败: {str(e)}")
        
        finally:
            if cursor:
                cursor.close()
            if connection and not self._in_transaction:
                self.pool.release_connection(connection.connection_id)
    
    def execute_many(
        self,
        sql: str,
        params_list: List[Tuple],
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        批量执行SQL语句
        
        Args:
            sql: SQL语句
            params_list: 参数列表
            timeout: 超时时间(秒,可选)
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        is_safe, error_msg = self._check_sql_security(sql)
        if not is_safe:
            raise SecurityError(error_msg)
        
        self._execute_hooks("before_execute", sql, params_list)
        
        timeout = timeout or self.pool.config.sql_timeout
        connection = None
        cursor = None
        
        try:
            with self._timeout_context(timeout):
                start_time = time.time()
                
                connection = self.pool.get_connection()
                cursor = connection.cursor()
                
                cursor.executemany(sql, params_list)
                
                affected_rows = cursor.rowcount
                
                if not self._in_transaction:
                    connection.connection.commit()
                
                execution_time = time.time() - start_time
                
                self.monitor.record_sql_execution(sql, execution_time, True)
                
                self._execute_hooks("after_execute", sql, params_list, affected_rows)
                
                return {
                    "success": True,
                    "affected_rows": affected_rows,
                    "execution_time": execution_time,
                }
        
        except Exception as e:
            if connection and not self._in_transaction:
                connection.connection.rollback()
            
            self.monitor.record_sql_execution(sql, 0, False, str(e))
            self._execute_hooks("on_error", sql, params_list, e)
            
            raise SQLExecutionError(f"批量执行失败: {str(e)}")
        
        finally:
            if cursor:
                cursor.close()
            if connection and not self._in_transaction:
                self.pool.release_connection(connection.connection_id)
    
    def begin_transaction(self):
        """
        开始事务
        """
        if self._in_transaction:
            raise SQLExecutionError("事务已开始")
        
        self._connection = self.pool.get_connection()
        self._connection.connection.begin()
        self._in_transaction = True
    
    def commit_transaction(self):
        """
        提交事务
        """
        if not self._in_transaction:
            raise SQLExecutionError("未开始事务")
        
        try:
            self._connection.connection.commit()
        finally:
            self.pool.release_connection(self._connection.connection_id)
            self._connection = None
            self._in_transaction = False
    
    def rollback_transaction(self):
        """
        回滚事务
        """
        if not self._in_transaction:
            raise SQLExecutionError("未开始事务")
        
        try:
            self._connection.connection.rollback()
        finally:
            self.pool.release_connection(self._connection.connection_id)
            self._connection = None
            self._in_transaction = False
    
    @contextmanager
    def transaction(self):
        """
        事务上下文管理器
        
        用法:
            with executor.transaction():
                executor.execute("INSERT INTO ...")
                executor.execute("UPDATE ...")
        """
        self.begin_transaction()
        try:
            yield
            self.commit_transaction()
        except Exception:
            self.rollback_transaction()
            raise
    
    def execute_in_transaction(
        self,
        sql_list: List[Tuple[str, Optional[Tuple]]],
    ) -> List[Dict[str, Any]]:
        """
        在事务中执行多条SQL
        
        Args:
            sql_list: SQL列表,每项为(sql, params)元组
            
        Returns:
            List[Dict[str, Any]]: 执行结果列表
        """
        results = []
        
        with self.transaction():
            for sql, params in sql_list:
                result = self.execute(sql, params)
                results.append(result)
        
        return results
