# --- AUDIO.PY ---
# Microphone stream & Voice Activity Detection (VAD)

import logging
import queue
import threading
import numpy as np
import sounddevice as sd
from modules import config
from modules.config import (
    SAMPLE_RATE,
    CHUNK,
    SILENCE_THRESHOLD,
    SILENCE_FRAMES,
    AUDIO_INPUT_DEVICE,
    AUDIO_INPUT_DEVICE_NAME,
)
from modules.brain import transcribe_audio
from modules.tts import is_speaking

logger = logging.getLogger(__name__)

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
        status_str = str(status).lower()
        if "overflow" not in status_str:
            logger.warning(status)

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
        except RuntimeError as exc:
            logger.warning("Audio queue error: %s", exc)
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
            if "note_activity" in _state_setters:
                _state_setters["note_activity"]()
            speaking = True
            silent_chunks = 0
            recorded_frames.append(pcm_data)
            if "status" in _state_setters:
                _state_setters["status"]("Recording voice...")
        elif speaking:
            recorded_frames.append(pcm_data)
            silent_chunks += 1

            if silent_chunks >= SILENCE_FRAMES:
                logger.info("Silence detected. Processing %s frames...", len(recorded_frames))
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
                    "set_muted": _state_setters.get("set_muted", lambda x: None),
                }

                logger.info("Starting transcription thread...")
                def transcribe_with_sleep():
                    result = transcribe_audio(full_audio, callbacks)
                    if result == "SHUTDOWN":
                        logger.info("SHUTDOWN signal received from brain - sleep mode activated by callback")
                
                threading.Thread(
                    target=transcribe_with_sleep,
                    daemon=False,  # Non-daemon so it completes
                ).start()


def _resolve_input_device():
    """Pick the most likely microphone device for this machine."""
    try:
        devices = sd.query_devices()
    except (OSError, RuntimeError) as exc:
        logger.warning("Could not list audio devices: %s", exc)
        return None

    requested = (AUDIO_INPUT_DEVICE or "").strip()
    if requested:
        try:
            return int(requested)
        except ValueError:
            pass

    preferred_name = (AUDIO_INPUT_DEVICE_NAME or "").strip().lower()
    if preferred_name:
        for idx, device in enumerate(devices):
            name = device[0] if isinstance(device, (list, tuple)) else str(device.get("name", ""))
            if preferred_name in str(name).lower():
                return idx

    for idx, device in enumerate(devices):
        name = device[0] if isinstance(device, (list, tuple)) else str(device.get("name", ""))
        lowered = str(name).lower()
        if any(keyword in lowered for keyword in ["microphone", "mic", "array", "headset", "usb"]):
            return idx

    default = getattr(sd.default, "device", None)
    if isinstance(default, (list, tuple)) and default:
        return default[0]
    return None


def start_audio_stream():
    """Initialize and start the audio input stream."""
    threading.Thread(target=speech_worker, daemon=True).start()

    device_index = _resolve_input_device()
    logger.info("Using input device index: %s", device_index)

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=CHUNK,
        device=device_index,
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
    # Removed print statement to reduce terminal noise
    skip_audio = value


def set_processing(value):
    """Manually control processing flag."""
    global is_processing
    # Removed print statement to reduce terminal noise
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
    # Removed print statement to reduce terminal noise
    is_sleeping = value


def _process_wake_word(audio_bytes):
    """Process audio and check for wake words."""
    global is_sleeping
    from modules.brain import check_wake_word
    
    try:
        if check_wake_word(audio_bytes):
            logger.info("Wake word detected!")
            is_sleeping = False
            if "status" in _state_setters:
                _state_setters["status"](f"{config.ASSISTANT_NAME} awakening...")
            if "response" in _state_setters:
                _state_setters["response"](
                    f"Hello, {config.ADDRESS_AS}. {config.ASSISTANT_NAME} online."
                )
            from modules.tts import speak
            speak(f"Hello, {config.ADDRESS_AS}. {config.ASSISTANT_NAME} online.")
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
        logger.warning("Wake word check error: %s", exc)
