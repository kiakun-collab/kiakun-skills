#!/usr/bin/env python3
"""Inspect actual image transparency; never generate or alter image pixels."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def inspect_alpha(path: Path) -> dict:
    from PIL import Image
    with Image.open(path) as image:
        image.load()
        has_alpha = "A" in image.getbands() or "transparency" in image.info
        alpha = image.convert("RGBA").getchannel("A")
        histogram = alpha.histogram()
        pixels = image.width * image.height
        minimum, maximum = alpha.getextrema()
        status = ("EMPTY" if maximum == 0 else "OPAQUE" if minimum == 255
                  else "ALPHA_PRESENT")
        return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "mode": image.mode, "width": image.width, "height": image.height,
                "hasAlpha": has_alpha, "alphaMin": minimum, "alphaMax": maximum,
                "transparentPixelRatio": histogram[0] / pixels,
                "partiallyTransparentPixelRatio": sum(histogram[1:255]) / pixels,
                "status": status,
                "edgeQuality": "NOT_REVIEWED"}


def audit_assets(manifest: dict, base: Path, policy: str = "manual-handoff") -> dict:
    if policy not in {"manual-handoff", "required"}:
        raise ValueError("alphaFailurePolicy must be manual-handoff or required")
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        raise ValueError("assets must be a list (empty is valid when no external assets are needed)")
    rows, ids = [], set()
    for asset in assets:
        if not isinstance(asset, dict) or not asset.get("id") or asset["id"] in ids:
            raise ValueError("assets require unique nonempty IDs")
        if type(asset.get("requiresAlpha")) is not bool:
            raise ValueError("each asset must explicitly declare requiresAlpha")
        ids.add(asset["id"])
        path = Path(asset["path"])
        path = path if path.is_absolute() else base / path
        try:
            result = inspect_alpha(path)
        except (OSError, ValueError) as exc:
            result = {"path": str(path.resolve()), "status": "UNREADABLE", "error": str(exc)}
        needed = asset["requiresAlpha"]
        failed = result["status"] in {"EMPTY", "UNREADABLE"} or needed and result["status"] != "ALPHA_PRESENT"
        handoff = failed and result["status"] == "OPAQUE" and policy == "manual-handoff"
        rows.append({**asset, **result, "requiresAlpha": needed,
                     "disposition": "MANUAL_CUTOUT_REQUIRED" if handoff else "BLOCKED" if failed else "READY_FOR_VISUAL_REVIEW",
                     "nextAction": "keep-replaceable-object-and-handoff" if handoff else "resolve-asset" if failed else "review-edge-and-identity",
                     "regenerateForAlpha": False})
    blocked = [r["id"] for r in rows if r["disposition"] == "BLOCKED"]
    manual = [r["id"] for r in rows if r["disposition"] == "MANUAL_CUTOUT_REQUIRED"]
    return {"schemaVersion": "2.0", "generatedBy": "audit_image_alpha.py",
            "alphaFailurePolicy": policy, "assets": rows, "blockedAssets": blocked,
            "manualCutoutAssets": manual,
            "status": "BLOCKED" if blocked else "MANUAL_CUTOUT_REQUIRED" if manual else "PASS",
            "note": "Alpha presence is a channel check, not proof of a correct cutout or unchanged identity."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--policy", choices=["manual-handoff", "required"], default="manual-handoff")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        path = Path(args.manifest).resolve()
        result = audit_assets(json.loads(path.read_text(encoding="utf-8-sig")), path.parent, args.policy)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": result["status"], "manualCutoutAssets": result["manualCutoutAssets"],
                          "blockedAssets": result["blockedAssets"]}, ensure_ascii=True))
        return 0 if result["status"] == "PASS" else 1
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        print(json.dumps({"status": "INVALID", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
