import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from modules import osm_places


class OSMPlacesTests(unittest.TestCase):
    @patch("modules.osm_places.requests.post")
    def test_search_businesses_without_websites_filters_results_and_maps_fields(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "elements": [
                {
                    "type": "node",
                    "id": 101,
                    "tags": {
                        "name": "Café Central",
                        "amenity": "cafe",
                        "addr:full": "10 Market St, Example City",
                    },
                },
                {
                    "type": "way",
                    "id": 202,
                    "tags": {
                        "name": "Bakery Corner",
                        "shop": "bakery",
                        "addr:city": "Example City",
                        "website": "https://example.com",
                    },
                },
            ]
        }
        post.return_value = response

        results = osm_places.search_businesses_without_websites("cafes", area_name="Example City")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Café Central")
        self.assertEqual(results[0]["types"], "cafe")
        self.assertIn("openstreetmap.org/node/101", results[0]["maps_url"])

    def test_save_business_report_writes_csv(self):
        businesses = [{
            "id": "1",
            "name": "Shop Name",
            "address": "1 Main St",
            "phone": "555-0100",
            "maps_url": "https://example.com/maps",
            "rating": "N/A",
            "types": "shop",
            "website": "",
        }]

        with tempfile.TemporaryDirectory() as directory:
            output_path = osm_places.save_business_report(businesses, output_dir=directory)
            self.assertTrue(Path(output_path).exists())
            with open(output_path, newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(rows[0]["name"], "Shop Name")
        self.assertEqual(rows[0]["types"], "shop")

    def test_invalid_query_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "business category"):
            osm_places.search_businesses_without_websites("   ", area_name="Example City")


if __name__ == "__main__":
    unittest.main()
