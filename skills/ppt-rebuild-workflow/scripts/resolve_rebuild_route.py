#!/usr/bin/env python3
"""Resolve normalized user intent; this is not a natural-language classifier."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PROFILES = {"fast": 1, "balanced": 2, "strict": 3}
TARGETS = {"preview": ("Mode A", "Level 1"), "editable": ("Mode B", "Level 2"),
           "layered": ("Mode C", "Level 3")}


def resolve_route(data: dict) -> dict:
    if not isinstance(data, dict):
        raise ValueError("input must be an object")
    intent = data.get("routingIntent", data)
    if not isinstance(intent, dict):
        raise ValueError("routingIntent must be an object")
    operation = intent.get("operation", "rebuild")
    deliverable = intent.get("deliverable", "editable")
    profile = data.get("executionProfile", intent.get("executionProfile", "balanced"))
    if operation not in {"rebuild", "incremental"}:
        raise ValueError("operation must be rebuild or incremental")
    if deliverable not in TARGETS or profile not in PROFILES:
        raise ValueError("unsupported deliverable or executionProfile")
    for key in ("redesignRequested", "referenceOnly", "userSelectsDesign"):
        if key in intent and not isinstance(intent[key], bool):
            raise ValueError(f"{key} must be a boolean")
    redesign = intent.get("redesignRequested", False)
    reference_only = intent.get("referenceOnly", False)
    selects = intent.get("userSelectsDesign", False)
    if (reference_only or selects) and not redesign:
        raise ValueError("referenceOnly/userSelectsDesign requires an explicit design phase")
    if operation == "incremental" and reference_only:
        raise ValueError("referenceOnly conflicts with incremental PPTX delivery")
    target, target_qa = TARGETS[deliverable]
    missing = []
    if operation == "incremental" and not data.get("sourcePptx", intent.get("sourcePptx")):
        missing.append("sourcePptx")
    primary = "Mode E" if operation == "incremental" else "Mode D" if redesign else target
    stages = (["design"] if redesign else []) + ([] if reference_only else
              ["incremental-edit" if operation == "incremental" else "build", "verify"])
    return {
        "taskMode": primary,
        "targetMode": None if reference_only else target,
        "qaLevel": None if reference_only else "Level 4" if operation == "incremental" else target_qa,
        "changedRegionQaLevel": target_qa if operation == "incremental" else None,
        "executionProfile": profile,
        "calibrationPolicy": "full" if profile == "strict" else "targeted",
        "maxRepairIterations": PROFILES[profile],
        "stages": stages,
        "waitForDesignChoice": bool(redesign and selects),
        "requiresInput": bool(missing),
        "missingInputs": missing,
        "reason": {"operation": operation, "deliverable": deliverable,
                   "redesignRequested": redesign, "intentEvidence": intent.get("intentEvidence", [])},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        result = resolve_route(json.loads(Path(args.input).read_text(encoding="utf-8-sig")))
        text = json.dumps(result, ensure_ascii=True, indent=2)
        if args.output:
            path = Path(args.output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 1 if result["requiresInput"] else 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "INVALID", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
