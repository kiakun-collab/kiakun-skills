---
name: video-director
description: 代码动画短片的总控流程：选题反问 → 选风格 → 分镜关键帧 → 逐镜头构建并自评打分 → 15 秒样片 → 全片渲染 → 沉淀账号风格。只在用户输入 /video-director 时使用。
disable-model-invocation: true
---

# video-director：代码动画短片总控

你是这条片子的导演兼制片。你不负责"发明风格"或"炫技"，你负责：**内容先想清楚、每一步有检查点、产物落盘、风格可复用**。

所有状态写在当前项目文件夹里，不靠对话记忆。任何一步都可以单独重跑；接手时先读已有文件，从第一个未完成的阶段继续。

```
<project>/
  brief.md          阶段 1 产物
  storyboard.md     阶段 3 产物
  scores.md         阶段 4 每轮打分
  src/index.html    动画源码（时间驱动）
  frames/ out/      渲染输出

  # 用 Blender 做写实 3D 时另外有：
  sim/choreo.py     所有物体的逐帧运动和音效事件 → data/*.json
  film.py           Blender 场景（读 data/，渲染到 render/）
  src/overlay.html  透明叠加层：字幕、标注、纸面世界、__events
```

模板在本 skill 的 `templates/`，参考资料在 `references/`。用到时再读，不要一开始全读。

## 阶段 0：接手检查

1. 看当前文件夹有哪些产物，判断进度，告诉用户"从阶段 N 继续"。
2. 若存在 `~/.video-director/house-style.md`（账号风格），读它，后续默认沿用。

## 阶段 1：Brief（内容关，必过）

复制 `templates/brief.md` 到 `brief.md`，用户已给的信息先填好，**缺的用 AskUserQuestion 一次问完（≤4 问），不许瞎编**。必须拿到：

- 主题和**一句话情绪**（"这条片子让观众感到 ___"）。说不清就继续追问，这是整条片子的锚。
- 观众带走的 1 个核心信息
- 时长、比例（默认 30 秒、9:16）
- 有无配乐或配音（有就作为时钟，见阶段 4）
- 不想要的东西
- **超出基线的地方**：同一个选题，一句话就能做出来的版本是什么样？这条片子比它好在哪里（具体例子、真实素材、声音、细节）？

片子里出现的数字和事实，写进 brief 的「关键事实」一节，并注明来源或推算过程（例如"16 队瑞士轮共 33 场 = 8+8+8+6+3"）。数据驱动的画面（比赛、排行、统计）用一个固定 seed 的独立数据文件生成，多个方向和最终成片共用这份数据。

**检查点**：把 brief 给用户过目，确认后再进入阶段 2。

## 阶段 2：风格

优先级：账号风格 > lemo 风格库 > awesome 提示词 > 自选技术栈。

- 若 `~/lemo-opuscar/styles/` 存在：根据 brief 的情绪挑 3 个候选，读各自的 `STYLE.md`，说明每个为什么配这条片子，让用户选一个。**引用路径，不要复制全文进 brief。**
- 若没有 lemo：提示可安装（`claude plugin marketplace add lemomo-ai/lemo-opuscar` 后 `claude plugin install lemo-opuscar@lemolab`），也可以先用 `references/stack-map.md` 的技术栈对照来定风格。
- 用户给了参考片或 awesome 提示词：拆出配色、字体、字幕位置、节奏、转场，写成规范。

**风格进阶**（选定风格之后做）：读 `references/style-levels.md`，如果 `~/.video-director/style-levels.md` 存在也一起读。热门风格不用回避，但要做得比基线版更好：
- 选的是热门风格：从对应行挑至少 2 条进阶做法，写进 brief。
- 不论什么风格：从「丰富度维度」里挑至少 3 个，写清这条片子具体怎么做（例如"声音：每个方块落位配一声木块音效"）。

结果写回 `brief.md` 的「风格」一节，并注明技术栈。新手默认选 Canvas/SVG，不碰 GLSL 和 3D，除非用户坚持。

**MV / 动漫 OP 式静帧动画**（要插画质感，代码画不出来）：画面用 AI 生图、整首配乐用 AI 生成，代码只做动效、字体和音效点缀。先读 `references/stack-map.md` 的「AI 生图 + AI 音乐 + 代码动效」一节和 `references/case-natsu-op.md` 的经验。要点：
- 调用付费接口前先报张数和费用；先出 2–3 张风格样张 + 1 首音乐样本让用户选方向，音乐样本满意就直接定稿
- brief 里写明姿势规则（没有姿势参考图不用扭身、回望）和构图多样性（出图清单标景别和构图类型，同一类不超过 2 张）
- 字体从第一版就分工：情绪词用毛笔书写（`scripts/brush.js`），歌词用明朝，闪卡用粗黑体；每句歌词的出现方式各不相同

## 阶段 3：分镜与方向

