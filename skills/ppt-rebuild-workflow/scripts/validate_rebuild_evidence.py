#!/usr/bin/env python3
"""Validate PPT rebuild evidence, canonicalize legacy fields, and enforce QA gates."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

from _io_common import write_json

ALIASES = {
    "renderBackend": "acceptanceRenderer",
    "flaggedPages": "visionFlaggedPages",
    "autoIteration": "autoIterationCount",
    "unexpectedTextOverlapCount": "visualOverlapCount",
}


def canonicalize(value, warnings: list[str], location: str = "$"):
    if isinstance(value, list):
        return [canonicalize(item, warnings, f"{location}[]") for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        canonical = ALIASES.get(key, key)
        if canonical != key:
            warnings.append(f"{location}.{key} is legacy; use {canonical}")
        if canonical in result:
            warnings.append(f"{location}.{key} ignored because canonical field exists")
            continue
        result[canonical] = canonicalize(item, warnings, f"{location}.{canonical}")
    if location.endswith("coordinateSystem") and ("w" in result or "h" in result):
        if "w" in result:
            result["width"] = result.pop("w")
            warnings.append(f"{location}.w is legacy; use width")
        if "h" in result:
            result["height"] = result.pop("h")
            warnings.append(f"{location}.h is legacy; use height")
    return result


def resolve_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base_dir / path


def load_json(path: Path, errors: list[str]) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"cannot read JSON {path}: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"JSON root must be an object: {path}")
        return None
    return value


def require_files(report: dict, base_dir: Path, errors: list[str]) -> None:
    scalar_fields = (
        "taskInputFile",
        "referenceRenderComparison",
        "referenceRenderPairingManifest",
        "visionAuditReport",
        "visualFidelityReport",
    )
    list_fields = (
        "visualExtractionFiles",
        "measurementAnnotatedImages",
        "typographyCalibrationFiles",
        "layoutSpecFiles",
    )
    for field in scalar_fields:
        value = report.get(field)
        if not value:
            errors.append(f"required artifact field is empty: {field}")
        elif not resolve_path(base_dir, value).exists():
            errors.append(f"artifact does not exist: {field}={value}")
    for field in list_fields:
        values = report.get(field)
        if not isinstance(values, list) or not values:
            errors.append(f"required artifact list is empty: {field}")
            continue
        for value in values:
            if not isinstance(value, str) or not resolve_path(base_dir, value).exists():
                errors.append(f"artifact does not exist: {field}={value}")


def validate_calibration(report: dict, base_dir: Path, errors: list[str], gates: list[str]) -> None:
    calibration = report.get("coordinateCalibration")
    if not isinstance(calibration, dict):
        errors.append("coordinateCalibration must be an object")
        return
    artifacts = calibration.get("artifacts")
    if calibration.get("status") == "PASS" and (not isinstance(artifacts, list) or not artifacts):
        errors.append("coordinateCalibration PASS requires computed artifacts")
        return
    statuses = []
    for value in artifacts or []:
        path = resolve_path(base_dir, value)
        data = load_json(path, errors)
        if not data:
            continue
        if data.get("generatedBy") != "calibrate_reference_render.py":
            errors.append(f"calibration is not computed by the calibration script: {path}")
        statuses.append(data.get("status"))
    if (
        calibration.get("status") != "PASS"
        or not statuses
        or any(status != "PASS" for status in statuses)
    ):
        gates.append("coordinate calibration did not pass with computed evidence")


def validate_typography(report: dict, base_dir: Path, errors: list[str], gates: list[str]) -> None:
    for value in report.get("typographyCalibrationFiles", []):
        path = resolve_path(base_dir, value)
        data = load_json(path, errors)
        if not data:
            continue
        if data.get("generatedBy") != "score_typography_candidates.py":
            errors.append(f"typography evidence was not measured by the scoring script: {path}")
        if data.get("status") != "PASS":
            gates.append(f"typography calibration failed: {path}")


def validate_cross_references(report: dict, base_dir: Path, errors: list[str]) -> None:
    extraction_ids = set()
    for value in report.get("visualExtractionFiles", []):
        data = load_json(resolve_path(base_dir, value), errors)
        if not data:
            continue
        for field in ("textBlocks", "shapes", "images"):
            for item in data.get(field, []):
                if item.get("id"):
                    extraction_ids.add(item["id"])
    for value in report.get("layoutSpecFiles", []):
        data = load_json(resolve_path(base_dir, value), errors)
        if not data:
            continue
        for item in data.get("objects", []):
            source_id = item.get("sourceExtractionId")
            has_alternative = bool(item.get("measurementEvidence") or item.get("source"))
            if source_id and source_id not in extraction_ids:
                errors.append(f"unknown sourceExtractionId {source_id} in {value}")
            if not source_id and not has_alternative:
                errors.append(f"layout object lacks extraction source: {value}:{item.get('name')}")


def validate_level3(report: dict, errors: list[str], gates: list[str]) -> None:
    required = (
        "wholeReferenceImageEmbedded",
        "combinedBackgroundPersonPictureCount",
        "contentPicturesAreIndependentObjects",
        "visualOverlapCount",
        "visualExtractionComplete",
        "typographyCalibrationComplete",
        "forbiddenOverlayShapesDetected",
    )
    level3 = report.get("level3Gates")
    if not isinstance(level3, dict):
        errors.append("Level 3 report requires level3Gates")
        return
    for name in required:
        gate = level3.get(name)
        if not isinstance(gate, dict):
            errors.append(f"missing Level 3 gate: {name}")
            continue
        missing = {"automatedEvidence", "manualEvidence", "status"} - set(gate)
        if missing:
            errors.append(f"Level 3 gate {name} misses fields: {sorted(missing)}")
        if gate.get("status") != "PASS":
            gates.append(f"Level 3 gate did not pass: {name}")
        if not gate.get("automatedEvidence"):
            errors.append(f"Level 3 gate lacks automated evidence: {name}")


def validate_gates(report: dict, gates: list[str]) -> None:
    expectations = {
        "visionAuditStatus": "PASS",
        "visualOverlapCount": 0,
        "visualFidelityStatus": "PASS",
        "majorFidelityDeviationCount": 0,
        "visibleAssetSeamCount": 0,
        "textFrameIntersections": 0,
        "unresolvedTextFrameCount": 0,
        "unresolvedGroupTransformCount": 0,
        "autoFidelityBlocked": False,
    }
    for field, expected in expectations.items():
        if report.get(field) != expected:
            gates.append(f"{field} must equal {expected!r}; got {report.get(field)!r}")
    iterations = report.get("autoIterationCount")
    if not isinstance(iterations, int) or not 0 <= iterations <= 3:
        gates.append("autoIterationCount must be an integer from 0 through 3")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", help="QA report JSON")
    parser.add_argument("--base-dir")
    parser.add_argument("--normalized-output")
    args = parser.parse_args()
    report_path = Path(args.report)
    errors: list[str] = []
    warnings: list[str] = []
    gates: list[str] = []
    raw = load_json(report_path, errors)
    if raw is None:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2
    report = canonicalize(copy.deepcopy(raw), warnings)
    report["schemaVersion"] = "2.0"
    base_dir = Path(args.base_dir) if args.base_dir else report_path.parent

    required = ("outputPptx", "qaLevel", "acceptanceRenderer")
    for field in required:
        if not report.get(field):
            errors.append(f"required field is empty: {field}")
    require_files(report, base_dir, errors)
    validate_calibration(report, base_dir, errors, gates)
    validate_typography(report, base_dir, errors, gates)
    validate_cross_references(report, base_dir, errors)
    validate_gates(report, gates)
    if str(report.get("qaLevel", "")).lower() in {"3", "level 3", "level3"}:
        validate_level3(report, errors, gates)

    result = {
        "schemaVersion": "2.0",
        "status": "INVALID" if errors else "FAIL" if gates else "PASS",
        "errors": errors,
        "gateFailures": gates,
        "migrationWarnings": warnings,
    }
    if args.normalized_output:
        write_json(Path(args.normalized_output), report)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if errors else 1 if gates else 0


if __name__ == "__main__":
    raise SystemExit(main())
