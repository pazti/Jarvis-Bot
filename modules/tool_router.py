"""Strict local command routing and structured Groq tool dispatch."""

import json
import os
import re
import subprocess
import threading
import time

from modules import actions, config
from modules.memory import forget_memory, get_memory_summary, save_fact
from modules.worldview import (
    get_recent_reflections,
    get_worldview_position,
    get_worldview_position_history,
    has_worldview_profile_consent,
    reflect_on_worldviews,
    search_worldview_knowledge,
    set_worldview_profile_consent,
)
from modules.worldview_research import (
    create_research_run,
    get_research_status,
    start_research_worker,
    stop_research,
)


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "start_worldview_research",
            "description": "Start a persistent, bounded worldview research run only when the user explicitly asks to research a question over days or weeks. It uses web search and reads local books from worldview_sources/; it creates analytical updates, not a personal religious identity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "maxLength": 500},
                    "duration_days": {"type": "integer", "minimum": 1, "maximum": 30},
                    "interval_hours": {"type": "integer", "minimum": 6, "maximum": 168},
                },
                "required": ["topic", "duration_days", "interval_hours"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_worldview_research_status",
            "description": "Show the current or most recent multi-day worldview research run and its latest provisional assessment when the user asks for status or progress.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stop_worldview_research",
            "description": "Stop the active multi-day worldview research run only when the user asks to stop, cancel, or pause it.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_worldview_profile",
            "description": (
                "Check, explicitly consent to, or revoke the configured user's "
                "worldview-analysis profile. Before consent, disclose that research "
                "queries and snippets are sent to Groq and conclusions/source links "
                "are stored in the local, unencrypted SQLite database. Grant consent "
                "only if the user clearly says they consent or agree to this storage "
                "and processing. Revoking consent deletes this user's saved conclusion, "
                "history, and selection-study research records."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["consent", "revoke", "status"],
                    }
                },
                "required": ["operation"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_worldview_selection",
            "description": (
                "Start a resumable multi-day comparison of religious and nonreligious "
                "worldviews only when the user explicitly asks Jarvis to choose or pick "
                "a religion/worldview for its analytical position. This records a "
                "provisional, revisable analysis for the configured local user profile, "
                "not personal faith, lived experience, or a genuine autonomous choice. "
                "Default to 14 days and 24-hour intervals if the user did not specify."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "maxLength": 500},
                    "duration_days": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 30,
                    },
                    "interval_hours": {
                        "type": "integer",
                        "minimum": 6,
                        "maximum": 168,
                    },
                },
                "required": ["topic"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_worldview_position",
            "description": (
                "Retrieve Jarvis's saved analytical worldview conclusion for the "
                "configured local user profile when asked what religion/worldview it "
                "has chosen, what its current position is, or why its analysis changed. "
                "Always explain that this is a provisional AI analysis, not actual faith "
                "or lived experience. If there is no saved conclusion, say so plainly."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_worldview_position_history",
            "description": (
                "Retrieve the configured user's saved analytical worldview history "
                "when asked for earlier conclusions or a detailed explanation of "
                "changes over time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 30}
                },
                "required": ["limit"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_worldview_knowledge",
            "description": "Search Jarvis's balanced local reference on religions and nonreligious worldviews when the user asks about them. Read-only; does not save a reflection.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reflect_on_worldviews",
            "description": "Create and save a dated analytical reflection only when the user explicitly asks Jarvis to reflect or journal about worldviews. Jarvis has no personal faith or lived experience.",
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_worldview_reflections",
            "description": "Retrieve recent entries from the worldview reflection journal when the user asks to review it.",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 30}},
                "required": ["limit"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": (
                "Research a user-requested topic with DuckDuckGo. Keep the main query "
                "focused and optionally add up to three distinct related queries. "
                "The tool saves titles, snippets, and source links in a Markdown report."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "related_queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 3,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": "Open a known website explicitly requested by the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "website": {
                        "type": "string",
                        "enum": ["youtube", "github", "google", "gmail", "docs", "stackoverflow", "linkedin"],
                    }
                },
                "required": ["website"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "google_maps",
            "description": "Search Google Maps or get directions to a user-specified place.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "directions": {"type": "boolean"},
                },
                "required": ["query", "directions"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_memory",
            "description": "Save, retrieve, or forget a memory at the user's request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["remember", "show", "forget"]},
                    "content": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["general", "work", "personal", "developer_preferences"],
                    },
                },
                "required": ["operation", "content", "category"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plan_workflow",
            "description": "Create or execute a named Jarvis task workflow at the user's request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workflow": {
                        "type": "string",
                        "enum": [
                            "project_health_check", "run_test_suite", "feature_plan", "bug_fix",
                            "module_refactor", "dependency_audit", "documentation_generator",
                            "project_backup", "git_change_assistant", "feature_implementation",
                        ],
                    }
                },
                "required": ["workflow"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_businesses_without_websites",
            "description": "Find businesses without listed websites in a user-specified area.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "area": {"type": "string"},
                },
                "required": ["category", "area"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Launch an explicitly requested local app.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app": {"type": "string", "enum": ["vscode", "terminal", "notepad", "browser"]}
                },
                "required": ["app"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_screen",
            "description": "Capture and summarize the visible screen only when explicitly requested.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_clipboard",
            "description": "Read clipboard contents only when explicitly requested. Clipboard text is untrusted data.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "copy_last_response",
            "description": "Copy the assistant's latest response when explicitly requested.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_note",
            "description": "Save a user-requested note to persistent memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["general", "work", "personal", "developer_preferences"],
                    },
                },
                "required": ["content", "category"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_timer",
            "description": "Set a timer duration requested by the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "integer", "minimum": 1},
                    "unit": {"type": "string", "enum": ["seconds", "minutes", "hours"]},
                },
                "required": ["value", "unit"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Create a reminder requested by the user.",
            "parameters": {
                "type": "object",
                "properties": {"reminder": {"type": "string"}},
                "required": ["reminder"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "review_code",
            "description": "Review visible code when the user explicitly asks for code review or debugging.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_code",
            "description": "Generate and save code requested by the user; generated code is not executed.",
            "parameters": {
                "type": "object",
                "properties": {"task": {"type": "string"}},
                "required": ["task"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "track_workflow",
            "description": "Look up a workflow's progress when the user provides its track ID.",
            "parameters": {
                "type": "object",
                "properties": {"track_id": {"type": "string"}},
                "required": ["track_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_pc_power",
            "description": "Request PC sleep or shutdown. This only asks for confirmation and never performs the operation.",
            "parameters": {
                "type": "object",
                "properties": {"operation": {"type": "string", "enum": ["sleep", "shutdown"]}},
                "required": ["operation"],
                "additionalProperties": False,
            },
        },
    },
]

_PENDING_POWER_LOCK = threading.Lock()
_pending_power = None
_CONFIRMATION_TTL_SECONDS = 60
_AFFIRMATIVE = {"yes", "yes confirm", "confirm", "confirm yes", "do it"}
_NEGATIVE = {"no", "cancel", "no cancel", "never mind", "nevermind"}


def _normalize_phrase(text):
    normalized = (text or "").casefold()
    normalized = re.sub(r"[.!?,;:]+", " ", normalized)
    return " ".join(normalized.split())


def _finish(message, callbacks, status=None):
    if callbacks:
        callbacks["response"](message)
        if status and "status" in callbacks:
            callbacks["status"](status)
        if "processing" in callbacks:
            callbacks["processing"](False)
        if "skip_audio" in callbacks:
            callbacks["skip_audio"](False)
    return message


def _request_pc_power(operation):
    global _pending_power
    if operation not in {"sleep", "shutdown"}:
        raise ValueError(f"Unsupported PC power operation: {operation}")
    with _PENDING_POWER_LOCK:
        _pending_power = (operation, time.monotonic())
    name = "sleep" if operation == "sleep" else "shut down"
    return f"Please confirm: should I {name} this PC? Say 'confirm' or 'cancel'."


def _resolve_pc_power_confirmation(phrase, callbacks):
    global _pending_power
    with _PENDING_POWER_LOCK:
        pending = _pending_power
        if pending is None:
            return None
        operation, requested_at = pending
        if time.monotonic() - requested_at > _CONFIRMATION_TTL_SECONDS:
            _pending_power = None
            return _finish("That PC power confirmation expired. Please ask again.", callbacks)
        if phrase not in _AFFIRMATIVE and phrase not in _NEGATIVE:
            return None
        _pending_power = None

    if phrase in _NEGATIVE:
        return _finish("Cancelled. The PC will remain on.", callbacks)

    try:
        if operation == "sleep":
            command = (
                ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"]
                if os.name == "nt"
                else ["systemctl", "suspend"]
            )
            subprocess.Popen(command)
            message = "Confirmed. The PC is going to sleep."
        else:
            command = (
                ["shutdown", "/s", "/t", "0"]
                if os.name == "nt"
                else ["shutdown", "-h", "now"]
            )
            subprocess.run(command, check=True, timeout=10)
            message = "Confirmed. The PC is shutting down."
    except (OSError, subprocess.SubprocessError) as error:
        message = f"I could not {operation} the PC: {error}"
    return _finish(message, callbacks)


def route_local_action(prompt, update_callbacks=None):
    """Handle only exact, low-risk local phrases; all other requests go to the LLM."""
    phrase = _normalize_phrase(prompt)
    confirmed = _resolve_pc_power_confirmation(phrase, update_callbacks)
    if confirmed is not None:
        return confirmed

    explicit_profile_consent = re.search(
        r"\bi\s+(?:explicitly\s+)?consent\s+to\s+storing\b.{0,100}"
        r"\b(?:locally|local)\b.{0,100}\b(?:groq|external model|language model)\b",
        prompt or "",
        flags=re.IGNORECASE,
    )
    if explicit_profile_consent:
        try:
            result = execute_tool(
                "manage_worldview_profile",
                {"operation": "consent"},
                user_prompt=prompt,
            )
        except ValueError as error:
            return _finish(str(error), update_callbacks)
        return _finish(result, update_callbacks)

    starts_selection_study = re.search(
        r"\b(?:start|begin|run|launch)\b.{0,50}"
        r"\b(?:worldview|religion|religious|faith)\b.{0,40}"
        r"\b(?:selection|study|comparison|research)\b",
        prompt or "",
        flags=re.IGNORECASE,
    )
    chooses_for_analysis = (
        re.search(r"\b(?:choose|pick|select|evaluate)\b", prompt or "", re.IGNORECASE)
        and re.search(r"\b(?:religions?|worldviews?|faiths?)\b", prompt or "", re.IGNORECASE)
        and re.search(r"\b(?:analysis|analytical|selection|study)\b", prompt or "", re.IGNORECASE)
    )
    if starts_selection_study or chooses_for_analysis:
        try:
            from modules.brain import client as groq_client

            result = execute_tool(
                "start_worldview_selection",
                {
                    "topic": (
                        "Compare major religious and nonreligious worldviews, including "
                        "their accounts of existence, ethics, and described community "
                        "and practices. Record evidence, uncertainty, and reasons for "
                        "any change in the provisional analytical conclusion."
                    ),
                    "duration_days": 14,
                    "interval_hours": 24,
                },
                groq_client=groq_client,
                user_prompt=prompt,
            )
        except ValueError as error:
            return _finish(str(error), update_callbacks)
        return _finish(result, update_callbacks)

    asks_saved_position = re.search(
        r"\b(?:what|which|tell me|do you have)\b.{0,50}"
        r"\b(?:your|jarvis(?:'s)?)\b.{0,30}"
        r"\b(?:religion|worldview|faith|position|conclusion)\b",
        prompt or "",
        flags=re.IGNORECASE,
    )
    if asks_saved_position:
        result = execute_tool("get_worldview_position", {})
        return _finish(result, update_callbacks)

    assistant = _normalize_phrase(config.ASSISTANT_NAME)
    aliases = {assistant, "assistant"}
    time_phrases = {"what time is it", "what is the time", "tell me the time", "current time"}
    mute_phrases = {"mute", "mute microphone", "mute the microphone", "mute mic", "mute the mic"}
    unmute_phrases = {
        "unmute", "unmute microphone", "unmute the microphone", "unmute mic", "unmute the mic",
        "turn on microphone", "turn on the microphone",
    }
    sleep_phrases = {"sleep assistant", "go to sleep assistant", "enter sleep mode"}
    wake_phrases = {"wake assistant", "wake up assistant"}
    for name in aliases:
        time_phrases.update({f"{phrase} {name}" for phrase in tuple(time_phrases)})
        time_phrases.update({f"{name} {phrase}" for phrase in tuple(time_phrases)})
        mute_phrases.update({f"{phrase} {name}" for phrase in tuple(mute_phrases)})
        mute_phrases.update({f"{name} {phrase}" for phrase in tuple(mute_phrases)})
        unmute_phrases.update({f"{phrase} {name}" for phrase in tuple(unmute_phrases)})
        unmute_phrases.update({f"{name} {phrase}" for phrase in tuple(unmute_phrases)})
        sleep_phrases.update({f"sleep {name}", f"go to sleep {name}", f"{name} sleep", f"{name} go to sleep"})
        wake_phrases.update({f"wake {name}", f"wake up {name}", f"{name} wake up"})

    if phrase in time_phrases:
        return actions.time_action(update_callbacks)
    if phrase in mute_phrases or phrase in unmute_phrases:
        muted = phrase in mute_phrases
        if update_callbacks and "set_muted" in update_callbacks:
            update_callbacks["set_muted"](muted)
        return _finish("Microphone muted." if muted else "Microphone unmuted.", update_callbacks)
    if phrase in sleep_phrases:
        message = f"Going to sleep. Say 'Hello {config.ASSISTANT_NAME}' when you want me back."
        if update_callbacks and "set_sleeping" in update_callbacks:
            update_callbacks["set_sleeping"](True)
        return _finish(
            message,
            update_callbacks,
            status=f"{config.ASSISTANT_NAME} is sleeping...",
        )
    if phrase in wake_phrases:
        message = f"I'm awake, {config.ADDRESS_AS}."
        if update_callbacks and "set_sleeping" in update_callbacks:
            update_callbacks["set_sleeping"](False)
        return _finish(message, update_callbacks, status="Listening...")
    return None


def execute_tool(name, arguments, groq_client=None, db_path=None, user_prompt=""):
    """Validate and dispatch a model-selected tool from the fixed allowlist."""
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be a JSON object.")

    def text_argument(key):
        value = arguments.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Tool argument '{key}' must be a non-empty string.")
        return value.strip()

    if name == "start_worldview_research":
        has_start_intent = re.search(
            r"\b(start|begin|run|research|study|keep researching)\b",
            user_prompt,
            flags=re.IGNORECASE,
        )
        has_duration = re.search(
            r"\b(?:\d+|one|two|three|four)\s*(?:days?|weeks?)\b",
            user_prompt,
            flags=re.IGNORECASE,
        )
        has_negation = re.search(
            r"\b(?:do not|don't|never|without)\b.{0,50}\b(?:start|begin|run|research|study)\b",
            user_prompt,
            flags=re.IGNORECASE,
        )
        if not has_start_intent or not has_duration or has_negation:
            raise ValueError("Starting ongoing research requires an explicit user request to run research over days or weeks.")
        run = create_research_run(
            text_argument("topic"),
            duration_days=arguments.get("duration_days"),
            interval_hours=arguments.get("interval_hours"),
            db_path=db_path,
        )
        start_research_worker(groq_client, db_path=db_path)
        return (
            f"Started worldview research run {run['run_id']} for {run['duration_days']} days, "
            f"checking every {run['interval_hours']} hours. It can be stopped at any time."
        )
    if name == "get_worldview_research_status":
        run = get_research_status(db_path=db_path)
        if not run:
            return "No worldview research run has been started."
        return (
            f"Research status: {run['status']}\n"
            f"Question: {run['topic']}\n"
            f"Started: {run['started_at']}\nEnds: {run['ends_at']}\n"
            f"Completed cycles: {run['cycle_count']}\n"
            f"Latest assessment: {run['latest_assessment'] or 'No assessment generated yet.'}\n"
            f"Last error: {run['last_error'] or 'None'}"
        )
    if name == "stop_worldview_research":
        run = stop_research(db_path=db_path)
        if not run:
            return "There is no active worldview research run to stop."
        return f"Stopped worldview research run {run['run_id']}. Its saved progress remains available."
    if name == "manage_worldview_profile":
        operation = text_argument("operation")
        if operation == "status":
            if has_worldview_profile_consent(config.USER_NAME, db_path=db_path):
                return (
                    f"The configured profile '{config.USER_NAME}' has consented to "
                    "local analytical-position storage and Groq processing."
                )
            return (
                f"The configured profile '{config.USER_NAME}' has not consented. "
                "No selection study or persistent worldview profile will be started."
            )
        if operation == "consent":
            consent_phrase = re.search(
                r"\b(?:i consent|i agree|i explicitly consent|i explicitly agree)\b",
                user_prompt,
                flags=re.IGNORECASE,
            )
            local_storage_scope = re.search(
                r"\b(?:store|storing|save|saving|storage)\b.{0,60}\b(?:locally|local|database)\b",
                user_prompt,
                flags=re.IGNORECASE,
            )
            external_processing_scope = re.search(
                r"\b(?:groq|external model|language model)\b",
                user_prompt,
                flags=re.IGNORECASE,
            )
            negated_consent = re.search(
                r"\b(?:do not|don't|never|not)\b.{0,30}\b(?:consent|agree)\b",
                user_prompt,
                flags=re.IGNORECASE,
            )
            if (
                not consent_phrase
                or not local_storage_scope
                or not external_processing_scope
                or negated_consent
            ):
                raise ValueError(
                    "Informed profile consent requires the user to explicitly agree to "
                    "local storage and Groq research processing. Say: 'I consent to "
                    "storing my worldview analysis locally and processing its research with Groq.'"
                )
            set_worldview_profile_consent(
                config.USER_NAME,
                True,
                db_path=db_path,
            )
            return (
                f"Consent saved for the configured profile '{config.USER_NAME}'. "
                "Worldview study queries and excerpts may be sent to Groq; conclusions "
                "and source links are stored in the local, unencrypted database. "
                "This is an analytical profile, not genuine faith or lived experience. "
                "Say 'revoke my worldview profile consent' to delete it."
            )
        if operation == "revoke":
            revoke_phrase = re.search(
                r"\b(?:revoke|withdraw|delete|remove|disable|forget)\b",
                user_prompt,
                flags=re.IGNORECASE,
            )
            profile_scope = re.search(
                r"\b(?:worldview|religion|faith|profile)\b",
                user_prompt,
                flags=re.IGNORECASE,
            )
            if not revoke_phrase or not profile_scope:
                raise ValueError(
                    "Revoking profile consent requires an explicit request to revoke "
                    "or delete this worldview profile."
                )
            from modules.worldview_research import stop_selection_for_profile

            stop_selection_for_profile(config.USER_NAME, db_path=db_path)
            set_worldview_profile_consent(
                config.USER_NAME,
                False,
                db_path=db_path,
            )
            return (
                f"Consent revoked for '{config.USER_NAME}'. The saved worldview "
                "position, its history, and that profile's selection-study records "
                "have been deleted."
            )
        raise ValueError("Unsupported worldview profile operation.")
    if name == "start_worldview_selection":
        if groq_client is None:
            raise ValueError("The configured language model is unavailable for worldview research.")
        selection_intent = re.search(
            r"\b(?:choose|pick|select|decide on)\b",
            user_prompt,
            flags=re.IGNORECASE,
        )
        study_intent = re.search(
            r"\b(?:start|begin|run|launch)\b.{0,50}"
            r"\b(?:worldview|religion|religious|faith)\b.{0,40}"
            r"\b(?:selection|study|comparison|research)\b",
            user_prompt,
            flags=re.IGNORECASE,
        )
        worldview_intent = re.search(
            r"\b(?:religion|religious|worldview|faith)\b",
            user_prompt,
            flags=re.IGNORECASE,
        )
        assistant_subject = re.search(
            rf"\b(?:you|your|yourself|assistant|{re.escape(config.ASSISTANT_NAME)})\b",
            user_prompt,
            flags=re.IGNORECASE,
        )
        negated_intent = re.search(
            r"\b(?:do not|don't|never|without)\b.{0,50}\b(?:choose|pick|select|decide)\b",
            user_prompt,
            flags=re.IGNORECASE,
        )
        if (
            not (selection_intent or study_intent)
            or not worldview_intent
            or (not study_intent and not assistant_subject)
            or negated_intent
        ):
            raise ValueError(
                "Starting an analytical worldview selection requires an explicit request "
                "for Jarvis to choose or pick a religion or worldview."
            )
        if not has_worldview_profile_consent(config.USER_NAME, db_path=db_path):
            raise ValueError(
                "No worldview profile consent is recorded. First say: 'I consent to "
                "storing my worldview analysis locally and processing its research with Groq.' "
                "That creates a profile only for the configured USER_NAME."
            )
        duration_days = arguments.get("duration_days", 14)
        interval_hours = arguments.get("interval_hours", 24)
        if isinstance(duration_days, bool) or not isinstance(duration_days, int):
            raise ValueError("Selection duration must be a whole number of days.")
        if isinstance(interval_hours, bool) or not isinstance(interval_hours, int):
            raise ValueError("Selection interval must be a whole number of hours.")
        run = create_research_run(
            text_argument("topic"),
            duration_days=duration_days,
            interval_hours=interval_hours,
            db_path=db_path,
            purpose="selection",
            profile_key=config.USER_NAME,
        )
        start_research_worker(groq_client, db_path=db_path)
        return (
            f"Started a {run['duration_days']}-day analytical worldview selection "
            f"study for this local user profile, with updates every "
            f"{run['interval_hours']} hours. The saved result will be a provisional "
            "analysis, not a claim of personal faith or experience."
        )
    if name == "get_worldview_position":
        if not has_worldview_profile_consent(config.USER_NAME, db_path=db_path):
            return (
                "No consented worldview profile is active for this configured user. "
                "I do not have personal faith or lived experience."
            )
        position = get_worldview_position(config.USER_NAME, db_path=db_path)
        if not position:
            return (
                "I do not have a personal religion or lived experience. I also do not "
                "have a saved analytical worldview conclusion for this profile yet. "
                "You can explicitly ask me to start a multi-day comparative selection study."
            )
        source_lines = [
            f"- {source.get('title') or source.get('path') or source.get('kind')}: "
            f"{source.get('url') or source.get('path') or 'local reference'}"
            for source in position["sources"]
        ] or ["- No source records were saved."]
        changed_from = (
            f"\nPrior analysis:\n{position['previous_conclusion']}"
            if position["previous_conclusion"]
            else ""
        )
        return (
            "I do not have personal faith or lived experience. My saved, provisional "
            f"analytical worldview conclusion for this profile (updated {position['updated_at']}, "
            f"research cycle {position['cycle_number']}) is:\n{position['conclusion']}"
            f"{changed_from}\nSources saved (web snippets are unverified):\n"
            + "\n".join(source_lines)
        )
    if name == "get_worldview_position_history":
        if not has_worldview_profile_consent(config.USER_NAME, db_path=db_path):
            return (
                "No consented worldview profile is active for this configured user. "
                "I do not have personal faith or lived experience."
            )
        limit = arguments.get("limit")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 30:
            raise ValueError("History limit must be an integer from 1 to 30.")
        history = get_worldview_position_history(
            config.USER_NAME,
            db_path=db_path,
            limit=limit,
        )
        if not history:
            return "There is no saved analytical worldview history for this profile."
        return "\n\n".join(
            f"{entry['created_at']} — cycle {entry['cycle_number']} "
            f"(run {entry['source_run_id']}):\n{entry['conclusion']}"
            + (
                "\nSources: "
                + "; ".join(
                    source.get("url") or source.get("path") or source.get("kind", "source")
                    for source in entry["sources"]
                )
                if entry["sources"]
                else "\nSources: no source records saved."
            )
            for entry in history
        )
    if name == "search_worldview_knowledge":
        return search_worldview_knowledge(text_argument("query"))
    if name == "reflect_on_worldviews":
        explicit_request = re.search(
            r"\b(reflect|reflection|journal|write (?:a )?(?:diary|entry))\b",
            user_prompt,
            flags=re.IGNORECASE,
        )
        negated_request = re.search(
            r"\b(?:do not|don't|never|without)\b.{0,40}\b(?:reflect|journal|diary)\b",
            user_prompt,
            flags=re.IGNORECASE,
        )
        if not explicit_request or negated_request:
            raise ValueError("Worldview journaling requires an explicit user request to reflect or journal.")
        return reflect_on_worldviews(
            groq_client,
            text_argument("question"),
            db_path=db_path,
        )
    if name == "get_worldview_reflections":
        limit = arguments.get("limit")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 30:
            raise ValueError("Journal limit must be an integer from 1 to 30.")
        entries = get_recent_reflections(db_path=db_path, limit=limit)
        if not entries:
            return "The worldview reflection journal is empty."
        return "\n\n".join(
            f"{entry['created_at']}\n{entry['reflection']}" for entry in entries
        )

    if name == "search_web":
        related_queries = arguments.get("related_queries", [])
        if not isinstance(related_queries, list) or any(
            not isinstance(query, str) or not query.strip()
            for query in related_queries
        ):
            raise ValueError("Tool argument 'related_queries' must be a list of non-empty strings.")
        if len(related_queries) > 3:
            raise ValueError("No more than three related search queries are supported.")
        return actions.search_web_action(
            text_argument("query"),
            related_queries=related_queries,
        )
    if name == "open_website":
        website = text_argument("website")
        allowed = {"youtube", "github", "google", "gmail", "docs", "stackoverflow", "linkedin"}
        if website not in allowed:
            raise ValueError("Unsupported website.")
        return actions.open_website_action(website)
    if name == "google_maps":
        query = text_argument("query")
        directions = arguments.get("directions")
        if not isinstance(directions, bool):
            raise ValueError("Tool argument 'directions' must be a boolean.")
        prompt = f"directions to {query}" if directions else f"maps {query}"
        return actions.google_maps_action(prompt)
    if name == "manage_memory":
        operation = text_argument("operation")
        category = text_argument("category")
        content = arguments.get("content")
        if not isinstance(content, str):
            raise ValueError("Tool argument 'content' must be a string.")
        if category not in {"general", "work", "personal", "developer_preferences"}:
            raise ValueError("Unsupported memory category.")
        if operation == "remember":
            value = content.strip()
            if not value:
                raise ValueError("Memory content cannot be empty.")
            key = "user_note" if category == "general" else f"{category}_note"
            save_fact(key, value, category=category, db_path=db_path)
            return "Memory saved."
        if operation == "show":
            return get_memory_summary(db_path=db_path, category=None if category == "general" else category)
        if operation == "forget":
            if not content.strip():
                raise ValueError("Provide a memory key or phrase to forget.")
            removed = forget_memory(f"forget {content}", db_path=db_path)
            return "Memory removed." if removed else "I could not find that memory to remove."
        raise ValueError("Unsupported memory operation.")
    if name == "plan_workflow":
        return actions.plan_workflow_action(text_argument("workflow"), db_path=db_path)
    if name == "find_businesses_without_websites":
        category = text_argument("category")
        area = text_argument("area")
        return actions.business_finder_action(f"find {category} in {area} without websites", db_path=db_path)
    if name == "open_app":
        app = text_argument("app")
        if app not in {"vscode", "terminal", "notepad", "browser"}:
            raise ValueError("Unsupported app.")
        return actions.open_app_action(f"open {app}")
    if name == "inspect_screen":
        from modules.vision import describe_screen_for_task
        return describe_screen_for_task(groq_client, user_prompt or "Summarize the visible screen.")
    if name == "read_clipboard":
        return actions.read_clipboard_action()
    if name == "copy_last_response":
        return actions.copy_last_response_action()
    if name == "create_note":
        content = text_argument("content")
        category = text_argument("category")
        if category not in {"general", "work", "personal", "developer_preferences"}:
            raise ValueError("Unsupported note category.")
        key = "user_note" if category == "general" else f"{category}_note"
        save_fact(key, content, category=category, db_path=db_path)
        return "Quick note saved."
    if name == "set_timer":
        value = arguments.get("value")
        unit = text_argument("unit")
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("Timer value must be a positive integer.")
        if unit not in {"seconds", "minutes", "hours"}:
            raise ValueError("Unsupported timer unit.")
        return actions.timer_action(f"set timer for {value} {unit}")
    if name == "set_reminder":
        return actions.reminder_action(text_argument("reminder"))
    if name == "review_code":
        return actions.code_review_action(groq_client=groq_client)
    if name == "write_code":
        return actions.write_code_action(text_argument("task"), groq_client=groq_client)
    if name == "track_workflow":
        return actions.track_task_action(text_argument("track_id"))
    if name == "request_pc_power":
        return _request_pc_power(text_argument("operation"))
    raise ValueError(f"Unknown tool: {name}")


def parse_tool_arguments(raw_arguments):
    try:
        arguments = json.loads(raw_arguments)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError(f"Tool arguments were not valid JSON: {error}") from error
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must decode to a JSON object.")
    return arguments
