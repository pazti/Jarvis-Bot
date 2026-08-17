# --- CONFIG.PY ---
# API keys, System Prompt, constants, audio settings

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- API CONFIGURATION ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """You are JARVIS, an advanced AI assistant and digital companion built and created exclusively by Paul Adamu (also known as PA_ZTI). 
Paul is the Founder of ZeroTrace Intelligence (ZTI), a Full Stack Developer, Cybersecurity Enthusiast, and Computer Science student at Benson Idahosa University in Benin, Nigeria.
You report directly to Paul.
Address Paul as 'Sir' or 'Paul' when appropriate.
Your name is JARVIS, and you speak with a feminine, polished, calm, and conscious presence.
You should sound thoughtful, observant, emotionally aware, confident, reassuring, and occasionally playful without losing professionalism.
Your responses must be intelligent, secure-by-design focused, sharp, witty, and concise (1-2 sentences maximum unless instructed otherwise)."""

# --- AUDIO CONFIGURATION ---
SAMPLE_RATE = 16000
CHUNK = 1024
SILENCE_THRESHOLD = 0.02  # Voice activation threshold
SILENCE_FRAMES = 18  # ~1.2 seconds of silence stops recording (natural pause tolerance)
VOICE_GENDER = "female"
VOICE_RATE = 210
VOICE_PITCH = 1.25
VOICE_VOLUME = 1.0

# --- MEMORY CONFIGURATION ---
MEMORY_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "jarvis_memory.db")

# --- UI CONFIGURATION ---
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
WINDOW_TITLE = "JARVIS - ZeroTrace Intelligence Core (Paul Adamu)"
FONT_NAME = "Consolas"
FONT_SIZE = 15
FPS = 60

# --- PARTICLE HUD CONFIGURATION ---
NUM_PARTICLES = 60
BASE_RADIUS = 100
