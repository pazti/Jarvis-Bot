import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from modules import config, proactive


class ProactiveRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "proactive.db")
        self.responses = []
        self.states = {"busy": False, "muted": False, "sleeping": False}
        self.callbacks = {
            "processing": lambda value: None,
            "skip_audio": lambda value: None,
            "status": lambda value: None,
            "response": self.responses.append,
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def _runtime(self):
        with patch.object(config, "PROACTIVE_QUIET_HOURS", ""), patch.object(
            config, "PROACTIVE_ENABLED", False
        ):
            return proactive.ProactiveRuntime(
                self.callbacks, lambda: self.states, db_path=self.db_path
            )

    def _make_timer_due(self):
        timer_id = proactive.schedule_timer(60, "tea", db_path=self.db_path)
        connection = sqlite3.connect(self.db_path)
        try:
            connection.execute(
                "UPDATE proactive_timers SET due_at = ? WHERE timer_id = ?",
                ("2000-01-01T00:00:00Z", timer_id),
            )
            connection.commit()
        finally:
            connection.close()

    @patch("modules.proactive.speak")
    @patch("modules.proactive.is_speaking", return_value=False)
    def test_due_timer_delivers_once_even_when_followups_are_disabled(
        self, is_speaking, speak
    ):
        self._make_timer_due()
        runtime = self._runtime()

        self.assertTrue(runtime.tick())
        self.assertFalse(runtime.tick())

        self.assertEqual(self.responses, ["Your timer for tea has finished."])
        speak.assert_called_once_with("Your timer for tea has finished.")

    @patch("modules.proactive.speak")
    @patch("modules.proactive.is_speaking", return_value=False)
    def test_muted_state_defers_due_timer_delivery(self, is_speaking, speak):
        self._make_timer_due()
        self.states["muted"] = True
        runtime = self._runtime()

        self.assertFalse(runtime.tick())
        self.assertEqual(self.responses, [])
        speak.assert_not_called()

        connection = sqlite3.connect(self.db_path)
        try:
            delivered_at = connection.execute(
                "SELECT delivered_at FROM proactive_timers"
            ).fetchone()[0]
        finally:
            connection.close()
        self.assertIsNone(delivered_at)


if __name__ == "__main__":
    unittest.main()
