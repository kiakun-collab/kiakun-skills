# 技术栈对照、确定性规则与常见坑

## 效果 ↔ 技术栈（越往下越有质感，但越慢越难）

| 想要的效果 | 技术栈 | 备注 |
|---|---|---|
| 排版、图表、界面动效 | HTML/CSS/SVG | 文字最清晰，适合产品介绍、数据讲解 |
| 粒子、光效、深色电影感 | Canvas 2D | 几万个点也流畅。光晕做法：先画好画面，复制亮部缩小再模糊，最后叠加回去 |
| 手绘感 | p5.js + 笔刷 | 边缘晕开、线条抖动，抖动要用固定 seed |
| 光影质感 | GLSL Shader | 渲染慢：同样 3 秒，Canvas 约 7 秒，加 Shader 约 48 秒 |
| 3D 空间 | Three.js | 只展示不交互；复杂写实物体做不好 |
| 写实 3D（实物、金属、光线追踪） | Blender Cycles + HTML 叠加层 | 质感最好；1080x1920 每帧约 1.5–2.5 秒，见文末「Blender」一节 |
| 公式推导 | Manim | 不走本 skill 的渲染脚本 |

需要真人、实景等写实画面时：先用生图模型出素材，再用代码做动效，不要硬用代码 3D 去替代。

## 确定性规则（写进代码注释）

1. 画面只由 `t` 决定：不读 `Date.now()` / `performance.now()`，不用 `requestAnimationFrame` 推进状态，也不用 CSS animation / transition 自己计时。
2. 随机数必须带固定 seed（比如 mulberry32），并且同一个 t 每次都要算出同样的结果。粒子位置要写成 `f(seed, i, t)`，不要逐帧累加状态。
3. 渲染过程中不加载新资源：字体、图片、音频都在 `__renderFrame` 第一次被调用之前加载好（`await document.fonts.ready`）。
4. 依赖从 CDN 引入时要写死版本号。

## 渲染契约

```html
<script>
  window.__duration = 30;  // 秒
  window.__fps = 30;
  window.__renderFrame = async (t) => { /* 清屏，然后画出 t 秒的那一帧 */ };
</script>
```

画布尺寸以 `window.innerWidth/innerHeight` 为准，渲染脚本会把视口设成目标分辨率。

## 常见坑（提前避开）

- 字幕被画面挡住：字幕单独一层，放在安全区内（9:16 时避开底部约 20% 和右侧约 15%，那里是平台按钮）
- 字幕太长：每屏一句，中文最多约 14 个字
- 镜头之间硬切：每次切换至少用 0.3 秒做淡入淡出、位移或遮罩
- 光晕过亮发白：叠加光晕时限制强度，留出暗部
- 一帧画太多导致渲染极慢：控制粒子数量，模糊结果能缓存就缓存
- 提问或钩子出现太晚：前 2 秒就要出现

## WebGL / Three.js（2026-10-31 技术验证结论，项目见 shuffle-spike/）

