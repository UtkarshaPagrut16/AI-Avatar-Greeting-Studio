"""
tts_service.py - Turns the greeting script into a real speech audio file (.wav).

Engine: pyttsx3 (free, offline). On Windows it uses the built-in Microsoft
SAPI5 voices (for example "Microsoft Zira" / "Microsoft David").
The heavy work happens in services/tts_worker.py, run as a separate process.
"""
import importlib.util
import json
import os
import subprocess
import sys
import time
import uuid
import wave
from pathlib import Path

import config


class TTSError(Exception):
    """Base class for speech problems. `user_message` is safe to show in the UI."""

    user_message = "Speech could not be generated."

    def __init__(self, detail=""):
        super().__init__(detail or self.user_message)
        self.detail = detail


class TTSUnavailableError(TTSError):
    user_message = ("The offline speech library (pyttsx3) is not installed. "
                    "Run run_windows.bat again or: pip install -r requirements.txt")


class TTSVoiceMissingError(TTSError):
    user_message = "No installed voice supports this language."


class TTSTimeoutError(TTSError):
    user_message = "Speech generation took too long and was stopped."


class TTSFailedError(TTSError):
    user_message = "The speech engine reported an error while creating the audio file."


_voice_cache = {"time": 0.0, "voices": None}
VOICE_CACHE_SECONDS = 120


def tts_library_installed():
    return importlib.util.find_spec("pyttsx3") is not None


def _run_worker(args, timeout):
    """Run tts_worker.py in a new process and return its JSON reply."""
    command = [sys.executable, "-m", "services.tts_worker", *args]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # hide console window on Windows
    try:
        completed = subprocess.run(
            command, cwd=str(config.BASE_DIR), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, creationflags=flags,
        )
    except subprocess.TimeoutExpired as exc:
        raise TTSTimeoutError(f"worker exceeded {timeout} seconds") from exc
    except OSError as exc:
        raise TTSFailedError(str(exc)) from exc

    lines = [line for line in (completed.stdout or "").splitlines() if line.strip().startswith("{")]
    try:
        reply = json.loads(lines[-1]) if lines else {}
    except ValueError:
        reply = {}
    if completed.returncode == 2:
        raise TTSUnavailableError(reply.get("error", "pyttsx3 missing"))
    if completed.returncode != 0 or not reply.get("ok"):
        detail = reply.get("error") or (completed.stderr or "").strip()[-300:] or "unknown error"
        raise TTSFailedError(detail)
    return reply


def list_voices(force=False):
    """Installed voices as [{id, name, lang, indian_english}]. Cached for 2 minutes."""
    if not tts_library_installed():
        raise TTSUnavailableError("pyttsx3 missing")
    now = time.time()
    if force or _voice_cache["voices"] is None or now - _voice_cache["time"] > VOICE_CACHE_SECONDS:
        _voice_cache["voices"] = _run_worker(["voices"], timeout=30).get("voices", [])
        _voice_cache["time"] = now
    return _voice_cache["voices"]


def supported_languages(voices):
    """Which of our form languages can actually be spoken with the installed voices."""
    langs = {v["lang"] for v in voices}
    result = {}
    for code, info in config.LANGUAGES.items():
        if info["needs_voice"] == "hindi":
            result[code] = "hi" in langs
        else:  # English and Hinglish are read by an English voice
            result[code] = "en" in langs or bool(voices)
    return result


def choose_voice(language, voices, preferred_id=None):
    """Pick the best voice for a language. Raises TTSVoiceMissingError if none fits."""
    if preferred_id:
        for voice in voices:
            if voice["id"] == preferred_id:
                return voice
    if language == "hi":
        hindi = [v for v in voices if v["lang"] == "hi"]
        if not hindi:
            raise TTSVoiceMissingError(
                "No Hindi voice is installed. Choose Hinglish instead, or install a Hindi "
                "speech voice in Windows Settings > Time & language > Speech.")
        return hindi[0]
    english = [v for v in voices if v["lang"] == "en"]
    if language == "hinglish":
        # An Indian-English voice pronounces Hinglish words more naturally.
        indian = [v for v in english if v.get("indian_english")]
        if indian:
            return indian[0]
    if english:
        # Prefer common US/UK/Indian English voices over rare regional ones.
        for marker in ("en-us", "united states", "america", "en-in", "india", "en-gb"):
            for voice in english:
                if marker in f"{voice['id']} {voice['name']}".lower():
                    return voice
        return english[0]
    if voices:
        return voices[0]
    raise TTSVoiceMissingError("No speech voices are installed on this computer.")


def wav_duration_seconds(path):
    """Length of a WAV file in seconds, or None if it cannot be read."""
    try:
        with wave.open(str(path), "rb") as audio:
            frames, rate = audio.getnframes(), audio.getframerate()
            return round(frames / float(rate), 2) if rate else None
    except (wave.Error, EOFError, OSError):
        return None


def cleanup_old_audio(max_age_hours=24):
    """Delete speech files older than a day so the output folder stays small."""
    limit = time.time() - max_age_hours * 3600
    for file in Path(config.AUDIO_DIR).glob("speech_*.wav"):
        try:
            if file.stat().st_mtime < limit:
                file.unlink()
        except OSError:
            pass


def synthesize(script, language, voice_id=None, rate=None):
    """Create a WAV file for the script. Returns details for the browser."""
    if not tts_library_installed():
        raise TTSUnavailableError("pyttsx3 missing")
    voice = choose_voice(language, list_voices(), voice_id)
    cleanup_old_audio()

    token = uuid.uuid4().hex[:12]
    text_file = Path(config.TMP_DIR) / f"script_{token}.txt"
    out_file = Path(config.AUDIO_DIR) / f"speech_{token}.wav"
    text_file.write_text(script, encoding="utf-8")
    try:
        _run_worker(
            ["speak", "--text-file", str(text_file), "--out", str(out_file),
             "--rate", str(rate or config.TTS_RATE), "--voice-id", voice["id"]],
            timeout=config.TTS_TIMEOUT_SECONDS,
        )
    finally:
        try:
            os.remove(text_file)
        except OSError:
            pass

    if not out_file.exists() or out_file.stat().st_size <= 44:  # 44 bytes = empty WAV header
        raise TTSFailedError("The audio file was not created or is empty.")
    return {
        "filename": out_file.name,
        "url": f"/media/audio/{out_file.name}",
        "duration": wav_duration_seconds(out_file),
        "voice_name": voice["name"],
        "voice_id": voice["id"],
    }
