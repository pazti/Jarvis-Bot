import unittest
from unittest.mock import patch

from modules import tool_router


class LocalRoutingTests(unittest.TestCase):
    def setUp(self):
        self.responses = []
        self.statuses = []
        self.muted = []
        self.sleeping = []
        self.callbacks = {
            "response": self.responses.append,
            "status": self.statuses.append,
            "processing": lambda value: None,
            "skip_audio": lambda value: None,
            "set_muted": self.muted.append,
            "set_sleeping": self.sleeping.append,
        }

    @patch("modules.actions.time_action", return_value="time")
    def test_time_uses_only_a_whitelisted_exact_phrase(self, time_action):
        self.assertEqual(
            tool_router.route_local_action("JARVIS, what time is it?", self.callbacks),
            "time",
        )
        time_action.assert_called_once_with(self.callbacks)

        self.assertIsNone(
            tool_router.route_local_action("JARVIS, what time is it in Tokyo?", self.callbacks)
        )
        time_action.assert_called_once()

    def test_mute_and_assistant_sleep_phrases_update_state(self):
        result = tool_router.route_local_action("mute microphone", self.callbacks)
        self.assertEqual(result, "Microphone muted.")
        self.assertEqual(self.muted, [True])

        result = tool_router.route_local_action("sleep assistant", self.callbacks)
        self.assertIn("Going to sleep", result)
        self.assertEqual(self.sleeping, [True])
        self.assertIn("JARVIS is sleeping...", self.statuses)

    def test_explicit_worldview_consent_is_routed_without_llm_selection(self):
        consent = (
            "I consent to storing my worldview analysis locally and "
            "processing its research with Groq."
        )
        with patch(
            "modules.tool_router.execute_tool",
            return_value="Consent saved.",
        ) as execute:
            result = tool_router.route_local_action(consent, self.callbacks)

        self.assertEqual(result, "Consent saved.")
        execute.assert_called_once_with(
            "manage_worldview_profile",
            {"operation": "consent"},
            user_prompt=consent,
        )

    def test_selection_study_request_routes_directly_and_uses_defaults(self):
        with patch("modules.tool_router.has_worldview_profile_consent", return_value=True), patch(
            "modules.brain.client", object()
        ), patch(
            "modules.tool_router.execute_tool",
            return_value="Study started.",
        ) as execute:
            result = tool_router.route_local_action(
                "Start a worldview selection study.",
                self.callbacks,
            )

        self.assertEqual(result, "Study started.")
        self.assertEqual(execute.call_args.args[0], "start_worldview_selection")
        self.assertEqual(execute.call_args.args[1]["duration_days"], 14)
        self.assertEqual(execute.call_args.args[1]["interval_hours"], 24)

    def test_select_and_evaluate_all_religions_command_starts_selection_study(self):
        prompt = (
            "Choose and evaluate all the religions for analysis from the "
            "worldview selection."
        )
        with patch("modules.tool_router.has_worldview_profile_consent", return_value=True), patch(
            "modules.brain.client", object()
        ), patch(
            "modules.tool_router.execute_tool",
            return_value="Study started.",
        ) as execute:
            result = tool_router.route_local_action(prompt, self.callbacks)

        self.assertEqual(result, "Study started.")
        self.assertEqual(execute.call_args.args[0], "start_worldview_selection")

    def test_missing_worldview_consent_returns_a_clear_local_response(self):
        with patch("modules.tool_router.has_worldview_profile_consent", return_value=False), patch(
            "modules.brain.client", object()
        ):
            result = tool_router.route_local_action(
                "Start a worldview selection study.",
                self.callbacks,
            )

        self.assertIn("No worldview profile consent", result)
        self.assertIn("I consent to storing", result)
        self.assertEqual(self.responses[-1], result)

    def test_pc_power_tool_requires_a_separate_explicit_confirmation(self):
        with patch.object(tool_router, "_pending_power", None), patch(
            "modules.tool_router.subprocess.Popen"
        ) as popen:
            message = tool_router.execute_tool(
                "request_pc_power", {"operation": "sleep"}
            )
            self.assertIn("Please confirm", message)
            popen.assert_not_called()

            result = tool_router.route_local_action("confirm", self.callbacks)
            self.assertIn("PC is going to sleep", result)
            popen.assert_called_once()

    def test_ordinary_power_request_does_not_execute_system_commands(self):
        with patch.object(tool_router, "_pending_power", None), patch(
            "modules.tool_router.subprocess.Popen"
        ) as popen, patch("modules.tool_router.subprocess.run") as run:
            result = tool_router.route_local_action("shut down this computer", self.callbacks)

        self.assertIsNone(result)
        popen.assert_not_called()
        run.assert_not_called()

    @patch("modules.actions.search_web_action", return_value="report saved")
    def test_web_search_tool_accepts_bounded_related_queries(self, search):
        result = tool_router.execute_tool(
            "search_web",
            {
                "query": "impact of urban trees",
                "related_queries": [
                    "urban tree heat mitigation studies",
                    "urban tree health risks",
                ],
            },
        )

        self.assertEqual(result, "report saved")
        search.assert_called_once_with(
            "impact of urban trees",
            related_queries=[
                "urban tree heat mitigation studies",
                "urban tree health risks",
            ],
        )

    def test_web_search_tool_rejects_invalid_related_queries(self):
        with self.assertRaisesRegex(ValueError, "related_queries"):
            tool_router.execute_tool(
                "search_web",
                {"query": "urban trees", "related_queries": ["", 12]},
            )


if __name__ == "__main__":
    unittest.main()
