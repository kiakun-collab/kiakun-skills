---
name: gpt-image-2-api
description: Generate and edit images through the aifast.site OpenAI-compatible GPT Image API with cost-aware routing between gpt-image-2 and gpt-image-2-vip. Use for text-to-image, single- or multi-reference editing, daily images, complex information-dense graphics, precision-sensitive output, and supported 1K/2K/4K specification tiers. Defaults to the lower-cost standard model and upgrades to VIP only when task complexity, requested output specification, quality control, or multiple references require it.
---

# GPT Image 2 API

Follow this workflow exactly. Do not inspect scripts to discover usage.

## 1. Choose The Operation

| User request | Command |
|---|---|
| Create an image from text | `node scripts/generate.js ...` |
| Edit using local reference files | `node scripts/edit.js --image ...` |
| Edit using public image URLs | `node scripts/edit.js --url ...` (downloads, then uploads multipart) |

API routes are fixed:

- Generate: `POST https://aifast.site/v1/images/generations`
- Edit: `POST https://aifast.site/v1/images/edits`

## 2. Choose The Model Profile

Use `--profile auto` unless the semantic task itself clearly requires VIP.

| Situation | Profile | Result |
|---|---|---|
| Daily illustration, avatar, simple product image, social post, concept image | `auto` or `standard` | `gpt-image-2`, default `1024x1024` |
| One reference image, ordinary background/style/object edit | `auto` or `standard` | `gpt-image-2`, default `1024x1024` |
| User explicitly requests a supported 2K or 4K tier | `auto` or `vip` plus a listed `--size` preset | `gpt-image-2-vip` |
| Information-dense infographic, architecture diagram, academic figure, UI board, poster with substantial text/layout | `vip` | `gpt-image-2-vip`, default `2048x2048` |
| Fine typography, small labels, precision-sensitive product detail, publication-ready output | `vip` | `gpt-image-2-vip`, default `2048x2048` |
| Two or more reference images | `auto` | Automatically selects `gpt-image-2-vip` |
| User explicitly asks for `quality=low/medium/high` | `auto` or `vip` | Automatically selects `gpt-image-2-vip` |

Never use VIP merely because it is available. VIP costs more.

## Important: Size Is A Preset, Not An Exact Resolution

`--size` selects a documented upstream output specification or aspect ratio. It does not ask the
model to render an arbitrary exact width and height.

- Use only values listed in [references/api-reference.md](./references/api-reference.md).
- Do not invent custom values such as `1600x900`, `1920x1080`, or `4096x4096`.
- Pixel-looking values such as `1024x1024` and `2560x1440` are gateway preset tokens. The gateway
  maps them to an upstream `aspectRatio` or output tier.
- The model or gateway controls the final pixel dimensions. Check `actualImages` in `--json` output
  instead of assuming that the returned file exactly matches the preset token.
- Use VIP preset tokens only to select a supported 2K/4K tier, not to request a custom resolution.

## 3. Run A Dry Plan

Before a paid request, run the final command once with `--dry-run`. It does not require an API key and does not create files.

```bash
node scripts/generate.js \
  --prompt "A cozy reading corner in warm daylight" \
  --dry-run
```

Check these fields:

- `endpoint`
- `selectedTier`
- `model`
- `size`
- `quality`
- `routeReasons`

If the plan selects VIP without a reason from the table above, change the arguments.

## 4. Execute

### Daily Text-To-Image

```bash
node scripts/generate.js \
  --profile auto \
  --prompt "A cozy reading corner in warm daylight" \
  --output output/reading-corner.png \
  --json
```

Expected routing: `gpt-image-2`, `1024x1024`, no `quality`.

### Complex Or High-Precision Image

```bash
node scripts/generate.js \
  --profile vip \
  --promptfile prompts/system-architecture.md \
  --size 2560x1440 \
  --quality high \
  --output output/system-architecture.png \
  --json
```

### Single-Reference Edit

```bash
node scripts/edit.js \
  --profile auto \
  --image references/product.png \
  --prompt "Replace the background with a warm studio scene" \
  --output output/product-edit.png \
  --json
```

Expected routing: `gpt-image-2`.

### Multi-Reference Edit

```bash
node scripts/edit.js \
  --profile auto \
  --image references/product.png \
  --image references/material.jpg \
  --prompt "Keep the form from image one and use the material from image two" \
  --output output/combined-edit.png \
  --json
```

Expected routing: `gpt-image-2-vip`.

### URL Reference Edit

```bash
node scripts/edit.js \
  --url "https://example.com/reference.jpg" \
  --prompt "Convert this scene into a watercolor illustration" \
  --output output/url-edit.png
```

Do not mix `--image` and `--url` in one request.

## 5. Parameter Rules

Common:

- `--profile auto|standard|vip`: routing policy; default `auto`.
- `--model gpt-image-2|gpt-image-2-vip`: explicit override; normally prefer `--profile`.
- `--size <preset>`: select a documented output specification or ratio. It is not an arbitrary or
  guaranteed exact resolution.
- `--prompt <text>` or `--promptfile <path>`: exactly one prompt source.
- `--output <path>`: final image path.
- `--prompt-output <path>`: optional prompt archive override.
- `--json`: structured result without Base64.
- `--dry-run`: route preview without API call.

Generate only:

- `--n <integer>`: number of images; default `1`.
- If the gateway returns fewer images than `--n`, the script automatically sends follow-up requests
  until the requested count is reached.

VIP only:

- `--quality auto|low|medium|high`: sampling quality. It does not control the output specification.

Do not pass `--quality` to the standard model. Do not pass 2K/4K presets to the standard model.

## 6. Output Paths

When `--output` is omitted, write under the current working directory:

```text
gpt-image-2-output/
|-- generated/   # text-to-image results
|-- edited/      # reference-image results
`-- prompts/     # archived prompts
```

All returned paths are absolute in `--json` output. When `--n > 1`, append `-1`, `-2`, and so on.
Structured output reports each image's actual dimensions. A mismatch warning means the gateway
treated the pixel-looking `--size` value as a preset rather than an exact resolution; it does not
necessarily mean generation failed.

## 7. Configuration

Require Node.js 18+ and `OPENAI_API_KEY`. Load settings in this order:

1. Process environment
2. `<cwd>/.env`
3. `<cwd>/.gateway.env`
4. `~/.gateway.env`

Use [.env.example](./.env.example). Never store a real key in this skill or a commit.

Check configuration:

```bash
node scripts/check-config.js
```

Read [references/api-reference.md](./references/api-reference.md) only when a parameter value or error needs lookup.
