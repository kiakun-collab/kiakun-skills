#!/usr/bin/env python3
"""
B站视频总结脚本
获取视频信息、字幕、评论、弹幕，并可用Whisper转写
"""

import argparse
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

# Add bilibili_api to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bilibili_api import video, Credential


def load_cookie_credential():
    """Load B站登录凭证"""
    candidates = [
        os.path.join(os.path.dirname(__file__), "cookies.json"),
        os.path.expanduser("~/.hermes/skills/openclaw-imports/bilibili-summary/cookies.json"),
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            data = json.load(open(path, "r", encoding="utf-8"))
            if data.get("sessdata") and data.get("bili_jct"):
                return Credential(
                    sessdata=data["sessdata"],
                    bili_jct=data["bili_jct"],
                    buvid3=data.get("buvid3", ""),
                )
        except Exception:
            continue
    return None


def extract_bvid(url_or_bvid: str) -> str:
    """从URL或BV号中提取BV号"""
    import re
    # BV号格式
    bv_pattern = r'BV([A-Za-z0-9]+)'
    match = re.search(bv_pattern, url_or_bvid)
    if match:
        return f"BV{match.group(1)}"
    
    # 完整URL格式
    url_pattern = r'bvid=([^&]+)'
    match = re.search(url_pattern, url_or_bvid)
    if match:
        return match.group(1)
    
    # 直接是BV号
    if url_or_bvid.startswith('BV'):
        return url_or_bvid
    
    return url_or_bvid


async def get_video_info(bvid: str, credential=None) -> dict:
    """获取视频信息"""
    v = video.Video(bvid=bvid, credential=credential)
    info = await v.get_info()
    return {
        "标题": info.get("title", ""),
        "BV号": info.get("bvid", ""),
        "AV号": info.get("aid", ""),
        "分区": info.get("tname", ""),
        "UP主": info.get("owner", {}).get("name", ""),
        "简介": info.get("desc", ""),
        "播放量": info.get("stat", {}).get("view", 0),
        "点赞": info.get("stat", {}).get("like", 0),
        "硬币": info.get("stat", {}).get("coin", 0),
        "收藏": info.get("stat", {}).get("favorite", 0),
        "评论": info.get("stat", {}).get("reply", 0),
        "弹幕": info.get("stat", {}).get("danmaku", 0),
        "时长": info.get("duration", 0),
        "链接": f"https://www.bilibili.com/video/{bvid}"
    }


async def get_subtitle(bvid: str, credential=None) -> dict:
    """获取字幕"""
    v = video.Video(bvid=bvid, credential=credential)
    info = await v.get_info()
    cid = info["cid"]
    
    subtitle = await v.get_subtitle(cid=cid)
    subtitles = subtitle.get("subtitles", [])
    
    if not subtitles:
        return {"has_subtitle": False, "subtitles": []}
    
    return {
        "has_subtitle": True,
        "subtitles": subtitles,
        "cid": cid
    }


async def get_danmakus(bvid: str, credential=None) -> list:
    """获取弹幕"""
    v = video.Video(bvid=bvid, credential=credential)
    info = await v.get_info()
    cid = info["cid"]
    
    danmakus = await v.get_danmakus(cid=cid)
    return [
        {"time": d.dm_time, "text": d.text}
        for d in danmakus
    ]


async def get_comments(bvid: str, credential=None) -> list:
    """获取评论"""
    from bilibili_api import comment
    
    try:
        c = comment.Comment(bvid=bvid, oid=None, type_=comment.CommentResourceType.VIDEO)
        replies = await c.get_replies()
        
        result = []
        for reply in replies.get("replies", [])[:10]:
            result.append({
                "用户": reply.get("member", {}).get("uname", ""),
                "评论": reply.get("content", {}).get("message", ""),
                "点赞": reply.get("like", 0)
            })
        return result
    except Exception as e:
        return [{"error": str(e)}]


async def get_audio_url(bvid: str, credential=None) -> str:
    """获取音频下载URL"""
    v = video.Video(bvid=bvid, credential=credential)
    info = await v.get_info()
    cid = info["cid"]
    
    download_url = await v.get_download_url(cid=cid)
    dash = download_url.get("dash", {})
    
    # 获取最高质量音频
    audio_list = dash.get("audio", [])
    if not audio_list:
        return None
    
    best_audio = max(audio_list, key=lambda x: x.get("bandwidth", 0))
    return best_audio.get("baseUrl", "")


def format_summary(info: dict, subtitles: dict = None, danmakus: list = None, 
                  comments: list = None, transcript: str = None) -> str:
    """格式化输出"""
    output = []
    output.append("=" * 50)
    output.append("📺 B站视频总结")
    output.append("=" * 50)
    output.append("")
    output.append(f"**标题：** {info['标题']}")
    output.append(f"**UP主：** {info['UP主']}")
    output.append(f"**时长：** {info['时长']}秒 ({info['时长']//60}分{info['时长']%60}秒)")
    output.append(f"**播放量：** {info['播放量']:,}")
    output.append(f"**点赞：** {info['点赞']:,}")
    output.append(f"**收藏：** {info['收藏']:,}")
    output.append(f"**评论：** {info['评论']:,}")
    output.append(f"**弹幕：** {info['弹幕']:,}")
    output.append("")
    output.append(f"🔗 {info['链接']}")
    output.append("")
    output.append("-" * 50)
    
    # 字幕
    if subtitles and subtitles.get("has_subtitle"):
        output.append("📝 有字幕（可直接获取）")
    elif transcript:
        output.append("📝 无字幕（已用Whisper转写）")
        output.append("")
        output.append("【转写内容】")
        output.append(transcript[:2000] + "..." if len(transcript) > 2000 else transcript)
    else:
        output.append("📝 无字幕，且未转写")
    
    output.append("")
    output.append("-" * 50)
    
    # 弹幕
    if danmakus and len(danmakus) > 0:
        output.append("🎯 弹幕亮点")
        for d in danmakus[:10]:
            output.append(f"  [{d['time']:.1f}s] {d['text']}")
        output.append("")
        output.append("-" * 50)
    
    # 评论
    if comments and len(comments) > 0:
        output.append("💬 热门评论")
        for c in comments[:5]:
            if "error" not in c:
                output.append(f"  - {c['用户']}: {c['评论'][:50]}...")
        output.append("")
        output.append("-" * 50)
    
    return "\n".join(output)


async def main():
    parser = argparse.ArgumentParser(description="B站视频总结工具")
    parser.add_argument("url", help="B站视频URL或BV号")
    parser.add_argument("--no-transcript", action="store_true", help="不转写音频")
    parser.add_argument("--cookie", help="Cookie文件路径")
    args = parser.parse_args()
    
    bvid = extract_bvid(args.url)
    print(f"正在分析视频: {bvid}", file=sys.stderr)
    
    # 加载凭证
    credential = load_cookie_credential()
    
    # 获取信息
    print("获取视频信息...", file=sys.stderr)
    info = await get_video_info(bvid, credential)
    
    print("获取字幕...", file=sys.stderr)
    subtitles = await get_subtitle(bvid, credential)
    
    print("获取弹幕...", file=sys.stderr)
    danmakus = await get_danmakus(bvid, credential)
    
    print("获取评论...", file=sys.stderr)
    comments = await get_comments(bvid, credential)
    
    transcript = None
    if not subtitles.get("has_subtitle") and not args.no_transcript:
        print("无字幕，正在准备音频转写...", file=sys.stderr)
        print("提示: 请使用 bilibili_whisper.py 进行音频转写", file=sys.stderr)
    
    # 输出结果
    result = {
        "info": info,
        "subtitles": subtitles,
        "danmakus": danmakus,
        "comments": comments,
        "transcript": transcript
    }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
