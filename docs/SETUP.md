# JARVIS Setup Guide

## Prerequisites

- **Python 3.10+** (download from https://python.org)
- **Microphone & Speakers** (for voice interaction)
- **Groq API Key** (free tier at https://console.groq.com)

## Step 1: Verify Python Installation

```bash
python --version
```

Should show: `Python 3.10.0` or higher

## Step 2: Create Virtual Environment

Navigate to the Jarvis folder and create an isolated Python environment:

```bash
cd Jarvis
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux
```

You'll see `(.venv)` in your terminal prompt when activated.

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `groq` - LLM and speech recognition
- `requests` - HTTP client for APIs
- `pygame` - Desktop UI rendering
- `pyttsx3` - Text-to-speech engine
- `sounddevice` - Audio capture
- `Pillow` - Image processing
- `python-dotenv` - Environment variable management
- `numpy` - Numerical operations

## Step 4: Configure API Keys

Create a `.env` file in the project root:

```bash
copy .env.example .env  # Windows
cp .env.example .env  # Mac/Linux
```

Edit `.env` and add your keys:

```env
GROQ_API_KEY=your_actual_groq_key_here
CLOUDFLARE_API_TOKEN=your_cloudflare_token_here
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id_here
```

### Getting Your Groq API Key (Required)

1. Visit https://console.groq.com
2. Sign up or log in
3. Click "API Keys" in the left menu
4. Click "Create API Key"
5. Copy the key and paste into `.env`

### Getting Cloudflare Credentials (Optional)

1. Visit https://dash.cloudflare.com/profile/api-tokens
2. Click "Create Token"
3. Select "Workers AI" permissions
4. Copy token to `.env` as `CLOUDFLARE_API_TOKEN`
5. Get Account ID from URL: https://dash.cloudflare.com/[ACCOUNT_ID]/

## Step 5: Verify Setup

Run the test suite to ensure everything is configured:

```bash
python -m unittest discover tests -v
```

You should see: **`OK` and `Ran X tests`**

## Step 6: Run JARVIS

```bash
python main.py
```

The desktop HUD will appear. Try speaking: **"What time is it?"**

## Optional: Cloudflare Vision Setup

For screen analysis (optional feature), accept the model agreement once:

```powershell
$account = (Get-Content .env | Select-String "CLOUDFLARE_ACCOUNT_ID").ToString().Split("=")[1].Trim()
$token = (Get-Content .env | Select-String "CLOUDFLARE_API_TOKEN").ToString().Split("=")[1].Trim()

python -c "import requests; r = requests.post('https://api.cloudflare.com/client/v4/accounts/$account/ai/run/@cf/meta/llama-3.2-11b-vision-instruct', headers={'Authorization': 'Bearer $token', 'Content-Type': 'application/json'}, json={'prompt': 'agree'}, timeout=30); print('Status:', r.status_code)"
```

Expected output: `Status: 200`

## Troubleshooting Setup

### Python command not found
- Reinstall Python from https://python.org
- **Check "Add Python to PATH"** during installation
- Restart terminal after installation

### pip install fails
- Ensure virtual environment is activated (`(.venv)` in prompt)
- Try: `pip install --upgrade pip`
- Then: `pip install -r requirements.txt`

### GROQ_API_KEY not found error
- Verify `.env` file exists in Jarvis folder
- Ensure no quotes around the key value
- Restart terminal after editing `.env`
- Check for extra spaces: `GROQ_API_KEY=key_with_no_spaces`

### Microphone not working
- Check Windows Settings → Sound → Input devices
- Run tests to verify Python can access mic
- See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions

### Tests fail after setup
- All tests should pass with proper `.env` setup
- Check console output for specific error messages
- Verify `GROQ_API_KEY` is correct and active
- Run: `python -c "import groq; print('Groq installed OK')"` to verify installation

## Next Steps

After successful setup:
- Read [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- Try commands from README.md Voice Commands Reference
- Explore custom commands in [modules/actions.py](../modules/actions.py)
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) if issues arise

Add your keys:

```env
GROQ_API_KEY=your_groq_key_here
CLOUDFLARE_API_TOKEN=your_cloudflare_token_here
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id_here
```

**Get your API keys:**
- Groq: https://console.groq.com/ (free tier with high rate limits)
- Cloudflare: https://dash.cloudflare.com/ (optional screen-vision fallback)

## 5) Run the assistant

```bash
python main.py
```

## 6) Cloudflare vision agreement fix

If the app says it cannot analyze the screen and prints a 403 error mentioning the model agreement, do this once:

```powershell
$account = (Get-Content .env | Select-String "CLOUDFLARE_ACCOUNT_ID").ToString().Split("=")[1].Trim()
$token = (Get-Content .env | Select-String "CLOUDFLARE_API_TOKEN").ToString().Split("=")[1].Trim()

python -c "import requests; r = requests.post('https://api.cloudflare.com/client/v4/accounts/$account/ai/run/@cf/meta/llama-3.2-11b-vision-instruct', headers={'Authorization': 'Bearer $token', 'Content-Type': 'application/json'}, json={'prompt': 'agree'}, timeout=30); print(r.status_code); print(r.text)"
```

This submits the required "agree" prompt and unlocks the Meta vision model for that account.

### Common mistake

The bad pattern was adding extra text after the JSON body or using malformed quoting. That creates errors like:

```text
Request body is not valid json
Could not resolve host: agree
```

The Python version above avoids that entirely because it sends real structured JSON.

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
- Confirm the Cloudflare credentials are valid and loaded from the project `.env` file.
- Check the console for provider initialization or API errors.
- If you get the model agreement 403, run the agreement command above once and retry.

### TTS warning on Windows
- Pitch adjustment may not be supported by SAPI5.
- The app catches that and continues; it is not fatal.

---

Use the other docs in this folder for deeper implementation details.
