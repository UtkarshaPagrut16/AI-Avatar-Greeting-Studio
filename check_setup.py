"""
check_setup.py - Friendly setup checker for AI Avatar Greeting Studio.

    python check_setup.py                 report only (changes nothing)
    python check_setup.py --interactive   report + ASK before starting Ollama
                                          or downloading the model

run_windows.bat calls this with --interactive. Nothing large is ever
downloaded without you typing Y first.
"""
import argparse
import ctypes
import importlib.util
import os
import platform
import shutil
import subprocess
import sys
import time

import config

MODEL_DOWNLOAD = "about 1 GB (986 MB)"
MODEL_DISK = "about 1.1 GB of free disk space"
MODEL_RAM = "8 GB RAM recommended (works with about 2 GB of RAM free); no graphics card needed"

OK, WARN, FAIL = "[ OK ]", "[WARN]", "[FAIL]"


def say(tag, text):
    print(f"  {tag} {text}")


def ask_yes_no(question, default_no=True):
    hint = "[y/N]" if default_no else "[Y/n]"
    try:
        answer = input(f"\n  {question} {hint}: ").strip().lower()
    except EOFError:
        return False
    if not answer:
        return not default_no
    return answer.startswith("y")


def total_ram_gb():
    """Total RAM in GB (Windows or Linux), or None if unknown."""
    try:
        if os.name == "nt":
            class MemoryStatus(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(MemoryStatus)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return round(status.ullTotalPhys / 1024 ** 3, 1)
        with open("/proc/meminfo", encoding="utf-8") as handle:
            kb = int(handle.readline().split()[1])
            return round(kb / 1024 ** 2, 1)
    except (OSError, ValueError, AttributeError):
        return None


def find_ollama():
    """Path to ollama.exe, also checking the default per-user install folder."""
    found = shutil.which("ollama")
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA")
    if local:
        candidate = os.path.join(local, "Programs", "Ollama", "ollama.exe")
        if os.path.exists(candidate):
            return candidate
    return None


def check_python():
    print("\n1) Python")
    version = sys.version_info
    text = f"Python {version.major}.{version.minor}.{version.micro} ({platform.system()})"
    if version < (3, 9):
        say(FAIL, text + " - please install Python 3.11 or 3.12 from python.org")
        return False
    say(OK, text)
    ram = total_ram_gb()
    if ram:
        say(OK if ram >= 6 else WARN, f"Computer RAM: {ram} GB" + ("" if ram >= 6 else " (the LLM may be slow)"))
    return True


def check_packages():
    print("\n2) Python packages")
    good = True
    for module, pip_name in (("flask", "Flask"), ("requests", "requests"), ("pyttsx3", "pyttsx3")):
        if importlib.util.find_spec(module):
            say(OK, pip_name)
        else:
            say(FAIL, f"{pip_name} missing - run: pip install -r requirements.txt")
            good = False
    return good


def check_llm(interactive):
    from services.llm_service import OllamaClient

    print(f"\n3) Local LLM (Ollama + model {config.OLLAMA_MODEL})")
    client = OllamaClient()
    status = client.status()
    exe = find_ollama()

    if not status["runner"] and exe:
        say(WARN, "Ollama is installed but not running.")
        if interactive and ask_yes_no("Start Ollama in the background now?", default_no=False):
            flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            subprocess.Popen([exe, "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=flags)
            for _ in range(15):
                time.sleep(1)
                status = client.status()
                if status["runner"]:
                    break

    if not status["runner"]:
        if exe:
            say(WARN, "Ollama is installed but not responding at " + config.OLLAMA_URL)
            say("    ", "Open 'Ollama' from the Start menu (it runs in the system tray), then run again.")
        else:
            say(WARN, "Ollama is not installed.")
            say("    ", "Install it free from https://ollama.com/download  (no account needed),")
            say("    ", "or in PowerShell:  winget install Ollama.Ollama")
        say(WARN, "Until then the app uses the clearly-labelled TEMPLATE fallback (not AI).")
        return False

    say(OK, f"Ollama is running at {config.OLLAMA_URL}")
    if status["model_ready"]:
        say(OK, f"Model {config.OLLAMA_MODEL} is downloaded and ready.")
        return True

    say(WARN, f"Model {config.OLLAMA_MODEL} is not downloaded yet.")
    print(f"        Download size : {MODEL_DOWNLOAD}")
    print(f"        Disk needed   : {MODEL_DISK}")
    print(f"        Hardware      : {MODEL_RAM}")
    print("        License       : Apache License 2.0 (Qwen2.5-1.5B by Alibaba Cloud)")
    if interactive and exe and ask_yes_no(f"Download {config.OLLAMA_MODEL} now (internet needed)?"):
        print()
        result = subprocess.run([exe, "pull", config.OLLAMA_MODEL])
        if result.returncode == 0 and client.status()["model_ready"]:
            say(OK, "Model downloaded successfully.")
            return True
        say(WARN, "Download did not finish. Check your internet and try:  ollama pull " + config.OLLAMA_MODEL)
    else:
        say("    ", f"To download later, run:  ollama pull {config.OLLAMA_MODEL}")
    say(WARN, "Until the model is ready the app uses the clearly-labelled TEMPLATE fallback.")
    return False


def check_tts():
    from services import tts_service

    print("\n4) Offline text-to-speech (pyttsx3)")
    if not tts_service.tts_library_installed():
        say(FAIL, "pyttsx3 is not installed - run: pip install -r requirements.txt")
        return False
    try:
        voices = tts_service.list_voices(force=True)
    except tts_service.TTSError as exc:
        say(FAIL, f"Speech engine problem: {exc.detail or exc.user_message}")
        return False
    english = [v["name"] for v in voices if v["lang"] == "en"]
    hindi = [v["name"] for v in voices if v["lang"] == "hi"]
    say(OK if english else WARN, f"English voices: {', '.join(english[:4]) or 'none found'}")
    if hindi:
        say(OK, f"Hindi voices: {', '.join(hindi[:3])}")
    else:
        say(WARN, "No Hindi voice found - Hindi (Devanagari) speech is disabled; English and Hinglish work.")
    return bool(voices)


def check_ffmpeg():
    print("\n5) FFmpeg (OPTIONAL - only for MP4 copies)")
    if shutil.which("ffmpeg"):
        say(OK, "FFmpeg found - the gallery can make MP4 copies.")
    else:
        say(WARN, "FFmpeg not found - that is fine, videos are saved as WebM.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--interactive", action="store_true", help="ask before starting Ollama or downloading")
    args = parser.parse_args()

    print("=" * 64)
    print("  AI Avatar Greeting Studio - setup check")
    print("=" * 64)
    python_ok = check_python()
    packages_ok = check_packages()
    if packages_ok:
        check_llm(args.interactive)
        check_tts()
    check_ffmpeg()
    print("\n" + "=" * 64)
    if not (python_ok and packages_ok):
        print("  Some REQUIRED items are missing. Fix the [FAIL] lines above.")
        print("=" * 64)
        return 1
    print("  Required items are OK. [WARN] lines are optional or have a fallback.")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
