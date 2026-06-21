from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


class ModeSelectionContractTests(unittest.TestCase):
    def test_mode_e_has_highest_routing_priority(self) -> None:
        text = (SKILL_ROOT / "references" / "mode-selection.md").read_text(
            encoding="utf-8"
        )
        decision_section = text.split("## 模式边界", 1)[0]
        positions = {
            mode: decision_section.index(f"Mode {mode}")
            for mode in ("A", "B", "C", "D", "E")
        }
        self.assertLess(positions["E"], positions["D"])
        self.assertLess(positions["D"], positions["A"])
        self.assertLess(positions["A"], positions["B"])
        self.assertLess(positions["B"], positions["C"])
        self.assertRegex(
            decision_section,
            r"用户.*修改.*局部.*Mode E",
        )

    def test_frontmatter_description_contains_triggers_not_workflow_summary(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        description = re.search(r"^description:\s*(.+)$", skill, re.MULTILINE).group(1)
        self.assertEqual(
            description,
            "Use when rebuilding slide screenshots, image-only PPTX files, "
            "AI-generated reference slides, or user-edited PowerPoint drafts "
            "into editable PPTX deliverables.",
        )

    def test_level_2_required_evidence_is_not_listed_as_optional(self) -> None:
        text = (SKILL_ROOT / "references" / "qa-standards.md").read_text(
            encoding="utf-8"
        )
        optional = text.split("## Level 2 可选增强", 1)[1].split("## Level 3", 1)[0]
        self.assertNotIn("audit_pptx_structure.py", optional)
        self.assertNotIn("audit_pptx_text_frames.py", optional)
        self.assertNotIn("make_reference_render_comparison.py", optional)

    def test_level_3_template_requires_sourced_evidence(self) -> None:
        report = json.loads(
            (SKILL_ROOT / "assets" / "templates" / "qa-report-template.json").read_text(
                encoding="utf-8"
            )
        )
        gates = report["level3Gates"]
        for name in (
            "wholeReferenceImageEmbedded",
            "combinedBackgroundPersonPictureCount",
            "contentPicturesAreIndependentObjects",
            "unexpectedTextOverlapCount",
            "forbiddenOverlayShapesDetected",
        ):
            self.assertEqual(
                set(gates[name]),
                {"automatedEvidence", "manualEvidence", "status"},
            )

    def test_level_3_contract_does_not_require_fifty_percent_overlay(self) -> None:
        files = (
            SKILL_ROOT / "references" / "qa-standards.md",
            SKILL_ROOT / "references" / "full-layered-workflow.md",
            SKILL_ROOT / "assets" / "templates" / "level-3-delivery-checklist.md",
            SKILL_ROOT / "assets" / "templates" / "qa-report-template.json",
        )
        combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
        self.assertNotIn("50% 叠加图", combined)
        self.assertNotIn("fiftyPercentOverlay", combined)

    def test_visual_qa_does_not_require_reference_image_hash_or_generic_graphic_frame_collisions(
        self,
    ) -> None:
        files = (
            SKILL_ROOT / "references" / "qa-standards.md",
            SKILL_ROOT / "references" / "script-output-contracts.md",
            SKILL_ROOT / "references" / "visual-overlap-qa.md",
            SKILL_ROOT / "assets" / "templates" / "level-2-delivery-checklist.md",
            SKILL_ROOT / "assets" / "templates" / "level-3-delivery-checklist.md",
        )
        combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
        self.assertNotIn("人工/哈希证据", combined)
        self.assertNotIn("像素哈希或感知哈希比对", combined)
        self.assertIn("不纳入通用碰撞门禁", combined)
        self.assertIn("文字可读性", combined)

    def test_visual_qa_is_full_slide_first_and_does_not_use_crops_as_evidence(
        self,
    ) -> None:
        files = (
            SKILL_ROOT / "references" / "qa-standards.md",
            SKILL_ROOT / "references" / "visual-overlap-qa.md",
            SKILL_ROOT / "references" / "full-layered-workflow.md",
            SKILL_ROOT / "references" / "subagent-prompts.md",
        )
        combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
        self.assertIn("整页优先", combined)
        self.assertIn("不得把多轮裁剪作为默认审计流程", combined)
        self.assertNotIn("区域视图", combined)

    def test_visual_qa_requires_both_text_readability_and_reference_fidelity(
        self,
    ) -> None:
        files = (
            SKILL_ROOT / "SKILL.md",
            SKILL_ROOT / "references" / "qa-standards.md",
            SKILL_ROOT / "references" / "visual-overlap-qa.md",
            SKILL_ROOT / "references" / "visual-fidelity-qa.md",
            SKILL_ROOT / "references" / "script-output-contracts.md",
            SKILL_ROOT / "references" / "semi-editable-workflow.md",
            SKILL_ROOT / "references" / "full-layered-workflow.md",
            SKILL_ROOT / "references" / "subagent-prompts.md",
            SKILL_ROOT / "assets" / "templates" / "level-2-delivery-checklist.md",
            SKILL_ROOT / "assets" / "templates" / "level-3-delivery-checklist.md",
        )
        combined = "\n".join(path.read_text(encoding="utf-8") for path in files)
        report = json.loads(
            (SKILL_ROOT / "assets" / "templates" / "qa-report-template.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("双门禁", combined)
        self.assertIn("版式、构图、层级、色彩", combined)
        self.assertIn("不要求像素级完全一致", combined)
        self.assertIn("majorFidelityDeviationCount = 0", combined)
        self.assertIn("仍可能构成视觉还原度偏差", combined)
        self.assertIn("visualFidelityStatus", report)
        self.assertIn("majorFidelityDeviationCount", report)
        self.assertIn("visualFidelityByPage", report)

    def test_corrupted_ai_image_text_uses_sourced_semantic_recovery_not_cropping(
        self,
    ) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        recovery = (SKILL_ROOT / "references" / "text-recovery.md").read_text(
            encoding="utf-8"
        )
        prompts = (SKILL_ROOT / "references" / "subagent-prompts.md").read_text(
            encoding="utf-8"
        )
        report = json.loads(
            (SKILL_ROOT / "assets" / "templates" / "qa-report-template.json").read_text(
                encoding="utf-8"
            )
        )
        combined = "\n".join((skill, recovery, prompts))
        self.assertIn("text-recovery.md", skill)
        self.assertIn("语义重建优先", combined)
        self.assertIn("不得通过裁剪或放大恢复", combined)
        self.assertIn("原 PPTX、用户文案或可信业务资料", recovery)
        self.assertIn("候选文字", combined)
        self.assertIn("不得写成确定文案", combined)
        self.assertEqual(
            set(report["textRecovery"]),
            {
                "sourceFiles",
                "resolvedItems",
                "unresolvedItems",
                "needsHumanReview",
            },
        )

    def test_runtime_contract_defers_build_and_render_to_presentations_skill(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("runtime-integration.md", skill)
        runtime = (SKILL_ROOT / "references" / "runtime-integration.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("artifact-tool", runtime)
        self.assertIn("只读", runtime)
        self.assertIn("python-pptx", runtime)
        self.assertIn("LibreOffice", runtime)

    def test_reference_rebuild_does_not_require_beating_the_reference(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        runtime = (SKILL_ROOT / "references" / "runtime-integration.md").read_text(
            encoding="utf-8"
        )
        fidelity = (SKILL_ROOT / "references" / "visual-fidelity-qa.md").read_text(
            encoding="utf-8"
        )
        prompts = (SKILL_ROOT / "references" / "subagent-prompts.md").read_text(
            encoding="utf-8"
        )
        combined = "\n".join((skill, runtime, fidelity, prompts))
        self.assertIn("不得要求超越参考图", combined)
        self.assertIn("参考图是忠实重构目标", runtime)
        self.assertIn("Mode B/C", runtime)
        self.assertIn("reference delta = n/a", runtime)
        self.assertIn("不得奖励未经用户授权的重新设计", prompts)

    def test_default_coordinate_system_is_not_claimed_as_only_supported_ratio(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("默认坐标系为 1280 x 720", skill)
        self.assertIn("非 16:9", skill)

    def test_measurement_precedes_layout_and_is_enforced_across_workflows(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        full = (SKILL_ROOT / "references" / "full-layered-workflow.md").read_text(
            encoding="utf-8"
        )
        checklist = (
            SKILL_ROOT / "assets" / "templates" / "level-2-delivery-checklist.md"
        ).read_text(encoding="utf-8")
        page_task = (
            SKILL_ROOT / "assets" / "templates" / "page-task-template.md"
        ).read_text(encoding="utf-8")

        self.assertLess(
            full.index("extract_reference_measurements.py"),
            full.index("建立 `layout-spec.json`"),
        )
        self.assertIn("`x/y/w/h` 已从参考图抽取", checklist)
        self.assertIn("测量 JSON、标注图", checklist)
        self.assertIn("先写 `layout-spec`", skill)
        self.assertIn("候选框当作最终形状清单", skill)
        self.assertIn("visual-extraction.shapes[]", skill)
        self.assertLess(
            page_task.index("测量参考图"),
            page_task.index("layout-spec"),
        )
        self.assertIn("保存测量 JSON 和标注图", page_task)

    def test_complex_visual_transitions_have_explicit_asset_and_qa_contracts(
        self,
    ) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        strategy_path = (
            SKILL_ROOT / "references" / "visual-transition-strategy.md"
        )
        self.assertTrue(
            strategy_path.exists(),
            "missing visual transition strategy reference",
        )
        strategy = strategy_path.read_text(encoding="utf-8")
        semi_editable = (
            SKILL_ROOT / "references" / "semi-editable-workflow.md"
        ).read_text(encoding="utf-8")
        fidelity = (
            SKILL_ROOT / "references" / "visual-fidelity-qa.md"
        ).read_text(encoding="utf-8")
        checklist = (
            SKILL_ROOT / "assets" / "templates" / "level-2-delivery-checklist.md"
        ).read_text(encoding="utf-8")
        layout = json.loads(
            (SKILL_ROOT / "assets" / "templates" / "layout-spec-template.json").read_text(
                encoding="utf-8"
            )
        )
        fidelity_template = json.loads(
            (
                SKILL_ROOT
                / "assets"
                / "templates"
                / "visual-fidelity-audit-template.json"
            ).read_text(encoding="utf-8")
        )
        report = json.loads(
            (SKILL_ROOT / "assets" / "templates" / "qa-report-template.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertIn("visual-transition-strategy.md", skill)
        self.assertIn("简单规则渐变", strategy)
        self.assertIn("纹理、光晕、雾气", strategy)
        self.assertIn("透明图片或无字底图", strategy)
        self.assertIn("素材裁切边界不得落在可见过渡区", strategy)
        self.assertIn("窄矩形渐变", strategy)
        self.assertIn("边缘融合", semi_editable)
        self.assertIn("明显矩形接缝", fidelity)
        self.assertIn("`major`", fidelity)
        self.assertIn("`visibleAssetSeamCount = 0`", checklist)

        transitions = layout["visualTransitions"]
        self.assertEqual(len(transitions), 1)
        self.assertEqual(
            set(transitions[0]),
            {
                "id",
                "bounds",
                "complexity",
                "strategy",
                "direction",
                "transitionWidthPx",
                "sourceAsset",
                "editableBoundary",
                "rationale",
            },
        )
        for document in (fidelity_template, report):
            self.assertIn("visibleAssetSeamCount", document)
            self.assertIn("transitionFlaggedPages", document)
            self.assertIn("visualTransitionByPage", document)


if __name__ == "__main__":
    unittest.main()
