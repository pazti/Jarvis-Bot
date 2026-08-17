# --- VISION.PY ---
# Screen capture & Vision API for screen analysis (Cloudflare → text fallback)

import base64
import io
import json
import re
import requests
from PIL import ImageGrab
from modules.config import CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID


def _normalize_prompt(prompt):
    return " ".join((prompt or "").lower().split())


def _matches_any(prompt, phrases):
    normalized = _normalize_prompt(prompt)
    if not normalized:
        return False
    for phrase in phrases:
        if re.search(rf"\b{re.escape(phrase)}\b", normalized):
            return True
    return False


# Initialize Cloudflare Workers AI client
cloudflare_ready = False
if CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID:
    print("[VISION] CLOUDFLARE_API_TOKEN found")
    print("[VISION] CLOUDFLARE_ACCOUNT_ID found")
    cloudflare_ready = True
    print("[VISION] Cloudflare Workers AI enabled as fallback")
    print("[VISION] Cloudflare vision requires policy acceptance before image analysis works. Run the 'agree' prompt once for this account, or Cloudflare will reject screen-analysis requests with a 403 error.")
else:
    print("[VISION] Cloudflare credentials not found - Workers AI vision unavailable")


def _call_cloudflare_vision(prompt, base64_image):
    """Call Cloudflare Workers AI for vision analysis using the supported model route."""
    if not cloudflare_ready:
        return None

    model_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/meta/llama-3.2-11b-vision-instruct"
    headers = {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    def _post(payload):
        return requests.post(model_url, headers=headers, json=payload, timeout=30)

    try:
        print("[VISION] Attempting Cloudflare Workers AI vision...")

        agreement_payload = {"prompt": "agree"}
        agreement_response = _post(agreement_payload)
        if agreement_response.status_code == 403 and "Model Agreement" in (agreement_response.text or ""):
            print("[VISION] Model agreement not yet accepted. Retrying with required agreement prompt...")
            agreement_result = agreement_response.json() if hasattr(agreement_response, "json") else {}
            if not isinstance(agreement_result, dict):
                agreement_result = {}
            if "result" in agreement_result:
                print("[VISION] Cloudflare model agreement already accepted.")

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 256,
            "temperature": 0.2,
        }

        response = _post(payload)

        if response.status_code == 200:
            result = response.json()
            if isinstance(result, dict):
                text = None
                if "result" in result and isinstance(result["result"], dict):
                    text = result["result"].get("response") or result["result"].get("answer")
                elif "response" in result:
                    text = result.get("response")

                if text:
                    print("[VISION] Cloudflare vision succeeded!")
                    return str(text).strip()
        elif response.status_code == 403 and "Model Agreement" in (response.text or ""):
            print("[VISION] Cloudflare vision requires policy acceptance. Submit the 'agree' prompt once for this account to unlock the model.")
            return None
        else:
            print(f"[VISION] Cloudflare returned status {response.status_code}")
            print(f"[VISION] Response: {response.text[:200]}")
    except Exception as e:
        print(f"[VISION] Cloudflare vision failed: {e}")

    return None


def _call_vision_model(client, prompt, base64_image):
    """Try Cloudflare Workers AI first, then fall back to a text-only Groq response."""
    # Try Cloudflare Workers AI (preferred fallback)
    cloudflare_result = _call_cloudflare_vision(prompt, base64_image)
    if cloudflare_result:
        return cloudflare_result

    # Final fallback: text-only response via Groq
    print("[VISION] Cloudflare vision requires policy acceptance. Falling back to text-only mode until the model agreement is accepted.")
    if client:
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "user",
                        "content": f"The user asked: '{prompt}'. Screen vision analysis is currently unavailable. Provide a helpful response acknowledging this limitation and offer to help them describe what they see or assist in another way. Keep it brief and professional.",
                    }
                ],
                max_tokens=256,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[VISION] Fallback text model also failed: {e}")

    raise RuntimeError("No supported vision model worked. Check API keys and internet connection.")


def capture_screen():
    """Capture the current screen and return as PIL Image."""
    try:
        screenshot = ImageGrab.grab()
        return screenshot
    except Exception as e:
        print(f"[VISION] Screen capture error: {e}")
        return None


def screenshot_to_base64(max_width=320, quality=20):
    """
    Capture screen, compress to Base64 for Groq Vision API.
    Aggressively compresses to stay within token limits.
    
    Args:
        max_width: Max width for compression (default 320 for low token usage)
        quality: JPEG quality 0-100 (default 20 for maximum compression)
    
    Returns:
        Base64 encoded string of the compressed screenshot
    """
    try:
        screenshot = capture_screen()
        if screenshot is None:
            return None

        # Ensure we can save a JPEG without alpha-channel issues
        if screenshot.mode in ("RGBA", "LA", "P"):
            screenshot = screenshot.convert("RGB")

        # Resize for API limits and token efficiency
        if screenshot.width > max_width:
            ratio = max_width / screenshot.width
            new_height = max(1, int(screenshot.height * ratio))
            from PIL import Image
            screenshot = screenshot.resize((max_width, new_height), Image.Resampling.LANCZOS)

        # Convert to JPEG with aggressive compression to reduce tokens
        buffer = io.BytesIO()
        screenshot.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=False)
        buffer.seek(0)

        # Encode to Base64
        base64_image = base64.b64encode(buffer.read()).decode("utf-8")
        print(f"[VISION] Screenshot encoded to Base64 ({len(base64_image)} bytes, max_width={max_width}, quality={quality})")
        return base64_image
    except Exception as e:
        print(f"[VISION] Base64 encoding error: {e}")
        return None


