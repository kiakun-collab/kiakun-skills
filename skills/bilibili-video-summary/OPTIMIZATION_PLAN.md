# bilibili-video-summary 优化开发计划

> 版本：v1.0（2026-07-04）
> 角色分工：本文档由规划方（Claude 调研会话）产出；**开发工作由执行 agent 完成**；完成后规划方将依据本文档和《开发结果报告》审阅质量。
> 本文档是唯一需求来源，执行时不依赖任何其他对话上下文。

---

## 1. 背景与产品目标

本 skill 的真实用途不是"下载视频数据"，而是**帮助用户快速判断和理解 B站长视频**：

1. **快速判断价值**：长视频值不值得看？看总结就够、还是只看高能片段、还是值得完整看？
2. **弹幕/评论作为内容补充**：他人的讨论往往比视频本身信息密度更高，热评和弹幕能快速揭示内容质量与亮点位置。
3. **UP主风评与舆论**：了解 UP主的口碑、本视频的舆论倾向、共识与争议。

**核心架构原则（所有开发决策的判断依据）**：

- **总结者是调用方 Claude，不是脚本、更不是 B站**。脚本职责 = 以最低成本拿到最完整的**原始文本素材**和**预消化的统计信号**，喂给 Claude 做理解和总结。
- **脚本预消化，LLM 只理解**：所有聚合计算（词频、密度、排序、比率）在脚本内完成；脚本最终输出的 JSON 必须是**固定量级（目标 ≤ 15KB）**，绝不把全量弹幕/评论 dump 给调用方。
- **素材优先级链**（成本从低到高）：
  ```
  主内容源：字幕正文（全文逐句，2 次请求秒回）
    → 无字幕时兜底：Whisper 转写（可采样转写）
  辅助信号（并行顺带取）：B站官方 AI 小结
    ├─ 有结果 → 只取分段章节时间戳提纲，作结构锚点
    └─ 字幕与转写都不可用 → 才降级采用其摘要文本，且必须标注来源
  ```
  注意：B站 AI 小结覆盖率有限（部分视频无结果，`result_type` 标识）、且为 B站自研小模型，质量低于 Claude 对全文素材的总结，**禁止将其作为默认主内容源**。

## 2. 现状文件清单

```
~/.claude/skills/bilibili-video-summary/
├── SKILL.md                    # 技能指令（需重写，见 M2-T7）
├── README.md                   # 人类文档（需同步更新）
├── requirements.txt            # bilibili-api-python / aiohttp / faster-whisper
└── scripts/
    ├── bilibili_summary.py     # 信息获取脚本（约 256 行）
    └── bilibili_whisper.py     # Whisper 转写脚本（约 140 行）
```

依赖库：`bilibili-api-python`（Nemo2011/bilibili-api），文档 https://nemo2011.github.io/bilibili-api/

## 3. 已确认的缺陷清单（M0 修复对象）

以下问题均已对照 Nemo2011/bilibili-api 官方源码核实：

