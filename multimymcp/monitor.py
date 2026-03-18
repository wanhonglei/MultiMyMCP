"""
监控模块

提供连接池状态监控、性能指标收集、日志记录功能
"""

import time
import logging
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
import json


class Monitor:
    """
    监控类
    
    收集和记录连接池性能指标
    提供可视化监控接口
    """
    
    def __init__(self, log_level: int = logging.INFO):
        """
        初始化监控器
        
        Args:
            log_level: 日志级别
        """
        self._lock = threading.RLock()
        self._events: List[Dict[str, Any]] = []
        self._metrics: Dict[str, Any] = defaultdict(list)
        self._counters: Dict[str, int] = defaultdict(int)
        self._timers: Dict[str, float] = {}
        
        self._setup_logger(log_level)
        self._max_events = 1000
    
    def _setup_logger(self, log_level: int):
        """
        设置日志记录器
        
        Args:
            log_level: 日志级别
        """
        self.logger = logging.getLogger("MultiMyMCP")
        self.logger.setLevel(log_level)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def record_pool_event(self, event_type: str, data: Dict[str, Any]):
        """
        记录连接池事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
        """
        with self._lock:
            event = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "data": data,
            }
            
            self._events.append(event)
            
            if len(self._events) > self._max_events:
                self._events.pop(0)
            
            self._counters[f"event_{event_type}"] += 1
            
            self.logger.info(f"Pool Event: {event_type} - {json.dumps(data)}")
    
    def record_sql_execution(
        self,
        sql: str,
        execution_time: float,
        success: bool,
        error: Optional[str] = None,
    ):
        """
        记录SQL执行
        
        Args:
            sql: SQL语句
            execution_time: 执行时间(秒)
            success: 是否成功
            error: 错误信息(可选)
        """
        with self._lock:
            sql_type = sql.strip().split()[0].upper() if sql else "UNKNOWN"
            
            metric = {
                "timestamp": datetime.now().isoformat(),
                "sql_type": sql_type,
                "execution_time": execution_time,
                "success": success,
                "error": error,
            }
            
            self._metrics["sql_executions"].append(metric)
            
            if len(self._metrics["sql_executions"]) > self._max_events:
                self._metrics["sql_executions"].pop(0)
            
            self._counters["sql_total"] += 1
            if success:
                self._counters["sql_success"] += 1
            else:
                self._counters["sql_failed"] += 1
            
            log_level = logging.INFO if success else logging.ERROR
            self.logger.log(
                log_level,
                f"SQL Execution: {sql_type} - Time: {execution_time:.3f}s - Success: {success}",
            )
    
    def start_timer(self, timer_name: str):
        """
        开始计时
        
        Args:
            timer_name: 计时器名称
        """
        with self._lock:
            self._timers[timer_name] = time.time()
    
    def stop_timer(self, timer_name: str) -> float:
        """
        停止计时
        
        Args:
            timer_name: 计时器名称
            
        Returns:
            float: 计时时长(秒)
        """
        with self._lock:
            if timer_name not in self._timers:
                return 0.0
            
            duration = time.time() - self._timers[timer_name]
            del self._timers[timer_name]
            
            self._metrics[f"timer_{timer_name}"].append({
                "timestamp": datetime.now().isoformat(),
                "duration": duration,
            })
            
            return duration
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        获取所有指标
        
        Returns:
            Dict[str, Any]: 指标数据
        """
        with self._lock:
            sql_metrics = self._metrics.get("sql_executions", [])
            
            avg_execution_time = 0.0
            if sql_metrics:
                total_time = sum(m["execution_time"] for m in sql_metrics)
                avg_execution_time = total_time / len(sql_metrics)
            
            return {
                "counters": dict(self._counters),
                "avg_sql_execution_time": avg_execution_time,
                "total_events": len(self._events),
                "total_sql_executions": len(sql_metrics),
            }
    
    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取最近的事件
        
        Args:
            limit: 返回事件数量
            
        Returns:
            List[Dict[str, Any]]: 事件列表
        """
        with self._lock:
            return self._events[-limit:]
    
    def get_sql_statistics(self) -> Dict[str, Any]:
        """
        获取SQL执行统计
        
        Returns:
            Dict[str, Any]: SQL统计信息
        """
        with self._lock:
            sql_metrics = self._metrics.get("sql_executions", [])
            
            if not sql_metrics:
                return {
                    "total": 0,
                    "success": 0,
                    "failed": 0,
                    "avg_time": 0.0,
                    "max_time": 0.0,
                    "min_time": 0.0,
                    "by_type": {},
                }
            
            by_type = defaultdict(lambda: {"count": 0, "total_time": 0.0})
            
            for metric in sql_metrics:
                sql_type = metric["sql_type"]
                by_type[sql_type]["count"] += 1
                by_type[sql_type]["total_time"] += metric["execution_time"]
            
            for sql_type in by_type:
                count = by_type[sql_type]["count"]
                by_type[sql_type]["avg_time"] = by_type[sql_type]["total_time"] / count
            
            execution_times = [m["execution_time"] for m in sql_metrics]
            
            return {
                "total": len(sql_metrics),
                "success": sum(1 for m in sql_metrics if m["success"]),
                "failed": sum(1 for m in sql_metrics if not m["success"]),
                "avg_time": sum(execution_times) / len(execution_times),
                "max_time": max(execution_times),
                "min_time": min(execution_times),
                "by_type": dict(by_type),
            }
    
    def clear_metrics(self):
        """
        清空所有指标
        """
        with self._lock:
            self._events.clear()
            self._metrics.clear()
            self._counters.clear()
    
    def export_metrics(self, format: str = "json") -> str:
        """
        导出指标数据
        
        Args:
            format: 导出格式(json)
            
        Returns:
            str: 导出的数据
        """
        with self._lock:
            data = {
                "metrics": self.get_metrics(),
                "sql_statistics": self.get_sql_statistics(),
                "recent_events": self.get_recent_events(100),
            }
            
            if format == "json":
                return json.dumps(data, indent=2, ensure_ascii=False)
            else:
                raise ValueError(f"不支持的导出格式: {format}")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        生成性能报告
        
        Returns:
            Dict[str, Any]: 性能报告
        """
        metrics = self.get_metrics()
        sql_stats = self.get_sql_statistics()
        
        report = {
            "summary": {
                "total_sql_executions": sql_stats["total"],
                "success_rate": (
                    sql_stats["success"] / sql_stats["total"] * 100
                    if sql_stats["total"] > 0
                    else 0
                ),
                "avg_execution_time": sql_stats["avg_time"],
            },
            "sql_statistics": sql_stats,
            "counters": metrics["counters"],
            "performance_indicators": {
                "slow_queries": sum(
                    1 for m in self._metrics.get("sql_executions", [])
                    if m["execution_time"] > 1.0
                ),
                "error_rate": (
                    sql_stats["failed"] / sql_stats["total"] * 100
                    if sql_stats["total"] > 0
                    else 0
                ),
            },
        }
        
        return report
