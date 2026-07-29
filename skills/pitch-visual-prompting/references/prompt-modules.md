# Prompt Modules

Load only the modules needed for the selected output mode. Do not paste every module into every prompt.

## Contents

- Core Skeleton
- Full-Slide Module
- Deck-Asset Module
- Activation-Scene Module
- Product-or-Prop Module
- App-UI-Social Module
- Multi-Panel Module
- Controlled-Edit Module
- Negative-Constraint Builder

## Core Skeleton

```text
Use case: [pitch / advertising / product visualization / realistic activation / UI demonstration]
Asset type: [full-slide image / deck visual asset / scene / product mockup / UI sample / multi-panel image / controlled edit]

Primary request:
[Describe the single communication objective and what the viewer must understand.]

Reference roles:
- Reference 1: [role]. Preserve [specific attributes]. Ignore [specific attributes].
- Reference 2: [role]. Preserve [specific attributes]. Ignore [specific attributes].

Reference handling:
- Load into model: [references whose identity, geometry, composition, or fixed pixels must carry over]
- Inspect only: [references translated into style/material/palette/camera language]
- Extract only: [references used only for copy or factual requirements]

Brand and audience:
[Current brand character, category, audience, campaign world, and intended reaction.]

Scene and action:
[Location, subjects, action, exact moment, scale, and relationship between objects.]

Composition and hierarchy:
[Aspect ratio, focal point, camera distance, placement, whitespace, panel structure, crop behavior, and visual priority.]

Style and production character:
[Medium, realism, camera feel, material quality, lighting, palette, density, budget level, and production plausibility.]

Text:
[None / exact permitted copy / paraphrasable copy.]

Authorized visible-text inventory:
[List every string or field allowed to contain readable text. All unspecified text-bearing surfaces must remain blank, abstract, or unreadable.]

Constraints:
[Required invariants and legal, brand, IP, structural, or technical boundaries.]

Avoid:
[Likely failure modes specific to this request.]
```

## Full-Slide Module

Add:

```text
This is a complete presentation slide, not a poster or isolated scene.
Keep the title as the strongest element. Separate title, explanation, visual evidence, and supporting notes.
Use images to prove the idea; do not reduce the page to text cards or a generic flow diagram.
Keep the composition reproducible with ordinary presentation shapes unless the user requests a more expressive art direction.
```

State the exact copy hierarchy:

- exact title
- exact subtitle or hook
- required short labels
- supporting copy that may be summarized
- copy that must not appear

## Deck-Asset Module

Add:

```text
This image will be placed inside an editable pitch deck.
Generate only the visual asset. Text: none.
Keep clean crop-safe edges and negative space appropriate to the destination frame.
Do not add captions, labels, logos, watermarks, UI, or decorative typography.
```

Include the destination crop ratio, not only the final slide ratio.

## Activation-Scene Module

Specify:

- venue and time of day
- event footprint and production budget level
- visitor count and behavior
- staff, creator, or participant actions
- installation scale relative to people and architecture
- materials, temporary construction logic, safety, and access
- camera character: smartphone snapshot, event documentation, architectural visualization, editorial campaign photo, etc.

Use action-state precision: already completed, actively happening, or about to happen.

## Product-or-Prop Module

Separate invariants:

```text
Structure invariants: [silhouette, openings, handles, part positions, scale]
Decoration invariants: [character/art placement, motif zones, palette, printed regions]
Material invariants: [acrylic, paper, metal, textile, finish, transparency]
Use-context invariants: [how it is held, worn, displayed, opened, or photographed]
```

If the object contains an opening, transparent region, screen, frame, window, or functional surface, state what must remain visible through it and what must never cover it.

## App-UI-Social Module

Specify:

- platform category rather than copying a protected logo unless authorized
- user entry action
- input state
- system response
- completion state or reward
- exact labels, codes, prices, or search terms
- information that must not be auto-generated

Inventory metadata fields explicitly: author name, account name, timestamps, metrics, comments, tags, buttons, navigation labels, and decorative slogans. If a field is not required, instruct the model to omit it rather than invent it.

Ask for a credible product or content sample, not a concept wireframe, unless wireframes are explicitly requested.

## Multi-Panel Module

For every panel define:

```text
Panel N purpose:
Scene/action:
Camera/crop:
Distinctive evidence:
Forbidden overlap or repetition:
```

Require exact grid geometry, visible gutters or separators, consistent visual language, and self-contained crop-safe panels.

## Controlled-Edit Module

Use:

```text
Edit this exact target image.
Preserve unchanged: [accepted regions, objects, copy, colors, framing].
Change only: [specific delta].
Permitted secondary adjustments: [minimal reflow, crop extension, lighting match, etc.].
Do not change: [frozen elements].
Output should remain nearly identical outside the requested change.
```

If the model previously edited the wrong image, restate unique target identifiers and include only the target reference when possible.

## Negative-Constraint Builder

Select only relevant failures:

- unwanted text, pseudo-text, misspellings, logos, watermarks, QR codes
- generic icons, emojis, decorative UI, unsupported controls
- incorrect product structure, blocked openings, wrong transparency, altered fixed assets
- distorted hands, duplicated people, malformed faces, unstable architecture
- implausible scale, excessive crowding, luxury staging beyond budget, cheap toy-like materials
- neon, glow, magic effects, smoke, lens flare, cinematic darkness, or complex backgrounds
- recognizable protected characters or brand marks when not authorized
- poster-like composition when a presentation page is required
- pure text cards or generic diagrams when photographic evidence is required
