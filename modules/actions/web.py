import re
import webbrowser
from urllib.parse import quote_plus


def search_web(query, related_queries=None):
    """Collect DuckDuckGo results and save a source-linked Markdown report."""
    try:
        from modules.web_search import search_duckduckgo

        queries = [query]
        if related_queries is not None:
            if not isinstance(related_queries, list):
                raise ValueError("Related search queries must be a list of strings.")
            queries.extend(related_queries)
        report = search_duckduckgo(queries)
        if report["results"]:
            findings = "\n".join(
                f"- {item['title']}: {item['snippet'][:400]} "
                f"(Source: {item['url']})"
                for item in report["results"]
            )
            message = (
                f"Found {len(report['results'])} DuckDuckGo results across "
                f"{len(report['queries'])} searches. Research report saved to "
                f"{report['report_path']}.\n"
                "Search snippets below are unverified source excerpts:\n"
                f"{findings}"
            )
        else:
            message = (
                "DuckDuckGo returned no parseable results. A report with the "
                f"search details was saved to {report['report_path']}."
            )
    except (ValueError, RuntimeError) as error:
        message = f"Web research failed: {error}"
    except OSError as error:
        message = (
            "Web research results were found, but the report could not be saved: "
            f"{error}"
        )
    return message


def open_website(prompt):
    lower = (prompt or "").lower()
    site_map = {
        "youtube": "https://www.youtube.com",
        "github": "https://github.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "docs": "https://docs.google.com",
        "stackoverflow": "https://stackoverflow.com",
        "linkedin": "https://www.linkedin.com",
        "x": "https://x.com",
        "twitter": "https://x.com",
    }
    target = "https://www.google.com"
    for key, url in site_map.items():
        if key in lower:
            target = url
            break

    try:
        webbrowser.open(target)
        return f"Opening {target}."
    except (OSError, webbrowser.Error):
        return "I could not open that website."


def google_maps(prompt):
    """Open Google Maps, search for a place, or show directions."""
    lower = (prompt or "").lower().strip()
    directions_requested = any(
        [
            re.search(r"\b(?:any\s+)?directions?\s+to\b", lower),
            *[phrase in lower for phrase in ["route to", "navigate to", "how do i get to"]],
        ]
    )
    query = re.sub(
        r"(?i)\b(jarvis|javis|chavis|i need|open|launch|go to|show me|search for|find|look up|google maps?|maps|any directions? to|directions? to|route to|navigate to|how do i get to)\b",
        " ",
        prompt or "",
    )
    query = re.sub(r"\s+", " ", query).strip(" .,:;!?\"")

    if directions_requested and query:
        url = f"https://www.google.com/maps/dir/?api=1&destination={quote_plus(query)}"
        message = f"Opening directions to {query}."
    elif query:
        url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"
        message = f"Searching Google Maps for: {query}."
    else:
        url = "https://www.google.com/maps"
        message = "Opening Google Maps."

    try:
        webbrowser.open(url)
    except (OSError, webbrowser.Error):
        return "I could not open Google Maps."
    return message
