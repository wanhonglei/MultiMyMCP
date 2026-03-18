#!/usr/bin/env python3
"""
测试 MCP 服务器是否能正确加载配置文件中的数据源
"""

import json
import subprocess
import time

# 启动 MCP 服务器
server_process = subprocess.Popen(
    ['python3', '-m', 'multimymcp.mcp_server'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# 等待服务器启动
time.sleep(1)

# 构建 list_datasources 请求
request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "list_datasources",
        "arguments": {}
    }
}

# 发送请求
try:
    # 发送请求
    server_process.stdin.write(json.dumps(request) + '\n')
    server_process.stdin.flush()
    
    # 读取响应
    response_line = server_process.stdout.readline()
    response = json.loads(response_line)
    
    print("\n测试结果:")
    print("响应:", json.dumps(response, indent=2, ensure_ascii=False))
    
    # 检查是否成功返回数据源
    if "result" in response and "content" in response["result"]:
        content = json.loads(response["result"]["content"][0]["text"])
        print("\n数据源列表:", content["datasources"])
        
        if len(content["datasources"]) > 0:
            print("\n✅ 成功加载到数据源！")
        else:
            print("\n❌ 未加载到任何数据源")
    else:
        print("\n❌ 响应格式错误")
        
finally:
    # 终止服务器进程
    server_process.terminate()
    try:
        server_process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        server_process.kill()
