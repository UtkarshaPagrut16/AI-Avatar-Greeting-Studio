"""
tts_worker.py - Small helper program that does the actual speech synthesis.

tts_service.py starts this file as a SEPARATE Python process for every
request. Why? pyttsx3 talks to the Windows speech engine (SAPI5) through
COM, and running it repeatedly inside the Flask web server can freeze.
A fresh process each time is simple, reliable and can be given a timeout.

Usage (normally called automatically, but you can try it yourself):
    python -m services.tts_worker voices
    python -m services.tts_worker speak --text-file hello.txt --out hello.wav

The worker prints exactly one JSON line on stdout.
Exit codes: 0 = success, 2 = pyttsx3 not installed, 3 = speech engine error.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys


def describe_language(voice_id, name, languages):
    """Guess a simple language code ('en', 'hi' or 'other') for a voice."""
    langs = []
    for item in languages or []:
        if isinstance(item, bytes):  # some engines return bytes
            item = item.decode("utf-8", "ignore")
        langs.append(str(item).lower())
    text = f"{voice_id} {name} {' '.join(langs)}".lower()
    if "hindi" in text or "hi-in" in text or "hi_in" in text or any(l.startswith("hi") for l in langs):
        return "hi"
    if "english" in text or "en-" in text or "en_" in text or any(l.startswith("en") for l in langs):
        return "en"
    return "other"


def is_indian_english(voice_id, name):
    text = f"{voice_id} {name}".lower()
    return "india" in text or "en-in" in text or "en_in" in text


def linux_espeak_fallback(args):
    """Linux only: pyttsx3's espeak driver sometimes finishes without writing
    longer texts. In that case call the espeak-ng program directly.
    This is never used on Windows, where pyttsx3 uses SAPI5."""
    program = shutil.which("espeak-ng") or shutil.which("espeak")
    if not sys.platform.startswith("linux") or not program:
        return
    voice = args.voice_id.split("/")[-1] if args.voice_id else "en-us"
    subprocess.run([program, "-w", args.out, "-s", str(args.rate), "-v", voice, "-f", args.text_file],
                   check=True, timeout=60, capture_output=True)


def emit(payload, code=0):
    print(json.dumps(payload, ensure_ascii=True))
    sys.exit(code)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline speech helper for AI Avatar Greeting Studio")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("voices", help="list installed voices")
    speak = sub.add_parser("speak", help="save speech to a WAV file")
    speak.add_argument("--text-file", required=True)
    speak.add_argument("--out", required=True)
    speak.add_argument("--rate", type=int, default=165)
    speak.add_argument("--voice-id", default="")
    args = parser.parse_args(argv)

    try:
        import pyttsx3
    except ImportError:
        emit({"ok": False, "error": "pyttsx3 is not installed"}, 2)

    try:
        engine = pyttsx3.init()
        if args.command == "voices":
            voices = []
            for v in engine.getProperty("voices"):
                name = getattr(v, "name", "") or v.id
                voices.append({
                    "id": v.id,
                    "name": name,
                    "lang": describe_language(v.id, name, getattr(v, "languages", [])),
                    "indian_english": is_indian_english(v.id, name),
                })
            emit({"ok": True, "voices": voices})

        with open(args.text_file, encoding="utf-8") as handle:
            text = handle.read()
        if args.voice_id:
            engine.setProperty("voice", args.voice_id)
        engine.setProperty("rate", args.rate)
        engine.save_to_file(text, args.out)
        engine.runAndWait()
        if not os.path.exists(args.out) or os.path.getsize(args.out) <= 44:
            linux_espeak_fallback(args)
        emit({"ok": True, "out": args.out})
    except Exception as exc:  # report any engine problem as JSON
        emit({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, 3)


if __name__ == "__main__":
    main()
