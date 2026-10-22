import unittest
from unittest.mock import patch, MagicMock
import modules.actions as actions

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

if __name__ == "__main__":
    unittest.main()
