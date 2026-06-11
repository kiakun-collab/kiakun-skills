---
name: gpt-image-2-api
description: Generate or edit images through the aifast.site GPT Image API with cost-aware routing. Use for text-to-image, local or URL reference editing, multi-reference composition, complex precision-sensitive graphics, and supported 1K/2K/4K output tiers. Default to gpt-image-2; use gpt-image-2-vip only for complex work, multiple references, quality control, or supported high-resolution presets.
---

# GPT Image 2 API

Run the bundled commands directly. Do not inspect scripts to discover usage.

## Command Paths

Run from this skill directory:

```bash
node scripts/generate.js ...
node scripts/edit.js ...
node scripts/check-config.js
```

Fixed endpoints:

- Generate: `POST https://aifast.site/v1/images/generations`
- Edit: `POST https://aifast.site/v1/images/edits`

## Route By Cost

Use `--profile auto` unless semantic complexity requires VIP.

| Task | Route |
|---|---|
| Daily illustration, avatar, product image, social post | Standard `gpt-image-2` |
| Ordinary edit with one reference | Standard `gpt-image-2` |
| Complex infographic, architecture diagram, academic figure, dense UI/poster | VIP |
| Fine typography, small labels, publication-grade detail | VIP |
| Two or more references | Auto-upgrade to VIP |
| Supported 2K/4K preset or explicit `quality` | Auto-upgrade to VIP |

Never use VIP merely because it is available.

## Treat Size As A Preset

`--size` is a whitelist preset/aspect-ratio selector, not an arbitrary exact resolution.

- Never invent values such as `1600x900`, `1920x1080`, or `4096x4096`.
- Pixel-looking values are gateway tokens mapped to an upstream ratio/output tier.
- Final dimensions may differ. Read `actualImages` from `--json`.
- Read [references/api-reference.md](./references/api-reference.md) only to select an uncommon
  preset or diagnose an API error.

## Execute

Always preview the paid request first:

```bash
node scripts/generate.js --profile auto --prompt "A cozy reading corner" --dry-run
```

Check `selectedTier`, `model`, `size`, `quality`, and `routeReasons`, then rerun without `--dry-run`.

Text-to-image:

```bash
node scripts/generate.js \
  --profile auto \
  --prompt "A cozy reading corner" \
  --output output/result.png \
  --json
```

Reference edit:

```bash
node scripts/edit.js \
  --profile auto \
  --image references/source.png \
  --prompt "Replace the background with a warm studio" \
  --output output/edited.png \
  --json
```

Repeat `--image` for multiple local references. Use repeatable `--url` for public references. Never
mix `--image` and `--url`.

For semantically complex work, force VIP and choose a listed preset:

```bash
node scripts/generate.js \
  --profile vip \
  --size 2560x1440 \
  --quality high \
  --promptfile prompts/task.md \
  --output output/high-detail.png \
  --json
```

## Essential Parameters

- Prompt: use exactly one of `--prompt` or `--promptfile`.
- Routing: `--profile auto|standard|vip`; prefer this over `--model`.
- Output preset: `--size <listed-preset-or-ratio>`.
- VIP sampling: `--quality auto|low|medium|high`; never use with standard.
- Generate count: `--n <integer from 1 to 10>`; the script backfills if the gateway returns too few images.
- Result: `--output`, optional `--prompt-output`, and recommended `--json`.

When `--output` is omitted, results go to `gpt-image-2-output/generated/` or `edited/`; prompts go to
`gpt-image-2-output/prompts/`.

Require Node.js 18+ and `OPENAI_API_KEY`. Never store a real key in this skill or Git.
