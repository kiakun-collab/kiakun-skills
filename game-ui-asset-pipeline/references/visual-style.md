# Visual Style Reference

Use this reference when prompting AI image generation for lightweight anime management-game UI assets.

## Baseline

- Bright, airy 2D Japanese anime management UI.
- White glass panels, sky blue accents, soft cyan borders, gentle sunlight.
- Light, clean, readable silhouettes.
- Blue/cyan line work with white fill and small warm yellow accents.
- Subtle inner highlight is allowed; heavy shading is not.

Avoid:

- 3D or skeuomorphic item rendering for persistent HUD icons.
- Thick sticker outlines, toy gloss, metallic highlights, deep bevels.
- Dark RPG UI, parchment, heavy wood, brown/orange tavern palettes.
- Baked text, numbers, labels, watermarks.

## Lightweight HUD Glyph Prompt

```text
Create a single clean icon sprite sheet for a Japanese anime-style restaurant management game HUD.

Canvas: <cols> columns x <rows> rows, equal cells, generous padding, perfectly flat solid <key_color> chroma-key background for later removal.

Style target: very lightweight 2D anime UI glyphs, not item icons. Fresh, airy, clean, translucent-feeling blue line icons with small flat fills. Use thin rounded cyan-blue strokes, simple shapes, white negative space, and tiny pale yellow accents only where meaningful. Almost no shading: no 3D, no bevel, no sticker border, no thick white outline, no realistic object volume, no toy-like gloss, no metallic highlight, no perspective. These should feel like persistent HUD symbols in a bright sky-blue Japanese UI, calm and readable.

Icons, left to right, top to bottom:
<numbered icon list>

Requirements:
- No text, no labels, no numbers, no watermark.
- Each icon centered in its cell, matching visual size, with simple readable silhouette.
- Use mostly blue/cyan strokes and flat pale fills, not rendered object materials.
- Keep every icon fully separated from the <key_color> background with crisp antialiased edges.
- Do not use <key_color> anywhere in the icons.
- Background must be perfectly uniform <key_color> with no shadows, gradients, texture, reflections, or lighting variation.
```

## Dish/Icon Prompt

```text
Create a single <grid> fixed-grid sprite sheet containing exactly <count> separate game UI food icons:
<cell list>.

Style: polished hand-painted 2D Japanese fantasy restaurant game icon art, appetizing, bright, readable at small size, consistent perspective and scale.
Composition: exact fixed grid on one square canvas; each cell contains exactly one centered subject with generous padding; no object crosses into another cell; no grid lines.
Background: perfectly flat solid <key_color> chroma-key background in every cell.
Lighting: soft icon lighting; no cast shadows or contact shadows on the background.
Constraints: no text, no labels, no watermark, no decorative frame, no aura cloud, no smoke outside the object silhouette, no loose glow around edges, no key color in subjects.
```

## UI Skin Prompt

Use for special fixed-size skins only.

```text
Create a transparent PNG UI skin for a bright Japanese anime restaurant management game.
Component: <component role and state>.
Target size: <width>x<height>.
Style: airy translucent white/sky-blue glass, soft cyan edge, very subtle highlight, light decorative sparkle if appropriate.
Keep center clean for Godot-rendered text and icons.
No text, no numbers, no labels, no watermark.
No heavy 3D, no thick toy gloss, no dark shadows.
If chroma key is needed, use perfectly flat <key_color> background and do not use that color in the subject.
```
