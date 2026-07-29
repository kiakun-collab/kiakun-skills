# kiakun-skills

Kiakun 的 AI Agent Skills 集合仓库，兼容 OpenClaw、Claude Code 及所有支持 `SKILL.md` 格式的 Agent 平台。

本仓库汇集了多个面向内容平台自动化与知识管理的技能，每个技能都遵循 `SKILL.md` 开放标准，可被 Agent 自动识别和加载。

---

## 最新更新

### 2026-07-15：新增 `deliverable-purifier` 客户交付物终稿净化 Skill

面向 PPT 文案、方案、报告、品牌策略和业务模板的最终编辑层：清除提示词痕迹、内部创作说明与意外占位，同时锁定事实、数据、引用、声明、专有名词和用户指定字段。通过受众正文/授权备注/内部过程三层边界、`KEEP / REWRITE / REMOVE / RESOLVE` 四类处置及 `FINAL / REVIEW / COMPARE` 三种输出模式，避免清洗时误删、误改或编造。与 `clean-deliverable` 分工：后者负责通用防元信息泄漏和跨模型约束提示词，本 skill 专注客户业务材料的保真终稿。

### 2026-07-06：新增 `clean-deliverable` 纯净交付守卫 Skill

新增模型通用的"防元信息泄漏"skill：防止占位符（"一个吸引人的标题"）、回声输入（把用户 brief 要点原样贴进成品）和思考残留混进幻灯片、文案、报告、代码等交付物。

- **核心原则**：分清三层，只交付"呈现内容"——幕后输入与思考过程一字不留；判断标准只有一条："这句话是说给受众看的，还是说给作者听的？"
- **三种用法**：① 产出可贴进任意目标模型（GPT / Gemini / Claude）system prompt 的约束提示词；② 审查并清洗已有交付物，输出对照表 + 干净版（图片类交付物给出修正后的重生成提示词，可接 `gpt-image-2-api`）；③ Agent 自己生成交付物时的交付前自检（信息缺口标注在成品外面）。
- **防误报**：信号词（"应该 / 需要 / 此处 / TODO"）是线索不是判决，命中后回到受众视角复核；附按交付物形态（幻灯片/文案/代码/模板）的高发泄漏对照表。纯 Markdown skill，无脚本依赖，任何支持 `SKILL.md` 的平台可直接使用。

### 2026-07-05：`ppt-rebuild-workflow` 引入"纯图片基线 deck"硬约束

把原本的死胡同预览模式 Mode A 重定义为**纯图片基线 deck**，并接入 Mode B/C 重构主流程：

- **Mode A 重定义**：其本质就是"做一份纯图片 PPT（每页整页图铺满，不需参考测量）"。它既是"只要平铺预览"时的独立交付，也是 Mode B/C 重构前**必建的对照基线**。
- **硬约束**：Mode B/C 重构前必须先建纯图片基线 deck、用同一交付渲染后端渲染为 `baseline-render/`；编辑版还原度必须**同时对照原始参考图与 baseline-render**（同后端同画布的 apples-to-apples 主判据，消除源图/浏览器 vs PPT 渲染的尺度与渲染器差异）；基线本身渲染异常先修环境（兜底地板）；未建基线或基线对照未过，不得判 Level 2/3 通过。
- 工具复用：基线渲染与对照直接用现有 `calibrate_reference_render.py` / `make_reference_render_comparison.py`，无需新脚本。同步 mode-selection / SKILL 推荐流程 / implementation-guardrails / qa-gates / Level 2·3 交付清单；契约与全部 66 单测保持全绿。

### 2026-07-05：`ppt-rebuild-workflow` 补充占位图/背景/字号规范（借鉴 image-ppt）

从 `image-ppt-to-editable-pptx` 提炼几条关键约束补进 PPT 重构 skill：