1. 给**两个不同方向**，每个方向渲染 1 张关键帧 PNG（用阶段 5 的单帧模式），并排展示。
2. 用户选定后，按 `templates/storyboard.md` 写分镜：每个镜头写清时间段、画面、文字、动作、转场。
3. 前 2 秒必须有钩子（问题、反常识或强视觉冲击）。
4. **导演原则**（洗牌片第一版"后面的 3D 看不懂"之后总结）：
   - 一个镜头只讲一件事，观众的视线只有一个落点
   - 抽象概念先用小尺度演示（8 张牌讲清"段"），再放大到真实规模（52 张只给结论数字）
   - 景别要有变化：特写 → 中景 → 拉远揭示；不要每个镜头都是"一个机位慢慢漂移"
   - 镜头之间用动作衔接剪辑（在拿牌、落牌的瞬间切），少用淡入淡出
   - 空间收紧：竖屏里一个镜头只用桌面上一小块区域；很宽的东西要么缩小规模，要么用透视或俯拍
   - 每个镜头写清楚"这个镜头让观众明白什么"，写不出来就删掉

**检查点**：分镜确认后才写完整代码。如果 brief 里已经确认过镜头大纲，分镜只是补充细节，这个检查点可以和方向选择合并，不必再单独问一次。

## 阶段 4：构建与自评

先读 `references/stack-map.md` 的「确定性规则」和「常见坑」，写进代码注释作为约束。

- 以 `templates/starter.html` 为起点复制到 `src/index.html`，它已经满足下面的契约。
- 需要写实 3D（真实材质、金属反光、光线追踪）时用 Blender：先读 `references/stack-map.md` 的「Blender」一节。运动由 `sim/choreo.py` 编排成数据（不要用刚体引擎），Blender 和 HTML 叠加层都读这份数据；Blender 渲染前先出几张 `--still --preview` 单帧检查材质和构图。
- 源码必须遵守**渲染契约**：页面暴露 `window.__duration`（秒）、`window.__fps`，以及 `window.__renderFrame(t)`（画出 t 秒的那一帧，可以是 async）。画面只由 t 决定。
- 有配乐或配音时，先得到节拍点或逐句时间戳，写进 `storyboard.md`，让动作卡在这些时间点上。AI 配乐用 `scripts/beats.py`（拍点、小节线、段落）和 `scripts/lyrics_align.py`（歌词逐字时间戳），不要相信 prompt 里写的 BPM。用整首歌，不要剪接
- 逐镜头开发：每写完一个镜头，渲染该镜头的 2~3 帧自己看一遍。
- 全部写完后，生成**关键帧拼图**（每个镜头取中点一帧，见阶段 5 的拼图命令），按 `templates/scores.md` 的 7 项打分（第 7 项「丰富度」对照 brief 里写下的进阶做法，逐条检查是否真的做到了）。
- 拼图看不到转场：每个切点另外抽 3 帧（切点前 0.15 秒、切点、切点后 0.15 秒），单独检查。
- 自评是自己给自己打分，容易手松。每项给 8 分时要写出具体依据；把残留风险写进 `scores.md`，交给用户判断。
- 任一项 < 8 分：写出具体原因和改法，改代码后重新出拼图打分。**最多 3 轮**，3 轮后仍不达标，就列出剩余问题让用户决定。

## 阶段 5：渲染

使用 `scripts/render.mjs`，需要在项目文件夹里运行（Playwright 从当前文件夹加载）。首次使用先在项目里运行 `npm i -D playwright && npx playwright install chromium`；在 Windows 上如果 `npm`/`npx` 报 `StandardOutputEncoding` 错误，改用 `node "C:/Program Files/nodejs/node_modules/npm/bin/npm-cli.js" i -D playwright` 和 `node node_modules/playwright/cli.js install chromium`。

```bash
# 单帧（阶段 3 关键帧 / 自检用）
node <skill>/scripts/render.mjs src/index.html --at 3.5 --out frames/key.png
# 15 秒样片
node <skill>/scripts/render.mjs src/index.html --to 15 --out out/sample.mp4
# 全片
node <skill>/scripts/render.mjs src/index.html --out out/final.mp4
# 关键帧拼图：给出各镜头中点时间
node <skill>/scripts/render.mjs src/index.html --sheet 1.5,5,9,14,20,27 --out frames/sheet.png
```

可选 `--audio music.mp3` 混入音轨。宽高取 brief 的比例（脚本默认 1080x1920，横屏传 `--size 1920x1080`）。

**Blender 片子的渲染**（3D 在 Blender，其余在叠加层）：
```bash
blender -b --factory-startup -P film.py -- --cam                 # 投影矩阵，给叠加层贴标注
blender -b --factory-startup -P film.py -- --preview --from 0 --to 1165   # 低清预览帧 → preview/
node <skill>/scripts/overlay.mjs src/overlay.html                # 透明叠加层帧 → overlay/
python <skill>/scripts/compose.py --base preview --overlay overlay --audio out/sfx.wav --out out/preview.mp4 --crf 20
blender -b --factory-startup -P film.py -- --from 0 --to 1165    # 正式帧 → render/（后台跑，约 2 秒/帧）
python <skill>/scripts/compose.py --base render --overlay overlay --audio out/sfx.wav --out out/final.mp4
```
纸面期间不渲染 3D，`compose.py` 会用黑帧补齐。改叠加层或声音只需重出叠加层帧、重新合成，不用重渲 Blender。

