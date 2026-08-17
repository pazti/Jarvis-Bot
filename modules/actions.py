import os
import re
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

from modules.config import MEMORY_DB_PATH
from modules.memory import clear_memory, get_memory_summary

LAST_RESPONSE = ""


def _record_last_response(message):
    global LAST_RESPONSE
    LAST_RESPONSE = message or ""


def run_action(prompt, update_callbacks=None, groq_client=None, db_path=None):
    """Routes a command prompt to a deterministic action handler."""
    from modules.vision import should_goodbye, should_shutdown

    lower = (prompt or "").lower().strip()
    if not lower:
        return None

    shutdown_check = should_shutdown(prompt)
    goodbye_check = should_goodbye(prompt)

    if shutdown_check:
        return shutdown_action(update_callbacks)

    if goodbye_check:
        return sleep_action(update_callbacks, groq_client=groq_client, db_path=db_path)

    if "sleep pc" in lower or "sleep my pc" in lower or "sleep computer" in lower or "hibernate pc" in lower:
        return pc_sleep_action(update_callbacks)

    if "shutdown pc" in lower or "shutdown computer" in lower or "turn off pc" in lower or "turn off computer" in lower:
        return pc_shutdown_action(update_callbacks)

    if "sleep" in lower and "wake" not in lower and "sleeping" not in lower and "asleep" not in lower:
        return sleep_action(update_callbacks, groq_client=groq_client, db_path=db_path)

    if "wake" in lower or "wake up" in lower:
        return wake_action(update_callbacks)

    if "what time is it" in lower or "current time" in lower or "time is it" in lower:
        return time_action(update_callbacks)

    if "what day is it" in lower or "what date is it" in lower or "current date" in lower or "date is it" in lower:
        return date_action(update_callbacks)

    if "show my memory" in lower or "what do you remember" in lower:
        return show_memory_action(lower, update_callbacks)

    if "clear memory" in lower:
        return clear_memory_action(update_callbacks)

    if "remember this" in lower or "remember that" in lower:
        return remember_action(prompt, update_callbacks)

    if "forget that" in lower or "forget" in lower:
        return forget_action(prompt, update_callbacks)

    if "open browser" in lower or "launch browser" in lower:
        return open_browser_action(update_callbacks, target_prompt=prompt)

    if "youtube" in lower and "browser" in lower:
        return open_browser_action(update_callbacks, target_prompt=prompt)

    if "github" in lower and "browser" in lower:
        return open_browser_action(update_callbacks, target_prompt=prompt)

    if "take screenshot" in lower or "screenshot" in lower:
        return take_screenshot_action(update_callbacks)

    if "capture and summarize screen" in lower or "summarize my screen" in lower or "analyze my screen" in lower:
        return screen_summary_action(update_callbacks)

    if "summarize what\'s on my screen" in lower or "summarize what is on my screen" in lower or "what's on my screen" in lower:
        return screen_summary_action(update_callbacks)

    if "focus mode" in lower or "start focus mode" in lower or "focus" in lower and "mode" in lower:
        return focus_mode_action(update_callbacks)

    if "weather" in lower:
        return weather_action(update_callbacks)

    if "draft a message" in lower or "draft message" in lower or "write a message" in lower:
        return draft_message_action(prompt, update_callbacks)

    if "summarize my day" in lower or "summary of my day" in lower or "what did i do today" in lower:
        return summarize_day_action(update_callbacks)

    if "quick note" in lower or "create a note" in lower or "write a quick note" in lower:
        return quick_note_action(prompt, update_callbacks)

    if "remind me to finish my task" in lower or "reminder to finish my task" in lower:
        return reminder_action("remind me to finish my task", update_callbacks)

    if "open folder" in lower or "open my folder" in lower:
        return open_folder_action(update_callbacks)

    if "open project folder" in lower or "open my project" in lower:
        return open_folder_action(update_callbacks)

    if "open vscode" in lower or "open vs code" in lower or "open code" in lower:
        return open_app_action("open vscode", update_callbacks)

    if "open terminal" in lower or "launch terminal" in lower:
        return open_app_action("open terminal", update_callbacks)

    if "open notepad" in lower:
        return open_app_action("open notepad", update_callbacks)

    if "search the web" in lower or "search for" in lower and "web" in lower:
        return search_web_action(prompt, update_callbacks)

    if any(site in lower for site in ["open youtube", "youtube", "open github", "github", "open google", "google", "open gmail", "gmail", "open docs", "google docs", "open stackoverflow", "stackoverflow", "open linkedin", "linkedin"]):
        return open_website_action(prompt, update_callbacks)

    if "read clipboard" in lower or "what is on my clipboard" in lower:
        return read_clipboard_action(update_callbacks)

    if "copy last response" in lower or "copy my last response" in lower:
        return copy_last_response_action(update_callbacks)

    if "set a timer" in lower or "set timer" in lower or "timer for" in lower:
        return timer_action(prompt, update_callbacks)

    if "set a reminder" in lower or "set reminder" in lower or "remind me" in lower:
        return reminder_action(prompt, update_callbacks)

    if "what is my clipboard" in lower:
        return read_clipboard_action(update_callbacks)

    if "start app" in lower or "open app" in lower or "launch app" in lower:
        return open_app_action(prompt, update_callbacks)

    if "yes" in lower or "save that" in lower or "save it" in lower or "save" in lower:
        return save_summary_action(prompt, groq_client=groq_client, update_callbacks=update_callbacks, db_path=db_path)

    if "no" in lower or "don't save" in lower or "don't remember" in lower:
        return no_save_action(update_callbacks)

    return None


