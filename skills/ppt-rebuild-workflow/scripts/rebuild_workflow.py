#!/usr/bin/env python3
"""Shared routing, execution records, evidence assembly and delivery reporting.

This orchestrates the installed presentation runtime; it does not infer a layout,
call image generation, or manufacture visual PASS results.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import copy
import datetime as dt
import hashlib
import json
import os
import posixpath
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from resolve_rebuild_route import resolve_route
from audit_image_alpha import audit_assets
from audit_pptx_structure import audit as audit_structure
from audit_pptx_text_frames import audit as audit_frames

HERE = Path(__file__).resolve().parent
STAGES = ("read", "imagegen", "build", "render", "probe", "operation", "review", "package")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def absolute(base, value):
    path = Path(value)
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def session(folder):
    folder = Path(folder).resolve()
    state = read(folder / "session.json")
    if sha(folder / "task-input.json") != state["taskInputSha256"]:
        raise ValueError("task-input changed after routing; initialize a new run for changed requirements")
    if sha(folder / "route.json") != state["routeSha256"]:
        raise ValueError("route changed after initialization")
    return folder, state, read(folder / "task-input.json"), read(folder / "route.json")


def initialize(task_path: Path, folder: Path):
    task_path, folder = task_path.resolve(), folder.resolve()
    if folder.exists() and any(folder.iterdir()):
        raise ValueError("run directory must be new or empty; previous evidence is preserved")
    task = read(task_path)
    if task.get("sourcePptx"):
        task["sourcePptx"] = str(absolute(task_path.parent, task["sourcePptx"]))
    route = resolve_route(task)
    if route["requiresInput"]:
        raise ValueError("missing route inputs: " + ", ".join(route["missingInputs"]))
    task.setdefault("deliveryProfile", "standard")
    if task["deliveryProfile"] not in {"standard", "benchmark"}:
        raise ValueError("deliveryProfile must be standard or benchmark")
    task.setdefault("assetPolicy", {"alphaFailurePolicy": "manual-handoff"})
    if task["assetPolicy"].get("alphaFailurePolicy", "manual-handoff") not in {"manual-handoff", "required"}:
        raise ValueError("invalid alphaFailurePolicy")
    user_copy = task.get("userCopy", [])
    if not isinstance(user_copy, list) or not all(isinstance(item, dict) for item in user_copy):
        raise ValueError("userCopy must be a list of objects")
    ids = set()
    for item in user_copy:
        if not item.get("id") or item["id"] in ids or type(item.get("page")) is not int or item["page"] < 1:
            raise ValueError("userCopy needs unique IDs and positive page numbers")
        if not isinstance(item.get("text"), str) or not item.get("source"):
            raise ValueError("userCopy needs exact text and an actual source reference")
        ids.add(item["id"])
    task.update({k: route[k] for k in ("taskMode", "qaLevel", "executionProfile", "calibrationPolicy")})
    folder.mkdir(parents=True, exist_ok=True)
    write(folder / "task-input.json", task)
    write(folder / "route.json", route)
    write(folder / "content-contract.json", {"userCopy": user_copy,
          "rule": "User-supplied copy overrides screenshot/PPTX copy only in its stated scope; preserve exact text."})
    state = {"startedAt": now(), "taskInputSha256": sha(folder / "task-input.json"),
             "routeSha256": sha(folder / "route.json"), "sourceTaskFile": str(task_path)}
    if route["taskMode"] == "Mode E":
        source = Path(task["sourcePptx"])
        if not source.is_file():
            raise ValueError("incremental sourcePptx is missing")
        backup = folder / "source-backup.pptx"
        shutil.copyfile(source, backup)
        state.update(sourceSha256=sha(source), sourceBackup=str(backup))
    write(folder / "session.json", state)
    return {"status": "READY", "run": str(folder), "route": route,
            "userCopyBlocks": len(user_copy)}


def preflight(folder):
    folder, _, task, _ = session(folder)
    config = task.get("runtime", {})
    checks = []
    for name, executable in [("python", config.get("pythonExecutable") or sys.executable),
                             ("node", config.get("nodeExecutable"))]:
        if not executable:
            checks.append({"name": name, "status": "NOT_CONFIGURED"})
            continue
        try:
            command = [executable, "-c", "print('child-process-ok')"] if name == "python" else [executable, "--version"]
            result = subprocess.run(command, capture_output=True, timeout=20, check=False)
            checks.append({"name": name, "status": "PASS" if result.returncode == 0 else "FAIL",
                           "exitCode": result.returncode, "detail": result.stderr.decode("utf-8", "replace")[-1200:]})
        except (OSError, subprocess.TimeoutExpired) as exc:
            checks.append({"name": name, "status": "FAIL", "detail": str(exc)})
    if config.get("nodeExecutable"):
        # The finalizer starts Python from Node; independent binary probes
        # miss the Windows nested-process EPERM failure.
        script = ("const r=require('node:child_process').spawnSync(process.argv[1],"
                  "['-B','-c','print(1)'],{encoding:'utf8'});"
                  "if(r.error)console.error(r.error.message);"
                  "if(r.stderr)console.error(r.stderr);process.exit(r.status===0?0:1)")
        try:
            result = subprocess.run([config["nodeExecutable"], "--eval", script,
                                     config.get("pythonExecutable") or sys.executable],
                                    capture_output=True, timeout=20, check=False)
            checks.append({"name": "node-to-python", "status": "PASS" if result.returncode == 0 else "FAIL",
                           "exitCode": result.returncode, "detail": result.stderr.decode("utf-8", "replace")[-1200:]})
        except (OSError, subprocess.TimeoutExpired) as exc:
            checks.append({"name": "node-to-python", "status": "FAIL", "detail": str(exc)})
    for key, suffix in [("nodeModules", "@oai/artifact-tool/package.json"),
                        ("presentationSkillDir", "container_tools/artifact_tool_utils.mjs")]:
        value = config.get(key)
        checks.append({"name": key, "status": ("PASS" if (Path(value) / suffix).is_file() else "FAIL") if value else "NOT_CONFIGURED"})
    result = {"checkedAt": now(), "checks": checks,
              "status": "FAIL" if any(c["status"] == "FAIL" for c in checks) else
                        "INCOMPLETE" if any(c["status"] == "NOT_CONFIGURED" for c in checks) else "PASS",
              "note": "No installs or permission changes. Runtime import/finalizer still validates each real deck."}
    write(folder / "preflight.json", result)
    return result


def begin(folder, stage, pages, revision=0, count=1):
    folder, _, _, route = session(folder)
    if stage not in STAGES or type(revision) is not int or revision < 0 or type(count) is not int or count < 0:
        raise ValueError("invalid stage, revision or count")
    if any(type(p) is not int or p < 1 for p in pages) or len(set(pages)) != len(pages):
        raise ValueError("pages must contain distinct positive integers")
    if stage in {"build", "render"} and revision > route["maxRepairIterations"]:
        raise ValueError("repair budget exhausted; do not relabel repairs as runtime retries")
    if stage == "build" and (route.get("waitForDesignChoice") or route.get("targetMode") is None):
        raise ValueError("build is not authorized by this route; record the user's design choice/new delivery request in a new run")
    event_id = uuid.uuid4().hex
    record = {"id": event_id, "stage": stage, "pages": pages, "revision": revision,
              "count": count, "startedAt": now(), "status": "RUNNING"}
    write(folder / "events" / (event_id + ".json"), record)
    return record


def end(folder, event_id, exit_code, artifacts=()):
    folder, _, _, _ = session(folder)
    if len(event_id) != 32 or any(c not in "0123456789abcdef" for c in event_id):
        raise ValueError("invalid event ID")
    path = folder / "events" / (event_id + ".json")
    event = read(path)
    if event["status"] != "RUNNING":
        raise ValueError("event already completed")
    event["endedAt"] = now()
    event["elapsedMs"] = round((dt.datetime.fromisoformat(event["endedAt"]) - dt.datetime.fromisoformat(event["startedAt"])).total_seconds() * 1000)
    event["exitCode"] = exit_code
    event["status"] = "PASS" if exit_code == 0 else "FAIL"
    event["artifacts"] = [{"path": str(Path(p).resolve()), "sha256": sha(p)} for p in artifacts]
    write(path, event)
    return event


def run_command(folder, stage, pages, revision, count, command, cwd=None, render_receipt=None):
    folder, _, task, _ = session(folder)
    if not command:
        raise ValueError("provide an executable and argument list after --")
    event = begin(folder, stage, pages, revision, count)
    env = os.environ.copy()
    config = task.get("runtime", {})
    if config.get("nodeModules"):
        env["RUNTIME_NODE_MODULES"] = config["nodeModules"]
    env["PYTHONUTF8"] = "1"
    log = folder / "events" / (event["id"] + ".log")
    with log.open("wb") as stream:
        try:
            result = subprocess.run(command, cwd=cwd or folder, env=env, stdout=stream, stderr=subprocess.STDOUT, check=False)
            code = result.returncode
        except OSError as exc:
            stream.write(str(exc).encode("utf-8"))
            code = 127
    result = end(folder, event["id"], code)
    result["log"] = str(log)
    if code == 0 and render_receipt:
        receipt_path = Path(render_receipt).resolve()
        receipt = read(receipt_path)
        if receipt.get("generatedBy") != "rebuild-runtime.mjs" or receipt.get("outputPptxSha256") != sha(receipt["outputPptx"]):
            raise ValueError("invalid integrated render receipt")
        start = dt.datetime.fromisoformat(receipt["renderStartedAt"])
        stop = dt.datetime.fromisoformat(receipt["completedAt"])
        if not dt.datetime.fromisoformat(event["startedAt"]) <= start <= stop <= dt.datetime.fromisoformat(result["endedAt"]):
            raise ValueError("integrated receipt did not originate in this execution")
        render_event = {"id": uuid.uuid4().hex, "stage": "render", "pages": [p["page"] for p in receipt["pages"]],
                        "revision": revision, "count": len(receipt["pages"]), "startedAt": receipt["renderStartedAt"],
                        "endedAt": receipt["completedAt"], "elapsedMs": receipt["renderMs"], "status": "PASS", "exitCode": 0,
                        "sourceReceipt": str(receipt_path), "parentEventId": event["id"]}
        write(folder / "events" / (render_event["id"] + ".json"), render_event)
    return result


def bind_copy(task, extraction):
    result = copy.deepcopy(extraction)
    blocks = {block["id"]: block for block in result.get("textBlocks", [])}
    for item in task.get("userCopy", []):
        if item["id"] not in blocks:
            continue  # other pages have their own extraction files
        block = blocks[item["id"]]
        if block.get("page", result.get("page", item["page"])) != item["page"]:
            raise ValueError("userCopy page conflicts with extraction: " + item["id"])
        block.update(text=item["text"], resolvedText=item["text"], textSource="user-provided",
                     textStatus="exact-source", textEvidence=item["source"], requiresTextRecognition=False)
    return result


def pptx_text(pptx):
    a = "http://schemas.openxmlformats.org/drawingml/2006/main"
    p = "http://schemas.openxmlformats.org/presentationml/2006/main"
    r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    rows = {}
    with zipfile.ZipFile(pptx) as archive:
        relations = ET.fromstring(archive.read("ppt/_rels/presentation.xml.rels"))
        targets = {node.get("Id"): node.get("Target") for node in relations}
        root = ET.fromstring(archive.read("ppt/presentation.xml"))
        for page, node in enumerate(root.findall(f"{{{p}}}sldIdLst/{{{p}}}sldId"), 1):
            target = targets[node.get(f"{{{r}}}id")]
            member = target.lstrip("/") if target.startswith("/") else posixpath.normpath("ppt/" + target)
            slide = ET.fromstring(archive.read(member))
            for shape in slide.findall(f".//{{{p}}}sp"):
                props = shape.find(f"{{{p}}}nvSpPr/{{{p}}}cNvPr")
                body = shape.find(f"{{{p}}}txBody")
                if props is not None and body is not None:
                    text = "\n".join("".join(t.text or "" for t in para.findall(f".//{{{a}}}t")) for para in body.findall(f"{{{a}}}p"))
                    rows.setdefault((page, props.get("name")), []).append(text)
    return rows


def audit_copy(task, pptx, layouts):
    items = task.get("userCopy", [])
    if not items:
        return {"status": "NOT_APPLICABLE", "items": []}
    names = {}
    for layout in layouts:
        for obj in layout.get("objects", []):
            if obj.get("sourceExtractionId") and obj.get("name"):
                names.setdefault(obj["sourceExtractionId"], []).append(obj["name"])
    actual = pptx_text(pptx)
    compact = lambda text: text.replace("\r\n", "\n").replace("\n", "")
    results = []
    for item in items:
        object_names = [item["pptxShapeName"]] if item.get("pptxShapeName") else names.get(item["id"], [item["id"]])
        values = [actual.get((item["page"], n), []) for n in object_names]
        matched = all(len(v) == 1 for v in values)
        observed = "".join(v[0] for v in values) if matched else None
        results.append({"id": item["id"], "page": item["page"], "source": item["source"],
                        "objects": object_names, "expected": item["text"], "actual": observed,
                        "status": "PASS" if observed is not None and compact(observed) == compact(item["text"]) else "FAIL"})
    return {"generatedBy": "rebuild_workflow.py", "status": "PASS" if all(i["status"] == "PASS" for i in results) else "FAIL",
            "items": results, "note": "Checks exported editable text against supplied copy; only line-break differences are ignored."}


def prepare_review(folder, pptx, render_receipt):
    folder, _, _, route = session(folder)
    pptx = Path(pptx).resolve()
    receipt = read(render_receipt)
    if receipt.get("outputPptxSha256") != sha(pptx):
        raise ValueError("render receipt belongs to a different PPTX")
    pages = copy.deepcopy(receipt.get("pages", []))
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        structure_future = pool.submit(audit_structure, pptx)
        frames_future = pool.submit(audit_frames, pptx, body_min_chars=45, min_overlap_px=1.0)
        structure, frames = structure_future.result(), frames_future.result()
    expected = list(range(1, structure["slideCount"] + 1))
    # Incremental comparisons can use a separate mode-specific report; full B/C
    # render verification always covers the delivered deck, including reused pages.
    page_ids = [p.get("page", 0) for p in pages]
    incremental_subset = route["taskMode"] == "Mode E" and page_ids and len(set(page_ids)) == len(page_ids) and set(page_ids).issubset(set(expected))
    if not incremental_subset and sorted(page_ids) != expected:
        raise ValueError("render receipt must cover every page exactly once")
    for page in pages:
        image = absolute(Path(render_receipt).resolve().parent, page["renderPath"])
        if page.get("renderSha256") != sha(image):
            raise ValueError("stale render receipt for page " + str(page["page"]))
        page.update(renderPath=str(image), reviewer="", observations="", coordinateStatus="PENDING",
                    typographyStatus="PENDING", triggeredChecks=[], unresolvedItems=[])
    for name, data in [("structure-audit.json", structure), ("text-frame-audit.json", frames)]:
        data["outputPptxSha256"] = sha(pptx)
        write(folder / name, data)
    review = {"schemaVersion": "2.0", "outputPptx": str(pptx), "outputPptxSha256": sha(pptx),
              "acceptanceRenderer": receipt.get("acceptanceRenderer", ""), "pages": pages,
              "contentStatus": "PENDING", "visionAuditStatus": "PENDING", "visualOverlapCount": None,
              "visualFidelityStatus": "PENDING", "majorFidelityDeviationCount": None,
              "minorFidelityDeviationCount": None, "visibleAssetSeamCount": None,
              "editableBoundaryStatus": "PENDING", "autoFidelityBlocked": None,
              "textRecovery": {"unresolvedItems": [], "needsHumanReview": False},
              "geometryExceptions": [], "issues": []}
    if route["qaLevel"] == "Level 3" or route.get("changedRegionQaLevel") == "Level 3":
        review["level3Gates"] = {name: {"status": "PENDING", "automatedEvidence": "", "manualEvidence": ""}
            for name in ("wholeReferenceImageEmbedded", "combinedBackgroundPersonPictureCount",
                         "contentPicturesAreIndependentObjects", "visualOverlapCount", "visualExtractionComplete",
                         "typographyCalibrationComplete", "forbiddenOverlayShapesDetected")}
    # One review per version; never erase an earlier human/model observation.
    path = folder / ("review-" + sha(pptx)[:12] + ".json")
    if path.exists():
        raise ValueError("review already exists for this PPTX; edit its pending fields directly")
    write(path, review)
    return {"status": "PENDING_VISUAL_REVIEW", "review": str(path), "slideCount": structure["slideCount"]}


def timings(folder):
    events = sorted((read(p) for p in (folder / "events").glob("*.json")), key=lambda e: e["startedAt"])
    finished = [e for e in events if e["status"] != "RUNNING"]
    builds = [e for e in finished if e["stage"] == "build" and e["status"] == "PASS"]
    return {"stages": events, "autoIterationCount": max((e["revision"] for e in builds), default=None),
            "renderCount": sum(e["count"] for e in finished if e["stage"] == "render" and e["status"] == "PASS"),
            "probeRenderCount": sum(e["count"] for e in finished if e["stage"] == "probe" and e["status"] == "PASS"),
            "imageGenerationCount": sum(e["count"] for e in finished if e["stage"] == "imagegen"),
            "repairedPages": sorted({p for e in builds if e["revision"] > 0 for p in e["pages"]}),
            "incompleteEvents": [e["id"] for e in events if e["status"] == "RUNNING"],
            "note": "Counts cover logged calls only. Overlapping event durations are not end-to-end elapsed time."}


def assemble_report(folder, evidence_path):
    folder, state, task, route = session(folder)
    evidence_path = Path(evidence_path).resolve()
    evidence = read(evidence_path)
    ref = lambda value: str(absolute(evidence_path.parent, value))
    review_path = Path(ref(evidence["reviewFile"]))
    review = read(review_path)
    pptx = Path(review["outputPptx"])
    if sha(pptx) != review["outputPptxSha256"]:
        raise ValueError("PPTX changed after visual review; render and review the new version")
    structure, frames = read(folder / "structure-audit.json"), read(folder / "text-frame-audit.json")
    if any(a.get("outputPptxSha256") != sha(pptx) for a in (structure, frames)):
        raise ValueError("structure audit is stale; prepare review for the final PPTX")
    report = {k: copy.deepcopy(v) for k, v in review.items() if k not in {"pages", "outputPptxSha256"}}
    report.update(schemaVersion="2.0", generatedBy="rebuild_workflow.py", taskMode=route["taskMode"], qaLevel=route["qaLevel"],
                  executionProfile=route["executionProfile"], calibrationPolicy=route["calibrationPolicy"],
                  deliveryProfile=task["deliveryProfile"], taskInputFile=str(folder / "task-input.json"),
                  visionAuditReport=str(review_path), visualFidelityReport=str(review_path),
                  renderVerificationFile=str(review_path), outputPptx=str(pptx))
    for key in ("slideCount", "mediaCount", "emptyMediaCount", "textRunCount", "shapeCount", "fontFamilies",
                "unresolvedInheritedFonts", "fullSlideImageRiskPages"):
        report[key] = structure.get(key)
    report.update({k: frames["totals"][k] for k in ("textFrameIntersections", "thinShapeTextFrameIntersections",
                   "unresolvedTextFrameCount", "unresolvedGroupTransformCount")})
    report["auditArtifacts"] = {"structureAudit": str(folder / "structure-audit.json"),
                                "textFrameAudit": str(folder / "text-frame-audit.json")}
    for key in ("visualExtractionFiles", "layoutSpecFiles", "measurementAnnotatedImages", "typographyCalibrationFiles"):
        report[key] = [ref(v) for v in evidence.get(key, [])]
    for key in ("referenceRenderComparison", "referenceRenderPairingManifest"):
        if evidence.get(key): report[key] = ref(evidence[key])
    if route["executionProfile"] == "strict":
        values = [ref(p) for p in evidence.get("coordinateCalibrationFiles", [])]
        report["coordinateCalibration"] = {"artifacts": values,
            "status": "PASS" if values and all(read(p).get("status") == "PASS" for p in values) else "PENDING"}
    else:
        report["coordinateCalibration"] = {"status": "NOT_REQUIRED", "reason": "Targeted profile; actual final-page observations and any computed triggers are in the shared review."}
    report["timings"] = timings(folder)
    report["autoIterationCount"] = report["timings"]["autoIterationCount"]
    copy_audit = audit_copy(task, pptx, [read(p) for p in report["layoutSpecFiles"]])
    copy_audit["outputPptxSha256"] = sha(pptx)
    write(folder / "user-copy-audit.json", copy_audit)
    report["userCopyAuditFile"] = str(folder / "user-copy-audit.json")
    if (folder / "asset-audit.json").is_file():
        report["assetAuditFile"] = str(folder / "asset-audit.json")
    path = folder / "qa-report.json"
    write(path, report)
    if route["qaLevel"] in {"Level 2", "Level 3"}:
        proc = subprocess.run([sys.executable, "-X", "utf8", "-B", str(HERE / "validate_rebuild_evidence.py"), str(path)],
                              capture_output=True, text=True, encoding="utf-8", check=False)
        try:
            validation = json.loads(proc.stdout)
        except ValueError:
            validation = {"status": "INVALID", "errors": [proc.stderr or proc.stdout]}
    else:
        # A/E have different contracts. Keep their actual dedicated evidence,
        # never interpret the Level 2/3 validator's NOT_APPLICABLE as a pass.
        mode_path = evidence.get("modeSpecificEvidenceFile")
        mode = read(ref(mode_path)) if mode_path else {}
        valid_binding = mode.get("outputPptxSha256") == sha(pptx)
        source_ok = route["taskMode"] != "Mode E" or (sha(task["sourcePptx"]) == state["sourceSha256"] == sha(state["sourceBackup"]))
        validation = {"status": mode.get("status", "INCOMPLETE") if valid_binding and source_ok else "INCOMPLETE",
                      "modeSpecificEvidenceFile": ref(mode_path) if mode_path else None,
                      "note": "Mode-specific checks remain required; only file identity/source preservation checked here."}
    write(folder / "evidence-validation.json", validation)
    assets = read(folder / "asset-audit.json") if (folder / "asset-audit.json").is_file() else {}
    summary = {"content": "FAIL" if copy_audit["status"] == "FAIL" or review.get("textRecovery", {}).get("unresolvedItems") else
                          review.get("contentStatus", "PENDING"),
               "visual": review.get("visualFidelityStatus", "PENDING"),
               "editability": "MANUAL_CUTOUT_REQUIRED" if assets.get("manualCutoutAssets") else review.get("editableBoundaryStatus", "PENDING"),
               "evidence": validation["status"]}
    report.update(dimensions=summary, evidenceStatus=validation["status"],
                  manualCutoutAssets=assets.get("manualCutoutAssets", []))
    write(path, report)
    lines = [f"内容：{summary['content']}；视觉：{summary['visual']}；编辑范围：{summary['editability']}；证据：{summary['evidence']}。",
             f"\n成品：{pptx}", f"\n路由：{route['taskMode']} → {route['targetMode']}；{route['executionProfile']}。"]
    if assets.get("manualCutoutAssets"):
        lines.append("\n待人工抠图：" + "、".join(assets["manualCutoutAssets"]) + "。对象替换位置与原素材见 asset-audit.json。")
    for issue in review.get("issues", []):
        lines.append("\n- " + (issue if isinstance(issue, str) else json.dumps(issue, ensure_ascii=False)))
    if task["deliveryProfile"] == "benchmark":
        lines.append("\n阶段计时与失败日志：events/；报告统计仅包含实际登记的调用。")
    (folder / "delivery-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": validation["status"], "report": str(path), "summary": str(folder / "delivery-summary.md"), "dimensions": summary}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    init = commands.add_parser("init")
    init.add_argument("task")
    init.add_argument("--run-dir", required=True)
    for action in ("preflight", "assets", "bind-copy", "begin", "end", "run", "prepare-review", "report"):
        p = commands.add_parser(action)
        p.add_argument("run_dir")
        if action == "assets": p.add_argument("manifest")
        if action == "bind-copy":
            p.add_argument("extraction"); p.add_argument("--output", required=True)
        if action in {"begin", "run"}:
            p.add_argument("--stage", choices=STAGES, required=True)
            p.add_argument("--pages", type=int, nargs="*", default=[])
            p.add_argument("--revision", type=int, default=0)
            p.add_argument("--count", type=int, default=1)
        if action == "run":
            p.add_argument("--cwd"); p.add_argument("--render-receipt")
        if action == "end":
            p.add_argument("id"); p.add_argument("--exit-code", type=int, required=True)
            p.add_argument("--artifacts", nargs="*", default=[])
        if action == "prepare-review":
            p.add_argument("--pptx", required=True); p.add_argument("--render-receipt", required=True)
        if action == "report": p.add_argument("evidence")
    argv = sys.argv[1:]
    command = []
    if "--" in argv:
        split = argv.index("--"); command = argv[split + 1:]; argv = argv[:split]
    args = parser.parse_args(argv)
    try:
        if args.action == "init": result = initialize(Path(args.task), Path(args.run_dir))
        elif args.action == "preflight": result = preflight(args.run_dir)
        elif args.action == "assets":
            folder, _, task, _ = session(args.run_dir)
            source = Path(args.manifest).resolve()
            result = audit_assets(read(source), source.parent, task["assetPolicy"].get("alphaFailurePolicy", "manual-handoff"))
            write(folder / "asset-audit.json", result)
        elif args.action == "bind-copy":
            _, _, task, _ = session(args.run_dir)
            result = bind_copy(task, read(args.extraction)); write(args.output, result)
        elif args.action == "begin": result = begin(args.run_dir, args.stage, args.pages, args.revision, args.count)
        elif args.action == "end": result = end(args.run_dir, args.id, args.exit_code, args.artifacts)
        elif args.action == "run": result = run_command(args.run_dir, args.stage, args.pages, args.revision, args.count, command, args.cwd, args.render_receipt)
        elif args.action == "prepare-review": result = prepare_review(args.run_dir, args.pptx, args.render_receipt)
        else: result = assemble_report(args.run_dir, args.evidence)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result.get("status") in {None, "READY", "PASS", "RUNNING", "PENDING_VISUAL_REVIEW"} else 1
    except (OSError, ValueError, KeyError, TypeError, ImportError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(json.dumps({"status": "INVALID", "error": str(exc)}, ensure_ascii=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