| ID | 严重度 | 位置 | 问题 | 修复要求 |
|----|--------|------|------|----------|
| BUG-1 | P0 | `bilibili_summary.py:124` | `comment.Comment(bvid=..., oid=None, ...)` 用错类：`Comment.__init__` 签名为 `(oid: int, type_, rpid: int, credential)`，不接受 `bvid`、必须传 `rpid`，该类是"操作单条评论"，不是评论列表入口。现被 `try/except` 吞错，评论功能静默失败 | 改用模块级 `comment.get_comments(oid=aid, type_=CommentResourceType.VIDEO, order=OrderType.LIKE, ...)`；`aid` 从 `get_info()` 结果取 |
| BUG-2 | P0 | `bilibili_whisper.py:40-45` | `curl` 下载音频无 `Referer`/`User-Agent`，B站 CDN 防盗链返回 403，Whisper 链路第一步即断 | 请求头必须含 `Referer: https://www.bilibili.com/` 和浏览器类 UA；建议同时改用 `aiohttp`（见 PERF-6） |
| BUG-3 | P0 | `bilibili_summary.py:87-103` | `get_subtitle()` 只拿到字幕**元数据**（语言列表 + `subtitle_url`），从未下载正文 JSON。有字幕的视频反而拿不到任何内容 | 对 `subtitle_url` 再发 GET（注意 url 可能以 `//` 开头需补 `https:`），解析 `body` 数组得到逐句 `{from, to, content}` |
| BUG-4 | P1 | `bilibili_summary.py:43-62` | `extract_bvid()` 不支持 AV 号（`av123456`），与文档"支持 BV/AV 号"矛盾 | 补 `av\d+`（大小写不敏感）分支；`video.Video(aid=...)` 支持 aid 构造 |
| BUG-5 | P1 | `bilibili_summary.py:157-209` | `format_summary()` 为死代码，`main()` 从未调用 | 删除（输出统一走 JSON 契约，见 §5） |
| BUG-6 | P1 | `bilibili_summary.py:212-256` | 文档承诺"2 秒请求间隔"，实际零限流；且 `get_video_info/get_subtitle/get_danmakus` 各自重复调用 `get_info()`（同一接口连打 3-4 次） | `get_info()` 只调 1 次、结果复用；请求间加限速（见 PERF-2） |
| BUG-7 | P1 | `bilibili_summary.py` `main()` | 网络调用无任何 `try/except`，接口失败直接崩溃 | 按错误类型区分输出结构化错误 JSON：视频不存在 / Cookie 失效或未登录 / 风控（-352/-412）/ 网络错误 |
| BUG-8 | P2 | 两脚本 | `sys.path.insert(0, parent)` 为无意义残留（依赖走 pip 标准安装） | 删除 |
| BUG-9 | P2 | `bilibili_whisper.py:51-65` | `get_audio_url()` 与 `bilibili_summary.py` 重复实现 | 合并为共享实现（M3 合并脚本时一并解决） |
| BUG-10 | P2 | 全部 | 仅支持单 P（`cid` 固定取 `info["cid"]`） | 用 `get_pages()` 列出分 P，CLI 支持 `--page N`，默认第 1 P 并在输出中注明总 P 数 |

## 4. 功能需求（按里程碑）

### M0：缺陷修复（上表 BUG-1 ~ BUG-8，BUG-9/10 可延至 M3）

**验收**：对一个真实 BV 号跑通：视频信息 + 按赞排序热评（非空、非 error）+ 字幕正文全文（对有 CC 字幕的视频）+ 音频下载成功（HTTP 200，文件非空）。

### M1：内容链路

- **T1 字幕正文为主内容源**：下载并解析字幕正文，输出逐句文本（带时间戳）；多语言时优先 `zh-CN`/`zh-Hans`，其次 ai 生成字幕（`lan` 以 `ai-` 开头），并在输出中标注字幕类型。
- **T2 官方 AI 小结作辅助信号**：调用 `Video.get_ai_conclusion(cid=...)`；解析 `model_result`：`result_type=0`（无结果）或接口异常时**静默跳过**，不影响主链路；有结果时提取 `summary`（摘要文本）与 `outline`（分段章节：标题 + 时间戳）。输出中 AI 小结永远放在 `auxiliary` 字段，注明 `source: "bilibili_official_ai"`。
- **T3 优先级链落地**：`transcript_source` 字段明确标注本次内容来源：`subtitle` / `whisper` / `ai_conclusion_fallback` / `none`。

**验收**：三类视频各跑通一次——①有 CC 字幕的视频输出全文；②无字幕视频提示需 Whisper（或自动触发）；③无 AI 小结的视频不报错。

### M2：信号聚合（本 skill 的差异化核心）

- **T4 弹幕聚合分析**（全部在脚本内计算，禁止输出全量弹幕）：
  - 词频 Top 20（需简单分词/清洗：过滤纯标点、单字符、"哈哈哈"类重复字符折叠计一次形态）；
  - 按时间分桶（建议 30s 或视频时长/100 取大者）的密度数组 + Top 5 峰值时刻；
  - 每个峰值时刻 ±15s 内采样最多 8 条代表性弹幕（去重）；
  - 与 `Video.get_pbp(cid=...)`（官方高能进度条）峰值互相印证，pbp 不可用时静默降级为纯弹幕密度。
- **T5 热评与争议**：
  - `order=OrderType.LIKE` 取前 2 页热评；每条保留：用户名、**完整正文（不截断）**、点赞数、回复数、是否置顶、是否 UP主本人回复过；
  - 对赞数 Top 3 的评论调用 `Comment.get_sub_comments()` 取每条最多 10 条子回复（楼中楼是争议与舆论的核心素材）；
  - 评论总输出条数上限 25 条主评 + 30 条子回复，超出截断并注明。
