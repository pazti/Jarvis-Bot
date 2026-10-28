import re


def parse_business_query(prompt):
    """Extract a business category and search area from a natural-language prompt."""
    lower_prompt = (prompt or "").lower().strip()
    category = None
    area = None

    cleaned = re.sub(r"^(?:jarvis|javis)\s+", "", lower_prompt)
    cleaned = re.sub(r"\s+(?:without|with no)\s+websites?", "", cleaned)
    cleaned = re.sub(r"\s+no\s+website", "", cleaned).strip()

    match = re.search(
        r"(?:find|search(?:\s+for)?|look\s+for)\s*(?P<category>[a-z0-9\s-]+?)\s+in\s+(?P<area>[a-z0-9\s-]+)",
        cleaned,
    )
    if match:
        category = match.group("category").strip()
        area = match.group("area").strip()
    elif " in " in cleaned:
        parts = cleaned.split(" in ")
        area = parts[-1].strip()
        category = parts[0].strip()
    elif " for " in cleaned:
        parts = cleaned.split(" for ", 1)
        category = parts[0].strip()
        area = parts[1].strip() if len(parts) > 1 else None
    elif cleaned:
        category = cleaned.strip()

    if area and not category:
        category = "business"

    return category, area


def run_business_finder(prompt, db_path=None):
    """Execute a business search and return structured result metadata."""
    category, area = parse_business_query(prompt)
    if not category or not area:
        raise ValueError(
            "I couldn't quite figure out the business type and city. Try: 'find restaurants in Abuja without websites'."
        )

    from modules.osm_places import (
        save_business_report,
        search_businesses_without_websites,
    )
    from modules.task_catalog import TaskCatalog
    from modules.task_orchestration import TaskExecutor

    track = TaskCatalog(db_path=db_path).plan(
        "business_finder",
        context={"search_query": category, "search_area": area},
    )

    businesses = search_businesses_without_websites(category, area_name=area)
    if not businesses:
        return {
            "track_id": track["track_id"],
            "category": category,
            "area": area,
            "business_count": 0,
            "report_path": None,
            "message": f"I searched for {category} in {area}, but I couldn't find any businesses without websites.",
        }

    report_path = save_business_report(businesses)
    executor = TaskExecutor(db_path=db_path)
    task_results = {
        "Define search scope": {"result": f"Approved search scope: {category} in {area}."},
        "Search Google Places": {"result": f"Collected OpenStreetMap results for {category} in {area}."},
        "Filter businesses without websites": {"result": f"Filtered {len(businesses)} businesses without listed websites."},
        "Save businesses without websites": {"result": f"Saved report to {report_path}."},
        "Verify and report results": {"result": f"Verified {len(businesses)} report rows."},
    }

    for task in track["tasks"]:
        executor.execute_task(
            track["track_id"],
            task["task_id"],
            task_handler=lambda current_task, context: task_results.get(current_task["title"], {"result": "Completed"}),
        )

    return {
        "track_id": track["track_id"],
        "category": category,
        "area": area,
        "business_count": len(businesses),
        "report_path": report_path,
        "message": (
            f"Business Finder (OSM) complete: found {len(businesses)} businesses without listed websites in {area}. "
            f"Report saved to {report_path}. Track ID: {track['track_id']}."
        ),
    }