顺序固定：**先出 15 秒样片 → 用户确认 → 才渲染全片**。Blender 片子用全片低清预览代替 15 秒样片。片子总长 ≤20 秒时，跳过样片，直接渲染全片。

参考速度（1080x1920）：纯 SVG 每秒画面约需 1.5 秒；加上全屏 SVG 滤镜（feTurbulence 纸纹、feDisplacementMap 抖动）后约需 17 秒，55 秒的片子要渲染 15 分钟。全片渲染要放到后台运行；赶时间就先关掉滤镜出预览版。

### 声音（AI 整首配乐时）
音乐由 AI 生成，`sfx.py` 只出点缀音效（不传 `__music`），再用 `python <skill>/scripts/mixdown.py music.wav out/sfx.wav out/mix.wav --dips <重点时刻,...>` 混音：重点时刻前压低配乐、音效 −9 dB、增益加限幅到 −14 LUFS。成品歌很满，不压低的话 contrast.py 量出来是 0 dB。

### 声音（不配乐时）
1. 页面里由同一套时间常量生成 `window.__events = [{t, type, ...}]`（音效）和 `window.__music = {bpm, chords, sections}`（配乐结构，段落风格见 sfx.py 开头），不要另外手写时间表。动画的关键点尽量落在拍点上（120 BPM 时为 0.5 秒）
2. `node <skill>/scripts/render.mjs src/index.html --fast --events 1 --out out/events.json`
3. `python -I <skill>/scripts/sfx.py out/events.json out/sfx.wav`（需要 numpy）
4. 检查：用 `showwavespic` 看波形、`showspectrumpic` 看频谱、`volumedetect` 看分段响度。段落之间要有起伏：高潮段最响，"爆冷/转折"段要真的空下来；音色好不好，必须请用户来听
5. **重点画面**：列出 3–6 个最关键的瞬间（钩子、转折、结论），在 `__music.dips` 里让配乐在它们之前空出半拍，再加一个 `swell` 音效正好落在那一帧，并把那一下的音效加重。检查标准：重击比它前半拍响 ≥6 dB（`python <skill>/scripts/contrast.py out/sfx.wav 2.5 11 ...`）。不够时先降低它前面那个 swell 的 gain
6. **段落起伏**：配乐每段有自己的音量（sfx.py 的 LEVELS，也可以在段落里写 `level` 覆盖），转折段要真的空下来，高潮段最响。整体响度范围（LRA）大约 6–8 LU
7. **响度**：短视频平台的标准是 −14 LUFS、真峰值 ≤ −1 dBTP。不要用 loudnorm 的动态模式（会压扁起伏），改成"整体增益 + 限幅器"，并给 AAC 编码留余量：
   `ffmpeg -i out/sfx-raw.wav -af "volume=<增益>dB,aresample=192000,alimiter=limit=0.75:attack=1:release=60:level=disabled,aresample=48000" out/sfx.wav`
   增益 = −14 − 原始 LUFS（用 `ffmpeg -af ebur128=peak=true` 量），限幅器会吃掉约 1 dB，再补回来
8. 渲染全片时加 `--audio out/sfx.wav`；如果只改了声音，不必重新渲染画面：`ffmpeg -i 旧成片.mp4 -i out/sfx.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k 新成片.mp4`，然后再量一次成片的响度（AAC 编码会让峰值上升）

### 死帧检查（每次全片渲染前都要做）
- `python -I <skill>/scripts/deadframes.py out/preview.mp4`：列出 ≥0.3 秒画面不变的片段
- 目标：只看内容的冻结占比 <10%，单段 ≤0.8 秒（结尾刻意停留的除外）
- 要量"只看内容"：临时关掉进度条、背景漂移、镜头缓推再量一次。环境运动能让数字变成 0，但观众要看的是有信息量的动作
- 胶片颗粒也算环境运动：Blender 片子用 `compose.py --no-grain` 合成一版再量（高尔顿板加颗粒量是 12%，关掉是 33%）
- 补停顿时优先补"和内容有关的动作"（配对线、计数器滚动、落地反馈、状态标签翻转），其次才是镜头缓推、背景漂移

### 快速预览
`--fast` 会设置 `window.__preview`，页面据此跳过昂贵的滤镜；配合 `--size 540x960`，55 秒的片子大约 1 分钟就能渲染完，适合反复修改。只有最终成片才用完整质量渲染。

## 阶段 6：沉淀账号风格

成片后问用户：是否把这次的配色、字体、字幕规范、节奏、片头片尾存为账号风格？同意就按 `templates/house-style.md` 写入或更新 `~/.video-director/house-style.md`。下一条默认沿用，这样同一系列更容易被记住。

## 原则

- 形式可以交给模型，"讲什么"必须由用户确认。
- 每个检查点都要停下来等用户确认，不要一路跑到底。
- 控制成本：自评最多 3 轮；渲染慢就先降分辨率或减少粒子，别硬等。