- **占位图规范**：截图/示例图/UI/照片墙/视频区默认只做**单一原生占位对象**，禁止内部拼假细节，命名带角色前缀便于审计统计与用户一键删除。
- **背景规范**：纯色/规则渐变底色用 **PPT 页面背景格式（`<p:bg>`）**，不要用整页实心矩形当背景层；并区分"页面底色"与 Mode B/C 的"背景环境素材"。
- **字号偶数整数 pt**：`audit_pptx_structure.py` 新增 `fontSizesPt` / `nonEvenFontSizesPt`，把 image-ppt 的"字号须偶数磅"手工包内检查**自动化**（勿用 px 判断偶数）。
- 同步 `implementation-guardrails.md`（构建细则+报告项+常见错误）、契约文档与单测（66 全绿）。

### 2026-07-05：`bilibili-video-summary` 重构为「决策助手」（架构升级）

从"下载视频数据"重构为**帮你快速判断长视频值不值得看**：核心原则「**脚本预消化 → LLM 只理解**」——脚本以最低成本拿全原始文本素材 + 预算好的统计信号，输出**≤15KB 固定量级 JSON**，由 Claude 生成"值得完整看/看高能点/看总结即可/不值得看"的决策导向报告。

- **修复一批真实缺陷**：评论 API 用错类导致静默失败、字幕只拿元数据从未下载正文、不支持 AV 号、`get_info` 重复调用、无错误处理直接崩溃等（对照 Nemo2011/bilibili-api 官方源码核实）。
- **信号聚合（差异化核心）**：弹幕词频 Top20 / 时间密度数组 / Top5 高能峰值+代表弹幕（与官方 pbp 高能进度条互印证）；热评+楼中楼（争议交锋）；点赞/收藏/投币/弹幕密度等价值信号+经验基准。
- **优先级链**：字幕正文（主）→ Whisper 兜底（可按峰值采样转写）；B站官方 AI 小结仅作辅助分段锚点。
- **单入口 `bilibili_digest.py`** + 24h 登录态分离缓存 + 并行限流；`bilibili_whisper.py` 修复 403（aiohttp+Referer/UA）、ffmpeg 16k 转码、按时长选模型。
- **工程化**：`pyproject.toml` + 27 个离线单测（网络全 mock）；`SKILL.md` 重写为 JSON 契约+决策报告模板+错误指引。开发与真实验证记录见 `skills/bilibili-video-summary/DEVELOPMENT_REPORT.md`。

### 2026-07-05：新增 `html-to-pptx` HTML 转可编辑 PPTX Skill

新增把 AI 生成的**固定比例 HTML 页面**转成高还原度、高可编辑度 PPTX 的独立 skill。与图片型复刻不同,它走**浏览器渲染 + DOM 几何提取**路线,直接测最终盒子而不解析布局语义。

- **五段流水线**:`extract_html.py`（Playwright chromium,1280×720 视口,DPR=2 截图,`document.fonts.ready` 后测几何/逐行文字/样式）→ `build_layout_spec.py`（角色分类、同 bounds 合并、语义分组、可表达性评分、fontMap）→ `build_pptx.py`（python-pptx + 直写 OXML 渐变/阴影/圆角/旋转/恒等变换组）→ `render_pptx_com.py`（PowerPoint COM 导出 2560×1440,规避僵尸进程）→ `qa_gate.py`（全页 SSIM + 逐元素 + 文字折行双门禁 + ≤3 轮自动返修）。
- **三个硬目标**:超高还原度(QA 双门禁)、超高可编辑度(文字=原生文本框、形状=原生 autoshape、图片=独立对象,仅不可表达元素才烘焙且逐个记 `bakedReason`)、干净整洁(无冗余 wrapper、同 bounds 合并、z-order 正确)。
- **可编辑度优先**:文字**绝不烘焙**,返修只加宽框/微调字号;非文字视觉差异大才最小降级为烘焙 PNG(Playwright 按 DOM 路径 `element_handle.screenshot()` 补截)。
- QA 工具默认路径复用同级 `ppt-rebuild-workflow/scripts`(`HTML2PPTX_QA_TOOLKIT` 可覆盖)。`run_pipeline.py` 一键驱动;离线组 37 测试 + COM 组 4 测试(`skipif` 隔离)全绿。
- 环境前置:PowerPoint(Office16)已激活 + 交互式会话 + Playwright chromium。契约见 `references/pipeline-contracts.md`。

