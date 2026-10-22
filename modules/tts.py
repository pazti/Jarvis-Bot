# --- TTS.PY ---
# Text-to-Speech logic (pyttsx3 engine)

import os
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
    # Adjusted for a "Butler/Sophisticated AI" feel:
    # Rates are slower for sophistication, slightly faster for urgency.
    profiles = {
        "warm": {"rate": 180, "volume": 1.0},        # Soft, welcoming
        "focused": {"rate": 170, "volume": 1.0},     # Precise and clear
        "serious": {"rate": 150, "volume": 1.1},     # Slow, weighty, authoritative
        "gentle": {"rate": 155, "volume": 0.8},      # Quiet and soothing
        "playful": {"rate": 210, "volume": 1.0},     # Brisk and energetic
        "reassuring": {"rate": 175, "volume": 1.0},   # Steady and calm
        "thoughtful": {"rate": 160, "volume": 0.9},  # Pensive, slower pace
        "confident": {"rate": 185, "volume": 1.0},   # The standard "JARVIS" tone
    }
    return profiles.get(emotion, profiles["confident"])


def _select_sophisticated_voice(engine):
    voices = engine.getProperty("voices") or []
    # Priority list for the "Butler" vibe: British English, then refined Female voices
    preferred_names = [
        "hazel", "george", "samantha", "zira", "victoria", "aria", "katherine", "william"
    ]

    # 1. Look for specific high-quality "Butler" names
    for preferred in preferred_names:
        for voice in voices:
            voice_name = (voice.name or "").lower()
            if preferred in voice_name:
                return voice.id

    # 2. Fallback to any English (UK/US) female voice for that crisp, clear AI feel
    for voice in voices:
        voice_name = (voice.name or "").lower()
        if any(token in voice_name for token in ["female", "woman", "english", "uk"]):
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
                
                # Set the "Butler" parameters
                engine.setProperty("rate", profile["rate"])
                engine.setProperty("volume", profile["volume"])

                # Select the most sophisticated voice available
                selected_voice = _select_sophisticated_voice(engine)
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
