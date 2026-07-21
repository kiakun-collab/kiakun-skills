---
name: gpt-image-2-api
description: Generate or edit images through independent aifast.site, XApex, and AtlasCloud routes with cost-aware routing, gpt-image-2-max support, XApex sync/async tasks, AtlasCloud edit fallback, and batch generation. Use for text-to-image, local or URL reference editing, multi-reference composition, precision-sensitive graphics, XApex image-group tokens, provider-specific sizes and quality, batch jobs, and resilient editing.
---

# GPT Image 2 API

The scripts are already built and tested. **Run them directly — never rewrite, regenerate,
or reimplement them.** Just call `node scripts/<name>.js` from this skill directory with the
right flags. Reach for `references/api-reference.md` only when you need provider payloads or to
diagnose an API error.

## Start Here (no setup needed on each run)

```bash
# Text to image
node scripts/generate.js --prompt "a red fox in snow"

# Edit one image
node scripts/edit.js --image photo.png --prompt "add sunglasses"

# Batch: many prompts at once
node scripts/batch.js --promptlist prompts.txt

# XApex: isolated credentials, quality, size mapping, and optional async polling
node scripts/generate.js --profile xapex --prompt "a red fox in snow" --quality low
node scripts/edit.js --profile xapex --image photo.png --prompt "add sunglasses"
node scripts/generate.js --profile xapex --async --prompt "a lighthouse at dusk"
```

Add `--dry-run` for a no-cost route/cost preview. Add `--json` for a machine-readable result.

If a run fails with a missing-key or config error, do the one-time setup below. Otherwise skip it.

## Choosing a command

| You want to... | Use |
|---|---|
| One image from text | `generate.js` |
| One image edited from a reference | `edit.js` |
| Many images in one go | `batch.js` |

## Reference-image intent (decide before editing)

When the user supplies a reference image, decide **why** the pixels matter, then route:

**A. Identity / replication — the reference itself must be preserved.**
Face swap, same character across scenes, keep this exact product/logo, "use this photo",
composition or subject must carry over. The model needs the actual pixels as context.
→ Use `edit.js` with `--image`/`--url`. For multi-image consistency (e.g. character + scene),
pass every needed reference; two or more references auto-route to VIP.

**B. Style / material / palette only — borrow the look, not the subject.**
"Same art style as this", "this brushwork/texture", "this color mood", but a *new* subject or
scene. Feeding raw pixels here tends to leak the reference's subject and composition.
→ Prefer describing the look in words and using `generate.js` (text-to-image): read the
reference, write the style/material/palette/lighting into the prompt, then generate fresh.
→ If the style is hard to verbalize and fidelity matters, fall back to `edit.js` with a prompt
that explicitly says to copy only the style and invent a new subject/composition.

**When unsure, ask one short question**: "Do you want this image reproduced (keep the subject),
or just its style on a new subject?" Default to A (edit with the reference) only when the user
clearly means "this exact thing".

## Batch generation

Two input modes:

**Prompt list** — one prompt per line, all sharing the same routing/size params:

```bash
node scripts/batch.js --promptlist prompts.txt --model gpt-image-2-max --size 9:16
```

**JSON manifest** — per-task control (mix generate and edit, different sizes, references):

```bash
node scripts/batch.js --batch tasks.json
```

`tasks.json` is a JSON array (or one JSON object per line, JSONL). Each task:

```json
[
  { "prompt": "a red fox in snow" },
  { "prompt": "a launch poster", "model": "gpt-image-2-max", "size": "9:16", "quality": "high" },
  { "prompt": "add sunglasses", "images": ["photo.png"] },
  { "prompt": "combine references", "images": ["a.png", "b.png"], "output": "combo.png" }
]
```

Per-task fields: `prompt` or `promptfile`, `profile`, `model`, `size`, `quality`, `n`,
`output`, and `images` / `urls` (presence of either routes the task to `edit.js`).

Batch flags: `--concurrency <n>` (default 2, keeps clear of rate limits), `--output-dir <dir>`
(base for auto-named outputs), `--dry-run`, `--json`. Batch continues past a failed task and
prints a summary of successes and failures at the end. Batch runs generate/edit tasks in-process,
so it avoids starting a fresh Node.js child process for every image.

Auto-named outputs include milliseconds plus a process-local counter, so parallel or rapid
same-prompt tasks do not overwrite each other by default.

## Common single-task flows

Preview a high-detail edit before incurring cost, then rerun without `--dry-run`:

```bash
node scripts/edit.js --profile vip --url https://example.com/source.jpg \
  --prompt "high-detail e-commerce poster" --size 2048x2048 --quality high --dry-run

node scripts/edit.js --profile vip --url https://example.com/source.jpg \
  --prompt "high-detail e-commerce poster" --size 2048x2048 --quality high \
  --output output/poster.png --json
```

VIP text-to-image:

```bash
node scripts/generate.js --model gpt-image-2-max --size 9:16 --quality high \
  --prompt "A launch poster with dense product detail" --output output/poster.png --json
```

