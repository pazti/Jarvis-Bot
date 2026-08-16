import os
import re
import sqlite3

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "jarvis_memory.db")
_ACTIVE_DB_PATH = DEFAULT_DB_PATH

MEMORY_CATEGORIES = {
    "general": "general",
    "work": "work",
    "personal": "personal",
    "developer_preferences": "developer_preferences",
    "developer": "developer_preferences",
    "memory": "memory",
    "preference": "preference",
}


def _resolve_db_path(db_path=None):
    return db_path or _ACTIVE_DB_PATH


def _connect(db_path=None):
    target = _resolve_db_path(db_path)
    directory = os.path.dirname(target)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    connection = sqlite3.connect(target)
    connection.row_factory = sqlite3.Row
    return connection


def _normalize_category(category):
    if not category:
        return "general"
    key = category.strip().lower().replace(" ", "_")
    return MEMORY_CATEGORIES.get(key, key if key else "general")


def init_memory_db(db_path=None):
    global _ACTIVE_DB_PATH
    _ACTIVE_DB_PATH = db_path or _ACTIVE_DB_PATH
    connection = _connect(_ACTIVE_DB_PATH)
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            value TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()
    connection.close()


def save_message(role, content, db_path=None):
    init_memory_db(db_path)
    connection = _connect(_resolve_db_path(db_path))
    connection.execute(
        "INSERT INTO conversation (role, content) VALUES (?, ?)",
        (role, content),
    )
    connection.commit()
    connection.close()


