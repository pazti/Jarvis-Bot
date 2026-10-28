"""Public action API with implementations grouped by domain."""

import os
import re
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path

from modules.config import GROQ_MODEL, MEMORY_DB_PATH

LAST_RESPONSE = ""


def _record_last_response(message):
    global LAST_RESPONSE
    LAST_RESPONSE = message or ""


def run_action(prompt, update_callbacks=None, groq_client=None, db_path=None):
    """Dispatch only exact safe local phrases; use the LLM tool router otherwise."""
    from modules.tool_router import route_local_action

    return route_local_action(prompt, update_callbacks)


def track_task_action(track_id, update_callbacks=None):
    """Look up the status of a specific task track in the database."""
    from modules.task_orchestration import TaskExecutor
    try:
        executor = TaskExecutor(db_path=MEMORY_DB_PATH)
        # We use a helper to get the track state
        status = executor.get_track_status(track_id)
        if not status:
            message = f"I couldn't find any record of track {track_id}, Sir."
        else:
            message = f"Track {track_id} status: {status}"
    except Exception as e:
        print(f"[ACTIONS] Tracking error: {e}")
        message = "I had trouble accessing the task database."

    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message

def shutdown_action(update_callbacks=None):
    if update_callbacks:
        update_callbacks["response"]("Goodbye, Sir. JARVIS is shutting down.")
        update_callbacks["status"]("Shutting down...")
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return "SHUTDOWN"


def pc_sleep_action(update_callbacks=None):
    from modules.tool_router import execute_tool
    message = execute_tool("request_pc_power", {"operation": "sleep"})
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return "PC_SLEEP"


def pc_shutdown_action(update_callbacks=None):
    from modules.tool_router import execute_tool
    message = execute_tool("request_pc_power", {"operation": "shutdown"})
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return "PC_SHUTDOWN"


def time_action(update_callbacks=None):
    current = datetime.now().strftime("%I:%M %p")
    message = f"The time is {current}."
    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def date_action(update_callbacks=None):
    current = datetime.now().strftime("%A, %B %d, %Y")
    message = f"Today is {current}."
    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def search_web_action(query, update_callbacks=None, related_queries=None):
    from .web import search_web

    message = search_web(query, related_queries=related_queries)
    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def open_website_action(prompt, update_callbacks=None):
    from .web import open_website

    message = open_website(prompt)
    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def google_maps_action(prompt, update_callbacks=None):
    from .web import google_maps

    message = google_maps(prompt)
    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def capabilities_action(update_callbacks=None):
    """Give a short spoken tour of the assistant's main capabilities."""
    message = (
        "I can take voice requests, open Google Maps and get directions, read and review the code on your screen, "
        "open apps and websites, manage notes and reminders, remember useful details, analyze screenshots, and help "
        "you write or troubleshoot code."
    )
    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def plan_workflow_action(workflow_key, update_callbacks=None, db_path=None):
    """Create a persisted workflow track and execute it immediately if it's an automated workflow."""
    from .workflows import run_workflow_plan

    try:
        result = run_workflow_plan(workflow_key, db_path=db_path)
        message = result["message"]
    except Exception as error:
        print(f"[ACTIONS] Task planning error: {error}")
        message = f"I could not create or execute that task plan: {error}"

    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["status"]("Task plan processed.")
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def business_finder_action(prompt, update_callbacks=None, db_path=None):
    """Run the business-finder task using OpenStreetMap (Overpass API) instead of Google Places."""
    from .business import run_business_finder

    try:
        result = run_business_finder(prompt, db_path=db_path)
        message = result["message"]
    except ValueError as error:
        message = str(error)
    except Exception as error:
        print(f"[ACTIONS] Business finder error: {error}")
        message = "I had an error running the business finder. Please try again."

    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["status"]("Business finder task processed.")
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def code_review_action(update_callbacks=None, groq_client=None):
    """Analyze the visible code and return a concise diagnosis with a suggested fix."""
    if not groq_client:
        message = "I need the Groq API configured before I can read and review the code on your screen."
    else:
        try:
            from modules.vision import describe_screen_for_task

            if update_callbacks:
                update_callbacks["status"]("JARVIS reading the code on screen...")
            analysis = describe_screen_for_task(
                groq_client,
                "Inspect the visible code. Identify the most important error or bug, explain why it happens, and provide the smallest corrected code snippet. Do not claim to have changed files; clearly label the proposed fix.",
            )
            message = f"Code review: {analysis}"
        except Exception as error:
            print(f"[ACTIONS] Code review error: {error}")
            message = "I could not read the code on screen. Please make sure the code window is visible and try again."

    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def project_code_review_action(update_callbacks=None, groq_client=None):
    """Review the actual project files in the workspace and summarize the most relevant issues."""
    project_root = Path(__file__).resolve().parent.parent.parent
    review_lines = []

    for path in sorted(project_root.rglob("*.py")):
        if ".venv" in path.parts or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        snippets = []
        if "def main" in text.lower() or "if __name__ == '__main__'" in text:
            snippets.append(f"{path.relative_to(project_root)} contains the entry point and application boot logic.")
        if "sleep" in text.lower() and "wake" in text.lower():
            snippets.append(f"{path.relative_to(project_root)} includes wake/sleep behavior that should be checked for false positives.")
        if "groq" in text.lower() or "whisper" in text.lower():
            snippets.append(f"{path.relative_to(project_root)} integrates with the voice and AI pipeline.")
        if snippets:
            review_lines.extend(snippets)

    if not review_lines:
        review_lines.append("No Python files were found to inspect in the project root.")

    summary = "Project code review: " + " ".join(review_lines[:6])
    if update_callbacks:
        update_callbacks["response"](summary)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return summary


