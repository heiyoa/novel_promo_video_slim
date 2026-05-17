# -*- coding: utf-8 -*-
"""
小说改写模块 - Novel Rewriter Module
将小说文本改写为吸引人的短视频脚本
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
from typing import List, Optional
from openai import OpenAI

# Rewrite prompt (override via config)
REWRITE_PROMPT = """# Role: Viral Short Video Scriptwriter (TikTok/Reels Style)

# Task:
Convert the provided Novel text into a 6-8 slide "Text Slideshow" video script. The goal is to hook the viewer immediately and lead them to a cliffhanger that makes them want to read the full book.

# Input Data:
I will provide the first few chapters of a novel.

# Guidelines for Rewrite:
1.  **POV:** Always use **First Person ("I")**. Even if the novel is third person, convert it to the protagonist's POV.
2.  **Structure:** Break the story into **6 to 8 Slides**.
3.  **The Hook (Slide 1):** MUST be the most shocking, conflict-heavy moment. Start in the middle of the action (In Media Res). Examples: Catching a partner cheating, a humiliating divorce, a sudden pregnancy reveal.
4.  **Conciseness:** 
    - Max 2-3 sentences per slide.
    - No long paragraphs. 
    - Use punchy, emotional language.
5.  **Keyword Highlighting:** Identify 1-2 words per slide that should be highlighted (colored Yellow/Red in the video) for emphasis. Put these words in **bold**.
6.  **Pacing:**
    - Slide 1: The Shock/Betrayal (The Hook).
    - Slide 2-3: The Villain's reaction (make them sound shameless/audacious).
    - Slide 4-5: The Protagonist's pain/backstory (make the viewer sympathize).
    - Slide 6-7: The Turning Point/Revenge Setup.
    - Slide 8: The Cliffhanger (The "Mic Drop" moment).

# Output Format:
Please present the result in a table with the following columns:
1.  **Slide #**
2.  **Overlay Text** (The actual text to put on the video. Include emojis. Bold the keywords.)
3.  **Visual Scene** (Brief description for AI image generation.)
4.  **Duration** (Recommended seconds.)

