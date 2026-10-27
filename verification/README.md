# 导出后技术核验（只读，项目本地）

对 `outputs/exported_videos/` 等位置已生成的 MP4 做**只读**技术核验，返回绑定 exact SHA-256 的结构化 Verdict。来源方法：[Doubaonew `tools/kr3/run_edit.py` @ `e4c5ac02`](https://github.com/heiyoa/Doubaonew/blob/e4c5ac02e73dc22060817f9a59234d0cd3005579/tools/kr3/run_edit.py) 的 SHA-256/ffprobe/抽帧技术方法，经 `m5_provider_consumer_trial_v0_1`（2026-10-28 第一轮真实消费实证）项目本地化。

## 用法

```bash
python verification/verify_export.py outputs/exported_videos/Fitness_Reset.mp4
# 可选：--json-out PATH 保存回执；--criteria PATH 覆盖标准（默认本目录 frozen_criteria.json）
```

退出码：`0` PASS / `1` FAIL / `2` UNKNOWN。

## Verdict 语义（fail-closed）

- **PASS**：全部冻结必要技术检查满足（时长≥5s、≥720×720、竖屏、全流解码、3 帧可解码、音轨策略 OPTIONAL、非空）。
- **FAIL**：文件已评估且某项必要条件失败（空文件、无视频流、解码错误、抽帧失败、尺寸/时长/竖屏不符、音轨策略不符）。
- **UNKNOWN**：无法评估——文件不存在/不可读、ffprobe/ffmpeg 不在 PATH、标准文件缺失或非法。

**FAIL 或 PASS 都不是专业或业务成功**：输出对象中 `professional_status` / `business_status` 恒为 `NOT_EVALUATED`，`publishing_authorization` 恒为 `NONE`。本工具不重新导出、不覆盖输入、不启动 GUI、不发布。

## 维护责任（Capability Maintainer）

- **归属项目**：`novel_promo_video_slim`（仓库内自维护，无常驻 Agent、无外部服务）。
- **维护人**：heiyoa（Owner）。
- **重新验证触发**：ffprobe/ffmpeg 大版本变更；导出管线/分辨率/编解码变更；`frozen_criteria.json` 有意修订（须新版本 + 来源，不得原地改）；本目录测试失败。
- **回归恢复**：`git revert` 引入本目录的提交即可整体回滚；方法上游（Doubaonew @ `e4c5ac02`）不受影响。
- **测试**：`python -m unittest verification.test_verify_export -v`（含合成正控 + 损坏/截断/静音/方形负控）。

## 与第一轮证据的关系

第一轮 Receipt、消费者决策与冻结标准见 [`outputs/m5_consumption_20261028/`](../outputs/m5_consumption_20261028/README.md)。本目录的 `frozen_criteria.json` 与第一轮标准同源（round1 record SHA 见文件内字段）。