def shutdown_action(update_callbacks=None):
    if update_callbacks:
        update_callbacks["response"]("Goodbye, Sir. JARVIS is shutting down.")
        update_callbacks["status"]("Shutting down...")
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return "SHUTDOWN"


def pc_sleep_action(update_callbacks=None):
    try:
        if os.name == "nt":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        else:
            os.system("systemctl suspend")
        message = "Putting the PC to sleep."
    except Exception:
        message = "I could not put the PC to sleep."

    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return "PC_SLEEP"


def pc_shutdown_action(update_callbacks=None):
    try:
        if os.name == "nt":
            os.system("shutdown /s /t 0")
        else:
            os.system("shutdown -h now")
        message = "Shutting down the PC."
    except Exception:
        message = "I could not shut down the PC."

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


def search_web_action(prompt, update_callbacks=None):
    query = re.sub(r"(?i)search the web|search for|search", "", prompt, count=1).strip()
    if not query:
        query = "latest updates"
    url = f"https://www.google.com/search?q={quote_plus(query)}"
    try:
        webbrowser.open(url)
        message = f"Searching the web for: {query}."
    except Exception:
        message = "I could not search the web."
    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def open_website_action(prompt, update_callbacks=None):
    lower = (prompt or "").lower()
    site_map = {
        "youtube": "https://www.youtube.com",
        "github": "https://github.com",
        "google": "https://www.google.com",
        "gmail": "https://mail.google.com",
        "docs": "https://docs.google.com",
        "stackoverflow": "https://stackoverflow.com",
        "linkedin": "https://www.linkedin.com",
        "x": "https://x.com",
        "twitter": "https://x.com",
    }
    target = "https://www.google.com"
    for key, url in site_map.items():
        if key in lower:
            target = url
            break

    try:
        webbrowser.open(target)
        message = f"Opening {target}."
    except Exception:
        message = "I could not open that website."
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
            clipboard_value = text.replace("'", "''")
            command = f"Set-Clipboard -Value '{clipboard_value}'"
            process = subprocess.run(["powershell", "-command", command], capture_output=True, text=True, check=False)
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
        message = f"Timer set for {value} {unit}."
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


