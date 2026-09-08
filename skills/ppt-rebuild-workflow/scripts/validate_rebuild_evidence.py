#!/usr/bin/env python3
"""Validate PPT rebuild evidence, canonicalize legacy fields, and enforce QA gates."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

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
        "layoutSpecFiles",
    )
    if report.get("executionProfile", "strict") == "strict":
        list_fields += ("measurementAnnotatedImages", "typographyCalibrationFiles")
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
        "unresolvedTextFrameCount": 0,
        "unresolvedGroupTransformCount": 0,
        "autoFidelityBlocked": False,
    }
    for field, expected in expectations.items():
        if report.get(field) != expected:
            gates.append(f"{field} must equal {expected!r}; got {report.get(field)!r}")
    intersections = report.get("textFrameIntersections")
    if type(intersections) is not int or intersections < 0:
        gates.append("textFrameIntersections must be a nonnegative integer")
    elif intersections and not report.get("geometryExceptions"):
        gates.append("text frame intersections require item-specific visual review")
    iterations = report.get("autoIterationCount")
    budget = {"fast": 1, "balanced": 2, "strict": 3}.get(report.get("executionProfile", "strict"), 3)
    if type(iterations) is not int or not 0 <= iterations <= budget:
        gates.append(f"autoIterationCount must be an integer from 0 through {budget}")
    if report.get("textRecovery", {}).get("unresolvedItems"):
        gates.append("textRecovery has unresolved items")
    if report.get("needsHumanReview") or report.get("textRecovery", {}).get("needsHumanReview"):
        gates.append("required human review is unresolved")



def validate_targeted(report: dict, base_dir: Path, errors: list[str], gates: list[str], targeted=True) -> None:
    value = report.get("renderVerificationFile")
    if not isinstance(value, str) or not value:
        errors.append("targeted calibration requires renderVerificationFile")
        return
    data = load_json(resolve_path(base_dir, value), errors)
    if not data:
        return
    pptx = resolve_path(base_dir, report.get("outputPptx", ""))
    if not pptx.is_file():
        errors.append("outputPptx does not exist")
    elif data.get("outputPptxSha256") != hashlib.sha256(pptx.read_bytes()).hexdigest():
        errors.append("render verification is not bound to the current PPTX")
    calibration = report.get("coordinateCalibration", {})
    if targeted and (calibration.get("status") != "NOT_REQUIRED" or not calibration.get("reason")):
        errors.append("targeted mode requires NOT_REQUIRED plus reason; computed triggers are recorded per page")
    count = report.get("slideCount")
    if type(count) is not int or count < 1:
        errors.append("slideCount must be a positive integer")
        return
    pages = data.get("pages", [])
    if not isinstance(pages, list) or not all(isinstance(p, dict) for p in pages):
        errors.append("render verification pages must be objects")
        return
    ids = [p.get("page") for p in pages]
    if len(ids) != count or len(set(str(p) for p in ids)) != count:
        errors.append("render verification must cover every page exactly once")
    pairing_value = report.get("referenceRenderPairingManifest", "")
    pairing = load_json(resolve_path(base_dir, pairing_value), errors) if pairing_value else None
    pairs = pairing.get("pairings", []) if pairing else []
    if len(pairs) != count or {str(p.get("page")) for p in pairs} != {str(p) for p in ids}:
        errors.append("render verification page IDs do not match the pairing manifest")
    pair_map = {str(p.get("page")): p for p in pairs}
    for page in pages:
        label = f"page {page.get('page')}"
        if not page.get("reviewer") or not page.get("observations"):
            errors.append(f"{label} requires actual reviewer observations")
        for status in ("coordinateStatus", "typographyStatus"):
            if page.get(status) != "PASS":
                gates.append(f"{label} {status} did not pass")
        if "unresolvedItems" not in page or not isinstance(page["unresolvedItems"], list):
            errors.append(f"{label} requires unresolvedItems list")
        elif page["unresolvedItems"]:
            gates.append(f"{label} has unresolved render issues")
        render_value = page.get("renderPath")
        render = resolve_path(base_dir, render_value) if isinstance(render_value, str) else None
        if not render or not render.is_file():
            errors.append(f"{label} render is missing")
        else:
            if page.get("renderSha256") != hashlib.sha256(render.read_bytes()).hexdigest():
                errors.append(f"{label} render evidence is stale")
            pair = pair_map.get(str(page.get("page")), {})
            if not pairing or not pairing.get("renderDirectory") or not pair.get("render"):
                errors.append(f"{label} pairing lacks render path")
            else:
                expected = resolve_path(base_dir, pairing["renderDirectory"]) / pair["render"]
                if expected.resolve() != render.resolve():
                    errors.append(f"{label} render differs from paired render")
        triggers = page.get("triggeredChecks")
        if not isinstance(triggers, list):
            errors.append(f"{label} requires triggeredChecks list")
            continue
        for trigger in triggers:
            if not isinstance(trigger, dict):
                errors.append(f"{label} trigger must be an object")
                continue
            generator = {"coordinate": "calibrate_reference_render.py",
                         "typography": "score_typography_candidates.py"}.get(trigger.get("kind"))
            if not generator or not trigger.get("reason") or not trigger.get("evidenceFile"):
                errors.append(f"{label} trigger lacks kind, reason or computed evidence")
                continue
            evidence = load_json(resolve_path(base_dir, trigger["evidenceFile"]), errors)
            if evidence and evidence.get("generatedBy") != generator:
                errors.append(f"{label} trigger has wrong evidence generator")
            if not evidence or evidence.get("status") != "PASS":
                gates.append(f"{label} triggered calibration did not pass")


def validate_geometry_exceptions(report, base_dir, errors, gates):
    exceptions = report.get("geometryExceptions", [])
    if not exceptions:
        return
    audit_path = report.get("auditArtifacts", {}).get("textFrameAudit")
    if not audit_path:
        errors.append("geometry exceptions require the actual text-frame audit")
        return
    audit = load_json(resolve_path(base_dir, audit_path), errors)
    if not audit:
        return
    pptx = resolve_path(base_dir, report.get("outputPptx", ""))
    if not pptx.is_file() or audit.get("outputPptxSha256") != hashlib.sha256(pptx.read_bytes()).hexdigest():
        errors.append("geometry exception audit is not bound to the current PPTX")
    expected = {(p.get("page"), i) for p in audit.get("pages", [])
                for i, _ in enumerate(p.get("textFrameIntersections", []))}
    if len(expected) != report.get("textFrameIntersections"):
        errors.append("raw textFrameIntersections differs from the audit; do not clear the count")
    seen = set()
    for item in exceptions:
        if not isinstance(item, dict):
            errors.append("geometry exception must be an object")
            continue
        key = (item.get("page"), item.get("intersectionIndex"))
        if key in seen or key not in expected:
            errors.append("geometry exception is duplicated or does not identify a real intersection")
        seen.add(key)
        if not item.get("reviewer") or not item.get("reason") or not item.get("renderObservation"):
            errors.append("geometry exception requires reviewer, reason and actual renderObservation")
        if item.get("status") != "NO_VISIBLE_TEXT_OVERLAP":
            gates.append("geometry exception did not resolve visible text overlap")
    if seen != expected:
        gates.append("not all text-frame intersections have been reviewed")


def validate_asset_and_copy_evidence(report, base_dir, errors, gates):
    level3 = str(report.get("qaLevel", "")).lower().replace(" ", "") in {"3", "level3"}
    task_value = report.get("taskInputFile")
    task = load_json(resolve_path(base_dir, task_value), errors) if task_value else {}
    task = task or {}
    value = report.get("assetAuditFile")
    if level3 and not value:
        errors.append("Level 3 requires assetAuditFile with actual transparency checks")
    if value:
        asset_audit = load_json(resolve_path(base_dir, value), errors)
        if asset_audit:
            if asset_audit.get("generatedBy") != "audit_image_alpha.py":
                errors.append("asset audit must come from audit_image_alpha.py")
            from audit_image_alpha import inspect_alpha
            rows = asset_audit.get("assets", [])
            ids = [row.get("id") for row in rows]
            if len(set(ids)) != len(ids):
                errors.append("duplicate asset audit IDs")
            boundary = task.get("editableBoundary", {})
            required = set(boundary.get("mustHaveAlpha", []))
            independent = set(boundary.get("mustRemainIndependentImages", []))
            if not (required | independent).issubset(set(ids)):
                errors.append("asset audit does not cover the requested independent/alpha asset IDs")
            for row in rows:
                try:
                    path = resolve_path(base_dir, row["path"])
                    actual = inspect_alpha(path)
                    if actual["sha256"] != row.get("sha256"):
                        errors.append(f"stale asset audit: {row.get('id')}")
                    if actual["status"] in {"EMPTY", "UNREADABLE"}:
                        gates.append(f"unusable asset: {row.get('id')}")
                    if (row.get("requiresAlpha") or row.get("id") in required) and actual["status"] != "ALPHA_PRESENT":
                        gates.append(f"required alpha is absent: {row.get('id')}; manual handoff is not complete Level 3")
                except (OSError, ValueError, KeyError) as exc:
                    errors.append(f"cannot inspect asset {row.get('id')}: {exc}")
    if report.get("generatedBy") == "rebuild_workflow.py":
        from resolve_rebuild_route import resolve_route
        try:
            route = resolve_route(task)
            for field in ("taskMode", "qaLevel", "executionProfile", "calibrationPolicy"):
                if report.get(field) != route[field]:
                    errors.append(f"report disagrees with input route: {field}")
        except (TypeError, ValueError) as exc:
            errors.append(f"invalid task route: {exc}")
        for key in ("contentStatus", "editableBoundaryStatus"):
            if report.get(key) != "PASS":
                gates.append(f"{key} did not pass")
        if report.get("timings", {}).get("incompleteEvents"):
            gates.append("execution events remain unfinished")
    if task.get("userCopy"):
        value = report.get("userCopyAuditFile")
        if not value:
            errors.append("user-provided copy requires exported-text audit, not screenshot OCR")
            return
        data = load_json(resolve_path(base_dir, value), errors)
        pptx = resolve_path(base_dir, report.get("outputPptx", ""))
        if data and pptx.is_file():
            if data.get("outputPptxSha256") != hashlib.sha256(pptx.read_bytes()).hexdigest():
                errors.append("user-copy audit is stale")
            from rebuild_workflow import audit_copy
            layouts = [load_json(resolve_path(base_dir, p), errors) or {} for p in report.get("layoutSpecFiles", [])]
            actual = audit_copy(task, pptx, layouts)
            if actual["status"] != "PASS":
                gates.append("exported editable text differs from the user's supplied copy")



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
    profile = report.get("executionProfile", "strict")
    if profile not in {"fast", "balanced", "strict"}:
        errors.append("unsupported executionProfile")
    level = str(report.get("qaLevel", "")).lower().replace(" ", "")
    if level not in {"2", "3", "level2", "level3"}:
        errors.append("validator supports only Level 2/3; use mode-specific QA for Level 1/4")
    policy = "full" if profile == "strict" else "targeted"
    if report.get("calibrationPolicy", policy) != policy:
        errors.append("calibrationPolicy conflicts with executionProfile")
    if not resolve_path(base_dir, report.get("outputPptx", "")).is_file():
        errors.append("outputPptx does not exist")
    require_files(report, base_dir, errors)
    if profile == "strict":
        validate_calibration(report, base_dir, errors, gates)
        validate_typography(report, base_dir, errors, gates)
        if report.get("renderVerificationFile"):
            validate_targeted(report, base_dir, errors, gates, targeted=False)
    else:
        validate_targeted(report, base_dir, errors, gates)
    validate_cross_references(report, base_dir, errors)
    validate_gates(report, gates)
    validate_geometry_exceptions(report, base_dir, errors, gates)
    validate_asset_and_copy_evidence(report, base_dir, errors, gates)
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
        normalized_path = Path(args.normalized_output)
        normalized_path.parent.mkdir(parents=True, exist_ok=True)
        normalized_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if errors else 1 if gates else 0


if __name__ == "__main__":
    raise SystemExit(main())
