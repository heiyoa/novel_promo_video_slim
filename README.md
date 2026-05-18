# 小说推文视频自动生成工作流

英文目录名：`novel_promo_video_slim`

## 概述

`novel_promo_video_slim` 用于将书单或小说推广内容整理为后续短视频链路可继续处理的结构化结果。项目重点是调度与链路组织，而不是单点模型调用。

## 核心模块

- `run_workflow.py`：主调度入口
- `config/`：系统与流程配置
- `modules/providers.py`：书目读取与选择
- `modules/promo_fetcher.py`：推广信息补抓
- `modules/video_pipeline.py`：视频处理链路编排
- `outputs/`：结果与中间产物输出

## 架构思路

```text
System Config + Workflow Config
              │
              ▼
        run_workflow.py
              │
              ▼
        providers.py
              │   选择目标书目
              ▼
      promo_fetcher.py
              │   按需补抓推广信息
              ▼
      video_pipeline.py
              │
              ├── 构造小说文本
              ├── 调用改写模块
              ├── 生成字幕
              ├── 准备图像提示词
              └── 输出任务结果
              ▼
           outputs/
```

## 工作流说明

```text
1. 读取系统与流程配置
2. 选择目标书目
3. 按需补抓推广信息
4. 组装视频链路所需输入
5. 进入视频处理模块
6. 输出本轮任务结果
```

## 容错设计

```text
- 支持跳过 promo、跳过 video：便于分段 smoke
- 配置集中管理：减少硬编码依赖
- 统一结果输出：便于回查具体失败阶段
- 主调度层与重型模块分离：便于逐步排查
```

## 当前状态

当前版本已完成最小 smoke 验证，主入口、配置读取与书目选择链路可执行。
