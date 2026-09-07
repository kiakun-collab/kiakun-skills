# AMap Web Service usage reference

Load this reference only when basic CLI examples are insufficient.

## Operations and endpoints

| CLI command | Endpoint | Primary result |
|---|---|---|
| `place` | `/v3/place/text` | `pois[]` |
| `regeo` | `/v3/geocode/regeo` | `regeocode` |
| `walking` | `/v3/direction/walking` | first `route.paths[]` entry |
| `transit` | `/v3/direction/transit/integrated` | first `route.transits[]` entry |
| `static-map` | `/v3/staticmap` | image bytes |

The client validates HTTP status and AMap's JSON `status`. When AMap returns `status=0`, report both `info` and `infocode`; do not treat an empty result as success unless the endpoint explicitly supports it.

## POI search

- `--city` accepts a city name, city code, or adcode supported by AMap.
- Add `--city-limit` when results must remain inside that city.
- Use `--types` with AMap POI type codes to reduce ambiguity.
- A page is capped at 25 results by the client. `--pages` controls the maximum number fetched.
- Deduplicate downstream by stable POI `id` when combining searches.

## Route payloads

`walking` returns an `available` flag and the first `route.paths[]` entry. `transit` uses the same availability wrapper and returns the first `route.transits[]` entry. Transit results may contain bus, metro, railway, walking, taxi, or other segments; do not label every segment as metro without checking its fields.

## Static-map overlays

The CLI passes `--markers`, `--paths`, and `--labels` through to AMap. Compose these values according to the current AMap static-map syntax. They may contain multiple items separated with `|`; quote the whole shell argument.

Use `--location` plus `--zoom` for a fixed viewport. AMap may infer a viewport from overlays when location or zoom is omitted. `--scale 2` requests high-density output; use the same scale with `geo_to_image_pixel` when drawing overlays locally.

## Coordinate helpers

Import helpers from `scripts/amap_client.py` when processing results in Python:

```python
from amap_client import geo_to_image_pixel, haversine_m, parse_coordinate
```

These helpers validate coordinates, calculate approximate great-circle distance, and project a GCJ-02 coordinate into a static-map frame. They do not convert coordinate systems.

## Troubleshooting

- `AMapConfigError`: the Web Service key is missing or the requested env file does not exist.
- `AMapAPIError` with `infocode`: consult current AMap error-code documentation and verify key type, service enablement, quota, signature rules, and IP restrictions.
- Static-map JSON response: AMap returned an error payload instead of image bytes; the client surfaces this rather than saving invalid image data.
- Empty POIs or unavailable route: narrow or correct search terms, city/type filters, coordinate order, and city codes before retrying broadly.
