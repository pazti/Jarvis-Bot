import unittest
from unittest.mock import Mock, call, patch

from modules import tts


class TtsWorkerTests(unittest.TestCase):
    def test_windows_com_is_initialized_before_sapi_engine_creation(self):
        events = Mock()
        engine = Mock()
        engine.getProperty.return_value = []
        tts._speech_queue.put("test message")
        tts._speech_queue.put(None)

        def create_engine():
            events.init_engine()
            return engine

        with patch("modules.tts.os.name", "nt"), patch(
            "comtypes.CoInitialize",
            side_effect=events.co_initialize,
        ), patch(
            "comtypes.CoUninitialize",
            side_effect=events.co_uninitialize,
        ), patch(
            "modules.tts.pyttsx3.init",
            side_effect=create_engine,
        ), patch(
            "modules.tts.get_voice_profile_for_text",
            return_value={"rate": 160, "volume": 0.5},
        ):
            tts._speech_worker()

        self.assertEqual(
            events.mock_calls[:2],
            [call.co_initialize(), call.init_engine()],
        )
        engine.say.assert_called_once_with("test message")
        engine.runAndWait.assert_called_once()
        engine.stop.assert_called_once()
        events.co_uninitialize.assert_called_once()
        self.assertFalse(tts.is_speaking())


if __name__ == "__main__":
    unittest.main()
