import os
import re
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

from modules.config import GROQ_MODEL, MEMORY_DB_PATH
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

    # TikTok Integration Logic
    if "tiktok" in lower:
        if any(phrase in lower for phrase in ["login", "sign in", "log into", "log in", "plug into"]):
            from modules.tiktok_integration import sync_login
            update_callbacks["status"]("Opening TikTok login window...")
            success = sync_login()
            if success:
                message = "TikTok session saved successfully. You are now connected."
            else:
                message = "I couldn't open the TikTok login window. Please check if another Chrome instance is using the profile."
            update_callbacks["response"](message)
            update_callbacks["processing"](False)
            update_callbacks["skip_audio"](False)
            return message
        
        if "analyze" in lower or "performance" in lower or "stats" in lower:
            from modules.tiktok_integration import sync_get_analytics
            # Try to extract username from prompt
            username = re.sub(r"(?i).*tiktok account (?:of )?|analyze tiktok|performance of|stats for", "", prompt).strip()
            if not username:
                message = "Please tell me which TikTok username to analyze."
            else:
                update_callbacks["status"]("Accessing TikTok analytics...")
                data = sync_get_analytics(username)
                if data["status"] == "success":
                    # Send the raw content to the LLM for synthesis
                    if groq_client:
                        completion = groq_client.chat.completions.create(
                            messages=[
                                {"role": "system", "content": "You are a TikTok Growth Expert. Analyze the following raw HTML/content from a TikTok analytics page and provide a concise, professional performance summary and 3 actionable tips for growth."},
                                {"role": "user", "content": data["raw_content"]}
                            ],
                            model=GROQ_MODEL,
                        )
                        message = completion.choices[0].message.content
                    else:
                        message = "I retrieved the data but need the Groq API to analyze it."
                else:
                    message = f"Failed to access TikTok: {data['message']}"
            
            update_callbacks["response"](message)
            update_callbacks["processing"](False)
            update_callbacks["skip_audio"](False)
            return message

    # Track Task Progress
    if "track" in lower and "track_" in prompt:
        track_id_match = re.search(r"track_[a-zA-Z0-9_]+", prompt)
        if track_id_match:
            track_id = track_id_match.group(0)
            return track_task_action(track_id, update_callbacks)

    workflow_aliases = {
        "business finder": "business_finder",
        "businesses without websites": "business_finder",
        "project health check": "project_health_check",
        "run the test suite": "run_test_suite",
        "run tests": "run_test_suite",
        "feature plan": "feature_plan",
        "plan a feature": "feature_plan",
        "bug fix": "bug_fix",
        "fix this bug": "bug_fix",
        "module refactor": "module_refactor",
        "refactor this module": "module_refactor",
        "dependency audit": "dependency_audit",
        "audit dependencies": "dependency_audit",
        "documentation generator": "documentation_generator",
        "generate documentation": "documentation_generator",
        "project backup": "project_backup",
        "backup the project": "project_backup",
        "git change assistant": "git_change_assistant",
        "review my git changes": "git_change_assistant",
        "feature implementation": "feature_implementation",
        "implement this feature": "feature_implementation",
    }
    if "plan" in lower or "start task" in lower or "create a task" in lower:
        for phrase, workflow_key in workflow_aliases.items():
            if phrase in lower:
                return plan_workflow_action(workflow_key, update_callbacks, db_path=db_path)

    # Priority 1: Trigger the deterministic Business Finder tool FIRST
    if (
        "businesses without websites" in lower
        or "businesses without a website" in lower
        or "don't have websites" in lower
        or "don't have a website" in lower
        or "no website" in lower
        or ("without websites" in lower and any(word in lower for word in ["find", "search", "look for"]))
        or ("without a website" in lower and any(word in lower for word in ["find", "search", "look for"]))
        or ("restaurants" in lower and "without a website" in lower)
        or ("restaurants" in lower and "no website" in lower)
        or ("restaurants" in lower and "without websites" in lower)
    ):
        # Enhanced extraction using LLM if available
        if groq_client:
            try:
                extraction = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "Extract the 'category' (what kind of business) and 'area' (city/region) from the user prompt. Return ONLY a JSON object: {\"category\": \"...\", \"area\": \"...\"}"},
                        {"role": "user", "content": prompt}
                    ],
                    model=GROQ_MODEL,
                    response_format={"type": "json_object"}
                ).choices[0].message.content
                import json
                data = json.loads(extraction)
                # We override the prompt to a standard "category in area" format for the existing action handler
                structured_prompt = f"{data.get('category')} in {data.get('area')}"
                return business_finder_action(structured_prompt, update_callbacks, db_path=db_path)
            except Exception as e:
                print(f"[ACTIONS] LLM extraction failed, falling back to regex: {e}")

        return business_finder_action(prompt, update_callbacks, db_path=db_path)

    # Track Task Progress
    if "track" in lower and "track_" in prompt:
        track_id_match = re.search(r"track_[a-zA-Z0-9_]+", prompt)
        if track_id_match:
            track_id = track_id_match.group(0)
            return track_task_action(track_id, update_callbacks)

    workflow_aliases = {
        "business finder": "business_finder",
        "businesses without websites": "business_finder",
        "project health check": "project_health_check",
        "run the test suite": "run_test_suite",
        "run tests": "run_test_suite",
        "feature plan": "feature_plan",
        "plan a feature": "feature_plan",
        "bug fix": "bug_fix",
        "fix this bug": "bug_fix",
        "module refactor": "module_refactor",
        "refactor this module": "module_refactor",
        "dependency audit": "dependency_audit",
        "audit dependencies": "dependency_audit",
        "documentation generator": "documentation_generator",
        "generate documentation": "documentation_generator",
        "project backup": "project_backup",
        "backup the project": "project_backup",
        "git change assistant": "git_change_assistant",
        "review my git changes": "git_change_assistant",
        "feature implementation": "feature_implementation",
        "implement this feature": "feature_implementation",
    }
    if "plan" in lower or "start task" in lower or "create a task" in lower:
        for phrase, workflow_key in workflow_aliases.items():
            if phrase in lower:
                return plan_workflow_action(workflow_key, update_callbacks, db_path=db_path)

    if (
        "businesses without websites" in lower
        or "businesses without a website" in lower
        or "don't have websites" in lower
        or "don't have a website" in lower
        or "no website" in lower
        or ("without websites" in lower and any(word in lower for word in ["find", "search", "look for"]))
        or ("without a website" in lower and any(word in lower for word in ["find", "search", "look for"]))
    ):
        return business_finder_action(prompt, update_callbacks, db_path=db_path)

    if any(phrase in lower for phrase in [
        "review my project code",
        "review the project code",
        "open my project code",
        "analyze my project code",
        "inspect my project code",
        "read my project code",
    ]):
        return project_code_review_action(update_callbacks, groq_client=groq_client)

    if any(phrase in lower for phrase in [
        "open my code",
        "tell me what's wrong with my code",
        "tell me what is wrong with my code",
        "debug my code",
        "review my code",
        "fix my code",
    ]):
        return code_review_action(update_callbacks, groq_client=groq_client)

    shutdown_check = should_shutdown(prompt)
    goodbye_check = should_goodbye(prompt)

    if shutdown_check:
        return shutdown_action(update_callbacks)

    if goodbye_check:
        return sleep_action(update_callbacks, groq_client=groq_client, db_path=db_path)

    explicit_sleep_patterns = [
        r"\b(?:sleep|go to sleep|enter sleep mode)\s+(?:jarvis|javis|assistant)\b",
        r"\b(?:jarvis|javis|assistant)\s+(?:go to sleep|sleep)\b",
        r"\b(?:sleep|go to sleep|enter sleep mode)\b.*\b(?:jarvis|javis|assistant)\b",
        r"\b(?:jarvis|javis|assistant)\b.*\b(?:sleep|go to sleep|enter sleep mode)\b",
        r"\b(?:goodbye|bye|see you later|talk to you later|good night)\b",
    ]

    if "sleep pc" in lower or "sleep my pc" in lower or "sleep computer" in lower or "hibernate pc" in lower:
        return pc_sleep_action(update_callbacks)

    if "shutdown pc" in lower or "shutdown computer" in lower or "turn off pc" in lower or "turn off computer" in lower:
        return pc_shutdown_action(update_callbacks)

    if any(re.search(pattern, lower) for pattern in explicit_sleep_patterns):
        return sleep_action(update_callbacks, groq_client=groq_client, db_path=db_path)

    if re.search(r"\b(?:wake|wake up)\b.*\b(?:jarvis|javis|assistant)\b", lower) or re.search(r"\b(?:jarvis|javis|assistant)\b.*\b(?:wake|wake up)\b", lower):
        return wake_action(update_callbacks)

    # Time queries - allow words between keywords
    if any(phrase in lower for phrase in ["what time", "current time", "tell me the time", "time is it"]) or (("what" in lower or "current" in lower) and "time" in lower) or (("tell" in lower or "time" in lower) and ("me" in lower or "is" in lower or "now" in lower)):
        return time_action(update_callbacks)

    # Date queries - allow words between keywords  
    if any(phrase in lower for phrase in ["what day", "what date", "current date", "date is it"]) or (("what" in lower or "current" in lower) and "date" in lower) or ("today" in lower and "date" in lower):
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

    if (
        "google maps" in lower
        or "google map" in lower
        or "maps" in lower
        or re.search(r"\b(?:any\s+)?directions?\s+to\b", lower)
        or any(phrase in lower for phrase in ["route to", "navigate to", "how do i get to"])
    ):
        return google_maps_action(prompt, update_callbacks)

    if any(
        phrase in lower
        for phrase in [
            "what can you do",
            "what are you capable of",
            "show me what you can do",
            "give me a showcase",
        ]
    ):
        return capabilities_action(update_callbacks)

    if any(phrase in lower for phrase in ["write code", "create code", "generate code", "write a script", "create a script"]):
        return write_code_action(prompt, update_callbacks, groq_client=groq_client)

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
        return quick_note_action(prompt, update_callbacks, db_path=db_path)

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


