# kiakun-skills

Kiakun 的 AI Agent Skills 集合仓库，兼容 OpenClaw、Claude Code 及所有支持 `SKILL.md` 格式的 Agent 平台。

本仓库汇集了多个面向内容平台自动化与知识管理的技能，每个技能都遵循 `SKILL.md` 开放标准，可被 Agent 自动识别和加载。

---

## 最新更新

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
| **bilibili-video-summary** | `skills/bilibili-video-summary/` | B站视频总结 | 链接解析、字幕/弹幕/评论提取、Whisper 语音转写、结构化总结 |
| **folder-to-vector-kb** | `skills/folder-to-vector-kb/` | 文件夹向量化 | 批量文档清洗、语义 chunk 切分、元数据补全、输出 `knowledge_base.jsonl` |
| **chinese-first-dialog** | `skills/chinese-first-dialog/` | 中文优先对话 | 默认简体中文回复，保留代码、命令、路径、配置键、API 标识符和原始错误文本 |
| **cc-switch-claude-provider** | `skills/cc-switch-claude-provider/` | Claude Code API 配置 | 通过 CC Switch 写入第三方 Claude-compatible API、切换 provider、冒烟测试 |
| **image-ppt-to-editable-pptx** | `skills/image-ppt-to-editable-pptx/` | 图片型 PPT 可编辑复刻 | 将截图/图片型 PPT 复刻为可编辑 PPTX，参数化字体、单形状占位图、PPT 背景格式与导出后 QA |
| **ppt-rebuild-workflow** | `skills/ppt-rebuild-workflow/` | PPT 重构工作流 | Mode A-E 路由、语义验收、自动坐标校准、视觉抽取、富文本、资产策略、复杂过渡与分级 QA |
| **game-ui-asset-pipeline** | `skills/game-ui-asset-pipeline/` | 游戏 UI 资产流水线 | 生成、清理、切片、验证并导入 Godot 游戏 UI 图标、HUD glyph、九宫格面板和按钮皮肤 |
| **gpt-image-2-api** | `skills/gpt-image-2-api/` | GPT Image 2 API | 日常默认标准版，复杂、高精度、多参考图或受支持的 2K/4K 规格时升级 VIP |

---

## 快速开始

### 前置条件

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) 包管理器
- Google Chrome 浏览器（小红书技能需要）
- Node.js >= 18（`gpt-image-2-api` 技能需要）

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
cp -r skills/cc-switch-claude-provider ~/.claude/skills/
cp -r skills/image-ppt-to-editable-pptx ~/.claude/skills/
cp -r skills/ppt-rebuild-workflow ~/.claude/skills/
cp -r skills/game-ui-asset-pipeline ~/.claude/skills/
cp -r skills/gpt-image-2-api ~/.claude/skills/

# Codex 示例
cp -r skills/gpt-image-2-api ~/.codex/skills/

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
# 填写 OPENAI_API_KEY；只有需要 AtlasCloud 备用编辑通道时才填写 ATLASCLOUD_API_KEY
node scripts/check-config.js
node scripts/generate.js --prompt "smoke test image" --dry-run --json
```

`check-config.js` 看到 `ready: true`、`hasApiKey: true`、`defaultProfile: auto`、`timeoutMs: none`
即代表标准/VIP 主通道配置可用。

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
    ├── gpt-image-2-api/
    │   ├── SKILL.md           # GPT Image 2 成本感知 API 生图与编辑
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

### bilibili-video-summary（B站视频总结）

当用户发送 B站视频链接时，自动识别 BV/AV 号，获取视频信息、字幕、弹幕、评论，并结合 Whisper 本地语音转写生成结构化总结。

**典型用法：**
> "帮我总结一下这个视频讲了什么：https://www.bilibili.com/video/BV1xx411c7mD"

详见 `skills/bilibili-video-summary/SKILL.md`。

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
- Mode A-E 路由：快版整页图、半可编辑重构、完全分层重构、先重做参考图、用户修改稿增量修正
- 语义优先：先判断参考图是否存在内容或版式方向错误，必要时转入 Mode D
- 自动坐标校准：使用测量脚本、自动宏观锚点和临时校准层减少手工点位确认
- 视觉抽取：逐页记录文字、形状、图片、间距、层级、置信度、来源证据和回退策略
- 字体校准：通过渲染候选比较字号、行距、文本框尺寸、内边距和最终 bbox
- 富文本处理：同一句多色/多字号文字优先用单文本框 runs，避免拆框造成异常空隙
- 资产策略：原资产优先，其次裁切/抠图，最后才重新生成；复杂低置信对象可自动烘焙或降级
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

### gpt-image-2-api（GPT Image 2 API）

通过 OpenAI-compatible 图片接口生成或编辑图片。日常任务默认使用成本更低的 `gpt-image-2`；复杂信息图、高精度内容、多个参考图或受支持的 2K/4K 规格使用 `gpt-image-2-vip`。VIP 编辑失败时可用 AtlasCloud 作为备用通道。提供 `--dry-run` 路由预览、`check-config.js` 配置检查、清晰的生成/编辑路径、参数校验、多图保存、超时与自动重试。

**典型用法：**
> "生成一张日常社交配图；如果是复杂信息图或 4K 海报，再自动使用 VIP。"

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
