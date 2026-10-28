import unittest
from unittest.mock import patch, MagicMock
import modules.actions as actions
from modules.tool_router import execute_tool

class SecurityTests(unittest.TestCase):
    @patch("subprocess.run")
    def test_copy_last_response_injection(self, mock_run):
        # We want to see if a malicious response can execute code
        malicious_response = "' ; Start-Process calc.exe ; '"
        actions.LAST_RESPONSE = malicious_response
        
        mock_run.return_value = MagicMock(returncode=0)
        actions.copy_last_response_action()
        
        # Get the arguments passed to subprocess.run
        args, kwargs = mock_run.call_args
        cmd_list = args[0]
        
        print(f"Executed Command: {cmd_list}")
        
        # Verify that the command is now the secure 'clip' utility
        self.assertEqual(cmd_list, ["clip"])
        # Verify that the malicious content was passed as input, not as part of the command string
        self.assertEqual(kwargs["input"], malicious_response)
        # Verify that 'Start-Process' is NOT part of the command list
        self.assertNotIn("Start-Process calc.exe", cmd_list)

    @patch("modules.actions.open_app_action")
    def test_structured_tool_rejects_command_injection_as_app_name(self, open_app):
        with self.assertRaisesRegex(ValueError, "Unsupported app"):
            execute_tool("open_app", {"app": "vscode; Start-Process calc.exe"})

        open_app.assert_not_called()

if __name__ == "__main__":
    unittest.main()
