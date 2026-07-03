from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_rebuild_evidence.py"


class ValidateRebuildEvidenceTests(unittest.TestCase):
    def test_normalizes_legacy_fields_but_rejects_self_attested_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = {
                "outputPptx": "deck.pptx",
                "qaLevel": "Level 2",
                "renderBackend": "artifact-tool",
                "unexpectedTextOverlapCount": 0,
                "flaggedPages": [],
                "autoIteration": 0,
                "coordinateCalibration": {"status": "PASS", "artifacts": []},
            }
            source = root / "report.json"
            normalized = root / "normalized.json"
            source.write_text(json.dumps(report), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    str(source),
                    "--normalized-output",
                    str(normalized),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            data = json.loads(normalized.read_text(encoding="utf-8"))
            validation = json.loads(result.stdout)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(data["acceptanceRenderer"], "artifact-tool")
        self.assertEqual(data["visualOverlapCount"], 0)
        self.assertEqual(data["visionFlaggedPages"], [])
        self.assertEqual(data["autoIterationCount"], 0)
        self.assertTrue(validation["migrationWarnings"])
        self.assertTrue(any("computed artifacts" in error for error in validation["errors"]))


if __name__ == "__main__":
    unittest.main()
