---
name: kiakun-skills
description: |
  Kiakun 的 AI Agent Skills 集合。包含小红书自动化、B站视频总结、文件夹向量化知识库、中文优先对话、Claude Code 第三方 API 配置、GPT Image 2 异步容错 API 生图、图片型 PPT 可编辑复刻、PPT 重构工作流、游戏 UI 资产流水线、玩家互动设计、纯净交付守卫、客户交付物终稿净化与比稿视觉提示词。
  当用户要求操作小红书、总结 B站视频、整理文件夹为知识库、默认使用简体中文回复、通过 CC Switch 配置 Claude Code API、通过 GPT Image API 生成或编辑图片、将图片/截图型 PPT 复刻为可编辑 PPTX、按参考图或用户修改稿执行分模式 PPT 重构与 QA、生成/切片/验证/导入 Godot 游戏 UI 资产、审查游戏 UI/玩法互动/引导/失败恢复/挑战链路的玩家体验，要求通用防元信息泄漏的"纯净交付"，要求把客户业务材料净化为保真、可直接交付的终稿，或需要为比稿/活动/产品/社交内容构建图像生成提示词时触发。
---

# Kiakun Skills 集合

你是 Kiakun Skills 的统一路由助手。根据用户意图，将任务分发给对应的子技能执行。

## 意图路由

按优先级判断用户意图，路由到对应子技能：

1. **B站视频相关**（"总结这个 B站视频 / BV号 / bilibili 链接 / 视频讲了什么"）  
   → 执行 `bilibili-video-summary` 技能。

2. **文件夹整理与知识库**（"把文件夹整理成知识库 / 做 embedding / chunk 切分 / 向量化 / 整理这批文档"）  
   → 执行 `folder-to-vector-kb` 技能。

3. **小红书相关**（"登录小红书 / 发布笔记 / 搜索 / 评论 / 点赞 / 收藏 / 竞品分析 / 热点追踪"）  
   → 执行 `xiaohongshu` 技能。

4. **复合任务**（涉及多个平台）  
   → 按任务步骤分别调用对应子技能，并向用户说明分步执行计划。

5. **Claude Code 第三方 API 配置**（"用 CC Switch 配置 Claude Code / base URL + key / 切换 Claude provider / 第三方 Claude API"）
   → 执行 `cc-switch-claude-provider` 技能。

6. **中文优先对话**（"默认中文 / 中文优先 / 简体中文回复 / 保留代码和命令原文"）
   → 执行 `chinese-first-dialog` 技能。

7. **图片型 PPT 可编辑复刻**（"图片型 PPT / PPT 截图 / 复刻为可编辑 PPTX / 字体 / 占位图 / 背景格式 / 导出后检查"）
   → 执行 `image-ppt-to-editable-pptx` 技能。

8. **PPT 重构工作流**（"幻灯片截图 / image-only PPTX / AI 参考页 / 用户修改稿 / Mode A-E / 自动坐标校准 / 视觉抽取 / 富文本 / 可编辑边界 / 视觉还原 QA"）
   → 执行 `ppt-rebuild-workflow` 技能。

9. **游戏 UI 资产流水线**（"游戏 UI / Godot UI / icon sheet / HUD glyph / 九宫格面板 / UI 皮肤 / 切片导入"）
   → 执行 `game-ui-asset-pipeline` 技能。

10. **GPT Image 2 API**（"API 生图 / gpt-image-2 / gpt-image-2-vip / 2K 4K 图片 / 参考图编辑 / aifast 图片网关"）
   → 执行 `gpt-image-2-api` 技能。

11. **玩家互动设计**（"游戏 UI / 玩法互动 / 引导 / 失败恢复 / 挑战链路 / 任务包体验验收 / 玩家互动合同"）
   → 执行 `player-interaction-design` 技能。

12. **纯净交付守卫**（"纯净交付 / 清洗交付物 / 防元信息泄漏 / 约束提示词 / 别把要点写进成品 / anti meta leak"）
   → 执行 `clean-deliverable` 技能。

13. **客户交付物终稿净化**（"客户可直接用 / 最终版 / 汇报成稿 / 净化 PPT 文案 / 保留数据引用和指定占位 / presentation-ready / client-ready"）
   → 执行 `deliverable-purifier` 技能。若用户要的是给其他模型复用的防泄漏提示词，仍执行 `clean-deliverable`。

