"""DuckDuckGo search-result collection and Markdown report writing."""

import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests


_SEARCH_URL = "https://html.duckduckgo.com/html/"
_MAX_QUERIES = 4
_RESULTS_PER_QUERY = 5
_MAX_RESULTS = 12


class DuckDuckGoResultsParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.results = []
        self._current = None
        self._result_depth = 0
        self._snippet_depth = None
        self._collecting_title = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set(attributes.get("class", "").split())

        if tag == "div" and self._current is None and "result" in classes:
            self._current = {"title": "", "url": "", "snippet": ""}
            self._result_depth = 1
        elif self._current is not None and tag == "div":
            self._result_depth += 1
            if "result__snippet" in classes:
                self._snippet_depth = self._result_depth

        if self._current is not None and tag == "a" and "result__a" in classes:
            self._current["url"] = self._resolve_url(attributes.get("href", ""))
            self._collecting_title = True

    def handle_endtag(self, tag):
        if tag == "a":
            self._collecting_title = False

        if tag == "div" and self._current is not None:
            if self._snippet_depth == self._result_depth:
                self._snippet_depth = None
            self._result_depth -= 1
            if self._result_depth == 0:
                if self._current["title"] and self._current["url"]:
                    self.results.append(self._current)
                self._current = None

    def handle_data(self, data):
        if self._current is None:
            return
        if self._collecting_title:
            self._current["title"] += data
        elif self._snippet_depth is not None:
            self._current["snippet"] += data

    @staticmethod
    def _resolve_url(href):
        if href.startswith("//"):
            href = f"https:{href}"
        parsed = urlparse(href)
        if parsed.hostname and parsed.hostname.endswith("duckduckgo.com"):
            target = parse_qs(parsed.query).get("uddg", [""])[0]
            href = target
            parsed = urlparse(href)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ""
        return href


def _clean_text(value):
    return " ".join(value.split()).strip()


def _escape_markdown(value):
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", value)


def _report_filename(query, now=None):
    slug = re.sub(r"[^a-z0-9]+", "-", query.casefold()).strip("-")[:60] or "web-research"
    timestamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%d-%H%M%S-%f")
    return f"{timestamp}-{slug}.md"


def search_duckduckgo(queries, output_dir=None):
    """Search DuckDuckGo for up to four queries and save a source-linked report."""
    if isinstance(queries, str):
        queries = [queries]
    if not isinstance(queries, (list, tuple)):
        raise ValueError("Search queries must be a string or a list of strings.")

    cleaned_queries = []
    for query in queries:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Each search query must be a non-empty string.")
        cleaned = _clean_text(query)
        if cleaned not in cleaned_queries:
            cleaned_queries.append(cleaned)
    if not cleaned_queries:
        raise ValueError("At least one search query is required.")
    if len(cleaned_queries) > _MAX_QUERIES:
        raise ValueError(f"Use no more than {_MAX_QUERIES} related search queries.")

    results = []
    seen_urls = set()
    failures = []
    for query in cleaned_queries:
        try:
            response = requests.get(
                _SEARCH_URL,
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0 (compatible; JarvisResearch/1.0)"},
                timeout=(5, 15),
            )
            response.raise_for_status()
        except requests.RequestException as error:
            failures.append(f"{query}: {error}")
            continue

        parser = DuckDuckGoResultsParser()
        parser.feed(response.text)
        for item in parser.results[:_RESULTS_PER_QUERY]:
            if item["url"] in seen_urls:
                continue
            seen_urls.add(item["url"])
            results.append(
                {
                    "query": query,
                    "title": _clean_text(item["title"]),
                    "url": item["url"],
                    "snippet": _clean_text(item["snippet"]),
                }
            )
            if len(results) >= _MAX_RESULTS:
                break
        if len(results) >= _MAX_RESULTS:
            break

    if failures and not results:
        raise RuntimeError("DuckDuckGo search failed: " + "; ".join(failures))

    report_dir = Path(output_dir) if output_dir else Path(__file__).resolve().parent.parent / "research"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / _report_filename(cleaned_queries[0])
    report_lines = [
        "# Web research",
        "",
        f"Created: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Search queries",
        "",
    ]
    report_lines.extend(f"- {_escape_markdown(query)}" for query in cleaned_queries)
    report_lines.extend(
        [
            "",
            "## Results",
            "",
            "These are DuckDuckGo search-result titles and snippets, not full-page verification.",
            "",
        ]
    )
    if results:
        for index, item in enumerate(results, start=1):
            report_lines.extend(
                [
                    f"### {index}. {_escape_markdown(item['title'])}",
                    "",
                    f"- Search: {_escape_markdown(item['query'])}",
                    f"- Source: <{item['url']}>",
                    f"- Snippet: {_escape_markdown(item['snippet']) or '(No snippet provided)'}",
                    "",
                ]
            )
    else:
        report_lines.append("DuckDuckGo returned no parseable results for these queries.")
        report_lines.append("")

    if failures:
        report_lines.extend(["## Search warnings", ""])
        report_lines.extend(f"- {_escape_markdown(failure)}" for failure in failures)
        report_lines.append("")

    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    return {
        "queries": cleaned_queries,
        "results": results,
        "failures": failures,
        "report_path": report_path,
    }
