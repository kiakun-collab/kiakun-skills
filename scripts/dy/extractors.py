"""从抖音网页版 DOM 中提取结构化数据。"""

from __future__ import annotations

import logging
from urllib.parse import urljoin

from playwright.sync_api import Page

from .types import CreatorBrief, ProfileMeta, VideoMeta

logger = logging.getLogger(__name__)
BASE_URL = "https://www.douyin.com"


def _safe_text(element, default: str = "") -> str:
    """安全获取文本。"""
    if element is None:
        return default
    text = element.inner_text() if hasattr(element, "inner_text") else str(element)
    return text.strip() if text else default


def extract_search_results(page: Page) -> list[CreatorBrief]:
    """从搜索结果页提取达人列表。"""
    creators: list[CreatorBrief] = []

    # 抖音网页版搜索结果可能有多种卡片结构
    selectors = [
        '[data-e2e="search-card-user"]',
        '.search-result-card',
        '[class*="search-result"]',
        '.card-content',
    ]

    cards: list = []
    for sel in selectors:
        cards = page.locator(sel).all()
        if cards:
            logger.info("使用选择器 %s 找到 %d 个结果", sel, len(cards))
            break

    for card in cards[:20]:
        try:
            nickname = ""
            for nsel in ['[data-e2e="user-title"]','.nickname','[class*="nickname"]','a span']:
                el = card.locator(nsel).first
                if el.count():
                    nickname = (el.inner_text() or "").strip()
                    if nickname:
                        break

            follower = ""
            for fsel in ['[data-e2e="user-follower-count"]','.follower-count','[class*="follower"]']:
                el = card.locator(fsel).first
                if el.count():
                    follower = (el.inner_text() or "").strip()
                    if follower:
                        break

            link = ""
            href = ""
            al = card.locator("a").first
            if al.count():
                href = al.get_attribute("href") or ""
            if href:
                link = urljoin(BASE_URL, href)

            sec_uid = ""
            if "/user/" in link:
                sec_uid = link.split("/user/")[-1].split("?")[0].split("/")[0]

            if nickname:
                creators.append(
                    CreatorBrief(
                        nickname=nickname,
                        sec_uid=sec_uid,
                        follower_count_text=follower,
                        homepage=link,
                    )
                )
        except Exception as e:
            logger.debug("提取搜索卡片失败: %s", e)
            continue

    return creators


def extract_profile_meta(page: Page) -> ProfileMeta:
    """提取达人主页元数据。"""
    meta = ProfileMeta()

    # 昵称
    for sel in ['[data-e2e="user-nickname"]','.nickname','h1','[class*="nickname"]']:
        try:
            text = (page.locator(sel).first.inner_text(timeout=500) or "").strip()
            if text:
                meta.nickname = text
                break
        except Exception:
            continue

    # 粉丝数 / 获赞数
    stats: list[str] = []
    for sel in ['[data-e2e="user-tab-count"]','.tab-count','[class*="count"]','.stats']:
        try:
            elems = page.locator(sel).all()
            stats = [(e.inner_text() or "").strip() for e in elems if (e.inner_text() or "").strip()]
            if len(stats) >= 2:
                break
        except Exception:
            continue

    if stats:
        meta.follower_count = stats[0]
        meta.total_likes = stats[1] if len(stats) > 1 else ""

    # 简介
    for sel in ['[data-e2e="user-signature"]','.signature','[class*="signature"]','.desc']:
        try:
            text = (page.locator(sel).first.inner_text(timeout=500) or "").strip()
            if text:
                meta.signature = text
                break
        except Exception:
            continue

    return meta


def extract_video_meta_list(page: Page, max_videos: int = 5) -> list[VideoMeta]:
    """从主页提取最近视频列表的元数据。"""
    videos: list[VideoMeta] = []

    selectors = [
        '[data-e2e="user-post-item"]',
        '[data-e2e="user-favorite-item"]',
        '.video-card',
        '[class*="video-card"]',
    ]

    cards: list = []
    for sel in selectors:
        cards = page.locator(sel).all()
        if cards:
            break

    for card in cards[:max_videos]:
        try:
            title = ""
            for tsel in ['[data-e2e="video-desc"]','.title','span','[class*="title"]']:
                el = card.locator(tsel).first
                if el.count():
                    title = (el.inner_text() or "").strip()
                    if title:
                        break

            likes = ""
            for lsel in ['[data-e2e="video-like-count"]','.like-count','[class*="like"]']:
                el = card.locator(lsel).first
                if el.count():
                    likes = (el.inner_text() or "").strip()
                    if likes:
                        break

            url = ""
            al = card.locator("a").first
            if al.count():
                href = al.get_attribute("href") or ""
                if href:
                    url = urljoin(BASE_URL, href)

            videos.append(VideoMeta(title=title, likes=likes, url=url))
        except Exception as e:
            logger.debug("提取视频卡片失败: %s", e)
            continue

    return videos
