# E2 专业评价证据包（M5 v0.4，2026-10-28）

对两份真实导出视频的**全 cue 视觉专业评价**、脚本意图差额三分定性与 rubric 对照攻击。上游方法语义：[Harbor #297 v0.4](https://github.com/heiyoa/Harbor/issues/297#issuecomment-6456421623)（六维研究 rubric）。**该 v0.4 工具包（m5_e2_professional_review_v0_1，ZIP SHA `8f4a52a1…`）从未传到本机，本目录按 #297 公布的语义执行并逐条注明缺口**；canonical 包到位后需对账复验。

## 素材与来源（原 SHA 全部保留）

| 素材 | SHA-256 | 来源对账 |
| --- | --- | --- |
| Love_Hidden_in_Dreams.mp4 | `9088b0e8…ecdc`（83,893,028B） | 仓库 blob（round 2 已证与本地一致） |
| Fitness_Reset.mp4 | `fd5a2466…37f0`（19,358,051B） | 仓库 blob |
| Love_Hidden script.md / draft.json / subtitles.srt | 见 evidence_packet.json | git blob `9ed0119f…` / `3c078b8b…` / `2985a37f…` 与 GitHub main 全部一致（仅 CRLF 差异） |

## 文件索引

- `evidence_packet.json` — 机械生成：素材 SHA 清单、逐 cue 时码/字符速率（Love_Hidden 20 cue max 21.43cps；Fitness 10 cue max 22.50cps）、意图差额（8/6 场景 vs 1 素材；计划 45s/18s vs 实际 78.3s/21.4s）、**全片场景变化检测 = 0**（静态照片实锤）、音频技术事实
- `storyboard_love_hidden/` + `love_hidden_contact_sheet.jpg` — 20 个 cue 中点帧拼贴（已逐格目视）
- `storyboard_fitness_reset/` + `fitness_reset_contact_sheet.jpg` — 10 个 cue 中点帧拼贴
- `e2_rubric_frozen.json` — 评价前冻结的六维 rubric（含防作弊规则）
- `review_love_hidden.json` / `review_fitness_reset.json` — 逐时间码六维评价（overall_e2 均 **NOT_PASS**；音频内容 UNKNOWN）
- `intent_gap_classification.json` — 三分定性：设计缺陷（单图架构 vs 逐场景脚本）+ 实现缺陷（Jimeng 失败静默回用他 run 图片 + 撇号排版）+ 部分可辩护风格（需 Owner 裁定）
- `rubric_contrast_attack.json` — 五项对照攻击（含 Fitness 正例区分力验证）
- `consumer_decision_*.json` — 消费者决策（verdict **REVISE**，readback PENDING）
- `e2_packet_tests.py` — 11 项完整性测试（全部 PASS）
- `packet_generator.py` — 证据包生成器（只读素材，不改原文件）

## 一句话结论

两个视频的 E2 均不 PASS：Love_Hidden 的图片与剧情**每一帧都不相关**（8 场景 0 实现），根因是"单图管线架构 + 生图失败静默回退"；Fitness 主题相邻但仍用了回退图。音频内容因无法收听保持 UNKNOWN。是否允许单图风格、是否需要多场景能力，由 Owner 裁定；本评价不授权任何重剪、发布或商业运营。