def should_analyze_screen(prompt):
    """
    Determines if the user is asking JARVIS to look at or analyze the screen.
    Returns True if keywords suggest screen analysis is needed.
    """
    keywords = [
        "screen", "see", "look", "show", "display", "what's on", 
        "read", "window", "tab", "browser", "app", "application",
        "code", "image", "picture", "visual", "watch", "observe",
        "capture", "screenshot", "view", "analyze", "what do you see",
        "can you see", "check my", "show me"
    ]
    
    prompt_lower = prompt.lower()
    return any(keyword in prompt_lower for keyword in keywords)


def should_shutdown(prompt):
    """
    Determines if the user is explicitly asking JARVIS to shut down.
    This intentionally excludes farewell keywords handled separately.
    """
    prompt_lower = _normalize_prompt(prompt)
    if "nadia" in prompt_lower:
        return False

    keywords = [
        "shutdown", "shut down", "power off", "turn off", "exit app",
        "quit app", "close app", "terminate", "end session", "complete shutdown"
    ]
    return _matches_any(prompt_lower, keywords)


def should_wake(prompt):
    """
    Determines if the user is trying to wake up JARVIS.
    Avoid false positives from other names or generic greetings.
    """
    prompt_lower = _normalize_prompt(prompt)
    if "nadia" in prompt_lower:
        return False

    if not prompt_lower:
        return False

    if "jarvis" not in prompt_lower:
        return False

    wake_phrases = [
        "hello jarvis", "hey jarvis", "hi jarvis",
        "wake up jarvis", "jarvis wake up", "wake jarvis",
        "good morning jarvis", "good afternoon jarvis", "good evening jarvis",
        "are you there jarvis", "jarvis are you there", "you there jarvis",
        "jarvis hello", "jarvis hey", "jarvis hi",
    ]

    return _matches_any(prompt_lower, wake_phrases) or (
        ("wake up" in prompt_lower or "are you there" in prompt_lower or "you there" in prompt_lower) and "jarvis" in prompt_lower
    )


def should_goodbye(prompt):
    """
    Determines if the user is saying goodbye (sleep with summary).
    This is distinct from a hard shutdown command.
    """
    prompt_lower = _normalize_prompt(prompt)
    if "nadia" in prompt_lower:
        return False

    keywords = [
        "goodbye", "bye", "good night", "see you later", "see ya",
        "catch you later", "take care", "talk to you later", "til later"
    ]
    return _matches_any(prompt_lower, keywords)


def analyze_screen(client, groq_api_key):
    """
    Analyze the current screen using a Groq vision-capable model.
    Falls back to text-based response if vision models unavailable.
    
    Args:
        client: Groq client instance
        groq_api_key: API key for authentication
    
    Returns:
        Analysis text from the model
    """
    try:
        base64_image = screenshot_to_base64()
        if base64_image is None:
            return "Unable to capture screen for analysis"

        print("[VISION] Sending screenshot to Groq for analysis...")
        prompt = "Analyze this screenshot. Describe what's visible, including apps, windows, text, and any important UI elements. Keep the answer concise but useful."
        analysis = _call_vision_model(client, prompt, base64_image)
        print(f"[VISION] Analysis complete: {analysis[:100]}...")
        return analysis

    except RuntimeError as e:
        # Vision models not available - provide graceful fallback
        print(f"[VISION] Screen analysis unavailable: {e}")
        return "Sir, screen analysis capability is temporarily unavailable. Please describe what you see on the screen, and I'll assist you with that information."
    except Exception as e:
        print(f"[VISION] Vision API error: {e}")
        import traceback
        traceback.print_exc()
        return "Screen analysis encountered an error. Please try again or describe what's on your screen."


def describe_screen_for_task(client, task_description):
    """
    Capture screen and get analysis for a specific task context.
    Falls back to text-based response if vision models unavailable.
    
    Args:
        client: Groq client instance
        task_description: What JARVIS should look for or analyze
    
    Returns:
        Analysis from the model tailored to the task
    """
    try:
        base64_image = screenshot_to_base64()
        if base64_image is None:
            return "Unable to capture screen"

        print(f"[VISION] Analyzing screen for task: {task_description}")
        prompt = f"Please analyze this screenshot and answer this request: {task_description}. Focus on the visible elements in the screen and give a short, direct answer."
        analysis = _call_vision_model(client, prompt, base64_image)
        print(f"[VISION] Analysis complete: {analysis[:100]}...")
        return analysis

    except RuntimeError as e:
        # Vision models not available - ask user to describe
        print(f"[VISION] Screen analysis unavailable: {e}")
        return f"Sir, screen analysis is temporarily unavailable. Could you please describe what you see? That will help me assist you with: {task_description}"
    except Exception as e:
        print(f"[VISION] Task analysis error: {e}")
        import traceback
        traceback.print_exc()
        return f"Screen analysis encountered an error. Please describe what you see, and I'll assist you."
