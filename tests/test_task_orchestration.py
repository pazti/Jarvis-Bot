import os
import tempfile
import unittest

from modules.task_orchestration import TaskManager


class TaskManagerTests(unittest.TestCase):
    def test_create_track_add_task_and_update_task_persist_in_sqlite(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = os.path.join(directory, "tasks.db")
            manager = TaskManager(db_path=db_path)

            track = manager.create_track(
                "Project health check",
                description="Verify current repo health",
                main_goal="Improve reliability",
                context={"owner": "Paul"},
                user_feedback="Please keep me posted",
            )

            self.assertEqual(track["name"], "Project health check")
            self.assertEqual(track["context"]["owner"], "Paul")
            self.assertEqual(track["status"], "PLANNING")

            task_id = manager.add_task(
                track["track_id"],
                "Inspect dependencies",
                "Review requirements and versions",
                "Confirm the environment is installable",
                dependencies=[],
                required_tools=["python"],
                expected_output="Installation summary",
                validation_criteria=["requirements available"],
                user_feedback_required=True,
                priority="HIGH",
            )

            task = manager.get_task(track["track_id"], task_id)
            self.assertEqual(task["title"], "Inspect dependencies")
            self.assertEqual(task["priority"], "HIGH")
            self.assertTrue(task["user_feedback_required"])

            updated = manager.update_task(
                track["track_id"],
                task_id,
                status="IN_PROGRESS",
                result="Started the dependency review",
                validation={"passed": True},
                feedback="Work underway",
            )

            self.assertEqual(updated["status"], "IN_PROGRESS")
            self.assertEqual(updated["result"], "Started the dependency review")
            self.assertTrue(updated["validation"]["passed"])
            self.assertEqual(updated["feedback"], "Work underway")

            self.assertEqual(len(manager.list_tasks(track["track_id"])), 1)


if __name__ == "__main__":
    unittest.main()
