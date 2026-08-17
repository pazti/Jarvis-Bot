# --- AUDIO.PY ---
# Microphone stream & Voice Activity Detection (VAD)

import queue
import threading
import time
import numpy as np
import sounddevice as sd
from modules.config import SAMPLE_RATE, CHUNK, SILENCE_THRESHOLD, SILENCE_FRAMES
from modules.brain import transcribe_audio
from modules.tts import is_speaking

# Audio state
audio_queue = queue.Queue(maxsize=100)
current_volume = 0.0
is_processing = False
skip_audio = False
is_sleeping = False  # JARVIS sleep/standby mode

# Callback state setters (to be set by main)
_state_setters = {}


def register_state_setters(setters_dict):
    """Register callbacks to update application state."""
    global _state_setters
    _state_setters = setters_dict


def audio_callback(indata, frames, time, status):
    """Callback for sounddevice audio stream."""
    global current_volume, skip_audio
    if status:
        import sys
        status_str = str(status).lower()
        # Suppress input overflow warnings - they're expected under heavy load
        if "overflow" not in status_str:
            print(status, file=sys.stderr)

    # Don't record if we're processing or if JARVIS is currently speaking
    if skip_audio or is_speaking():
        return

    volume = np.sqrt(np.mean(indata**2)) if len(indata) > 0 else 0
    current_volume = volume

    pcm_data = (indata * 32767).astype(np.int16).tobytes()

    # Don't block if queue is full, just skip this frame
    try:
        audio_queue.put_nowait((pcm_data, volume))
    except queue.Full:
        pass


def speech_worker():
    """Monitors live mic stream and triggers recording when voice is detected."""
    global is_processing, skip_audio, is_sleeping

    recorded_frames = []
    silent_chunks = 0
    speaking = False
    wake_frames = []  # Frames for wake-word detection
    wake_silent_chunks = 0

    while True:
        try:
            pcm_data, volume = audio_queue.get(timeout=1)
        except queue.Empty:
            continue
        except Exception as e:
            print(f"[AUDIO] Queue error: {e}")
            continue

        # While sleeping, only listen for wake words
        if is_sleeping:
            if volume > SILENCE_THRESHOLD:
                wake_frames.append(pcm_data)
                wake_silent_chunks = 0
            elif wake_frames:
                wake_frames.append(pcm_data)
                wake_silent_chunks += 1
                if wake_silent_chunks >= SILENCE_FRAMES:
                    # Check for wake word
                    full_audio = b"".join(wake_frames)
                    wake_frames.clear()
                    wake_silent_chunks = 0
                    _process_wake_word(full_audio)
            continue

        if is_processing:
            recorded_frames.clear()
            speaking = False
            silent_chunks = 0
            continue

        if volume > SILENCE_THRESHOLD:
            speaking = True
            silent_chunks = 0
            recorded_frames.append(pcm_data)
            if "status" in _state_setters:
                _state_setters["status"]("Recording voice...")
        elif speaking:
            recorded_frames.append(pcm_data)
            silent_chunks += 1

            if silent_chunks >= SILENCE_FRAMES:
                print(f"[AUDIO] Silence detected. Processing {len(recorded_frames)} frames...")
                is_processing = True
                skip_audio = True  # Turn off mic immediately
                if "processing" in _state_setters:
                    _state_setters["processing"](True)

                full_audio = b"".join(recorded_frames)
                recorded_frames.clear()
                speaking = False
                silent_chunks = 0

                # Build callbacks dict for transcribe_audio
                callbacks = {
                    "status": _state_setters.get("status", lambda x: None),
                    "user_text": _state_setters.get("user_text", lambda x: None),
                    "response": _state_setters.get("response", lambda x: None),
                    "processing": _state_setters.get("processing", lambda x: None),
                    "skip_audio": _state_setters.get("skip_audio", lambda x: None),
                    "set_sleeping": _state_setters.get("set_sleeping", lambda x: None),
                }

                print(f"[AUDIO] Starting transcription thread...")
                def transcribe_with_sleep():
                    result = transcribe_audio(full_audio, callbacks)
                    if result == "SHUTDOWN":
                        print("[AUDIO] SHUTDOWN signal received from brain - sleep mode activated by callback")
                
                threading.Thread(
                    target=transcribe_with_sleep,
                    daemon=False,  # Non-daemon so it completes
                ).start()


def start_audio_stream():
    """Initialize and start the audio input stream."""
    threading.Thread(target=speech_worker, daemon=True).start()

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=CHUNK,
        callback=audio_callback,
    )
    stream.start()
    return stream


def get_current_volume():
    """Get the current microphone volume level."""
    return current_volume


def set_skip_audio(value):
    """Manually control audio skip flag."""
    global skip_audio
    print(f"[AUDIO] Setting skip_audio={value}")
    skip_audio = value


def set_processing(value):
    """Manually control processing flag."""
    global is_processing
    print(f"[AUDIO] Setting is_processing={value}")
    is_processing = value


def get_state():
    """Get current audio state for debugging."""
    return {
        "is_processing": is_processing,
        "skip_audio": skip_audio,
        "current_volume": current_volume,
        "is_sleeping": is_sleeping,
    }


def set_sleeping(value):
    """Manually control sleep flag."""
    global is_sleeping
    print(f"[AUDIO] Setting is_sleeping={value}")
    is_sleeping = value


def _process_wake_word(audio_bytes):
    """Process audio and check for wake words."""
    global is_sleeping
    from modules.brain import check_wake_word
    
    try:
        if check_wake_word(audio_bytes):
            print("[AUDIO] Wake word detected!")
            is_sleeping = False
            if "status" in _state_setters:
                _state_setters["status"]("JARVIS awakening...")
            if "response" in _state_setters:
                _state_setters["response"]("Hello, Sir. JARVIS online.")
            from modules.tts import speak
            speak("Hello, Sir. JARVIS online.")
    except Exception as e:
        print(f"[AUDIO] Wake word check error: {e}")
