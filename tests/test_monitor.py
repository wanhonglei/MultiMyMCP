"""
监控模块测试
"""

import pytest
from multimymcp.monitor import Monitor


def test_monitor_events():
    """测试监控事件记录"""
    monitor = Monitor()
    
    # 记录事件
    monitor.record_pool_event("test_event", {"test_key": "test_value"})
    
    # 获取事件
    events = monitor.get_recent_events()
    assert len(events) > 0
    assert events[-1]["event_type"] == "test_event"
    assert events[-1]["data"]["test_key"] == "test_value"


def test_monitor_sql_execution():
    """测试SQL执行记录"""
    monitor = Monitor()
    
    # 记录SQL执行
    monitor.record_sql_execution("SELECT * FROM users", 0.1, True)
    
    # 获取SQL统计
    stats = monitor.get_sql_statistics()
    assert stats["total"] == 1
    assert stats["success"] == 1
    assert stats["failed"] == 0


def test_monitor_metrics():
    """测试指标收集"""
    monitor = Monitor()
    
    # 记录事件和SQL执行
    monitor.record_pool_event("test_event", {})
    monitor.record_sql_execution("SELECT * FROM users", 0.1, True)
    
    # 获取指标
    metrics = monitor.get_metrics()
    assert "counters" in metrics
    assert "sql_total" in metrics["counters"]
    assert "event_test_event" in metrics["counters"]


def test_monitor_timers():
    """测试计时器功能"""
    import time
    monitor = Monitor()
    
    # 开始计时
    monitor.start_timer("test_timer")
    time.sleep(0.1)
    # 停止计时
    duration = monitor.stop_timer("test_timer")
    
    assert duration > 0
    assert duration < 0.2


def test_monitor_performance_report():
    """测试性能报告生成"""
    monitor = Monitor()
    
    # 记录SQL执行
    monitor.record_sql_execution("SELECT * FROM users", 0.1, True)
    monitor.record_sql_execution("INSERT INTO users VALUES (1, 'test')", 0.05, True)
    
    # 获取性能报告
    report = monitor.get_performance_report()
    assert "summary" in report
    assert "sql_statistics" in report
    assert report["summary"]["total_sql_executions"] == 2
