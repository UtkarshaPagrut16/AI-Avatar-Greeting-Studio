# Complete Project Study Guide

This guide teaches the **whole project** from zero: every important file, every technology,
the complete data flow, how to modify things safely, and the concepts behind them. Read it with
the code open beside you — function names here match the real code.

**Suggested study plan (about 6–8 hours in total):**
| Day | Read | Do |
|---|---|---|
| 1 | Part E (concepts 1–6), Part A: `config.py`, `app.py` | Run the app, open `/api/status` in the browser |
| 2 | Part A: `services/*`, Part B (backend tech) | Change a tone description, regenerate |
| 3 | Part A: `static/js/*`, Part B (browser APIs) | Change avatar colours, record a video |
| 4 | Part C (full flow), Part D | Run the tests, break one on purpose, fix it |
| 5 | `JURY_PREPARATION.md` | Practise the 2-minute explanation aloud |

---

# Part A — File-by-file explanation

### Legend
**Essential** = the app breaks without it. **Optional** = nice to have.

---

### `config.py` — Essential
**What / why:** One place for every setting: folders, server address, model name, timeouts,
temperature, form options. Keeps "magic numbers" out of the code.
**Used by:** every backend module and the HTML template (via `app.py`).
**Important items:** `OLLAMA_MODEL = "qwen2.5:1.5b"`, `LLM_TIMEOUT_SECONDS = 120`,
`LLM_TEMPERATURE = 0.8`, `ALLOW_TEMPLATE_FALLBACK`, `OCCASIONS`, `TONES`,
`LENGTHS = {"Short": (40, 65), "Medium": (70, 100)}`, `LANGUAGES` (with `needs_voice`).
Each value reads an environment variable first: `os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")`.
**Talks to:** imported with `import config`. It also creates `output/audio`, `output/videos`,
`output/tmp` when imported.
**Modify safely:** change defaults here or set environment variables. If you add an occasion or
tone here you must also add guidance/templates (see Part D).

---

### `app.py` — Essential (the web server)
**What / why:** Creates the Flask app, defines all URLs ("routes"), and converts errors into
friendly JSON.
**Important functions/routes:**
| Function | Route | Job |
|---|---|---|
| `index` | `GET /` | renders the page with option lists |
| `status` | `GET /api/status` | Ollama/model/voices/FFmpeg status |
| `api_generate_script` | `POST /api/generate-script` | validate → `generate_script` |
| `api_tts` | `POST /api/tts` | validate script → `tts_service.synthesize` |
| `api_list_videos` / `api_upload_video` / `api_delete_video` / `api_convert_mp4` | `/api/videos…` | gallery |
| `media_audio` / `media_video` | `/media/...` | serve files safely |
| `too_large`, `http_error`, `unexpected_error` | – | error handlers |

`create_app()` is an *application factory*: a function that builds a fresh app — handy for tests.
`error_response()` makes every error look like `{"ok": false, "error": "..."}`.
**Talks to:** `services/*` (Python imports), the browser (HTTP JSON).
**Modify safely:** add a new route inside `create_app()` with `@app.get(...)`/`@app.post(...)`;
always return JSON from `/api/` routes; never set `debug=True` for the jury (it shows code on errors).

---

### `services/validators.py` — Essential
**What / why:** Server-side input checking. The browser checks too, but a server must never trust
the browser (anyone can send requests with tools like curl).
**Important:** `validate_greeting_request(data)` returns a cleaned dict or raises
`ValidationError` whose `.errors` maps field → message (shown under the right input box).
`is_valid_name` uses `unicodedata.category` so Hindi names like "प्रिया" (letters + vowel signs) are
allowed while digits, `<`, `>` are rejected. `validate_script_text` checks the edited script.
`_BLOCKED_WORDS` is a short list of offensive words.
**Modify safely:** change `NAME_MAX`, `MESSAGE_MAX`; add words to `_BLOCKED_WORDS` (lowercase).