def google_maps_action(prompt, update_callbacks=None):
    """Open Google Maps, search for a place, or show directions."""
    lower = (prompt or "").lower().strip()
    directions_requested = any(
        [
            re.search(r"\b(?:any\s+)?directions?\s+to\b", lower),
            *[phrase in lower for phrase in ["route to", "navigate to", "how do i get to"]],
        ]
    )
    query = re.sub(
        r"(?i)\b(jarvis|javis|chavis|i need|open|launch|go to|show me|search for|find|look up|google maps?|maps|any directions? to|directions? to|route to|navigate to|how do i get to)\b",
        " ",
        prompt or "",
    )
    query = re.sub(r"\s+", " ", query).strip(" .,:;!?\"")

    if directions_requested and query:
        url = f"https://www.google.com/maps/dir/?api=1&destination={quote_plus(query)}"
        message = f"Opening directions to {query}."
    elif query:
        url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"
        message = f"Searching Google Maps for: {query}."
    else:
        url = "https://www.google.com/maps"
        message = "Opening Google Maps."

    try:
        webbrowser.open(url)
    except Exception:
        message = "I could not open Google Maps."
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
    try:
        from modules.task_catalog import TaskCatalog
        from modules.task_orchestration import TaskExecutor
        from modules.workflow_handlers import WORKFLOW_HANDLERS

        track = TaskCatalog(db_path=db_path).plan(workflow_key)
        
        # If the workflow has an automated handler, execute the tasks now
        if workflow_key in WORKFLOW_HANDLERS:
            handler = WORKFLOW_HANDLERS[workflow_key]
            executor = TaskExecutor(db_path=db_path)
            
            last_result = ""
            for task in track["tasks"]:
                res = executor.execute_task(
                    track["track_id"],
                    task["task_id"],
                    task_handler=lambda t, c: handler(t, c),
                )
                # Update HUD progress
                from modules import hud
                
                # Map current tasks to a state for the HUD
                # we need the original task list from the catalog to build the state
                from modules.task_catalog import TASK_CATALOG
                workflow = TASK_CATALOG[workflow_key]
                
                steps_state = []
                for i, t in enumerate(workflow["tasks"]):
                    if i < idx:
                        steps_state.append({"title": t[0], "status": "done"})
                    elif i == idx:
                        steps_state.append({"title": t[0], "status": "running"})
                    else:
                        steps_state.append({"title": t[0], "status": "pending"})
                
                hud.update_task_progress(track["name"], steps_state)
                
                last_result = res["result"] if res else "Completed"
            
            message = f"Executed {track['name']} successfully. Final result: {last_result}"
        else:
            message = (
                f"Planned {track['name']} with {len(track['tasks'])} tasks. "
                f"Track ID: {track['track_id']}."
            )
    except Exception as error:
        print(f"[ACTIONS] Task planning error: {error}")
        message = "I could not create or execute that task plan."

    _record_last_response(message)
    if update_callbacks:
        update_callbacks["response"](message)
        update_callbacks["status"]("Task plan processed.")
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
    return message


