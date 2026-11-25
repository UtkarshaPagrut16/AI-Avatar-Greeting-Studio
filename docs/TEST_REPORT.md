# Test Report — what was tested, results, and what is NOT verified

Build and verification environment: **Linux** cloud workspace (Python 3.13, headless Chromium via
Playwright, espeak-ng speech engine, FFmpeg 6). **Not** Windows 11. Date: 19 October 2026.
The internet access in that environment blocked `ollama.com` and the Ollama model registry, so
**the real Ollama program and the real `qwen2.5:1.5b` model could not be installed or run there.**

## 1. Automated unit/integration tests (`python -m pytest`)
**Result: 166 passed, 0 failed** (about 1 second), run both in the development folder and again in
a clean folder extracted from the final ZIP with a fresh virtual environment.

| Area (file) | What is checked |
|---|---|
| App startup, home page, static files (`test_app.py`) | `create_app()`, `/` renders all occasions, canvas and record button; all JS/CSS/SVG served |
| Form validation | missing names, invalid characters, too long, bad occasion/tone/language/length, Custom without name, long message, offensive words, non-JSON body; Hindi names accepted |
| Script generation | LLM success labelled `llm`; prompt contains every field and changes with tone/language/occasion/length; output cleaning; length limit; name insertion |
| LLM service (`test_llm_service.py`) | success request format; Ollama not running; timeout; model missing (404); server error; empty / invalid JSON answer; status reporting |
| Fallback | used for unavailable/timeout/empty/missing-model/too-short; labelled `template` with "NOT written by an AI model"; disabled fallback → HTTP 503; a template exists for every occasion × tone × language (84 combinations) |
| TTS (`test_tts_service.py`) | pyttsx3 missing; worker exit codes; engine error message hidden from user; timeout; empty WAV; voice choice (English, Hinglish → Indian English, Hindi, missing Hindi voice → clear message); WAV duration |
| Videos / download | upload, list, download with `attachment` header, delete; empty/non-WebM uploads rejected; missing file; path traversal blocked; MP4 without FFmpeg gives a clear message |
| Error handling | unknown API route → JSON 404; unexpected exception → generic message with no stack trace |

Mocks are used for Ollama and the speech engine, so these tests need no model and no audio device.

## 2. End-to-end browser check (`tests/browser_check.py`, headless Chromium)
Run against the running app. **Result: 18 passed, 0 failed**, in two configurations:

| Configuration | Script source | Result |
|---|---|---|
| A. A small **simulated** Ollama-compatible server (test helper, *not* an LLM — it returned a fixed greeting built from the names) | labelled "AI-generated" by the app | 18/18 passed |
| B. Ollama absent (real situation in the build environment) | **template fallback**, labelled "NOT AI" | 18/18 passed (this run produced the screenshots in `docs/screenshots/`) |

Configuration A proves the app's HTTP integration with the Ollama `/api/tags` and `/api/chat`
formats and the cleaning of a reply containing "Here is your greeting:" and quotes. It does **not**
prove the quality of real `qwen2.5:1.5b` output.

Checks performed in each run: page loads; empty-form validation; script contains the recipient;
source badge present; edit detected; voice created (real WAV via pyttsx3/espeak-ng, 16–19 s);
avatar enters speaking state and the mouth opens with the audio (max openness ≈ 0.94); record
button disabled before consent; success message only after recording finished; download produced a
`.webm` file starting with the WebM signature; **ffprobe found a VP9 video track and an Opus audio
track**; the video appears in the gallery; a browser without MediaRecorder gets a clear message; no
JavaScript errors.

Additional manual measurements on a downloaded file: 960×540 VP9 + Opus 48 kHz stereo, ~18.7 s,
decodes without errors, **audio mean volume −22 dB, max −1.5 dB** (real speech, not silence).
MP4 conversion through the gallery API produced H.264 + AAC, 18.76 s.

## 3. Other verifications
* `check_setup.py` ran and correctly reported Python, RAM, packages, missing Ollama (as a warning
  with install instructions), voices and FFmpeg.
* All 7 Mermaid diagrams in `FLOWCHARTS.md` were parsed and rendered with mermaid.js 11 without errors.
* ZIP: created, `unzip -t` integrity test passed, extracted into an empty folder, structure
  inspected, fresh venv + `pip install -r requirements.txt` + pytest passed, app started from the
  extracted copy and the browser check passed (fallback mode).
* File names and commands referenced in README and SETUP_AND_RUN were cross-checked against the
  extracted files.

## 4. NOT verified — please test these yourself on Windows 11
| Item | Why not verified | How to verify |
|---|---|---|
| Real Ollama + real `qwen2.5:1.5b` generation, quality, speed | Ollama download blocked in build environment | `ollama run qwen2.5:1.5b "Say hi to Priya"`, then generate in the app; badge must say "AI-generated · qwen2.5:1.5b" |
| `run_windows.bat` | No Windows machine | Double-click it; every step should print `[ OK ]`/`[WARN]`; app opens in the browser |
| pyttsx3 with **Windows SAPI5** (Zira/David) | Tested only with Linux espeak-ng | `python -m services.tts_worker voices`; Create voice in the app |
| Hindi SAPI5 voice detection | No Windows voices available | Check the status chip tooltip / `check_setup.py` |
| Recording in **Windows** Chrome/Edge with speakers | Tested in Linux headless Chromium | Record, download, play in Chrome/VLC — hear the voice and see the animation |
| `check_setup.py` Ollama start / model pull prompts | Ollama unavailable | Run with Ollama installed but stopped, and with the model missing |
| `GlobalMemoryStatusEx` RAM reading on Windows | Linux | `python check_setup.py` shows "Computer RAM: … GB" |

### Manual verification checklist (Windows)
1. `run_windows.bat` → all required items OK.
2. Status chips: "LLM ready: qwen2.5:1.5b", "Voices: N".
3. Generate for Priya/Rahul/Birthday/Friendly → AI badge, Priya's name appears.
4. Edit → "Edited by you". Regenerate → different wording.
5. Create voice → voice name and duration shown → Play → sound + moving mouth.
6. Tick consent → Record → progress → "Recording finished successfully".
7. Download → play the file in Chrome or VLC: **both animation and voice present**.
8. Quit Ollama → Generate → amber "Template fallback – NOT AI" with the reason.
9. `run_tests.bat` → 166 passed.