---

### `services/llm_service.py` — Essential for AI
**What / why:** The only file that talks to Ollama. Keeping it separate means you could switch to a
different local runner by changing just this file.
**Important:** class `OllamaClient` with `list_models()` (`GET /api/tags`), `has_model()`,
`status()` (never raises), `chat(system_prompt, user_prompt)` (`POST /api/chat`).
Error classes: `LLMUnavailableError`, `LLMModelMissingError`, `LLMTimeoutError`,
`LLMEmptyResponseError` (all subclasses of `LLMError`, each with a readable `.reason`).
**Request it sends:**
```python
{"model": "qwen2.5:1.5b", "stream": False, "keep_alive": "10m",
 "messages": [{"role": "system", "content": SYSTEM_PROMPT},
              {"role": "user", "content": user_prompt}],
 "options": {"temperature": 0.8, "num_predict": 260, "top_p": 0.9}}
```
**Modify safely:** change model via `config.OLLAMA_MODEL`; keep the error mapping so fallback works.

---

### `services/script_generator.py` — Essential for AI (prompt engineering lives here)
**What / why:** Decides *what to ask* the LLM and *how to clean* its answer, and decides when to
fall back.
**Important:** `SYSTEM_PROMPT`, `TONE_GUIDE`, `OCCASION_GUIDE`, `LANGUAGE_GUIDE`,
`build_prompts(details)`, `clean_llm_output(text)`, `enforce_length(text, max_words)`,
`ensure_personalised(text, details)`, `generate_script(details, client, allow_fallback)`.
**How it communicates:** called by `app.py`; calls `OllamaClient.chat` and, on `LLMError`,
`generate_template_greeting`.
**Modify safely:** edit the guide dictionaries in plain English; run the tests afterwards.

---

### `services/template_generator.py` — Essential for the fallback (NOT AI)
**What / why:** Backup greetings so the project can be demonstrated without the model.
**Important:** `ENGLISH[occasion][tone]` (list of sentences with `{r}`, `{s}`, `{e}`),
`HINGLISH`, `HINDI`, `MESSAGE_LEAD`, `default_event_name`, `generate_template_greeting`.
**Modify safely:** add more sentences to any list (keep the placeholders exactly `{r}`, `{s}`, `{e}`).
`test_template_exists_for_every_combination` will catch missing combinations.

---

### `services/tts_service.py` + `services/tts_worker.py` — Essential for voice
**What / why:** Turn text into a `.wav`. The *service* (inside Flask) chooses the voice and
manages files/timeouts; the *worker* (separate process) actually runs pyttsx3.
**Important:** `synthesize(script, language)` → `{url, duration, voice_name, …}`;
`choose_voice`, `list_voices` (cached 2 min), `supported_languages`, `wav_duration_seconds`,
`cleanup_old_audio` (removes files older than 24 h); error classes `TTSUnavailableError`,
`TTSVoiceMissingError`, `TTSTimeoutError`, `TTSFailedError`. In the worker: `describe_language`,
`is_indian_english`, `main` (sub-commands `voices` and `speak`), `emit` (prints one JSON line).
**Communication:** the service starts `python -m services.tts_worker speak --text-file … --out …`
with `subprocess.run`, then reads the JSON line from its output.
**Modify safely:** speech speed → `config.TTS_RATE`; voice preference → `choose_voice`.

---

### `services/video_store.py` — Essential for the gallery (FFmpeg parts optional)
**What / why:** Save the browser's recording, list, delete, and optionally convert/inspect videos.
**Important:** `save_uploaded_video` (checks size and the WebM signature `1A 45 DF A3`),
`list_videos`, `delete_video`, `is_safe_name` / `safe_path` (security), `inspect_streams`
(ffprobe), `convert_to_mp4` (FFmpeg).
**Modify safely:** keep `SAFE_NAME_RE` strict — it is what stops path-traversal attacks.

---

