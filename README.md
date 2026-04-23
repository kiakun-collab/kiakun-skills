# kiakun-skills

Kiakun 的 AI Agent Skills 集合仓库，兼容 OpenClaw、Claude Code 及所有支持 `SKILL.md` 格式的 Agent 平台。

本仓库汇集了多个面向内容平台自动化与知识管理的技能，每个技能都遵循 `SKILL.md` 开放标准，可被 Agent 自动识别和加载。

---

## 技能清单

| 技能 | 路径 | 说明 | 核心能力 |
|------|------|------|----------|
| **xiaohongshu** | `skills/xiaohongshu/` | 小红书自动化 | 认证登录、内容发布、搜索发现、社交互动、复合运营分析 |
| **bilibili-video-summary** | `skills/bilibili-video-summary/` | B站视频总结 | 链接解析、字幕/弹幕/评论提取、Whisper 语音转写、结构化总结 |
| **folder-to-vector-kb** | `skills/folder-to-vector-kb/` | 文件夹向量化 | 批量文档清洗、语义 chunk 切分、元数据补全、输出 `knowledge_base.jsonl` |
| **cc-switch-claude-provider** | `skills/cc-switch-claude-provider/` | Claude Code API 配置 | 通过 CC Switch 写入第三方 Claude-compatible API、切换 provider、冒烟测试 |

---

## 快速开始

### 前置条件

- Python >= 3.11
- [uv](https://docs.astral.sh/uv/) 包管理器
- Google Chrome 浏览器（小红书技能需要）

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
cp -r skills/cc-switch-claude-provider ~/.claude/skills/

# OpenClaw 示例
cp -r skills/xiaohongshu <openclaw-project>/skills/
```

> Agent 会自动识别每个 skill 目录下的 `SKILL.md` 并加载对应能力。

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
    ├── cc-switch-claude-provider/
    │   ├── SKILL.md           # CC Switch Claude Code 第三方 API 配置
    │   ├── agents/
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

### cc-switch-claude-provider（Claude Code API 配置）

把第三方 Claude-compatible `base URL` 和 `API key` 写入本地 CC Switch，自动切换 Claude provider，并运行一次 `claude` 冒烟测试确认 Claude Code 可用。

**典型用法：**
> "用 CC Switch 帮我配置 Claude Code，base url 是 https://example.com/api，key 是 sk-xxx。"

详见 `skills/cc-switch-claude-provider/SKILL.md`。

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
