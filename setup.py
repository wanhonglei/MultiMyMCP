from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="multimymcp",
    version="1.0.0",
    author="TraeMCP Team",
    author_email="support@trae.com",
    description="生产级 MySQL 多数据源 MCP 工具,适配 TRAE CN IDE 环境",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/trae/multimymcp",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Database",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pymysql>=1.0.0",
        "DBUtils>=2.0.0",
        "python-dotenv>=0.19.0",
        "cryptography>=3.4.0",
        "psutil>=5.8.0",
        "json5>=0.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.2.0",
            "pytest-cov>=3.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "multimymcp=multimymcp.cli:main",
        ],
    },
)