### 2026-07-05：`ppt-rebuild-workflow` P0–P5 优化(性能 / 健壮性 / 去重 / 功能 / 文档)

对 PPT 重构 skill 做了一轮系统优化,测试从 37 → 64 全绿:

- **去重与依赖**:抽取共享模块 `_pptx_common` / `_image_common` / `_io_common`,新增 `pyproject.toml`。
- **性能**:`extract_reference_measurements.py` 逐页并行化(`--jobs`,并行/串行逐字节一致);calibrate 无 numpy 回退路径 2.5× 提速并补齐此前零覆盖的匹配路径测试。
- **健壮性/契约**:修复 calibrate 与 make_comparison 对同一文件名算出不同页码的契约 bug;收窄过宽 `except`;CJK 叠加字体系统探测;`make_comparison --allow-missing`、`calibrate --verbose`。
- **功能**:新增顶层驱动器 `run_pipeline.py`、`--doctor` 引擎自检、`--verbose` 进度、audit 安静模式。
- **文档**:新建 `qa-gates.md` 门禁单一事实源、16:9 降级声明、模板漂移修正、字体候选种子规则。

### 2026-06-22：新增 `player-interaction-design` 玩家互动设计 Skill

新增面向游戏 UI、玩法互动、引导、挑战链路和失败恢复的玩家互动设计 skill。它要求 Agent 在实现、拆任务包或写验收前先写“玩家互动合同”，明确玩家当前阶段、入口、第一眼信息、主操作、成功反馈、阻断原因、恢复路径、下一步和 `not_proven`。

本 skill 同时打包了合同 guide、可复制模板和轻量校验脚本，帮助把“玩家真实怎么交互”从软提示变成可检查的工程约束。

### 2026-06-22：`ppt-rebuild-workflow` 可编辑 PPT 重构流程增强

本次更新聚焦图片/截图型 PPT 重构的真实生产问题：视觉坐标难测、形状难复原、字号与行距漂移、复杂图片边缘难处理，以及多色文字被拆框后出现异常空隙。

**流程与渐进式披露**
- 精简 `SKILL.md` 主入口：合并模式说明和加载路径，改为 Mode A-E 表格，减少重复阅读。
- 输入确认改为两级：先确认所有模式通用字段，再按 Mode B/C/E 补充可编辑边界、资产策略和视觉抽取字段。
- 推荐流程调整为先做语义验收，确认不需要 Mode D 后再执行 Mode B/C 自动坐标校准。
- 新增醒目的“始终防错”规则，避免先写 `layout-spec` 后倒填测量、把候选框误当最终形状清单。
- Mode C Level 3 交付现在在主流程中明确要求完成 `level-3-delivery-checklist.md`。

**视觉抽取与坐标校准**
- 新增自动坐标锁和视觉抽取流程文档，要求 Mode B/C 在构建前生成参考图测量、自动宏观锚点、临时校准层和逐页 `visual-extraction`。
- 新增 `extract_reference_measurements.py`，用于从参考图生成候选文本行、区域、线条、主色、坐标变换、自动锚点和标注图。
- 新增 `visual-extraction-template.json`、`typography-calibration-template.json`，把文字、形状、图片、间距、字体候选和渲染指标落盘。
- `layout-spec` 模板新增 `coordinateCalibrationId`、`sourceExtractionId`、`textFlowPolicy` 和 `textRuns`，避免只在构建脚本里保存关键参数。

**文字与富文本**
- 明确同一句标题、口号或强调句中的多色/多字号片段应优先使用单文本框富文本 runs，不应拆成多个相邻文本框。
- QA 新增检查：富文本合并后必须保留每个 run 的颜色、字号、字重和描边，不能被统一文本框样式覆盖。
- 字号、行距、文本框宽高和内边距要求通过 2-4 个渲染候选校准，不能只靠肉眼估算或自动缩小文字。

