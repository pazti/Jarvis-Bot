# JARVIS — ZeroTrace Intelligence Core

<p align="center">
  <img src="https://img.shields.io/badge/AI-Voice%20Assistant-8A2BE2?style=for-the-badge&logo=opencv&logoColor=white" alt="AI Voice Assistant" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/Groq%20%2B%20Cloudflare-Active-8A2BE2?style=for-the-badge" alt="Groq and Cloudflare active" />
  <img src="https://img.shields.io/badge/Tests-20%2F20%20Passing-28a745?style=for-the-badge" alt="All tests passing" />
</p>

> A sleek, voice-driven desktop AI assistant with persistent memory, screen awareness, and intelligent command routing.

JARVIS is a personal AI assistant built for voice interaction, real-time screen analysis, and smart local reasoning. It combines Groq's lightning-fast LLM with optional Cloudflare Workers AI for vision tasks, delivering sub-second responses for everyday queries.

## ✨ Core Features

- **Voice-Driven Interaction**: Listen for natural speech, transcribe via Groq, and respond conversationally
- **Screen Awareness**: Analyze your screen with Cloudflare vision or fall back to text-only mode
- **Persistent Memory**: Save facts, remember preferences, and retrieve context across sessions
- **25+ Built-In Actions**: Browser control, file operations, reminders, timers, clipboard management, and more
- **Emotional TTS**: Text-to-speech with emotion detection (serious, casual, thoughtful, playful)
- **Sleep/Wake Modes**: Enter low-power listening state or full shutdown
- **Category-Based Memory**: Organize memories as general, work, personal, or developer preferences
- **Animated Desktop HUD**: Real-time status display with volume visualization

## 🧠 Core workflow

1. The app listens for voice input.
2. Audio is captured and transcribed using Groq Whisper.
3. The prompt is parsed for wake words, actions, and screen-analysis intents.
4. If needed, a screenshot is captured and analyzed by Cloudflare or Groq.
5. The result is processed by the LLM for context-aware response generation.
6. The response is spoken aloud with emotion-based TTS.

## 🚀 Quick Start

### 1) Prerequisites

- Python 3.10+
- Microphone and speakers
- Groq API key (free tier at https://console.groq.com)

### 2) Setup Environment

```bash
# Navigate to project
cd Jarvis

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### 3) Configure API Keys

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_key_here
CLOUDFLARE_API_TOKEN=your_cloudflare_token_here  # Optional
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id_here  # Optional
```

### 4) Run the Assistant

```bash
python main.py
```

The desktop HUD will appear. Start speaking to JARVIS!

## �️ Voice Commands Reference

### Wake & Sleep
- **"Hey JARVIS"** / **"Hello JARVIS"** → Activate assistant
- **"Sleep JARVIS"** / **"Goodbye"** → Enter sleep mode
- **"Wake up"** / **"Wake JARVIS"** → Exit sleep mode
- **"Shutdown JARVIS"** → Full system shutdown

### System Information
- **"What time is it?"** → Current time
- **"What day is it?"** → Current date and day

### System Control
- **"Sleep PC"** → Suspend computer
- **"Shutdown PC"** → Power down computer

### Browser & Web Navigation
- **"Open browser"** → Launch default browser (Google)
- **"Open YouTube"** → Open YouTube in browser
- **"Open GitHub"** → Open GitHub in browser
- **"Search the web for [query]"** → Google search for query

### Files & Applications
- **"Take a screenshot"** → Capture and save screen as PNG
- **"Summarize my screen"** → Analyze current screen contents
- **"Open folder"** → Open project directory
- **"Open VS Code"** / **"Open Code"** → Launch VS Code
- **"Open terminal"** → Launch command terminal
- **"Open Notepad"** → Launch text editor

### Memory Management
- **"Remember this: [fact]"** → Save to general memory
- **"Forget that [topic]"** → Remove from memory
- **"Show my memory"** → Display all memories (all categories)
- **"Show my work memory"** → Show work-related memories
- **"Show my personal memory"** → Show personal memories
- **"Show my developer memory"** → Show developer preferences
- **"Clear memory"** → Erase all saved memories

### Productivity & Time Management
- **"Set a timer for [duration]"** → Start countdown (e.g., "5 minutes", "30 seconds")
- **"Remind me to [task]"** → Set a reminder
- **"Remind me to finish my task"** → Quick task reminder
- **"Start focus mode"** → Activate distraction-free listening
- **"Summarize my day"** → Review activities and progress

### Notes & Drafts
- **"Create a quick note: [text]"** → Save quick note to memory
- **"Draft a message: [content]"** → Draft text for later use

### Clipboard
- **"Read my clipboard"** → Read and speak clipboard contents
- **"Copy last response"** → Copy JARVIS's last response to clipboard

### Screen Analysis (Cloudflare Vision)
- **"Analyze my screen"** → Detailed analysis of what's currently visible
- **"What's on my screen?"** → Same as above
- **"Describe my screen"** → Screen description for task assistance

## 🧠 Memory System

JARVIS includes persistent SQLite-based memory with four categories:

| Category | Use Case |
|----------|----------|
| **general** | Default facts and preferences |
| **work** | Project notes, deadlines, goals |
| **personal** | Personal preferences, favorites |
| **developer_preferences** | Coding styles, frameworks, tools |

Memory persists across sessions and is automatically included in LLM context, allowing JARVIS to learn your preferences over time.

| Category | Use Case |
|----------|----------|
| **general** | Default facts and preferences |
| **work** | Project notes, deadlines, goals |
| **personal** | Personal preferences, favorites |
| **developer_preferences** | Coding styles, frameworks, tools |

Memory persists across sessions and is automatically included in LLM context, allowing JARVIS to learn your preferences over time.

## 🔧 What this bot uses

- **Groq** (Llama 3) for ultra-fast text processing and reasoning (sub-second latency)
- **Cloudflare Workers AI** as an optional screen-analysis fallback
- SQLite for persistent memory storage
- Pygame for desktop UI rendering
- TTS with `pyttsx3` for unified spoken responses
- SoundDevice for microphone input

## 📚 Documentation

- [Setup guide](docs/SETUP.md)
- [Architecture overview](docs/ARCHITECTURE.md)

## � Cloudflare Vision Setup (Optional)

Screen analysis is **optional** but requires one-time policy acceptance:

### 1. Get Cloudflare Credentials
- Visit https://dash.cloudflare.com/profile/api-tokens
- Create token with Workers AI permissions
- Add to `.env` file

### 2. Accept Model Agreement (First Use Only)

Run this **once** from the project directory:

```powershell
$account = (Get-Content .env | Select-String "CLOUDFLARE_ACCOUNT_ID").ToString().Split("=")[1].Trim()
$token = (Get-Content .env | Select-String "CLOUDFLARE_API_TOKEN").ToString().Split("=")[1].Trim()

python -c "import requests; r = requests.post('https://api.cloudflare.com/client/v4/accounts/$account/ai/run/@cf/meta/llama-3.2-11b-vision-instruct', headers={'Authorization': 'Bearer $token', 'Content-Type': 'application/json'}, json={'prompt': 'agree'}, timeout=30); print('Status:', r.status_code)"
```

Expected output: `Status: 200`

### 3. Test Screen Analysis

After acceptance, try: **"Analyze my screen"**

### Without Cloudflare

If you skip this setup, JARVIS automatically falls back to text-only mode—still fully functional!

## 📌 Notes

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
