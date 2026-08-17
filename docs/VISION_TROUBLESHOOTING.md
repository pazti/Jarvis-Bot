# Cloudflare Vision Agreement Fix

## Problem

When you ask JARVIS to analyze the screen, the app may fail with a 403 error like this:

`AiError: Model Agreement: Prior to using this model, you must submit the prompt 'agree'.`

This is not a bug in the app logic. It means the Cloudflare account has not accepted the Meta Llama 3.2 Vision model terms yet.

## Why this happens

The screen-analysis path in the app tries the Cloudflare Workers AI model:

`@cf/meta/llama-3.2-11b-vision-instruct`

Before that model can be used, Cloudflare requires the account to submit the model agreement prompt once.

## The fix

Run this in PowerShell from the project folder.

```powershell
$account = (Get-Content .env | Select-String "CLOUDFLARE_ACCOUNT_ID").ToString().Split("=")[1].Trim()
$token = (Get-Content .env | Select-String "CLOUDFLARE_API_TOKEN").ToString().Split("=")[1].Trim()

python -c "import requests; r = requests.post('https://api.cloudflare.com/client/v4/accounts/$account/ai/run/@cf/meta/llama-3.2-11b-vision-instruct', headers={'Authorization': 'Bearer $token', 'Content-Type': 'application/json'}, json={'prompt': 'agree'}, timeout=30); print(r.status_code); print(r.text)"
```

This is the correct pattern because it sends real JSON, not a malformed string command.

## What success looks like

You want a successful response, usually with a 200 status code and some JSON result data.

If the call returns a 403 agreement error again, it means the account still has not accepted the terms.

## The common mistake

This is the mistake that caused the pain:

```powershell
curl.exe "..." -H "..." --data '{"prompt":"agree"}'
```

If you add extra text after the JSON or format the command incorrectly, PowerShell will break the body and you get:

- `Request body is not valid json`
- `Could not resolve host: agree`

The fix is to send the JSON as a real JSON payload, not as a shell string with trailing junk.

## After the agreement is accepted

Restart the assistant and try:

> Analyze my screen

If the agreement is accepted, the app will stop falling back to the text-only response and should actually use the Cloudflare vision model.

## Related files

- [README.md](README.md)
- [docs/SETUP.md](SETUP.md)
- [modules/vision.py](../modules/vision.py)