**图片、形状与资产策略**
- 明确资产优先级：原 PPTX 图片优先，其次从参考图裁切/抠图，最后才考虑重新生成；避免人物、产品和主视觉被 AI 重画后失真。
- 对复杂低置信形状、雾气、光晕、图片边缘融合和不规则过渡，默认采用 `baked-asset` 或 Mode B fallback，不强行用原生形状硬画。
- 支持记录参考图中有意的 shape/image 覆盖关系，例如标签压住图片、角标遮挡主图等，避免被通用重叠门禁误判。

**QA 与测试**
- Level 2/3 QA 增强了文本可读性、参考图还原度、视觉重叠、整页图片风险、字体槽位、形状角色、视觉过渡和自动降级记录。
- QA 报告模板新增视觉抽取、坐标校准、字体校准、富文本、形状角色、允许覆盖、视觉还原度和剩余风险字段。
- 新增和扩展了结构审计、文本框审计、参考图测量、配对渲染对照和模式契约测试。

---

## 技能清单

| 技能 | 路径 | 说明 | 核心能力 |
|------|------|------|----------|
| **xiaohongshu** | `skills/xiaohongshu/` | 小红书自动化 | 认证登录、内容发布、搜索发现、社交互动、复合运营分析 |
| **bilibili-video-summary** | `skills/bilibili-video-summary/` | B站视频决策助手 | 脚本预消化为 ≤15KB 信号 JSON；字幕正文/弹幕聚合(词频·密度·高能峰值)/热评楼中楼/价值信号/Whisper 兜底，LLM 出"值不值得看"决策报告 |
| **folder-to-vector-kb** | `skills/folder-to-vector-kb/` | 文件夹向量化 | 批量文档清洗、语义 chunk 切分、元数据补全、输出 `knowledge_base.jsonl` |
| **chinese-first-dialog** | `skills/chinese-first-dialog/` | 中文优先对话 | 默认简体中文回复，保留代码、命令、路径、配置键、API 标识符和原始错误文本 |
| **clean-deliverable** | `skills/clean-deliverable/` | 纯净交付守卫 | 防占位符/回声输入/思考残留泄漏进交付物；约束提示词、审查清洗、交付前自检三种用法 |
| **deliverable-purifier** | `skills/deliverable-purifier/` | 客户交付物终稿净化 | 客户业务材料的保真清洗、内容分层、四类处置与三种输出模式 |
| **cc-switch-claude-provider** | `skills/cc-switch-claude-provider/` | Claude Code API 配置 | 通过 CC Switch 写入第三方 Claude-compatible API、切换 provider、冒烟测试 |
| **image-ppt-to-editable-pptx** | `skills/image-ppt-to-editable-pptx/` | 图片型 PPT 可编辑复刻 | 将截图/图片型 PPT 复刻为可编辑 PPTX，参数化字体、单形状占位图、PPT 背景格式与导出后 QA |
| **ppt-rebuild-workflow** | `skills/ppt-rebuild-workflow/` | PPT 重构工作流 | 语义验收、自动坐标校准、视觉抽取、富文本、资产策略、纯图片基线对照（硬门禁）、占位图/背景/字号规范与分级 QA |
| **html-to-pptx** | `skills/html-to-pptx/` | HTML 转可编辑 PPTX | 浏览器渲染 + DOM 几何提取、角色分类与整洁扁平化、原生对象构建、PowerPoint COM 渲染、SSIM 双门禁与自动返修 |
| **game-ui-asset-pipeline** | `skills/game-ui-asset-pipeline/` | 游戏 UI 资产流水线 | 生成、清理、切片、验证并导入 Godot 游戏 UI 图标、HUD glyph、九宫格面板和按钮皮肤 |
| **player-interaction-design** | `skills/player-interaction-design/` | 游戏玩家互动设计 | 先写玩家入口、主操作、可见反馈、失败恢复和证据层级合同 |
| **gpt-image-2-api** | `skills/gpt-image-2-api/` | GPT Image 2 API | XApex 默认异步，AtlasCloud 编辑备用，aifast 最终备用 |
| **pitch-visual-prompting** | `skills/pitch-visual-prompting/` | 比稿视觉提示词 | 将多品牌比稿 brief 和参考资料转化为可执行、可迭代的图像生成提示词 |

