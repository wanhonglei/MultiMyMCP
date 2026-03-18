"""
命令行接口模块

提供命令行工具，用于管理数据源、查看状态等
"""

import argparse
import json
from multimymcp import MultiMyMCP


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description='MultiMyMCP 命令行工具')
    
    # 全局参数
    parser.add_argument('--config', '-c', type=str, help='配置文件路径')
    parser.add_argument('--key', '-k', type=str, help='加密密钥')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 连接数据源
    connect_parser = subparsers.add_parser('connect', help='连接数据源')
    connect_parser.add_argument('datasource', type=str, help='数据源名称')
    
    # 执行SQL
    execute_parser = subparsers.add_parser('execute', help='执行SQL')
    execute_parser.add_argument('sql', type=str, help='SQL语句')
    execute_parser.add_argument('--datasource', '-d', type=str, default='default', help='数据源名称')
    execute_parser.add_argument('--params', '-p', type=str, help='参数(JSON格式)')
    
    # 查看状态
    status_parser = subparsers.add_parser('status', help='查看连接池状态')
    status_parser.add_argument('--datasource', '-d', type=str, default='default', help='数据源名称')
    
    # 健康检查
    health_parser = subparsers.add_parser('health', help='健康检查')
    health_parser.add_argument('--datasource', '-d', type=str, default='default', help='数据源名称')
    
    # 性能报告
    perf_parser = subparsers.add_parser('performance', help='性能报告')
    perf_parser.add_argument('--datasource', '-d', type=str, default='default', help='数据源名称')
    
    # 列出数据源
    list_parser = subparsers.add_parser('list', help='列出所有数据源')
    
    # 调整连接池大小
    resize_parser = subparsers.add_parser('resize', help='调整连接池大小')
    resize_parser.add_argument('min_size', type=int, help='最小连接数')
    resize_parser.add_argument('max_size', type=int, help='最大连接数')
    resize_parser.add_argument('--datasource', '-d', type=str, default='default', help='数据源名称')
    
    # 保存配置
    save_parser = subparsers.add_parser('save', help='保存配置')
    save_parser.add_argument('file', type=str, help='保存文件路径')
    
    # 加载配置
    load_parser = subparsers.add_parser('load', help='加载配置')
    load_parser.add_argument('file', type=str, help='配置文件路径')
    
    args = parser.parse_args()
    
    with MultiMyMCP(args.config, args.key) as mcp:
        if args.command == 'connect':
            success = mcp.connect(args.datasource)
            print(f"连接成功: {success}")
            
        elif args.command == 'execute':
            params = None
            if args.params:
                params = json.loads(args.params)
            result = mcp.execute(args.sql, params, args.datasource)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
        elif args.command == 'status':
            status = mcp.get_pool_status(args.datasource)
            print(json.dumps(status, indent=2, ensure_ascii=False))
            
        elif args.command == 'health':
            health = mcp.get_health_status(args.datasource)
            print(json.dumps(health, indent=2, ensure_ascii=False))
            
        elif args.command == 'performance':
            report = mcp.get_performance_report(args.datasource)
            print(json.dumps(report, indent=2, ensure_ascii=False))
            
        elif args.command == 'list':
            datasources = mcp.list_data_sources()
            print("数据源列表:")
            for ds in datasources:
                print(f"  - {ds}")
            
        elif args.command == 'resize':
            mcp.resize_pool(args.min_size, args.max_size, args.datasource)
            print(f"连接池大小已调整: 最小={args.min_size}, 最大={args.max_size}")
            
        elif args.command == 'save':
            mcp.save_config(args.file)
            print(f"配置已保存到: {args.file}")
            
        elif args.command == 'load':
            mcp.load_config(args.file)
            print(f"配置已加载: {args.file}")


if __name__ == '__main__':
    main()
