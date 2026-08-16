# Setup Guide

## 1) Install Python

Use Python 3.10 or newer.

```bash
python --version
```

## 2) Create a virtual environment

```bash
cd Jarvis
python -m venv .venv
.venv\Scripts\activate
```

## 3) Install required packages

```bash
pip install -r requirements.txt
```

## 4) Create your environment file

```bash
copy .env.example .env
```

Add your keys:

```env
GROQ_API_KEY=your_groq_key_here
ANTHROPIC_API_KEY=your_claude_key_here
```

## 5) Install Ollama for local vision

Download Ollama from: https://ollama.com/download

Then pull the vision model:

```bash
ollama pull llava
```

Start the service:

```bash
ollama serve
```

## 6) Run the assistant

```bash
python main.py
```

## 7) Troubleshooting

### App does not start
- Ensure the virtual environment is active.
- Check whether dependencies installed correctly.
- Confirm `.env` exists and contains valid keys.

### No voice response
- Verify microphone permissions.
- Confirm `sounddevice` installs correctly.
- Check the console for any runtime errors.

### Vision is not working
- Confirm Ollama is running.
- Confirm `llava` exists in the model list:

```bash
ollama list
```

- If it is missing, run:

```bash
ollama pull llava
```

---

Use the other docs in this folder for deeper implementation details.
