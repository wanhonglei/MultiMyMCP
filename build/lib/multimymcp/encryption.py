"""
加密工具模块

提供AES-256加密/解密功能
用于数据源配置密码的加密存储
"""

import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from multimymcp.exceptions import EncryptionError


class EncryptionUtil:
    """
    加密工具类
    
    使用AES-256对称加密算法
    支持密码加密/解密
    """
    
    def __init__(self, key: str):
        """
        初始化加密工具
        
        Args:
            key: 加密密钥(32字节)
            
        Raises:
            EncryptionError: 密钥长度不足
        """
        if len(key) < 32:
            raise EncryptionError("加密密钥长度必须至少32字节")
        
        self.key = key[:32].encode() if isinstance(key, str) else key[:32]
        self._fernet = self._create_fernet()
    
    def _create_fernet(self) -> Fernet:
        """
        创建Fernet加密器
        
        Returns:
            Fernet: Fernet加密器实例
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"multimymcp_salt",
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.key))
        return Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        加密明文
        
        Args:
            plaintext: 明文字符串
            
        Returns:
            str: 加密后的字符串(Base64编码)
            
        Raises:
            EncryptionError: 加密失败
        """
        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode())
            return base64.b64encode(encrypted_bytes).decode()
        except Exception as e:
            raise EncryptionError(f"加密失败: {str(e)}")
    
    def decrypt(self, ciphertext: str) -> str:
        """
        解密密文
        
        Args:
            ciphertext: 加密字符串(Base64编码)
            
        Returns:
            str: 解密后的明文字符串
            
        Raises:
            EncryptionError: 解密失败
        """
        try:
            encrypted_bytes = base64.b64decode(ciphertext.encode())
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            raise EncryptionError(f"解密失败: {str(e)}")
    
    @staticmethod
    def generate_key() -> str:
        """
        生成随机加密密钥
        
        Returns:
            str: 32字节的随机密钥(Base64编码)
        """
        import secrets
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        密码哈希(用于验证)
        
        Args:
            password: 密码字符串
            
        Returns:
            str: SHA256哈希值
        """
        return hashlib.sha256(password.encode()).hexdigest()
