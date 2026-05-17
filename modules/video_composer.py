#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪映合成视频模块
负责使用剪映草稿操作合并音乐、底图、字幕生成视频
"""

import os
import sys
import re
from pathlib import Path

# 强制重置标准输出编码，防止Windows下的编码问题
sys.stdout.reconfigure(encoding='utf-8')

# Add pyJianYingDraft path (prefer local copy)
module_dir = Path(__file__).resolve().parent
local_pyjy = module_dir / "pyJianYingDraft-main"
if local_pyjy.exists():
    sys.path.insert(0, str(local_pyjy))
else:
    raise RuntimeError("pyJianYingDraft-main not found next to video_composer.py")

import pyJianYingDraft as draft
from pyJianYingDraft import trange, ClipSettings, FontType, AudioMaterial
from pyJianYingDraft.time_util import Timerange


def srt_time_to_seconds(time_str):
    """
    将SRT时间格式转换为秒数
    格式: 00:00:00,000
    """
    try:
        # 替换逗号为点，便于解析
        time_str = time_str.replace(',', '.')
        
        # 解析时间
        if '.' in time_str:
            time_part, ms_part = time_str.split('.')
            ms = float(ms_part) / 1000
        else:
            time_part = time_str
            ms = 0
        
        # 解析时:分:秒
        parts = time_part.split(':')
        if len(parts) == 3:
            hours, minutes, seconds = map(float, parts)
        else:
            return 0.0
        
        # 计算总秒数
        total_seconds = hours * 3600 + minutes * 60 + seconds + ms
        return total_seconds
        
    except Exception as e:
        print(f"[X] 时间转换失败: {time_str} - {e}")
        return 0.0


def get_srt_duration(srt_path):
    """
    解析SRT文件，获取最后一个字幕的结束时间（秒）
    """
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 按空行分割字幕条目
        blocks = content.strip().split('\n\n')
        
        last_end_time = 0.0
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 2:
                # 解析时间码
                time_line = lines[1]
                if '-->' in time_line:
                    start_str, end_str = time_line.split(' --> ')
                    end_time = srt_time_to_seconds(end_str)
                    if end_time > last_end_time:
                        last_end_time = end_time
        
        print(f"[OK] SRT文件解析成功，总时长: {last_end_time:.3f}秒")
        return last_end_time
        
    except Exception as e:
        print(f"[X] 解析SRT文件失败: {e}")
        return 0.0


def get_audio_duration(file_path):
    """
    获取音频文件的真实时长（秒）
    """
    try:
        # 使用AudioMaterial获取时长（最准确）
        try:
            audio_material = AudioMaterial(file_path)
            duration = audio_material.duration / 1000000  # 转换为秒
            print(f"[OK] 使用AudioMaterial获取音频时长: {duration:.3f}秒 ({audio_material.duration} 微秒)")
            return duration
        except Exception as e:
            print(f"[X] AudioMaterial获取时长失败: {e}")
        
        # 尝试使用mutagen库
        try:
            from mutagen.mp3 import MP3
            audio = MP3(file_path)
            duration = audio.info.length
            print(f"[OK] 使用mutagen获取音频时长: {duration:.3f}秒")
            return duration
        except ImportError:
            pass
        
        # 尝试使用eyed3库
        try:
            import eyed3
            audio = eyed3.load(file_path)
            if audio and audio.info:
                duration = audio.info.time_secs
                print(f"[OK] 使用eyed3获取音频时长: {duration:.3f}秒")
                return duration
        except:
            pass
        
        # 尝试使用ffprobe
        try:
            import subprocess
            result = subprocess.run([
                'ffprobe', '-v', 'error', '-show_entries',
                'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1',
                file_path
            ], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                print(f"[OK] 使用ffprobe获取音频时长: {duration:.3f}秒")
                return duration
        except:
            pass
        
    except Exception as e:
        print(f"[X] 获取音频时长失败 {file_path}: {e}")
    
    # 最后 fallback: 尝试使用文件大小估算
    try:
        file_size = os.path.getsize(file_path)
        # 粗略估算：1MB ≈ 10秒（对于128kbps MP3）
        estimated_duration = (file_size / (1024 * 1024)) * 10
        print(f"[OK] 使用文件大小估算音频时长: {estimated_duration:.1f}秒")
        return estimated_duration
    except:
        print(f"[X] 所有方法都失败，返回默认时长60秒")
        return 60.0  # 默认返回60秒


def create_video_from_srt(
    srt_path,
    background_image_path,
    music_path,
    output_path,
    draft_folder_path,
    draft_name="小说推文视频",
    audio_volume=0.3,
    font_name="挥墨体",
    font_size=15,
    letter_spacing=0,
    line_spacing=7,
    bold=True,
    auto_wrapping=True,
):
    """
    根据SRT字幕、底图和音乐创建视频
    
    Args:
        srt_path: SRT字幕文件路径
        background_image_path: 底图文件路径
        music_path: 音乐文件路径
        output_path: 输出视频文件路径
        draft_folder_path: 剪映草稿文件夹路径
    """
    print("=== 开始创建视频 ===")
    
    # 检查必要文件是否存在
    if not os.path.exists(srt_path):
        print(f"[X] SRT文件不存在: {srt_path}")
        return False
    
    if not os.path.exists(background_image_path):
        print(f"[X] 底图文件不存在: {background_image_path}")
        return False
    
    if not os.path.exists(music_path):
        print(f"[X] 音乐文件不存在: {music_path}")
        return False
    
    if not os.path.exists(draft_folder_path):
        print(f"[X] 剪映草稿文件夹不存在: {draft_folder_path}")
        return False
    
    # 获取SRT时长
    srt_duration = get_srt_duration(srt_path)
    if srt_duration <= 0:
        print(f"[X] SRT时长无效: {srt_duration}")
        return False
    
    # 获取音乐时长
    music_duration = get_audio_duration(music_path)
    if music_duration <= 0:
        print(f"[X] 音乐时长无效: {music_duration}")
        return False
    
    # 计算需要的音乐时长（循环播放以匹配SRT时长）
    required_music_duration = srt_duration
    print(f"[INFO] 视频时长: {srt_duration:.3f}秒")
    print(f"[INFO] 音乐时长: {music_duration:.3f}秒")
    
    # 设置草稿文件夹
    try:
        draft_folder = draft.DraftFolder(draft_folder_path)
        print(f"[OK] 成功设置草稿文件夹: {draft_folder_path}")
    except Exception as e:
        print(f"[X] 设置草稿文件夹失败: {e}")
        return False
    
    # 创建新的草稿 (9:16 比例，1080x1920)
    try:
        script = draft_folder.create_draft(draft_name, 1080, 1920, allow_replace=True)
        print(f"[OK] 成功创建草稿: {draft_name} (1080x1920)")
    except Exception as e:
        print(f"[X] 创建草稿失败: {e}")
        return False
    
    # 添加轨道
    try:
        script.add_track(draft.TrackType.video, "底图轨道")
        script.add_track(draft.TrackType.audio, "音乐轨道")
        script.add_track(draft.TrackType.text, "字幕轨道")
        print("[OK] 成功添加底图轨道、音乐轨道和字幕轨道")
    except Exception as e:
        print(f"[X] 添加轨道失败: {e}")
        return False
    
    # 添加底图（裁剪到与SRT相同长度）
    try:
        # 将秒转换为微秒
        duration_microseconds = int(srt_duration * 1000000)
        
        # 创建底图片段
        image_segment = draft.VideoSegment(
            background_image_path,
            trange(0, duration_microseconds),
            clip_settings=ClipSettings(scale_x=1.0, scale_y=1.0)
        )
        
        script.add_segment(image_segment, "底图轨道")
        print(f"[OK] 成功添加底图，时长: {srt_duration:.3f}秒")
        
    except Exception as e:
        print(f"[X] 添加底图失败: {e}")
        return False
    
    # 添加音乐（循环播放以匹配SRT时长）
    try:
        # 将秒转换为微秒
        srt_duration_microseconds = int(srt_duration * 1000000)
        music_duration_microseconds = int(music_duration * 1000000)
        
        print(f"[INFO] 视频时长: {srt_duration:.3f}秒 ({srt_duration_microseconds} 微秒)")
        print(f"[INFO] 音乐时长: {music_duration:.3f}秒 ({music_duration_microseconds} 微秒)")
        
        full_loops = int(srt_duration_microseconds / music_duration_microseconds)
        remainder = srt_duration_microseconds % music_duration_microseconds
        
        print(f"[INFO] 完整循环次数: {full_loops}")
        print(f"[INFO] 剩余时间: {remainder/1000000:.3f}秒 ({remainder} 微秒)")
        
        # 添加完整循环的音乐片段
        current_time = 0
        segment_count = 0
        
        for loop in range(full_loops):
            if current_time >= srt_duration_microseconds:
                break
            
            # 计算本次循环的实际时长
            loop_duration = min(music_duration_microseconds, srt_duration_microseconds - current_time)
            
            if loop_duration > 0:
                try:
                    target_timerange = trange(current_time, loop_duration)
                    source_timerange = Timerange(0, loop_duration)
                    music_segment = draft.AudioSegment(
                        music_path,
                        target_timerange,
                        source_timerange=source_timerange,
                        volume=audio_volume,
                    )
                    
                    script.add_segment(music_segment, "音乐轨道")
                    segment_count += 1
                    print(f"[OK] 添加音乐片段 {segment_count}: {current_time/1000000:.1f}s - {(current_time + loop_duration)/1000000:.1f}s")
                    
                    current_time += loop_duration
                    
                except Exception as e:
                    print(f"[X] 添加音乐片段 {segment_count + 1} 失败: {e}")
        
        # 处理剩余时间
        if remainder > 0 and current_time < srt_duration_microseconds:
            final_duration = min(music_duration_microseconds, remainder, srt_duration_microseconds - current_time)
            
            if final_duration > 0:
                try:
                    target_timerange = trange(current_time, final_duration)
                    source_timerange = Timerange(0, final_duration)
                    music_final_segment = draft.AudioSegment(
                        music_path,
                        target_timerange,
                        source_timerange=source_timerange,
                        volume=audio_volume,
                    )
                    
                    script.add_segment(music_final_segment, "音乐轨道")
                    segment_count += 1
                    print(f"[OK] 添加最后音乐片段: {current_time/1000000:.1f}s - {(current_time + final_duration)/1000000:.1f}s")
                    
                except Exception as e:
                    print(f"[X] 添加最后音乐片段失败: {e}")
        
        if segment_count > 0:
            print(f"[OK] 成功添加 {segment_count} 个音乐片段")
        else:
            print("[X] 未能添加任何音乐片段")
        
    except Exception as e:
        print(f"[X] 添加音乐失败: {e}")
        return False
    
    # 解析SRT文件并添加字幕
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 按空行分割字幕条目
        blocks = content.strip().split('\n\n')
        
        subtitle_count = 0
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                # 解析时间码
                time_line = lines[1]
                if '-->' in time_line:
                    start_str, end_str = time_line.split(' --> ')
                    start_time = srt_time_to_seconds(start_str)
                    end_time = srt_time_to_seconds(end_str)
                    duration = end_time - start_time
                    
                    # 获取字幕文本
                    text = ' '.join(lines[2:])
                    
                    # 将秒转换为微秒
                    start_microseconds = int(start_time * 1000000)
                    duration_microseconds = int(duration * 1000000)
                    
                    # 创建字幕片段
                    # 字幕格式要求：位置(0,0)，大小15，字间距0，行间距7，字体挥墨体，加粗，自动换行
                    font = getattr(FontType, font_name, FontType.挥墨体)
                    text_segment = draft.TextSegment(
                        text,
                        trange(start_microseconds, duration_microseconds),
                        clip_settings=ClipSettings(transform_x=0, transform_y=0),
                        font=font,
                        style=draft.TextStyle(
                            size=font_size,
                            letter_spacing=letter_spacing,
                            line_spacing=line_spacing,
                            bold=bold,
                            auto_wrapping=auto_wrapping,
                        ),
                    )
                    
                    script.add_segment(text_segment, "字幕轨道")
                    subtitle_count += 1
                    print(f"[OK] 添加字幕 {subtitle_count}: '{text[:30]}...' ({start_time:.3f}s - {end_time:.3f}s)")
        
        print(f"[OK] 成功添加 {subtitle_count} 条字幕")
        
    except Exception as e:
        print(f"[X] 添加字幕失败: {e}")
        return False
    
    # 保存草稿
    try:
        script.save()
        print("[OK] 草稿保存成功!")
        print(f"[OK] 草稿名称: {draft_name}")
        print(f"[OK] 总时长: {srt_duration:.1f} 秒")
        print(f"[OK] 总字幕数: {subtitle_count}")
        
        # 将草稿内容保存到项目文件夹
        try:
            import shutil
            
            draft_dir = os.path.join(draft_folder_path, draft_name)
            # 尝试多种可能的草稿文件路径
            possible_paths = [
                os.path.join(draft_dir, "draft_content.json"),
                os.path.join(draft_dir, "draft_content"),
                os.path.join(draft_folder_path, f"{draft_name}.draft_content"),
                os.path.join(draft_folder_path, f"{draft_name}.json"),
                os.path.join(draft_dir, f"{draft_name}.draft"),
            ]
            
            copied = False
            for source_path in possible_paths:
                if os.path.exists(source_path):
                    shutil.copy2(source_path, output_path)
                    print(f"[OK] 草稿已复制到: {output_path}")
                    copied = True
                    break
            
            if not copied:
                print(f"[WARN] 未找到草稿文件，无法复制到输出路径")
                print(f"[INFO] 搜索的路径: {possible_paths}")
            
        except Exception as e:
            print(f"[WARN] 无法保存草稿到输出路径: {e}")
        
    except Exception as e:
        print(f"[X] 保存草稿失败: {e}")
        return False
    
    print("=== 视频创建完成 ===")
    print("请在剪映中打开草稿查看效果")
    return True


def main():
    """
    主函数
    """
    # 获取当前工作目录和脚本所在目录
    current_dir = os.getcwd()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    print(f"[DEBUG] 当前工作目录: {current_dir}")
    print(f"[DEBUG] 脚本所在目录: {script_dir}")
    
    # 使用绝对路径配置（与 script_to_subtitle.py 保持一致）
    srt_path = os.path.join(script_dir, "字幕.srt")
    background_image_path = os.path.join(script_dir, "outputs", "images", "base_image_1768424808.png")
    music_path = os.path.join(script_dir, "壁上观.mp3")
    output_path = os.path.join(script_dir, "输出视频.mp4")
    draft_folder_path = r"E:\jianying\JianyingPro Drafts"
    
    print(f"[DEBUG] SRT文件路径: {srt_path}")
    print(f"[DEBUG] 底图文件路径: {background_image_path}")
    print(f"[DEBUG] 音乐文件路径: {music_path}")
    print(f"[DEBUG] 输出视频路径: {output_path}")
    
    # 检查文件是否存在
    if not os.path.exists(srt_path):
        print(f"[X] SRT文件不存在: {srt_path}")
        print(f"[INFO] 请先运行字幕生成模块生成字幕文件")
        return
    
    if not os.path.exists(background_image_path):
        print(f"[X] 底图文件不存在: {background_image_path}")
        print(f"[INFO] 请先运行即梦生图模块生成底图文件")
        return
    
    if not os.path.exists(music_path):
        print(f"[X] 音乐文件不存在: {music_path}")
        print(f"[INFO] 请先运行音频提取模块生成音乐文件")
        return
    
    # 创建视频
    success = create_video_from_srt(
        srt_path=srt_path,
        background_image_path=background_image_path,
        music_path=music_path,
        output_path=output_path,
        draft_folder_path=draft_folder_path
    )
    
    if success:
        print("[OK] 视频合成成功!")
    else:
        print("[X] 视频合成失败!")


if __name__ == "__main__":
    main()
