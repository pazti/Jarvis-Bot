import importlib
import os
import tempfile
import unittest
from unittest.mock import patch

from dotenv import get_key

from modules import config


class IdentitySettingsTests(unittest.TestCase):
    def test_identity_settings_update_environment_prompt_and_window_title(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = os.path.join(directory, ".env")
            original_values = {
                "USER_NAME": config.USER_NAME,
                "ASSISTANT_NAME": config.ASSISTANT_NAME,
                "ADDRESS_AS": config.ADDRESS_AS,
                "SYSTEM_PROMPT": config.SYSTEM_PROMPT,
                "WINDOW_TITLE": config.WINDOW_TITLE,
                "ENV_FILE_PATH": config.ENV_FILE_PATH,
            }
            with patch.multiple(config, **original_values), patch.dict(os.environ, {}, clear=True):
                config.ENV_FILE_PATH = env_path
                config.save_identity_settings("Morgan", "Nova", "Captain")

                self.assertEqual(config.USER_NAME, "Morgan")
                self.assertEqual(config.ASSISTANT_NAME, "Nova")
                self.assertEqual(config.ADDRESS_AS, "Captain")
                self.assertIn("You are Nova", config.SYSTEM_PROMPT)
                self.assertIn("Morgan", config.SYSTEM_PROMPT)
                self.assertEqual(
                    config.WINDOW_TITLE,
                    "Nova - ZeroTrace Intelligence Core (Morgan)",
                )
                self.assertEqual(os.environ["ADDRESS_AS"], "Captain")
                self.assertEqual(get_key(env_path, "USER_NAME"), "Morgan")
                self.assertEqual(get_key(env_path, "ASSISTANT_NAME"), "Nova")

    def test_missing_groq_api_key_raises_runtime_error(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Missing required environment variable: GROQ_API_KEY"):
                importlib.reload(config)


if __name__ == "__main__":
    unittest.main()
