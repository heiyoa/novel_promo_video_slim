# 即梦AI核心API包 (jimeng_api_core)

一个用于与即梦AI服务交互的Python核心包，提供图片生成、签名验证、常量定义等功能。

## 特性

- 🎨 支持多种即梦模型版本 (1.4 - 4.5)
- 🖼️ 支持多种分辨率和宽高比
- 🔐 完整的签名算法实现
- 🔄 自动轮询检查生成状态
- 📥 自动图片下载功能
- ⚡ 支持同步和异步操作
- 🛡️ 完善的异常处理机制
- 📝 详细的中文注释和文档

## 安装

### 依赖安装

```bash
pip install requests
```

或者使用requirements.txt：

```bash
pip install -r requirements.txt
```

## 快速开始

### 3行代码生成图片

```python
from jimeng_api_core import JimengClient

# 创建客户端
client = JimengClient(session_id="your_session_id_here")

# 生成图片
result = client.generate_image("一只可爱的小猫", auto_download=True)
```

### 详细示例

```python
from jimeng_api_core import JimengClient, ModelVersion, AspectRatio, Resolution

# 创建客户端，指定模型和参数
client = JimengClient(
    session_id="your_session_id_here",
    model=ModelVersion.JIMENG_4_5,
    ratio=AspectRatio.RATIO_16_9,
    resolution=Resolution.RESOLUTION_2K,
    debug=True  # 开启调试模式
)

# 生成图片
prompt = "一只可爱的小猫温柔地抱着一只小狗，温馨感人的场景。高清摄影风格，自然光效。"
negative_prompt = "模糊，低质量，变形，扭曲，恐怖，丑陋。"

try:
    # 生成图片并自动下载
    images = client.generate_image(
        prompt=prompt,
        negative_prompt=negative_prompt,
        auto_download=True,
        output_dir="./my_images"
    )
    
    print(f"成功生成 {len(images)} 张图片")
    
except Exception as e:
    print(f"生成失败: {e}")
```

## API文档

### JimengClient

即梦API客户端类，提供与即梦AI服务交互的核心功能。

#### 构造函数参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| session_id | str | 必填 | 会话ID，用于身份验证 |
| model | ModelVersion | JIMENG_4_5 | 模型版本 |
| ratio | AspectRatio | RATIO_1_1 | 图片宽高比 |
| resolution | Resolution | RESOLUTION_2K | 图片分辨率 |
| sample_strength | float | 0.5 | 采样强度 |
| timeout | int | 45 | 请求超时时间（秒） |
| max_poll_count | int | 600 | 最大轮询次数 |
| poll_interval | int | 1 | 轮询间隔（秒） |
| debug | bool | False | 是否启用调试模式 |

#### 主要方法

##### generate_image()

生成图片的核心方法。

```python
generate_image(
    prompt: str,
    negative_prompt: str = "",
    auto_download: bool = False,
    output_dir: str = "./downloads"
) -> List[Dict[str, Any]]
```

**参数：**

- `prompt`: 正向提示词（必填）
- `negative_prompt`: 负向提示词（可选）
- `auto_download`: 是否自动下载图片（默认False）
- `output_dir`: 图片保存目录（默认"./downloads"）

**返回：**
生成的图片信息列表，每个元素包含图片URL、尺寸等信息。

### 常量定义

#### ModelVersion - 模型版本

```python
from jimeng_api_core import ModelVersion

ModelVersion.JIMENG_4_5    # 即梦4.5版本（推荐）
ModelVersion.JIMENG_4_1    # 即梦4.1版本
ModelVersion.JIMENG_3_1    # 即梦3.1版本
ModelVersion.JIMENG_2_1    # 即梦2.1版本
# ... 更多版本
```

#### AspectRatio - 宽高比

```python
from jimeng_api_core import AspectRatio

AspectRatio.RATIO_1_1    # 正方形 1:1
AspectRatio.RATIO_16_9    # 横向 16:9
AspectRatio.RATIO_9_16    # 纵向 9:16
AspectRatio.RATIO_4_3     # 横向 4:3
AspectRatio.RATIO_3_4     # 纵向 3:4
# ... 更多比例
```

#### Resolution - 分辨率

```python
from jimeng_api_core import Resolution

Resolution.RESOLUTION_1K    # 1K分辨率
Resolution.RESOLUTION_2K    # 2K分辨率（推荐）
Resolution.RESOLUTION_4K    # 4K分辨率
```

