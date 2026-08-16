# Ollama Vision Guide

## Why use Ollama?

Ollama gives you a free local route for image understanding without needing a cloud vision API for every screenshot.

This project checks for Ollama at:

```text
http://localhost:11434/api/tags
```

If a model like `llava` is installed, it tries to use it first for screen analysis.

## Install Ollama

1. Download Ollama from the official website.
2. Install and verify it works:

```bash
ollama --version
```

## Pull a vision model

```bash
ollama pull llava
```

## Start the service

```bash
ollama serve
```

## Test it manually

```bash
ollama run llava
```

Then ask it something like:

```text
Describe this image.
```

## Check installed models

```bash
ollama list
```

## Recommended flow for this project

- Keep Ollama running in the background
- Pull `llava`
- Run the desktop app
- If the assistant needs to inspect the screen, it will try the local model automatically

## Troubleshooting

### The app says Ollama is not available
- Ollama may not be installed or running.
- Start it with:

```bash
ollama serve
```

### The app says LLaVA not found
- Pull the model again:

```bash
ollama pull llava
```

### Vision returns poor results
- The screenshot is intentionally compressed for lower token load.
- For best results, use smaller, clearer desktop captures.
- Consider adding a different local or cloud model later.

## Notes

This project is intentionally built so local vision is preferred, but it still supports premium fallbacks if you configure keys in `.env`.