def get_recent_conversation(db_path=None, limit=10):
    init_memory_db(db_path)
    connection = _connect(_resolve_db_path(db_path))
    rows = connection.execute(
        "SELECT role, content, created_at FROM conversation ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    connection.close()

    return [dict(row) for row in reversed(rows)]


def save_fact(key, value, category="general", db_path=None):
    init_memory_db(db_path)
    category = _normalize_category(category)
    connection = _connect(_resolve_db_path(db_path))
    connection.execute(
        """
        INSERT INTO memory_facts (key, value, category, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key)
        DO UPDATE SET value = excluded.value, category = excluded.category, updated_at = CURRENT_TIMESTAMP
        """,
        (key, value, category),
    )
    connection.commit()
    connection.close()


def get_facts(db_path=None, limit=20, category=None):
    init_memory_db(db_path)
    connection = _connect(_resolve_db_path(db_path))
    if category:
        category = _normalize_category(category)
        rows = connection.execute(
            "SELECT key, value, category, updated_at FROM memory_facts WHERE category = ? ORDER BY updated_at DESC LIMIT ?",
            (category, limit),
        ).fetchall()
    else:
        rows = connection.execute(
            "SELECT key, value, category, updated_at FROM memory_facts ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    connection.close()
    return [dict(row) for row in rows]


def get_memory_summary(db_path=None, category=None):
    facts = get_facts(db_path=db_path, limit=50, category=category)
    if not facts:
        if category:
            return f"No saved memory in the {category} category yet."
        return "No saved memory yet."

    lines = [f"{fact['key']}: {fact['value']}" for fact in facts]
    return " | ".join(lines)


def _normalize_key(value):
    cleaned = re.sub(r"[^a-z0-9_\s]", "", value.lower().strip())
    cleaned = cleaned.replace(" ", "_")
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "user_note"


def _detect_category(prompt):
    lower = (prompt or "").lower()
    if "work" in lower:
        return "work"
    if "personal" in lower:
        return "personal"
    if "developer" in lower or "programming" in lower or "coding" in lower or "stack" in lower:
        return "developer_preferences"
    return "general"


def extract_fact_from_prompt(prompt, db_path=None):
    text = (prompt or "").strip()
    if not text:
        return None

    lower = text.lower()
    category = _detect_category(text)

    if "remember this" in lower or "remember that" in lower:
        reminder = text.split(":", 1)[-1].strip() if ":" in text else text.replace("remember this", "").replace("remember that", "").strip()
        if reminder:
            key = "user_note" if category == "general" else f"{category}_note"
            save_fact(key, reminder, category=category, db_path=db_path)
            return {"key": key, "value": reminder, "category": category}

    match = re.search(r"(?:my\s+)?([a-zA-Z0-9_\s]+?)\s+(?:is|are|equals|=)\s+(.+)", text, flags=re.IGNORECASE)
    if match:
        key_text = match.group(1).strip()
        value_text = match.group(2).strip().strip(".?!")
        if value_text and key_text:
            if key_text.lower() in {"i", "myself"}:
                return None
            key = _normalize_key(key_text)
            save_fact(key, value_text, category=category, db_path=db_path)
            return {"key": key, "value": value_text, "category": category}

    keywords = ["prefer", "like", "love", "hate", "need", "want", "favorite", "favourite"]
    for keyword in keywords:
        pattern = rf"(?:i\s+{keyword}\s+)(.+?)(?:[.;!?]|$)"
        match = re.search(pattern, lower, flags=re.IGNORECASE)
        if match:
            value_text = match.group(1).strip().strip(".?!")
            key = f"preference_{keyword}"
            save_fact(key, value_text, category=category, db_path=db_path)
            return {"key": key, "value": value_text, "category": category}

    return None


def remember_memory(prompt, db_path=None):
    result = extract_fact_from_prompt(prompt, db_path=db_path)
    if result:
        return result["value"]
    return None


def forget_memory(prompt, db_path=None):
    text = (prompt or "").strip()
    if not text:
        return False

    lower = text.lower()
    if "forget that" not in lower and "forget" not in lower:
        return False

    match = re.search(r"forget\s+(?:that\s+)?(.+)", lower)
    if not match:
        return False

    target = match.group(1).strip().strip(".?!")

    category = None
    if "work" in target:
        category = "work"
    elif "personal" in target:
        category = "personal"
    elif "developer" in target or "coding" in target or "programming" in target:
        category = "developer_preferences"

    target_key = _normalize_key(target)
    target_value = target.lower().strip()

    init_memory_db(db_path)
    connection = _connect(_resolve_db_path(db_path))
    if category:
        cursor = connection.execute(
            "DELETE FROM memory_facts WHERE category = ?",
            (_normalize_category(category),),
        )
        connection.commit()
        connection.close()
        return cursor.rowcount > 0

    rows = connection.execute(
        "SELECT key, value FROM memory_facts"
    ).fetchall()
    matching_keys = []
    for row in rows:
        key = row["key"]
        value = row["value"].lower()
        if key == target_key or target_key in key or target_value in value or value in target_value:
            matching_keys.append(key)

    if matching_keys:
        placeholders = ", ".join("?" for _ in matching_keys)
        cursor = connection.execute(
            f"DELETE FROM memory_facts WHERE key IN ({placeholders})",
            matching_keys,
        )
    else:
        cursor = connection.execute("DELETE FROM memory_facts WHERE key = ?", (target_key,))

    connection.commit()
    connection.close()
    return cursor.rowcount > 0


def build_memory_context(db_path=None, recent_limit=8, fact_limit=10):
    recent_messages = get_recent_conversation(db_path=db_path, limit=recent_limit)
    facts = get_facts(db_path=db_path, limit=fact_limit)

    parts = []
    if recent_messages:
        parts.append("Recent conversation:")
        for message in recent_messages:
            parts.append(f"- {message['role'].title()}: {message['content']}")

    if facts:
        parts.append("Relevant memory facts:")
        for fact in facts:
            parts.append(f"- {fact['key']}: {fact['value']} ({fact['category']})")

    return "\n".join(parts)


def remember_from_prompt(prompt, db_path=None):
    return remember_memory(prompt, db_path=db_path)


def build_summary_from_conversation(messages):
    if not messages:
        return "No recent conversation history."

    summary_items = []
    for item in messages:
        content = str(item.get("content", "")).strip()
        if content:
            summary_items.append(content)

    return " | ".join(summary_items[-8:])


def trim_conversation_for_summary(db_path=None, max_messages=10):
    init_memory_db(db_path)
    connection = _connect(_resolve_db_path(db_path))

    total_rows = connection.execute("SELECT COUNT(*) FROM conversation").fetchone()[0]
    if total_rows > max_messages:
        old_rows = connection.execute(
            "SELECT id FROM conversation ORDER BY id ASC LIMIT ?",
            (total_rows - max_messages,),
        ).fetchall()
        if old_rows:
            ids = [row["id"] for row in old_rows]
            placeholders = ", ".join("?" for _ in ids)
            connection.execute(
                f"DELETE FROM conversation WHERE id IN ({placeholders})",
                ids,
            )

    rows = connection.execute(
        "SELECT id, role, content FROM conversation ORDER BY id DESC LIMIT ?",
        (max_messages,),
    ).fetchall()
    connection.commit()
    connection.close()

    if not rows:
        return "No conversation to summarize."

    recent = [dict(row) for row in reversed(rows)]
    return build_summary_from_conversation(recent)


def clear_memory(db_path=None):
    init_memory_db(db_path)
    connection = _connect(_resolve_db_path(db_path))
    connection.execute("DELETE FROM conversation")
    connection.execute("DELETE FROM memory_facts")
    connection.commit()
    connection.close()