For generation, `--quality high` is only a routing hint that selects `gpt-image-2-max`; it is not
sent as an API field. Standard `gpt-image-2` uses the provider 1K create sizes. Max
`gpt-image-2-max` follows the aifast VIP size table; ratio tokens such as `9:16` map to documented
2K presets such as `1440x2560` so the requested and returned dimensions stay aligned.

## Routing

Default `--profile auto`. In `auto`, multiple reference images, explicit `--quality`, or a
2K/4K preset promote the task to VIP automatically.

| Task | Primary route | Fallback |
|---|---|---|
| Text-to-image, daily illustration, social post | Standard `gpt-image-2` | None |
| Ordinary edit with one reference | Standard `gpt-image-2` | None |
| Multiple references or explicit `--quality` | VIP `gpt-image-2-max` | AtlasCloud (edit only) |
| Precision-sensitive work or explicit max model | VIP `gpt-image-2-max` | AtlasCloud (edit only) |
| XApex image-group token, sync or async | XApex `gpt-image-2` | None |

`--profile hd` is a legacy alias for `vip`. Use `--profile atlas` only to force the AtlasCloud
channel for diagnosis. AtlasCloud uses `openai/gpt-image-2/edit`, so it needs at least one
reference image; VIP text-to-image does not fall back. Disable edit fallback with
`GPT_IMAGE_ATLAS_FALLBACK=false`.

`--profile xapex` is isolated from aifast and AtlasCloud: it uses `XAPEX_API_KEY`,
`XAPEX_BASE_URL`, its own model/size/quality defaults, request retries, and async polling settings.

## Parameters

- Prompt: use exactly one of `--prompt` or `--promptfile`.
- Routing: `--profile auto|standard|vip|atlas|xapex`; prefer `auto` for aifast and select
  `xapex` explicitly for XApex (`hd` = legacy alias for `vip`).
- References for editing: repeat `--image` for local files or repeat `--url` for public URLs.
  Do not mix `--image` and `--url` in the same request.
- Standard generation size: `auto`, `256x256`, `512x512`, `1024x1024`, `1280x720`,
  `720x1280`, `1536x1024`, `1024x1536`, `1792x1024`, or `1024x1792`.
- Max generation size: a documented aifast VIP/max preset, including 1K, 2K, and 4K table
  entries such as `2048x2048`, `2560x1440`, `1440x2560`, `3840x2160`, or `2160x3840`.
  Ratio tokens such as `9:16` map to the documented 2K presets by default.
- Edit/VIP size: a documented edit preset or ratio token such as `9:16`.
- XApex size: `1024x1024`, `1536x1024`, or `1024x1536`. Other pixel sizes and ratios are
  mapped client-side by orientation to one of these safe sizes.
- Quality: for generation, `--quality` only routes to `gpt-image-2-max` and is omitted from the
  API request. Live probes against aifast showed `quality` can make max generation disconnect even
  when the same size succeeds without it. For edit/Atlas fallback, `auto`, `low`, `medium`, or
  `high` are supported. XApex sends `quality` for both generation and edits; its default is `low`.
- XApex async: add `--async` with `--profile xapex`. The script submits to the XApex `/async`
  endpoint and polls `/v1/images/tasks/{task_id}` with the same XApex key until completion.
- Timeout: leave `OPENAI_IMAGE_TIMEOUT_MS=0` so long high-resolution jobs can finish.
- Retries: `OPENAI_IMAGE_MAX_RETRIES` also covers generated-image URL downloads and remote
  reference downloads; 5xx/429/network failures retry, ordinary 4xx failures do not.
- Generation omits `quality` and `response_format`; the scripts save either `data[].url` or
  `data[].b64_json` responses.
- Output: `--output`, optional `--prompt-output`, and recommended `--json`.

Read [references/api-reference.md](./references/api-reference.md) for provider payloads,
supported sizes, fallback behavior, or API error diagnosis.

## One-time setup (only when a run reports missing config)

```bash
node scripts/check-config.js          # reports keys, models, endpoints, timeout, fallback
cp .env.example .gateway.env          # then fill OPENAI_API_KEY
```

1. Provide Node.js 18+. Keep secrets out of Git.
2. Put gateway settings in an auto-loaded file: current-directory `.env`, current-directory
   `.gateway.env`, user-level `~/.gateway.env`, or the skill root `.env` / `.gateway.env`.
   Earlier sources win; process environment variables always win over files.
3. `OPENAI_API_KEY` is required for standard/VIP. Add `ATLASCLOUD_API_KEY` only for edit
   fallback or forced `--profile atlas`. Add `XAPEX_API_KEY` only for `--profile xapex`; it must
   be an XApex token in the `图片` group.
4. Keep `OPENAI_IMAGE_TIMEOUT_MS=0` unless the caller wants a local abort limit.
5. Confirm `check-config.js` shows `ready: true`, `hasApiKey: true`, and `timeoutMs: none`.
