#!/usr/bin/env python3
"""Shared image/measurement helpers for the reference-render scripts.

Extracted (P1-2) from ``extract_reference_measurements.py``,
``calibrate_reference_render.py``, ``make_reference_render_comparison.py`` and
``score_typography_candidates.py``. Behaviour is preserved byte-for-byte so the
scripts' JSON outputs remain identical (subprocess tests assert on them).
"""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageFilter, ImageFont

try:  # Optional acceleration; helpers degrade to pure Python without it.
    import numpy as np
except ImportError:  # pragma: no cover - environment dependent
    np = None


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

# Candidate CJK-capable system fonts, probed in order (P2-2, decision D2:
# detect system fonts, do not bundle font files). Bare names first (PIL also
# searches the platform font directory), then common absolute paths.
_CJK_FONT_CANDIDATES = (
    # Windows
    "msyh.ttc",
    "msyh.ttf",
    "simhei.ttf",
    "simsun.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
    # macOS
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    # Linux
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "NotoSansCJK-Regular.ttc",
)


def load_overlay_font(size: int = 14) -> ImageFont.ImageFont:
    """Return a CJK-capable overlay font, or ``load_default()`` if none is found.

    Annotation overlays label shapes that may carry Chinese names; the PIL
    default bitmap font renders CJK as tofu boxes. This probes common system
    fonts and only falls back to the default when every probe fails (P2-2).
    """
    for candidate in _CJK_FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, size)
        except (OSError, ValueError):
            continue
    return ImageFont.load_default()


def natural_key(path: Path) -> list[object]:
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", path.name)
    ]


def extract_page_number(path: Path, explicit: dict[str, int] | None = None) -> int | None:
    """Derive a 1-based page number from a filename (P2-1: shared strategy).

    Both ``calibrate_reference_render`` and ``make_reference_render_comparison``
    use this so the same filename always maps to the same page inside one
    pipeline. Precedence (label-first): an explicit ``filename -> page`` mapping,
    then a ``page``/``slide``/``p`` label prefix, then a single bare number,
    else ``None`` (ambiguous).
    """
    if explicit and path.name in explicit:
        return explicit[path.name]
    stem = path.stem
    labelled = re.search(r"(?:page|slide|p)[-_ ]*0*(\d+)(?!\d)", stem, re.IGNORECASE)
    if labelled:
        return int(labelled.group(1))
    numbers = re.findall(r"\d+", stem)
    if len(numbers) == 1:
        return int(numbers[0])
    return None


def percentile_from_histogram(histogram: list[int], percentile: float) -> int:
    total = sum(histogram)
    if total <= 0:
        return 0
    cutoff = total * percentile
    running = 0
    for value, count in enumerate(histogram):
        running += count
        if running >= cutoff:
            return value
    return len(histogram) - 1


def load_image_rgb(path: Path) -> Image.Image:
    """Open ``path`` and return it as an RGB image (file handle closed)."""
    with Image.open(path) as source:
        return source.convert("RGB")


def edge_binary(
    image: Image.Image,
    use_numpy: bool = True,
    percentile: float = 0.90,
    min_threshold: int = 24,
) -> tuple[bytearray, int]:
    """Return a 0/1 edge mask and its threshold.

    Edges come from ``ImageFilter.FIND_EDGES`` on the grayscale image, binarized
    at ``max(min_threshold, histogram-percentile)``. The mask *content* is
    identical on both the numpy and pure-Python paths; ``use_numpy`` only picks
    the faster branch (and is honoured only when numpy is importable).
    """
    gray = image.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    threshold = max(min_threshold, percentile_from_histogram(edges.histogram(), percentile))
    raw = edges.tobytes()
    if use_numpy and np is not None:
        array = np.frombuffer(raw, dtype=np.uint8)
        return bytearray((array >= threshold).astype(np.uint8).tobytes()), threshold
    return bytearray(1 if value >= threshold else 0 for value in raw), threshold
