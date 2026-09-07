from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from amap_client import AMapAPIError, AMapClient, AMapConfigError, load_env_file, parse_coordinate


def emit(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="AMap Web Service CLI")
    root.add_argument("--env-file", type=Path, help="Optional KEY=VALUE file")
    sub = root.add_subparsers(dest="command", required=True)

    place = sub.add_parser("place", help="Search POIs by keyword")
    place.add_argument("keywords")
    place.add_argument("--city")
    place.add_argument("--types")
    place.add_argument("--city-limit", action="store_true")
    place.add_argument("--pages", type=int, default=1)

    regeo = sub.add_parser("regeo", help="Reverse geocode a coordinate")
    regeo.add_argument("location", type=parse_coordinate)
    regeo.add_argument("--radius", type=int, default=100)
    regeo.add_argument("--extensions", choices=("base", "all"), default="base")

    walking = sub.add_parser("walking", help="Plan a walking route")
    walking.add_argument("origin", type=parse_coordinate)
    walking.add_argument("destination", type=parse_coordinate)

    transit = sub.add_parser("transit", help="Plan a public-transit route")
    transit.add_argument("origin", type=parse_coordinate)
    transit.add_argument("destination", type=parse_coordinate)
    transit.add_argument("--city", required=True, help="City name, code, or adcode")
    transit.add_argument("--destination-city")
    transit.add_argument("--strategy", type=int, default=0)
    transit.add_argument("--night", action="store_true")

    static_map = sub.add_parser("static-map", help="Download a static map")
    static_map.add_argument("output", type=Path)
    static_map.add_argument("--location", type=parse_coordinate)
    static_map.add_argument("--zoom", type=int)
    static_map.add_argument("--width", type=int, default=750)
    static_map.add_argument("--height", type=int, default=500)
    static_map.add_argument("--scale", type=int, choices=(1, 2), default=1)
    static_map.add_argument("--traffic", action="store_true")
    static_map.add_argument("--markers")
    static_map.add_argument("--paths")
    static_map.add_argument("--labels")
    return root


def run(args: argparse.Namespace) -> Any:
    if args.env_file:
        load_env_file(args.env_file)
    with AMapClient() as client:
        if args.command == "place":
            return {
                "pois": list(
                    client.iter_place_text(
                        args.keywords,
                        city=args.city,
                        types=args.types,
                        city_limit=args.city_limit,
                        max_pages=args.pages,
                    )
                )
            }
        if args.command == "regeo":
            return {
                "regeocode": client.reverse_geocode(
                    args.location,
                    radius=args.radius,
                    extensions=args.extensions,
                )
            }
        if args.command == "walking":
            return {"walking": client.walking(args.origin, args.destination)}
        if args.command == "transit":
            return {
                "transit": client.transit(
                    args.origin,
                    args.destination,
                    city=args.city,
                    destination_city=args.destination_city,
                    strategy=args.strategy,
                    night_flag=args.night,
                )
            }
        if args.command == "static-map":
            output = client.save_static_map(
                args.output,
                location=args.location,
                zoom=args.zoom,
                size=(args.width, args.height),
                scale=args.scale,
                traffic=args.traffic,
                markers=args.markers,
                paths=args.paths,
                labels=args.labels,
            )
            return {"output": str(output.resolve()), "bytes": output.stat().st_size}
    raise AssertionError(f"Unhandled command: {args.command}")


def main() -> int:
    try:
        emit(run(parser().parse_args()))
        return 0
    except (AMapAPIError, AMapConfigError, ValueError) as exc:
        emit(
            {
                "error": type(exc).__name__,
                "message": str(exc),
                "infocode": getattr(exc, "info_code", None),
            }
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
