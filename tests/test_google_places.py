import csv
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from modules.google_places import save_business_report, search_businesses_without_websites


class GooglePlacesTests(unittest.TestCase):
    @patch("modules.google_places.requests.post")
    def test_search_filters_places_with_websites(self, post):
        response = Mock()
        response.json.return_value = {
            "places": [
                {"id": "with-site", "displayName": {"text": "Has Site"}, "websiteUri": "https://example.com"},
                {"id": "without-site", "displayName": {"text": "Needs Site"}, "formattedAddress": "Main Street"},
            ]
        }
        response.raise_for_status.return_value = None
        post.return_value = response

        results = search_businesses_without_websites("restaurants in Benin City", api_key="test-key")

        self.assertEqual([result["name"] for result in results], ["Needs Site"])
        post.assert_called_once()

    def test_save_report_writes_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            path = save_business_report([{"id": "1", "name": "Needs Site", "address": "Main Street"}], directory)
            self.assertTrue(os.path.exists(path))
            with open(path, newline="", encoding="utf-8") as report:
                rows = list(csv.DictReader(report))
            self.assertEqual(rows[0]["name"], "Needs Site")


if __name__ == "__main__":
    unittest.main()
