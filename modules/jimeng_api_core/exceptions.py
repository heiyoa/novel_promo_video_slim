"""
自定义异常类模块

定义了即梦API相关的各种异常类型，用于更好地处理错误情况。
"""


class JimengAPIException(Exception):
    """即梦API基础异常类"""
    
    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
    
    def __str__(self):
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class JimengAuthException(JimengAPIException):
    """认证异常类"""
    
    def __init__(self, message: str = "认证失败，请检查session_id是否有效"):
        super().__init__(message, "AUTH_ERROR")


class JimengGenerateException(JimengAPIException):
    """图片生成异常类"""
    
    def __init__(self, message: str, error_code: str = None):
        super().__init__(message, error_code or "GENERATE_ERROR")


class JimengNetworkException(JimengAPIException):
    """网络异常类"""
    
    def __init__(self, message: str = "网络请求失败"):
        super().__init__(message, "NETWORK_ERROR")


class JimengTimeoutException(JimengAPIException):
    """超时异常类"""
    
    def __init__(self, message: str = "请求超时"):
        super().__init__(message, "TIMEOUT_ERROR")


class JimengContentFilterException(JimengGenerateException):
    """内容过滤异常类"""
    
    def __init__(self, message: str = "内容被过滤，请调整提示词"):
        super().__init__(message, "CONTENT_FILTERED")


class JimengInsufficientPointsException(JimengGenerateException):
    """积分不足异常类"""
    
    def __init__(self, message: str = "即梦积分不足"):
        super().__init__(message, "INSUFFICIENT_POINTS")