---

## 快速开始

### 前置条件

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) 包管理器
- Google Chrome 浏览器（小红书技能需要）
- Node.js >= 18（`gpt-image-2-api` 技能需要）
- Playwright chromium + 已激活的 PowerPoint（Office16，Windows；`html-to-pptx` 技能的渲染与 QA 需要）

### 安装

1. 克隆仓库到本地：

```bash
git clone https://github.com/kiakun-collab/kiakun-skills.git
cd kiakun-skills
```

2. 安装共享依赖：

```bash
uv sync
```

3. 将需要的 skill 目录复制或链接到你的 Agent 的 skills 目录下：

```bash
# Claude Code 示例
cp -r skills/xiaohongshu ~/.claude/skills/
cp -r skills/bilibili-video-summary ~/.claude/skills/
cp -r skills/chinese-first-dialog ~/.claude/skills/
cp -r skills/clean-deliverable ~/.claude/skills/
cp -r skills/deliverable-purifier ~/.claude/skills/
cp -r skills/cc-switch-claude-provider ~/.claude/skills/
cp -r skills/image-ppt-to-editable-pptx ~/.claude/skills/
cp -r skills/ppt-rebuild-workflow ~/.claude/skills/
cp -r skills/html-to-pptx ~/.claude/skills/
cp -r skills/game-ui-asset-pipeline ~/.claude/skills/
cp -r skills/player-interaction-design ~/.claude/skills/
cp -r skills/gpt-image-2-api ~/.claude/skills/
cp -r skills/pitch-visual-prompting ~/.claude/skills/

# Codex 示例
cp -r skills/deliverable-purifier ~/.codex/skills/
cp -r skills/player-interaction-design ~/.codex/skills/
cp -r skills/gpt-image-2-api ~/.codex/skills/
cp -r skills/pitch-visual-prompting ~/.codex/skills/

# OpenClaw 示例
cp -r skills/xiaohongshu <openclaw-project>/skills/
```

> Agent 会自动识别每个 skill 目录下的 `SKILL.md` 并加载对应能力。

### gpt-image-2-api 快速配置

这个技能不依赖仓库的 Python 环境，复制 skill 后让 Agent 进入对应目录运行 Node 脚本即可。
把真实密钥放在本机配置文件中，不要提交到仓库：

```bash
cd <agent-skills-dir>/gpt-image-2-api
cp .env.example .gateway.env
# 默认主通道填写 XApex 图片组 XAPEX_API_KEY
# 编辑备用填写 ATLASCLOUD_API_KEY；最终 aifast 备用填写 OPENAI_API_KEY
node scripts/check-config.js
node scripts/generate.js --prompt "smoke test image" --dry-run --json
node scripts/generate.js --prompt "XApex async smoke test" --quality low --dry-run --json
```

`check-config.js` 通过 `hasApiKey` 与 `hasXapexApiKey` 分别报告 aifast 和 XApex 凭据状态；
XApex 默认异步并使用独立 Base URL、模型、尺寸、quality、重试和轮询配置。

---

## 仓库结构

