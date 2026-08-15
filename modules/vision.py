# --- VISION.PY ---
# Screen capture & Vision API for screen analysis

import base64
import io
import json
from PIL import ImageGrab
from modules.config import ANTHROPIC_API_KEY

VISION_MODELS = [
    "llama-3.2-90b-vision-preview",  # Original Groq vision model
    "llama-3.2-11b-vision-preview",  # Backup option
    "qwen-vl-max",                   # Qwen's vision-language model if available
    "qwen-vl-plus",                  # Qwen vision variant
    "llama-3.2-vision-preview",      # Alternative Llama
    "llava-1.5-7b-hf",               # LLaVA if available
]

# Initialize Anthropic client if API key is available
anthropic_client = None
if ANTHROPIC_API_KEY:
    try:
        from anthropic import Anthropic
        anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
        print("[VISION] Anthropic Claude client initialized for vision")
    except Exception as e:
        print(f"[VISION] Failed to initialize Anthropic client: {e}")
else:
    print("[VISION] ANTHROPIC_API_KEY not found - Claude vision unavailable")

# Try to initialize Ollama client for local vision (FREE!)
ollama_available = False
try:
    import requests
    # Test if Ollama is running
    response = requests.get("http://localhost:11434/api/tags", timeout=2)
    if response.status_code == 200:
        models = response.json().get("models", [])
        if any("llava" in m.get("name", "").lower() for m in models):
            ollama_available = True
            print("[VISION] Ollama with LLaVA detected - local vision available!")
        else:
            print("[VISION] Ollama running but LLaVA not found. Run: ollama pull llava")
except Exception as e:
    print(f"[VISION] Ollama not available (install from ollama.ai): {e}")


def _call_vision_model(client, prompt, base64_image):
    """Try vision models in order: Ollama (free), Claude (paid), Groq (decommissioned)."""
    
    # Try Ollama FIRST (FREE and LOCAL!)
    if ollama_available:
        try:
            print("[VISION] Attempting local Ollama + LLaVA vision...")
            import requests
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llava",
                    "prompt": prompt,
                    "images": [base64_image],
                    "stream": False,
                },
                timeout=60,
            )
            
            if response.status_code == 200:
                result = response.json().get("response", "").strip()
                if result:
                    print("[VISION] Ollama vision succeeded!")
                    return result
        except Exception as e:
            print(f"[VISION] Ollama vision failed: {e}")
    
    # Try Claude vision (requires API credits)
    if anthropic_client:
        try:
            print("[VISION] Attempting Claude 3.5 Sonnet vision...")
            response = anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": base64_image,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
            )
            result = response.content[0].text.strip()
            print("[VISION] Claude vision succeeded!")
            return result
        except Exception as e:
            print(f"[VISION] Claude vision failed: {e}")
    
    # Fallback to Groq vision models
    data_url = f"data:image/jpeg;base64,{base64_image}"
    last_error = None

    for model in VISION_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url, "detail": "low"}},
                        ],
                    }
                ],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            last_error = e
            print(f"[VISION] Vision model '{model}' failed: {e}")

    # Fallback: Try using a text-only model to respond helpfully
    print("[VISION] No vision models available, using text-based response...")
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": f"The user asked: '{prompt}'. Screen vision analysis is currently unavailable. Provide a helpful response acknowledging this limitation and offer to help them describe what they see or assist in another way. Keep it brief and professional.",
                }
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[VISION] Fallback text model also failed: {e}")
        raise RuntimeError(f"No supported vision model worked. Last error: {last_error}")


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
    Determines if the user is asking JARVIS to shut down.
    Returns True if shutdown keywords are detected.
    """
    keywords = [
        "shutdown", "shut down", "exit", "quit", "close", "stop",
        "goodbye", "bye", "see you", "turn off", "power off", "terminate",
        "end", "finish", "sleep", "hibernate"
    ]
    
    prompt_lower = prompt.lower()
    return any(keyword in prompt_lower for keyword in keywords)


def should_wake(prompt):
    """
    Determines if the user is trying to wake up JARVIS.
    Returns True if wake keywords are detected.
    """
    keywords = [
        "hello", "wake", "wake up", "hey jarvis", "jarvis",
        "hi", "good morning", "good afternoon", "good evening",
        "you there", "are you there"
    ]
    
    prompt_lower = prompt.lower()
    return any(keyword in prompt_lower for keyword in keywords)


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
