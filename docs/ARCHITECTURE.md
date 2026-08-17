# JARVIS Architecture Overview

## System Design

JARVIS is designed as a modular, event-driven voice assistant with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                     JARVIS Assistant                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌────────────┐  ┌──────────────────┐   │
│  │   Audio I/O  │  │    HUD     │  │    Actions       │   │
│  │  (SoundDevice)│ │  (Pygame)  │  │  (Command Router)│   │
│  └──────┬───────┘  └────────────┘  └────────┬─────────┘   │
│         │                                     │               │
│         └──────────────────┬──────────────────┘               │
│                            │                                  │
│                  ┌─────────▼─────────┐                       │
│                  │   Brain (Brain)   │◄──────┐               │
│                  │ - Wake Detection  │       │               │
│                  │ - Action Routing  │    Feedback           │
│                  │ - LLM Orchestration           │           │
│                  └─────────┬─────────┘       │               │
│                            │                │               │
│      ┌─────────────────────┼─────────────────┘               │
│      │                     │                                 │
│   ┌──▼─────┐         ┌─────▼──────┐      ┌──────────┐      │
│   │ Groq   │         │  Vision    │      │ Memory   │      │
│   │ (LLM & │         │ (Cloudflare)      │ (SQLite) │      │
│   │ Speech)│         │ + Fallback │      │          │      │
│   └────────┘         └────────────┘      └──────────┘      │
│                                                              │
│   TTS Output                                                 │
│   ┌──────────────┐                                          │
│   │  pyttsx3    │                                          │
│   │ (Emotional  │                                          │
│   │  Speaker)   │                                          │
│   └──────────────┘                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Core Modules

### main.py
**Entry point and event loop coordinator.**

```
main()
  ├─ Initialize Pygame HUD
  ├─ Register state callbacks
  ├─ Start audio stream
  └─ Main loop (check events, render)
```

Key responsibilities:
- Window lifecycle
- Thread synchronization
- Graceful shutdown handling

### modules/audio.py
**Real-time microphone capture and voice activity detection.**

Flow:
```
SoundDevice Stream
  ├─ Capture audio frames (16kHz, 16-bit mono)
  ├─ Compute RMS (root mean square) for volume detection
  ├─ Detect silence (< SILENCE_THRESHOLD)
  ├─ Accumulate until silence > SILENCE_FRAMES
  ├─ Send to brain.py for transcription
  └─ Return to listening loop
```

Key functions:
- `start_audio_stream()` - Initialize SoundDevice stream
- `speech_worker()` - Background thread for audio processing
- `check_wake_word()` - Detect JARVIS-specific phrases
- `set_sleeping()` / `set_processing()` - State management

### modules/brain.py
**LLM orchestration and command processing.**

Main flow:
```
User speaks → Audio transcription → Parse command
  ├─ Is wake word? → No: discard
  ├─ Is shutdown/sleep? → Yes: execute
  ├─ Is vision request? → Yes: capture screen
  ├─ Send to Groq LLM
  └─ Speak response + record in memory
```

Key functions:
- `ask_groq()` - Send prompt to LLM with memory context
- `transcribe_audio()` - Groq Whisper API integration
- `check_wake_word()` - Verify JARVIS activation
- Memory context building for personalization

### modules/actions.py
**Command routing and execution (25+ handlers).**

Pattern:
```
run_action(prompt)
  ├─ Parse command from prompt
  ├─ Match against 25+ action patterns
  ├─ Execute handler (browser, timer, memory, etc.)
  └─ Return result to HUD
```

Action categories:
- System (time, date, sleep, shutdown)
- Browser/Web (open sites, search)
- Files (folder, screenshots, apps)
- Memory (save, retrieve, categorize)
- Productivity (timer, reminders, focus)
- Clipboard (read, copy, paste)

### modules/vision.py
**Screen capture and analysis with fallback chain.**

Flow:
```
User: "Analyze my screen"
  ├─ Capture screenshot
  ├─ Convert to base64
  ├─ Try Cloudflare Workers AI
  │   ├─ Check agreement status
  │   └─ Submit with prompt
  ├─ On 403: auto-retry with "agree" prompt
  ├─ If Cloudflare fails: fallback to text-only Groq
  └─ Return analysis to user
```

Key functions:
- `describe_screen_for_task()` - Main entry point
- `_call_cloudflare_vision()` - Vision API integration
- `_encode_screenshot_base64()` - Image compression
- Graceful degradation if vision unavailable

### modules/memory.py
**SQLite-based persistent memory with categories.**

Database schema:
```sql
facts (id, category, key, value, timestamp)
conversations (id, role, content, timestamp)
```

Categories:
- **general** - default preferences
- **work** - project-related
- **personal** - personal preferences
- **developer_preferences** - coding habits

Features:
- Automatic memory context injection
- Conversation history trimming
- Session summarization
- Category-based filtering

### modules/tts.py
**Text-to-speech with emotion detection.**

Emotion classification:
- **serious** - "error", "danger", "critical"
- **casual** - "lol", "funny", "cool"
- **thoughtful** - "think", "consider", "analyze"
- **playful** - "fun", "exciting", "surprise"

