"""
config.py - Central settings for AI Avatar Greeting Studio.

Every value has a sensible default, so the app works without any setup.
You can override a value WITHOUT editing this file by setting an
environment variable before starting the app, for example (Windows CMD):

    set OLLAMA_MODEL=qwen2.5:0.5b
    python app.py
"""
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Folders
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = Path(os.environ.get("GREETING_OUTPUT_DIR", BASE_DIR / "output"))
AUDIO_DIR = OUTPUT_DIR / "audio"      # generated speech (.wav)
VIDEO_DIR = OUTPUT_DIR / "videos"     # recorded greeting videos (.webm / .mp4)
TMP_DIR = OUTPUT_DIR / "tmp"          # short-lived helper files

# ---------------------------------------------------------------------------
# Web server
# ---------------------------------------------------------------------------
HOST = os.environ.get("GREETING_HOST", "127.0.0.1")   # local machine only
PORT = int(os.environ.get("GREETING_PORT", "5000"))
MAX_UPLOAD_MB = 100                                     # biggest video we accept

# ---------------------------------------------------------------------------
# Local LLM (Ollama)
# ---------------------------------------------------------------------------
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")
# Seconds to wait for one greeting. The first request after starting the
# computer is slower because the model has to be loaded into RAM.
LLM_TIMEOUT_SECONDS = float(os.environ.get("LLM_TIMEOUT_SECONDS", "120"))
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.8"))
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "260"))
# If True, the app uses the clearly-labelled template generator when the LLM
# cannot be reached. The UI always shows which generator produced the text.
ALLOW_TEMPLATE_FALLBACK = os.environ.get("ALLOW_TEMPLATE_FALLBACK", "1") == "1"

# ---------------------------------------------------------------------------
# Text-to-speech (pyttsx3)
# ---------------------------------------------------------------------------
TTS_RATE = int(os.environ.get("TTS_RATE", "165"))     # words per minute
TTS_TIMEOUT_SECONDS = float(os.environ.get("TTS_TIMEOUT_SECONDS", "90"))

# ---------------------------------------------------------------------------
# Greeting options shown in the form
# ---------------------------------------------------------------------------
OCCASIONS = ["Birthday", "Anniversary", "Congratulations", "Thank You",
             "Welcome", "Festival", "Custom"]
TONES = ["Friendly", "Formal", "Funny", "Heartfelt"]
LENGTHS = {"Short": (40, 65), "Medium": (70, 100)}     # target word ranges

# Language code -> details. "needs_voice" is the text a Windows voice name
# must contain for speech in that language (None = any English voice works).
LANGUAGES = {
    "en": {"label": "English", "needs_voice": None},
    "hinglish": {"label": "Hinglish (Hindi in English letters)", "needs_voice": None},
    "hi": {"label": "Hindi (Devanagari)", "needs_voice": "hindi"},
}

for _folder in (AUDIO_DIR, VIDEO_DIR, TMP_DIR):
    _folder.mkdir(parents=True, exist_ok=True)