- **T6 价值信号指标**：脚本直接计算并输出：点赞/播放、收藏/播放、硬币/播放、弹幕密度（条/分钟）、评论率（评论/播放）。数值保留 4 位小数，同时附一行 `hint` 说明经验基准（如"收藏率>3% 通常为干货型内容"）。
- **T7 重写 SKILL.md**：新 SKILL.md 必须包含：
  - 触发条件（保持现有）；
  - 脚本调用方式与 JSON 输出字段契约（§5）；
  - **报告生成指令**：要求 Claude 按以下模板产出决策导向报告：
    ```
    ① 一句话结论（值得完整看 / 看高能点即可 / 看本总结即可 / 不值得看）
    ② 内容摘要 + 分段大纲（注明素材来源：字幕/转写/AI小结降级）
    ③ 高能点时间轴（峰值时刻 + 代表弹幕 + 对应内容段落）
    ④ 评论区共识与争议（观点聚类；楼中楼交锋摘要）
    ⑤ UP主风评（画像 + 本视频舆论倾向）※ M3 后启用
    ⑥ 价值信号（互动率指标 + 判断依据）
    ```
  - 舆论提取指令：从热评中区分"对内容的评价"与"对 UP主的评价"，输出共识观点、少数派观点、风评倾向；
  - 错误处理指引（对应 BUG-7 的结构化错误码）。

**验收**：对一个 10 万播放以上、弹幕 5000+ 的视频运行，输出 JSON ≤ 15KB，包含全部聚合字段；Claude 依据输出能直接写出 ①-④、⑥ 各节。

### M3：UP主风评、性能与工程收尾

- **T8 UP主画像**：`user.User(uid).get_user_info()`（名称、签名、认证信息）+ `get_relation_info()`（粉丝数）+ 最近 5 个视频（标题、播放、发布时间），输出 `uploader_profile` 字段。
- **T9 采样转写**：`bilibili_whisper` 支持 `--sample` 模式——依据 M2 的弹幕/pbp 峰值时刻，用 `ffmpeg -ss <t> -t 90` 切取每个峰值前后片段分别转写，替代全片转写；无峰值数据时均匀采样 5 段。
- **T10 单入口整合**：合并为 `bilibili_digest.py` 单入口，内部自动走优先级链；保留 `--no-whisper`、`--whisper-model`、`--sample`、`--page`、`--skip-comments` 等开关。旧的两个脚本可保留为薄包装或删除（在报告中说明选择）。
- **T11 本地缓存**：按 `bvid+page` 缓存拉取结果到 `~/.cache/bilibili-summary/<bvid>.json`（含抓取时间戳，默认 24h 有效，`--no-cache` 跳过）。
- **T12 工程补齐**：新增 `pyproject.toml`；`tests/` 下补单元测试（至少覆盖：BV/AV/URL 解析、弹幕聚合函数（用固定样本数据）、价值指标计算、字幕正文解析（用 mock JSON）、错误分类）。网络调用一律 mock，测试不依赖真实网络。

### 性能要求（贯穿各里程碑）

| ID | 要求 |
|----|------|
| PERF-1 | `get_info()` 全流程只调用 1 次 |
| PERF-2 | 独立请求（字幕正文/弹幕/热评/tags/pbp/AI小结）用 `asyncio.gather` 并行，`Semaphore(2)` 限并发，组间 `await asyncio.sleep(1~2)`，兼顾速度与风控 |
| PERF-3 | 最终输出 JSON ≤ 15KB（不含 transcript 全文时；transcript 全文单独可控：`--transcript full|head|none`，默认 full 但超过 8000 字时自动截取头部并注明） |
| PERF-4 | Whisper：先 `ffmpeg` 转 16kHz 单声道 wav 再转写；按时长自动选模型（≤15min → small，>15min → base），允许 `--whisper-model` 覆盖 |
| PERF-5 | 音频/网络下载统一 `aiohttp`（复用 session，带 Referer/UA），移除 `curl` 子进程依赖 |

### 合规约束