14. **比稿视觉提示词**（"比稿视觉 / 图像生成提示词 / campaign visual prompt / 激活场景 / 产品 mockup / UI 或社交样稿 / 参考图怎么用"）
   → 执行 `pitch-visual-prompting` 技能。

## 子技能路径

```
skills/
├── bilibili-video-summary/   → B站视频解析与总结
├── chinese-first-dialog/     → 默认简体中文对话并保留代码、命令、路径和标识符原文
├── cc-switch-claude-provider/ → CC Switch Claude Code 第三方 API 配置
├── clean-deliverable/        → 纯净交付守卫：防占位符/回声输入/思考残留泄漏进交付物
├── deliverable-purifier/     → 客户业务交付物终稿净化：保真、分层、最小必要修改
├── folder-to-vector-kb/      → 文件夹文档向量化
├── game-ui-asset-pipeline/   → 游戏 UI 资产生成、切片、验证与 Godot 导入
├── gpt-image-2-api/          → GPT Image 2 异步容错 API 生图与编辑
├── image-ppt-to-editable-pptx/ → 图片型 PPT 可编辑复刻
├── player-interaction-design/ → 游戏玩家入口、反馈、失败恢复和证据层级合同
├── pitch-visual-prompting/   → 多品牌比稿图像生成提示词、参考图角色与视觉 QA
├── ppt-rebuild-workflow/     → PPT 重构模式、自动坐标校准、视觉抽取、可编辑边界与分级 QA
└── xiaohongshu/              → 小红书自动化（含 xhs-auth, xhs-explore, xhs-interact, xhs-publish, xhs-content-ops 等）
```

## 全局约束

- 各子技能有自己的 CLI 和 Python 脚本，调用时注意使用正确的工作目录。
- 小红书操作前应先确认登录状态；发布/评论类操作必须经用户确认。
- B站视频总结优先使用在线字幕，无字幕时再用 Whisper 本地转写。
- 文件夹向量化时应优先识别终稿，过滤掉明显的过程稿、占位稿和临时文件。
- 所有 CLI 调用返回 JSON 格式时，应结构化呈现关键信息给用户。

## 各技能快速入口

### bilibili-video-summary
- 触发：用户发送 B站视频链接
- 能力：视频信息获取 → 字幕/弹幕/评论 → 语音转写 → 结构化总结
- 入口文件：`skills/bilibili-video-summary/SKILL.md`

### folder-to-vector-kb
- 触发：用户要求整理文件夹为知识库
- 能力：文档清洗 → 终稿筛选 → 语义 chunk → 元数据补全 → 输出 `knowledge_base.jsonl`
- 入口文件：`skills/folder-to-vector-kb/SKILL.md`

### cc-switch-claude-provider
- 触发：用户提供 Claude-compatible `base URL` 和 API key，要求让 Claude Code 直接可用
- 能力：写入 CC Switch provider → 切换当前 Claude provider → 同步 Claude Code 配置 → 冒烟测试
- 入口文件：`skills/cc-switch-claude-provider/SKILL.md`

### chinese-first-dialog
- 触发：用户要求默认使用简体中文回复，或需要中文优先但保留代码、命令、路径、配置键、API 标识符和原始错误文本
- 能力：简体中文优先沟通 → 技术字面量保持原文 → 权限与风险说明中文化 → 按需切换其他语言或双语输出
- 入口文件：`skills/chinese-first-dialog/SKILL.md`

### clean-deliverable
- 触发：用户要求生成防元信息泄漏的约束提示词、审查/清洗一份已有交付物，或在生成交付物时要求"纯净交付"
- 能力：三层分离（呈现内容/幕后输入/思考过程）→ 三类泄漏识别（占位符/回声输入/思考残留）→ 用法 A 约束提示词 / 用法 B 审查清洗（含图片类重生成提示词）/ 用法 C 交付前自检
- 入口文件：`skills/clean-deliverable/SKILL.md`

### deliverable-purifier
- 触发：用户要求把 PPT 文案、方案、报告、品牌策略、模板等客户业务材料整理为可直接交付的终稿
- 能力：受众正文/授权备注/内部过程三层分离 → KEEP/REWRITE/REMOVE/RESOLVE 四类处置 → 事实、引用、声明与指定占位保真 → FINAL/REVIEW/COMPARE 输出模式
- 入口文件：`skills/deliverable-purifier/SKILL.md`

