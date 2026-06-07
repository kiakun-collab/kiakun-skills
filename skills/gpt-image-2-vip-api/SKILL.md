---
name: gpt-image-2-vip-api
description: Generate and edit high-resolution images through an OpenAI-compatible GPT Image API, using gpt-image-2-vip with 2K and high quality by default. Use when the user wants direct API image generation, reference-image editing, multiple image outputs, 2K/4K rendering, or configuration of the aifast.site image gateway. Requires OPENAI_API_KEY at runtime and never stores real API keys in the skill.
---

# GPT Image 2 VIP API

Use this skill for direct image generation and editing through the configured API. This is a standalone API workflow: do not delegate rendering to a host image tool and do not fall back to prompt-only mode.

## Defaults

- Base URL: `https://aifast.site/v1`
- Model: `gpt-image-2-vip`
- Size: `2048x2048`
- Quality: `high`
- Count: `1`
- Response format: `b64_json`
- Request timeout: 300 seconds
- Retry count: 2 for network failures, HTTP 429, and HTTP 5xx

Use 2K unless the user explicitly requests 4K. Use pixel dimensions for the VIP model; do not use ratio-only values such as `1:1`.

## Configure

Require `OPENAI_API_KEY`. Read configuration in this order:

1. Existing process environment variables
2. `<cwd>/.env`
3. `<cwd>/.gateway.env`
4. `~/.gateway.env`

Use [.env.example](./.env.example) as a template. Never place a real key in this skill, a prompt file, command output, commit, or response.

Run the configuration check before a paid request:

```bash
node scripts/check-config.js
```

## Generate

Generate one image with the defaults:

```bash
node scripts/generate.js \
  --prompt "A premium product photograph of a ceramic watch" \
  --image output/watch.png
```

Override size, quality, or count only when requested:

```bash
node scripts/generate.js \
  --promptfile prompts/campaign.md \
  --size 3840x2160 \
  --quality high \
  --n 2 \
  --image output/campaign.png \
  --json
```

When `n` is greater than 1, save every returned image with `-1`, `-2`, and so on.

## Edit Local Images

Use one or more local PNG, JPEG, or WebP files:

```bash
node scripts/edit.js \
  --image references/product.png \
  --image references/material.jpg \
  --prompt "Keep the product shape from image one and use the material from image two" \
  --output output/edited.png
```

## Edit Image URLs

Use one or more publicly accessible image URLs:

```bash
node scripts/edit.js \
  --url "https://example.com/reference-1.jpg" \
  --url "https://example.com/reference-2.jpg" \
  --prompt "Create a cohesive studio composition from these references" \
  --output output/url-edit.png
```

Do not mix `--image` and `--url` in one request.

## Output

Unless explicitly overridden, save:

- Prompts under `gpt-image-2-vip-output/prompt/`
- Images under `gpt-image-2-vip-output/image/`

Print image paths on success. With `--json`, return paths and response metadata, never image Base64.

## Failure Handling

- `400`: report the gateway message; do not retry.
- `401`: request a valid `OPENAI_API_KEY`; do not expose the current value.
- `429`: retry automatically, then report rate limiting.
- `5xx`: retry automatically, then report the upstream failure.
- Timeout: report the configured timeout and suggest a smaller output only if the user did not explicitly require 4K.

Read [references/api-reference.md](./references/api-reference.md) when selecting 2K/4K dimensions or diagnosing gateway-specific behavior.
