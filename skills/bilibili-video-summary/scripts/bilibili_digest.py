#!/usr/bin/env python3
"""B站视频摘要素材获取（单入口）。

架构原则：脚本预消化 → LLM 只理解。脚本以最低成本拿全原始文本素材 + 预算好的统计
信号，输出**固定量级 JSON（目标 ≤ 15KB）**给调用方 Claude 做总结；绝不 dump 全量弹幕/评论。

素材优先级链：字幕正文（主）→ Whisper（兜底）；AI 小结仅作辅助信号（永远放 auxiliary）。
纯计算函数（可单测、无网络）集中在上半部；异步网络编排在下半部。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path

SCHEMA_MAX_KB = 15
TRANSCRIPT_HEAD_CHARS = 8000
CACHE_TTL_SEC = 24 * 3600
DEGRADED_TTL_SEC = 3600  # 降级结果（无字幕/画像失败）缓存更短，避免配好 cookie 后仍返回旧降级数据
CACHE_DIR = Path(os.path.expanduser("~/.cache/bilibili-summary"))

# ---------------------------------------------------------------------------
# 纯函数（无网络，单测覆盖）
# ---------------------------------------------------------------------------

_BV_RE = re.compile(r"BV[0-9A-Za-z]{10}")
_AV_RE = re.compile(r"av(\d+)", re.IGNORECASE)


def extract_id(text: str) -> tuple[str, object]:
    """从 URL / BV号 / AV号解析出标识。返回 ("bvid", "BV..") 或 ("aid", 123)。"""
    text = (text or "").strip()
    m = _BV_RE.search(text)
    if m:
        return ("bvid", m.group(0))
    m = _AV_RE.search(text)
    if m:
        return ("aid", int(m.group(1)))
    raise ValueError(f"无法从 '{text}' 解析 BV/AV 号")


def fold_repeats(token: str) -> str:
    """把连续重复字符折叠成一个（"哈哈哈"→"哈"），让重复弹幕计一次形态。"""
    return re.sub(r"(.)\1+", r"\1", token)


_TOKEN_RE = re.compile(r"[一-鿿]+|[A-Za-z0-9]+")
_STOPWORDS = set("的了是我你他她它们也都就还在有和吗啊呢吧嘛哦这那不都很啊哦嗯")


def top_words(texts, limit: int = 20) -> list[dict]:
    """弹幕词频 Top N：抽取 CJK/ASCII token，折叠重复，过滤纯标点/单字符/停用词。"""
    counter: Counter = Counter()
    for text in texts:
        for tok in _TOKEN_RE.findall(text or ""):
            norm = fold_repeats(tok)
            if len(norm) < 2:
                continue
            if len(norm) > 8:
                norm = norm[:8]
            if norm in _STOPWORDS:
                continue
            counter[norm] += 1
    return [{"word": w, "count": c} for w, c in counter.most_common(limit)]


def bucket_seconds(duration_sec: int) -> int:
    """分桶粒度：30s 与 时长/100 取大者。"""
    return max(30, int(round((duration_sec or 0) / 100)))


def density_buckets(times, duration_sec: int, bucket_sec: int) -> list[int]:
    n = max(1, math.ceil((duration_sec or 1) / max(1, bucket_sec)))
    buckets = [0] * n
    for t in times:
        idx = min(n - 1, max(0, int(t // bucket_sec)))
        buckets[idx] += 1
    return buckets


def find_peaks(buckets, bucket_sec: int, k: int = 5) -> list[dict]:
    """密度 Top k 峰值（按时间升序返回）。"""
    ranked = sorted(range(len(buckets)), key=lambda i: buckets[i], reverse=True)
    top = sorted(ranked[:k])
    return [
        {"t_sec": round(i * bucket_sec + bucket_sec / 2, 1), "count": buckets[i], "samples": []}
        for i in top
        if buckets[i] > 0
    ]


def peak_samples(peaks, danmaku, window: float = 15.0, per_peak: int = 8) -> None:
    """为每个峰值 ±window 秒采样至多 per_peak 条去重弹幕（就地写入 samples）。"""
    for peak in peaks:
        seen, samples = set(), []
        for d in danmaku:
            if abs(d["t"] - peak["t_sec"]) <= window:
                text = d["text"].strip()
                key = fold_repeats(text)
                if text and key not in seen:
                    seen.add(key)
                    samples.append(text)
                if len(samples) >= per_peak:
                    break
        peak["samples"] = samples


def value_signals(stats: dict, duration_sec: int) -> dict:
    view = max(1, stats.get("view", 0))
    dur_min = max(1 / 60, (duration_sec or 0) / 60)
    like_rate = round(stats.get("like", 0) / view, 4)
    fav_rate = round(stats.get("favorite", 0) / view, 4)
    coin_rate = round(stats.get("coin", 0) / view, 4)
    danmaku_per_min = round(stats.get("danmaku", 0) / dur_min, 4)
    reply_rate = round(stats.get("reply", 0) / view, 4)
    hints = []
    if fav_rate > 0.03:
        hints.append(f"收藏率 {fav_rate:.2%} 偏高，通常为干货/工具型内容")
    if coin_rate > 0.02:
        hints.append(f"投币率 {coin_rate:.2%} 偏高，观众认可度强")
    if like_rate > 0.08:
        hints.append(f"点赞率 {like_rate:.2%} 偏高，好评倾向明显")
    if danmaku_per_min > 30:
        hints.append(f"弹幕密度 {danmaku_per_min:.0f} 条/分，互动氛围热烈")
    if not hints:
        hints.append("互动指标平平，参考基准：收藏率>3% 干货、投币率>2% 认可、点赞率>8% 好评")
    return {
        "like_rate": like_rate, "fav_rate": fav_rate, "coin_rate": coin_rate,
        "danmaku_per_min": danmaku_per_min, "reply_rate": reply_rate,
        "hint": "；".join(hints),
    }


def parse_subtitle_body(data: dict):
    """解析字幕正文 JSON 的 body 数组 → 逐句 {from,to,content}。"""
    body = (data or {}).get("body", []) or []
    segs = []
    for item in body:
        if "content" in item:
            segs.append({"from": item.get("from", 0.0), "to": item.get("to", 0.0),
                         "content": item.get("content", "")})
    return segs


def subtitle_to_text(segments) -> str:
    return "".join(s["content"] for s in segments)


def choose_subtitle(subtitle_list):
    """多语言字幕择优：zh-CN/zh-Hans > 其他 cc > ai 生成。返回 (entry, subtitle_type) 或 (None,None)。"""
    if not subtitle_list:
        return None, None
    def is_ai(e):
        return str(e.get("lan", "")).startswith("ai-")
    for pref in ("zh-CN", "zh-Hans"):
        for e in subtitle_list:
            if e.get("lan") == pref and not is_ai(e):
                return e, "cc"
    for e in subtitle_list:
        if not is_ai(e):
            return e, "cc"
    return subtitle_list[0], "ai"


def classify_error(exc) -> dict:
    """把异常映射为结构化 error（BUG-7）。"""
    code = getattr(exc, "code", None)
    msg = str(exc)
    if code in (-404,) or "不存在" in msg or "not found" in msg.lower() or "稿件不可见" in msg:
        return {"code": "not_found", "message": msg}
    if code in (-101, -111, -2, 62002) or "未登录" in msg or "Cookie" in msg or "登录" in msg:
        return {"code": "auth", "message": msg}
    if code in (-352, -412) or "风控" in msg or "请求被拦截" in msg:
        return {"code": "rate_limited", "message": msg}
    lowered = type(exc).__name__.lower()
    if "client" in lowered or "timeout" in lowered or "connection" in lowered or "network" in msg.lower():
        return {"code": "network", "message": msg}
    return {"code": "unknown", "message": f"{type(exc).__name__}: {msg}"}


def enforce_transcript_budget(text: str, mode: str) -> tuple[str, bool]:
    """PERF-3：transcript full|head|none；full 超 8000 字自动取头部。"""
    if mode == "none" or not text:
        return "", False
    if mode == "head" or len(text) > TRANSCRIPT_HEAD_CHARS:
        return text[:TRANSCRIPT_HEAD_CHARS], len(text) > TRANSCRIPT_HEAD_CHARS
    return text, False


# ---------------------------------------------------------------------------
# 异步网络层
# ---------------------------------------------------------------------------

def load_credential():
    """Cookie 仅从本地读取，skill 目录 cookies.json 优先。"""
    candidates = [
        Path(__file__).resolve().parents[1] / "cookies.json",  # skill 目录（第一优先）
        Path(__file__).resolve().parent / "cookies.json",       # scripts 目录
        Path(os.path.expanduser("~/.hermes/skills/openclaw-imports/bilibili-summary/cookies.json")),
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("sessdata"):
            from bilibili_api import Credential

            return Credential(sessdata=data.get("sessdata"), bili_jct=data.get("bili_jct", ""),
                              buvid3=data.get("buvid3", ""))
    return None


async def _fetch_subtitle_text(session, subtitle_list):
    entry, sub_type = choose_subtitle(subtitle_list)
    if not entry:
        return None, None, []
    url = entry.get("subtitle_url", "")
    if url.startswith("//"):
        url = "https:" + url
    if not url:
        return None, sub_type, []
    async with session.get(url) as resp:
        data = await resp.json(content_type=None)
    segs = parse_subtitle_body(data)
    return subtitle_to_text(segs), sub_type, segs


def _hint_for_uploader():  # placeholder for symmetry
    return None


async def gather_material(id_kind, id_value, credential, args, session) -> dict:
    """一次 get_info() → 并行取各信号（Semaphore(2)）→ 组装。"""
    from bilibili_api import comment, video

    v = video.Video(bvid=id_value, credential=credential) if id_kind == "bvid" \
        else video.Video(aid=id_value, credential=credential)
    info = await v.get_info()  # PERF-1：只调一次
    requests_made = {"n": 1}
    aid = info["aid"]
    pages = info.get("pages") or [{"cid": info["cid"], "page": 1}]
    total_pages = len(pages)
    page_idx = min(max(1, args.page), total_pages) - 1
    cid = pages[page_idx]["cid"]

    sem = asyncio.Semaphore(2)

    async def guarded(coro_fn, label):
        async with sem:
            try:
                requests_made["n"] += 1
                return await coro_fn()
            except Exception as exc:  # 单信号失败不拖垮主链路
                return {"__error__": f"{label}: {exc}"}

    # 第一组：字幕元数据 / 弹幕 / AI 小结 / pbp
    subtitle_meta, danmakus, ai_conc, pbp = await asyncio.gather(
        guarded(lambda: v.get_subtitle(cid=cid), "subtitle"),
        guarded(lambda: v.get_danmakus(cid=cid), "danmaku"),
        guarded(lambda: v.get_ai_conclusion(cid=cid), "ai_conclusion"),
        guarded(lambda: v.get_pbp(cid=cid), "pbp"),
    )
    await asyncio.sleep(args.throttle)

    # 第二组：热评（按赞）
    comments_raw = {"__error__": "skipped"}
    if not args.skip_comments:
        async def fetch_comments():
            page1 = await comment.get_comments(aid, comment.CommentResourceType.VIDEO,
                                               1, comment.OrderType.LIKE, credential)
            page2 = await comment.get_comments(aid, comment.CommentResourceType.VIDEO,
                                               2, comment.OrderType.LIKE, credential)
            return [page1, page2]
        comments_raw = await guarded(fetch_comments, "comments")
        await asyncio.sleep(args.throttle)

    # 第三组：UP主画像（T8）。三个子接口各自 guarded，部分成功也保留；失败落到 errors 供诊断。
    uploader_raw = None
    up_mid = info.get("owner", {}).get("mid")
    if up_mid and not getattr(args, "skip_uploader", False):
        from bilibili_api import user

        u = user.User(uid=up_mid, credential=credential)
        uploader_raw = {"info": None, "rel": None, "vids": None, "errors": []}
        for key, coro_fn in (("info", lambda: u.get_user_info()),
                             ("rel", lambda: u.get_relation_info()),
                             ("vids", lambda: u.get_videos(pn=1, ps=5))):
            async with sem:
                try:
                    requests_made["n"] += 1
                    uploader_raw[key] = await coro_fn()
                except Exception as exc:  # get_videos 常因 wbi 风控瞬时失败
                    uploader_raw["errors"].append(f"{key}: {exc}")
        await asyncio.sleep(args.throttle)

    # 字幕正文
    transcript_text, subtitle_type, segs = None, None, []
    if isinstance(subtitle_meta, dict) and "__error__" not in subtitle_meta:
        sub_list = subtitle_meta.get("subtitles", [])
        if sub_list:
            try:
                requests_made["n"] += 1
                transcript_text, subtitle_type, segs = await _fetch_subtitle_text(session, sub_list)
            except Exception as exc:
                transcript_text = None

    return {
        "info": info, "aid": aid, "cid": cid, "total_pages": total_pages,
        "current_page": page_idx + 1, "danmakus": danmakus, "ai_conclusion": ai_conc,
        "pbp": pbp, "comments_raw": comments_raw, "transcript_text": transcript_text,
        "subtitle_type": subtitle_type, "segments": segs, "uploader_profile_raw": uploader_raw,
        "requests_made": requests_made["n"],
    }


def parse_uploader_profile(raw):
    """UP主原始数据 → (uploader_profile, error)。防御式：部分字段成功也返回；全失败返回 (None, 错误串)。"""
    if not isinstance(raw, dict):
        return None, None
    errors = raw.get("errors") or []
    uinfo = raw.get("info") or {}
    rel = raw.get("rel") or {}
    vids = raw.get("vids") or {}
    if not uinfo and not rel and not vids:
        return None, ("；".join(errors) if errors else "uploader fetch failed")
    vlist = (((vids.get("list") or {}).get("vlist")) or [])[:5]
    official = (uinfo.get("official") or {}).get("title") or ""
    profile = {
        "sign": uinfo.get("sign", ""),
        "official": official,
        "followers": rel.get("follower", 0),
        "recent_videos": [{"title": x.get("title", ""), "play": x.get("play", 0),
                           "pubdate": x.get("created", 0)} for x in vlist],
    }
    return profile, ("；".join(errors) if errors else None)


async def fetch_sub_replies(aid, root_rpid, credential, limit=10):
    from bilibili_api import comment

    c = comment.Comment(oid=aid, type_=comment.CommentResourceType.VIDEO, rpid=root_rpid,
                        credential=credential)
    data = await c.get_sub_comments(page_index=1, page_size=limit)
    out = []
    for r in (data.get("replies") or [])[:limit]:
        out.append({"user": r.get("member", {}).get("uname", ""),
                    "text": r.get("content", {}).get("message", ""),
                    "likes": r.get("like", 0)})
    return out


def build_hot_comments(comments_raw, up_mid):
    """从两页热评组装 hot_comments（含置顶/UP回复标记）。返回 (list, top3_rpids)。"""
    if not isinstance(comments_raw, list):
        return [], []
    seen, merged = set(), []
    top_replies = []
    for page in comments_raw:
        if not isinstance(page, dict):
            continue
        top_replies = page.get("top_replies") or top_replies
        for r in page.get("replies") or []:
            rpid = r.get("rpid")
            if rpid in seen:
                continue
            seen.add(rpid)
            merged.append(r)
    pinned_ids = {r.get("rpid") for r in (top_replies or [])}
    result = []
    for r in merged[:25]:
        replies_preview = r.get("replies") or []
        up_replied = any(rr.get("member", {}).get("mid") == up_mid for rr in replies_preview)
        result.append({
            "rpid": r.get("rpid"),
            "user": r.get("member", {}).get("uname", ""),
            "text": r.get("content", {}).get("message", ""),
            "likes": r.get("like", 0),
            "reply_count": r.get("rcount", 0),
            "is_pinned": r.get("rpid") in pinned_ids,
            "up_replied": up_replied,
            "sub_replies": [],
        })
    top3 = sorted(result, key=lambda c: c["likes"], reverse=True)[:3]
    return result, [c["rpid"] for c in top3 if c["rpid"]]


# ---------------------------------------------------------------------------
# 组装 + 缓存 + CLI
# ---------------------------------------------------------------------------

def cache_path(id_kind, id_value, page, logged_in: bool) -> Path:
    # 登录态并入 key：匿名降级结果与登录结果分开缓存，互不覆盖
    base = f"{id_value}_p{page}" if id_kind == "bvid" else f"av{id_value}_p{page}"
    return CACHE_DIR / f"{base}_{'auth' if logged_in else 'anon'}.json"


def read_cache(path: Path):
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    epoch = data.get("meta", {}).get("_cached_epoch", 0)
    degraded = (data.get("transcript", {}).get("source") == "none") or (data.get("uploader_profile") is None)
    ttl = DEGRADED_TTL_SEC if degraded else CACHE_TTL_SEC
    if time.time() - epoch > ttl:
        return None
    data["meta"]["cache_hit"] = True
    return data


def write_cache(path: Path, payload: dict):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def assemble(material, args) -> dict:
    info = material["info"]
    stat = info.get("stat", {})
    duration = info.get("duration", 0)
    owner = info.get("owner", {})
    up_mid = owner.get("mid")
    _up_profile, _up_error = parse_uploader_profile(material.get("uploader_profile_raw"))

    danmaku = []
    if isinstance(material["danmakus"], list):
        danmaku = [{"t": float(getattr(d, "dm_time", 0.0)), "text": getattr(d, "text", "")}
                   for d in material["danmakus"]]
    bsec = bucket_seconds(duration)
    buckets = density_buckets([d["t"] for d in danmaku], duration, bsec)
    peaks = find_peaks(buckets, bsec)
    peak_samples(peaks, danmaku)
    pbp_ok = isinstance(material["pbp"], dict) and "__error__" not in material["pbp"] and bool(material["pbp"])

    stats = {"view": stat.get("view", 0), "like": stat.get("like", 0), "coin": stat.get("coin", 0),
             "favorite": stat.get("favorite", 0), "reply": stat.get("reply", 0),
             "danmaku": stat.get("danmaku", 0), "share": stat.get("share", 0)}

    # transcript 来源判定
    if material["transcript_text"]:
        source, sub_type, text = "subtitle", material["subtitle_type"], material["transcript_text"]
    else:
        source, sub_type, text = "none", None, ""
    ai = material["ai_conclusion"]
    ai_available = isinstance(ai, dict) and "__error__" not in ai
    ai_model = (ai or {}).get("model_result", {}) if ai_available else {}
    if source == "none" and ai_model.get("summary"):
        source, text = "ai_conclusion_fallback", ai_model.get("summary", "")
    trans_text, truncated = enforce_transcript_budget(text, args.transcript)

    hot_comments, _top3 = build_hot_comments(material["comments_raw"], up_mid)

    aux = {"ai_conclusion": {"available": bool(ai_model.get("result_type", 0)) if ai_available else False,
                             "source": "bilibili_official_ai",
                             "outline": [{"title": o.get("title", ""), "timestamp": o.get("timestamp", 0)}
                                         for o in (ai_model.get("outline") or [])],
                             "summary": ai_model.get("summary", "")}}

    return {
        "ok": True, "error": None,
        "video": {"bvid": info.get("bvid"), "aid": info.get("aid"), "title": info.get("title"),
                  "desc": (info.get("desc") or "")[:500], "duration_sec": duration,
                  "pubdate": info.get("pubdate"), "tname": info.get("tname"),
                  "pages_total": material["total_pages"], "current_page": material["current_page"],
                  "url": f"https://www.bilibili.com/video/{info.get('bvid')}", "tags": []},
        "uploader": {"uid": up_mid, "name": owner.get("name", "")},
        "uploader_profile": _up_profile,
        "uploader_profile_error": _up_error,
        "stats": stats,
        "value_signals": value_signals(stats, duration),
        "transcript": {"source": source, "subtitle_type": sub_type, "text": trans_text,
                       "truncated": truncated,
                       "segments_sample": [{"t": s["from"], "text": s["content"]}
                                           for s in material["segments"][:20]]},
        "auxiliary": aux,
        "danmaku_analysis": {"total": len(danmaku), "top_words": top_words([d["text"] for d in danmaku]),
                             "density_buckets": buckets, "bucket_sec": bsec, "peaks": peaks,
                             "pbp_available": pbp_ok},
        "hot_comments": hot_comments,
        "meta": {"fetched_at": int(time.time()), "cache_hit": False,
                 "requests_made": material["requests_made"], "elapsed_sec": 0.0,
                 "_cached_epoch": time.time()},
    }


async def run(args) -> dict:
    id_kind, id_value = extract_id(args.url)
    credential = load_credential()
    cpath = cache_path(id_kind, id_value, args.page, credential is not None)
    if not args.no_cache:
        cached = read_cache(cpath)
        if cached:
            return cached

    import aiohttp

    started = time.time()
    headers = {"Referer": "https://www.bilibili.com/", "User-Agent":
               "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            material = await gather_material(id_kind, id_value, credential, args, session)
            payload = assemble(material, args)
            # top3 楼中楼
            if not args.skip_comments and payload["hot_comments"]:
                _, top3_rpids = build_hot_comments(material["comments_raw"], payload["uploader"]["uid"])
                by_rpid = {c["rpid"]: c for c in payload["hot_comments"]}
                for rpid in top3_rpids:
                    payload["meta"]["requests_made"] += 1  # 计入楼中楼请求（#3a）
                    try:
                        by_rpid[rpid]["sub_replies"] = await fetch_sub_replies(
                            material["aid"], rpid, credential)
                    except Exception:
                        by_rpid[rpid]["sub_replies"] = []
    except Exception as exc:
        return {"ok": False, "error": classify_error(exc)}

    if payload.get("uploader_profile_error"):
        print(f"warning: uploader_profile 抓取失败: {payload['uploader_profile_error']}", file=sys.stderr)

    # 评论截断（≤25 主 + ≤30 子）
    sub_total = 0
    for c in payload["hot_comments"]:
        room = max(0, 30 - sub_total)
        c["sub_replies"] = c["sub_replies"][:room]
        sub_total += len(c["sub_replies"])
    payload["meta"]["elapsed_sec"] = round(time.time() - started, 2)
    payload["meta"].pop("_cached_epoch", None)
    payload["meta"]["_cached_epoch"] = time.time()
    if not args.no_cache:
        write_cache(cpath, payload)
    payload["meta"].pop("_cached_epoch", None)
    return payload


def make_stdout_robust():
    # 强制 UTF-8 输出：Windows 下重定向到文件/管道时 stdout 默认走 GBK，会破坏中文 JSON。
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")


def main() -> int:
    parser = argparse.ArgumentParser(description="B站视频摘要素材获取（输出 JSON ≤15KB 供 LLM 总结）")
    parser.add_argument("url", help="B站视频 URL / BV号 / AV号")
    parser.add_argument("--page", type=int, default=1, help="分P序号（默认1）")
    parser.add_argument("--transcript", choices=("full", "head", "none"), default="full")
    parser.add_argument("--skip-comments", action="store_true")
    parser.add_argument("--skip-uploader", action="store_true", help="跳过 UP主画像抓取")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--throttle", type=float, default=1.5, help="请求组间隔秒")
    args = parser.parse_args()

    try:
        result = asyncio.run(run(args))
    except ValueError as exc:  # 解析失败
        result = {"ok": False, "error": {"code": "not_found", "message": str(exc)}}
    make_stdout_robust()
    text = json.dumps(result, ensure_ascii=False)
    print(text)
    # PERF-3：15KB 目标针对「信号信封」（不含 transcript 全文，全文单独可控）
    if result.get("ok"):
        envelope = dict(result)
        envelope["transcript"] = {**result["transcript"], "text": "", "segments_sample": []}
        env_bytes = len(json.dumps(envelope, ensure_ascii=False).encode("utf-8"))
        if env_bytes > SCHEMA_MAX_KB * 1024:
            print(f"warning: signal envelope {env_bytes // 1024}KB > {SCHEMA_MAX_KB}KB", file=sys.stderr)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
