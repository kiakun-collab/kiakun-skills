# bilibili-video-summary

B站视频**决策助手**：不是简单"下载视频数据"，而是帮你快速判断长视频**值不值得看、看哪一段、评论区共识与争议**。

核心思路：**脚本预消化 → LLM 只理解**。脚本以最低成本拿全原始文本素材（字幕正文/弹幕/热评）+ 预算好的统计信号（词频、密度、峰值、互动率），输出一份 **≤15KB 的固定量级 JSON**，由调用方 Claude 生成决策导向报告。绝不把全量弹幕/评论 dump 出来。

## 安装

```bash
pip install -e .            # bilibili-api-python + aiohttp
pip install -e ".[whisper]" # 可选：无 CC 字幕时的 Whisper 兜底（另需系统 ffmpeg）
```

## 用法

```bash
# 主脚本：拉全素材 + 预消化，输出 JSON
python scripts/bilibili_digest.py "https://www.bilibili.com/video/BV1xx411c7mD"
python scripts/bilibili_digest.py "av170001" --page 1 --transcript head

# 无字幕兜底：Whisper 转写（需 ffmpeg）
python scripts/bilibili_whisper.py "BV1xx411c7mD" --sample --peaks peaks.json
```

常用开关：`--page N`、`--transcript full|head|none`、`--skip-comments`、`--skip-uploader`、`--no-cache`、`--throttle 秒`。

## 素材优先级链

```
主内容源：字幕正文（全文逐句）  →  无字幕兜底：Whisper 转写（可采样）
辅助信号（并行顺带取）：B站官方 AI 小结（仅作分段章节锚点；字幕/转写都拿不到时才降级采用其摘要，且标注来源）
```

`transcript.source` 字段标注本次内容来源：`subtitle` / `whisper` / `ai_conclusion_fallback` / `none`。

## 输出字段

见 [SKILL.md](SKILL.md) 的「输出 JSON 契约」。要点：`value_signals`（互动率+基准提示）、`danmaku_analysis`（词频 Top20 / 密度数组 / Top5 峰值+代表弹幕 / pbp 印证）、`hot_comments`（热评+楼中楼，含置顶/UP回复标记）、`uploader_profile`（UP主画像）。

## 配置（Cookie，可选但建议）

字幕、部分接口需登录态。将凭证写入 `cookies.json`（skill 目录优先）：

```json
{ "sessdata": "你的SESSDATA", "bili_jct": "你的BILI_JCT", "buvid3": "你的BUVID3" }
```

**不要泄露 SESSDATA/BILI_JCT。** 脚本内置限速与 24h 本地缓存（`~/.cache/bilibili-summary/`），不做任何绕过风控的行为。

## 测试

```bash
python -m pytest tests/ -q   # 网络调用全 mock，离线可跑
```

开发细节与验证记录见 [DEVELOPMENT_REPORT.md](DEVELOPMENT_REPORT.md)。
