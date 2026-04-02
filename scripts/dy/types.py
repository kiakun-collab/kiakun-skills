"""Pydantic 类型定义。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreatorBrief(BaseModel):
    """搜索结果中的达人简要信息。"""

    nickname: str = ""
    sec_uid: str = ""
    follower_count_text: str = ""
    homepage: str = ""


class ProfileMeta(BaseModel):
    """达人主页元数据。"""

    nickname: str = ""
    follower_count: str = ""
    total_likes: str = ""
    signature: str = ""


class VideoMeta(BaseModel):
    """视频元数据。"""

    title: str = ""
    likes: str = ""
    comments: str = ""
    shares: str = ""
    url: str = ""


class ExploreResult(BaseModel):
    """搜索结果。"""

    keyword: str
    screenshots: list[str] = Field(default_factory=list)
    creators: list[CreatorBrief] = Field(default_factory=list)


class ProfileSnapshot(BaseModel):
    """达人主页快照。"""

    nickname: str = ""
    follower_count: str = ""
    total_likes: str = ""
    signature: str = ""
    homepage_screenshot: str = ""
    video_screenshots: list[str] = Field(default_factory=list)
    recent_videos_meta: list[VideoMeta] = Field(default_factory=list)
