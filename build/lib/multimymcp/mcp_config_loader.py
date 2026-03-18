"""
MCP 配置加载器

支持从多个位置加载配置文件，实现优先级机制
"""

import os
import json5
from pathlib import Path
from typing import Dict, Any, Optional


class MCPConfigLoader:
    """
    MCP 配置加载器
    
    支持从多个位置加载配置：
    1. 命令行参数 --config
    2. 环境变量 TRAE_MYSQL_MCP_CONFIG
    3. 全局配置文件 ~/.trae-mysql-mcp/mcp_config.json5
    4. 默认配置
    """
    
    def __init__(self):
        """初始化配置加载器"""
        self.home_dir = Path.home()
        self.config_dir = self.home_dir / ".trae-mysql-mcp"
        self.config_file = self.config_dir / "mcp_config.json5"
        self.multimymcp_config_file = self.home_dir / ".multimymcp" / "mcp_config.json5"
    
    def get_default_config_path(self) -> Path:
        """
        获取默认配置文件路径
        
        Returns:
            Path: 配置文件路径
        """
        return self.config_file
    
    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径（可选）
            
        Returns:
            Dict[str, Any]: 配置数据
            
        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置文件格式错误
        """
        if config_path:
            path = Path(config_path)
        elif os.getenv("TRAE_MYSQL_MCP_CONFIG"):
            path = Path(os.getenv("TRAE_MYSQL_MCP_CONFIG"))
        elif self.config_file.exists():
            path = self.config_file
        elif self.multimymcp_config_file.exists():
            path = self.multimymcp_config_file
        else:
            return self._get_default_config()
        
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json5.load(f)
        except Exception as e:
            raise ValueError(f"Failed to parse config file: {str(e)}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置
        
        Returns:
            Dict[str, Any]: 默认配置
        """
        return {
            "datasources": {},
            "security": {
                "whitelist_enabled": False,
                "blacklist_enabled": True,
                "blacklist": ["DROP", "TRUNCATE", "ALTER", "CREATE"]
            }
        }
    
    def ensure_config_dir(self):
        """
        确保配置目录存在
        """
        self.config_dir.mkdir(parents=True, exist_ok=True)
