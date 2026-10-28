import unittest
from unittest.mock import Mock, patch

from modules import workflow_handlers


class WorkflowHandlerTests(unittest.TestCase):
    @patch("modules.workflow_handlers.subprocess.run")
    def test_project_health_check_and_run_test_suite_handlers(self, run):
        run.return_value = Mock(returncode=0, stdout="Ran 2 tests in 0.10s\nOK\n", stderr="")

        structure = workflow_handlers.handle_project_health_check({"title": "Inspect project structure"}, {})
        configuration = workflow_handlers.handle_project_health_check({"title": "Review dependencies and configuration"}, {})
        report = workflow_handlers.handle_project_health_check({"title": "Report project health"}, {})
        tests = workflow_handlers.handle_run_test_suite({"title": "Discover tests"}, {})

        self.assertIn("Project structure inspected", structure["result"])
        self.assertIn("requirements.txt found", configuration["result"])
        self.assertIn("Health report", report["result"])
        self.assertIn("Discovered", tests["result"])

    @patch("modules.workflow_handlers.subprocess.run")
    def test_git_assistant_handler_reads_repository_status(self, run):
        run.return_value = Mock(stdout=" M README.md\n", stderr="", returncode=0)

        result = workflow_handlers.handle_git_assistant({"title": "Inspect repository status"}, {})

        self.assertIn("Git status", result["result"])
        self.assertIn("README.md", result["result"])

    def test_dependency_audit_and_backup_scope_are_supported(self):
        inventory = workflow_handlers.handle_dependency_audit({"title": "Inventory dependencies"}, {})
        scope = workflow_handlers.handle_project_backup({"title": "Define backup scope"}, {})

        self.assertIn("15 core dependencies", inventory["result"])
        self.assertIn(".git", scope["result"])


if __name__ == "__main__":
    unittest.main()
