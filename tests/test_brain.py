import unittest
import os
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch

from modules import brain, config
from modules.memory import get_facts, get_recent_conversation, init_memory_db


class StructuredToolRoutingTests(unittest.TestCase):
    def test_non_local_request_uses_groq_structured_tool_calls(self):
        tool_call = SimpleNamespace(
            id="call-1",
            function=SimpleNamespace(
                name="search_web",
                arguments='{"query":"weather in London"}',
            ),
        )
        tool_response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=None, tool_calls=[tool_call])
                )
            ]
        )
        final_response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="I opened a search for the London weather.",
                        tool_calls=[],
                    )
                )
            ]
        )
        completions = Mock(
            side_effect=[tool_response, final_response]
        )
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=completions))
        )
        callbacks = {
            "status": Mock(),
            "response": Mock(),
            "processing": Mock(),
            "skip_audio": Mock(),
        }

        with patch.object(brain, "client", fake_client), patch.object(
            brain, "build_memory_context", return_value=""
        ), patch.object(brain, "execute_tool", return_value="Search opened") as execute, patch.object(
            brain, "save_message"
        ), patch.object(brain, "trim_conversation_for_summary"), patch.object(
            brain, "speak"
        ):
            result = brain.ask_groq("Find current weather in London", callbacks)

        self.assertIsNone(result)
        execute.assert_called_once()
        self.assertEqual(execute.call_args.args[:2], ("search_web", {"query": "weather in London"}))
        first_request = completions.call_args_list[0].kwargs
        self.assertEqual(first_request["model"], config.GROQ_MODEL)
        self.assertTrue(first_request["tools"])
        self.assertEqual(first_request["tool_choice"], "auto")
        callbacks["response"].assert_called_once_with(
            "I opened a search for the London weather."
        )


class TranscriptionMemoryTests(unittest.TestCase):
    def test_transcribed_chat_is_not_automatically_saved_as_a_fact(self):
        transcription = SimpleNamespace(text="Thank you.")
        fake_client = SimpleNamespace(
            audio=SimpleNamespace(
                transcriptions=SimpleNamespace(create=Mock(return_value=transcription))
            )
        )
        callbacks = {
            key: Mock()
            for key in ("status", "user_text", "response", "processing", "skip_audio")
        }

        with tempfile.TemporaryDirectory() as directory:
            db_path = os.path.join(directory, "memory.db")
            init_memory_db(db_path)
            with patch.object(brain, "client", fake_client), patch.object(
                brain, "MEMORY_DB_PATH", db_path
            ), patch.object(brain, "ask_groq"):
                brain.transcribe_audio(b"\0\0" * 160, callbacks)

            self.assertEqual(get_facts(db_path=db_path), [])
            messages = get_recent_conversation(db_path=db_path)
            self.assertEqual(messages[-1]["content"], "Thank you.")


if __name__ == "__main__":
    unittest.main()
