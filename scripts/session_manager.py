"""Session 管理：创建、保存、读取研究会话数据。"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

DEFAULT_ROOT = Path.home() / ".douyin-research" / "sessions"


def _ensure_root() -> Path:
    """确保根目录存在。"""
    DEFAULT_ROOT.mkdir(parents=True, exist_ok=True)
    return DEFAULT_ROOT


def create_session(name: str, game: str, meta: dict[str, Any] | None = None) -> str:
    """创建新 session，返回 session_id。"""
    session_id = f"{game}-{uuid.uuid4().hex[:8]}"
    root = _ensure_root() / session_id
    root.mkdir(parents=True, exist_ok=False)

    payload = {
        "session_id": session_id,
        "name": name,
        "game": game,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "meta": meta or {},
    }
    (root / "meta.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return session_id


def get_session_dir(session_id: str) -> Path:
    """获取 session 数据目录。"""
    return _ensure_root() / session_id


def save_meta(session_id: str, data: dict[str, Any]) -> None:
    """覆写 meta.json。"""
    path = get_session_dir(session_id) / "meta.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_meta(session_id: str) -> dict[str, Any]:
    """读取 meta.json。"""
    path = get_session_dir(session_id) / "meta.json"
    if not path.exists():
        raise FileNotFoundError(f"Session {session_id} not found")
    return json.loads(path.read_text(encoding="utf-8"))


def append_record(session_id: str, record: dict[str, Any]) -> None:
    """追加一条记录到 data.jsonl。"""
    path = get_session_dir(session_id) / "data.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_records(session_id: str) -> list[dict[str, Any]]:
    """读取 data.jsonl 所有记录。"""
    path = get_session_dir(session_id) / "data.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def list_sessions() -> list[dict[str, Any]]:
    """列出所有 session 的 meta。"""
    root = _ensure_root()
    sessions = []
    for d in sorted(root.iterdir()):
        meta_path = d / "meta.json"
        if meta_path.exists():
            sessions.append(json.loads(meta_path.read_text(encoding="utf-8")))
    return sessions


def next_screenshot_path(session_id: str, prefix: str, ext: str = "png") -> Path:
    """生成下一个截图文件路径。"""
    root = get_session_dir(session_id)
    existing = [p.name for p in root.glob(f"{prefix}_*.{ext}")]
    idx = len(existing) + 1
    path = root / f"{prefix}_{idx:03d}.{ext}"
    return path
