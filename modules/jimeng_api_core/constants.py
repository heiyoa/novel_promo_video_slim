"""
常量定义模块

定义了即梦API中使用的各种枚举类型和常量。
"""

from enum import Enum
from typing import Dict, Tuple


class AspectRatio(Enum):
    """图片宽高比枚举"""
    RATIO_1_1 = "1:1"      # 正方形
    RATIO_4_3 = "4:3"      # 横向4:3
    RATIO_3_4 = "3:4"      # 纵向3:4
    RATIO_16_9 = "16:9"    # 横向16:9
    RATIO_9_16 = "9:16"    # 纵向9:16
    RATIO_3_2 = "3:2"      # 横向3:2
    RATIO_2_3 = "2:3"      # 纵向2:3
    RATIO_21_9 = "21:9"    # 超宽屏21:9

    @property
    def ratio_code(self) -> int:
        """获取对应的ratio代码"""
        ratio_map = {
            "1:1": 1,
            "4:3": 4,
            "3:4": 2,
            "16:9": 3,
            "9:16": 5,
            "3:2": 7,
            "2:3": 6,
            "21:9": 8,
        }
        return ratio_map.get(self.value, 1)


class Resolution(Enum):
    """图片分辨率枚举"""
    RESOLUTION_1K = "1k"
    RESOLUTION_2K = "2k"
    RESOLUTION_4K = "4k"

    def get_dimensions(self, ratio: AspectRatio) -> Tuple[int, int]:
        """获取指定比例下的实际尺寸"""
        resolution_map = {
            "1k": {
                "1:1": (1024, 1024),
                "4:3": (768, 1024),
                "3:4": (1024, 768),
                "16:9": (1024, 576),
                "9:16": (576, 1024),
                "3:2": (1024, 682),
                "2:3": (682, 1024),
                "21:9": (1195, 512),
            },
            "2k": {
                "1:1": (2048, 2048),
                "4:3": (2304, 1728),
                "3:4": (1728, 2304),
                "16:9": (2560, 1440),
                "9:16": (1440, 2560),
                "3:2": (2496, 1664),
                "2:3": (1664, 2496),
                "21:9": (3024, 1296),
            },
            "4k": {
                "1:1": (4096, 4096),
                "4:3": (4608, 3456),
                "3:4": (3456, 4608),
                "16:9": (5120, 2880),
                "9:16": (2880, 5120),
                "3:2": (4992, 3328),
                "2:3": (3328, 4992),
                "21:9": (6048, 2592),
            },
        }
        
        dimensions = resolution_map.get(self.value, {}).get(ratio.value, (1024, 1024))
        return dimensions


class ModelVersion(Enum):
    """模型版本枚举"""
    JIMENG_4_5 = "jimeng-4.5"           # 即梦4.5版本
    JIMENG_4_1 = "jimeng-4.1"           # 即梦4.1版本
    JIMENG_4_0 = "jimeng-4.0"           # 即梦4.0版本
    JIMENG_3_1 = "jimeng-3.1"           # 即梦3.1版本
    JIMENG_3_0 = "jimeng-3.0"           # 即梦3.0版本
    JIMENG_2_1 = "jimeng-2.1"           # 即梦2.1版本
    JIMENG_2_0_PRO = "jimeng-2.0-pro"    # 即梦2.0专业版
    JIMENG_2_0 = "jimeng-2.0"           # 即梦2.0版本
    JIMENG_1_4 = "jimeng-1.4"           # 即梦1.4版本
    JIMENG_XL_PRO = "jimeng-xl-pro"      # 即梦XL专业版

    @property
    def model_code(self) -> str:
        """获取对应的模型代码"""
        model_map = {
            "jimeng-4.5": "high_aes_general_v40l",
            "jimeng-4.1": "high_aes_general_v41",
            "jimeng-4.0": "high_aes_general_v40",
            "jimeng-3.1": "high_aes_general_v30l_art_fangzhou:general_v3.0_18b",
            "jimeng-3.0": "high_aes_general_v30l:general_v3.0_18b",
            "jimeng-2.1": "high_aes_general_v21_L:general_v2.1_L",
            "jimeng-2.0-pro": "high_aes_general_v20_L:general_v2.0_L",
            "jimeng-2.0": "high_aes_general_v20:general_v2.0",
            "jimeng-1.4": "high_aes_general_v14:general_v1.4",
            "jimeng-xl-pro": "text2img_xl_sft",
        }
        return model_map.get(self.value, "high_aes_general_v40l")


class ImageFormat(Enum):
    """图片格式枚举"""
    WEBP = "webp"
    JPEG = "jpeg"
    PNG = "png"


class ImageScene(Enum):
    """图片场景枚举"""
    SMART_CROP = "smart_crop"
    NORMAL = "normal"


# API常量
DEFAULT_ASSISTANT_ID = 513695
VERSION_CODE = "1.0.0"
PLATFORM_CODE = "web"
BASE_URL = "https://jimeng.jianying.com"

# 生成状态常量
class GenerateStatus:
    """生成状态常量"""
    PENDING = 20      # 等待中
    SUCCESS = 10      # 成功
    FAILED = 30       # 失败

# 错误代码常量
class ErrorCodes:
    """错误代码常量"""
    CONTENT_FILTERED = "2038"    # 内容被过滤
    INSUFFICIENT_POINTS = "5000"   # 积分不足
    AUTH_FAILED = "401"           # 认证失败
    RATE_LIMIT = "429"            # 请求频率限制

# 默认配置
DEFAULT_CONFIG = {
    "model": ModelVersion.JIMENG_4_5,
    "ratio": AspectRatio.RATIO_1_1,
    "resolution": Resolution.RESOLUTION_2K,
    "sample_strength": 0.5,
    "timeout": 45,
    "max_poll_count": 600,
    "poll_interval": 1,
}