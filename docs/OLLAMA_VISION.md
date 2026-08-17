# Vision Setup

This project no longer relies on local Ollama-based vision.

Use the configured cloud provider fallback instead:
- Cloudflare Workers AI (optional vision fallback)
- Groq text fallback when screen vision is unavailable

If screen analysis fails, confirm:
- the `.env` file contains valid Cloudflare credentials and a Groq key
- the environment has the required Python packages installed
- the console shows any provider initialization or API errors