- **可行**：render.mjs 不用改。无头 Chromium 加 `--use-gl=angle` 时会用上真实显卡（实测 RTX 3070 走 ANGLE/D3D11），不是软件渲染。启动时把 `WEBGL_debug_renderer_info` 打出来确认一下
- **速度**：1080x1920，4 倍 MSAA、2048 阴影贴图、24 次采样的景深 Shader → 每秒画面约需 11.5 秒（60 秒的片子约 12 分钟）；`--fast` 加 540x960 时约 3.5 秒
- **确定性**：同一帧渲染 3 次哈希一致；两次全片渲染逐帧一致
- **加载**：页面走 `file://`，ES module 的 import 会被拦截。用 `npm i three@0.149.0`（最后一个带 UMD 构建的版本），以 `<script src="../node_modules/three/build/three.min.js">` 引入；需要新版时，再给 render.mjs 加一个本地 http 服务
- **必须**：`preserveDrawingBuffer: true`（否则截图是黑的）；setPixelRatio(1)
- **不要用物理引擎**：物理引擎靠逐帧累加，跳帧渲染或并行渲染时结果会对不上。所有物体的轨迹都写成 t 的纯函数，随机数（比如洗牌顺序）用固定种子预先算好
- **后期**：先渲染到 WebGLRenderTarget（同时挂上 DepthTexture），再用全屏四边形加 ShaderMaterial 做景深、颗粒、暗角、调色；颗粒的随机种子取 floor(t·fps)
- **快速预览**：在 `window.__preview` 下降低景深采样数、阴影贴图尺寸，关掉 MSAA
- **和 2D 叠加**：WebGL canvas 放在下面，SVG 字幕层用 position:absolute 叠在上面，两层都由同一个 __renderFrame(t) 驱动
- **3D 和纸面混合时的坑**（洗牌片）：
  - 关掉 WebGL 画布后，要把 `html` 和 `body` 的背景一起改掉，只改 body 会露出 html 的颜色
  - 3D 到 2D 的匹配剪辑：先把相机和物体摆到切点那一帧的姿态，用 `vector.project(camera)` 换算成 SVG 坐标并缓存，2D 元素从这些坐标出发
  - 切到纯 2D 之后就停止渲染 WebGL（隐藏画布），后半段渲染会快很多
  - 贴图方向问题（文字是不是倒的、镜像的）不要凭缩略图判断：把几种方向并排渲染出来，一次比较
  - 竖屏拍很宽的物体（一整排 52 张牌）：用透视（站在一端往深处看，或者俯拍）解决，不要靠把镜头拉远
  - 后期 Shader 里的转场效果（比如带噪声边缘的纸张展开）在进度为 0 时必须完全不生效（`uPaper <= 0.0 ? 0.0 : ...`）。噪声会让阈值在局部略低于 0，于是每一帧都有个固定的小斑点。排查方法：跳过后期再渲染一次，斑点消失就是后期的问题
  - 交付编码：带全屏胶片颗粒的片子，CRF 18 时 60 秒有 232 MB（颗粒是随机噪声，压缩不动）。交付用 `-preset slow -crf 23`，约 25 MB，肉眼几乎看不出差别。母版另外保留一份
  - AAC 编码会让真峰值上升约 2 dB：限幅器设到 limit=0.63（约 −4 dBFS），编码后才能落在 −1 dBTP 以内
- **闪烁怎么测**（洗牌片）：同一时刻 t 和 t+0.001 秒各渲染一次（冻结颗粒），统计变化很大的像素占比。1 毫秒里画面本不该变化，所以跳变的像素就是深度冲突或锯齿闪烁。参考脚本：shuffle-spike/flicker-probe.mjs。目标 <0.05%
  - 常见原因：叠放物体的间距小于物体厚度，互相穿插（扇形、牌堆）；共面重叠（立着的一排牌）；近裁剪面太小，深度精度不够；细线贴图（斜纹）在运动中闪烁
  - 例外：镜头快速横移时这个测试会把运动也算进去。这时看连续两帧的放大裁剪图：边缘干净、只是位移很大，就是"频闪"（30 帧/秒下每帧位移太大），要把运动放慢到每帧约 30–40 像素

## Blender（2026-10-31 洗牌片重渲 + 高尔顿板成片，项目见 shuffle-spike/blender/、galton-spike/）

**什么时候用**：暗世界需要"真实物体"的质感（金属反光、软阴影、运动模糊、光学景深），并且有时间等渲染。纸面世界、字幕、图表仍然用 HTML/SVG，两层按帧合成。

