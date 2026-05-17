# -*- coding: utf-8 -*-
"""
文案转字幕模块
将改写后的脚本转换为 SRT 字幕格式
"""

import sys
import re
import json
from typing import List, Dict, Tuple

# Windows 编码防御性代码
sys.stdout.reconfigure(encoding='utf-8')


class ScriptToSubtitle:
    """脚本转字幕转换器"""
    
    # 基础阅读速度（秒/字符）
    READING_SPEED = {
        'english': 0.3,  # 英文单词
        'chinese': 0.25  # 中文汉字
    }
    
    # 情绪缓冲时间（秒）
    EMOTION_BUFFER = {
        'normal': 0.5,      # 普通叙述
        'hook': 1.5,        # 冲突/转折/震惊
        'cliffhanger': 2.0  # 结尾悬念
    }
    
    def __init__(self):
        self.slides = []
    
    def remove_emoji(self, text: str) -> str:
        """Remove emoji chars that might render poorly."""
        # 使用更简单的方法：移除常见的 emoji 字符
        # 这些是常见的 emoji Unicode 范围
        result = []
        for char in text:
            code = ord(char)
            # 检查是否在 emoji Unicode 范围内
            if (0x1F600 <= code <= 0x1F64F or  # emoticons
                0x1F300 <= code <= 0x1F5FF or  # symbols & pictographs
                0x1F680 <= code <= 0x1F6FF or  # transport & map symbols
                0x1F1E0 <= code <= 0x1F1FF or  # flags
                0x2600 <= code <= 0x26FF or      # miscellaneous symbols
                0x2700 <= code <= 0x27BF):      # dingbats
                continue  # 跳过 emoji
            result.append(char)
        return ''.join(result)

    def clean_overlay_text(self, text: str) -> str:
        """Strip lightweight markdown markers used for emphasis."""
        if not text:
            return ""
        return text.replace("**", "").replace("__", "").strip()
    
    def load_json(self, filepath: str) -> bool:
        """加载 JSON 格式的脚本"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.slides = data
            return True
        except Exception as e:
            print(f"[ERROR] Failed to load JSON file: {e}")
            return False
    
    def load_markdown(self, filepath: str) -> bool:
        """加载 Markdown 格式的脚本"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析 Markdown 表格
            lines = content.split('\n')
            slides = []
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('|') and '---' in line:
                    continue
                
                # 匹配表格行
                if line.startswith('|'):
                    parts = [p.strip() for p in line.split('|')[1:-1]]
                    if len(parts) >= 4:
                        # 过滤表头
                        if parts[1] == 'Overlay Text' or parts[1] == ':---':
                            continue
                        
                        # 尝试解析 Slide # 为数字
                        slide_num = parts[0]
                        if slide_num.isdigit():
                            slide_num = int(slide_num)
                        
                        # 提取 Duration 中的数字
                        duration_str = parts[3]
                        duration_match = re.search(r'(\d+(?:\.\d+)?)', duration_str)
                        duration = float(duration_match.group(1)) if duration_match else 0
                        
                        overlay_text = self.clean_overlay_text(parts[1])
                        
                        slides.append({
                            'slide_number': slide_num,
                            'overlay_text': overlay_text,
                            'visual_scene': parts[2],
                            'duration': duration
                        })
            
            self.slides = slides
            return True
        except Exception as e:
            print(f"[ERROR] Failed to load Markdown file: {e}")
            return False
    
    def load_script(self, filepath: str) -> bool:
        """自动识别并加载脚本文件"""
        if filepath.endswith('.json'):
            return self.load_json(filepath)
        elif filepath.endswith('.md'):
            return self.load_markdown(filepath)
        else:
            # 尝试 JSON
            if self.load_json(filepath):
                return True
            # 尝试 Markdown
            if self.load_markdown(filepath):
                return True
            print(f"[ERROR] Unknown file format: {filepath}")
            return False
    
    def detect_emotion(self, text: str, slide_num: int, total_slides: int) -> str:
        """检测文本情绪类型"""
        text_lower = text.lower()
        
        # 关键词检测
        hook_keywords = [
            'finally', 'suddenly', 'shocked', 'betrayed', 'cheating',
            'revenge', 'ex', 'jerk', 'monster', 'dumped', 'confronted',
            'screamed', 'ungrateful', 'small-minded', 'lovesick fool'
        ]
        
        cliffhanger_keywords = [
            'just beginning', 'wait until', 'no idea', 'the real show',
            'receipts', 'ruin them all', 'finally saw', 'cold smirk'
        ]
        
        # 检测关键词
        for keyword in cliffhanger_keywords:
            if keyword in text_lower:
                return 'cliffhanger'
        
        for keyword in hook_keywords:
            if keyword in text_lower:
                return 'hook'
        
        # 最后一个 slide 可能是悬念
        if slide_num == total_slides:
            return 'cliffhanger'
        
        return 'normal'
    
    def calculate_reading_time(self, text: str) -> float:
        """计算文本阅读时间"""
        # 移除 emoji 和特殊字符
        text_clean = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)
        
        # 统计中文字符
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text_clean))
        
        # 统计英文单词
        english_words = len(re.findall(r'[a-zA-Z]+', text_clean))
        
        # 计算时间
        time = (chinese_chars * self.READING_SPEED['chinese'] + 
                english_words * self.READING_SPEED['english'])
        
        return time
    
    def split_text_for_screen(self, text: str, max_sentences: int = 3) -> List[str]:
        """将文本分割为适合屏幕显示的片段"""
        # 按句子分割（句号、问号、感叹号），保留标点符号
        sentences = re.split(r'([.!?。！？])', text)
        
        # 重新组合句子（将标点符号附加到句子后面）
        sentences = [''.join(sentences[i:i+2]).strip() 
                    for i in range(0, len(sentences)-1, 2)]
        sentences = [s for s in sentences if s.strip()]
        
        # 如果句子数量少于等于 max_sentences，直接返回
        if len(sentences) <= max_sentences:
            return sentences if sentences else [text]
        
        # 否则，按 max_sentences 分组
        result = []
        for i in range(0, len(sentences), max_sentences):
            chunk = sentences[i:i + max_sentences]
            result.append(' '.join(chunk))
        
        return result
    
    def format_srt_time(self, seconds: float) -> str:
        """将秒数格式化为 SRT 时间格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    def generate_subtitle(self, output_path: str) -> bool:
        """生成 SRT 字幕文件"""
        if not self.slides:
            print("[ERROR] No slides loaded")
            return False
        
        try:
            subtitle_lines = []
            current_time = 0.0
            subtitle_index = 1
            
            total_slides = len(self.slides)
            
            for i, slide in enumerate(self.slides):
                text = slide.get('overlay_text', '')
                slide_num = i + 1
                
                text = self.remove_emoji(self.clean_overlay_text(text))
                
                # 检测情绪类型
                emotion = self.detect_emotion(text, slide_num, total_slides)
                
                # 分割文本
                text_chunks = self.split_text_for_screen(text)
                
                for j, chunk in enumerate(text_chunks):
                    # 计算阅读时间
                    reading_time = self.calculate_reading_time(chunk)
                    
                    # 确保至少有 1 秒
                    reading_time = max(reading_time, 1.0)
                    
                    # 计算结束时间
                    end_time = current_time + reading_time
                    
                    # 如果是最后一块，添加情绪缓冲
                    is_last_chunk = (j == len(text_chunks) - 1)
                    if is_last_chunk:
                        buffer = self.EMOTION_BUFFER.get(emotion, self.EMOTION_BUFFER['normal'])
                        end_time += buffer
                    
                    # 格式化时间
                    start_time_str = self.format_srt_time(current_time)
                    end_time_str = self.format_srt_time(end_time)
                    
                    # 添加到字幕
                    subtitle_lines.append(f"{subtitle_index}")
                    subtitle_lines.append(f"{start_time_str} --> {end_time_str}")
                    subtitle_lines.append(chunk)
                    subtitle_lines.append("")  # 空行
                    
                    # 更新时间和索引
                    current_time = end_time
                    subtitle_index += 1
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(subtitle_lines))
            
            print(f"[OK] Subtitle generated successfully: {output_path}")
            print(f"[INFO] Total subtitle blocks: {subtitle_index - 1}")
            print(f"[INFO] Total duration: {self.format_srt_time(current_time)}")
            
            return True
        except Exception as e:
            print(f"[ERROR] Failed to generate subtitle: {e}")
            return False


def main():
    """主函数"""
    import os
    
    # 设置路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 尝试加载 JSON 格式
    json_path = os.path.join(base_dir, '改写脚本.json')
    # 尝试加载 Markdown 格式
    md_path = os.path.join(base_dir, '改写脚本.md')
    
    # 输出路径
    output_path = os.path.join(base_dir, '字幕.srt')
    
    # 创建转换器
    converter = ScriptToSubtitle()
    
    # 优先加载 Markdown（通常包含实际内容），其次 JSON
    input_path = None
    if os.path.exists(md_path):
        input_path = md_path
        print(f"[INFO] Loading Markdown script: {md_path}")
    elif os.path.exists(json_path):
        input_path = json_path
        print(f"[INFO] Loading JSON script: {json_path}")
    else:
        print("[ERROR] No script file found")
        return
    
    # 加载脚本
    if not converter.load_script(input_path):
        return
    
    # 生成字幕
    converter.generate_subtitle(output_path)


if __name__ == '__main__':
    main()
