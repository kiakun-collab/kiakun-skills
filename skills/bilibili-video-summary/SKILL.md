---
name: bilibili-video-summary
description: |
  B站视频决策助手。当用户发送B站视频链接时，拉取视频信息、字幕正文、弹幕、热评与官方AI小结，
  由脚本预消化为统计信号，再生成"值不值得看/看哪段/评论共识争议"的决策导向总结。

  触发条件：用户发送B站视频链接（BV号、AV号或完整URL）时自动触发。
---

# B站视频决策助手

**你（Claude）是总结者，脚本只负责取素材。** 脚本以最低成本拿全原始文本素材 + 预算好的统计信号，
输出一份 **≤15KB 的固定量级 JSON**；你据此写出帮助用户**快速判断长视频价值**的报告。

## Start Here

```bash
python scripts/bilibili_digest.py "<B站链接 / BV号 / AV号>"
```

- 常用开关：`--page N`（分P，默认1）、`--transcript full|head|none`（字幕正文，默认full，超8000字自动截头部）、
  `--skip-comments`、`--skip-uploader`、`--no-cache`。
- 无 CC 字幕时用 Whisper 兜底：`python scripts/bilibili_whisper.py "<链接>" [--sample --peaks peaks.json] [--whisper-model small]`（需系统 ffmpeg）。
- 脚本自带 24h 本地缓存（`~/.cache/bilibili-summary/`）与限速；stdout 是 UTF-8 JSON，进度走 stderr。

## 输出 JSON 契约（字段即事实源）

```jsonc
{
  "ok": true, "error": null,                 // ok=false 时仅含 error{code,message}
  "video": { "bvid","aid","title","desc","duration_sec","pubdate","tname","pages_total","current_page","url","tags" },
  "uploader": { "uid","name" },
  "uploader_profile": { "sign","official","followers","recent_videos":[{title,play,pubdate}] },  // 可能为 null
  "uploader_profile_error": null,            // 画像抓取失败时的原因串（区分"UP无数据"与"接口失败/wbi风控"）
  "stats": { "view","like","coin","favorite","reply","danmaku","share" },
  "value_signals": { "like_rate","fav_rate","coin_rate","danmaku_per_min","reply_rate","hint" },
  "transcript": { "source":"subtitle|whisper|ai_conclusion_fallback|none", "subtitle_type":"cc|ai|null",
                  "text":"...", "truncated":false, "segments_sample":[{t,text}] },
  "auxiliary": { "ai_conclusion": { "available","source":"bilibili_official_ai","outline":[{title,timestamp}],"summary" } },
  "danmaku_analysis": { "total","top_words":[{word,count}],"density_buckets":[],"bucket_sec",
                        "peaks":[{t_sec,count,samples:[]}],"pbp_available" },
  "hot_comments": [{ "rpid","user","text","likes","reply_count","is_pinned","up_replied","sub_replies":[{user,text,likes}] }],
  "meta": { "fetched_at","cache_hit","requests_made","elapsed_sec" }
}
```

**素材优先级**：`transcript.source` 标注本次内容来源。`subtitle`/`whisper` 是主内容源；`ai_conclusion_fallback`
仅在字幕与转写都拿不到时降级采用（B站自研小模型，质量低于你对全文的总结，用时**必须注明来源**）。
AI 小结永远只是 `auxiliary` 辅助信号（分段章节可作结构锚点）。

## 报告生成指令（决策导向）

依据 JSON 产出以下结构（无对应数据的小节注明"数据不足"，不要编造）：

① **一句话结论**：值得完整看 / 看高能点即可 / 看本总结即可 / 不值得看（结合 value_signals 与内容判断）。
② **内容摘要 + 分段大纲**：基于 `transcript.text`（注明素材来源：字幕/转写/AI小结降级）；有 `auxiliary.ai_conclusion.outline` 时用其时间戳作章节锚点。
③ **高能点时间轴**：`danmaku_analysis.peaks` 的 `t_sec` + `samples` 代表弹幕 + 对应内容段落；`pbp_available` 为 true 时说明与官方高能进度条互相印证。
④ **评论区共识与争议**：对 `hot_comments` 做观点聚类；用 `sub_replies`（楼中楼）摘要争议交锋；区分"对内容的评价"与"对UP主的评价"，输出共识观点、少数派观点、风评倾向。
⑤ **UP主风评**（有 `uploader_profile` 时）：画像（粉丝量、认证、近期作品）+ 本视频舆论倾向。
⑥ **价值信号**：列 `value_signals` 各互动率 + `hint` 判断依据。

## 错误处理指引

`ok=false` 时按 `error.code` 应对，不要重试到风控：
- `not_found`：BV/AV 号可能有误或视频不可见，请用户核对。
- `auth`：需要登录态（字幕/部分接口）——提示配置 `cookies.json`（`sessdata`/`bili_jct`/`buvid3`）；可继续用无需登录的字段。
- `rate_limited`（-352/-412）：触发风控，稍后再试，不要连续重试。
- `network`：网络问题，检查连接后重试。
- `unknown`：附原始 message 供排查。

## 配置与合规

- Cookie 仅本地读取，优先 skill 目录 `cookies.json`，其次 `~/.hermes/skills/openclaw-imports/bilibili-summary/cookies.json`。**不要泄露 SESSDATA/BILI_JCT**。
- 保持脚本内置限速，不做任何绕过登录/风控的行为。
- 依赖：`pip install -e .`（或 `bilibili-api-python aiohttp`）；Whisper 兜底另需 `pip install faster-whisper` + 系统 ffmpeg。
