# --- BRAIN.PY ---
# Groq API handling (Llama 3, Whisper, and Vision)

import os
import tempfile
import wave
from groq import Groq
from modules.config import GROQ_API_KEY, SYSTEM_PROMPT, SAMPLE_RATE, MEMORY_DB_PATH
from modules.tts import speak
from modules.vision import describe_screen_for_task, should_shutdown, should_wake
from modules.memory import (
    build_memory_context,
    forget_memory,
    get_memory_summary,
    remember_from_prompt,
    save_message,
    trim_conversation_for_summary,
)
from modules.actions import run_action

# Initialize Groq client
client = None
if GROQ_API_KEY:
    try:
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"Groq Init Error: {e}")
else:
    print("WARNING: GROQ_API_KEY not found in .env file!")


def should_analyze_screen(prompt):
    """Check if the user is asking JARVIS to look at the screen."""
    vision_keywords = [
        "screen", "see", "look", "show me", "what's on",
        "display", "window", "read", "analyze screen",
        "what do you see", "describe", "visible",
        "desktop", "what's showing", "look at",
    ]
    prompt_lower = prompt.lower()
    return any(keyword in prompt_lower for keyword in vision_keywords)


def ask_groq(prompt, update_callbacks):
    """Sends transcript to Groq Llama 3 with Paul Adamu's custom persona. Includes Vision API for screen analysis."""
    print(f"[BRAIN] ask_groq called with prompt: '{prompt[:50]}...'")
    
    # Check for shutdown command
    if should_shutdown(prompt):
        shutdown_msg = "Goodbye, Sir. JARVIS entering sleep mode. Say 'Hello' to wake me."
        update_callbacks["response"](shutdown_msg)
        try:
            speak(shutdown_msg)
        except Exception as e:
            print(f"[BRAIN] speak() error: {e}")
        update_callbacks["status"]("JARVIS is sleeping... Say 'Hello' to wake")
        print("[BRAIN] SHUTDOWN command detected - entering sleep mode")
        # Trigger sleep mode
        if "set_sleeping" in update_callbacks:
            update_callbacks["set_sleeping"](True)
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
        return "SHUTDOWN"
    
    if not client:
        error_msg = "Please set GROQ_API_KEY in your .env file, Sir."
        update_callbacks["response"](error_msg)
        try:
            speak(error_msg)
        except Exception as e:
            print(f"[BRAIN] speak() error: {e}")
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
        return

    try:
        action_result = run_action(prompt, update_callbacks, groq_client=client, db_path=MEMORY_DB_PATH)
        if action_result is not None:
            if action_result in {"SHUTDOWN", "SLEEP", "WAKE", "SLEEP_WITH_SUMMARY"}:
                return action_result
            if isinstance(action_result, str):
                if "Memory saved" in action_result or "I cleared" in action_result or "Memory cleared" in action_result or "Opening" in action_result or "Screenshot" in action_result or "Launching" in action_result or "Saved:" in action_result or "what we discussed" in action_result:
                    try:
                        speak(action_result)
                    except Exception as e:
                        print(f"[BRAIN] speak() error: {e}")
                    return action_result
            return action_result

        # Check if user is asking to analyze the screen
        screen_analysis = None
        if should_analyze_screen(prompt):
            update_callbacks["status"]("JARVIS analyzing screen...")
            print(f"[BRAIN] Vision request detected. Capturing screen...")
            screen_analysis = describe_screen_for_task(client, prompt)
            print(f"[BRAIN] Screen analysis complete")

        memory_action = None
        lower_prompt = prompt.lower()

        if "show my memory" in lower_prompt or "what do you remember" in lower_prompt:
            category = "general"
            if "work" in lower_prompt:
                category = "work"
            elif "personal" in lower_prompt:
                category = "personal"
            elif "developer" in lower_prompt or "coding" in lower_prompt or "programming" in lower_prompt:
                category = "developer_preferences"

            memory_summary = get_memory_summary(db_path=MEMORY_DB_PATH, category=category)
            update_callbacks["response"](memory_summary)
            try:
                speak(memory_summary)
            except Exception as e:
                print(f"[BRAIN] speak() error: {e}")
            update_callbacks["processing"](False)
            update_callbacks["skip_audio"](False)
            return

        if "remember this" in lower_prompt or "remember that" in lower_prompt:
            memory_action = remember_from_prompt(prompt, db_path=MEMORY_DB_PATH)
        elif "forget that" in lower_prompt or "forget" in lower_prompt:
            memory_action = forget_memory(prompt, db_path=MEMORY_DB_PATH)

        if memory_action is not None and isinstance(memory_action, str):
            update_callbacks["response"](f"Memory saved: {memory_action}")
            try:
                speak(f"Memory saved: {memory_action}")
            except Exception as e:
                print(f"[BRAIN] speak() error: {e}")
            update_callbacks["processing"](False)
            update_callbacks["skip_audio"](False)
            return

        if memory_action is False:
            update_callbacks["response"]("I cleared the matching memory entry.")
            try:
                speak("I cleared the matching memory entry.")
            except Exception as e:
                print(f"[BRAIN] speak() error: {e}")
            update_callbacks["processing"](False)
            update_callbacks["skip_audio"](False)
            return
        
        update_callbacks["status"]("JARVIS is thinking...")
        print(f"[BRAIN] Calling Groq API...")

        # Build message with optional screen analysis
        user_message = prompt
        if screen_analysis:
            user_message = f"{prompt}\n\n[SCREEN ANALYSIS]:\n{screen_analysis}"

        memory_context = build_memory_context(db_path=MEMORY_DB_PATH, recent_limit=12, fact_limit=20)
        memory_prefix = ""
        if memory_context:
            memory_prefix = f"\n\n[MEMORY CONTEXT]\n{memory_context}\n"

        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT + memory_prefix},
                {"role": "user", "content": user_message},
            ],
            model="llama-3.3-70b-versatile",
        )

        response = chat_completion.choices[0].message.content.strip()
        save_message("assistant", response, db_path=MEMORY_DB_PATH)
        trim_conversation_for_summary(db_path=MEMORY_DB_PATH, max_messages=60)
        print(f"[BRAIN] Got response from LLM")
        update_callbacks["status"]("JARVIS speaking...")
        update_callbacks["response"](response)

        print(f"\n[JARVIS]: {response}\n")
        print(f"[BRAIN] Calling speak()...")
        try:
            speak(response)
        except Exception as e:
            print(f"[BRAIN] speak() error: {e}")
        print(f"[BRAIN] speak() returned")
        # Let speak() run asynchronously - mic will stop while speaking

    except Exception as e:
        print(f"[BRAIN] Brain Error: {e}")
        import traceback
        traceback.print_exc()
        update_callbacks["status"]("Error reaching Groq servers.")
    finally:
        print(f"[BRAIN] Recovered from error")
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
        update_callbacks["status"]("Listening... Speak into your mic!")
        print(f"[BRAIN] ask_groq complete")


