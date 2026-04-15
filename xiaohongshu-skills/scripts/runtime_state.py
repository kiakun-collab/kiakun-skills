"""运行时状态持久化，避免分步流程串到错误页面。"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

_RUNTIME_DIR = Path.home() / ".xhs" / "runtime"


def _scope(account: str) -> str:
    value = account.strip() or "__default__"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def _state_path(port: int, account: str) -> Path:
    return _RUNTIME_DIR / f"active_page_{port}_{_scope(account)}.json"


def save_active_page(
    port: int,
    account: str,
    target_id: str,
    *,
    flow: str = "",
    stage: str = "",
) -> None:
    """保存当前流程对应的页面 target_id。"""
    _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "target_id": target_id,
        "flow": flow,
        "stage": stage,
        "updated_at": int(time.time()),
    }
    with open(_state_path(port, account), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_active_page(port: int, account: str) -> dict | None:
    """读取当前流程对应的页面状态。"""
    path = _state_path(port, account)
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def clear_active_page(port: int, account: str) -> None:
    """清除当前流程对应的页面状态。"""
    path = _state_path(port, account)
    if path.exists():
        path.unlink()
