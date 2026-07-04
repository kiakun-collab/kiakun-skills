#!/usr/bin/env python3
"""Top-level driver that chains the audit/measurement scripts (P3-1).

This orchestrator only *calls* the individual scripts via subprocess and
aggregates their exit codes and product paths; it never re-implements analysis.
Steps whose inputs are absent (renders, typography input, QA report) are marked
``skipped`` rather than failing the run.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent

# Ordered pipeline. Each entry: (name, builds a (cmd, output) pair or None to skip).
STEP_ORDER = (
    "audit_structure",
    "audit_text_frames",
    "extract",
    "calibrate",
    "score_typography",
    "make_comparison",
    "validate",
)


def _script(name: str) -> str:
    return str(SCRIPTS_DIR / name)


def build_steps(args: argparse.Namespace) -> list[dict]:
    out = Path(args.out_dir)
    measurements = out / "reference-measurements.json"
    steps: list[dict] = []

    steps.append(
        {
            "name": "audit_structure",
            "cmd": [sys.executable, _script("audit_pptx_structure.py"), str(args.deck),
                    "--output", str(out / "structure-audit.json")],
            "output": out / "structure-audit.json",
        }
    )
    steps.append(
        {
            "name": "audit_text_frames",
            "cmd": [sys.executable, _script("audit_pptx_text_frames.py"), str(args.deck),
                    "--output", str(out / "text-frame-audit.json")],
            "output": out / "text-frame-audit.json",
        }
    )
    steps.append(
        {
            "name": "extract",
            "cmd": [sys.executable, _script("extract_reference_measurements.py"),
                    str(args.reference_dir), "--output", str(measurements),
                    "--annotated-dir", str(out / "measurements-annotated")],
            "output": measurements,
        }
    )
    if args.renders_dir:
        steps.append(
            {
                "name": "calibrate",
                "cmd": [sys.executable, _script("calibrate_reference_render.py"),
                        str(measurements), str(args.renders_dir),
                        "--output", str(out / "coordinate-calibration.json"),
                        "--overlay-dir", str(out / "calibration-overlays")],
                "output": out / "coordinate-calibration.json",
                "requires": measurements,
            }
        )
    else:
        steps.append({"name": "calibrate", "skip": "no --renders-dir"})
    if args.typography_input:
        steps.append(
            {
                "name": "score_typography",
                "cmd": [sys.executable, _script("score_typography_candidates.py"),
                        str(args.typography_input),
                        "--output", str(out / "typography-calibration-scored.json")],
                "output": out / "typography-calibration-scored.json",
            }
        )
    else:
        steps.append({"name": "score_typography", "skip": "no --typography-input"})
    if args.renders_dir:
        steps.append(
            {
                "name": "make_comparison",
                "cmd": [sys.executable, _script("make_reference_render_comparison.py"),
                        str(args.reference_dir), str(args.renders_dir),
                        str(out / "comparison.png")],
                "output": out / "comparison.png",
            }
        )
    else:
        steps.append({"name": "make_comparison", "skip": "no --renders-dir"})
    if args.qa_report:
        steps.append(
            {
                "name": "validate",
                "cmd": [sys.executable, _script("validate_rebuild_evidence.py"),
                        str(args.qa_report),
                        "--normalized-output", str(out / "qa-report-v2.json")],
                "output": out / "qa-report-v2.json",
            }
        )
    else:
        steps.append({"name": "validate", "skip": "no --qa-report"})
    return steps


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("deck", help="Deck PPTX to audit")
    parser.add_argument("--reference-dir", required=True, help="Reference image directory")
    parser.add_argument("--out-dir", required=True, help="Directory for all products")
    parser.add_argument("--renders-dir", help="Rendered deck images (enables calibrate/comparison)")
    parser.add_argument("--typography-input", help="typography-calibration JSON (enables scoring)")
    parser.add_argument("--qa-report", help="QA report JSON (enables validate)")
    parser.add_argument(
        "--steps",
        help="Comma-separated subset of steps to run (default: all available).",
    )
    parser.add_argument("--stop-on-fail", action="store_true", help="Stop at first nonzero exit.")
    args = parser.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    selected = set(args.steps.split(",")) if args.steps else None
    if selected:
        unknown = selected - set(STEP_ORDER)
        if unknown:
            parser.error(f"unknown --steps: {', '.join(sorted(unknown))}")

    reports: list[dict] = []
    for step in build_steps(args):
        name = step["name"]
        if selected is not None and name not in selected:
            continue
        if "skip" in step:
            reports.append({"step": name, "status": "skipped", "reason": step["skip"]})
            continue
        requires = step.get("requires")
        if requires is not None and not Path(requires).exists():
            reports.append({"step": name, "status": "skipped", "reason": f"missing input {requires}"})
            continue
        completed = subprocess.run(step["cmd"], capture_output=True, text=True, check=False)
        output = step["output"]
        reports.append(
            {
                "step": name,
                "status": "ok" if completed.returncode == 0 else "nonzero",
                "exitCode": completed.returncode,
                "output": str(output) if output.exists() else None,
                "stderrTail": completed.stderr.strip().splitlines()[-3:],
            }
        )
        if completed.returncode != 0 and args.stop_on_fail:
            break

    ran = [item for item in reports if item["status"] in {"ok", "nonzero"}]
    failed = [item for item in ran if item["status"] == "nonzero"]
    result = {
        "schemaVersion": "2.0",
        "deck": str(args.deck),
        "referenceDir": str(args.reference_dir),
        "outDir": str(out),
        "status": "PASS" if ran and not failed else "FAIL" if failed else "EMPTY",
        "steps": reports,
    }
    report_path = out / "pipeline-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(report_path)
    return 0 if ran and not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
