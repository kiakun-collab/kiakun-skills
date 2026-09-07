from __future__ import annotations

import math
import os
import time
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter

Coordinate = tuple[float, float]


class AMapConfigError(RuntimeError):
    """Raised when the Web Service key is unavailable."""


class AMapAPIError(RuntimeError):
    """Raised for transport errors or an AMap status=0 response."""

    def __init__(self, message: str, *, info_code: str | None = None):
        super().__init__(message)
        self.info_code = info_code


def load_env_file(path: str | Path, *, override: bool = False) -> None:
    """Load a small KEY=VALUE file without adding a dotenv dependency."""
    env_path = Path(path)
    if not env_path.is_file():
        raise AMapConfigError(f"Environment file does not exist: {env_path}")
    for raw in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and (override or key not in os.environ):
            os.environ[key] = value


def resolve_api_key(api_key: str | None = None) -> str:
    key = (api_key or os.getenv("AMAP_WEBSERVICE_KEY", "")).strip()
    if not key:
        raise AMapConfigError("AMAP_WEBSERVICE_KEY is missing. Configure an AMap Web Service key.")
    return key


def normalize_coordinate(value: Sequence[float]) -> Coordinate:
    if len(value) != 2:
        raise ValueError("Coordinate must be (longitude, latitude)")
    lon, lat = float(value[0]), float(value[1])
    if not -180 <= lon <= 180 or not -90 <= lat <= 90:
        raise ValueError(f"Coordinate is out of range: {lon},{lat}")
    return lon, lat


def parse_coordinate(value: str) -> Coordinate:
    parts = value.split(",")
    if len(parts) != 2:
        raise ValueError("Coordinate must use longitude,latitude format")
    return normalize_coordinate((float(parts[0]), float(parts[1])))


def format_coordinate(value: Sequence[float], precision: int = 6) -> str:
    lon, lat = normalize_coordinate(value)
    return f"{lon:.{precision}f},{lat:.{precision}f}"


def haversine_m(a: Sequence[float], b: Sequence[float]) -> float:
    lon1, lat1 = map(math.radians, normalize_coordinate(a))
    lon2, lat2 = map(math.radians, normalize_coordinate(b))
    dlon, dlat = lon2 - lon1, lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6_371_000 * 2 * math.asin(math.sqrt(h))


def mercator_pixel(lon: float, lat: float, zoom: int) -> Coordinate:
    lon, lat = normalize_coordinate((lon, lat))
    if zoom < 0:
        raise ValueError("zoom cannot be negative")
    scale = 256 * (2**zoom)
    x = (lon + 180.0) / 360.0 * scale
    sin_y = min(max(math.sin(math.radians(lat)), -0.9999), 0.9999)
    y = (0.5 - math.log((1 + sin_y) / (1 - sin_y)) / (4 * math.pi)) * scale
    return x, y


def geo_to_image_pixel(
    point: Sequence[float],
    center: Sequence[float],
    zoom: int,
    width: int,
    height: int,
    *,
    scale: int = 1,
) -> Coordinate:
    point_x, point_y = mercator_pixel(*normalize_coordinate(point), zoom)
    center_x, center_y = mercator_pixel(*normalize_coordinate(center), zoom)
    return (
        width / 2 + (point_x - center_x) * scale,
        height / 2 + (point_y - center_y) * scale,
    )


