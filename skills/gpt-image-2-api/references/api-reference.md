# GPT Image 2 API Reference

## Providers

| Route | Provider | Model | Use |
|---|---|---|---|
| Standard | aifast.site | `gpt-image-2` | Generation and ordinary single-reference edits |
| VIP | aifast.site | `gpt-image-2-max` | Primary max-model, multi-reference, and precision-sensitive route |
| Atlas fallback | AtlasCloud | `openai/gpt-image-2/edit` | Backup for VIP edit failures and explicit `--profile atlas` |

`--profile hd` maps to `vip` for compatibility with the previous AtlasCloud-only version.

## aifast Standard/VIP Route

- Generate: `POST https://aifast.site/v1/images/generations`
- Edit: `POST https://aifast.site/v1/images/edits`
- Authentication: `OPENAI_API_KEY`
- Generate body: JSON
- Edit body: multipart form

Models:

| Model | Output tier | Quality |
|---|---|---|
| `gpt-image-2` | Up to 1K | omit |
| `gpt-image-2-max` | Provider create sizes / edit ratios | omit for aifast create/edit; use model choice for max quality |

`gpt-image-2-vip` is retired upstream. The scripts still accept it as a `--model`/manifest alias and
silently map it to `gpt-image-2-max`.

Create endpoint constraints from the provider OpenAPI:

- JSON body should use `model`, `prompt`, `n`, and `size`.
- Do not send `quality` or `response_format`.
- Supported create sizes are `auto`, `1024x1024`, `1536x1024`, and `1024x1536`.
- CLI ratio tokens are mapped before request: square -> `1024x1024`, landscape -> `1536x1024`,
  portrait -> `1024x1536`.

Edit endpoint size tokens:

`auto`, `1:1`, `3:2`, `2:3`, `4:3`, `3:4`, `5:4`, `4:5`, `16:9`, `9:16`, `21:9`, `9:21`,
`2:1`, `1:2`, `3:1`, and `1:3`.

## AtlasCloud Fallback Route

Submit:

```http
POST https://api.atlascloud.ai/api/v1/model/generateImage
Authorization: Bearer <ATLASCLOUD_API_KEY>
Content-Type: application/json
```

Poll:

```http
GET https://api.atlascloud.ai/api/v1/model/result/<request-id>
Authorization: Bearer <ATLASCLOUD_API_KEY>
```

The scripts also accept a `data` wrapper for compatibility with older AtlasCloud examples. Continue
while status is `created` or `processing`. On `completed`, download every URL in `outputs`. On
`failed`, surface the returned error. Preserve `has_nsfw_contents` in JSON output.

AtlasCloud accepts 1 to 10 public reference URLs. Local PNG, JPEG, and WebP files are encoded as data
URLs before submission.

AtlasCloud size enum: `1024x1024`, `1024x1536`, `1536x1024`, `2048x2048`, `2048x1152`,
`3840x2160`, `2160x3840`.

When VIP falls back to AtlasCloud, unsupported VIP sizes are mapped conservatively:

- square -> `2048x2048`
- landscape -> `2048x1152`
- tall portrait -> `2160x3840`
- other portrait -> `1024x1536`

## Fallback Rules

- VIP edit failures fall back to AtlasCloud when `ATLASCLOUD_API_KEY` is configured.
- HTTP 400/401 from VIP do not fall back, because they usually mean invalid parameters, policy block,
  or invalid credentials.
- VIP generation does not fall back because AtlasCloud uses an edit-only model.
- Set `GPT_IMAGE_ATLAS_FALLBACK=false` to disable automatic fallback.

## Timeout Behavior

- aifast standard/VIP image requests default to no local client timeout. The API is synchronous and
  long-running high-resolution jobs may take more than five minutes.
- Set `OPENAI_IMAGE_TIMEOUT_MS` to a positive integer only when the caller needs its own abort limit.
- AtlasCloud fallback remains async and uses `ATLASCLOUD_POLL_TIMEOUT_MS` for polling.

## Response Format

- Generation omits `response_format` and `quality`, because the copied provider OpenAPI for
  `/v1/images/generations` does not define either field for GPT Image 2.
- The scripts can save both `data[].url` and `data[].b64_json`.
- URL downloads for generated images, Atlas outputs, and remote reference images use
  `OPENAI_IMAGE_MAX_RETRIES`; 5xx/429/network failures retry with exponential backoff, while
  ordinary 4xx failures fail immediately.
- Multiple remote reference URLs are downloaded in parallel, then appended to multipart form data in
  the original CLI/manifest order.
- Auto-named output files include milliseconds plus a process-local counter to avoid same-second
  collisions in batch/concurrent runs.

## Configuration

The scripts call `loadAmbientEnv()` and read settings from these files, in order:

1. `.env` in the current working directory
2. `.gateway.env` in the current working directory
3. `~/.gateway.env`
4. `.env` in the skill root directory
5. `.gateway.env` in the skill root directory

Existing process environment variables win over file values. Prefer `~/.gateway.env` for a local
agent machine; the skill-root files are a fallback for running scripts from another cwd. Keep real
keys out of Git.

Agent quick configuration:

```bash
cd path/to/gpt-image-2-api
cp .env.example .gateway.env
# Fill OPENAI_API_KEY. Fill ATLASCLOUD_API_KEY only for Atlas fallback.
node scripts/check-config.js
node scripts/generate.js --prompt "smoke test image" --dry-run --json
```

Expected `check-config.js` signals:

- `ready: true`
- `hasApiKey: true` for standard/VIP
- `hasAtlasApiKey: true` only when Atlas fallback is configured
- `defaultProfile: auto`
- `timeoutMs: none` when `OPENAI_IMAGE_TIMEOUT_MS=0`

```dotenv
OPENAI_API_KEY=
OPENAI_BASE_URL=https://aifast.site/v1

ATLASCLOUD_API_KEY=
ATLASCLOUD_BASE_URL=https://api.atlascloud.ai/api/v1/model
ATLASCLOUD_POLL_INTERVAL_MS=2000
ATLASCLOUD_POLL_TIMEOUT_MS=300000

GPT_IMAGE_PROFILE=auto
GPT_IMAGE_GENERATION_SIZE=1024x1024
GPT_IMAGE_STANDARD_SIZE=1024x1024
GPT_IMAGE_VIP_SIZE=2048x2048
GPT_IMAGE_VIP_QUALITY=high
GPT_IMAGE_ATLAS_FALLBACK=true
GPT_IMAGE_ATLAS_SIZE=2048x2048
GPT_IMAGE_ATLAS_QUALITY=high
OPENAI_IMAGE_TIMEOUT_MS=0
OPENAI_IMAGE_MAX_RETRIES=2
```
