from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from amap_client import (
    AMapAPIError,
    AMapClient,
    format_coordinate,
    geo_to_image_pixel,
    haversine_m,
    parse_coordinate,
)


class AMapClientTests(unittest.TestCase):
    def test_coordinate_round_trip(self):
        value = parse_coordinate("116.397428,39.909230")
        self.assertEqual(format_coordinate(value), "116.397428,39.909230")

    def test_haversine_same_point(self):
        self.assertEqual(haversine_m((116.3, 39.9), (116.3, 39.9)), 0)

    def test_center_projects_to_image_center(self):
        point = (116.397428, 39.90923)
        self.assertEqual(
            geo_to_image_pixel(point, point, 12, 750, 500),
            (375, 250),
        )

    def test_api_error_preserves_infocode(self):
        with self.assertRaises(AMapAPIError) as raised:
            AMapClient._validate_payload(
                {"status": "0", "info": "INVALID_USER_KEY", "infocode": "10001"}
            )
        self.assertEqual(raised.exception.info_code, "10001")


if __name__ == "__main__":
    unittest.main()
