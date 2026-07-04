from __future__ import annotations

import sys
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from _pptx_common import NS, group_transform, shape_name, slide_sort_key  # noqa: E402

NS_DECL = f'xmlns:p="{NS["p"]}" xmlns:a="{NS["a"]}"'


def group(xfrm_inner: str | None, rot: str = "0") -> ET.Element:
    if xfrm_inner is None:
        body = "<p:grpSpPr/>"
    else:
        body = f'<p:grpSpPr><a:xfrm rot="{rot}">{xfrm_inner}</a:xfrm></p:grpSpPr>'
    return ET.fromstring(f"<p:grpSp {NS_DECL}>{body}</p:grpSp>")


FULL = (
    '<a:off x="0" y="0"/><a:ext cx="200" cy="100"/>'
    '<a:chOff x="0" y="0"/><a:chExt cx="100" cy="50"/>'
)


class GroupTransformTests(unittest.TestCase):
    def test_normal_nested_group_composes_scale_and_offset(self) -> None:
        transform, risk = group_transform(group(FULL), (1.0, 1.0, 0.0, 0.0))
        self.assertIsNone(risk)
        self.assertEqual(transform, (2.0, 2.0, 0.0, 0.0))

    def test_parent_transform_is_composed(self) -> None:
        transform, risk = group_transform(group(FULL), (2.0, 2.0, 10.0, 20.0))
        self.assertIsNone(risk)
        self.assertEqual(transform, (4.0, 4.0, 10.0, 20.0))

    def test_rotated_group_is_unresolved(self) -> None:
        transform, risk = group_transform(group(FULL, rot="60000"), (1.0, 1.0, 0.0, 0.0))
        self.assertIsNone(transform)
        self.assertEqual(risk, "rotated group transform is not resolved")

    def test_missing_child_extent_is_incomplete(self) -> None:
        partial = '<a:off x="0" y="0"/><a:ext cx="200" cy="100"/><a:chOff x="0" y="0"/>'
        transform, risk = group_transform(group(partial), (1.0, 1.0, 0.0, 0.0))
        self.assertIsNone(transform)
        self.assertEqual(risk, "group transform is incomplete")

    def test_zero_child_extent_is_flagged(self) -> None:
        zero = (
            '<a:off x="0" y="0"/><a:ext cx="200" cy="100"/>'
            '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="50"/>'
        )
        transform, risk = group_transform(group(zero), (1.0, 1.0, 0.0, 0.0))
        self.assertIsNone(transform)
        self.assertEqual(risk, "group child extent is zero")

    def test_no_transform_element(self) -> None:
        transform, risk = group_transform(group(None), (1.0, 1.0, 0.0, 0.0))
        self.assertIsNone(transform)
        self.assertEqual(risk, "group has no transform")

    def test_shape_name_infers_container_by_kind_and_tag(self) -> None:
        sp = ET.fromstring(
            f'<p:sp {NS_DECL}><p:nvSpPr><p:cNvPr name="body-1"/></p:nvSpPr></p:sp>'
        )
        cxn = ET.fromstring(
            f'<p:cxnSp {NS_DECL}><p:nvCxnSpPr><p:cNvPr name="line-1"/></p:nvCxnSpPr></p:cxnSp>'
        )
        pic = ET.fromstring(
            f'<p:pic {NS_DECL}><p:nvPicPr><p:cNvPr name="img-1"/></p:nvPicPr></p:pic>'
        )
        self.assertEqual(shape_name(sp), "body-1")
        self.assertEqual(shape_name(cxn), "line-1")  # inferred cxnSp container
        self.assertEqual(shape_name(sp, "shape"), "body-1")
        self.assertEqual(shape_name(pic, "picture"), "img-1")

    def test_slide_sort_key(self) -> None:
        self.assertEqual(slide_sort_key("ppt/slides/slide12.xml"), 12)
        self.assertEqual(slide_sort_key("no-number.xml"), 0)


if __name__ == "__main__":
    unittest.main()
