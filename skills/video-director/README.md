# video-director（最小原型）

代码动画短片的总控 skill。它只做三件事：编排流程、设置检查点、把风格沉淀下来。风格库复用 lemo-opuscar，渲染使用自带的 `scripts/render.mjs`。

## 安装

把整个 `video-director` 文件夹复制到 `~/.claude/skills/` 下，然后在新会话里输入 `/video-director`。
它设置了 `disable-model-invocation: true`，只有手动调用才会触发，不会和 lemo 等 skill 抢着被调用。

可选：安装 lemo 风格库

```bash
claude plugin marketplace add lemomo-ai/lemo-opuscar
claude plugin install lemo-opuscar@lemolab
```

## 依赖

Node 20+、ffmpeg；项目里需要安装 Playwright（见 SKILL.md 阶段 5）。

AI 静帧 + AI 配乐的片子另需：Python 的 librosa、soundfile、faster-whisper、rembg[cpu]、scipy（`pip install --user ...`）；项目里 `npm i -D p5@1.9.4`；atlas-cloud-image skill 和 `~/.atlas/key`。

## 文件

| 路径 | 作用 |
|---|---|
| `SKILL.md` | 6 个阶段的流程和检查点 |
| `templates/brief.md` | 选题 brief，内容关 |
| `templates/storyboard.md` | 分镜和时钟 |
| `templates/scores.md` | 7 项自评，每项 ≥8 分，最多 3 轮 |
| `templates/house-style.md` | 账号风格，存到 `~/.video-director/` 供下一条复用 |
| `templates/starter.html` | 满足渲染契约的起手页面 |
| `references/style-levels.md` | 热门风格的基线版与进阶做法、7 个丰富度维度 |
| `references/stack-map.md` | 效果与技术栈对照、确定性规则、常见坑 |
| `scripts/render.mjs` | 单帧 / 关键帧拼图 / 样片 / 全片渲染 / 导出音效时间轴 |
| `scripts/sfx.py` | 把音效时间轴和配乐结构合成为 WAV（120 BPM 配乐底 + 音效 + 混响） |
| `scripts/deadframes.py` | 统计成片里画面不动的片段（死帧） |
| `scripts/contrast.py` | 量重点时刻比前半拍响多少 dB（目标 ≥6） |
| `scripts/overlay.mjs` | 把叠加层页面逐帧渲染成透明 PNG，叠在 Blender 画面上 |
| `scripts/compose.py` | 合成：外部渲染帧（可缺帧）+ 透明叠加层 + 音轨，颗粒只加在 3D 层 |
| `scripts/blender_kit.py` | Blender 场景脚本的公共工具：材质、长方体、Cycles 设置、逐帧投影矩阵导出 |
| `scripts/beats.py` | 分析 AI 配乐：BPM、拍点、小节线、段落边界、分段响度（librosa） |
| `scripts/lyrics_align.py` | 歌声逐字时间戳（faster-whisper，CPU） |
| `scripts/cutout.py` | 从插画抠出人物层（rembg isnet-anime），做 2.5D 视差 |
| `scripts/mixdown.py` | AI 配乐 + 音效混音：重点时刻前压低配乐，增益加限幅到 −14 LUFS |
| `scripts/brush.js` | 毛笔书写模拟：按 KanjiVG 笔顺一笔一笔写字（依赖 p5.js 1.9.4） |
| `scripts/kanjivg.py` | 把 KanjiVG 的 SVG 转成 brush.js 用的笔画表 |
| `templates/ai-art.py` | AI 静帧批量生成模板（GPT Image 2.5 Flare，正负面提示词、角色锚点、背景板） |
| `references/case-natsu-op.md` | 案例复盘：『夏の残響』OP，4 轮用户反馈和经验 |

## 已验证

- 起手页面可以渲染单帧、关键帧拼图和 MP4（180 帧约 6 秒，540x960）
- 同一时间点渲染两次，像素完全一致
- 试跑（2026-10-31）：用「瑞士轮赛制」这个选题完整走完阶段 1–5，产出 15 秒 9:16 成片。自评 2 轮通过，450 帧渲染用时 23 秒。试跑发现的问题已补进 SKILL.md：关键事实要写进 brief、短片跳过样片、转场要单独抽帧检查、自评防止手松
- 试跑 v2（2026-10-31）：用「瑞士轮 · 自我纠错」选题做出 55 秒成片。包含一万届蒙特卡洛模拟数据、7 个镜头、匹配剪辑和 41 个合成音效；自评 2 轮通过；全片渲染 15 分钟
- 试跑 v3（2026-10-31）：只看内容的死帧从 51% 降到 10%；声音改为 10 段结构化配乐加音效
- 试跑 v4（2026-11-01）：『夏の残響』动漫 OP 式竖版 MV，79.8 秒。30 张 AI 插画 + MiniMax Music 3.0 整首配乐 + 代码动效和毛笔字，改了 4 轮，定稿为低清预览（用户确认不必出成片）。复盘见 `references/case-natsu-op.md`
- 尚未验证：与 lemo 的联动、阶段 6 账号风格的复用、合成音乐的听感、毛笔字在 1080×1920 全片渲染下的速度