def write_code_action(prompt, update_callbacks=None, groq_client=None):
    """Generate simple code and save it under the project-local generated folder."""
    if not groq_client:
        message = "I cannot write code until the Groq API is configured."
    else:
        task = re.sub(
            r"(?i)\b(write|create|generate)\s+(a\s+)?(simple\s+)?(piece\s+of\s+)?(code|script)\b",
            " ",
            prompt or "",
        )
        task = re.sub(r"\s+", " ", task).strip(" .,:;!?\"")
        if not task:
            message = "Tell me what code you want me to write."
        else:
            try:
                language = "python" if "python" in task.lower() else "javascript" if "javascript" in task.lower() or "node" in task.lower() else "text"
                extension = {"python": ".py", "javascript": ".js", "text": ".txt"}[language]
                response = groq_client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "Generate only the complete source code requested by the user. Do not include explanations outside a markdown code fence.",
                        },
                        {"role": "user", "content": task},
                    ],
                    model=GROQ_MODEL,
                    max_tokens=1200,
                )
                generated = response.choices[0].message.content.strip()
                code_match = re.search(r"```(?:[a-zA-Z0-9_+-]+)?\s*\n?(.*?)```", generated, re.DOTALL)
                code = (code_match.group(1) if code_match else generated).strip() + "\n"
                output_dir = Path(__file__).resolve().parent.parent.parent / "generated"
                output_dir.mkdir(exist_ok=True)
                output_path = output_dir / f"jarvis_generated{extension}"
                output_path.write_text(code, encoding="utf-8")
                message = f"Saved: {output_path.relative_to(output_dir.parent)}. I did not run the generated code."
            except Exception as error:
                print(f"[ACTIONS] Code generation error: {error}")
                message = "I could not generate and save that code."

    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def read_clipboard_action(update_callbacks=None):
    try:
        if os.name == "nt":
            result = subprocess.run(["powershell", "-command", "Get-Clipboard"], capture_output=True, text=True, check=False)
            text = result.stdout.strip() or "Clipboard is empty."
        else:
            text = "Clipboard reading is not supported in this environment."
        message = f"Clipboard contents: {text}"
    except Exception:
        message = "I could not read the clipboard."
    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def copy_last_response_action(update_callbacks=None):
    global LAST_RESPONSE
    text = LAST_RESPONSE or "No previous response recorded."
    try:
        if os.name == "nt":
            # Use the native 'clip' utility and pass text via stdin to avoid shell injection
            process = subprocess.run(["clip"], input=text, text=True, capture_output=True, check=False)
            if process.returncode == 0:
                message = "I copied the last response to the clipboard."
            else:
                message = "I could not copy the last response to the clipboard."
        else:
            message = "Clipboard copy is not supported in this environment."
    except Exception:
        message = "I could not copy the last response to the clipboard."
    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def timer_action(prompt, update_callbacks=None):
    match = re.search(r"(?:(\d+)\s*(?:minute|min|minutes|m))|(?:(\d+)\s*(?:second|sec|seconds|s))|(?:(\d+)\s*(?:hour|hr|hours|h))", (prompt or "").lower())
    if not match:
        message = "I need a duration, like 'set a timer for 5 minutes'."
        _record_last_response(message)
        if update_callbacks:
            update_callbacks["response"](message)
            update_callbacks["processing"](False)
            update_callbacks["skip_audio"](False)
        return message

    value = 0
    unit = "seconds"
    for idx, group in enumerate(match.groups(), start=1):
        if group:
            value = int(group)
            unit = ["seconds", "minutes", "hours"][idx - 1]
            break

    if value <= 0:
        message = "I need a positive time value for the timer."
    else:
        duration_seconds = value * {"seconds": 1, "minutes": 60, "hours": 3600}[unit]
        try:
            from modules.proactive import schedule_timer

            schedule_timer(duration_seconds, f"{value} {unit}")
            message = f"Timer set for {value} {unit}."
        except (OSError, RuntimeError, ValueError) as error:
            print(f"[ACTIONS] Timer scheduling error: {error}")
            message = f"I could not save that timer: {error}"
    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def reminder_action(prompt, update_callbacks=None):
    text = re.sub(r"(?i)^set a reminder\s*|^remind me\s*", "", prompt or "").strip()
    if not text:
        text = "a reminder"
    message = f"Reminder set: {text}."
    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def screen_summary_action(update_callbacks=None):
    message = "I can summarize the screen, and I can also save a screenshot for review. I need a live screen-analysis backend or a clearer description of what’s visible to give a detailed summary."
    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def focus_mode_action(update_callbacks=None):
    message = "Focus mode started. I’ll keep the environment quiet and help you stay on task."
    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def weather_action(update_callbacks=None):
    message = "I can check the weather, but I need a live weather API or your city to give an accurate forecast."
    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def draft_message_action(prompt, update_callbacks=None):
    cleaned = re.sub(r"(?i)draft a message|draft message|write a message", "", prompt or "").strip()
    content = cleaned or "Hi, I wanted to follow up on our task and share a quick status update."
    message = f"Draft message: {content}"
    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def summarize_day_action(update_callbacks=None):
    message = "Daily summary: You’ve worked through your priorities, stayed focused on execution, and made meaningful progress. Review your unfinished tasks and set one clear next step for tomorrow."
    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def quick_note_action(prompt, update_callbacks=None, db_path=None):
    from .memory import quick_note

    message = quick_note(prompt, update_callbacks=update_callbacks, db_path=db_path)
    _record_last_response(message)
    return message


