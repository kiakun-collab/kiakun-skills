# GPT Image 2 API Reference

Source: `https://9nnc8eo3c5.apifox.cn/8671595m0.md` (updated 2026-04-30).

## Models

| Model | Use | Resolution | Quality parameter |
|---|---|---|---|
| `gpt-image-2` | Default daily generation and ordinary single-reference edits | Up to 1K | Not effective; omit it |
| `gpt-image-2-vip` | Complex/high-precision work, multiple references, 2K/4K | 1K/2K/4K | `auto`, `low`, `medium`, `high` |

## Routes

| Operation | Method | Path | Body |
|---|---|---|---|
| Text-to-image | POST | `/v1/images/generations` | JSON |
| Local reference edit | POST | `/v1/images/edits` | multipart form |
| Public URL reference edit | POST | `/v1/images/edits` | JSON |

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
| `size` | string | No | Pixel dimensions or a supported ratio |
| `quality` | string | No | VIP only |
| `response_format` | string | No | Always use `b64_json` |

## Edit Parameters

| Parameter | Type | Required | Rules |
|---|---|---|---|
| `model` | string | Yes | Standard or VIP |
| `prompt` | string | Yes | Edit instruction |
| `image` | file | For multipart | PNG, JPEG, or WebP; repeatable |
| `urls` | string[] | For JSON | Publicly accessible URLs; gateway extension |
| `size` | string | No | Pixel dimensions or ratio |
| `quality` | string | No | VIP only |

## Standard Sizes

Use these with `gpt-image-2`:

| Size | Ratio / purpose |
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

## VIP 2K / 4K Sizes

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

Use explicit 2K/4K pixel values for VIP. A live gateway test observed `1024x1024` being converted to `1:1` and rejected by the VIP upstream.

## Quality

VIP only:

| Value | Meaning |
|---|---|
| `auto` | Automatic |
| `low` | Fastest, least detail |
| `medium` | Balanced |
| `high` | Most detail, slowest |

Quality controls sampling detail, not resolution. Select resolution with `size`.

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

## Errors

| Status | Meaning | Retry |
|---|---|---|
| `400` | Policy block or invalid parameters | No |
| `401` | Invalid/expired API key | No |
| `429` | Rate limit | Yes |
| `500` | Upstream failure | Yes |

Policy-blocked HTTP 400 requests are documented as not charged.
