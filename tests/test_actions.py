import os
import tempfile
import unittest
from unittest.mock import ANY, patch

from modules import actions
from modules.actions import run_action


class ActionTests(unittest.TestCase):
    def setUp(self):
        self.responses = []
        self.muted = []
        self.sleeping = []
        self.callbacks = {
            "response": self.responses.append,
            "status": self.responses.append,
            "processing": lambda value: None,
            "skip_audio": lambda value: None,
            "set_muted": self.muted.append,
            "set_sleeping": self.sleeping.append,
        }

    def test_non_local_requests_are_left_for_structured_llm_routing(self):
        for prompt in (
            "JARVIS, I need directions to the airport",
            "What can you do?",
            "Review my project code",
            "Find restaurants in Benin City without websites",
        ):
            with self.subTest(prompt=prompt):
                self.assertIsNone(run_action(prompt, self.callbacks))

        self.assertEqual(self.responses, [])

    def test_only_exact_assistant_sleep_phrase_changes_sleep_state(self):
        result = run_action("sleep jarvis", self.callbacks)

        self.assertIn("Going to sleep", result)
        self.assertEqual(self.sleeping, [True])

        self.assertIsNone(run_action("I need to sleep on this decision", self.callbacks))
        self.assertEqual(self.sleeping, [True])

    def test_common_local_actions_cover_standard_responses_and_callbacks(self):
        self.assertIn("The time is", actions.time_action(self.callbacks))
        self.assertIn("Today is", actions.date_action(self.callbacks))
        self.assertIn("Reminder set:", actions.reminder_action("set a reminder to call mom", self.callbacks))
        self.assertIn("Draft message:", actions.draft_message_action("draft a message to Alex", self.callbacks))
        self.assertIn("Focus mode started", actions.focus_mode_action(self.callbacks))
        self.assertIn("I can summarize the screen", actions.screen_summary_action(self.callbacks))
        self.assertIn("I can check the weather", actions.weather_action(self.callbacks))
        self.assertIn("Project code review:", actions.project_code_review_action(self.callbacks))

    def test_search_web_and_business_finder_actions_execute_workflows(self):
        with patch("modules.web_search.search_duckduckgo") as search_duckduckgo:
            search_duckduckgo.return_value = {
                "results": [{"title": "Alpha result", "snippet": "Useful snippet.", "url": "https://example.org"}],
                "queries": ["weather"],
                "report_path": "report.md",
            }
            response = actions.search_web_action("weather in London", self.callbacks)
            self.assertIn("DuckDuckGo results", response)

        with tempfile.TemporaryDirectory() as directory:
            with patch("modules.osm_places.search_businesses_without_websites", return_value=[{
                "id": "1",
                "name": "Cafe Central",
                "address": "10 Main St",
                "phone": "555-0100",
                "maps_url": "https://example.org/map/1",
                "rating": "N/A",
                "types": "cafe",
                "website": "",
            }]), patch("modules.osm_places.save_business_report", return_value=os.path.join(directory, "report.csv")):
                response = actions.business_finder_action("find restaurants in Abuja without websites", self.callbacks, db_path=os.path.join(directory, "tasks.db"))

            self.assertIn("Business Finder (OSM) complete", response)

    @patch("webbrowser.open")
    def test_open_website_and_google_maps_actions_use_expected_targets(self, open_browser):
        self.assertIn("Opening https://github.com", actions.open_website_action("open github", self.callbacks))
        self.assertIn("Opening directions to airport", actions.google_maps_action("directions to airport", self.callbacks))
        open_browser.assert_any_call("https://github.com")
        open_browser.assert_any_call("https://www.google.com/maps/dir/?api=1&destination=airport")

    @patch("webbrowser.open", side_effect=OSError("browser unavailable"))
    def test_browser_actions_report_open_failures(self, open_browser):
        self.assertEqual(
            actions.open_website_action("open github", self.callbacks),
            "I could not open that website.",
        )
        self.assertEqual(
            actions.google_maps_action("directions to airport", self.callbacks),
            "I could not open Google Maps.",
        )
        self.assertEqual(open_browser.call_count, 2)

    @patch("modules.actions.memory.get_memory_summary", return_value="General memory summary")
    @patch("modules.actions.memory.remember_memory", return_value=True)
    def test_memory_and_sleep_helpers_return_coherent_messages(self, remember_memory, get_memory_summary):
        self.assertEqual(actions.quick_note_action("create a quick note: hold the line", self.callbacks), "Quick note saved: hold the line")
        self.assertEqual(actions.show_memory_action("show my general memory", self.callbacks), "General memory summary")
        self.assertIn("Entering sleep mode", actions.sleep_action(self.callbacks, groq_client=None, db_path=None))
        self.assertIn("Hello, Sir. JARVIS is awake.", actions.wake_action(self.callbacks))
        remember_memory.assert_called_once()

    @patch("modules.actions.memory.clear_memory")
    @patch("modules.actions.memory.remember_memory", return_value="Saved preference")
    @patch("modules.actions.memory.forget_memory", return_value=True)
    def test_memory_mutation_actions_preserve_messages_and_callbacks(
        self, forget_memory, remember_memory, clear_memory
    ):
        self.assertEqual(actions.remember_action("remember this", self.callbacks), "Memory saved: Saved preference")
        self.assertEqual(actions.forget_action("forget this", self.callbacks), "I cleared the matching memory entry.")
        self.assertEqual(actions.clear_memory_action(self.callbacks), "MEMORY_CLEARED")
        self.assertIn("Memory cleared.", self.responses)
        forget_memory.assert_called_once()
        remember_memory.assert_called_once()
        clear_memory.assert_called_once()

    @patch("modules.actions.memory.save_fact")
    @patch("modules.actions.memory.create_session_summary", return_value="Session recap")
    def test_summary_saving_persists_memory_and_enters_sleep(
        self, create_summary, save_fact
    ):
        result = actions.save_summary_action(
            "yes",
            groq_client=object(),
            update_callbacks=self.callbacks,
            db_path="memory.db",
        )

        self.assertEqual(result, "SLEEP")
        self.assertIn("Saved: Session recap", self.responses)
        self.assertEqual(self.sleeping, [True])
        create_summary.assert_called_once_with(ANY, db_path="memory.db")
        save_fact.assert_called_once_with(
            "session_summary",
            "Session recap",
            category="general",
            db_path="memory.db",
        )


if __name__ == "__main__":
    unittest.main()