# JARVIS Troubleshooting Guide

## Common Issues & Solutions

### Audio & Microphone

#### Microphone Not Detected
**Symptoms**: App starts but doesn't capture audio. "No input device available" error.

**Solutions**:
1. **Windows Settings**
   - Go to Settings → Sound → Input devices
   - Verify your microphone is listed and enabled
   - Set as default input device if needed
   - Test with another app (Zoom, Teams, etc.)

2. **Device Manager**
   - Open Device Manager (Win+X → Device Manager)
   - Look for "Audio inputs and outputs"
   - Ensure microphone is not disabled (yellow exclamation mark)
   - Update audio drivers if needed

3. **App Permissions**
   - Settings → Privacy & security → Microphone
   - Ensure Python has microphone permission
   - You may see a permission prompt on first run

4. **Multiple Microphones**
   - If multiple mics are connected, JARVIS uses the default one
   - Set your desired microphone as default in Sound settings

#### Audio Crackling or Distortion
**Solutions**:
- Lower microphone input level (Settings → Sound → Volume mixer)
- Move microphone away from speakers to avoid feedback
- Close other apps using audio
- Check for USB hub interference (try direct USB port)

#### No Sound Output (TTS Not Speaking)
**Solutions**:
1. **Check Windows Sound**
   - Settings → Sound → Volume mixer
   - Ensure output device is not muted
   - Check speaker is connected and enabled

2. **Narrator Enabled**
   - Settings → Ease of Access → Narrator
   - Windows Narrator must be enabled for pyttsx3 to work
   - Toggle on if off

3. **Voice Selection**
   - Edit `modules/config.py` if TTS sounds wrong
   - Adjust `VOICE_RATE` (default: 210, increase for faster)
   - Adjust `VOICE_PITCH` (default: 1.25, increase for higher pitch)

#### Speech Recognition Not Working
**Solutions**:
- Microphone must be enabled (see above)
- Speak clearly and at normal volume
- Ensure no background noise (fans, AC, traffic)
- Test with simple commands: "What time is it?"

---

### API & Authentication

#### GROQ_API_KEY Not Found
**Error**: "WARNING: GROQ_API_KEY not found in .env file!"

**Solutions**:
1. **Verify `.env` file exists**
   ```bash
   dir .env  # Windows
   ls -la .env  # Mac/Linux
   ```

2. **Check key format**
   - `.env` should have exactly: `GROQ_API_KEY=your_actual_key`
   - No spaces around `=`
   - No quotes around the key value

3. **Restart Terminal**
   - Close and reopen terminal after creating/editing `.env`
   - Environment variables don't reload automatically

4. **Get a Groq Key**
   - Visit https://console.groq.com
   - Sign up for free
   - Create API key in your account dashboard
   - Copy and paste into `.env`

#### Groq API Rate Limit
**Error**: "Rate limit exceeded" or 429 status code

**Solutions**:
- Free tier has rate limits (check your Groq dashboard)
- Wait a few minutes before next query
- Upgrade Groq account for higher limits
- JARVIS automatically retries once with exponential backoff

#### Invalid Groq API Key
**Error**: "Unauthorized" or 401 error

**Solutions**:
- Copy key again from https://console.groq.com (no typos)
- Verify key hasn't expired
- Check `.env` file has no extra spaces or quotes
- Regenerate key if unsure

---

### Cloudflare Vision

#### Cloudflare Credentials Missing
**Symptoms**: Screen analysis doesn't work, falls back to text-only

**Solutions**:
1. **Get Cloudflare Token**
   - Visit https://dash.cloudflare.com/profile/api-tokens
   - Click "Create Token"
   - Select "Workers AI" scope (or "All Zones" for broader access)
   - Copy token to `.env` as `CLOUDFLARE_API_TOKEN`

2. **Get Account ID**
   - Go to https://dash.cloudflare.com
   - Look at URL: `https://dash.cloudflare.com/[ACCOUNT_ID]/`
   - Copy Account ID to `.env` as `CLOUDFLARE_ACCOUNT_ID`

#### Cloudflare Returns 403 - Model Agreement Required
**Error**: "AiError: Model Agreement: Prior to using this model, you must submit the prompt 'agree'."

**This is NORMAL on first use.** You must accept the Meta Llama Vision model agreement once:

```powershell
# Run this command ONCE in PowerShell from the Jarvis folder:
$account = (Get-Content .env | Select-String "CLOUDFLARE_ACCOUNT_ID").ToString().Split("=")[1].Trim()
$token = (Get-Content .env | Select-String "CLOUDFLARE_API_TOKEN").ToString().Split("=")[1].Trim()

python -c "import requests; r = requests.post('https://api.cloudflare.com/client/v4/accounts/$account/ai/run/@cf/meta/llama-3.2-11b-vision-instruct', headers={'Authorization': 'Bearer $token', 'Content-Type': 'application/json'}, json={'prompt': 'agree'}, timeout=30); print('Status:', r.status_code); print('Response:', r.text[:200])"
```