### `check_setup.py` — Optional but very helpful
Prints a checklist (Python, RAM, packages, Ollama, model, voices, FFmpeg). With `--interactive`
it can start Ollama and **asks before** downloading the model. Called by `run_windows.bat`.

### `run_windows.bat` / `run_tests.bat` — Optional convenience
Windows batch scripts: find Python → create `.venv` → `pip install` → `check_setup.py` → `app.py --open`.
`run_tests.bat` runs `pytest -v` with the project's `.venv`.

### `requirements.txt`, `pytest.ini`, `.gitignore` — Essential config
Package list with version ranges; test folder setting; files Git should ignore (`.venv`, `output`).

---

### `templates/index.html` — Essential
The page skeleton: header with status chips, stepper, form card, script card, studio card
(canvas, controls, customisation, consent, record button, result box), gallery, ethics panel,
toast area, the hidden `<audio id="voiceAudio">`, and the four script tags.
Jinja2 loops (`{% for occasion in occasions %}`) create the options from `config.py`, so the
form and the server always agree.

### `static/css/style.css` — Essential for looks
CSS variables in `:root` (`--purple`, `--blue`, `--radius`, `--shadow`) control the theme. Notable
classes: `.card`, `.btn-primary`, `.pill`, `.badge-ai`, `.badge-template`, `.progress`, `.toast`.
A media query switches to one column under 980 px.

### `static/js/avatar.js` — Essential (avatar)
Class `AvatarRenderer`. See Part B (Canvas) and Part C step 7. Data objects at the top
(`AVATAR_THEMES`, `EXPRESSIONS`, `TONE_EXPRESSION`, `AVATAR_LOOKS`) are the easiest things to modify.

### `static/js/voice.js` — Essential (audio + lip movement + recordable sound)
Class `VoicePlayer`: `ensureGraph`, `load`, `play`, `pause`, `stop`, `replay`, `level`, `recordingTrack`.

### `static/js/recorder.js` — Essential (video)
Class `GreetingRecorder`: `checkSupport`, `pickMimeType`, `record`, `cancel`; class `RecorderError`.

### `static/js/app.js` — Essential (glue)
Connects buttons to functions and functions to the API. Main functions: `generateScript`,
`createVoice`, `recordVideo`, `saveToGallery`, `loadStatus`, `onScriptChanged`.

### `static/img/logo.svg` — Optional
Original vector logo (made for this project), also used as the browser tab icon.

### `tests/` — Essential for quality
`conftest.py` (shared fixtures, temporary folders, `FakeLLM`, `make_wav`), four `test_*.py` files
(166 tests), `browser_check.py` (optional real-browser end-to-end check).

### `output/` — Created automatically
`audio/` (speech `.wav`, auto-cleaned after 24 h), `videos/` (gallery `.webm`, `.mp4`, `.json`),
`tmp/`. Safe to delete when the app is stopped.

---

# Part B — Technology stack (what, why, how, pros/cons, if removed)

### Python
1. **What:** a popular, readable programming language.
2. **Why:** beginner-friendly; excellent libraries (Flask, requests, pyttsx3).
3. **How used:** the whole backend.
4. **+** simple syntax, huge ecosystem. **−** slower than compiled languages (irrelevant here).
5. **If removed:** the backend would need rewriting (e.g. Node.js + Express).

### Flask
1. A *micro web framework*: maps URLs to Python functions.
2. Tiny, easy to explain, no project boilerplate.
3. `create_app()` routes; `jsonify`, `render_template`, `send_from_directory`, error handlers.
4. **+** minimal, flexible. **−** built-in server is for development/local use only (fine here).
5. Could be replaced by FastAPI or Django; the JS front end would stay the same.