**管线**（每一层只由时间 t 决定，所有层读同一份数据）：
1. `sim/choreo.py`（纯 Python）：算出所有物体的逐帧位置、落点、计数和音效事件 → `data/*.json`。几何常数也写进去，Blender 和 HTML 共用这一份
2. `film.py`（`blender -b --factory-startup -P film.py -- ...`）：搭场景、按数据打关键帧、逐帧算摄像机；`--cam` 导出逐帧投影矩阵（`blender_kit.export_vp`），`--still <秒>` 出单帧，`--from/--to` 渲染帧序列，`--preview` 半分辨率 8 采样
3. HTML 叠加层（背景透明）：字幕、贴在 3D 物体旁的标注（用投影矩阵算屏幕位置）、纸面世界、`__events`/`__music`。`node <skill>/scripts/overlay.mjs src/overlay.html` 出透明 PNG 序列
4. `python <skill>/scripts/compose.py --base render --overlay overlay --audio out/sfx.wav --out out/final.mp4`：颗粒和暗角只加在 3D 层；纸面期间不渲染 3D，缺帧自动用黑帧补
- 参考实现：`galton-spike/film.py`、`src/overlay.html`、`sim/choreo.py`；公共工具 `<skill>/scripts/blender_kit.py`

**速度**（RTX 3070，OptiX）：1080x1920、32 采样 + OptiX 降噪约 1.5–2.5 秒/帧（32 和 128 采样降噪后肉眼无差，128 要 3.9 秒）；每帧约 1 秒固定开销（降噪、写盘），降采样省不掉。预览（半分辨率 8 采样）约 0.2 秒/帧。高尔顿板 1408 帧 3D 正式渲染 36 分钟。EEVEE 首帧要编译几十个材质（30 秒），画质也不如 Cycles，不用

**物理：用编排，不用刚体引擎**
- 高尔顿板试了十几轮 Bullet 刚体：漏斗会卡死；球顺斜板滚出来带着很大的横向速度，一路冲到对面；横向动量在钉子间消不掉，分布是平的或两边多。改阻尼、弹性、后倾、竖直导槽都只能在"卡住"和"平的"之间切换
- 编排式物理：每颗球的路线由固定种子的选择决定（结果严格服从目标分布，可以直接当数据用），运动按重力抛物线算（每一跳加一点随机弹跳高度）。慢动作用较小的重力，整段物理自洽
- 板子比实物大（约 10 米）时，用 3g 左右的重力，速度才像真实尺寸
- 真刚体只适合"结果不重要、只要看起来自然"的局部（例如槽里落定），并且要先烘焙、存成数据再回放

**场景和材质的坑**
- `transform_apply` 默认连位置一起烘焙：原点跑到世界原点，绕自身旋转会变成绕世界原点转，刚体碰撞盒也会错。只传 `scale=True`（`blender_kit.box` 已处理）
- Bullet 的阻尼取值是 0–1，填 2 会让物体完全不动
- 有清漆（Coat）的大平面会把方形面光反射成一块硬边亮斑：背板用哑光（Roughness ≈ 0.7，不加 Coat）
- 竖直细金属条（隔板）反射暗环境会发黑：粗糙度提高到 0.45 左右才接得住光
- 钢珠靠反射环境发亮：世界光太暗球会发黑（世界光强度 ≈ 0.6，再加一盏冷色补光）
- AgX 会把品牌红压成暗红 → `Khronos PBR Neutral`
- 运动模糊要逐帧关键帧 + 线性插值；快门 0.3（108°），快速运镜时不至于糊成一片
- 打关键帧只打运动窗口（每颗球动的那几十帧，前后各一帧定住），几百个物体也只要几秒
- 节点按类型找（`n.type == 'BSDF_PRINCIPLED'`），不要按名字

**镜头和叠加层**
- 跟拍特写：目标点用球的位置做指数平滑（系数约 0.22/帧），镜头跟得上又不抖
- 固定机位超过 3 秒就算死帧：用缓慢横移（几秒内平移 2–3 米）代替推近，推近会让顶部元素撞上字幕
- 字幕在暗世界：顶部垫一层自上而下的暗色渐变；片尾机位把看向点抬高，让字幕落在暗的木板上，不要压在亮的物体上
- 标注离物体要留出物体在屏幕上的半径（特写里球半径约 70 像素，标注偏移 175 像素）
- 从纸面回到暗世界：纸从中心撕开、洞往外扩（反向用同一个毛边遮罩）。不要让纸缩回中心，会剩一团像出错的米白色块；纸面的网格线要跟着一起消失