Output adjustment:
- Rate (speed): default 210, tunable per emotion
- Pitch: default 1.25, adjusted for emotion
- Volume: consistent 1.0
- Voice: Female (SAPI5 on Windows)

### modules/hud.py
**Pygame desktop UI rendering.**

Elements:
- Status bar (top): Current mode, actions
- Response text (center): JARVIS replies
- User text (below): Your transcribed speech
- Volume visualization: Real-time audio level
- Particle system: Visual feedback

Refresh: 60 FPS

### modules/config.py
**Centralized configuration and constants.**

Sections:
- API keys (Groq, Cloudflare)
- Audio parameters (sample rate, silence threshold)
- System prompt (JARVIS persona)
- UI constants (window size, fonts)
- Memory settings (database path)

## Data Flow Examples

### Example 1: Simple Query
```
User: "What time is it?"
  ↓
audio.py: Capture speech, detect silence
  ↓
brain.py: transcribe_audio() → "What time is it?"
  ↓
actions.py: run_action() → time_action()
  ↓
tts.py: speak("The time is 3:45 PM")
  ↓
hud.py: Display response on screen
  ↓
memory.py: Log interaction (optional)
```

### Example 2: Memory + LLM
```
User: "Remember: I like Python"
  ↓
actions.py: remember_action() → save to SQLite
  ↓
memory.py: Insert fact into database
  ↓
User: "What's my preferred language?"
  ↓
brain.py: ask_groq() includes memory context
  ↓
Groq LLM: "Your preferred language is Python"
  ↓
tts.py: Speak response
```

### Example 3: Vision Request
```
User: "Analyze my screen"
  ↓
brain.py: detect_vision_request()
  ↓
vision.py: describe_screen_for_task()
  ├─ ImageGrab: screenshot()
  ├─ Cloudflare API: send for analysis
  └─ On failure: text fallback
  ↓
brain.py: ask_groq() with analysis
  ↓
tts.py: Speak findings
```

## Thread Model

**Main Thread:**
- Pygame event loop
- HUD rendering

**Audio Worker Thread:**
- Continuous microphone capture
- Silence detection
- Wake word checking

**Transcription Thread:**
- Groq Whisper API calls
- Brain module interaction

**TTS Thread:**
- pyttsx3 speech synthesis
- Prevents main thread blocking

## API Integration Points

### Groq
- **LLM:** text-davinci-003 equivalent (Llama 3.1)
- **Speech:** Whisper API for audio transcription
- **Headers:** Authorization with API key
- **Latency:** Sub-100ms typical

### Cloudflare Workers AI
- **Model:** @cf/meta/llama-3.2-11b-vision-instruct
- **Input:** Base64-encoded PNG screenshot
- **Agreement:** Must accept policy once per account
- **Fallback:** Auto-degrade to text-only if unavailable

### Windows APIs
- **Audio:** SoundDevice (PortAudio wrapper)
- **TTS:** SAPI5 via pyttsx3
- **UI:** Pygame (SDL wrapper)
- **System:** os.system() for PC sleep/shutdown

## Error Handling Strategy

1. **Graceful Degradation**
   - Vision fails → text-only mode
   - TTS fails → console output only
   - Memory fails → continue without persistence

2. **Retry Logic**
   - Groq 403 (agreement) → auto-retry with "agree"
   - Transient network errors → exponential backoff

3. **User Feedback**
   - All errors displayed in HUD
   - Console logs for debugging
   - Specific error messages for action failures

## Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Voice capture | Real-time | <100ms end-to-end |
| Transcription | ~500ms | Groq Whisper API |
| LLM response | ~300ms | Groq Llama 3.1 |
| TTS generation | ~500ms | pyttsx3 system |
| **Total response** | **~1.3s** | Sub-2 seconds typical |
| Screen capture | ~100ms | ImageGrab.grab() |
| Vision analysis | ~2s | Cloudflare API |
| Memory query | <10ms | SQLite local |

## Security Considerations

- **API Keys**: Stored in `.env` only (not in code)
- **Memory**: SQLite at rest (can add encryption)
- **Network**: HTTPS for all API calls
- **Audio**: Processed locally or sent only to your API keys
- **No telemetry**: No external logging or analytics

## Future Architecture Improvements

- [ ] Local wake-word detector (reduce mic stream overhead)
- [ ] SQLite encryption (SQLCipher)
- [ ] Async/await refactor (currently thread-based)
- [ ] Plugin system for custom commands
- [ ] Multi-model LLM selection
- [ ] Websocket connection pooling (reduce API overhead)

## Design principles

- Local-first where possible
- Graceful fallback between providers
- Clear separation of concerns between audio, reasoning, and UI
- Minimal dependency on paid services unless configured

## Provider strategy

### LLM (Text Processing)
1. **Groq Llama 3.3** - Primary reasoning engine (sub-second latency)
   - Used for all chat, reasoning, and text processing
   - Optimized for speed and cost efficiency

### Vision (Screen Analysis)
1. **Cloudflare Workers AI** - Optional remote vision fallback when available
2. **Groq text fallback** - Used when screen vision is unavailable
3. **Text-only fallback** - Helpful response when no vision backend is available

This architecture keeps the assistant fast and compatible without requiring local-only image tooling.