# Example Tone:
"Pregnant with his child, I watched him propose to my sister. He said I was just a substitute." (Sadness -> Anger)
"""


class NovelRewriter:
    """小说改写器类"""

    DEFAULT_MODELS = [
        "gemini-3-flash",
        "gemini-3-pro-high",
        "gemini-3-pro-low",
        "gemini-3-pro-image",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-pro",
        "gemini-2.5-flash-thinking",
        "claude-sonnet-4-5",
        "claude-sonnet-4-5-thinking",
        "claude-opus-4-5-thinking",
    ]

    def __init__(
        self,
        api_key: str = "",
        api_endpoint: str = "http://127.0.0.1:8045",
        model_name: Optional[str] = None,
        model_fallbacks: Optional[List[str]] = None,
    ):
        """
        初始化小说改写器
        
        Args:
            api_key: API密钥
            api_endpoint: API端点地址
            model_name: 模型名称（如果不指定，从可用模型列表中选择）
        """
        self.api_key = api_key
        self.api_endpoint = api_endpoint
        
        self.available_models = list(model_fallbacks or self.DEFAULT_MODELS)
        if model_name and model_name not in self.available_models:
            self.available_models.insert(0, model_name)

        if model_name and model_name in self.available_models:
            self.current_model_index = self.available_models.index(model_name)
        else:
            self.current_model_index = 0

        self.model_name = self.available_models[self.current_model_index]
        self._configure_api()
    
    def _configure_api(self):
        """配置AI API"""
        self.client = OpenAI(
            base_url=f"{self.api_endpoint}/v1",
            api_key=self.api_key
        )
    
    def read_novel(self, file_path):
        """
        读取小说文本文件
        
        Args:
            file_path: 小说文件路径
            
        Returns:
            小说文本内容
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"[OK] 成功读取小说文件: {file_path}")
            return content
        except FileNotFoundError:
            print(f"[ERROR] 文件不存在: {file_path}")
            return None
        except Exception as e:
            print(f"[ERROR] 读取文件失败: {e}")
            return None
    
    def _switch_to_next_model(self):
        """
        切换到下一个可用模型
        
        Returns:
            bool: 切换成功返回True，否则返回False
        """
        if self.current_model_index < len(self.available_models) - 1:
            self.current_model_index += 1
            self.model_name = self.available_models[self.current_model_index]
            print(f"[INFO] 切换到模型: {self.model_name}")
            self._configure_api()
            return True
        else:
            print(f"[ERROR] 所有模型都已尝试，无法继续切换")
            return False
    
    def _is_quota_error(self, error):
        """
        判断是否是额度不足或API限制错误
        
        Args:
            error: 异常对象
            
        Returns:
            bool: 是额度错误返回True，否则返回False
        """
        error_str = str(error).lower()
        # 检查常见的额度不足和API限制错误
        quota_keywords = [
            '429', 'rate limit', 'quota', 'insufficient',
            'exceeded', 'limit', '403', 'forbidden'
        ]
        return any(keyword in error_str for keyword in quota_keywords)
    
    def rewrite_novel(self, novel_text, prompt_override: str | None = None):
        """
        使用AI改写小说为短视频脚本，支持模型自动轮换

        Args:
            novel_text: 小说文本内容

        Returns:
            改写后的脚本内容
        """
        max_retries = len(self.available_models)
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                print(f"[INFO] 正在调用AI进行改写... (模型: {self.model_name})")
                prompt = prompt_override.strip() if prompt_override else REWRITE_PROMPT
                full_prompt = f"{prompt}\n\n# Novel Text:\n{novel_text}"
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": full_prompt}]
                )
                print(f"[OK] AI改写完成 (模型: {self.model_name})")
                return response.choices[0].message.content
            except Exception as e:
                error_msg = str(e)
                print(f"[ERROR] AI改写失败 (模型: {self.model_name}): {error_msg}")
                
                # 判断是否是额度不足或API限制错误
                if self._is_quota_error(e):
                    print(f"[INFO] 检测到额度不足或API限制，尝试切换模型...")
                    if not self._switch_to_next_model():
                        print(f"[ERROR] 模型切换失败，无法继续改写")
                        return None
                    retry_count += 1
                else:
                    # 其他错误直接返回失败
                    print(f"[ERROR] 非额度相关错误，停止重试")
                    return None
        
        print(f"[ERROR] 所有模型都已尝试，改写失败")
        return None
    
    def parse_script(self, script_text):
        """
        解析AI返回的脚本文本，提取结构化数据
        
        Args:
            script_text: AI返回的脚本文本
            
        Returns:
            解析后的脚本数据列表
        """
        slides = []
        lines = script_text.split('\n')
        current_slide = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测是否是新的幻灯片行
            if line.startswith('Slide') or line.startswith('| Slide'):
                if current_slide:
                    slides.append(current_slide)
                current_slide = {
                    'slide_number': '',
                    'overlay_text': '',
                    'visual_scene': '',
                    'duration': ''
                }
                # 提取幻灯片编号
                if '|' in line:
                    parts = line.split('|')
                    for part in parts:
                        if 'Slide' in part:
                            current_slide['slide_number'] = part.strip()
                            break
                else:
                    current_slide['slide_number'] = line
            elif current_slide:
                # 解析表格列
                if '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 4:
                        # 跳过表头
                        if 'Slide #' in line or 'Overlay Text' in line:
                            continue
                        # 解析数据行
                        current_slide['slide_number'] = parts[0] if parts[0] else current_slide['slide_number']
                        current_slide['overlay_text'] = parts[1]
                        current_slide['visual_scene'] = parts[2]
                        current_slide['duration'] = parts[3]
                        slides.append(current_slide)
                        current_slide = None
        
        # 添加最后一个幻灯片
        if current_slide:
            slides.append(current_slide)
        
        return slides
    
    def save_script_json(self, script_data, output_path):
        """
        将脚本保存为JSON格式
        
        Args:
            script_data: 脚本数据
            output_path: 输出文件路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(script_data, f, ensure_ascii=False, indent=2)
            print(f"[OK] 脚本已保存为JSON: {output_path}")
            return True
        except Exception as e:
            print(f"[ERROR] 保存JSON失败: {e}")
            return False
    
    def save_script_markdown(self, script_text, output_path):
        """
        将脚本保存为Markdown格式
        
        Args:
            script_text: 脚本文本
            output_path: 输出文件路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(script_text)
            print(f"[OK] 脚本已保存为Markdown: {output_path}")
            return True
        except Exception as e:
            print(f"[ERROR] 保存Markdown失败: {e}")
            return False
    
    def process(self, input_path, output_json_path=None, output_md_path=None):
        """
        完整的处理流程：读取小说 -> 改写 -> 保存
        
        Args:
            input_path: 输入小说文件路径
            output_json_path: 输出JSON文件路径（可选）
            output_md_path: 输出Markdown文件路径（可选）
        """
        print("=" * 50)
        print("小说改写模块 - Novel Rewriter")
        print("=" * 50)
        
        # 读取小说
        novel_text = self.read_novel(input_path)
        if not novel_text:
            return False
        
        # 改写小说
        script_text = self.rewrite_novel(novel_text)
        if not script_text:
            return False
        
        # 保存结果
        success = True
        
        if output_json_path:
            script_data = self.parse_script(script_text)
            if not self.save_script_json(script_data, output_json_path):
                success = False
        
        if output_md_path:
            if not self.save_script_markdown(script_text, output_md_path):
                success = False
        
        print("=" * 50)
        if success:
            print("[OK] 改写完成!")
        else:
            print("[ERROR] 改写过程中出现错误")
        print("=" * 50)
        
        return success


def main():
    """主函数"""
    # 配置路径（使用相对路径，从当前工作目录开始）
    input_path = "小说样例.md"
    output_json_path = "改写脚本.json"
    output_md_path = "改写脚本.md"
    
    # 创建改写器实例
    rewriter = NovelRewriter()
    
    # 执行改写
    rewriter.process(input_path, output_json_path, output_md_path)


if __name__ == "__main__":
    main()
