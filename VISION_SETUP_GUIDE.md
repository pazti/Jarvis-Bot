# Vision Setup Guide

## Overview

This project is configured for a Groq-first workflow with an optional Cloudflare vision fallback and a safe text fallback.

## Required environment values

Add the following to your `.env` file:

```env
GROQ_API_KEY=your_groq_key_here
CLOUDFLARE_API_TOKEN=your_cloudflare_token_here
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id_here
```

## Check your setup

1. Confirm the `GROQ_API_KEY` is valid in your Groq console.
2. If you want Cloudflare screen analysis, confirm the token and account ID are set.
3. Run the app:

```bash
python main.py
```

## Troubleshooting

- If there is no voice response, confirm the microphone is available and `sounddevice` is installed.
- If screen analysis is unavailable, the assistant will gracefully fall back to a text-only response.
- If the app logs a vision error, verify the Cloudflare credentials or keep the fallback mode enabled.

## Notes

- Older provider integrations were removed from this project.
- Vision support is now intentionally limited to Cloudflare when configured, otherwise a safe text fallback is used.
