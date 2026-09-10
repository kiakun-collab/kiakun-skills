from __future__ import annotations
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/validate_rebuild_evidence.py"


class AdaptiveEvidenceTests(unittest.TestCase):
    def make_fixture(self, root):
        def write(name, value):
            (root / name).write_text(json.dumps(value), encoding="utf-8")
            return name
        (root / "deck.pptx").write_bytes(b"fixture only: artifact identity binding")
        (root / "slide-01.png").write_bytes(b"fixture only: rendered artifact identity")
        (root / "comparison.png").write_bytes(b"fixture")
        write("extraction.json", {"textBlocks": [{"id": "title"}]})
        write("layout.json", {"objects": [{"name": "title", "sourceExtractionId": "title"}]})
        write("task.json", {"executionProfile": "balanced"})
        write("vision.json", {"observations": "Fixture review"})
        write("pairing.json", {"renderDirectory": ".", "pairings": [{"page": 1, "render": "slide-01.png"}]})
        verification = {
            "outputPptxSha256": hashlib.sha256((root / "deck.pptx").read_bytes()).hexdigest(),
            "pages": [{"page": 1, "renderPath": "slide-01.png",
                       "renderSha256": hashlib.sha256((root / "slide-01.png").read_bytes()).hexdigest(),
                       "reviewer": "test fixture", "observations": "Coordinates and line wrapping reviewed",
                       "coordinateStatus": "PASS", "typographyStatus": "PASS",
                       "triggeredChecks": [], "unresolvedItems": []}]}
        write("verification.json", verification)
        report = {
            "outputPptx": "deck.pptx", "qaLevel": "Level 2",
            "executionProfile": "balanced", "calibrationPolicy": "targeted",
            "acceptanceRenderer": "fixture", "slideCount": 1,
            "taskInputFile": "task.json", "referenceRenderComparison": "comparison.png",
            "referenceRenderPairingManifest": "pairing.json",
            "visionAuditReport": "vision.json", "visualFidelityReport": "vision.json",
            "visualExtractionFiles": ["extraction.json"], "layoutSpecFiles": ["layout.json"],
            "renderVerificationFile": "verification.json",
            "coordinateCalibration": {"status": "NOT_REQUIRED", "reason": "No trigger in final render"},
            "visionAuditStatus": "PASS", "visualOverlapCount": 0,
            "visualFidelityStatus": "PASS", "majorFidelityDeviationCount": 0,
            "visibleAssetSeamCount": 0, "textFrameIntersections": 0,
            "unresolvedTextFrameCount": 0, "unresolvedGroupTransformCount": 0,
            "autoFidelityBlocked": False, "autoIterationCount": 0,
            "textRecovery": {"unresolvedItems": [], "needsHumanReview": False}}
        return report, verification

    def run_case(self, mutate=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report, verification = self.make_fixture(root)
            if mutate:
                mutate(root, report, verification)
            (root / "verification.json").write_text(json.dumps(verification), encoding="utf-8")
            (root / "report.json").write_text(json.dumps(report), encoding="utf-8")
            proc = subprocess.run([sys.executable, str(SCRIPT), str(root / "report.json")],
                                  capture_output=True, text=True)
            self.assertNotIn("Traceback", proc.stderr)
            return proc.returncode, json.loads(proc.stdout)

    def test_balanced_accepts_actual_render_review_without_unused_probes(self):
        code, data = self.run_case()
        self.assertEqual((code, data["status"]), (0, "PASS"))

    def test_stale_pptx_is_invalid(self):
        code, data = self.run_case(lambda p,r,v: (p / "deck.pptx").write_bytes(b"changed"))
        self.assertEqual(code, 2)
        self.assertIn("current PPTX", " ".join(data["errors"]))

    def test_stale_render_is_invalid(self):
        code, data = self.run_case(lambda p,r,v: (p / "slide-01.png").write_bytes(b"changed"))
        self.assertEqual(code, 2)
        self.assertIn("stale", " ".join(data["errors"]))

    def test_missing_page_review_is_invalid(self):
        code, data = self.run_case(lambda p,r,v: r.update(slideCount=2))
        self.assertEqual(code, 2)

    def test_unresolved_text_cannot_pass_fast_path(self):
        code, data = self.run_case(lambda p,r,v: r["textRecovery"]["unresolvedItems"].append("uncertain number"))
        self.assertEqual((code, data["status"]), (1, "FAIL"))

    def test_trigger_without_computed_evidence_is_invalid(self):
        def change(p, r, v):
            v["pages"][0]["triggeredChecks"] = [{"kind": "typography", "reason": "line wrap changed"}]
        code, data = self.run_case(change)
        self.assertEqual(code, 2)

    def test_triggered_failed_calibration_cannot_pass(self):
        def change(p, r, v):
            (p / "probe.json").write_text(json.dumps({"generatedBy": "score_typography_candidates.py", "status": "FAIL"}))
            v["pages"][0]["triggeredChecks"] = [{"kind": "typography", "reason": "line wrap changed", "evidenceFile": "probe.json"}]
        code, data = self.run_case(change)
        self.assertEqual((code, data["status"]), (1, "FAIL"))

    def test_strict_cannot_use_targeted_shortcut(self):
        code, data = self.run_case(lambda p,r,v: r.update(executionProfile="strict", calibrationPolicy="full"))
        self.assertEqual(code, 2)
        self.assertIn("typographyCalibrationFiles", " ".join(data["errors"]))

    def test_budget_is_not_permission_to_claim_pass(self):
        code, data = self.run_case(lambda p,r,v: r.update(executionProfile="fast", autoIterationCount=2))
        self.assertEqual((code, data["status"]), (1, "FAIL"))

    def test_pairing_mismatch_is_invalid(self):
        def change(p, r, v):
            (p / "pairing.json").write_text(json.dumps({"renderDirectory": ".", "pairings": [{"page": 1, "render": "different.png"}]}))
        code, data = self.run_case(change)
        self.assertEqual(code, 2)

    def test_unknown_profile_fails_closed(self):
        code, data = self.run_case(lambda p,r,v: r.update(executionProfile="typo"))
        self.assertEqual(code, 2)
