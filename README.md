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
- **Worldview Reference**: Search balanced local summaries of religious and nonreligious traditions, with optional user-requested, dated analytical reflections.
- **Autonomous Task Orchestration**: Create dependency-aware task tracks that JARVIS executes automatically.
- **OpenStreetMap Business Intelligence**: Find businesses without websites globally—100% free, no API keys required.
- **Butler-Grade TTS**: Dynamic speech modulation that changes rate and tone based on emotion and context.
- **Sleep/Wake Modes**: Enter low-power listening state or full shutdown.
- **Animated Desktop HUD**: Real-time status display with volume visualization, a mute button, and an interactive chat bar.
- **Safe tool routing**: Only exact time, microphone mute, and assistant sleep phrases are handled locally; other requests use structured Groq tools. PC sleep/shutdown requires a separate confirmation.

## 🧠 Core Workflow

1. **Input**: The app listens for voice input and transcribes via Groq Whisper.
2. **Routing**: The prompt is parsed for wake words, actions, and screen-analysis intents.
3. **Reasoning**: Groq's pinned `openai/gpt-oss-20b` model answers normally or selects from structured, allowlisted tools.
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
USER_NAME=Your Name
ASSISTANT_NAME=JARVIS
ADDRESS_AS=Sir
```

`GROQ_API_KEY` is required to start the assistant. The Groq model is pinned to
`openai/gpt-oss-20b` in `modules/config.py`; it is not overridden through `.env`.
The HUD's **SETTINGS** panel edits and saves the three identity values above to `.env`.

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
- **"Research [topic]"** $\rightarrow$ Search DuckDuckGo using a main query and related angles, then save result titles, snippets, and source links to a Markdown report in `research/`.
- **"Search the web for [query]"** $\rightarrow$ DuckDuckGo research report; results are search snippets and links, not full-page verification.
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

Long-term memory is saved only when you explicitly ask JARVIS to remember a fact or note. Ordinary conversation is kept as recent chat history, not automatically promoted to memory.

## Proactive Runtime
JARVIS can deliver requested timer alerts and, after an idle period, ask whether you want to resume a recently unfinished workflow. Proactive messages are deterministic; this runtime does not make LLM requests or execute tools on its own. Timer alerts are stored in the local SQLite database so they can be delivered after a restart.

The runtime is enabled by default. It suppresses speech during configured quiet hours (default `22:00-08:00` local time), while the assistant is muted or sleeping, during active processing or speech, and delays workflow follow-ups until you have been idle for 15 minutes. Workflow follow-ups have a one-hour cooldown and are limited to once per track per run. Set `PROACTIVE_ENABLED=false` to turn off workflow follow-ups; explicit timer alerts remain enabled. Configure `PROACTIVE_IDLE_MINUTES`, `PROACTIVE_COOLDOWN_MINUTES`, `PROACTIVE_POLL_SECONDS`, and `PROACTIVE_QUIET_HOURS` in `.env` as needed.

## Worldview Reference & Reflection
JARVIS can search the local `knowledge/worldviews.md` reference for introductory summaries of Christianity, Islam, Judaism, Buddhism, Hindu traditions, Sikhism, atheism, agnosticism, secular humanism, and a note on Indigenous and other traditions. The summaries are non-exhaustive and emphasize internal diversity.

Ask JARVIS to compare worldviews to search this reference. Ask it to "reflect on" a question to generate and save a dated analytical entry; ask it to review its worldview journal to retrieve recent entries. Entries are stored in `jarvis_memory.db` (up to 30). Reflection is never scheduled automatically. JARVIS does not claim consciousness, personal faith, or lived experience, and does not choose or perform religious practices.

Reflection requests, recent journal context, and the local reference are sent to the configured Groq model to generate an entry. Journal storage is local SQLite and is not encrypted by this feature; do not include information you would not send to that service.

If explicitly asked to choose a religion or worldview for its analytical position, JARVIS can start a bounded, resumable selection study (default 14 days, with daily updates). Before a study starts, the configured user must explicitly consent to both local storage and Groq processing; for example: "I consent to storing my worldview analysis locally and processing its research with Groq." Consent is per configured `USER_NAME`; this desktop profile name is not an authentication mechanism and does not protect one local user from another with access to the database.

Each study cycle stores its full analytical conclusion, prior conclusion, and source records. The prompt requests comparative scores, reasons and counterarguments, uncertainty/evidence gaps, and an explanation of what changed and why. Web search snippets are unverified, local book excerpts are identified by path, and research prompts, excerpts, and conclusions are sent to Groq. Records are stored in the local, unencrypted SQLite database. Ask for the current worldview position or its history to retrieve the analysis. Say "revoke my worldview profile consent and delete its records" to stop retaining the profile and remove its saved selection-study data.

This feature is a functional analogue only: it is not personal faith, subjective experience, an autonomous conscious choice, or a promise to follow practices. JARVIS can explain religious practices but does not perform them or claim to have done so.

## 🧪 Tests
Run the regression suite from the project root (the same command CI runs on
Python 3.10 and 3.11):

```bash
pytest --cov=modules --cov-report=term-missing --cov-fail-under=50
```

GitHub Actions also uses Ruff to check for unused imports in `modules/` and
`tests/` on every push and pull request.

## 🔧 Tech Stack
- **LLM**: Groq `openai/gpt-oss-20b` for tool-capable reasoning.
- **Vision**: Cloudflare Workers AI / Groq Vision.
- **Automation**: Playwright for browser-based account analysis.
- **Storage**: SQLite for persistent, category-based memory.
- **UI**: Pygame for the animated HUD.
- **OS**: Python `subprocess` and `shutil` for system-level automation.

## 🙏 Credits
Built around the vision of a personal AI assistant for Paul Adamu / ZeroTrace Intelligence.
---
Made with focus, curiosity, and a little futuristic energy.
