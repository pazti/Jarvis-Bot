import os
import tempfile
import unittest

from modules.task_catalog import TASK_CATALOG, TaskCatalog


class TaskCatalogTests(unittest.TestCase):
    def test_catalog_contains_expected_workflows(self):
        expected_workflows = {
            "project_health_check",
            "run_test_suite",
            "feature_implementation",
            "business_finder",
        }
        self.assertTrue(expected_workflows.issubset(TASK_CATALOG))
        self.assertGreaterEqual(len(TASK_CATALOG), len(expected_workflows))

    def test_business_finder_workflow_has_api_and_report_steps(self):
        workflow = TASK_CATALOG["business_finder"]
        titles = [task[0] for task in workflow["tasks"]]
        self.assertIn("Search OpenStreetMap", titles)
        self.assertIn("Save businesses without websites", titles)

    def test_catalog_plans_a_track_for_each_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog = TaskCatalog(db_path=os.path.join(directory, "tasks.db"))
            for task_key in TASK_CATALOG:
                track = catalog.plan(task_key)
                self.assertEqual(track["status"], "PLANNING")
                self.assertGreaterEqual(len(track["tasks"]), 2)

    def test_unknown_workflow_has_helpful_error(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog = TaskCatalog(db_path=os.path.join(directory, "tasks.db"))
            with self.assertRaises(ValueError):
                catalog.plan("not_a_real_workflow")


if __name__ == "__main__":
    unittest.main()