```
kiakun-skills/
├── README.md                  # 本文件
├── SKILL.md                   # Agent 统一入口：意图路由到各子技能
├── pyproject.toml             # 共享 Python 依赖配置
├── LESSONS_LEARNED.md         # 项目经验与踩坑记录
├── scripts/                   # 共享自动化引擎与工具脚本
│   ├── xhs/                   # 小红书 CDP 浏览器自动化引擎
│   ├── dy/                    # 抖音相关脚本
│   └── cli.py                 # 统一 CLI 入口
├── tests/                     # 测试用例
├── references/                # 参考资料与模板
└── skills/                    # 所有 Skill 定义
    ├── xiaohongshu/
    │   ├── SKILL.md           # 小红书总入口
    │   ├── xhs-auth/          # 认证管理
    │   ├── xhs-explore/       # 内容发现
    │   ├── xhs-interact/      # 社交互动
    │   ├── xhs-publish/       # 内容发布
    │   ├── xhs-content-ops/   # 复合运营
    │   └── xhs-research-bridge/ # 研究桥接
    ├── bilibili-video-summary/
    │   └── SKILL.md           # B站视频总结
    ├── chinese-first-dialog/
    │   ├── SKILL.md           # 中文优先对话
    │   └── agents/
    ├── clean-deliverable/
    │   ├── SKILL.md           # 纯净交付守卫
    │   └── agents/
    ├── deliverable-purifier/
    │   ├── SKILL.md           # 客户业务交付物终稿净化
    │   └── agents/
    ├── cc-switch-claude-provider/
    │   ├── SKILL.md           # CC Switch Claude Code 第三方 API 配置
    │   ├── agents/
    │   └── scripts/
    ├── image-ppt-to-editable-pptx/
    │   ├── SKILL.md           # 图片型 PPT 可编辑复刻
    │   └── agents/
    ├── ppt-rebuild-workflow/
    │   ├── SKILL.md           # PPT 重构模式、可编辑边界与 QA 工作流
    │   ├── agents/
    │   ├── assets/
    │   ├── references/
    │   ├── scripts/
    │   └── tests/
    ├── game-ui-asset-pipeline/
    │   ├── SKILL.md           # 游戏 UI 资产流水线
    │   ├── agents/
    │   ├── references/
    │   └── scripts/
    ├── player-interaction-design/
    │   ├── SKILL.md           # 玩家互动设计合同
    │   ├── agents/
    │   ├── assets/
    │   ├── references/
    │   └── scripts/
    ├── gpt-image-2-api/
    │   ├── SKILL.md           # GPT Image 2 异步容错 API 生图与编辑
    │   ├── agents/
    │   ├── references/
    │   └── scripts/
    └── folder-to-vector-kb/
        └── SKILL.md           # 文件夹向量化知识库
```

---

## 各技能简介

### xiaohongshu（小红书自动化）

基于 Python CDP 浏览器自动化引擎，支持 Agent 通过自然语言操作小红书。

**子技能：**
- `xhs-auth` — 登录检查、二维码登录、多账号切换
- `xhs-explore` — 关键词搜索、笔记详情、用户主页、首页推荐
- `xhs-interact` — 评论、回复、点赞、收藏
- `xhs-publish` — 图文 / 视频 / 长文发布、分步预览
- `xhs-content-ops` — 竞品分析、热点追踪、批量互动、内容创作
- `xhs-research-bridge` — 研究数据桥接

**典型用法：**
> "搜索露营赛道最近的爆款笔记，分析选题方向并帮我写一版草稿。"

详见 `skills/xiaohongshu/SKILL.md`。

---

### bilibili-video-summary（B站视频决策助手）

当用户发送 B站视频链接时，`bilibili_digest.py` 拉取视频信息、字幕正文、弹幕、热评与官方 AI 小结，**在脚本内预消化为统计信号**（弹幕词频/密度/高能峰值、热评楼中楼、价值互动率），输出 ≤15KB JSON，由 Claude 生成"值得完整看 / 看高能点 / 看总结即可 / 不值得看"的决策导向报告。无 CC 字幕时用 Whisper 兜底转写（需 ffmpeg）。

**典型用法：**
> "帮我判断这个视频值不值得看：https://www.bilibili.com/video/BV1xx411c7mD"

详见 `skills/bilibili-video-summary/SKILL.md`；开发与真实验证记录见 `DEVELOPMENT_REPORT.md`。

---

### folder-to-vector-kb（文件夹向量化）

将指定文件夹中的 PPT / PDF / DOCX / Markdown / TXT 等文档，整理为可用于向量检索的结构化知识库。

**核心能力：**
- 终稿识别与过程稿过滤
- 语义 chunk 切分（保持语义边界）
- 元数据补全（项目名、文档类型、标签）
- 输出 `knowledge_base.jsonl`

