# GPT Image 2 VIP API Reference

## Endpoints

| Task | Method | Endpoint | Content type |
|---|---|---|---|
| Generate | POST | `/images/generations` | `application/json` |
| Edit local files | POST | `/images/edits` | `multipart/form-data` |
| Edit public URLs | POST | `/images/edits` | `application/json` |

All requests use `Authorization: Bearer <OPENAI_API_KEY>`.

## Generation Body

```json
{
  "model": "gpt-image-2-vip",
  "prompt": "Image description",
  "n": 1,
  "size": "2048x2048",
  "quality": "high",
  "response_format": "b64_json"
}
```

## Edit Fields

- `model`: defaults to `gpt-image-2-vip`
- `prompt`: required
- `image`: repeatable file field for local images
- `urls`: array of public image URLs for JSON requests
- `size`: pixel dimensions
- `quality`: `auto`, `low`, `medium`, or `high`

## Recommended VIP Sizes

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

The aifast.site gateway was observed converting `1024x1024` to `1:1`, which the VIP upstream rejected. Prefer the listed 2K/4K pixel values.

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

The scripts also accept `data[].url` for compatibility.