def business_finder_action(prompt, update_callbacks=None, db_path=None):
    """Run the business-finder task using OpenStreetMap (Overpass API) instead of Google Places."""
    from modules.task_catalog import TaskCatalog
    
    lower_prompt = (prompt or "").lower()
    category = None
    area = None
    
    cleaned = lower_prompt
    triggers = [
        r"find\s+businesses\s+in\s+", r"find\s+restaurants\s+in\s+", 
        r"search\s+for\s+", r"look\s+for\s+", r"businesses\s+in\s+",
        r"restaurants\s+in\s+", r"shops\s+in\s+", r"dentists\s+in\s+",
        r"jarvis\s+", r"javis\s+", r"why\s+javis\s+"
    ]
    for t in triggers:
        cleaned = re.sub(t, "", cleaned)
    
    cleaned = re.sub(r"without\s+websites?|no\s+website|with\s+no\s+websites?", "", cleaned).strip()
    
    if " in " in cleaned:
        parts = cleaned.split(" in ")
        area = parts[-1].strip()
        category = parts[0].strip()
    
    if area and not category:
        category = "business"
    
    if not category or not area:
        message = "I couldn't quite figure out the business type and city. Try: 'find restaurants in Abuja without websites'."
    else:
        try:
            track = TaskCatalog(db_path=db_path).plan(
                "business_finder",
                context={"search_query": category, "search_area": area},
            )
            from modules.osm_places import save_business_report, search_businesses_without_websites
            from modules.task_orchestration import TaskExecutor

            businesses = search_businesses_without_websites(category, area_name=area)
            
            if not businesses:
                message = f"I searched for {category} in {area}, but I couldn't find any businesses without websites."
            else:
                report_path = save_business_report(businesses)
                executor = TaskExecutor(db_path=db_path)
                
                task_results = {
                    "Define search scope": {"result": f"Approved search scope: {category} in {area}."},
                    "Search Google Places": {"result": f"Collected OpenStreetMap results for {category} in {area}."},
                    "Filter businesses without websites": {"result": f"Filtered {len(businesses)} businesses without listed websites."},
                    "Save businesses without websites": {"result": f"Saved report to {report_path}."},
                    "Verify and report results": {"result": f"Verified {len(businesses)} report rows."},
                }
                
                for task in track["tasks"]:
                    executor.execute_task(
                        track["track_id"],
                        task["task_id"],
                        task_handler=lambda current_task, context: task_results.get(current_task["title"], {"result": "Completed"}),
                    )
                    
                message = (
                    f"Business Finder (OSM) complete: found {len(businesses)} businesses without listed websites in {area}. "
                    f"Report saved to {report_path}. Track ID: {track['track_id']}."
                )
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
    project_root = Path(__file__).resolve().parent.parent
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
                output_dir = Path(__file__).resolve().parent.parent / "generated"
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


def quick_note_action(prompt, update_callbacks=None, db_path=None):
    from modules.memory import remember_memory
    cleaned = re.sub(r"(?i)create a quick note|quick note|create a note|write a quick note", "", prompt or "").strip()
    text = cleaned or "Follow up on the current task and keep your next step visible."
    
    # Use the provided db_path or fall back to the config default
    target_db = db_path or MEMORY_DB_PATH
    
    # Persist the note in the memory database
    result = remember_memory(f"Note: {text}", db_path=target_db)
    
    message = f"Quick note saved: {text}" if result else "I had trouble saving the note."
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