**典型用法：**
> "把 `/path/to/cases` 文件夹整理成可以 embedding 的知识库。"

详见 `skills/folder-to-vector-kb/SKILL.md`。

---

### chinese-first-dialog（中文优先对话）

让 Agent 在该工作区默认使用简体中文沟通，同时保留代码、命令、文件路径、配置键、API 标识符和原始错误文本不被翻译。

**典型用法：**
> "之后默认用中文回复，但代码和命令保持原文。"

详见 `skills/chinese-first-dialog/SKILL.md`。

---

### clean-deliverable（纯净交付守卫）

防止元信息泄漏进交付物（幻灯片、文案、报告、邮件、代码等）：自造占位符、回声输入（把 brief 要点原样贴进成品）、思考过程残留。模型通用（GPT / Gemini / Claude 均适用），纯 Markdown 无脚本依赖。

**三种用法：**
- 用法 A — 产出可贴进目标模型 system prompt 的约束提示词
- 用法 B — 审查并清洗已有交付物（对照表 + 干净版；图片类给重生成提示词）
- 用法 C — Agent 生成交付物时的交付前自检

**典型用法：**
> "帮我检查这份幻灯片文案有没有把我给你的要点直接抄进去，清洗一版干净的。"

详见 `skills/clean-deliverable/SKILL.md`。

---

### deliverable-purifier（交付物纯净化）

把 PPT 页面文案、营销方案、提案、品牌策略、报告和业务模板整理为可直接交付的终稿。清除提示词痕迹和内部创作说明，同时保护事实、数字、引用、必要声明、speaker notes、production notes 及用户明确要求的占位符。

**典型用法：**
> "把这份客户汇报文案净化成最终版，保留所有数据、引用和图片占位，不要把制作备注写进页面正文。"

详见 `skills/deliverable-purifier/SKILL.md`。

---

### cc-switch-claude-provider（Claude Code API 配置）

把第三方 Claude-compatible `base URL` 和 `API key` 写入本地 CC Switch，自动切换 Claude provider，并运行一次 `claude` 冒烟测试确认 Claude Code 可用。

**典型用法：**
> "用 CC Switch 帮我配置 Claude Code，base url 是 https://example.com/api，key 是 sk-xxx。"

详见 `skills/cc-switch-claude-provider/SKILL.md`。

---

### image-ppt-to-editable-pptx（图片型 PPT 可编辑复刻）

将图片型 PPT、页面截图或栅格化演示稿参考图重建为可编辑 `.pptx`，强调普通文字文本框化、PPT 原生形状、单一矩形占位图、页面背景格式、参数化字体与导出后重新导入渲染检查。

**典型用法：**
> "把这几张图片型 PPT 复刻成可编辑 PPTX，字体用腾讯体w7。"

详见 `skills/image-ppt-to-editable-pptx/SKILL.md`。

---

### ppt-rebuild-workflow（PPT 重构工作流）

用于把幻灯片截图、图片型 PPTX、AI 生成参考页或用户修改稿重构为可编辑 PPTX。根据速度、可编辑性和还原度选择 Mode A-E，并对语义、坐标、视觉抽取、字体、对象角色、文字碰撞、整页图片风险、页码配对、边缘融合和视觉还原度执行分级 QA。

