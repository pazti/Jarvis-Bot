"""Serialized text-to-speech using one reusable pyttsx3 engine."""

import atexit
import os
import queue
import threading

import pyttsx3

speech_lock = threading.Lock()
speech_is_active = False
_speech_queue = queue.Queue()
_worker_lock = threading.Lock()
_state_lock = threading.Lock()
_worker_thread = None


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
    return best_emotion if score[best_emotion] else "confident"


def get_voice_profile_for_text(text):
    profiles = {
        "warm": {"rate": 180, "volume": 1.0},
        "focused": {"rate": 170, "volume": 1.0},
        "serious": {"rate": 150, "volume": 1.0},
        "gentle": {"rate": 155, "volume": 0.8},
        "playful": {"rate": 210, "volume": 1.0},
        "reassuring": {"rate": 175, "volume": 1.0},
        "thoughtful": {"rate": 160, "volume": 0.9},
        "confident": {"rate": 185, "volume": 1.0},
    }
    return profiles.get(_detect_emotion(text), profiles["confident"])


def _select_sophisticated_voice(engine):
    voices = engine.getProperty("voices") or []
    preferred_names = ["hazel", "george", "samantha", "zira", "victoria", "aria", "katherine", "william"]
    for preferred in preferred_names:
        for voice in voices:
            if preferred in (voice.name or "").lower():
                return voice.id
    for voice in voices:
        voice_name = (voice.name or "").lower()
        if any(token in voice_name for token in ["female", "woman", "english", "uk"]):
            return voice.id
    return voices[0].id if voices else None


def is_speaking():
    """Return whether speech is queued or currently being played."""
    with _state_lock:
        return speech_is_active


def _speech_worker():
    global speech_is_active
    engine = None
    comtypes_module = None
    com_initialized = False
    while True:
        message = _speech_queue.get()
        try:
            if message is None:
                break
            with speech_lock:
                if engine is None:
                    print("[TTS] Initializing speech engine.")
                    if os.name == "nt" and not com_initialized:
                        import comtypes

                        comtypes.CoInitialize()
                        comtypes_module = comtypes
                        com_initialized = True
                    engine = pyttsx3.init()
                    selected_voice = _select_sophisticated_voice(engine)
                    if selected_voice:
                        engine.setProperty("voice", selected_voice)
                        print(f"[TTS] Selected voice: {selected_voice}")
                    else:
                        print("[TTS] No installed voice was found; using the system default.")
                    engine.connect(
                        "started-utterance",
                        lambda name: print(
                            f"[TTS] Playback started: {name or 'utterance'}."
                        ),
                    )
                    engine.connect(
                        "finished-utterance",
                        lambda name, completed: print(
                            f"[TTS] Playback completed: {name or 'utterance'}."
                            if completed
                            else f"[TTS] Playback stopped before completion: {name or 'utterance'}."
                        ),
                    )
                profile = get_voice_profile_for_text(message)
                engine.setProperty("rate", profile["rate"])
                engine.setProperty("volume", profile["volume"])
                print("[TTS] Starting playback request.")
                engine.say(message)
                engine.runAndWait()
                print("[TTS] Playback request returned.")
        except Exception as error:
            print(f"[TTS] Speech error: {error}")
        finally:
            _speech_queue.task_done()
            with _state_lock:
                if _speech_queue.empty():
                    speech_is_active = False
    if engine is not None:
        try:
            engine.stop()
        except Exception as error:
            print(f"[TTS] Speech engine shutdown error: {error}")
    if com_initialized and comtypes_module is not None:
        try:
            comtypes_module.CoUninitialize()
        except Exception as error:
            print(f"[TTS] Windows COM shutdown error: {error}")


def speak(text):
    """Queue speech on the reusable engine worker instead of spawning per-call threads."""
    global _worker_thread, speech_is_active
    if not text:
        return
    with _worker_lock:
        if _worker_thread is None or not _worker_thread.is_alive():
            _worker_thread = threading.Thread(
                target=_speech_worker,
                name="jarvis-tts",
                daemon=True,
            )
            _worker_thread.start()
        with _state_lock:
            speech_is_active = True
            _speech_queue.put(str(text))
        print(f"[TTS] Speech queued ({len(str(text))} characters).")


def shutdown(timeout=5):
    """Drain queued speech and stop the worker during application shutdown."""
    global _worker_thread, speech_is_active
    with _worker_lock:
        worker = _worker_thread
        if worker is None or not worker.is_alive():
            _worker_thread = None
            with _state_lock:
                speech_is_active = False
            return
        _speech_queue.put(None)
    worker.join(timeout)
    if worker.is_alive():
        print("[TTS] Speech worker did not stop before the shutdown timeout.")
    else:
        with _worker_lock:
            if _worker_thread is worker:
                _worker_thread = None
        with _state_lock:
            speech_is_active = False


atexit.register(shutdown)