def transcribe_audio(audio_bytes, update_callbacks):
    """
    Transcribes audio via Groq Whisper API and initiates response generation.
    
    update_callbacks: dict with keys 'status', 'user_text', 'processing', 'skip_audio'
    """
    print(f"[TRANSCRIPTION] Starting audio transcription...")
    update_callbacks["skip_audio"](True)
    update_callbacks["status"]("Processing audio with Whisper...")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        tmp_filename = tmp_file.name

    try:
        with wave.open(tmp_filename, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_bytes)

        print(f"[TRANSCRIPTION] Sending audio to Whisper API...")
        # Transcribe audio using Groq Whisper Turbo
        with open(tmp_filename, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(tmp_filename, file.read()),
                model="whisper-large-v3-turbo",
            )

        text = transcription.text.strip()
        print(f"[TRANSCRIPTION] Audio transcribed: '{text[:60]}...'")

        if text and len(text) > 2:
            remember_from_prompt(text, db_path=MEMORY_DB_PATH)
            save_message("user", text, db_path=MEMORY_DB_PATH)
            user_text = f"Paul: '{text}'"
            update_callbacks["user_text"](user_text)
            print(f"\n[PAUL ADAMU]: {text}")
            print(f"[BRAIN] Calling ask_groq...")
            result = ask_groq(text, update_callbacks)
            if result == "SHUTDOWN":
                return "SHUTDOWN"
            print(f"[BRAIN] ask_groq returned")
        else:
            print(f"[BRAIN] Transcription too short or empty")
            update_callbacks["processing"](False)
            update_callbacks["skip_audio"](False)
            update_callbacks["status"]("Listening... Speak into your mic!")

    except Exception as e:
        print(f"[BRAIN] Transcription Error: {e}")
        import traceback
        traceback.print_exc()
        update_callbacks["processing"](False)
        update_callbacks["skip_audio"](False)
        update_callbacks["status"]("Listening... Speak into your mic!")
    finally:
        print(f"[BRAIN] Cleaning up temporary file")
        if os.path.exists(tmp_filename):
            os.remove(tmp_filename)
        print(f"[BRAIN] Transcription complete")


def check_wake_word(audio_bytes):
    """
    Transcribe audio and check if it contains a wake word.
    Used when JARVIS is in sleep mode to detect wake commands.
    
    Returns True if a wake word is detected, False otherwise.
    """
    if not client:
        print("[BRAIN] Groq client not initialized for wake word check")
        return False
    
    print("[BRAIN] Checking for wake word...")
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        tmp_filename = tmp_file.name
    
    try:
        with wave.open(tmp_filename, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_bytes)
        
        # Transcribe using Groq Whisper
        with open(tmp_filename, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(tmp_filename, file.read()),
                model="whisper-large-v3-turbo",
            )
        
        text = transcription.text.strip()
        print(f"[BRAIN] Wake word check transcription: '{text}'")
        
        # Check if the transcribed text contains wake keywords
        if should_wake(text):
            print(f"[BRAIN] Wake word detected: '{text}'")
            return True
        else:
            print(f"[BRAIN] No wake word detected in: '{text}'")
            return False
            
    except Exception as e:
        print(f"[BRAIN] Wake word check error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if os.path.exists(tmp_filename):
            os.remove(tmp_filename)
