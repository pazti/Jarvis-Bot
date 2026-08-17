# --- TTS.PY ---
# Text-to-Speech logic (pyttsx3 engine)

import threading
import pyttsx3

speech_lock = threading.Lock()
speech_is_active = False


def _detect_emotion(text):
    lower = (text or "").lower()
    emotional_signals = {
        "warm": ["hello", "hi", "good morning", "great", "awesome", "happy", "smile", "love", "excited", "glad", "nice", "beautiful", "excellent"],
        "focused": ["analyze", "check", "review", "scan", "investigate", "secure", "system", "monitor", "status", "diagnose", "inspect"],
        "serious": ["error", "danger", "warning", "security", "urgent", "alert", "critical", "issue", "breach", "risk", "threat"],
        "gentle": ["good night", "sleep", "rest", "bye", "later", "goodbye", "calm", "gentle", "take care", "relax"],
        "playful": ["joke", "funny", "amazing", "clever", "smart", "impressive", "wow", "nice one"],
        "reassuring": ["don't worry", "it's okay", "safe", "secure", "fine", "under control", "we can handle", "no problem", "I can help"],
        "thoughtful": ["let me think", "consider", "reflect", "understand", "observe", "I see", "interesting", "reasoning", "pattern", "context"],
    }

    score = {key: 0 for key in emotional_signals}
    for emotion, signals in emotional_signals.items():
        for signal in signals:
            if signal in lower:
                score[emotion] += 1

    best_emotion = max(score, key=score.get, default="confident")
    if score[best_emotion] == 0:
        return "confident"
    return best_emotion


def get_voice_profile_for_text(text):
    emotion = _detect_emotion(text)
    profiles = {
        "warm": {"rate": 215, "pitch": 1.42, "volume": 1.0},
        "focused": {"rate": 190, "pitch": 1.18, "volume": 1.0},
        "serious": {"rate": 170, "pitch": 1.0, "volume": 1.0},
        "gentle": {"rate": 165, "pitch": 1.32, "volume": 0.9},
        "playful": {"rate": 225, "pitch": 1.5, "volume": 1.0},
        "reassuring": {"rate": 200, "pitch": 1.28, "volume": 1.0},
        "thoughtful": {"rate": 180, "pitch": 1.2, "volume": 0.95},
        "confident": {"rate": 205, "pitch": 1.25, "volume": 1.0},
    }
    return profiles.get(emotion, profiles["confident"])


def _select_female_voice(engine):
    voices = engine.getProperty("voices") or []
    preferred_names = [
        "zira", "samantha", "susan", "female", "aria", "karen", "victoria",
        "lily", "alice", "serena", "megan", "jenny", "hazel", "natalie"
    ]

    for preferred in preferred_names:
        for voice in voices:
            voice_name = (voice.name or "").lower()
            if preferred in voice_name:
                return voice.id

    for voice in voices:
        voice_name = (voice.name or "").lower()
        if any(token in voice_name for token in ["female", "woman", "girl", "zira", "samantha", "susan", "aria"]):
            return voice.id

    return voices[0].id if voices else None


def is_speaking():
    """Returns True if TTS is currently playing audio."""
    return speech_is_active


def speak(text):
    """Speak text using pyttsx3 in a separate thread with serialization lock."""
    if not text:
        return

    def _speak_safe(message):
        global speech_is_active
        try:
            acquired = speech_lock.acquire(timeout=5.0)
            if not acquired:
                print(f"[TTS] Timeout waiting for speech lock - skipping: {message[:50]}")
                return

            try:
                speech_is_active = True
                engine = pyttsx3.init()
                profile = get_voice_profile_for_text(message)
                engine.setProperty("rate", profile["rate"])
                try:
                    engine.setProperty("pitch", profile["pitch"])
                except Exception:
                    print("[TTS] Pitch adjustment unsupported on this engine; using default pitch.")
                engine.setProperty("volume", profile["volume"])

                selected_voice = _select_female_voice(engine)
                if selected_voice:
                    engine.setProperty("voice", selected_voice)

                engine.say(message)
                engine.runAndWait()
                engine.stop()
            finally:
                speech_lock.release()
        except Exception as e:
            print(f"[TTS] Error: {e}")
        finally:
            speech_is_active = False

    try:
        thread = threading.Thread(target=_speak_safe, args=(text,), daemon=False)
        thread.start()
    except Exception as e:
        print(f"[TTS] Failed to start thread: {e}")
