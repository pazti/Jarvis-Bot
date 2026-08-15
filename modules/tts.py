# --- TTS.PY ---
# Text-to-Speech logic (pyttsx3 engine)

import threading
import pyttsx3
import time

speech_lock = threading.Lock()
speech_is_active = False


def is_speaking():
    """Returns True if TTS is currently playing audio."""
    return speech_is_active


def speak(text):
    """Speak in a fresh pyttsx3 instance without blocking."""

    def _speak_once(message):
        global speech_is_active
        try:
            with speech_lock:
                speech_is_active = True  # Mark as speaking
            
            local_engine = pyttsx3.init()
            local_engine.setProperty("rate", 220)  # Faster speech rate for quicker responses
            local_engine.setProperty("volume", 1.0)

            voices = local_engine.getProperty("voices")
            selected_voice = None

            for voice in voices:
                voice_name = voice.name.lower()
                if (
                    "david" in voice_name
                    or "george" in voice_name
                    or "english_uk" in voice_name
                ):
                    selected_voice = voice.id
                    break

            if not selected_voice and voices:
                selected_voice = voices[0].id

            if selected_voice:
                local_engine.setProperty("voice", selected_voice)

            local_engine.say(message)
            local_engine.runAndWait()
            local_engine.stop()
        except Exception as e:
            print(f"TTS Error: {e}")
        finally:
            with speech_lock:
                speech_is_active = False  # Mark as done

    try:
        threading.Thread(target=_speak_once, args=(text,), daemon=False).start()
    except Exception as e:
        print(f"TTS Error: {e}")
