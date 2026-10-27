# M5 消费实证归档（2026-10-28）

本目录是 `novel_promo_video_slim` 作为**第二个真实消费者**对 Provider 技术核验方法（来源：[Doubaonew `tools/kr3/run_edit.py` @ `e4c5ac02`](https://github.com/heiyoa/Doubaonew/blob/e4c5ac02e73dc22060817f9a59234d0cd3005579/tools/kr3/run_edit.py)）的**真实消费证据归档**。第一轮在 2026-10-28 由 heiyoa 授权的 ZCode 会话于本机执行；本目录使其在 Git 中可恢复。

## 文件索引

| 文件 | 内容 |
| --- | --- |
| `consumer_frozen_criteria.json` | 消费者 E1 最低技术验收标准（**验证前冻结**，2026-10-27T22:44:02Z） |
| `fitness_reset_E1_real.json` | 第一轮真实媒体 E1 只读核验 Receipt（`m5.video_technical_receipt/v1`） |
| `project_review.json` | 消费者评审输入（exact SHA、before/after、verdict 依据） |
| `project_decision.json` | 消费者决策记录（`m5.consumer_decision_record/v1`，verdict=ACCEPT 仅限 E1） |
| `e2_limited_precheck_note.json` | E2 有限预检观察（非 E2 PASS） |
| `srt_crosscheck_addendum.json` | 第二轮补充：三帧渲染字幕与项目自有 SRT 时间窗交叉核对（3/3 吻合） |
| `review_frames_thumbs/` | 三帧 360px JPEG 缩略图（原图 PNG 约 2.4MB/张，仅存本机，SHA 见 addendum） |

## 关键事实

- **Artifact**：`outputs/exported_videos/Fitness_Reset.mp4`，19,358,051 字节，SHA-256 `fd5a2466f292529fe08e85932a9b07208cc44d9dd815e43206dc5d57d04737f0`。**本仓库 Git blob 即该字节序列**（第二轮已克隆核对一致），因此本 Receipt 对仓库内文件直接有效。
- **E1 结果**：PASS —— h264 1080×1920 竖屏、21.41s、1 音轨（OPTIONAL）、全流解码零错误、3/3 抽帧。
- **消费者裁决**：ACCEPT（仅限 E1 技术回执）；`selection_changed: true`；`requires_controller_readback: true`（保持 **PENDING**，未宣称正式 Controller 已读回）。
- **E2/E3/E4**：E2 仅有限预检（见 note 与 addendum），E3 正式 Harbor 消费授权仍为候选级（#209 PRE_FORMATION），E4 未测量。均不得从 E1 PASS 推断。

## 边界

- 本目录不授予任何发布/改编/商业运营权限。
- 工具版本：`m5_provider_consumer_trial_v0_1`（会话本地包，ZIP SHA-256 `619a073a67404cef81d79947214b7c9fa87eafa06cbdb0f3e66f1839a8a0da5b`）；其方法已在本仓库 `verification/` 中项目本地化（见该目录 README）。
- Harbor 来源索引：#32 第一轮回执 `issuecomment-6455477025`；#297 M5 v0.3 `issuecomment-6454995783`。
