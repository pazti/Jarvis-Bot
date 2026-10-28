"""Scheduled, policy-gated proactive messages."""

import os
import sqlite3
import threading
import time
from datetime import datetime, time as datetime_time, timedelta, timezone

from modules import config
from modules.task_orchestration import TaskManager
from modules.tts import is_speaking, speak

_TRACK_LOOKBACK_DAYS = 7


def _connect(db_path=None):
    target = db_path or config.MEMORY_DB_PATH
    directory = os.path.dirname(target)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    connection = sqlite3.connect(target, timeout=10, check_same_thread=False)
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_schema(db_path=None):
    connection = _connect(db_path)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS proactive_timers (
                timer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                due_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                delivered_at TEXT
            )
            """
        )
        connection.commit()
    except sqlite3.Error as error:
        raise RuntimeError(f"Could not initialize the proactive timer store: {error}") from error
    finally:
        connection.close()


def schedule_timer(duration_seconds, label, db_path=None):
    """Persist a timer requested by the user."""
    if (
        isinstance(duration_seconds, bool)
        or not isinstance(duration_seconds, int)
        or duration_seconds < 1
    ):
        raise ValueError("Timer duration must be a positive integer number of seconds.")
    if not isinstance(label, str) or not label.strip():
        raise ValueError("Timer label must be a non-empty string.")

    _ensure_schema(db_path)
    now = datetime.now(timezone.utc)
    due_at = (now + timedelta(seconds=duration_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
    created_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    connection = _connect(db_path)
    try:
        cursor = connection.execute(
            "INSERT INTO proactive_timers (label, due_at, created_at) VALUES (?, ?, ?)",
            (label.strip(), due_at, created_at),
        )
        connection.commit()
        return cursor.lastrowid
    except sqlite3.Error as error:
        raise RuntimeError(f"Could not save the timer: {error}") from error
    finally:
        connection.close()


def _get_due_timers(db_path=None, now=None):
    _ensure_schema(db_path)
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    timestamp = current_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    connection = _connect(db_path)
    try:
        rows = connection.execute(
            """
            SELECT timer_id, label FROM proactive_timers
            WHERE delivered_at IS NULL AND due_at <= ?
            ORDER BY due_at, timer_id LIMIT 1
            """,
            (timestamp,),
        ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as error:
        raise RuntimeError(f"Could not read due timers: {error}") from error
    finally:
        connection.close()


def _mark_timer_delivered(timer_id, db_path=None):
    connection = _connect(db_path)
    try:
        connection.execute(
            "UPDATE proactive_timers SET delivered_at = ? WHERE timer_id = ? AND delivered_at IS NULL",
            (
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                timer_id,
            ),
        )
        connection.commit()
    except sqlite3.Error as error:
        raise RuntimeError(f"Could not mark timer {timer_id} as delivered: {error}") from error
    finally:
        connection.close()


def _parse_quiet_hours(value):
    if not value.strip():
        return None
    try:
        start, end = (
            datetime_time.fromisoformat(part.strip())
            for part in value.split("-", 1)
        )
    except (TypeError, ValueError) as error:
        raise ValueError(
            "PROACTIVE_QUIET_HOURS must use 'HH:MM-HH:MM' local time or be empty."
        ) from error
    if start.tzinfo is not None or end.tzinfo is not None or start == end:
        raise ValueError(
            "PROACTIVE_QUIET_HOURS must use two different local times in 'HH:MM-HH:MM' format."
        )
    return start, end


def _is_quiet_hours(now, quiet_period):
    if quiet_period is None:
        return False
    start, end = quiet_period
    current_time = now.timetz().replace(tzinfo=None)
    if start < end:
        return start <= current_time < end
    return current_time >= start or current_time < end


class ProactiveRuntime:
    def __init__(self, callbacks, get_application_state, db_path=None):
        self.callbacks = callbacks
        self.get_application_state = get_application_state
        self.db_path = db_path or config.MEMORY_DB_PATH
        self.poll_seconds = config.PROACTIVE_POLL_SECONDS
        self.idle_seconds = config.PROACTIVE_IDLE_MINUTES * 60
        self.cooldown_seconds = config.PROACTIVE_COOLDOWN_MINUTES * 60
        self.enabled = config.PROACTIVE_ENABLED
        self.quiet_period = _parse_quiet_hours(config.PROACTIVE_QUIET_HOURS)
        if self.poll_seconds < 1:
            raise ValueError("PROACTIVE_POLL_SECONDS must be at least 1.")
        if self.idle_seconds < 0:
            raise ValueError("PROACTIVE_IDLE_MINUTES cannot be negative.")
        if self.cooldown_seconds < 0:
            raise ValueError("PROACTIVE_COOLDOWN_MINUTES cannot be negative.")

        self._stop_event = threading.Event()
        self._thread = None
        self._tick_lock = threading.Lock()
        self._activity_lock = threading.Lock()
        self._last_user_activity = time.monotonic()
        self._last_proactive_delivery = 0.0
        self._delivered_track_ids = set()

    def note_user_activity(self):
        with self._activity_lock:
            self._last_user_activity = time.monotonic()

    def start(self):
        _ensure_schema(self.db_path)
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="jarvis-proactive",
            daemon=True,
        )
        self._thread.start()
        if not self.enabled:
            print("[PROACTIVE] Workflow follow-ups are disabled; requested timers remain active.")

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1, self.poll_seconds + 1))
            if self._thread.is_alive():
                print("[PROACTIVE] Runtime did not stop before the shutdown timeout.")
            else:
                self._thread = None

    def _run(self):
        while not self._stop_event.wait(self.poll_seconds):
            try:
                self.tick()
            except Exception as error:
                print(f"[PROACTIVE] Scheduler error: {error}")

    def tick(self, now_monotonic=None, wall_now=None):
        """Check current policy and deliver at most one proactive message."""
        if not self._tick_lock.acquire(blocking=False):
            return False
        try:
            monotonic_now = time.monotonic() if now_monotonic is None else now_monotonic
            current_time = wall_now or datetime.now().astimezone()
            state = self.get_application_state()
            if (
                state.get("busy", False)
                or state.get("muted", False)
                or state.get("sleeping", False)
                or is_speaking()
                or _is_quiet_hours(current_time, self.quiet_period)
            ):
                return False

            due_timers = _get_due_timers(self.db_path)
            if due_timers:
                timer = due_timers[0]
                message = f"Your timer for {timer['label']} has finished."
                if self._deliver(message):
                    _mark_timer_delivered(timer["timer_id"], self.db_path)
                    self._last_proactive_delivery = monotonic_now
                    return True
                return False

            if not self.enabled:
                return False
            with self._activity_lock:
                last_activity = self._last_user_activity
            if monotonic_now - last_activity < self.idle_seconds:
                return False
            if monotonic_now - self._last_proactive_delivery < self.cooldown_seconds:
                return False

            updated_since = (
                datetime.now(timezone.utc) - timedelta(days=_TRACK_LOOKBACK_DAYS)
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
            tracks = TaskManager(db_path=self.db_path).list_incomplete_tracks(
                limit=20,
                updated_since=updated_since,
            )
            track = next(
                (
                    candidate
                    for candidate in tracks
                    if candidate["track_id"] not in self._delivered_track_ids
                ),
                None,
            )
            if track is None:
                return False

            message = (
                f"Your workflow '{track['name']}' is still unfinished. "
                "Would you like to continue it?"
            )
            if self._deliver(message):
                self._delivered_track_ids.add(track["track_id"])
                self._last_proactive_delivery = monotonic_now
                return True
            return False
        finally:
            self._tick_lock.release()

    def _deliver(self, message):
        try:
            self.callbacks["processing"](True)
            self.callbacks["skip_audio"](True)
            self.callbacks["status"](f"{config.ASSISTANT_NAME} has an update.")
            self.callbacks["response"](message)
            speak(message)
            return True
        except Exception as error:
            print(f"[PROACTIVE] Could not deliver message: {error}")
            return False
        finally:
            for callback_name, value in (("processing", False), ("skip_audio", False)):
                try:
                    self.callbacks[callback_name](value)
                except Exception as error:
                    print(f"[PROACTIVE] Could not reset {callback_name}: {error}")
            try:
                self.callbacks["status"]("Listening...")
            except Exception as error:
                print(f"[PROACTIVE] Could not reset listening status: {error}")
