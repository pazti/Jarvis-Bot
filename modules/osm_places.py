import csv
import os
from datetime import datetime
from pathlib import Path

import requests

# Overpass API endpoint
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def search_businesses_without_websites(query, area_name=None, timeout=60):
    """
    Search OpenStreetMap via Overpass API for businesses without websites.
    """
    if not query or not query.strip():
        raise ValueError("A business category (query) is required.")
    if not area_name or not area_name.strip():
        raise ValueError("A geographic area is required for OSM searches.")
    
    # Basic mapping to handle plurals and common terms
    mapping = {
        "restaurants": "restaurant",
        "dentists": "dentist",
        "plumbers": "plumber",
        "hotels": "hotel",
        "cafes": "cafe",
        "pharmacies": "pharmacy",
        "bakery": "bakery",
        "salons": "hairdresser",
    }
    search_term = mapping.get(query.lower(), query.lower())

    overpass_query = f"""
    [out:json][timeout:25];
    area["name"="{area_name}"]->.searchArea;
    (
      node["amenity"="{search_term}"](area.searchArea);
      way["amenity"="{search_term}"](area.searchArea);
      node["shop"="{search_term}"](area.searchArea);
      way["shop"="{search_term}"](area.searchArea);
      node["craft"="{search_term}"](area.searchArea);
      way["craft"="{search_term}"](area.searchArea);
    );
    node(r);
    way(r);
    out center;
    """

    try:
        response = requests.post(OVERPASS_URL, data={"data": overpass_query}, timeout=timeout)
        response.raise_for_status()
        data = response.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Error querying Overpass API: {e}")
        return []

    results = []
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        
        # Filter: Only include if there is NO website tag
        if "website" in tags:
            continue
            
        # Extract basic info
        name = tags.get("name", "Unknown Name")
        address = tags.get("addr:full") or \
                  f"{tags.get('addr:street', '')} {tags.get('addr:housenumber', '')}, {tags.get('addr:city', '')}".strip()
        phone = tags.get("phone") or tags.get("contact:phone", "")
        
        # Create a link to OSM for reference
        osm_id = element.get("id")
        osm_url = f"https://www.openstreetmap.org/{'way' if element.get('type') == 'way' else 'node'}/{osm_id}"

        results.append({
            "id": str(osm_id),
            "name": name,
            "address": address or "No address listed",
            "phone": phone,
            "maps_url": osm_url,
            "rating": "N/A", # OSM doesn't provide ratings
            "types": tags.get("amenity") or tags.get("shop") or tags.get("craft") or "business",
            "website": "",
        })

    return results


def save_business_report(businesses, output_dir=None):
    """Save business results as a timestamped CSV and return its path."""
    target_dir = Path(output_dir or Path(__file__).resolve().parent.parent / "reports")
    target_dir.mkdir(parents=True, exist_ok=True)
    output_path = target_dir / f"osm_businesses_without_websites_{datetime.now():%Y%m%d_%H%M%S}.csv"
    fields = ["id", "name", "address", "phone", "maps_url", "rating", "types", "website"]
    with output_path.open("w", newline="", encoding="utf-8") as report:
        writer = csv.DictWriter(report, fieldnames=fields)
        writer.writeheader()
        writer.writerows(businesses)
    return output_path


__all__ = ["save_business_report", "search_businesses_without_websites"]
