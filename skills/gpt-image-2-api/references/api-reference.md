# GPT Image 2 API Reference

## Providers

| Route | Provider | Model | Use |
|---|---|---|---|
| Standard | aifast.site | `gpt-image-2` | Generation and ordinary edits |
| HD | AtlasCloud | `openai/gpt-image-2/edit` | High-quality reference edits |

The former `gpt-image-2-vip` route is disabled. `--profile vip` is accepted only as an alias for
the AtlasCloud `hd` profile.

## Standard Route

- Generate: `POST https://aifast.site/v1/images/generations`
- Edit: `POST https://aifast.site/v1/images/edits`
- Authentication: `OPENAI_API_KEY`
- Generate body: JSON
- Edit body: multipart form

## AtlasCloud HD Route

Submit:

```http
POST https://api.atlascloud.ai/api/v1/model/generateImage
Authorization: Bearer <ATLASCLOUD_API_KEY>
Content-Type: application/json
```

Payload:

```json
{
  "model": "openai/gpt-image-2/edit",
  "enable_base64_output": false,
  "enable_sync_mode": false,
  "images": ["https://example.com/reference.jpg"],
  "output_format": "png",
  "prompt": "Edit instruction",
  "quality": "high",
  "size": "1536x1024",
  "moderation": "low"
}
```

Poll:

```http
GET https://api.atlascloud.ai/api/v1/model/result/<request-id>
Authorization: Bearer <ATLASCLOUD_API_KEY>
```

The OpenAPI Schema returns prediction fields at the response root. The scripts also accept a
`data` wrapper for compatibility with the earlier code example.

Continue while status is `created` or `processing`. On `completed`, download every URL in
`outputs`. On `failed`, surface the returned error. Preserve `has_nsfw_contents` in JSON output.

The scripts accept 1 to 10 public reference URLs. Local PNG, JPEG, and WebP files are encoded as
data URLs for the Atlas request.

## HD Parameters

- Model: always `openai/gpt-image-2/edit`
- Quality: `low`, `medium`, or `high`
- Output format: `png` or `jpeg`, inferred from `--output`
- Default size: `2048x2048`
- Schema size enum: `1024x1024`, `1024x1536`, `1536x1024`, `2048x2048`, `2048x1152`,
  `3840x2160`, `2160x3840`

The Schema description says arbitrary GPT Image 2 resolutions may be accepted when both dimensions
are divisible by 16, the ratio is between 1:3 and 3:1, and the maximum is `3840x2160`. However, the
same Schema declares a strict 7-value enum. The scripts follow the enum to avoid paid invalid
requests. Resolutions above `2560x1440` are experimental.

## Configuration

```dotenv
OPENAI_API_KEY=
OPENAI_BASE_URL=https://aifast.site/v1

ATLASCLOUD_API_KEY=
ATLASCLOUD_BASE_URL=https://api.atlascloud.ai/api/v1/model
ATLASCLOUD_POLL_INTERVAL_MS=2000
ATLASCLOUD_POLL_TIMEOUT_MS=300000

GPT_IMAGE_PROFILE=auto
GPT_IMAGE_STANDARD_SIZE=1024x1024
GPT_IMAGE_HD_SIZE=2048x2048
GPT_IMAGE_HD_QUALITY=high
```
