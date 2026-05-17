#!/usr/bin/env python3
"""
即梦AI核心API包使用示例

演示如何使用jimeng_api_core包生成图片。
"""

from jimeng_api_core import (
    JimengClient, 
    ModelVersion, 
    AspectRatio, 
    Resolution,
    JimengAPIException,
    JimengAuthException,
    JimengContentFilterException,
    JimengInsufficientPointsException
)


def main():
    """主函数"""
    print("=" * 50)
    print("🎨 即梦AI核心API包使用示例")
    print("=" * 50)
    
    # 配置参数
    session_id = "your_session_id_here"  # 请替换为实际的session_id
    
    # 检查session_id
    if session_id == "your_session_id_here":
        print("❌ 请先设置有效的session_id")
        print("💡 获取方法：")
        print("1. 访问 https://jimeng.jianying.com")
        print("2. 登录账户")
        print("3. 在浏览器开发者工具中查看Cookie")
        print("4. 找到sessionid字段的值")
        return
    
    try:
        # 创建客户端
        print("🔧 初始化客户端...")
        client = JimengClient(
            session_id=session_id,
            model=ModelVersion.JIMENG_4_5,
            ratio=AspectRatio.RATIO_1_1,
            resolution=Resolution.RESOLUTION_2K,
            debug=True
        )
        
        # 设置提示词
        prompt = """
        一只可爱的小猫温柔地抱着一只小狗，温馨感人的场景。
        小猫表情温柔友善，小狗乖巧地依偎在小猫怀中。
        背景温暖舒适，可能是柔软的毯子或舒适的家居环境。
        高清摄影风格，自然光效，细节丰富，色彩温暖柔和。
        """.strip()
        
        negative_prompt = """
        模糊，低质量，变形，扭曲，恐怖，丑陋，暴力，血腥，色情，不适宜内容。
        """.strip()
        
        print(f"📝 提示词: {prompt[:50]}...")
        print(f"🚫 负向提示词: {negative_prompt[:30]}...")
        
        # 生成图片
        print("🎨 开始生成图片...")
        images = client.generate_image(
            prompt=prompt,
            negative_prompt=negative_prompt,
            auto_download=True,
            output_dir="./generated_images"
        )
        
        # 输出结果
        print(f"✅ 成功生成 {len(images)} 张图片!")
        
        for i, image in enumerate(images):
            print(f"🖼️  图片 {i+1}:")
            
            # 获取图片URL
            image_url = None
            if image.get("image", {}).get("large_images"):
                image_url = image["image"]["large_images"][0].get("image_url")
            elif image.get("common_attr", {}).get("cover_url"):
                image_url = image["common_attr"]["cover_url"]
            
            if image_url:
                print(f"  🔗 URL: {image_url}")
            else:
                print("  ⚠️ 未找到图片URL")
    
    except JimengAuthException:
        print("❌ 认证失败：请检查session_id是否有效")
    except JimengContentFilterException:
        print("❌ 内容被过滤：请调整提示词")
    except JimengInsufficientPointsException:
        print("❌ 积分不足：请充值后重试")
    except JimengAPIException as e:
        print(f"❌ API错误：{e}")
    except Exception as e:
        print(f"❌ 未知错误：{e}")


def simple_example():
    """简单示例 - 3行代码生成图片"""
    print("\n" + "=" * 50)
    print("🚀 简单示例 - 3行代码生成图片")
    print("=" * 50)
    
    # 注意：请替换为实际的session_id
    session_id = "your_session_id_here"
    
    if session_id == "your_session_id_here":
        print("❌ 请先设置有效的session_id")
        return
    
    try:
        # 3行代码生成图片
        client = JimengClient(session_id=session_id)
        result = client.generate_image("一只可爱的小猫", auto_download=True)
        print(f"✅ 生成成功！共 {len(result)} 张图片")
    except Exception as e:
        print(f"❌ 生成失败：{e}")


def advanced_example():
    """高级示例 - 自定义参数"""
    print("\n" + "=" * 50)
    print("🔧 高级示例 - 自定义参数")
    print("=" * 50)
    
    # 注意：请替换为实际的session_id
    session_id = "your_session_id_here"
    
    if session_id == "your_session_id_here":
        print("❌ 请先设置有效的session_id")
        return
    
    try:
        # 使用专业模型和超高清分辨率
        client = JimengClient(
            session_id=session_id,
            model=ModelVersion.JIMENG_2_0_PRO,  # 专业模型
            ratio=AspectRatio.RATIO_16_9,        # 16:9宽屏
            resolution=Resolution.RESOLUTION_4K,   # 4K超高清
            sample_strength=0.7,                 # 较高采样强度
            max_poll_count=300,                   # 减少轮询次数
            debug=True                           # 开启调试
        )
        
        # 生成风景图片
        prompt = """
        壮丽的山川风景，日出时分，云雾缭绕。
        山峰巍峨，阳光穿透云层洒向大地。
        湖水如镜，倒映着山峦和彩霞。
        超高清摄影风格，电影级光效，细节丰富。
        """.strip()
        
        images = client.generate_image(
            prompt=prompt,
            auto_download=True,
            output_dir="./landscape_images"
        )
        
        print(f"✅ 风景图片生成成功！共 {len(images)} 张")
        
    except Exception as e:
        print(f"❌ 生成失败：{e}")


if __name__ == "__main__":
    # 运行示例
    main()
    simple_example()
    advanced_example()