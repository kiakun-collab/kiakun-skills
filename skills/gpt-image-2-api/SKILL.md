---
name: gpt-image-2-api
description: Generate or edit images through the aifast.site GPT Image API with cost-aware routing, restored gpt-image-2-vip high-resolution support, and AtlasCloud fallback for VIP edit failures. Use for text-to-image, local or URL reference editing, multi-reference composition, precision-sensitive graphics, quality-controlled edits, supported 1K/2K/4K output tiers, and resilient high-resolution editing when VIP may be unavailable.
---

# GPT Image 2 API

Run the bundled commands from this skill directory.

## Quick Start

```bash
# Text to image
node scripts/generate.js --prompt "a red fox in snow"

# Edit one image
node scripts/edit.js --image photo.png --prompt "add sunglasses"
```

For a cost preview before sending an API request, add `--dry-run`. To print a machine-readable
result, add `--json`.

Check local environment and routing defaults when setup looks suspicious:

```bash
node scripts/check-config.js
```

It reports whether required keys are present, which models and endpoints are configured, local
timeout behavior, and whether AtlasCloud fallback is available.

## Common Flows

Preview a high-detail edit before incurring cost:

```bash
node scripts/edit.js \
  --profile vip \
  --url https://example.com/source.jpg \
  --prompt "Create a high-detail e-commerce poster" \
  --size 2048x2048 \
  --quality high \
  --dry-run
```

Then rerun without `--dry-run`:

```bash
node scripts/edit.js \
  --profile vip \
  --url https://example.com/source.jpg \
  --prompt "Create a high-detail e-commerce poster" \
  --size 2048x2048 \
  --quality high \
  --output output/poster.png \
  --json
```

VIP text-to-image:

```bash
node scripts/generate.js \
  --profile vip \
  --size 2560x1440 \
  --quality high \
  --prompt "A launch poster with dense product detail" \
  --output output/poster.png \
  --json
```

## Routing

Use `--profile auto` by default.

| Task | Primary Route | Fallback |
|---|---|---|
| Text-to-image, daily illustration, social post | Standard `gpt-image-2` | None |
| Ordinary edit with one reference | Standard `gpt-image-2` | None |
| Multiple references or explicit `--quality` | VIP `gpt-image-2-vip` | AtlasCloud for edit only |
| 2K/4K preset or precision-sensitive work | VIP `gpt-image-2-vip` | AtlasCloud for edit only |

In `auto`, multiple reference images, explicit `--quality`, or a 2K/4K preset automatically route
to VIP.

`--profile hd` is a compatibility alias for `vip`.
Use `--profile atlas` only to force the AtlasCloud channel for diagnosis or manual fallback.

AtlasCloud uses `openai/gpt-image-2/edit`, so it requires at least one reference image. VIP
generation does not automatically fall back because AtlasCloud does not provide text-to-image for
this model. Disable edit fallback with `GPT_IMAGE_ATLAS_FALLBACK=false`.

## Parameters

- Prompt: use exactly one of `--prompt` or `--promptfile`.
- Routing: `--profile auto|standard|vip|atlas`; prefer `auto`; `hd` is accepted as a legacy alias
  for `vip`.
- References for editing: repeat `--image` for local files or repeat `--url` for public URLs. Do
  not mix `--image` and `--url` in the same request.
- VIP size: use a documented VIP preset such as `2048x2048`, `2560x1440`, or `3840x2160`.
- VIP quality: use `auto`, `low`, `medium`, or `high`.
- AtlasCloud fallback: override with `GPT_IMAGE_ATLAS_FALLBACK=false`.
- Timeout: leave `OPENAI_IMAGE_TIMEOUT_MS=0` so aifast standard/VIP requests can wait for the API to
  finish.
- VIP generation omits `response_format` intentionally so high-resolution results return by URL
  instead of slow Base64 payloads.
- Output: use `--output`, optional `--prompt-output`, and recommended `--json`.

Read [references/api-reference.md](./references/api-reference.md) for provider payloads, supported
sizes, fallback behavior, configuration, or API error diagnosis.

Require Node.js 18+ and `OPENAI_API_KEY` for standard/VIP. Configure `ATLASCLOUD_API_KEY` to enable
AtlasCloud fallback. Never store real keys in this skill or Git.
