# 氛围感小说推文简化版

目标：仅保留“申请推广 → 获取推广信息 → 生成视频”的最小链路，数据库与音乐使用可替换接口，所有可调项集中在配置文件中。  
所有脚本为 UTF-8 编码，复制到新电脑后仅需改配置即可运行。

## 目录结构

- `run_workflow.py`：主入口
- `config/system_config.json`：系统/路径/账号配置
- `config/workflow_config.json`：工作流与文案配置
- `data/books.db`：数据库（已复制旧项目）
- `assets/music_audio`：本地音乐目录（随机取一首）
- `modules/`：功能模块（推广抓取、改写、字幕、剪映草稿、即梦生图）
- `outputs/`：输出目录

## 依赖安装

```bash
python -m pip install -r requirements.txt
```

## 快速运行

```bash
python run_workflow.py
```

常用参数：
- `--book-name "书名"`
- `--book-limit 3`
- `--include-complete`
- `--skip-promo`
- `--skip-video`
- `--system-config config/system_config.json`
- `--workflow-config config/workflow_config.json`

## 关键配置

### system_config.json（系统配置）

- `paths.*`：数据库、输出、音乐、剪映草稿目录
- `providers.books`：数据库接口（当前为 sqlite）
- `providers.music`：音乐接口（当前为本地随机）
- `edge.*`：Edge 路径 / 用户目录 / 端口
- `promo_fetch.*`：抓取站点与选择器（可按页面变化调整）
- `llm.*`：改写模型接口与回退顺序
- `jimeng.*`：即梦生图配置（session_id 必填）
- `jianying.*`：剪映自动导出配置（可选）

### workflow_config.json（工作流配置）

- `steps.fetch_promo` / `steps.run_video`
- `book_selection.*`：选书条件
- `promo_required_fields`：缺哪个字段就继续抓取
- `rewrite_prompt`：改写提示词
- `image_prompt` / `image_negative_prompt`：即梦生图提示词
- `video.*`：字幕样式与音量

## 输出内容

- `outputs/<book>/novel_input.txt`：输入正文
- `outputs/<book>/script.md` / `script.json`：改写结果
- `outputs/<book>/subtitles.srt`：字幕
- `outputs/<book>/images/`：即梦生成图片
- `outputs/<book>/draft.json`：剪映草稿复制件
- `outputs/promo/promo_<book>.json`：推广抓取结果
- `outputs/job_output.json`：本次运行总结果

## 迁移到新电脑

1) 复制整个 `Projects/novel_promo_video_slim` 目录  
2) 修改 `config/system_config.json`（Edge 路径、用户目录、剪映草稿目录、session_id 等）  
3) 安装依赖后运行 `run_workflow.py`