**死帧要关掉颗粒再量**：3D 层的颗粒每帧都在变，冻结的画面也会被判成"在动"。用 `compose.py --no-grain` 合成一版再跑 `deadframes.py`。高尔顿板第一版加颗粒量是 12%，关掉颗粒是 33%

**MCP（blender-mcp）**：只用来在界面里调画面风格（打光、材质、构图），确定的参数写回脚本；正式渲染一律走脚本。服务只在 Blender 界面里运行（后台 `-b` 模式不工作）；带着 .blend 文件路径启动 Blender 最可靠

**PowerShell 的坑**：用双引号字符串做替换时，JS 模板字符串里的 `${...}` 会被当成 PowerShell 变量吃掉，页面直接报语法错误。改 JS 用 Edit 工具或单引号字符串

## AI 生图 + AI 音乐 + 代码动效（MV / 动漫 OP 式静帧动画，2026-11-01，项目见 natsu-op/，复盘见 references/case-natsu-op.md）

**什么时候用**：要高质量插画质感（人物、场景）而代码画不出来时。分工：AI 出静帧和整首配乐，代码只做动效、字体和音效点缀。画面仍由 t 决定，渲染契约不变。

**管线**
1. 音乐先行：`minimax/music-3.0`（Atlas，$0.15/首，一次出整首）。prompt 按"结构化描述"写：曲风、BPM、调性、人声音色、每段情绪和配器的进出；歌词用 `[Intro] [Verse] [Pre Chorus] [Chorus] [Outro]` 等段落标签控制结构。样本满意就直接定稿，不用再生成
2. 分析时钟：`python <skill>/scripts/beats.py music.wav out/beats.json --bpm-hint <预设>`（拍点、小节线、段落、分段响度）＋ `python <skill>/scripts/lyrics_align.py music.wav out/lyrics.json "<歌词>"`（faster-whisper 逐字时间戳，CPU 约 1–3 分钟）。分镜里的切点只用这两份数据
3. 出图：复制 `<skill>/templates/ai-art.py` 到 `gen/art.py`。先出 2–3 张风格样张 → 再出角色锚点图 → 用户确认后批量
4. 分层：有人物的中景用 `gen/art.py plate <id>`（/edit 去掉人物）出背景板，人物层用 `python <skill>/scripts/cutout.py art/<id>.png`（rembg isnet-anime，本地，和原图像素对齐）
5. 页面：Canvas 2D，`layer()` / `parallax()` 画图层，镜头表 `[起, 止, fn(t, lt, p)]`，参考 natsu-op/src/index.html
6. 声音：页面导出 `__events` → `sfx.py` 出点缀音效 → `python <skill>/scripts/mixdown.py music.wav sfx.wav mix.wav --dips <重点时刻>`（重点前压低配乐 + 音效 −9 dB + 增益限幅到 −14 LUFS）

**生图（GPT Image 2.5 Flare，Atlas `openai/gpt-image-2.5-flare/text-to-image` 和 `/edit`）**
- 竖屏一律 `size=1088x2560, quality=xhigh, output_format=png`。**high 档不按 size 出图**，会被缩到约 820×1919；xhigh 才给足尺寸。实测 xhigh 约 $0.05/张，/edit 带参考图约 $0.08/张；20 多张图加背景板全片约 $2.5
- 尺寸只能用 schema 里的枚举值（竖屏 9:16 附近是 `1088x2560`、`1152x2048`），`1440x2560` 会被拒
- 提示词分段：`[USE] → STYLE → SCENE → SUBJECT → COMPOSITION → LIGHTING & COLOR → PALETTE → FINISH → AVOID`。没有 negative 参数，负面提示词写成一段 AVOID 句子
- 防脏纹理和偏黄：风格词只用 clean crisp lineart / flat cel shading / matte clean skin / smooth gradients；不要 film grain、screentone、crosshatching、gritty、cinematic grading、8k、masterpiece。偏黄靠写明冷色色板和 "whites stay clean white"
- 角色一致性：一张正面 3/4 胸像当锚点，每条提示词重复同一段固定特征，加 "Do not redesign the character"；永远从锚点出发，不要在上一张编辑结果上接着改
- 姿势：扭头回望、背对扭身最容易画错（用户第一眼就指出），没有姿势参考图就不用。稳的是正面、3/4、纯侧脸、远景背影、局部特写；手部特写 xhigh 一次就对（握铁丝网），但要放大检查手指数
- 出图后逐张放大看：手指、肩颈、乱入文字、颗粒、偏色。透明抠图在暗底上看残边
- 偶尔会返回缩小的图（941×1672、817×1923）：背景板直接 LANCZOS 放大到 1088×2560 对齐；正片图放大也看不出

