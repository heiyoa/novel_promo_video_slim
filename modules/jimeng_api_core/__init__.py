"""
即梦AI核心API包

这是一个用于与即梦AI服务交互的Python核心包，提供了图片生成、
签名验证、常量定义等功能。

版本: 1.0.0
作者: AI Assistant
"""

__version__ = "1.0.0"
__author__ = "AI Assistant"

# 导入核心类
from .api import JimengClient
from .constants import AspectRatio, ModelVersion, Resolution
from .exceptions import (
    JimengAPIException,
    JimengGenerateException,
    JimengAuthException,
    JimengContentFilterException,
    JimengInsufficientPointsException
)

# 暴露主要接口
__all__ = [
    "JimengClient",
    "AspectRatio",
    "ModelVersion",
    "Resolution",
    "JimengAPIException",
    "JimengGenerateException",
    "JimengAuthException",
    "JimengContentFilterException",
    "JimengInsufficientPointsException",
    "__version__"
]