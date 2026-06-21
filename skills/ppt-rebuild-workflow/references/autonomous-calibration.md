# Autonomous Calibration

Use this profile for Mode B/C when the user wants an AI-only reconstruction workflow and does not want to approve per-slide anchors. It does not change the final editable boundary; it changes how the agent reaches it.

## Principle

Use the reference image as a temporary calibration surface, never as a final-page shortcut. Inserting it into a temporary PPT page or an overlay render locks the same pixels to the target canvas; it does not improve visual recognition by itself. Accuracy comes from the loop:

`measure -> coordinate lock -> build -> render -> compare -> revise`

## Required artifacts

Save these per page before a Level 2/3 pass can succeed:

- `reference-measurements.json` with `coordinateTransform` and `autoAnchors`.
- Measurement annotation with the automatically selected anchors visible.
- Temporary calibration overlay render or calibration PPT page. It may contain the complete reference image; it must not be part of the final editable deck.
- `typography-calibration.json` with candidate renders and the selected result.
- Reference/render comparison and a region-aware fidelity report.

## Automatic coordinate lock

1. Map source pixels to the final canvas and record scale, offset, crop, and fit mode. Do not estimate coordinates separately in image pixels and PPT units.
2. Run `extract_reference_measurements.py`; use its `autoAnchors` as a compact starting set. Keep the canvas frame plus 6-12 high-value regions or lines, not dozens of manual points.
3. Create a temporary overlay that draws those anchors on the source reference at the final canvas size.
4. Inspect the overlay and correct the transform or anchor selection automatically. A coordinate gate passes only when the overlay follows the intended large regions. Record the maximum anchor offset and marked exceptions.
5. Generate all final object coordinates from the locked transform. Do not hand-tune one unit system while measuring in another.

Use a default tolerance of `max(6 px, 0.5% of canvas dimension)` for a macro anchor edge. Tighter thresholds are appropriate for straight borders and panels; use a wider documented tolerance for shadows, glow, and feathered image boundaries.

## Automatic shape policy

Classify every visible object into one of these execution paths:

- `native-shape`: cards, panels, labels, borders, rules, dividers, simple gradients, and regular icons.
- `independent-image`: content photos and replaceable screenshots.
- `baked-asset`: texture, brush strokes, complex wave paths, glow, fog, irregular masking, and photo-edge integration.
- `mode-b-fallback`: a visually complex region that cannot be stably separated but may be baked while text and structure remain editable.

Never turn an uncertain contour into an arbitrary freeform or many anonymous rectangles. If confidence is below `0.75`, choose a safe automatic fallback. Request human intervention only when both conditions hold: the object must remain editable **and** no stable native representation or user-approved baked fallback exists.

## Render-probe typography

Use a render probe for each main text style: title, subtitle, label/tag, body, page number, and any style whose wrap affects layout.

1. Start from the reference text block bbox, glyph bbox, line count, line gaps, and internal padding.
2. When no font is supplied, create a `fontCandidateSet` from available fonts; do not block waiting for a font answer. Record the selected fallback and confidence.
3. Render 2-4 candidates that vary font family, size, weight, line spacing, text-box dimensions, padding, and vertical alignment.
4. Compare final render output, not only requested point size. Record the rendering backend and units used by the construction runtime.
5. Select the candidate with the closest line count, wrapping, baseline, glyph height, and text-block height. Disable auto-shrink as a substitute for calibration.

For high-confidence readable text, require exact line count, no clipping, and a documented glyph/text-block difference no larger than `max(6 px, 1% of the relevant dimension)`. For AI pseudo-text or unavailable fonts, calibrate baseline, height, spacing, and visual weight; record the textual limitation instead of pretending the font match is exact.

## Automatic iteration and fallback

Run the full build/render/compare loop up to three times. On each failed pass, update only the affected transform, layout, shape decision, or typography candidate and re-render all affected pages.

After the third failed pass, do not claim Level 2/3 success. Apply the least-destructive automatic fallback:

- Move an unresolved complex visual from native-shape to `baked-asset` or Mode B.
- Preserve text, panels, labels, borders, and other promised editable structures.
- Record `autoFidelityBlocked`, the failed metrics, and the fallback in QA.

## Autonomy boundary

`needsHumanReview` is not a routine anchor-approval step in this profile. Use it only for:

- business-critical text with multiple plausible source readings;
- a user requirement that a visually ambiguous complex object must remain individually editable;
- a reference image whose source crop, page order, or intended layout is genuinely unknown.

In all other cases, select and document an automatic fallback rather than requesting dozens of point confirmations.

## Required QA fields

The final QA report must include `autonomyProfile`, `coordinateCalibration`, `renderBackend`, `fontCandidateSet`, `typographyMetricsByPage`, `autoIterationCount`, `autoFallbacks`, and `autoFidelityBlocked`. A Level 2/3 pass requires `coordinateCalibration.status = PASS`, no unresolved required-editability conflicts, and no reference image embedded in the final deck.
