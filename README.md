# kiakun-skills

用于内容创作、办公交付与自动化的 15 个 AI Agent Skills。每个技能独立提供 `SKILL.md`，可按需安装到 Codex、Claude Code 或其他支持该格式的 Agent。

## 技能目录

| 方向 | 技能 | 用途 |
|---|---|---|
| 演示文稿 | [ppt-rebuild-workflow](skills/ppt-rebuild-workflow/SKILL.md) | 将截图、图片型 PPT 或参考稿重构为可编辑 PPTX |
| 演示文稿 | [html-to-pptx](skills/html-to-pptx/SKILL.md) | 将 HTML 演示文稿转换为可编辑 PPTX |
| 演示文稿 | [image-ppt-to-editable-pptx](skills/image-ppt-to-editable-pptx/SKILL.md) | 复刻图片型幻灯片的文字、形状与布局 |
| 视觉创作 | [gpt-image-2-api](skills/gpt-image-2-api/SKILL.md) | 图片生成、编辑、多参考图与批量任务 |
| 视觉创作 | [pitch-visual-prompting](skills/pitch-visual-prompting/SKILL.md) | 将比稿 brief 和参考资料转为视觉提示词 |
| 游戏设计 | [game-ui-asset-pipeline](skills/game-ui-asset-pipeline/SKILL.md) | UI 素材切片、透明背景处理与 Godot 资产交付 |
| 游戏设计 | [player-interaction-design](skills/player-interaction-design/SKILL.md) | 设计和检查玩家入口、操作、反馈与恢复流程 |
| 内容平台 | [xiaohongshu](skills/xiaohongshu/SKILL.md) | 小红书登录、搜索、发布与内容运营 |
| 内容平台 | [bilibili-video-summary](skills/bilibili-video-summary/SKILL.md) | 汇总视频、字幕与互动信息，辅助判断观看价值 |
| 知识与地图 | [folder-to-vector-kb](skills/folder-to-vector-kb/SKILL.md) | 将文件夹文档整理为结构化知识库 |
| 知识与地图 | [amap-web-service](skills/amap-web-service/SKILL.md) | POI 搜索、地理编码、路线与静态地图 |
| 交付质量 | [deliverable-purifier](skills/deliverable-purifier/SKILL.md) | 精修客户业务材料，保留事实与必要注释 |
| 交付质量 | [clean-deliverable](skills/clean-deliverable/SKILL.md) | 检查成品中的提示词残留与无意占位内容 |
| Agent 配置 | [chinese-first-dialog](skills/chinese-first-dialog/SKILL.md) | 默认中文交流，保留技术标识原文 |
| Agent 配置 | [cc-switch-claude-provider](skills/cc-switch-claude-provider/SKILL.md) | 通过 CC Switch 配置 Claude Code provider |

## 快速开始

1. 克隆仓库：

   ```bash
   git clone https://github.com/kiakun-collab/kiakun-skills.git
   cd kiakun-skills
   ```

2. 将所需技能的完整目录复制到 Agent 的 skills 目录。以 Codex 为例：

   ```bash
   mkdir -p ~/.codex/skills
   cp -r skills/gpt-image-2-api ~/.codex/skills/
   ```

   Windows PowerShell：

   ```powershell
   New-Item -ItemType Directory -Force "$HOME/.codex/skills" | Out-Null
   Copy-Item -Recurse skills/gpt-image-2-api "$HOME/.codex/skills/"
   ```

   Claude Code 使用 `~/.claude/skills/`；其他 Agent 使用对应的技能目录。

3. 阅读该技能的 `SKILL.md`，安装其依赖并完成所需配置，然后在对话中说明任务或直接指定技能名称。

各技能依赖不同，按需配置 Python、Node.js、浏览器或 API Key。图片服务配置见 [gpt-image-2-api 安装说明](skills/gpt-image-2-api/SKILL.md)。

## 选择建议

- 从参考稿还原 PPT：从 `ppt-rebuild-workflow` 开始；已有 HTML 时使用 `html-to-pptx`。
- 清理客户方案、报告或提案：使用 `deliverable-purifier`；通用成品检查使用 `clean-deliverable`。
- 每个技能目录中的脚本、模板和参考资料应一起安装。

## 开发与更新

具体操作和配置以各技能的 `SKILL.md` 为准。更新记录见 [提交历史](https://github.com/kiakun-collab/kiakun-skills/commits/main/)。

```bash
uv sync
uv run ruff check .
uv run pytest
```

图片 API 脚本测试：

```bash
node --test skills/gpt-image-2-api/scripts/shared.test.js
```

## License

MIT