**Expected output:**
```
Status: 200
Response: {"result": {"response": "ok"}}
```

After this, screen analysis will work.

#### Cloudflare Token Missing Permissions
**Error**: 403 Forbidden (after agreement already accepted)

**Solutions**:
1. Check token has "Workers AI" permissions
2. Create a new token with proper scope
3. Verify `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` are correct

#### Cloudflare Vision Still Not Working
**Solutions**:
- Without Cloudflare, app falls back to text-only mode (still functional!)
- If you don't need vision, you can skip Cloudflare setup entirely
- Try simple command: "Take a screenshot" (doesn't require Cloudflare)

---

### Memory & Database

#### Memory Not Persisting
**Symptoms**: Saved memories don't appear after restart

**Solutions**:
1. **Check database file exists**
   ```bash
   ls -la jarvis_memory.db  # Mac/Linux
   dir jarvis_memory.db  # Windows
   ```

2. **Database corruption**
   - Delete `jarvis_memory.db` to reset
   - Run app again to recreate fresh database
   - All memories will be cleared, but app will work normally

3. **Permission issue**
   - Ensure write permission for `.` folder
   - Run terminal as administrator if needed

#### Memory Commands Not Working
**Solutions**:
- Say "Remember this:" before the fact
- Say "Forget that:" to remove memories
- Use "Show my memory" to verify what's saved
- Memory is case-insensitive

---

### Commands & Actions

#### Command Not Recognized
**Symptoms**: JARVIS responds with "I don't understand" or doesn't execute action

**Solutions**:
- Say the exact command phrasing (see Command Reference in README)
- Speak clearly, not too fast or quiet
- Remove background noise
- Test with simple commands first: "What time is it?"

#### Wake Word Not Detected
**Symptoms**: JARVIS doesn't respond when you speak

**Make sure you use JARVIS-specific wake words:**
- ✅ "Hey JARVIS"
- ✅ "Hello JARVIS"
- ❌ "Hey" (too generic)
- ❌ "Wake" (triggers sleep instead)

#### App Opens But Nothing Happens
**Solutions**:
1. Check console output for error messages
2. Verify microphone is working and enabled
3. Check API keys are set (`GROQ_API_KEY` is required)
4. Run tests: `python -m unittest discover tests -v`

---

### Performance

#### Response is Slow (>2 seconds)
**Possible Causes**:
- Network latency to Groq servers
- Many memories loaded (slows context)
- Computer under heavy load

**Solutions**:
- Groq free tier may have slight delays
- Clear old memories if excessive
- Close other CPU-intensive apps
- Normal response time: 500ms - 1 second

#### High CPU Usage
**Solutions**:
- Pygame HUD refreshes at 60 FPS; can cause high CPU
- Close other apps
- Check Task Manager for other processes

#### High Memory Usage
**Solutions**:
- App uses ~150MB normally
- Memory increases with large conversation history
- Clear memory with "Clear memory" command
- Restart app to reset memory buffer

---

### Integration & Compatibility

#### App Crashes Immediately
**Solutions**:
1. Check Python version: `python --version` (need 3.10+)
2. Check dependencies: `pip list`
3. Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
4. Check for error logs in console output

#### Works in Terminal but Not from Shortcut
**Solutions**:
- Shortcut must include full path to python
- Working directory must be set to Jarvis folder
- Example batch file:
  ```batch
  cd C:\Users\[YourName]\Documents\Jarvis
  .venv\Scripts\python.exe main.py
  ```

#### Pygame Window Issues
**Solutions**:
- HUD window may appear off-screen
- Drag it back if not visible
- Click on terminal window if HUD is unresponsive
- Adjust window size in `modules/config.py` (WINDOW_WIDTH, WINDOW_HEIGHT)

---

### Getting Help

#### Check Debug Output
Enable debug logging by adding to `main.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Run Tests
```bash
python -m unittest discover tests -v
```

All tests should pass. If not, it indicates a configuration issue.

#### Common Solutions Checklist
- [ ] Python 3.10+ installed
- [ ] Virtual environment activated
- [ ] `requirements.txt` installed (`pip install -r requirements.txt`)
- [ ] `.env` file exists with `GROQ_API_KEY`
- [ ] Microphone is enabled and working
- [ ] Windows Narrator is enabled (for TTS)
- [ ] Tests pass (`python -m unittest discover tests -q`)

---

## Still Having Issues?

1. **Check the console output** for specific error messages
2. **Run the test suite** to verify configuration: `python -m unittest discover tests -v`
3. **Try simple commands first** like "What time is it?"
4. **Review the ARCHITECTURE.md** to understand data flow
5. **Check .env file** for proper formatting (no quotes, exact key names)

Remember: JARVIS falls back gracefully. If something doesn't work, other features will still be available.
