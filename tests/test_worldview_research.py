import os
import sqlite3
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from modules import tool_router
from modules import worldview_research
from modules.worldview_research import (
    _finish_cycle,
    _generate_assessment,
    _run_cycle,
    create_research_run,
    get_research_status,
    read_next_book_excerpt,
    stop_research,
)
from modules.worldview import set_worldview_profile_consent


class WorldviewResearchRunTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "memory.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_run_duration_and_interval_are_bounded(self):
        with self.assertRaisesRegex(ValueError, "from 1 to 30 days"):
            create_research_run("What is purpose?", duration_days=31, db_path=self.db_path)
        with self.assertRaisesRegex(ValueError, "from 6 to 168 hours"):
            create_research_run(
                "What is purpose?", duration_days=7, interval_hours=1, db_path=self.db_path
            )

    def test_existing_research_database_migrates_selection_fields(self):
        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute(
                """
                CREATE TABLE worldview_research_runs (
                    run_id TEXT PRIMARY KEY, topic TEXT NOT NULL,
                    duration_days INTEGER NOT NULL, interval_hours INTEGER NOT NULL,
                    started_at TEXT NOT NULL, ends_at TEXT NOT NULL,
                    next_run_at TEXT NOT NULL, status TEXT NOT NULL,
                    cycle_count INTEGER NOT NULL DEFAULT 0,
                    source_index INTEGER NOT NULL DEFAULT 0,
                    source_offset INTEGER NOT NULL DEFAULT 0,
                    latest_assessment TEXT, last_error TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()
        finally:
            connection.close()

        get_research_status(db_path=self.db_path)

        connection = sqlite3.connect(self.db_path)
        try:
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(worldview_research_runs)"
                )
            }
        finally:
            connection.close()
        self.assertIn("purpose", columns)
        self.assertIn("profile_key", columns)

    def test_active_run_is_unique_and_can_be_stopped(self):
        run = create_research_run("What is purpose?", duration_days=7, db_path=self.db_path)

        with self.assertRaisesRegex(ValueError, "already active"):
            create_research_run("Another topic", db_path=self.db_path)

        stopped = stop_research(db_path=self.db_path)

        self.assertEqual(stopped["run_id"], run["run_id"])
        self.assertEqual(get_research_status(db_path=self.db_path)["status"], "STOPPED")

    def test_cycle_saves_assessment_and_book_cursor(self):
        run = create_research_run("What is purpose?", duration_days=7, db_path=self.db_path)
        run.update(source_index=1, source_offset=12000)
        book = {"path": "worldview_sources/book.txt", "excerpt": "An excerpt."}

        _finish_cycle(
            run,
            1,
            ["purpose comparison"],
            [{"title": "A source", "url": "https://example.org", "snippet": "Summary"}],
            book,
            "A provisional analytical conclusion.",
            None,
            self.db_path,
        )
        status = get_research_status(db_path=self.db_path)

        self.assertEqual(status["cycle_count"], 1)
        self.assertEqual(status["source_index"], 1)
        self.assertEqual(status["source_offset"], 12000)
        self.assertIn("provisional analytical conclusion", status["latest_assessment"])
        self.assertEqual(status["recent_cycles"][0]["book_path"], book["path"])

    def test_selection_cycle_saves_profile_position_and_history(self):
        from modules.worldview import get_worldview_position, get_worldview_position_history

        set_worldview_profile_consent("Morgan", True, db_path=self.db_path)
        run = create_research_run(
            "Compare religious and nonreligious worldviews",
            duration_days=7,
            db_path=self.db_path,
            purpose="selection",
            profile_key="Morgan",
        )

        _finish_cycle(
            run,
            1,
            ["worldview comparison"],
            [{"title": "Source", "url": "https://example.org", "snippet": "Evidence"}],
            None,
            "A provisional conclusion with reasons.",
            None,
            self.db_path,
        )

        position = get_worldview_position("Morgan", db_path=self.db_path)
        history = get_worldview_position_history("Morgan", db_path=self.db_path)
        self.assertEqual(position["conclusion"], "A provisional conclusion with reasons.")
        self.assertEqual(position["source_run_id"], run["run_id"])
        self.assertEqual(position["sources"][0]["url"], "https://example.org")
        self.assertEqual(len(history), 1)

    def test_selection_assessment_prompt_uses_non_personal_scoring_criteria(self):
        client = Mock()
        client.chat.completions.create.return_value = type(
            "Response",
            (),
            {"choices": [type("Choice", (), {"message": type("Message", (), {"content": "Assessment"})()})()]},
        )()
        run = {
            "purpose": "selection",
            "profile_key": "morgan",
            "topic": "Compare major worldviews",
        }

        _generate_assessment(client, run, 1, [], None, db_path=self.db_path)

        user_content = client.chat.completions.create.call_args.kwargs["messages"][1]["content"]
        self.assertIn("1-5", user_content)
        self.assertIn("not fit with personal experiences", user_content)
        self.assertIn("does not support a single conclusion", user_content)

    def test_stop_during_search_skips_model_call_and_cycle_write(self):
        run = create_research_run("What is purpose?", duration_days=7, db_path=self.db_path)
        stop_event = threading.Event()

        def stop_after_search(*args, **kwargs):
            stop_event.set()
            return {"results": [{"title": "Source", "url": "https://example.org", "snippet": "Text"}]}

        client = Mock()
        with patch.object(worldview_research, "search_duckduckgo", side_effect=stop_after_search):
            _run_cycle(client, run, db_path=self.db_path, stop_event=stop_event)

        client.chat.completions.create.assert_not_called()
        status = get_research_status(db_path=self.db_path)
        self.assertEqual(status["cycle_count"], 0)
        self.assertEqual(status["recent_cycles"], [])

    def test_run_tool_requires_explicit_multi_day_request(self):
        with self.assertRaisesRegex(ValueError, "explicit user request"):
            tool_router.execute_tool(
                "start_worldview_research",
                {"topic": "What is purpose?", "duration_days": 7, "interval_hours": 24},
                user_prompt="Could this study religions?",
                db_path=self.db_path,
            )

    def test_run_tool_starts_when_user_explicitly_requests_it(self):
        with patch("modules.tool_router.start_research_worker") as start_worker:
            result = tool_router.execute_tool(
                "start_worldview_research",
                {"topic": "Compare accounts of purpose", "duration_days": 7, "interval_hours": 24},
                groq_client=object(),
                db_path=self.db_path,
                user_prompt="Start researching this question for 7 days.",
            )

        self.assertIn("Started worldview research run", result)
        start_worker.assert_called_once()

    def test_selection_tool_requires_explicit_jarvis_intent_and_persists_profile(self):
        args = {
            "topic": "Compare major religious and nonreligious worldviews",
        }
        with self.assertRaisesRegex(ValueError, "explicit request"):
            tool_router.execute_tool(
                "start_worldview_selection",
                args,
                groq_client=object(),
                db_path=self.db_path,
                user_prompt="Which religion should I choose?",
            )

        with patch("modules.tool_router.config.USER_NAME", "Morgan"), patch(
            "modules.tool_router.start_research_worker"
        ) as start_worker:
            set_worldview_profile_consent("Morgan", True, db_path=self.db_path)
            result = tool_router.execute_tool(
                "start_worldview_selection",
                args,
                groq_client=object(),
                db_path=self.db_path,
                user_prompt="Jarvis, choose your own religion after researching.",
            )

        run = get_research_status(db_path=self.db_path)
        self.assertIn("analytical worldview selection", result)
        self.assertEqual(run["purpose"], "selection")
        self.assertEqual(run["profile_key"], "morgan")
        self.assertEqual(run["duration_days"], 14)
        self.assertEqual(run["interval_hours"], 24)
        start_worker.assert_called_once()

    def test_selection_study_requires_prior_profile_consent(self):
        args = {
            "topic": "Compare major religious and nonreligious worldviews",
            "duration_days": 14,
            "interval_hours": 24,
        }
        with patch("modules.tool_router.config.USER_NAME", "Morgan"):
            with self.assertRaisesRegex(ValueError, "No worldview profile consent"):
                tool_router.execute_tool(
                    "start_worldview_selection",
                    args,
                    groq_client=object(),
                    db_path=self.db_path,
                    user_prompt="Jarvis, choose your own religion after researching.",
                )

    def test_profile_consent_requires_informed_explicit_agreement(self):
        with patch("modules.tool_router.config.USER_NAME", "Morgan"):
            with self.assertRaisesRegex(ValueError, "Informed profile consent"):
                tool_router.execute_tool(
                    "manage_worldview_profile",
                    {"operation": "consent"},
                    db_path=self.db_path,
                    user_prompt="I consent to researching a worldview.",
                )

            result = tool_router.execute_tool(
                "manage_worldview_profile",
                {"operation": "consent"},
                db_path=self.db_path,
                user_prompt=(
                    "I consent to storing my worldview analysis locally and "
                    "processing its research with Groq."
                ),
            )

        self.assertIn("Consent saved", result)

    def test_revoking_consent_deletes_selection_study_data(self):
        with patch("modules.tool_router.config.USER_NAME", "Morgan"):
            set_worldview_profile_consent("Morgan", True, db_path=self.db_path)
            create_research_run(
                "Compare worldviews",
                db_path=self.db_path,
                purpose="selection",
                profile_key="Morgan",
            )
            stop_event = threading.Event()
            with patch.object(worldview_research, "_WORKER_STOP_EVENT", stop_event):
                result = tool_router.execute_tool(
                    "manage_worldview_profile",
                    {"operation": "revoke"},
                    db_path=self.db_path,
                    user_prompt="Revoke my worldview profile consent and delete its records.",
                )

        self.assertIn("have been deleted", result)
        self.assertTrue(stop_event.is_set())
        self.assertIsNone(get_research_status(db_path=self.db_path))

    def test_position_tool_reports_saved_analysis_and_disclaims_personal_faith(self):
        from modules.worldview import save_worldview_position

        save_worldview_position(
            "Morgan", "A provisional analysis.", "run-1", 1, db_path=self.db_path
        )

        with patch("modules.tool_router.config.USER_NAME", "Morgan"):
            set_worldview_profile_consent("Morgan", True, db_path=self.db_path)
            result = tool_router.execute_tool(
                "get_worldview_position", {}, db_path=self.db_path
            )

        self.assertIn("not have personal faith or lived experience", result)
        self.assertIn("A provisional analysis.", result)


class LocalBookReadingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.books = self.root / "worldview_sources"
        self.books.mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_reads_plain_text_in_bounded_resumable_excerpts(self):
        (self.books / "notes.md").write_text("First paragraph.\n\nSecond paragraph.", encoding="utf-8")

        with patch("modules.worldview_research.BOOKS_DIRECTORY", self.books), patch(
            "modules.worldview_research.PROJECT_ROOT", self.root
        ):
            excerpt = read_next_book_excerpt()

        self.assertIn("First paragraph", excerpt["excerpt"])
        self.assertIn("Second paragraph", excerpt["excerpt"])
        self.assertEqual(excerpt["path"], "worldview_sources/notes.md")

    def test_reads_epub_spine_text(self):
        epub_path = self.books / "book.epub"
        with zipfile.ZipFile(epub_path, "w") as archive:
            archive.writestr(
                "META-INF/container.xml",
                '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                '<rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>',
            )
            archive.writestr(
                "OEBPS/content.opf",
                '<package xmlns="http://www.idpf.org/2007/opf"><manifest>'
                '<item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/>'
                '</manifest><spine><itemref idref="chapter"/></spine></package>',
            )
            archive.writestr(
                "OEBPS/chapter.xhtml",
                "<html><body><p>Book chapter text.</p><script>ignore this</script></body></html>",
            )

        with patch("modules.worldview_research.BOOKS_DIRECTORY", self.books), patch(
            "modules.worldview_research.PROJECT_ROOT", self.root
        ):
            excerpt = read_next_book_excerpt()

        self.assertIn("Book chapter text", excerpt["excerpt"])
        self.assertNotIn("ignore this", excerpt["excerpt"])


if __name__ == "__main__":
    unittest.main()