### image-ppt-to-editable-pptx
- 触发：用户提供图片型 PPT、PPT 截图或参考页图片，要求复刻为可编辑 `.pptx`
- 能力：字体参数化 → 普通文字文本框化 → 原生形状重建 → 单形状截图占位 → PPT 背景格式 → 导出后重新导入/渲染/包内 QA
- 入口文件：`skills/image-ppt-to-editable-pptx/SKILL.md`

### ppt-rebuild-workflow
- 触发：用户提供幻灯片截图、图片型 PPTX、AI 参考页或用户修改稿，要求选择适当重构模式并交付可编辑 PPTX
- 能力：Mode A-E 路由 → 语义验收 → 自动坐标校准 → 视觉抽取 → 字体校准 → 富文本 runs → 资产与可编辑边界 → 复杂视觉过渡策略 → 结构审计 → 文字可读性与参考图还原度双门禁
- 入口文件：`skills/ppt-rebuild-workflow/SKILL.md`

### game-ui-asset-pipeline
- 触发：用户要求生成、清理、切片、验证或导入游戏 UI 位图资产，尤其是 Godot 项目的 icon sheet、HUD glyph、九宫格面板、按钮皮肤和轻量动漫风 UI 装饰
- 能力：视觉风格约束 → chroma-key 抠图 → 固定网格切片 → alpha 验证 → Godot `res://` 导入与截图检查
- 入口文件：`skills/game-ui-asset-pipeline/SKILL.md`

### gpt-image-2-api
- 触发：用户要求通过 `gpt-image-2`、`gpt-image-2-max`、aifast.site、XApex 或 AtlasCloud 兼容接口生成、编辑图片
- 能力：XApex 默认异步 → 编辑失败时 AtlasCloud → 最终 aifast → 强制渠道 profile → 多参考图 → 2K/4K → 路由预览 → `check-config.js` 配置检查
- 配置：复制 skill 后在本地 `.env`、`.gateway.env` 或 `~/.gateway.env` 放置 aifast 的 `OPENAI_API_KEY`
  或 XApex 图片组的 `XAPEX_API_KEY`；两条路由使用独立 Base URL、模型、尺寸、quality 和超时设置；
  需要 AtlasCloud 编辑备用通道时再配置 `ATLASCLOUD_API_KEY`
- 入口文件：`skills/gpt-image-2-api/SKILL.md`

### player-interaction-design
- 触发：用户要求处理游戏 UI、玩法互动、引导、失败恢复、挑战链路、任务包体验验收或玩家互动合同
- 能力：完整/短合同判断 → 玩家入口、第一眼信息、主操作、可见反馈、阻断原因和恢复路径前置 → 证据层级结构化 → `not_proven` 收口 → 合同模板与校验脚本
- 入口文件：`skills/player-interaction-design/SKILL.md`

### pitch-visual-prompting
- 触发：用户要求为比稿、活动、产品、界面或社交内容构建、优化或审查图像生成提示词，且需要处理视觉目标、参考图角色、可见文字与视觉 QA
- 能力：明确交付模式 → 为每份参考图分配角色与 load/inspect-only/extract-only 路由 → 以可见证据落实比稿主张 → 拼装可执行 prompt → 文本、保真度、层级、现实感与不必要新增内容检查
- 入口文件：`skills/pitch-visual-prompting/SKILL.md`

### xiaohongshu
- 触发：用户要求操作小红书
- 内部路由：
  - `xhs-auth` → 认证管理
  - `xhs-explore` → 搜索发现
  - `xhs-interact` → 社交互动
  - `xhs-publish` → 内容发布
  - `xhs-content-ops` → 复合运营
  - `xhs-research-bridge` → 研究桥接
- 入口文件：`skills/xiaohongshu/SKILL.md`

## 失败处理

1. 若子技能 CLI 返回 `failure_artifacts`，优先提取日志路径与截图告知用户。
2. 若用户请求的技能未安装或路径不存在，提示用户将对应 skill 目录复制到 Agent 的 skills 目录下。
3. 不要在未确认的情况下执行小红书的发帖、评论、点赞等写操作。