### HTTP / REST and JSON
1. HTTP is how browsers talk to servers; REST style = resources at URLs with verbs (GET, POST, DELETE).
2. Standard, testable, and the same way Ollama's API works.
3. `fetch("/api/generate-script", {method: "POST", body: JSON.stringify(data)})`.
4. **+** universal, debuggable in browser DevTools. **−** request/response only (no live streaming here).
5. Without it the browser and Python could not communicate.

### HTML, CSS, JavaScript
1. Structure, styling and behaviour of web pages.
2. Run in every browser; no installation for the user.
3. One HTML page; one CSS file; four JS files, no frameworks.
4. **+** lightweight, offline. **−** more manual DOM code than React (but easier to explain).
5. A desktop GUI (Tkinter) could replace it, but recording would become much harder.

### Ollama (local LLM runner)
1. Free program that downloads and runs LLMs locally, with an HTTP API on port 11434.
2. One-click Windows installer, no account, CPU support, handles quantised models.
3. `llm_service.OllamaClient` calls `/api/tags` and `/api/chat`.
4. **+** private, offline, free. **−** uses RAM/disk; slower than cloud GPUs.
5. Could be replaced by llama.cpp server or LM Studio's local server (change `llm_service.py`).

### The model: `qwen2.5:1.5b`
1. Qwen2.5-1.5B-Instruct by Alibaba Cloud: 1.54 billion parameters, instruction-tuned, supports
   29+ languages, Apache-2.0 license. In Ollama it is quantised to 4-bit (Q4_K_M), 986 MB.
2. Small enough for an ordinary laptop CPU, good at short instructions, permissive license.
3. Writes the greeting from our prompts.
4. **+** free, private, multilingual. **−** small models can be generic, occasionally ignore a
   rule, and are weaker in Hindi than in English.
5. Swap with `set OLLAMA_MODEL=qwen2.5:3b` (better, slower; note: its license differs — check it)
   or `qwen2.5:0.5b` (faster, weaker). If no model: template fallback.

### Prompt engineering
1. Designing the instructions given to an LLM.
2. Small models need clear, explicit rules to stay on task.
3. System prompt (role + strict output rules) + user prompt (structured details + guides), plus
   post-processing (`clean_llm_output`) as a safety net.
4. **+** big quality gain with no training. **−** not guaranteed; the model may still deviate.
5. Without it: rambling answers, titles, emojis, explanations around the greeting.

### pyttsx3 + SAPI5 (text-to-speech)
1. Python library controlling the OS speech engine (SAPI5 on Windows, espeak on Linux, NSSpeech on macOS).
2. Offline, free, voices preinstalled on Windows.
3. `tts_worker.py`: `engine.setProperty("voice"/"rate")`, `save_to_file`, `runAndWait`.
4. **+** zero downloads, fast. **−** robotic sound, limited languages, voice availability varies.
5. Replacement: Piper (neural offline TTS) for natural voices — bigger setup.

### Canvas 2D API
1. A drawing surface in HTML; JavaScript draws shapes with `ctx.ellipse`, `bezierCurveTo`, `fillRect`.
2. Fast, no assets needed, and *recordable* with `captureStream`.
3. `AvatarRenderer.draw*` functions.
4. **+** full control, light. **−** everything is drawn by code (more code than an image).
5. SVG could be used for drawing but cannot be captured as a video stream directly.

### requestAnimationFrame
Browser function that calls our draw loop before every screen refresh (~60 fps). Pauses in hidden
tabs — which is why recording asks you to keep the tab visible.

### Web Audio API (AudioContext, AnalyserNode, MediaStreamAudioDestinationNode)
1. A browser audio-processing system built from connected "nodes".
2. Needed for (a) measuring loudness for the mouth and (b) creating a recordable audio track.
3. `VoicePlayer.ensureGraph()` and `level()`.
4. **+** precise, real-time. **−** browsers require a user click before audio can start.
5. Without it: no lip movement and **no sound in the recording**.

### MediaStream, captureStream and MediaRecorder
1. `MediaStream` = a bundle of audio/video tracks. `captureStream` turns a canvas into a video
   track. `MediaRecorder` encodes a stream into a file.
