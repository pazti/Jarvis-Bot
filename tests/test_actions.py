import unittest
from unittest.mock import patch

from modules.actions import run_action


class ActionTests(unittest.TestCase):
    def setUp(self):
        self.responses = []
        self.callbacks = {
            "response": self.responses.append,
            "status": lambda message: None,
            "processing": lambda value: None,
            "skip_audio": lambda value: None,
        }

    @patch("modules.actions.webbrowser.open")
    def test_directions_request_opens_maps_route(self, open_browser):
        result = run_action("JARVIS, I need directions to the airport", self.callbacks)

        self.assertEqual(result, "Opening directions to the airport.")
        open_browser.assert_called_once_with(
            "https://www.google.com/maps/dir/?api=1&destination=the+airport"
        )
        self.assertEqual(self.responses[-1], result)

    @patch("modules.actions.webbrowser.open")
    def test_any_direction_request_does_not_fall_through_to_llm(self, open_browser):
        result = run_action(
            "Chavis, I need any direction to the National Assembly of Nigeria",
            self.callbacks,
        )

        self.assertEqual(
            result,
            "Opening directions to the National Assembly of Nigeria.",
        )
        open_browser.assert_called_once_with(
            "https://www.google.com/maps/dir/?api=1&destination=the+National+Assembly+of+Nigeria"
        )

    def test_capabilities_request_returns_showcase(self):
        result = run_action("What can you do?", self.callbacks)

        self.assertIn("Google Maps", result)
        self.assertIn("review the code", result)
        self.assertEqual(self.responses[-1], result)

    @patch("modules.vision.describe_screen_for_task", return_value="The loop uses the wrong boundary; change <= to <.")
    def test_code_review_request_uses_screen_vision(self, describe_screen):
        fake_client = object()

        result = run_action(
            "Open my code and tell me what's wrong",
            self.callbacks,
            groq_client=fake_client,
        )

        describe_screen.assert_called_once()
        self.assertIn("The loop uses the wrong boundary", result)
        self.assertIn("Code review:", result)
        self.assertEqual(self.responses[-1], result)


if __name__ == "__main__":
    unittest.main()