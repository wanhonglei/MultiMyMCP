"""
加密工具测试
"""

import pytest
from multimymcp.encryption import EncryptionUtil
from multimymcp.exceptions import EncryptionError


def test_encryption_basic():
    """测试基本加密/解密功能"""
    key = "test_encryption_key_32_bytes_long_1234567890"
    util = EncryptionUtil(key)
    
    plaintext = "test_password_123"
    encrypted = util.encrypt(plaintext)
    decrypted = util.decrypt(encrypted)
    
    assert decrypted == plaintext
    assert encrypted != plaintext


def test_encryption_key_length():
    """测试密钥长度校验"""
    # 密钥长度不足
    with pytest.raises(EncryptionError):
        EncryptionUtil("short_key")


def test_encryption_hash():
    """测试密码哈希功能"""
    key = "test_encryption_key_32_bytes_long_1234567890"
    util = EncryptionUtil(key)
    
    password = "test_password"
    hashed1 = util.hash_password(password)
    hashed2 = util.hash_password(password)
    
    assert hashed1 == hashed2
    assert len(hashed1) == 64  # SHA256 哈希长度


def test_encryption_generate_key():
    """测试生成随机密钥"""
    key = EncryptionUtil.generate_key()
    assert len(key) >= 32