2. Built into Chrome/Edge/Firefox; no server-side video tools needed.
3. `GreetingRecorder.record()`.
4. **+** simple, real-time, free. **−** real-time only; WebM output; duration metadata missing.
5. Alternative: render frames and use FFmpeg on the server (much more complex).

### WebM (VP9/VP8 + Opus)
1. Open, royalty-free video container; VP9/VP8 video codecs, Opus audio codec.
2. The format MediaRecorder supports in Chrome/Edge.
3. Output file of the recorder; uploaded to the gallery.
4. **+** open, good compression. **−** some phones/old players prefer MP4 → optional FFmpeg conversion.

### FFmpeg / ffprobe (optional)
Free command-line tools. `convert_to_mp4` uses H.264 + AAC; `inspect_streams` confirms a file has
both video and audio tracks. Not needed for the core workflow.

### Local file storage
Files in `output/` instead of a database: simple, transparent, easy to delete. A database would be
overkill for a list of videos.

### pytest + mocks; Playwright (optional)
pytest runs test functions; *mocks/fakes* replace Ollama and the speech engine, so tests are fast
and need no downloads. Playwright drives a real Chromium browser for the optional end-to-end check.

---

# Part C — Complete working methodology (step by step, with Priya)

**1. Page load.** Browser requests `GET /` → `index()` renders `index.html`. `app.js` runs:
creates `AvatarRenderer`, `VoicePlayer`, `GreetingRecorder`; `avatar.start()` begins the 60 fps loop;
`loadStatus()` calls `/api/status` and colours the chips; `loadGallery()` lists videos.

**2. User input.** Priya / Rahul / Birthday / Friendly / English / Short / "Can't wait for our Goa
trip!". Changing *Occasion* calls `updateOccasionField()` → `avatar.setTheme("Birthday")` (pink
gradient + confetti). Changing *Tone* calls `applyAutoExpression()` → *happy*.

**3. Generate.** `generateScript()` → `quickValidate` → `fetch POST /api/generate-script` with JSON.

**4. Server validation.** `api_generate_script` → `validate_greeting_request` → cleaned dict.

**5. Prompting and the LLM.** `generate_script(details)` → `build_prompts` → `OllamaClient().chat`
→ Ollama loads `qwen2.5:1.5b` (first time) and generates tokens → JSON reply
`{"message": {"content": "..."}}`.

**6. Cleaning and response.** `clean_llm_output` → length/name checks → JSON
`{"source": "llm", "model": "qwen2.5:1.5b", "script": "...", "notice": "..."}`. The browser shows the
script, the purple **AI-generated** badge, the notice and the word count; caption on the canvas
becomes "Happy Birthday / Priya / with love from Rahul".
*(If Ollama were off: `LLMUnavailableError` → `generate_template_greeting` → amber badge.)*

**7. Editing.** Typing in the editor fires `onScriptChanged()`: updates word count and ~seconds,
shows "Edited by you", and (if a voice existed) warns that the voice is outdated.

**8. Voice.** `createVoice()` → `voice.ensureGraph()` (inside the click, as browsers require) →
`POST /api/tts` → `synthesize()` → `choose_voice("en")` → Zira → `_run_worker(["speak", ...])` →
`speech_<id>.wav` → JSON with `url` and `duration` → `voice.load(url)`.

**9. Playback and lip movement.** ▶ Play → `voice.play()` → `<audio>` "play" event →
`avatar.setSpeaking(true)`. Every frame `avatar.update()` calls `levelSource()` = `voice.level()`
(RMS loudness) → mouth opening. Bars on the card follow too. "ended" → `setSpeaking(false)`, wave.

**10. Recording.** Tick consent → `setRecordEnabled()` enables the button → `recordVideo()` →
`recorder.record(onProgress)`: support check → audio track + canvas track → MediaRecorder start →
wave 0.9 s → voice plays (mouth moves) → "ended" → goodbye wave 1.3 s → `stop()` → chunks → Blob.