### 异常处理

包提供了完善的异常处理机制：

```python
from jimeng_api_core import (
    JimengAPIException,
    JimengAuthException,
    JimengGenerateException,
    JimengNetworkException,
    JimengTimeoutException,
    JimengContentFilterException,
    JimengInsufficientPointsException
)

try:
    client = JimengClient(session_id="invalid_session")
    images = client.generate_image("测试提示词")
except JimengAuthException:
    print("认证失败，请检查session_id")
except JimengContentFilterException:
    print("内容被过滤，请调整提示词")
except JimengInsufficientPointsException:
    print("积分不足，请充值")
except JimengTimeoutException:
    print("生成超时，请稍后重试")
except JimengAPIException as e:
    print(f"API错误: {e}")
```

## 高级用法

### 自定义参数

```python
from jimeng_api_core import JimengClient, ModelVersion, AspectRatio, Resolution

# 使用专业模型和超高清分辨率
client = JimengClient(
    session_id="your_session_id",
    model=ModelVersion.JIMENG_2_0_PRO,  # 专业模型
    ratio=AspectRatio.RATIO_16_9,        # 16:9宽屏
    resolution=Resolution.RESOLUTION_4K,   # 4K超高清
    sample_strength=0.7,                 # 较高采样强度
    max_poll_count=300,                   # 减少轮询次数
    debug=True                           # 开启调试
)
```

### 调试模式

开启调试模式可以看到详细的请求和响应信息：

```python
client = JimengClient(
    session_id="your_session_id",
    debug=True  # 开启调试模式
)
```

调试输出示例：
```
🎨 即梦客户端初始化完成
  模型: jimeng-4.5
  分辨率: 2k (2048x2048)
  宽高比: 1:1
  采样强度: 0.5
🔗 正在调用API: /mweb/v1/aigc_draft/generate
📊 响应状态: 200 OK
✅ 请求提交成功! history_id: 1234567890
⏳ 等待图片生成完成...
🔄 第 30 次轮询，当前状态: 20，已生成: 0 张图片...
✅ 图片生成完成! 状态=10，已生成 1 张图片
```

## 故障排除

### 常见问题

#### 1. 认证失败
**错误：** `JimengAuthException: 认证失败，请检查session_id是否有效`

**解决方案：**
- 确保session_id是有效的
- 检查session_id是否过期
- 重新获取session_id

#### 2. 内容被过滤
**错误：** `JimengContentFilterException: 内容被过滤，请调整提示词`

**解决方案：**
- 修改提示词，避免敏感内容
- 使用更正向、积极的描述
- 减少可能触发过滤的关键词

#### 3. 积分不足
**错误：** `JimengInsufficientPointsException: 即梦积分可能不足`

**解决方案：**
- 检查账户积分余额
- 充值积分
- 使用积分消耗较少的模型

#### 4. 生成超时
**错误：** `JimengTimeoutException: 生成超时: 轮询了 600 次`

**解决方案：**
- 增加`max_poll_count`参数
- 检查网络连接
- 稍后重试

#### 5. 网络错误
**错误：** `JimengNetworkException: 网络请求失败`

**解决方案：**
- 检查网络连接
- 确认防火墙设置
- 尝试使用代理

### 获取Session ID

1. 访问即梦官网：https://jimeng.jianying.com
2. 登录账户
3. 在浏览器开发者工具中查看Cookie
4. 找到`sessionid`字段的值

### 最佳实践

1. **提示词优化**：
   - 使用具体、详细的描述
   - 包含风格和质感描述
   - 避免模糊或抽象的表达

2. **参数选择**：
   - 一般用途使用`jimeng-4.5`模型
   - 高质量需求使用`2k`分辨率
   - 根据用途选择合适的宽高比

3. **错误处理**：
   - 始终使用try-catch处理异常
   - 根据不同异常类型采取不同处理策略
   - 实现重试机制

4. **性能优化**：
   - 合理设置轮询参数
   - 避免过于频繁的请求
   - 使用异步操作提高效率

## 更新日志

### v1.0.0
- 初始版本发布
- 支持即梦4.5/4.1/4.0/3.1/3.0/2.1/2.0/1.4等模型
- 完整的签名算法实现
- 自动轮询和下载功能
- 完善的异常处理机制

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进这个包。

## 联系方式

如有问题或建议，请通过GitHub Issues联系。