- 保持限速（PERF-2），不做任何绕过登录/风控的激进行为；Cookie 仅从本地 `cookies.json` 读取（维持现有路径约定，可增加 skill 目录内 `cookies.json` 为第一优先路径）；提醒用户不要泄露 SESSDATA。

## 5. 输出 JSON 契约（`bilibili_digest.py` 最终形态）

```jsonc
{
  "ok": true,                          // false 时仅含 error 字段
  "error": null,                       // {code: "not_found|auth|rate_limited|network|unknown", message: "..."}
  "video": { "bvid", "aid", "title", "desc", "duration_sec", "pubdate", "tname", "pages_total", "current_page", "url", "tags": [] },
  "uploader": { "uid", "name" },
  "uploader_profile": { "sign", "official", "followers", "recent_videos": [{ "title", "play", "pubdate" }] },  // M3
  "stats": { "view", "like", "coin", "favorite", "reply", "danmaku", "share" },
  "value_signals": { "like_rate", "fav_rate", "coin_rate", "danmaku_per_min", "reply_rate", "hint" },
  "transcript": { "source": "subtitle|whisper|ai_conclusion_fallback|none", "subtitle_type": "cc|ai|null", "text": "...", "truncated": false, "segments_sample": [{ "t": 0.0, "text" }] },
  "auxiliary": { "ai_conclusion": { "available": true, "outline": [{ "title", "timestamp" }], "summary": "..." } },
  "danmaku_analysis": { "total", "top_words": [{ "word", "count" }], "density_buckets": [], "bucket_sec": 30,
                        "peaks": [{ "t_sec", "count", "samples": [] }], "pbp_available": true },
  "hot_comments": [{ "user", "text", "likes", "reply_count", "is_pinned", "up_replied",
                     "sub_replies": [{ "user", "text", "likes" }] }],
  "meta": { "fetched_at", "cache_hit": false, "requests_made": 0, "elapsed_sec": 0.0 }
}
```

字段可按实现微调，但**调整必须同步写进 SKILL.md 和开发结果报告**。

## 6. 真实验证要求（开发完成前必须执行）

至少对以下 4 类真实视频各完整跑通一次，并把 BV 号和运行结果记入开发结果报告：

1. 有 CC 字幕的知识区/科技区视频（验证字幕正文主链路）；
2. 无字幕、时长 <10min 的视频（验证 Whisper 兜底全链路：下载不 403、转写出文）；
3. 播放 10 万+、弹幕 5000+ 的热门视频（验证聚合质量与输出体积 ≤15KB）；
4. 多 P 视频（验证 `--page` 与默认行为）。

另需验证 2 个错误路径：不存在的 BV 号、无 Cookie 状态下运行（应优雅降级或给出结构化错误，而非崩溃）。

## 7. 交付物清单

1. 修复并重构后的 `scripts/`（最终形态见 T10）；
2. 重写的 `SKILL.md` + 同步更新的 `README.md`；
3. `pyproject.toml` + `tests/`（全绿，附运行输出）；
4. **《开发结果报告》`DEVELOPMENT_REPORT.md`（强制，置于 skill 目录下）**，格式见 §8。

## 8. 开发结果报告要求（`DEVELOPMENT_REPORT.md`）

规划方将依据此报告 + 代码 diff 审阅开发质量，报告必须包含：

1. **任务完成矩阵**：本计划中每个 BUG-x / T-x / PERF-x 的状态（完成 / 部分完成 / 未做），未完成的写明原因；
2. **偏离计划说明**：任何与本计划不一致的实现决策（含 JSON 契约字段调整），逐条列出"计划要求 → 实际实现 → 理由"；
3. **真实验证记录**：§6 全部 6 个用例的 BV 号（错误路径除外）、执行命令、关键输出摘录（含输出 JSON 体积、耗时、`requests_made`）；
4. **测试结果**：`pytest` 完整输出（用例数、通过数）；
5. **已知问题与遗留风险**：如实列出（例如某接口偶发风控、AI 小结在某些分区不可用等）；
6. **审阅入口**：列出改动文件清单，标注每个文件的改动性质（新增/重写/修补/删除）。

> ⚠️ 报告必须如实反映：跑不通就写跑不通，禁止用"应该可以工作"替代真实运行证据。审阅时会抽查复跑验证用例。