**11. Result and download.** `showResult()` creates an object URL, sets it on `<video>` and on the
download link (`greeting_priya_birthday_YYYYMMDD-HHMM.webm`). Success text appears now — not earlier.

**12. Gallery.** `saveToGallery()` → `POST /api/videos` (multipart) → `save_uploaded_video` checks
and stores the file → optional ffprobe → "✓ video + audio" tag → `loadGallery()`.

---

# Part D — Code understanding and modifications

### Change the LLM prompt
Edit `SYSTEM_PROMPT` or the guide dictionaries in `services/script_generator.py`. Example — make
Formal greetings mention "best regards":
```python
"Formal": "polite, respectful and professional; no slang and no jokes; end with 'Best regards'",
```
Restart the app (Ctrl+C, then start again) and regenerate. Run `python -m pytest`.

### Change templates / add an occasion (e.g. "Graduation")
1. `config.py`: add `"Graduation"` to `OCCASIONS`.
2. `script_generator.py`: add `"Graduation": "congratulate them on graduating"` to `OCCASION_GUIDE`.
3. `template_generator.py`: add `"Graduation": {"Friendly": [...], "Formal": [...], "Funny": [...],
   "Heartfelt": [...]}` to `ENGLISH`, and one line each to `HINGLISH` and `HINDI`.
4. `avatar.js`: add `Graduation: { bg: [...], accent: "...", particle: "confetti", headline: "Happy Graduation" }` to `AVATAR_THEMES`.
5. Run the tests — the template test now also checks Graduation.

### Add or modify tones
Add the tone to `config.TONES`, a description to `TONE_GUIDE`, templates for every occasion in
`ENGLISH`, an icon in `index.html` (`icons` dict), and an expression mapping in `TONE_EXPRESSION`.

### Add a language (example: Marathi)
1. `config.LANGUAGES["mr"] = {"label": "Marathi", "needs_voice": "marathi"}`.
2. `LANGUAGE_GUIDE["mr"] = "Write entirely in Marathi using Devanagari script."`
3. Templates in `template_generator.py` and `MESSAGE_LEAD["mr"]`.
4. `tts_worker.describe_language` and `tts_service.choose_voice`/`supported_languages` must
   recognise Marathi voices. Be honest: only enable it if a Marathi SAPI5 voice exists, and test
   the small model's Marathi quality.

### Change avatar colours, expressions, animations
* Palettes: `AVATAR_LOOKS` in `avatar.js` (hex colours; first is the default).
* Expressions: edit numbers in `EXPRESSIONS` (e.g. bigger `smile`), or add
  `sleepy: { browRaise: -4, browTilt: 0, smile: 0.4, eyeOpen: 0.45, eyeSize: 1, mouthO: 0 }` and a
  button `<button class="mini" data-expression="sleepy">Sleepy</button>` in `index.html`.
* Blink speed: the `140` (ms) and `2000 + Math.random() * 3000` in `update()`.
* Mouth sensitivity: `voice.js` `level()` constants `0.012` (noise floor) and `0.16` (scale).
* Waving length: `LEAD_IN_MS`, `TAIL_MS` in `recorder.js`.

### Modify interface styling
Change `:root` variables in `style.css` (e.g. `--purple: #0f9d8a;` for a teal theme). Keep
contrast readable.

### Adjust recording settings
In `recorder.js`: `FPS` (30), `videoBitsPerSecond` (3 Mbps), the MIME list in `pickMimeType`.
Resolution = canvas `width/height` in `index.html` (960×540); if you change it, also update
`this.W/this.H` positions in `avatar.js` drawing code.