class AMapClient:
    BASE_URL = "https://restapi.amap.com"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        timeout: float = 30,
        retries: int = 2,
        retry_backoff: float = 0.5,
        session: requests.Session | None = None,
    ) -> None:
        self.api_key = resolve_api_key(api_key)
        self.timeout = timeout
        self.retries = max(0, retries)
        self.retry_backoff = max(0.0, retry_backoff)
        self.session = session or requests.Session()
        self.session.mount("https://", HTTPAdapter(pool_connections=10, pool_maxsize=10))

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> AMapClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _validate_payload(payload: dict[str, Any]) -> None:
        if str(payload.get("status", "")) != "1":
            info = str(payload.get("info") or "Unknown AMap error")
            info_code = str(payload.get("infocode") or "") or None
            suffix = f" (infocode={info_code})" if info_code else ""
            raise AMapAPIError(
                f"AMap API rejected the request: {info}{suffix}", info_code=info_code
            )

    def _request(
        self,
        path: str,
        params: dict[str, Any],
        *,
        expect_json: bool = True,
        timeout: float | None = None,
    ) -> dict[str, Any] | bytes:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.get(
                    f"{self.BASE_URL}{path}",
                    params={"key": self.api_key, **params},
                    timeout=timeout or self.timeout,
                )
                response.raise_for_status()
                if expect_json:
                    payload = response.json()
                    self._validate_payload(payload)
                    return payload
                if response.headers.get("Content-Type", "").startswith("image/"):
                    return response.content
                payload = response.json()
                self._validate_payload(payload)
                raise AMapAPIError("Static-map endpoint did not return an image")
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt == self.retries:
                    break
                time.sleep(self.retry_backoff * (2**attempt))
        raise AMapAPIError(f"AMap request failed: {last_error}") from last_error

    def place_text(
        self,
        keywords: str,
        *,
        city: str | None = None,
        types: str | None = None,
        city_limit: bool = False,
        page: int = 1,
        page_size: int = 20,
        extensions: str = "base",
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "keywords": keywords,
            "page": max(page, 1),
            "offset": min(max(page_size, 1), 25),
            "extensions": extensions,
        }
        if city:
            params["city"] = city
        if types:
            params["types"] = types
        if city_limit:
            params["citylimit"] = "true"
        payload = self._request("/v3/place/text", params)
        assert isinstance(payload, dict)
        return payload.get("pois", [])

    def iter_place_text(
        self,
        keywords: str,
        *,
        max_pages: int = 20,
        **kwargs: Any,
    ) -> Iterator[dict[str, Any]]:
        for page in range(1, max(1, max_pages) + 1):
            pois = self.place_text(keywords, page=page, page_size=25, **kwargs)
            if not pois:
                break
            yield from pois
            if len(pois) < 25:
                break

    def reverse_geocode(
        self,
        location: Coordinate,
        *,
        radius: int = 100,
        extensions: str = "base",
        road_level: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "location": format_coordinate(location),
            "radius": min(max(radius, 0), 3000),
            "extensions": extensions,
        }
        if road_level is not None:
            params["roadlevel"] = road_level
        payload = self._request("/v3/geocode/regeo", params)
        assert isinstance(payload, dict)
        return payload.get("regeocode", {})

    def walking(self, origin: Coordinate, destination: Coordinate) -> dict[str, Any]:
        payload = self._request(
            "/v3/direction/walking",
            {
                "origin": format_coordinate(origin),
                "destination": format_coordinate(destination),
            },
        )
        assert isinstance(payload, dict)
        paths = payload.get("route", {}).get("paths", [])
        return {"available": bool(paths), "path": paths[0] if paths else None}

    def transit(
        self,
        origin: Coordinate,
        destination: Coordinate,
        *,
        city: str,
        destination_city: str | None = None,
        strategy: int = 0,
        night_flag: bool = False,
        extensions: str = "base",
    ) -> dict[str, Any]:
        payload = self._request(
            "/v3/direction/transit/integrated",
            {
                "origin": format_coordinate(origin),
                "destination": format_coordinate(destination),
                "city": city,
                "cityd": destination_city or city,
                "strategy": strategy,
                "nightflag": 1 if night_flag else 0,
                "extensions": extensions,
            },
        )
        assert isinstance(payload, dict)
        routes = payload.get("route", {}).get("transits", [])
        return {"available": bool(routes), "route": routes[0] if routes else None}

    def static_map(
        self,
        *,
        location: Coordinate | None = None,
        zoom: int | None = None,
        size: tuple[int, int] = (750, 500),
        scale: int = 1,
        traffic: bool = False,
        markers: str | None = None,
        paths: str | None = None,
        labels: str | None = None,
    ) -> bytes:
        width, height = size
        params: dict[str, Any] = {
            "size": f"{width}*{height}",
            "scale": scale,
            "traffic": 1 if traffic else 0,
        }
        if location is not None:
            params["location"] = format_coordinate(location)
        if zoom is not None:
            params["zoom"] = zoom
        if markers:
            params["markers"] = markers
        if paths:
            params["paths"] = paths
        if labels:
            params["labels"] = labels
        result = self._request(
            "/v3/staticmap", params, expect_json=False, timeout=max(self.timeout, 60)
        )
        assert isinstance(result, bytes)
        return result

    def save_static_map(self, output: str | Path, **kwargs: Any) -> Path:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(self.static_map(**kwargs))
        return output_path
