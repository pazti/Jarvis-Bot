import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from modules.config import MEMORY_DB_PATH


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TaskDatabaseMixin:
    def __init__(self, db_path=None):
        self.db_path = db_path or MEMORY_DB_PATH
        self._ensure_schema()

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _session(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _ensure_schema(self):
        with self._session() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS tracks (
                    track_id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT,
                    main_goal TEXT, status TEXT NOT NULL, progress REAL NOT NULL,
                    current_task_id TEXT, context TEXT, user_feedback TEXT,
                    created_at TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS track_tasks (
                    task_id TEXT PRIMARY KEY, track_id TEXT NOT NULL, title TEXT NOT NULL,
                    description TEXT, objective TEXT, priority TEXT, status TEXT NOT NULL,
                    dependencies TEXT, required_tools TEXT, expected_output TEXT,
                    validation_criteria TEXT, user_feedback_required INTEGER,
                    created_at TEXT, started_at TEXT, completed_at TEXT, result TEXT,
                    error TEXT, validation TEXT, feedback TEXT, attempt_count INTEGER
                );
                CREATE TABLE IF NOT EXISTS task_feedback (
                    feedback_id TEXT PRIMARY KEY, track_id TEXT, task_id TEXT,
                    decision TEXT, message TEXT, created_at TEXT
                );
                """
            )

    @staticmethod
    def _json(value):
        return json.dumps(value if value is not None else [])

    @staticmethod
    def _list(value):
        try:
            parsed = json.loads(value or "[]")
            return parsed if isinstance(parsed, list) else []
        except (TypeError, ValueError):
            return []

    def _task(self, row):
        if row is None:
            return None
        data = dict(row)
        for key in ("dependencies", "required_tools", "validation_criteria"):
            data[key] = self._list(data[key])
        data["validation"] = json.loads(data["validation"] or "{}")
        data["user_feedback_required"] = bool(data["user_feedback_required"])
        return data


class TaskManager(TaskDatabaseMixin):
    def create_track(self, name, description="", main_goal="", context=None, user_feedback=""):
        track_id = str(uuid.uuid4())
        timestamp = _now()
        with self._session() as connection:
            connection.execute(
                "INSERT INTO tracks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (track_id, name, description, main_goal, "PLANNING", 0, None,
                 json.dumps(context or {}), user_feedback, timestamp, timestamp),
            )
        return self.get_track(track_id)

    def get_track(self, track_id):
        with self._session() as connection:
            row = connection.execute("SELECT * FROM tracks WHERE track_id = ?", (track_id,)).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["context"] = json.loads(data["context"] or "{}")
        return data

    def update_track(self, track_id, **updates):
        updates["updated_at"] = _now()
        fields = ", ".join(f"{key} = ?" for key in updates)
        values = list(updates.values()) + [track_id]
        with self._session() as connection:
            connection.execute(f"UPDATE tracks SET {fields} WHERE track_id = ?", values)
        return self.get_track(track_id)

    def add_task(self, track_id, title, description, objective, dependencies=None,
                 required_tools=None, expected_output="", validation_criteria=None,
                 user_feedback_required=False, priority="MEDIUM"):
        if not self.get_track(track_id):
            raise ValueError(f"Track {track_id} does not exist.")
        task_id = str(uuid.uuid4())
        with self._session() as connection:
            connection.execute(
                "INSERT INTO track_tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (task_id, track_id, title, description, objective, priority, "PENDING",
                 self._json(dependencies), self._json(required_tools), expected_output,
                 self._json(validation_criteria), int(user_feedback_required), _now(),
                 None, None, None, None, json.dumps({"passed": False}), None, 0),
            )
            if self.get_track(track_id)["current_task_id"] is None:
                connection.execute("UPDATE tracks SET current_task_id = ? WHERE track_id = ?", (task_id, track_id))
        return task_id

    def get_task(self, track_id, task_id):
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM track_tasks WHERE track_id = ? AND task_id = ?", (track_id, task_id)
            ).fetchone()
        return self._task(row)

    def list_tasks(self, track_id):
        with self._session() as connection:
            rows = connection.execute(
                "SELECT * FROM track_tasks WHERE track_id = ? ORDER BY created_at", (track_id,)
            ).fetchall()
        return [self._task(row) for row in rows]

    def update_task(self, track_id, task_id, **updates):
        if "validation" in updates:
            updates["validation"] = json.dumps(updates["validation"])
        for key in ("dependencies", "required_tools", "validation_criteria"):
            if key in updates:
                updates[key] = self._json(updates[key])
        fields = ", ".join(f"{key} = ?" for key in updates)
        with self._session() as connection:
            connection.execute(
                f"UPDATE track_tasks SET {fields} WHERE track_id = ? AND task_id = ?",
                list(updates.values()) + [track_id, task_id],
            )
        return self.get_task(track_id, task_id)

    def update_task_status(self, track_id, task_id, status, result=None, error=None, validation=None):
        updates = {"status": status.upper()}
        if result is not None:
            updates["result"] = result
        if error is not None:
            updates["error"] = error
        if validation is not None:
            updates["validation"] = validation
        if status.upper() == "IN_PROGRESS":
            updates["started_at"] = _now()
        if status.upper() in {"COMPLETED", "FAILED", "BLOCKED", "SKIPPED"}:
            updates["completed_at"] = _now()
        task = self.update_task(track_id, task_id, **updates)
        ProgressManager(self.db_path).refresh_track_progress(track_id)
        return task


class ProgressManager(TaskManager):
    def refresh_track_progress(self, track_id):
        tasks = self.list_tasks(track_id)
        completed = sum(task["status"] == "COMPLETED" for task in tasks)
        current = next((task["task_id"] for task in tasks if task["status"] in {"PENDING", "IN_PROGRESS"}), None)
        progress = round(completed * 100 / len(tasks), 2) if tasks else 0
        status = "COMPLETED" if tasks and completed == len(tasks) else "IN_PROGRESS" if tasks else "PLANNING"
        return self.update_track(track_id, progress=progress, current_task_id=current, status=status)

    def get_progress(self, track_id):
        track = self.get_track(track_id)
        tasks = self.list_tasks(track_id)
        return {
            "track_id": track_id,
            "total_tasks": len(tasks),
            "completed_tasks": sum(task["status"] == "COMPLETED" for task in tasks),
            "pending_tasks": sum(task["status"] in {"PENDING", "IN_PROGRESS"} for task in tasks),
            "progress_percent": track["progress"] if track else 0,
            "status": track["status"] if track else "UNKNOWN",
        }


class TaskExecutor(TaskManager):
    def execute_task(self, track_id, task_id, task_handler=None, context=None):
        task = self.get_task(track_id, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found in track {track_id}.")
        for dependency_id in task["dependencies"]:
            dependency = self.get_task(track_id, dependency_id)
            if dependency and dependency["status"] != "COMPLETED":
                return self.update_task_status(track_id, task_id, "BLOCKED", error="Dependency is not complete.")
        self.update_task_status(track_id, task_id, "IN_PROGRESS")
        try:
            outcome = task_handler(task, context) if task_handler else {"result": "Task ready for execution."}
            if not isinstance(outcome, dict):
                outcome = {"result": str(outcome)}
            return self.update_task_status(
                track_id, task_id, "COMPLETED", result=outcome.get("result"),
                validation=outcome.get("validation", {"passed": True}),
            )
        except Exception as error:
            return self.update_task_status(track_id, task_id, "FAILED", error=str(error), validation={"passed": False})

    def get_track_status(self, track_id):
        """Return a human-readable summary of a track's progress."""
        track = self.get_track(track_id)
        if not track:
            return None
        tasks = self.list_tasks(track_id)
        completed = sum(1 for t in tasks if t["status"] == "COMPLETED")
        total = len(tasks)
        return f"Track '{track['name']}' is {track['status']} ({completed}/{total} tasks completed). Progress: {track['progress']}%"


class FeedbackManager(TaskDatabaseMixin):
    def record_feedback(self, track_id, task_id, decision, message=""):
        record = (str(uuid.uuid4()), track_id, task_id, decision, message, _now())
        with self._session() as connection:
            connection.execute("INSERT INTO task_feedback VALUES (?, ?, ?, ?, ?, ?)", record)
        return dict(zip(("feedback_id", "track_id", "task_id", "decision", "message", "created_at"), record))


class RetryManager:
    def __init__(self, max_attempts=3, db_path=None):
        self.max_attempts = max_attempts
        self.db_path = db_path

    def run_with_retry(self, task, function, *args, **kwargs):
        last_error = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = function(task, *args, **kwargs)
                return {"status": "completed", "attempts": attempt, "result": result}
            except Exception as error:
                last_error = error
        return {"status": "failed", "attempts": self.max_attempts, "error": str(last_error)}


class VerificationEngine(TaskManager):
    def verify_track(self, track_id):
        track = self.get_track(track_id)
        tasks = self.list_tasks(track_id)
        issues = [] if track and tasks else ["Track or tasks are missing."]
        issues.extend(f"Task '{task['title']}' is {task['status'].lower()}." for task in tasks if task["status"] != "COMPLETED")
        return {"passed": not issues, "issues": issues, "warnings": [], "recommendations": []}


class TaskContextManager(TaskManager):
    def build_context(self, track_id, task_id=None):
        track = self.get_track(track_id)
        return {"track": track, "current_task": self.get_task(track_id, task_id) if task_id else None,
                "completed_tasks": [task for task in self.list_tasks(track_id) if task["status"] == "COMPLETED"]}


class TrackManager(TaskManager):
    def resume_track(self, track_id):
        return {"track": self.get_track(track_id), "tasks": self.list_tasks(track_id),
                "progress": ProgressManager(self.db_path).get_progress(track_id)}


__all__ = ["FeedbackManager", "ProgressManager", "RetryManager", "TaskContextManager", "TaskExecutor", "TaskManager", "TrackManager", "VerificationEngine"]