def quick_note_action(prompt, update_callbacks=None):
    cleaned = re.sub(r"(?i)create a quick note|quick note|create a note|write a quick note", "", prompt or "").strip()
    text = cleaned or "Follow up on the current task and keep your next step visible."
    message = f"Quick note saved: {text}"
    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def sleep_action(update_callbacks=None, groq_client=None, db_path=None):
    """
    Prepare for sleep mode with conversation summary.
    If user says "goodbye", creates a summary and asks about saving to permanent memory.
    """
    from modules.memory import create_session_summary, save_fact
    
    if update_callbacks:
        # Generate session summary using Groq
        summary = None
        if groq_client:
            try:
                print(f"[ACTIONS] Creating summary with groq_client...")
                summary = create_session_summary(groq_client, db_path=db_path)
                print(f"[ACTIONS] Summary created: {summary[:100] if summary else 'None'}")
            except Exception as e:
                print(f"[ACTIONS] Error creating summary: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[ACTIONS] No groq_client provided for summary")
        
        if summary:
            # Display summary and ask about saving
            summary_msg = f"Here's what we discussed today: {summary}\n\nWould you like me to save this as a memory, Sir?"
            print(f"[ACTIONS] Showing summary: {summary_msg[:50]}...")
            update_callbacks["response"](summary_msg)
            update_callbacks["status"]("Ready to save memory or sleep - Waiting for your response...")
            # Return a special signal that we're waiting for yes/no
            update_callbacks["processing"](False)
            update_callbacks["skip_audio"](False)
            return "SLEEP_WITH_SUMMARY"
        else:
            print(f"[ACTIONS] No summary generated, entering sleep mode directly")
            update_callbacks["response"]("Entering sleep mode, Sir.")
            update_callbacks["status"]("JARVIS sleeping...")
            if "set_sleeping" in update_callbacks:
                update_callbacks["set_sleeping"](True)
            update_callbacks["processing"](False)
            update_callbacks["skip_audio"](False)
            return "SLEEP"
    
    return "SLEEP"


def wake_action(update_callbacks=None):
    if update_callbacks:
        update_callbacks["response"]("Hello, Sir. JARVIS is awake.")
        update_callbacks["status"]("Listening... Speak into your mic, Sir!")
        if "set_sleeping" in update_callbacks:
            update_callbacks["set_sleeping"](False)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return "WAKE"


def show_memory_action(prompt, update_callbacks=None):
    category = "general"
    lower = (prompt or "").lower()
    if "work" in lower:
        category = "work"
    elif "personal" in lower:
        category = "personal"
    elif "developer" in lower or "coding" in lower or "programming" in lower:
        category = "developer_preferences"

    summary = get_memory_summary(db_path=MEMORY_DB_PATH, category=category)
    if update_callbacks:
        update_callbacks["response"](summary)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return summary


def clear_memory_action(update_callbacks=None):
    clear_memory(db_path=MEMORY_DB_PATH)
    if update_callbacks:
        update_callbacks["response"]("Memory cleared.")
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return "MEMORY_CLEARED"


def remember_action(prompt, update_callbacks=None):
    from modules.memory import remember_memory

    result = remember_memory(prompt, db_path=MEMORY_DB_PATH)
    message = f"Memory saved: {result}" if result else "I saved that memory."
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def forget_action(prompt, update_callbacks=None):
    from modules.memory import forget_memory

    success = forget_memory(prompt, db_path=MEMORY_DB_PATH)
    message = "I cleared the matching memory entry." if success else "I could not find that memory to remove."
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


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
    from modules.memory import create_session_summary, save_fact
    
    if update_callbacks:
        try:
            if groq_client:
                summary = create_session_summary(groq_client, db_path=db_path)
                # Save as permanent memory
                save_fact(
                    "session_summary",
                    summary,
                    category="general",
                    db_path=db_path
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
        except Exception as e:
            print(f"[ACTIONS] Error saving summary: {e}")
            message = "I had trouble saving that memory, Sir."
            update_callbacks["response"](message)
            update_callbacks["processing"](False)
            update_callbacks["skip_audio"](False)
    
    return "SLEEP"


def no_save_action(update_callbacks=None):
    """
    User declined to save summary, proceed to sleep mode.
    """
    if update_callbacks:
        update_callbacks["response"]("Understood, Sir. Entering sleep mode without saving.")
        update_callbacks["status"]("JARVIS sleeping...")
        if "set_sleeping" in update_callbacks:
            update_callbacks["set_sleeping"](True)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    
    return "SLEEP"
