# Godot Integration Reference

## Runtime Asset Placement

Put final runtime assets inside the project and reference them with `res://`.

Recommended structure:

```text
assets/generated/<feature>/<batch>/
assets/generated/ui/<style>/<component>/
```

Keep intermediate source sheets, raw generated images, cells, and cutouts outside the Godot project, such as under `$HOME/.codex/tmp/<project>_asset_pipeline/`.

## Import

Run a Godot import pass after copying files into the project:

```bash
sh scripts/qa/run_godot_safe.sh quit_probe --quit
```

Confirm `.import` files are created for final PNGs. Do not commit or reference intermediate sheet imports unless they are intentionally kept as QA previews.

## Icon Integration

For data icons, set the relevant `Texture2D` resource field.

For HUD glyphs in compact buttons, avoid `Button.icon` when the source texture is larger than the intended displayed icon. Godot may include the icon's source size in minimum-size calculation and stretch the HUD. Prefer:

- keep button text as normal text
- add a child `TextureRect`
- set fixed offsets/anchors
- set `MOUSE_FILTER_IGNORE`

## UI Skins

Use `StyleBoxTexture` only when the source was designed for nine-slice stretching and margins have been tested. Otherwise prefer fixed-size `TextureRect`, `TextureButton`, or a dedicated wrapper component.

Nine-slice checklist:

- Margins cover the entire corner radius, border, shadow, and highlight bend.
- Slice lines do not cross decorative marks.
- Center area is clean and tile/stretch safe.
- Test every target size and state.

If a small variable-width button looks dirty, stop using bitmap skin for that button class and return to Theme/`StyleBoxFlat`.

## Screenshot QA

Every UI asset batch should end with a screenshot. Check:

- source image and in-engine result match in style weight
- alpha edges are clean
- no green/magenta fringe
- layout did not shift
- text is not clipped or overlapped
- interactive states still work
- hidden or decorative nodes do not block input

If the generated source looks clean but the game screenshot looks dirty, investigate Godot import settings, scale mode, min-size behavior, and nine-slice margins before regenerating.
