# GPT Image 2 API Reference

Source: `https://9nnc8eo3c5.apifox.cn/8671595m0.md` (updated 2026-04-30).

## Models

| Model | Use | Supported output tier | Quality parameter |
|---|---|---|---|
| `gpt-image-2` | Default daily generation and ordinary single-reference edits | Up to 1K | Not effective; omit it |
| `gpt-image-2-vip` | Complex/high-precision work, multiple references, 2K/4K | 1K/2K/4K | `auto`, `low`, `medium`, `high` |

## Routes

| Operation | Method | Path | Body |
|---|---|---|---|
| Text-to-image | POST | `/v1/images/generations` | JSON |
| Local reference edit | POST | `/v1/images/edits` | multipart form |
| Public URL reference edit | POST | `/v1/images/edits` | Script downloads URLs and uploads multipart |

Authentication:

```http
Authorization: Bearer <OPENAI_API_KEY>
```

## Generate Parameters

| Parameter | Type | Required | Rules |
|---|---|---|---|
| `model` | string | Yes | `gpt-image-2` or `gpt-image-2-vip` |
| `prompt` | string | Yes | Image description |
| `n` | integer | No | Default `1` |
| `size` | string | No | Supported preset token or aspect ratio; not arbitrary exact dimensions |
| `quality` | string | No | VIP only |
| `response_format` | string | No | Always use `b64_json` |

## Edit Parameters

| Parameter | Type | Required | Rules |
|---|---|---|---|
| `model` | string | Yes | Standard or VIP |
| `prompt` | string | Yes | Edit instruction |
| `image` | file | For multipart | PNG, JPEG, or WebP; repeatable |
| `urls` | string[] | Documented gateway extension | Do not send directly; live testing found the gateway expects multipart |
| `size` | string | No | Supported preset token or aspect ratio; not arbitrary exact dimensions |
| `quality` | string | No | VIP only |

## Size Semantics

The API field is named `size`, but it is not a free-form resolution control. The gateway converts
pixel-looking values to the upstream `aspectRatio` field. Therefore:

- Only use a token listed below.
- Values such as `1600x900`, `1920x1080`, and `4096x4096` are unsupported unless explicitly listed.
- Several tokens can map to the same aspect ratio.
- The final PNG dimensions are selected by the model/gateway and may differ from the token.
- Treat 1K/2K/4K as supported output tiers, not a promise of arbitrary pixel dimensions.

Live standard-model tests returned `1254x1254` for both `256x256` and `1024x1024` requests. The
scripts report actual dimensions so callers do not mistake the request token for the final file size.

## Standard Preset Tokens

Use these with `gpt-image-2`:

| Preset token | Mapped ratio / purpose |
|---|---|
| `1024x1024` | 1:1 default |
| `512x512` | Small square |
| `256x256` | Minimum square |
| `1536x1024` | 3:2 landscape |
| `1792x1024` | 3:2 wide landscape |
| `1024x1536` | 2:3 portrait |
| `1024x1792` | 2:3 tall portrait |
| `1280x720` | 16:9 |
| `720x1280` | 9:16 |
| `auto` | Model decides |

Supported ratio strings:

`1:1`, `3:2`, `2:3`, `4:3`, `3:4`, `5:4`, `4:5`, `16:9`, `9:16`, `21:9`, `9:21`, `2:1`, `1:2`, `3:1`, `1:3`, `auto`.

## VIP 2K / 4K Preset Tokens

| Ratio | 2K | 4K |
|---|---|---|
| 1:1 | `2048x2048` | `2880x2880` |
| 16:9 | `2560x1440` | `3840x2160` |
| 9:16 | `1440x2560` | `2160x3840` |
| 4:3 | `2304x1728` | `3264x2448` |
| 3:4 | `1728x2304` | `2448x3264` |
| 3:2 | `2496x1664` | `3504x2336` |
| 2:3 | `1664x2496` | `2336x3504` |
| 5:4 | `2240x1792` | `3200x2560` |
| 4:5 | `1792x2240` | `2560x3200` |
| 21:9 | `3024x1296` | `3696x1584` |

Use one of the listed 2K/4K preset tokens for VIP. Do not substitute a custom resolution. A live
gateway test observed `1024x1024` being converted to `1:1` and rejected by the VIP upstream.

## Quality

VIP only:

| Value | Meaning |
|---|---|
| `auto` | Automatic |
| `low` | Fastest, least detail |
| `medium` | Balanced |
| `high` | Most detail, slowest |

Quality controls sampling detail, not the output specification. Select only a supported preset or
ratio with `size`.

## Response

```json
{
  "created": 1714444800,
  "data": [
    {
      "b64_json": "..."
    }
  ]
}
```

The scripts decode every `data[]` item to PNG and also accept `data[].url` for compatibility.
Live testing found that the gateway may ignore `n > 1` and return one image. The generation script
automatically makes follow-up requests until it has saved the requested number of images.

## Errors

| Status | Meaning | Retry |
|---|---|---|
| `400` | Policy block or invalid parameters | No |
| `401` | Invalid/expired API key | No |
| `429` | Rate limit | Yes |
| `500` | Upstream failure | Yes |

Policy-blocked HTTP 400 requests are documented as not charged.
