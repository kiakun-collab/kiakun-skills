#!/usr/bin/env python3
"""Shared IO helpers: canonical JSON writing and robust stdout (P1-3).

Kept dependency-light (stdlib only) so both the PPTX audit scripts and the
image scripts can import it without pulling in Pillow/numpy.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def write_json(path: Path, obj: object) -> None:
    """Write ``obj`` as UTF-8 JSON, creating parent directories.

    Uses ``ensure_ascii=False`` + ``indent=2`` and ``mkdir(parents=True,
    exist_ok=True)`` to match the byte-for-byte convention the scripts already
    used, so existing subprocess assertions on the output stay valid.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def make_stdout_robust() -> None:
    """Avoid ``UnicodeEncodeError`` when printing non-ASCII paths on GBK consoles.

    Mirrors the guard in ``audit_pptx_structure.py``: unencodable characters are
    replaced with backslash escapes instead of crashing the process.
    """
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