### Diagnose problems
| Symptom | Where to look |
|---|---|
| Amber "Template fallback" badge | Status chip text; terminal; `ollama list`; `python check_setup.py` |
| Voice error | Terminal shows `TTS failed: ...`; run `python -m services.tts_worker voices` |
| Recording error | Browser DevTools (F12) → Console; message under the record button |
| Anything server-side | The black terminal window shows the full error (users only see a short message) |

### Add features without breaking things
1. Make one small change at a time. 2. Run `python -m pytest` after each change.
3. Add a test for the new behaviour (copy a similar test). 4. Keep API responses in the
`{"ok": ..., ...}` format. 5. Use browser DevTools (F12) → Network tab to see requests.

---

# Part E — Beginner-to-jury concepts (gradual)

**1. Client and server.** The browser (client) shows the page and sends requests; Flask (server)
answers. Both run on your laptop here — `127.0.0.1` means "this computer".

**2. API and JSON.** An API is a set of URLs a program can call. JSON is the text format for data:
`{"recipient": "Priya"}`. Our app has its own API (`/api/...`) and *uses* Ollama's API.

**3. What an LLM is.** A neural network trained on huge amounts of text to predict the next token.
"Instruction-tuned" models are further trained to follow instructions. Parameters (1.54 B) are the
learned numbers; more parameters usually means better quality but more RAM and slower speed.

**4. Tokens, temperature, max tokens.** Text is split into tokens (word pieces). Temperature
controls randomness (0 = always the most likely word; 0.8 = varied but sensible). `num_predict`
caps length.

**5. Quantisation.** Storing weights in 4 bits instead of 16 shrinks a ~3 GB model to under 1 GB
with a small quality loss — that is why it runs on ordinary laptops.

**6. Local vs cloud inference.** Local: private, free, offline, but limited by your hardware.
Cloud: powerful, but costs money, needs internet and sends data to a company.

**7. Prompt engineering.** System prompt = rules and role; user prompt = the specific task.
Clear, explicit, structured prompts make small models behave. Post-processing catches leftovers.

**8. Fallback and honesty.** Systems should degrade gracefully. Our fallback keeps the demo working
but is always labelled — calling template text "AI" would be misleading.

**9. Text-to-speech.** Text → normalisation (numbers, abbreviations) → phonemes → audio. SAPI5
desktop voices are classic (non-neural) synthesisers: clear but robotic.

**10. Audio as numbers.** A WAV file is a list of amplitude samples (e.g. 22,050 per second).
Loudness ≈ RMS (root mean square) of recent samples — that is what moves the mouth.

**11. Animation loop.** Redraw everything many times per second, changing values slightly each
time; easing (`value += (target − value) × factor`) makes motion smooth.

**12. Streams and tracks.** A stream bundles tracks (video, audio). Recording a stream with both
tracks gives a video with sound.

**13. Codecs and containers.** WebM is the container ("box"); VP9 (video) and Opus (audio) are the
codecs (compression methods) inside it. MP4 with H.264/AAC is another common combination.

**14. Validation and security.** Never trust input: validate on the server, whitelist file names,
limit sizes, hide internal errors, listen only on localhost.

**15. Testing with mocks.** Replace slow or external parts (Ollama, speech engine) with fakes that
behave predictably, so tests run in a second and can simulate failures like timeouts.

**16. Ethics of synthetic media.** Synthetic faces/voices can deceive. Good practice: use original
avatars, get consent before using a real person's likeness or voice, label content as
computer-generated, and keep personal data private. Local processing protects privacy but does
**not** replace consent.

### Cost, offline behaviour, privacy (summary)
* **Cost:** ₹0 — all software and the model are free to download and use.
* **Offline:** after installing Python packages, Ollama and the model, generation, speech,
  animation and recording work without internet. Internet is only for installing/downloading.
* **Privacy:** names and messages are processed only on your computer.

### Limitations and future improvements
See `PROJECT_OVERVIEW.md` sections 23–24. Be ready to say *why* each limitation exists (e.g.
phoneme lip-sync needs a phoneme aligner; better voices need neural TTS models).
