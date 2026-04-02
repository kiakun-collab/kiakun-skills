"""Playwright 浏览器封装，支持连接已有 Chrome 实例。"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright, Page

from .extractors import extract_profile_meta, extract_search_results, extract_video_meta_list
from .types import ExploreResult, ProfileSnapshot

logger = logging.getLogger(__name__)

# 硬编码安全约束
MAX_PAGES_PER_SESSION = 30
MIN_INTERVAL_SECONDS = 5.0


class DouyinBrowser:
    """抖音网页版浏览器控制器。"""

    def __init__(
        self,
        headless: bool = False,
        user_data_dir: str | None = None,
        chrome_bin: str | None = None,
        connect_cdp: str | None = None,  # CDP 连接地址，如 "http://localhost:9222"
    ):
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.chrome_bin = chrome_bin
        self.connect_cdp = connect_cdp
        self.playwright = None
        self.browser = None
        self.context = None
        self.page: Page | None = None
        self._pages_visited = 0
        self._last_action_time = 0.0

    def _guard(self) -> None:
        """安全检查。"""
        if self._pages_visited >= MAX_PAGES_PER_SESSION:
            raise RuntimeError(f"单 session 页面访问已达上限 {MAX_PAGES_PER_SESSION}")
        elapsed = time.time() - self._last_action_time
        if elapsed < MIN_INTERVAL_SECONDS and self._last_action_time > 0:
            sleep_for = MIN_INTERVAL_SECONDS - elapsed
            logger.info("安全间隔：等待 %.1f 秒", sleep_for)
            time.sleep(sleep_for)
        self._last_action_time = time.time()

    def connect(self) -> None:
        """启动或连接到 Chrome。"""
        self.playwright = sync_playwright().start()

        if self.connect_cdp:
            # 连接到已有 Chrome 实例（通过 CDP）
            logger.info("连接到已有 Chrome: %s", self.connect_cdp)
            self.browser = self.playwright.chromium.connect_over_cdp(self.connect_cdp)
            # 使用已有 context 或创建新 context
            if self.browser.contexts:
                self.context = self.browser.contexts[0]
                logger.info("使用已有 browser context")
            else:
                self.context = self.browser.new_context()
            # 使用已有页面或创建新页面
            if self.context.pages:
                self.page = self.context.pages[0]
                logger.info("使用已有页面")
            else:
                self.page = self.context.new_page()
        else:
            # 启动新 Chrome 实例
            logger.info("启动新 Chrome 实例")
            if self.user_data_dir:
                Path(self.user_data_dir).mkdir(parents=True, exist_ok=True)
            
            chrome_path = self.chrome_bin or "/usr/bin/google-chrome"
            
            self.browser = self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir or "",
                headless=self.headless,
                executable_path=chrome_path,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
                viewport={"width": 1280, "height": 800},
            )
            self.page = self.browser.new_page()
        
        logger.info("浏览器已就绪")

    def close(self) -> None:
        """关闭浏览器。"""
        if self.browser:
            self.browser.close()
            self.browser = None
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
        logger.info("浏览器已关闭")

    def _goto(self, url: str) -> None:
        """安全导航。"""
        self._guard()
        if not self.page:
            raise RuntimeError("浏览器未连接")
        logger.info("导航到: %s", url)
        try:
            self.page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            # 加载失败时截图保存用于调试
            debug_path = f"/tmp/douyin_debug_{int(time.time())}.png"
            try:
                self.page.screenshot(path=debug_path)
                logger.error("页面加载失败，调试截图: %s", debug_path)
            except:
                pass
            raise
        self._pages_visited += 1

    def capture(self, save_path: str) -> str:
        """截图并保存，返回绝对路径。"""
        if not self.page:
            raise RuntimeError("浏览器未连接")
        self.page.screenshot(path=save_path, full_page=False)
        logger.info("截图已保存: %s", save_path)
        return str(Path(save_path).resolve())

    def search(self, keyword: str, screenshot_path: str | None = None) -> ExploreResult:
        """在抖音搜索关键词，返回截图和达人列表。"""
        encoded = quote(keyword)
        url = f"https://www.douyin.com/search/{encoded}?type=user"
        self._goto(url)

        # 等待内容加载
        time.sleep(3.0)

        result = ExploreResult(keyword=keyword)
        if screenshot_path:
            result.screenshots.append(self.capture(screenshot_path))

        result.creators = extract_search_results(self.page)
        return result

    def open_profile(
        self,
        url: str,
        homepage_screenshot_path: str | None = None,
        max_videos: int = 5,
        video_screenshot_prefix: str | None = None,
    ) -> ProfileSnapshot:
        """打开达人主页，返回截图和元数据。"""
        self._goto(url)
        time.sleep(3.0)

        snapshot = ProfileSnapshot()
        meta = extract_profile_meta(self.page)
        snapshot.nickname = meta.nickname
        snapshot.follower_count = meta.follower_count
        snapshot.total_likes = meta.total_likes
        snapshot.signature = meta.signature

        if homepage_screenshot_path:
            snapshot.homepage_screenshot = self.capture(homepage_screenshot_path)

        # 提取视频列表
        videos = extract_video_meta_list(self.page, max_videos=max_videos)
        snapshot.recent_videos_meta = videos

        # 依次打开前 N 个视频详情页截图
        if video_screenshot_prefix and videos:
            for idx, video in enumerate(videos[:max_videos], 1):
                if not video.url:
                    continue
                try:
                    self._goto(video.url)
                    time.sleep(2.5)
                    video_path = f"{video_screenshot_prefix}_{idx:03d}.png"
                    snapshot.video_screenshots.append(self.capture(video_path))
                except Exception as e:
                    logger.warning("视频 %d 截图失败: %s", idx, e)
                    continue

        return snapshot
