import logging
import re
import sqlite3

from modules.config import MEMORY_DB_PATH
from modules.memory import (
    clear_memory,
    create_session_summary,
    forget_memory,
    get_memory_summary,
    remember_memory,
    save_fact,
)

logger = logging.getLogger(__name__)


def _finish_action(callbacks, message, status=None):
    if not callbacks:
        return
    callbacks["response"](message)
    if status:
        callbacks["status"](status)
    callbacks["processing"](False)
    callbacks["skip_audio"](False)


def quick_note(prompt, update_callbacks=None, db_path=None):
    cleaned = re.sub(
        r"(?i)^create a quick note\s*[:\-]?\s*|^quick note\s*[:\-]?\s*|^create a note\s*[:\-]?\s*|^write a quick note\s*[:\-]?\s*",
        "",
        prompt or "",
    ).strip()
    text = cleaned or "Follow up on the current task and keep your next step visible."
    result = remember_memory(f"Note: {text}", db_path=db_path or MEMORY_DB_PATH)
    message = f"Quick note saved: {text}" if result else "I had trouble saving the note."
    _finish_action(update_callbacks, message)
    return message


def sleep(update_callbacks=None, groq_client=None, db_path=None):
    sleep_message = "Entering sleep mode, Sir."
    if not update_callbacks:
        return sleep_message

    summary = None
    if groq_client:
        try:
            summary = create_session_summary(groq_client, db_path=db_path)
        except (OSError, RuntimeError, ValueError, sqlite3.Error):
            logger.exception("Error creating session summary")

    if summary:
        summary_message = (
            f"Here's what we discussed today: {summary}\n\n"
            "Would you like me to save this as a memory, Sir?"
        )
        _finish_action(
            update_callbacks,
            summary_message,
            "Ready to save memory or sleep - Waiting for your response...",
        )
        return summary_message

    update_callbacks["response"](sleep_message)
    update_callbacks["status"]("JARVIS sleeping...")
    if "set_sleeping" in update_callbacks:
        update_callbacks["set_sleeping"](True)
    update_callbacks["processing"](False)
    update_callbacks["skip_audio"](False)
    return sleep_message


def wake(update_callbacks=None):
    message = "Hello, Sir. JARVIS is awake."
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["status"]("Listening... Speak into your mic, Sir!")
        if "set_sleeping" in update_callbacks:
            update_callbacks["set_sleeping"](False)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def show_memory(prompt, update_callbacks=None, db_path=None):
    lower = (prompt or "").lower()
    if "work" in lower:
        category = "work"
    elif "personal" in lower:
        category = "personal"
    elif "developer" in lower or "coding" in lower or "programming" in lower:
        category = "developer_preferences"
    else:
        category = "general"

    summary = get_memory_summary(db_path=db_path or MEMORY_DB_PATH, category=category)
    _finish_action(update_callbacks, summary)
    return summary


def clear_all_memory(update_callbacks=None, db_path=None):
    clear_memory(db_path=db_path or MEMORY_DB_PATH)
    _finish_action(update_callbacks, "Memory cleared.")
    return "MEMORY_CLEARED"


def remember(prompt, update_callbacks=None, db_path=None):
    result = remember_memory(prompt, db_path=db_path or MEMORY_DB_PATH)
    message = f"Memory saved: {result}" if result else "I saved that memory."
    _finish_action(update_callbacks, message)
    return message


def forget(prompt, update_callbacks=None, db_path=None):
    success = forget_memory(prompt, db_path=db_path or MEMORY_DB_PATH)
    message = (
        "I cleared the matching memory entry."
        if success
        else "I could not find that memory to remove."
    )
    _finish_action(update_callbacks, message)
    return message


def save_summary(groq_client=None, update_callbacks=None, db_path=None):
    if update_callbacks:
        try:
            if groq_client:
                summary = create_session_summary(groq_client, db_path=db_path)
                save_fact(
                    "session_summary",
                    summary,
                    category="general",
                    db_path=db_path,
                )
                message = f"Saved: {summary}"
            else:
                message = "Could not create summary without API access."

            update_callbacks["response"](message)
            update_callbacks["status"]("Summary saved. Entering sleep mode...")
            if "set_sleeping" in update_callbacks:
                update_callbacks["set_sleeping"](True)
            update_callbacks["processing"](False)
            update_callbacks["skip_audio"](False)
        except (OSError, RuntimeError, ValueError, sqlite3.Error):
            logger.exception("Error saving summary")
            message = "I had trouble saving that memory, Sir."
            update_callbacks["response"](message)
            update_callbacks["processing"](False)
            update_callbacks["skip_audio"](False)
    return "SLEEP"


def decline_summary(update_callbacks=None):
    if update_callbacks:
        message = "Understood, Sir. Entering sleep mode without saving."
        update_callbacks["response"](message)
        update_callbacks["status"]("JARVIS sleeping...")
        if "set_sleeping" in update_callbacks:
            update_callbacks["set_sleeping"](True)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return "SLEEP"
