from __future__ import annotations
import json
import re
import unittest
from pathlib import Path
from scripts.resolve_rebuild_route import resolve_route

ROOT = Path(__file__).resolve().parents[1]


class RouteBehaviorTests(unittest.TestCase):
    def test_realistic_normalized_intents(self):
        # These are normalized user requests, not keyword matching fixtures.
        cases = [
            ("image to PPT", {}, ("Mode B", "Mode B", "balanced")),
            ("editable ASAP", {"executionProfile": "fast"}, ("Mode B", "Mode B", "fast")),
            ("independent person and background", {"deliverable": "layered"}, ("Mode C", "Mode C", "balanced")),
            ("layered ASAP", {"deliverable": "layered", "executionProfile": "fast"}, ("Mode C", "Mode C", "fast")),
            ("strict editable", {"executionProfile": "strict"}, ("Mode B", "Mode B", "strict")),
            ("only wrap images", {"deliverable": "preview"}, ("Mode A", "Mode A", "balanced")),
            ("fix typos", {"redesignRequested": False}, ("Mode B", "Mode B", "balanced")),
            ("improve recognition", {"redesignRequested": False, "intentEvidence": ["Improve OCR accuracy"]}, ("Mode B", "Mode B", "balanced")),
            ("edit current background", {"operation": "incremental", "sourcePptx": "current.pptx"}, ("Mode E", "Mode B", "balanced")),
            ("edit current page with layering", {"operation": "incremental", "sourcePptx": "current.pptx", "deliverable": "layered"}, ("Mode E", "Mode C", "balanced")),
            ("existing deck entirely redesigned", {"sourcePptx": "old.pptx", "redesignRequested": True}, ("Mode D", "Mode B", "balanced")),
            ("new design and layered deck", {"redesignRequested": True, "deliverable": "layered"}, ("Mode D", "Mode C", "balanced")),
            ("local redesign of current deck", {"sourcePptx": "current.pptx", "operation": "incremental", "redesignRequested": True}, ("Mode E", "Mode B", "balanced")),
        ]
        for label, intent, expected in cases:
            with self.subTest(label=label):
                actual = resolve_route(intent)
                self.assertEqual((actual["taskMode"], actual["targetMode"], actual["executionProfile"]), expected)
                self.assertFalse(actual["requiresInput"])

    def test_incremental_edit_retains_layered_acceptance(self):
        result = resolve_route({"operation": "incremental", "sourcePptx": "current.pptx", "deliverable": "layered"})
        self.assertEqual(result["qaLevel"], "Level 4")
        self.assertEqual(result["changedRegionQaLevel"], "Level 3")

    def test_autonomous_design_does_not_force_user_selection(self):
        result = resolve_route({"redesignRequested": True})
        self.assertEqual(result["stages"], ["design", "build", "verify"])
        self.assertFalse(result["waitForDesignChoice"])
        self.assertTrue(resolve_route({"redesignRequested": True, "userSelectsDesign": True})["waitForDesignChoice"])

    def test_reference_only_stops_before_build(self):
        result = resolve_route({"redesignRequested": True, "referenceOnly": True})
        self.assertEqual(result["stages"], ["design"])
        self.assertIsNone(result["targetMode"])
        self.assertIsNone(result["qaLevel"])

    def test_missing_incremental_source_does_not_silently_rebuild(self):
        result = resolve_route({"operation": "incremental"})
        self.assertEqual(result["taskMode"], "Mode E")
        self.assertEqual(result["missingInputs"], ["sourcePptx"])
        self.assertTrue(result["requiresInput"])

    def test_invalid_and_contradictory_intent_fails_explicitly(self):
        for data in ({"operation": "unknown"}, {"executionProfile": "cheap"},
                     {"redesignRequested": "false"}, {"referenceOnly": True},
                     {"operation": "incremental", "redesignRequested": True, "referenceOnly": True}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                resolve_route(data)

    def test_task_template_routes_to_balanced_editable(self):
        data = json.loads((ROOT / "assets/templates/task-input-template.json").read_text(encoding="utf-8"))
        result = resolve_route(data)
        self.assertEqual(result["taskMode"], "Mode B")
        self.assertEqual(result["calibrationPolicy"], "targeted")
        self.assertEqual(result["maxRepairIterations"], 2)

    def test_markdown_local_references_exist(self):
        for path in ROOT.rglob("*.md"):
            for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                target = target.split("#")[0]
                if not target or "://" in target:
                    continue
                self.assertTrue((path.parent / target).exists(), (path.name, target))

    def test_json_templates_are_parseable_and_canonical(self):
        for path in (ROOT / "assets/templates").glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            expected = "3.0" if path.name in {
                "layout-spec-template.json", "layout-spec-shared-template-example.json"
            } else "2.0"
            self.assertEqual(data["schemaVersion"], expected)
            for legacy in ("unexpectedTextOverlapCount", "flaggedPages", "autoIteration"):
                self.assertNotIn(legacy, data)
