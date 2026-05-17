# pyJianYingDraft

轻量、灵活、易上手的Python剪映草稿生成及导出工具，构建全自动视频剪辑/混剪流水线！

## 功能特性

- 创建和编辑剪映草稿文件
- 添加视频、音频、图片、文本片段
- 支持关键帧动画
- 支持特效、滤镜、转场
- 批量导出功能

## 安装

```bash
pip install pyJianYingDraft
```

## 快速开始

```python
import pyJianYingDraft as draft

# 创建草稿文件夹
draft_folder = draft.DraftFolder("你的剪映草稿文件夹路径")

# 创建新草稿
script = draft_folder.create_draft("我的草稿", 1920, 1080)

# 添加轨道
script.add_track(draft.TrackType.video)

# 添加视频片段
video_segment = draft.VideoSegment("视频路径.mp4", trange("0s", "5s"))
script.add_segment(video_segment)

# 保存草稿
script.save()
```

更多用法请参考项目文档。