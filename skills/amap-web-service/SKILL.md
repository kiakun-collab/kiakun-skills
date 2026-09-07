---
name: amap-web-service
description: Query AMap (Gaode) Web Service for POI search, reverse geocoding, walking or public-transit routing, and static-map downloads. Use when a task needs current AMap data, GCJ-02 coordinates, route estimates, or a map image; do not use it for browser-side AMap JS SDK integration.
---

# AMap Web Service

Use this skill to obtain structured results from AMap's server-side Web Service API. Run the bundled CLI instead of rebuilding request and error-handling logic.

## Configuration

The CLI reads the Web Service key from `AMAP_WEBSERVICE_KEY`. If the user provides a local environment file, pass it with `--env-file`; never print, log, commit, or embed the key in generated URLs or source files.

```powershell
python scripts/amap_cli.py --env-file .env regeo "116.397428,39.909230"
```

If no key is available, ask the user to configure a **Web Service Key** from the AMap Open Platform. Do not substitute a Web JS API key.

## Workflow

1. Identify the needed operation and required parameters.
2. Keep all coordinates in `longitude,latitude` order and treat AMap coordinates as GCJ-02.
3. Run one of the CLI commands below. Add `--env-file <path>` before the subcommand when needed.
4. Parse the returned JSON. Preserve AMap's factual fields and distinguish API results from interpretation.
5. For route estimates or POI availability, mention the query date when the result will be used operationally.

```powershell
python scripts/amap_cli.py place "地铁站" --city "上海" --types 150500 --city-limit --pages 2
python scripts/amap_cli.py regeo "121.473701,31.230416" --extensions all
python scripts/amap_cli.py walking "121.473701,31.230416" "121.481000,31.233000"
python scripts/amap_cli.py transit "121.473701,31.230416" "121.499700,31.239700" --city "上海"
python scripts/amap_cli.py static-map output.png --location "121.473701,31.230416" --zoom 12 --scale 2
```

Use `--help` on the main command or a subcommand for all parameters. Read [references/api-usage.md](references/api-usage.md) only when composing static-map overlays, paginating large POI searches, interpreting route payloads, or troubleshooting an AMap `infocode`.

## Operational Constraints

- A successful HTTP response is not sufficient; require AMap JSON `status` to equal `1`.
- Do not silently convert WGS84, BD-09, or another coordinate system to GCJ-02. Confirm or perform an explicit conversion outside this skill when necessary.
- Treat route duration and distance as query-time estimates, not guarantees.
- Keep POI pagination bounded. Start with the fewest pages needed and narrow by `city`, `types`, and `city-limit` where possible.
- For static maps, use the image bytes returned by the endpoint; if the endpoint returns JSON instead of an image, surface the AMap error.
- Do not infer venue access, operating hours, permissions, or event feasibility from map presence alone.

## Bundled Scripts

- `scripts/amap_cli.py`: command-line interface that emits JSON and downloads static maps.
- `scripts/amap_client.py`: reusable Python client, coordinate validation, distance calculation, and Web Mercator helpers.
