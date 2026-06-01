---
name: game-ui-asset-pipeline
description: Generate, clean, slice, validate, and import AI-created game UI assets for Godot projects. Use when Codex needs to create or refine icon sheets, dish/ingredient icons, HUD glyphs, anime-style UI skins, nine-slice panels, button states, chips, decorations, or other raster UI assets while preserving a consistent lightweight 2D game art style and avoiding bad cutouts, dirty alpha, broken slicing, or Godot layout regressions.
---

# Game UI Asset Pipeline

Use this skill to turn AI-generated bitmap art into production-ready Godot UI assets. The core rule is: **AI creates visual style, scripts own geometry, Godot owns text, layout, and interaction.**

## Workflow

1. Classify the asset before generating:
   - Single-subject icons: dishes, ingredients, rewards, events.
   - Lightweight HUD glyphs: persistent top/side UI symbols.
   - Special UI skins: selected nav, large CTA, decorative buttons.
   - Nine-slice panels/cards: main panels, cards, summary boxes.
   - Plain variable-size controls: small buttons, chips, dropdowns.
2. Read only the reference needed:
   - Prompt/style rules: `references/visual-style.md`.
   - Godot integration and validation: `references/godot-integration.md`.
3. Generate a fixed grid or fixed-size component family. Do not ask the model to crop, name, or align final assets.
4. Use a removable chroma-key background for transparent assets unless true native alpha is explicitly available. Prefer `#ff00ff` for mostly blue UI glyphs and `#00ff00` for food/object icons.
5. Remove the key, slice by deterministic coordinates, normalize to final canvas sizes, and validate alpha.
6. Put only final runtime assets in the project under a stable `res://` path. Keep source sheets and intermediate cells outside the Godot project when possible.
7. Import with Godot, wire resources through data, Theme, `StyleBoxTexture`, `TextureRect`, or dedicated components.
8. Run a relevant runner and capture a screenshot. If the screenshot differs from the generated source, debug import/layout before regenerating.

## Asset Decisions

Use AI bitmap assets when the component needs special shape, texture, or anime UI polish that code cannot reproduce cheaply: selected side nav skins, large CTA skins, star icons, decorative strips, title sparkles, and fixed-size HUD glyphs.

Use code/Theme instead when the control is small and variable-sized: ordinary buttons, price steppers, chips, dropdowns, counters, and labels. These usually become dirty when stretched from bitmaps.

Never bake Chinese text, numbers, prices, labels, dynamic icons, or button copy into UI skins. Let Godot render text and state.

## Sheet Processing

For fixed-grid icon sheets, use the bundled script:

```bash
python skills/game-ui-asset-pipeline/scripts/slice_sprite_sheet.py \
  --input /abs/path/sheet_cutout.png \
  --out /abs/path/final_icons \
  --cols 6 --rows 3 \
  --names top_day,top_money,top_reputation,top_income,top_portal,action_save,nav_overview,nav_menu,nav_employees,nav_decoration,nav_inventory,action_pause,nav_reports,nav_finance,nav_settings,nav_omen,nav_research,action_speed \
  --size 64 --max-subject 54 --alpha-threshold 12
```

Use the same script for dish/ingredient sheets with `--size 256 --max-subject 220`.

## Godot Rules

- Refer to final files with `res://...`; never reference `$HOME/.codex/generated_images`.
- For button icons in compact HUD buttons, prefer child `TextureRect` overlays over `Button.icon` if the original texture would change the button minimum size.
- For special button skins, use a fixed size or a documented size family. Do not reuse one bitmap skin across unrelated button sizes.
- For nine-slice assets, verify margins in Godot screenshots before accepting. Dirty corners, broken edges, or repeated center artifacts usually mean the margin or source art is wrong.
- Keep decorative `TextureRect` nodes `MOUSE_FILTER_IGNORE`.

## Validation

At minimum, run:

```bash
git diff --check
sh scripts/qa/run_godot_safe.sh quit_probe --quit
```

For UI work, also run the closest UI runner and capture a screenshot. Inspect the screenshot for:

- no layout shift from icon texture sizes
- clean transparent edges
- no chroma-key fringe
- no baked text in skins
- no clipped labels
- no button/icon overlap
- no nine-slice border tearing

If validation fails, identify whether the issue is source generation, alpha removal, slicing, import settings, or layout. Fix that stage directly instead of adding visual hacks.
