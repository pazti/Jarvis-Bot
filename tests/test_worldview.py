import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from modules import tool_router
from modules.worldview import (
    get_recent_reflections,
    get_worldview_position,
    get_worldview_position_history,
    has_worldview_profile_consent,
    reflect_on_worldviews,
    save_reflection,
    save_worldview_position,
    set_worldview_profile_consent,
    search_worldview_knowledge,
)


class WorldviewKnowledgeTests(unittest.TestCase):
    def test_search_finds_balanced_tradition_summaries(self):
        result = search_worldview_knowledge("Buddhism and Christianity purpose")

        self.assertIn("Buddhist traditions", result)
        self.assertIn("Christian traditions", result)

    def test_unmatched_search_returns_full_reference(self):
        result = search_worldview_knowledge("unmatched-term-xyz")

        self.assertIn("## Christianity", result)
        self.assertIn("## Agnosticism", result)


class WorldviewJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "memory.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_reflections_persist_in_date_order(self):
        save_reflection("First reflection", db_path=self.db_path)
        save_reflection("Second reflection", db_path=self.db_path)

        entries = get_recent_reflections(db_path=self.db_path)

        self.assertEqual(
            [entry["reflection"] for entry in entries],
            ["First reflection", "Second reflection"],
        )
        self.assertTrue(entries[0]["created_at"])

    def test_reflection_uses_reference_and_saves_generated_entry(self):
        message = SimpleNamespace(content="A balanced analytical reflection.")
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=Mock(
                        return_value=SimpleNamespace(
                            choices=[SimpleNamespace(message=message)]
                        )
                    )
                )
            )
        )

        result = reflect_on_worldviews(client, "Compare views of purpose", db_path=self.db_path)

        self.assertIn("Reflection saved", result)
        self.assertIn("A balanced analytical reflection.", result)
        self.assertEqual(
            get_recent_reflections(db_path=self.db_path)[0]["reflection"],
            message.content,
        )
        request = client.chat.completions.create.call_args.kwargs
        self.assertIn("## Christianity", request["messages"][1]["content"])

    def test_empty_reflection_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            save_reflection("  ", db_path=self.db_path)

    def test_worldview_position_persists_per_profile_with_revision_history(self):
        save_worldview_position(
            "Morgan", "First analytical conclusion.", "run-1", 1, db_path=self.db_path
        )
        save_worldview_position(
            "Morgan", "Revised conclusion with new evidence.", "run-1", 2,
            sources=[{"kind": "web search snippet", "url": "https://example.org", "verified": False}],
            db_path=self.db_path,
        )
        save_worldview_position(
            "Taylor", "A different profile's conclusion.", "run-2", 1,
            db_path=self.db_path,
        )

        current = get_worldview_position("morgan", db_path=self.db_path)
        history = get_worldview_position_history("MORGAN", db_path=self.db_path)

        self.assertEqual(current["conclusion"], "Revised conclusion with new evidence.")
        self.assertEqual(current["cycle_number"], 2)
        self.assertEqual(current["previous_conclusion"], "First analytical conclusion.")
        self.assertEqual(current["sources"][0]["url"], "https://example.org")
        self.assertEqual(
            [entry["conclusion"] for entry in history],
            ["First analytical conclusion.", "Revised conclusion with new evidence."],
        )
        self.assertIsNone(get_worldview_position("Other", db_path=self.db_path))

    def test_empty_worldview_position_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            save_worldview_position("Morgan", " ", "run-1", 1, db_path=self.db_path)

    def test_profile_consent_is_per_profile_and_revocation_deletes_saved_analysis(self):
        set_worldview_profile_consent("Morgan", True, db_path=self.db_path)
        save_worldview_position(
            "Morgan", "Private analysis.", "run-1", 1, db_path=self.db_path
        )
        save_worldview_position(
            "Taylor", "Separate analysis.", "run-2", 1, db_path=self.db_path
        )

        self.assertTrue(has_worldview_profile_consent("morgan", db_path=self.db_path))
        self.assertFalse(has_worldview_profile_consent("Taylor", db_path=self.db_path))

        set_worldview_profile_consent("Morgan", False, db_path=self.db_path)

        self.assertFalse(has_worldview_profile_consent("Morgan", db_path=self.db_path))
        self.assertIsNone(get_worldview_position("Morgan", db_path=self.db_path))
        self.assertIsNotNone(get_worldview_position("Taylor", db_path=self.db_path))

    def test_tool_requires_user_requested_reflection(self):
        with self.assertRaisesRegex(ValueError, "explicit user request"):
            tool_router.execute_tool(
                "reflect_on_worldviews",
                {"question": "Choose a religion"},
                user_prompt="Which religion is best?",
                db_path=self.db_path,
            )

    def test_tool_rejects_negated_reflection_request(self):
        with self.assertRaisesRegex(ValueError, "explicit user request"):
            tool_router.execute_tool(
                "reflect_on_worldviews",
                {"question": "Compare views of purpose"},
                user_prompt="Do not journal about this topic.",
                db_path=self.db_path,
            )


if __name__ == "__main__":
    unittest.main()