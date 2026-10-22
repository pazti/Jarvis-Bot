import csv
import os
from datetime import datetime
from pathlib import Path

import requests


PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.nationalPhoneNumber",
        "places.websiteUri",
        "places.googleMapsUri",
        "places.rating",
        "places.types",
    ]
)


def _get_api_key(api_key=None):
    return api_key or os.getenv("GOOGLE_MAPS_API_KEY")


def search_businesses_without_websites(query, api_key=None, max_pages=5, page_size=20, timeout=30):
    """Search Google Places Text Search and return only places without websiteUri."""
    key = _get_api_key(api_key)
    if not key:
        raise RuntimeError("GOOGLE_MAPS_API_KEY is not configured.")
    if not query or not query.strip():
        raise ValueError("A business category and geographic area are required.")

    headers = {"X-Goog-Api-Key": key, "X-Goog-FieldMask": FIELD_MASK}
    payload = {"textQuery": query.strip(), "pageSize": max(1, min(page_size, 20))}
    results = []
    seen_ids = set()

    for _ in range(max(1, max_pages)):
        response = requests.post(PLACES_SEARCH_URL, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        for place in data.get("places", []):
            place_id = place.get("id")
            if place_id in seen_ids or place.get("websiteUri"):
                continue
            seen_ids.add(place_id)
            results.append(
                {
                    "id": place_id or "",
                    "name": (place.get("displayName") or {}).get("text", ""),
                    "address": place.get("formattedAddress", ""),
                    "phone": place.get("nationalPhoneNumber", ""),
                    "maps_url": place.get("googleMapsUri", ""),
                    "rating": place.get("rating", ""),
                    "types": ", ".join(place.get("types", [])),
                    "website": "",
                }
            )
        token = data.get("nextPageToken")
        if not token:
            break
        payload = {"pageToken": token, "pageSize": payload["pageSize"]}

    return results


def save_business_report(businesses, output_dir=None):
    """Save business results as a timestamped CSV and return its path."""
    target_dir = Path(output_dir or Path(__file__).resolve().parent.parent / "reports")
    target_dir.mkdir(parents=True, exist_ok=True)
    output_path = target_dir / f"businesses_without_websites_{datetime.now():%Y%m%d_%H%M%S}.csv"
    fields = ["id", "name", "address", "phone", "maps_url", "rating", "types", "website"]
    with output_path.open("w", newline="", encoding="utf-8") as report:
        writer = csv.DictWriter(report, fieldnames=fields)
        writer.writeheader()
        writer.writerows(businesses)
    return output_path


__all__ = ["save_business_report", "search_businesses_without_websites"]
