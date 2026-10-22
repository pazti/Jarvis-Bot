# JARVIS — ZeroTrace Intelligence Core

<p align="center">
  <img src="https://img.shields.io/badge/AI-Voice%20Assistant-8A2BE2?style=for-the-badge&logo=opencv&logoColor=white" alt="AI Voice Assistant" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/Groq%20%2B%20Cloudflare-Active-8A2BE2?style=for-the-badge" alt="Groq and Cloudflare active" />
  <img src="https://img.shields.io/badge/Tests-100%25%20Passing-28a745?style=for-the-badge" alt="All tests passing" />
</p>

> A sleek, voice-driven desktop AI assistant with persistent memory, screen awareness, and autonomous task orchestration.

JARVIS is a personal AI assistant built for voice interaction, real-time screen analysis, and smart local reasoning. He combines Groq's lightning-fast LLM with optional Cloudflare Workers AI for vision tasks, delivering sub-second responses. Unlike basic bots, JARVIS can now **plan, track, and execute complex multi-step workflows** autonomously.

## ✨ Core Features

- **Voice-Driven Interaction**: Listen for natural speech, transcribe via Groq, and respond with a sophisticated "Butler" persona.
- **Screen Awareness**: Analyze your screen with Cloudflare vision or fall back to text-only mode.
- **Persistent Memory**: Save facts, remember preferences, and retrieve context across sessions.
- **Autonomous Task Orchestration**: Create dependency-aware task tracks that JARVIS executes automatically.
- **OpenStreetMap Business Intelligence**: Find businesses without websites globally—100% free, no API keys required.
- **Butler-Grade TTS**: Dynamic speech modulation that changes rate and tone based on emotion and context.
- **Sleep/Wake Modes**: Enter low-power listening state or full shutdown.
- **Animated Desktop HUD**: Real-time status display with volume visualization, a mute button, and an interactive chat bar.

## 🧠 Core Workflow

1. **Input**: The app listens for voice input and transcribes via Groq Whisper.
2. **Routing**: The prompt is parsed for wake words, actions, and screen-analysis intents.
3. **Reasoning**: The LLM (Llama 3) determines if a simple response or a complex **Workflow** is needed.
4. **Execution**: If a workflow is triggered, JARVIS creates a track in SQLite and executes steps via `workflow_handlers`.
5. **Output**: Results are spoken aloud using dynamic prosody and rendered on the HUD.

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
.venv\\Scripts\\activate  # Windows
source .venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt
# IMPORTANT: Install Playwright for TikTok/Browser automation
pip install playwright
python -m playwright install chromium
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

## 🎙️ Voice Commands Reference

### Wake & Sleep
- **"Hey JARVIS"** / **"Hello JARVIS"** $\rightarrow$ Activate assistant
- **"Sleep JARVIS"** / **"Goodbye"** $\rightarrow$ Enter sleep mode
- **"Wake up"** / **"Wake JARVIS"** $\rightarrow$ Exit sleep mode

### TikTok & Business Intelligence (Free & Unlimited)
- **"JARVIS, login to TikTok"** $\rightarrow$ Opens browser for one-time manual login.
- **"JARVIS, analyze the performance of [Username]"** $\rightarrow$ Scrapes analytics and provides growth tips.
- **"Find [Category] in [City] without websites"** $\rightarrow$ Search OpenStreetMap, filter for no-website businesses, and save a CSV report.

### System & Browser Control
- **"Search the web for [query]"** $\rightarrow$ Google search
- **"Open [YouTube/GitHub/Maps]"** $\rightarrow$ Launch specific site
- **"Directions to [place]"** $\rightarrow$ Open Google Maps directions
- **"Open VS Code"** / **"Open Terminal"** $\rightarrow$ Launch local apps

### Memory & Productivity
- **"Remember this: [fact]"** $\rightarrow$ Save to memory
- **"Show my [work/personal/developer] memory"** $\rightarrow$ Retrieve specific contexts
- **"Set a timer for [duration]"** $\rightarrow$ Start countdown
- **"Create a quick note: [text]"** $\rightarrow$ Save note to memory

### Code & Vision
- **"Write code to [task]"** $\rightarrow$ Generate and save code to `generated/`
- **"Summarize my screen"** $\rightarrow$ Analyze current window contents
- **"Open my code and tell me what's wrong"** $\rightarrow$ Vision-based debugging

## ⚙️ Autonomous Task Workflows
JARVIS can now lauch complex a series of tasks. Just say **"Plan a..."** or **"Start a task..."**

| Workflow | Action | Outcome |
| :--- | :--- | :--- |
| **Project Health Check** | "Plan a project health check" | Scans structure, checks `.env`/`reqs`, and reports risks. |
| **Project Backup** | "Plan a project backup" | Creates a timestamped `.zip` excluding `.git` and `.venv`. |
| **Dependency Audit** | "Plan a dependency audit" | Inventories packages and checks for version conflicts. |
| **Git Assistant** | "Plan a Git change review" | Reviews `git diff`, suggests commit messages, and verifies status. |
| **Test Suite** | "Run the test suite" | Discovers tests, executes them, and reports pass rate. |
| **Feature Plan** | "Plan a feature [name]" | Breaks a request into milestones and acceptance criteria. |

## 🧠 Memory System
JARVIS uses SQLite to organize your life into four categories:
- **General**: Default facts and preferences.
- **Work**: Project notes, deadlines, and goals.
- **Personal**: Personal preferences and favorites.
- **Developer**: Coding styles, frameworks, and tool preferences.

## 🔧 Tech Stack
- **LLM**: Groq (Llama 3) for sub-second reasoning.
- **Vision**: Cloudflare Workers AI / Groq Vision.
- **Automation**: Playwright for browser-based account analysis.
- **Storage**: SQLite for persistent, category-based memory.
- **UI**: Pygame for the animated HUD.
- **OS**: Python `subprocess` and `shutil` for system-level automation.

## 🙏 Credits
Built around the vision of a personal AI assistant for Paul Adamu / ZeroTrace Intelligence.
---
Made with focus, curiosity, and a little futuristic energy.
