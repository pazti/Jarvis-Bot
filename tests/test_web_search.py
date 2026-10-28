import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from modules.web_search import DuckDuckGoResultsParser, search_duckduckgo


class WebSearchTests(unittest.TestCase):
    def test_parser_extracts_titles_snippets_and_redirect_urls(self):
        parser = DuckDuckGoResultsParser()
        parser.feed(
            """
            <div class="result">
              <div class="result__body">
                <a class="result__a" href="https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.org%2Freport">
                  Study <b>results</b>
                </a>
                <div class="result__snippet">A useful <b>source</b> summary.</div>
              </div>
            </div>
            """
        )

        self.assertEqual(len(parser.results), 1)
        self.assertEqual(parser.results[0]["title"].strip(), "Study results")
        self.assertEqual(parser.results[0]["url"], "https://example.org/report")
        self.assertIn("A useful", parser.results[0]["snippet"])

    @patch("modules.web_search.requests.get")
    def test_related_searches_are_deduplicated_and_saved_to_markdown(self, get):
        html_one = """
        <div class="result">
          <a class="result__a" href="https://example.org/shared">Shared report</a>
          <div class="result__snippet">Shared result snippet.</div>
        </div>
        <div class="result">
          <a class="result__a" href="https://example.org/first">First report</a>
          <div class="result__snippet">First source snippet.</div>
        </div>
        """
        html_two = """
        <div class="result">
          <a class="result__a" href="https://example.org/shared">Shared report</a>
          <div class="result__snippet">Duplicate result snippet.</div>
        </div>
        <div class="result">
          <a class="result__a" href="https://example.org/second">Second report</a>
          <div class="result__snippet">Second source snippet.</div>
        </div>
        """
        get.side_effect = [
            Mock(text=html_one, raise_for_status=Mock()),
            Mock(text=html_two, raise_for_status=Mock()),
        ]
        with tempfile.TemporaryDirectory() as directory:
            result = search_duckduckgo(
                ["urban tree research", "urban tree health studies"],
                output_dir=directory,
            )

            self.assertEqual(len(result["results"]), 3)
            self.assertEqual(len(get.call_args_list), 2)
            self.assertTrue(Path(result["report_path"]).is_file())
            report = Path(result["report_path"]).read_text(encoding="utf-8")
            self.assertIn("urban tree research", report)
            self.assertIn(r"Second source snippet\.", report)
            self.assertEqual(report.count("https://example.org/shared"), 1)

    @patch(
        "modules.web_search.requests.get",
        side_effect=requests.RequestException("network unavailable"),
    )
    def test_all_search_failures_are_reported(self, get):
        with self.assertRaisesRegex(RuntimeError, "network unavailable"):
            search_duckduckgo(["test query"])
        get.assert_called_once()


if __name__ == "__main__":
    unittest.main()