**抠图（cutout.py）的坑**
- 亮色小饰品（发夹）会被判成背景挖出洞 → 填洞（binary_fill_holes）
- 运动模糊背景的光斑会粘在人物边上 → 只留最大连通区域
- 人物占满画面上半部的图，"字放在人物身后"会被完全挡住，这种镜头字只能放前面

**动效手法（都写成 t 的纯函数，见 natsu-op/src/index.html）**
- 2.5D：背景板和人物层用不同的缩放 / 位移；`parallax(id, {mid})` 的 mid 回调画在两层之间（巨字压在人物身后）
- 构图：`dutch(deg)` 荷兰角（自动放大到盖满）、`panel(poly)` 斜向分格滑入、`card()` 全屏纯色闪卡、`bleed()` 出血巨字、`invert()` 反相闪、小物件 2–3 帧频闪
- 光：烟火光按拍变色照在脸上、光带扫过遮切点、代码烟火粒子、萤火虫光点、冲击帧色差、副歌末尾 bloom 冲白场
- 镜头起步不要用 ease-in-out，前 0.3 秒几乎不动会被判成死帧

**字体**
- 三种字体分工：毛笔（情绪词）、明朝 Noto Serif SC（歌词）、粗黑体 Noto Sans SC 900（全屏闪卡）。系统没有日文明朝体时，Noto Serif SC 含假名可用
- 毛笔字：`<skill>/scripts/brush.js` + KanjiVG 笔顺数据（`python <skill>/scripts/kanjivg.py svgdir strokes.js`，SVG 从 github.com/KanjiVG/kanjivg 的 kanji/ 目录按码位下载，CC BY-SA 3.0 需署名）。`makeWriter({text, x, y, size, t0, dur, weight, dry, tremble, glow, ink})`，一笔一笔按笔顺写出；依赖 p5.js（npm 固定 1.9.4）只用它的 noise
- 每句歌词换一种做法，并和画面内容呼应：车窗光块、汽水气泡、烧红后冷却、化成火星、随风飘、竖排错位。用户反馈：全片同一种"逐字升起"会单调；铁丝网细线这类装饰线不好看
- 字放在每个镜头的负空间里，可以斜、可以出血、可以被人物挡住一部分，不要都放左上

**声音**
- 成品 AI 歌很满，contrast.py 的 ≥6 dB 天然是 0：用 mixdown.py 在 3–4 个重点时刻前压低配乐 0.27 秒（−14 dB），再加重击音效
- 用整首歌，不要剪接：剪接结尾哪怕卡在强拍上，用户也听得出硬切
- AI 歌不保证按 prompt 的 BPM：要 180 出来 161.5，一切以 beats.py 实测为准

**环境坑**
- `python -I` 会关掉用户 site-packages（librosa、rembg 装在 --user 下就找不到）；只对不受信任的下载目录用 -I
- faster-whisper 的 CUDA 版缺 cublas64_12.dll，直接用 CPU int8
- 长补丁用 bash heredoc 容易被引号截断，改成先 Write 一个 .py 再运行
- 速度：80 秒 1080×1920 的页面，`--fast --size 540x960` 预览约 5–6 分钟
