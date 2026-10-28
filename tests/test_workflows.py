import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from modules.actions import plan_workflow_action
from modules.task_catalog import TaskCatalog
from modules.task_orchestration import TaskManager
from modules.workflow_handlers import _run_unittest_suite


class WorkflowExecutionTests(unittest.TestCase):
    def test_catalog_plan_persists_executable_tasks_and_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = os.path.join(directory, "tasks.db")
            track = TaskCatalog(db_path=db_path).plan("project_health_check")
            manager = TaskManager(db_path=db_path)
            saved_tasks = manager.list_tasks(track["track_id"])

            self.assertEqual(len(track["tasks"]), 4)
            self.assertEqual(
                [task["task_id"] for task in track["tasks"]],
                [task["task_id"] for task in saved_tasks],
            )
            self.assertEqual(saved_tasks[0]["dependencies"], [])
            for index, task in enumerate(saved_tasks[1:], start=1):
                self.assertEqual(task["dependencies"], [saved_tasks[index - 1]["task_id"]])

    def test_automated_workflow_progress_uses_each_planned_task_index(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = os.path.join(directory, "tasks.db")
            progress_updates = []
            callbacks = {
                "response": lambda message: None,
                "status": lambda message: None,
                "processing": lambda value: None,
                "skip_audio": lambda value: None,
            }

            with patch.dict(
                "modules.workflow_handlers.WORKFLOW_HANDLERS",
                {"project_health_check": lambda task, context: {"result": task["title"]}},
                clear=True,
            ), patch(
                "modules.hud.update_task_progress",
                side_effect=lambda name, steps, active=True: progress_updates.append(
                    [step["status"] for step in steps]
                ),
            ):
                result = plan_workflow_action(
                    "project_health_check", callbacks, db_path=db_path
                )

            self.assertIn("Executed Project Health Check successfully", result)
            self.assertEqual(len(progress_updates), 8)
            self.assertEqual(progress_updates[-1], ["done", "done", "done", "done"])

    @patch(
        "modules.workflow_handlers.subprocess.run",
        return_value=SimpleNamespace(
            returncode=0,
            stdout="",
            stderr="Ran 7 tests in 0.2s\n\nOK",
        ),
    )
    def test_run_test_workflow_executes_unittest_and_reports_real_summary(self, run):
        result = _run_unittest_suite()

        self.assertEqual(result, "Unit test suite passed: Ran 7 tests in 0.2s")
        self.assertEqual(
            run.call_args.args[0],
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        )
        self.assertFalse(run.call_args.kwargs["check"])

    @patch(
        "modules.workflow_handlers.subprocess.run",
        return_value=SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="Ran 2 tests in 0.1s\n\nFAILED (failures=1)",
        ),
    )
    def test_run_test_workflow_does_not_report_failed_tests_as_success(self, run):
        with self.assertRaisesRegex(RuntimeError, "exit code 1"):
            _run_unittest_suite()


if __name__ == "__main__":
    unittest.main()
