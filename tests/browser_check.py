"""
browser_check.py - OPTIONAL automated end-to-end check in a real browser.

It drives Chromium through the whole workflow (form -> script -> edit ->
voice -> record -> download) and then checks the downloaded WebM file.
It is NOT part of the normal `pytest` run because it needs extra tools.

One-time setup (about 150 MB download for Chromium):
    pip install playwright
    python -m playwright install chromium

Usage (start the app first with run_windows.bat or `python app.py`):
    python tests/browser_check.py
    python tests/browser_check.py --headed        # watch it happen
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

URL = "http://127.0.0.1:5000"
OUT_DIR = Path(__file__).resolve().parent.parent / "output" / "browser_check"
results = []


def check(name, condition, detail=""):
    results.append((name, bool(condition)))
    print(f"  [{'PASS' if condition else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))
    return bool(condition)


def probe(path):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    out = subprocess.run([ffprobe, "-v", "error", "-show_entries", "stream=codec_type,codec_name:format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True)
    return json.loads(out.stdout or "{}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=URL)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--screenshots", default="", help="folder to save screenshots in")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Run: pip install playwright && python -m playwright install chromium")
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    shots = Path(args.screenshots) if args.screenshots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headed,
                                     args=["--autoplay-policy=no-user-gesture-required"])
        page = browser.new_page(viewport={"width": 1366, "height": 900}, accept_downloads=True)
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))

        print("\n1) Load page")
        page.goto(args.url)
        page.wait_for_function("document.querySelector('#chipLlm').textContent.indexOf('checking') === -1", timeout=30000)
        check("home page loads", page.title() == "AI Avatar Greeting Studio")
        print("     status:", page.inner_text("#chipLlm"), "|", page.inner_text("#chipVoice"))

        print("\n2) Validation")
        page.click("#generateBtn")
        check("empty form shows an error", "required" in page.inner_text("[data-for=recipient]").lower())

        print("\n3) Generate script")
        page.fill("input[name=recipient]", "Priya")
        page.fill("input[name=sender]", "Rahul")
        page.select_option("#occasionSelect", "Birthday")
        page.check("input[name=tone][value=Friendly]", force=True)
        page.fill("textarea[name=message]", "Can't wait for our Goa trip!")
        if shots:
            page.screenshot(path=str(shots / "01_form.png"), full_page=False)
        page.click("#generateBtn")
        page.wait_for_function("document.querySelector('#scriptBox').value.length > 10", timeout=180000)
        script = page.input_value("#scriptBox")
        badge = page.inner_text("#sourceBadge")
        check("script mentions recipient", "Priya" in script, script[:70] + "...")
        check("generator is clearly labelled", "AI-generated" in badge or "Template" in badge, badge)

        print("\n4) Edit script")
        page.fill("#scriptBox", script + " See you soon!")
        page.dispatch_event("#scriptBox", "input")
        check("edit is detected", page.is_visible("#editedFlag"))

        print("\n5) Create voice")
        page.click("#voiceBtn")
        page.wait_for_function("!document.querySelector('#playBtn').disabled", timeout=120000)
        info = page.inner_text("#voiceInfo")
        check("voice created", "Voice:" in info, info)
        duration = page.evaluate("window.greetingStudio.voice.duration")
        check("audio has a duration", duration > 1, f"{duration:.1f} s")

        print("\n6) Preview playback animates the mouth")
        page.click("#playBtn")
        page.wait_for_timeout(1500)
        speaking = page.evaluate("window.greetingStudio.avatar.speaking")
        max_mouth = page.evaluate("""() => new Promise(r => { let m = 0; const t = setInterval(() =>
            { m = Math.max(m, window.greetingStudio.avatar.mouthOpen); }, 30); setTimeout(() => { clearInterval(t); r(m); }, 1200); })""")
        check("avatar is speaking during playback", speaking)
        check("mouth opens with the audio", max_mouth > 0.1, f"max openness {max_mouth:.2f}")
        if shots:
            page.screenshot(path=str(shots / "02_speaking.png"))
        page.click("#stopBtn")

        print("\n7) Record video")
        check("record disabled before consent", page.is_disabled("#recordBtn"))
        page.check("#consentBox")
        page.click("#recordBtn")
        page.wait_for_selector("#resultBox:not(.hidden)", timeout=int((duration + 40) * 1000))
        status = page.inner_text("#recordStatus")
        check("success shown only after finishing", "finished successfully" in status, status)
        page.wait_for_function("document.querySelector('#resultInfo').textContent.indexOf('gallery') !== -1", timeout=30000)
        if shots:
            page.screenshot(path=str(shots / "03_result.png"), full_page=True)

        print("\n8) Download and inspect the file")
        with page.expect_download() as download_info:
            page.click("#downloadLink")
        target = OUT_DIR / download_info.value.suggested_filename
        download_info.value.save_as(str(target))
        size = target.stat().st_size
        check("downloaded .webm exists", target.suffix == ".webm" and size > 10000, f"{target.name}, {size // 1024} KB")
        with open(target, "rb") as handle:
            check("file is real WebM", handle.read(4) == b"\x1a\x45\xdf\xa3")
        info = probe(target)
        if info is None:
            print("  [SKIP] ffprobe not installed - cannot list tracks")
        else:
            types = [s["codec_type"] for s in info.get("streams", [])]
            codecs = [s.get("codec_name") for s in info.get("streams", [])]
            check("WebM has a video track", "video" in types, str(codecs))
            check("WebM has an audio track", "audio" in types, str(codecs))

        print("\n9) Gallery")
        page.wait_for_selector(".gallery-item", timeout=10000)
        check("video listed in gallery", page.locator(".gallery-item").count() >= 1)

        print("\n10) Recording failure handling (MediaRecorder missing)")
        page2 = browser.new_page()
        page2.add_init_script("delete window.MediaRecorder;")
        page2.goto(args.url)
        reason = page2.evaluate("GreetingRecorder.checkSupport(document.querySelector('#avatarCanvas')).reason")
        check("unsupported browser gives a clear message", "MediaRecorder" in reason, reason)
        page2.close()

        check("no JavaScript errors on the page", not errors, "; ".join(errors[:3]))
        browser.close()

    failed = [name for name, ok in results if not ok]
    print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
