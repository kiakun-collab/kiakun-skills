"""操作日志与失败工件管理。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

_LOG_ROOT = Path.home() / ".xhs" / "logs"


def _json_default(value: Any) -> Any:
    if isinstance(value, set):
        return sorted(value)
    return str(value)


def _today_dir() -> Path:
    return _LOG_ROOT / datetime.now().strftime("%Y-%m-%d")


def _run_dir(run_id: str) -> Path:
    return _today_dir() / run_id


def start_command(command: str, account: str, args: dict[str, Any]) -> dict[str, str]:
    """初始化一次命令执行日志。"""
    run_id = datetime.now().strftime("%H%M%S") + "-" + uuid.uuid4().hex[:8]
    run_dir = _run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "run_id": run_id,
        "command": command,
        "account": account,
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "status": "running",
        "args": args,
    }
    _write_json(run_dir / "run.json", payload)
    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "log_file": str(run_dir / "run.json"),
    }


def finish_command(
    run_id: str,
    *,
    exit_code: int,
    result: dict[str, Any],
    failure_artifacts: dict[str, str] | None = None,
) -> None:
    """完成一次命令执行日志。"""
    run_dir = _run_dir(run_id)
    payload = _load_json(run_dir / "run.json")
    payload.update(
        {
            "run_id": run_id,
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "status": "success" if exit_code == 0 else "error",
        "exit_code": exit_code,
        "result": result,
        "failure_artifacts": failure_artifacts or {},
        }
    )
    _write_json(run_dir / "run.json", payload)


def capture_failure_artifacts(page: Any, run_id: str, *, reason: str = "") -> dict[str, str]:
    """保存失败截图与基础页面上下文。"""
    run_dir = _run_dir(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    artifacts: dict[str, str] = {}
    screenshot_path = run_dir / "failure.png"
    try:
        page.capture_screenshot(str(screenshot_path))
        artifacts["screenshot"] = str(screenshot_path)
    except Exception:
        pass

    context_path = run_dir / "failure-context.json"
    try:
        page_context = {
            "reason": reason,
            "url": page.evaluate("window.location.href"),
            "title": page.evaluate("document.title"),
            "captured_at": datetime.now().isoformat(timespec="seconds"),
        }
        _write_json(context_path, page_context)
        artifacts["context"] = str(context_path)
    except Exception:
        pass

    return artifacts


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=_json_default)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)
