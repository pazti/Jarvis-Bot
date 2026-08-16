# JARVIS — ZeroTrace Intelligence Core

<p align="center">
  <img src="https://img.shields.io/badge/AI-Voice%20Assistant-8A2BE2?style=for-the-badge&logo=opencv&logoColor=white" alt="AI Voice Assistant" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/Ollama-Local%20Vision-FF6B6B?style=for-the-badge" alt="Ollama Local Vision" />
</p>

> A sleek desktop AI assistant built for voice interaction, screen awareness, and smart local reasoning.

JARVIS is a personal assistant project inspired by the classic AI assistant concept: listen to voice commands, transcribe audio, query a LLM, and optionally analyze the current screen with vision-capable models.

## ✨ Highlights

- Voice-driven interaction using microphone input and real-time audio monitoring
- Local screen capture and vision analysis
- Groq-powered reasoning with custom persona prompts
- Ollama support for free local vision using LLaVA
- Claude vision fallback for premium API users
- Persistent memory with short-term and fact-based recall
- Memory commands for save, forget, and retrieval
- Category-based memory for work, personal, and developer preferences
- Animated desktop HUD with status and response display
- Sleep/wake behavior and command-based listening flow

## 🧠 Core workflow

1. The app listens for voice input.
2. Audio is captured and transcribed.
3. The prompt is checked for wake/shutdown and screen-analysis intents.
4. If needed, a screenshot is captured and analyzed by a vision model.
5. The result is sent to the LLM for the final answer.
6. The response is spoken aloud with text-to-speech.

## 🏗️ Project structure

```text
Jarvis/
├── main.py
├── requirements.txt
├── .env.example
├── README.md
├── modules/
│   ├── __init__.py
│   ├── audio.py
│   ├── brain.py
│   ├── config.py
│   ├── hud.py
│   ├── tts.py
│   └── vision.py
├── docs/
│   ├── SETUP.md
│   ├── ARCHITECTURE.md
│   └── OLLAMA_VISION.md
└── jarvis_error.log
```

## 🚀 Quick start

### 1) Create a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment variables

Copy the sample environment file and add your keys:

```bash
copy .env.example .env
```

Then edit `.env`:

```env
GROQ_API_KEY=your_groq_key_here
ANTHROPIC_API_KEY=your_claude_key_here
```

### 4) Start Ollama vision support

If you want local vision:

```bash
ollama pull llava
ollama serve
```

### 5) Run the project

```bash
python main.py
```

## 🧠 Memory system

JARVIS now includes a lightweight persistent memory layer using SQLite.

Supported memory commands:

- “remember this: I prefer short answers”
- “forget that favorite language”
- “show my memory”
- “show my work memory”
- “show my personal memory”
- “show my developer memory”

Memory categories:

- general
- work
- personal
- developer_preferences

This lets the assistant keep relevant context across sessions without growing the prompt indefinitely.

## 🔧 What this bot uses

- Groq for chat and model inference
- SQLite for persistent memory storage
- OpenAI-style local local pattern with vision fallback logic
- Ollama + LLaVA for offline image understanding
- Anthropic Claude for premium vision fallback
- Pygame for desktop UI rendering
- TTS with `pyttsx3` for spoken responses
- SoundDevice for microphone input

## 📚 Documentation

- [Setup guide](docs/SETUP.md)
- [Architecture overview](docs/ARCHITECTURE.md)
- [Ollama vision guide](docs/OLLAMA_VISION.md)

## 🔐 Environment setup

The app reads API credentials from a `.env` file via `python-dotenv`.

Example:

```env
GROQ_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

## 📌 Notes

- Vision works best when Ollama is installed and `llava` is pulled.
- If no vision backend is available, the app falls back to a helpful text-only response.
- This project is designed as a personal assistant prototype and can be extended with custom commands, memory, and automation.

## 🛠️ Roadmap ideas

- Wake word recognition improvements
- Memory and personal context persistence
- App automation commands
- Better desktop HUD visuals
- Multiple assistant personas
- Web or mobile companion dashboard

## 🙏 Credits

Built around the vision of a personal AI assistant for Paul Adamu / ZeroTrace Intelligence.

---

Made with focus, curiosity, and a little futuristic energy.
