---
name: gpt-image-2-api
description: Generate images through the aifast.site GPT Image API and perform high-quality reference edits through AtlasCloud. Use for text-to-image, local or URL reference editing, multi-reference composition, quality-controlled edits, and supported 1K, 2K, or experimental 4K output. Default to the lower-cost standard route; use AtlasCloud HD for multiple references, explicit quality control, high resolution, or precision-sensitive editing.
---

# GPT Image 2 API

Run the bundled commands from this skill directory:

```bash
node scripts/generate.js ...
node scripts/edit.js ...
node scripts/check-config.js
```

## Route By Cost

Use `--profile auto` by default.

| Task | Route |
|---|---|
| Text-to-image | Standard `gpt-image-2` |
| Ordinary edit with one reference | Standard `gpt-image-2` |
| Multiple references or explicit `--quality` | AtlasCloud HD |
| Precision-sensitive edit | Explicit `--profile hd` |

`--profile vip` remains a compatibility alias for `hd`. Do not use the failed
`gpt-image-2-vip` provider directly.

AtlasCloud HD currently uses `openai/gpt-image-2/edit`, so it requires at least one reference image.
Use standard generation when no reference is available.

## Execute

Preview the request before incurring cost:

```bash
node scripts/edit.js \
  --profile hd \
  --url https://example.com/source.jpg \
  --prompt "Create a high-detail e-commerce poster" \
  --size 2048x1152 \
  --quality high \
  --dry-run
```

Then rerun without `--dry-run`:

```bash
node scripts/edit.js \
  --profile hd \
  --url https://example.com/source.jpg \
  --prompt "Create a high-detail e-commerce poster" \
  --size 2048x1152 \
  --quality high \
  --output output/poster.png \
  --json
```

Standard text-to-image:

```bash
node scripts/generate.js \
  --prompt "A cozy reading corner" \
  --output output/result.png \
  --json
```

Repeat `--image` for local references or `--url` for public references, up to 10 total. Never mix
the two.

## Parameters

- Prompt: use exactly one of `--prompt` or `--promptfile`.
- Routing: `--profile auto|standard|hd`.
- HD size: use one of the 7 AtlasCloud Schema values. Prefer `2048x2048` or `2048x1152`;
  use 4K only when explicitly requested.
- HD quality: use `low`, `medium`, or `high`.
- Output: use `--output`, optional `--prompt-output`, and recommended `--json`.

Read [references/api-reference.md](./references/api-reference.md) for provider payloads, supported
sizes, polling behavior, configuration, or API error diagnosis.

Require Node.js 18+. Configure `OPENAI_API_KEY` for the standard route and
`ATLASCLOUD_API_KEY` for AtlasCloud HD. Never store real keys in this skill or Git.