**核心能力：**
- 模式路由：纯图片基线 deck（Mode A 本质）、半可编辑重构、完全分层重构、先重做参考图、用户修改稿增量修正
- **纯图片基线对照（硬门禁）**：Mode B/C 重构前必建纯图片基线 deck，用同一后端渲染为 `baseline-render/`，编辑版还原度必须同时对照原始参考图与该基线（同后端同画布 apples-to-apples 主判据），未过不判 Level 2/3 通过
- 语义优先：先判断参考图是否存在内容或版式方向错误，必要时转入 Mode D
- 自动坐标校准：使用测量脚本、自动宏观锚点和临时校准层减少手工点位确认
- 视觉抽取：逐页记录文字、形状、图片、间距、层级、置信度、来源证据和回退策略
- 字体校准：通过渲染候选比较字号、行距、文本框尺寸、内边距和最终 bbox
- 富文本处理：同一句多色/多字号文字优先用单文本框 runs，避免拆框造成异常空隙
- 资产策略：原资产优先，其次裁切/抠图，最后才重新生成；复杂低置信对象可自动烘焙或降级
- 占位图/背景/字号规范：截图区单一原生占位对象、纯色底色用页面背景格式（非整页矩形）、字号须偶数整数 pt（`audit_pptx_structure.py` 的 `nonEvenFontSizesPt` 自动列出）
- QA 门禁：结构审计、文本框审计、视觉重叠审计、参考图还原度审计、复杂过渡检查和分级交付 checklist

**典型用法：**
> "按照这些参考图重构为可编辑 PPTX，保留文字可编辑，并检查复杂渐隐和整体还原度。"

详见 `skills/ppt-rebuild-workflow/SKILL.md`。

---

### game-ui-asset-pipeline（游戏 UI 资产流水线）

将 AI 生成的游戏 UI 位图整理成可用于 Godot 的生产资产，强调由 AI 负责视觉风格、脚本负责几何切片、Godot 负责文字布局和交互。

**核心能力：**
- 图标表、菜品/素材图标、HUD glyph、按钮皮肤和装饰组件的风格约束
- chroma-key 抠图、固定网格切片、透明边缘和 alpha 验证
- Godot `res://` 路径、Theme、`TextureRect`、`StyleBoxTexture` 与九宫格导入规则

**典型用法：**
> "用 game-ui-asset-pipeline 帮我给 Godot 餐厅游戏生成一套轻量动漫风 HUD 图标表，并切片导入。"

详见 `skills/game-ui-asset-pipeline/SKILL.md`。

---

### player-interaction-design（玩家互动设计）

用于游戏 UI、玩法互动、引导、挑战链路、任务包拆分和体验验收。它要求 Agent 在动手实现前先写玩家互动合同，避免只改系统状态而忽略真实玩家的入口、主操作、反馈和失败恢复。

**核心能力：**
- 完整/短合同判断：新入口、新面板、新弹窗、新挑战或失败恢复默认写完整合同。
- 玩家链路前置：先写玩家当前阶段、目标、入口、第一眼信息、主操作、成功反馈、阻断原因、恢复路径和下一步。
- 证据层级收口：用 `logic_runner`、`ui_contract`、`interactive_mcp`、`visible_capture`、`manual_canary` 和严格条件下的 `natural UI-only` 区分 claim scope。
- 结构化字段约束：`证据层级` 只写枚举，runner、fixture、加速、bridge helper、fallback 等说明放到 `证据说明` 或 `not_proven`。
- 工程化配套：内置合同 guide、任务包模板和 `validate_player_interaction_contract.py` 校验脚本。

**典型用法：**
> "用 player-interaction-design 审查这个游戏 UI/玩法任务的玩家入口、反馈与失败恢复。"

详见 `skills/player-interaction-design/SKILL.md`。

---

### gpt-image-2-api（GPT Image 2 API）

通过 OpenAI-compatible 图片接口生成或编辑图片。默认 `auto` 路由首先使用 XApex 异步任务；图片编辑失败后依次尝试 AtlasCloud 与 aifast，纯文生图因 AtlasCloud 模型仅支持编辑而直接回退到 aifast。显式 profile 可强制 XApex、AtlasCloud 或 aifast 标准/VIP。提供 `--dry-run` 路由预览、`check-config.js` 配置检查、参数校验、多图保存、超时与自动重试。

**典型用法：**
> "用默认异步渠道生成一张社交配图；失败时按可用渠道自动回退。"

详见 `skills/gpt-image-2-api/SKILL.md`。

---

## 开发

```bash
uv sync                    # 安装依赖
uv run ruff check .        # Lint 检查
uv run ruff format .       # 代码格式化
uv run pytest              # 运行测试
```

---

## License

MIT