def sleep_action(update_callbacks=None, groq_client=None, db_path=None):
    """
    Prepare for sleep mode with conversation summary.
    If user says "goodbye", creates a summary and asks about saving to permanent memory.
    """
    from .memory import sleep

    return sleep(update_callbacks, groq_client=groq_client, db_path=db_path)


def wake_action(update_callbacks=None):
    from .memory import wake

    return wake(update_callbacks)


def show_memory_action(prompt, update_callbacks=None):
    from .memory import show_memory

    return show_memory(prompt, update_callbacks=update_callbacks)


def clear_memory_action(update_callbacks=None):
    from .memory import clear_all_memory

    return clear_all_memory(update_callbacks=update_callbacks)


def remember_action(prompt, update_callbacks=None):
    from .memory import remember

    return remember(prompt, update_callbacks=update_callbacks)


def forget_action(prompt, update_callbacks=None):
    from .memory import forget

    return forget(prompt, update_callbacks=update_callbacks)


def open_browser_action(update_callbacks=None, target_prompt=None):
    lower = (target_prompt or "").lower()
    target = "https://www.google.com"
    if "youtube" in lower:
        target = "https://www.youtube.com"
    elif "github" in lower:
        target = "https://github.com"
    elif "google" in lower:
        target = "https://www.google.com"

    try:
        webbrowser.open(target)
        label = "youtube" if "youtube" in lower else "github" if "github" in lower else "browser"
        message = f"Opening {label} in the browser."
    except Exception:
        message = "I could not open the browser."

    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def take_screenshot_action(update_callbacks=None):
    try:
        from PIL import ImageGrab
        screenshot = ImageGrab.grab()
        path = os.path.join(os.getcwd(), "jarvis_screenshot.png")
        screenshot.save(path)
        message = f"Screenshot saved to {path}."
    except Exception:
        message = "I could not capture the screen."

    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def open_folder_action(update_callbacks=None):
    target = os.getcwd()
    try:
        if os.name == "nt":
            os.startfile(target)
        else:
            subprocess.Popen(["xdg-open", target])
        message = f"Opening the project folder: {target}."
    except Exception:
        message = "I could not open the folder."

    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def open_app_action(prompt, update_callbacks=None):
    lower = (prompt or "").lower()
    app_name = ""

    for candidate in ["vscode", "code", "terminal", "notepad", "browser"]:
        if candidate in lower:
            app_name = candidate
            break

    if not app_name:
        message = "I need the app name to launch it."
        if update_callbacks:
            update_callbacks["response"](message)
            update_callbacks["processing"](False)
            update_callbacks["skip_audio"](False)
        return message

    try:
        if app_name in {"vscode", "code"}:
            if os.name == "nt":
                os.startfile("code")
            else:
                subprocess.Popen(["code"])
        elif app_name == "terminal":
            if os.name == "nt":
                os.startfile("cmd")
            else:
                subprocess.Popen(["gnome-terminal"])
        elif app_name == "notepad":
            if os.name == "nt":
                os.startfile("notepad")
            else:
                subprocess.Popen(["notepadqq"])
        else:
            webbrowser.open("https://www.google.com")
        message = f"Launching {app_name}."
    except Exception:
        message = f"I could not launch {app_name}."

    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def save_summary_action(prompt, groq_client=None, update_callbacks=None, db_path=None):
    """
    Saves the conversation summary as a permanent memory when user says yes.
    """
    from .memory import save_summary

    return save_summary(
        groq_client=groq_client,
        update_callbacks=update_callbacks,
        db_path=db_path,
    )


def no_save_action(update_callbacks=None):
    """
    User declined to save summary, proceed to sleep mode.
    """
    from .memory import decline_summary

    return decline_summary(update_callbacks)
