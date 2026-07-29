# Intake and Routing

Use this reference when the request is broad, references have mixed purposes, or the correct output mode is uncertain.

## Minimum Brief

Infer what is obvious from supplied files and context. Ask only when a missing answer would materially change the result.

Capture:

- business category, offer, and campaign moment
- target audience and desired reaction
- pitch claim the visual must prove
- output use: slide, standalone image, ad, UI sample, social sample, environment render, product mockup, or edit
- aspect ratio or destination frame
- required content and immutable copy
- reference files and the role of each
- brand assets, palette, typography, and visual boundaries
- realism level, budget level, scale, camera character, and production plausibility
- prohibited content, legal/IP boundaries, and privacy constraints

## Routing Matrix

| User intent | Output mode | Default text policy | Primary success test |
|---|---|---|---|
| “Generate a complete proposal page” | Full-slide image | Essential copy only | The slide communicates one clear idea in three seconds |
| “Create an image for this slide” | Deck visual asset | Text none | The asset explains the claim and crops cleanly |
| “Show how the campaign happens offline” | Activation scene | Incidental text minimized | The action, scale, and environment look executable |
| “Show this packaging, merchandise, or installation” | Product/prop mockup | Only specified object text | Structure and material identity remain correct |
| “Show the app/search/check-in/content flow” | App/UI/social sample | Only specified states and labels | User action and outcome are immediately legible |
| “Give every point a visual” | Multi-panel composition | Short labels only | Every panel has a distinct job and is independently usable |
| “Keep this image and change X” | Controlled edit | Preserve existing copy unless specified | The delta is correct and accepted areas do not regress |

## Reference-Role Contract

For every reference, record:

| Role | Extract | Ignore |
|---|---|---|
| Content source | claims, actions, copy, required objects | weak layout or styling unless requested |
| Layout reference | spatial rhythm, proportions, hierarchy | names, copy, products, brand colors |
| Style reference | medium, camera, texture, lighting, mood | composition and content unless requested |
| Brand reference | palette, typography character, shapes, logo rules | unrelated campaign content |
| Object/character structure | silhouette, part relationships, decoration zones | scene and background |
| Scene/camera reference | location, viewpoint, framing, scale | unwanted objects and incidental text |
| Fixed asset | the supplied pixels or object unchanged | reinterpretation or redrawing |

Assign one primary role per reference. Add a secondary role only when necessary and non-conflicting.

Also record one handling mode for every supplied image:

- `load`: the image pixels must reach the image model
- `inspect-only`: inspect locally and translate the relevant visual traits into words
- `extract-only`: extract copy or requirements without using the image as visual context

## Brand Abstraction

Convert brand-specific material into runtime variables:

- `brand_character`: restrained, playful, technical, luxurious, mass-market, youthful, institutional, etc.
- `brand_palette`: supplied colors and permitted accents
- `brand_shapes`: geometric, rounded, editorial, organic, modular, expressive, etc.
- `brand_voice`: direct, witty, authoritative, warm, provocative, premium, etc.
- `category_codes`: visual conventions appropriate to the current industry
- `campaign_world`: the temporary visual world created for this pitch

Do not turn one client's choices into permanent defaults.

## Defaults When the Brief Is Silent

- Prioritize the communication goal over decorative novelty.
- Use one primary focal point and no more than two supporting levels.
- Keep incidental text out of generated scenes.
- Use realistic scale, believable materials, and production-aware detail for business pitches.
- Preserve whitespace or crop-safe edges when the image will sit inside a slide.
- Prefer a small number of clear objects over dense crowds and uncontrolled signage.
