# Technical Documentation

## 1. Components and dependencies
| Layer | Component | Version / detail |
|---|---|---|
| Runtime | Python | 3.9+ (3.11/3.12 recommended) |
| Web | Flask (+ Werkzeug, Jinja2) | `>=3.0,<4.0` |
| HTTP client | requests | `>=2.31,<3.0` |
| Speech | pyttsx3 (+ pywin32, comtypes on Windows) | `>=2.90,<3.0` |
| Tests | pytest | `>=8.0` |
| LLM runner | Ollama (separate program) | HTTP API on `127.0.0.1:11434` |
| Model | `qwen2.5:1.5b` | 1.54 B params, Q4_K_M, 986 MB, Apache-2.0 |
| Optional | FFmpeg / ffprobe | MP4 conversion, stream check |
| Browser APIs | Canvas 2D, `HTMLCanvasElement.captureStream`, Web Audio (`AudioContext`, `AnalyserNode`, `MediaStreamAudioDestinationNode`), `MediaStream`, `MediaRecorder`, `fetch`, `Blob`, `URL.createObjectURL` | Chrome/Edge recommended |

No database, no front-end framework, no CDN. Configuration lives in `config.py`
(each value can be overridden with an environment variable of the same name).

## 2. Configuration (`config.py`)
| Name | Default | Purpose |
|---|---|---|
| `OUTPUT_DIR` / `AUDIO_DIR` / `VIDEO_DIR` / `TMP_DIR` | `output/…` | Local storage (created on import) |
| `HOST`, `PORT` | `127.0.0.1`, `5000` | Local-only web server |
| `MAX_UPLOAD_MB` | 100 | Max uploaded video size |
| `OLLAMA_URL`, `OLLAMA_MODEL` | `http://127.0.0.1:11434`, `qwen2.5:1.5b` | LLM runner and model |
| `LLM_TIMEOUT_SECONDS` | 120 | Max wait for one generation |
| `LLM_TEMPERATURE`, `LLM_MAX_TOKENS` | 0.8, 260 | Creativity and output cap |
| `ALLOW_TEMPLATE_FALLBACK` | on | Use templates when the LLM fails |
| `TTS_RATE`, `TTS_TIMEOUT_SECONDS` | 165 wpm, 90 s | Speech speed and timeout |
| `OCCASIONS`, `TONES`, `LENGTHS`, `LANGUAGES` | lists/dicts | Form options; `LENGTHS` = target word ranges |

## 3. HTTP API
All JSON errors have the shape `{"ok": false, "error": "<message>"}` (+ `fields` for validation).

### `GET /`
Renders `templates/index.html` with `occasions`, `tones`, `languages`, `lengths`, `model_name`.

### `GET /api/status`
```json
{"ok": true,
 "llm": {"runner": true, "model_ready": true, "model": "qwen2.5:1.5b"},
 "fallback_enabled": true,
 "tts": {"installed": true, "voices": [{"id": "...", "name": "Microsoft Zira ...", "lang": "en"}],
         "languages": {"en": true, "hinglish": true, "hi": false}},
 "ffmpeg": false}
```

### `POST /api/generate-script`
Request:
```json
{"recipient": "Priya", "sender": "Rahul", "occasion": "Birthday", "occasion_name": "",
 "tone": "Friendly", "language": "en", "length": "Short", "message": "Can't wait for Goa!"}
```
Success (LLM):
```json
{"ok": true, "source": "llm", "model": "qwen2.5:1.5b", "script": "Happy birthday, Priya! ...",
 "notice": "Written by the local AI model qwen2.5:1.5b running in Ollama on this computer.",
 "word_count": 52}
```
Success (fallback): `"source": "template"`, `"model": null`, `"fallback_reason": "..."`, notice
contains *"NOT written by an AI model"*.
Errors: `400` validation (`fields` map), `503` LLM failed and fallback disabled.

### `POST /api/tts`
Request `{"script": "...", "language": "en|hinglish|hi", "voice_id": "(optional)"}`.
Success `{"ok": true, "url": "/media/audio/speech_<12hex>.wav", "filename": "...", "duration": 17.4,
"voice_name": "...", "voice_id": "..."}`.
Errors: `400` empty/too long/offensive script or bad language; `422` no voice for language;
`500` pyttsx3 missing, engine error, timeout, empty file (friendly message; detail only in terminal).

### `GET /api/videos`
`{"ok": true, "ffmpeg": false, "videos": [{"name", "url", "label", "size_kb", "created", "mp4_url", "streams"}]}`
(`streams` is `{"video": bool, "audio": bool}` when ffprobe exists, else `null`).

### `POST /api/videos` (multipart: `video` file, `label` text)
Validates size ≥ 2000 bytes and the WebM/Matroska signature `1A 45 DF A3`; saves as
`greeting_<slug>_<YYYYmmdd-HHMMSS>_<6hex>.webm` plus a `.json` side file. `201` on success.

### `DELETE /api/videos/<name>` · `POST /api/videos/<name>/mp4`
Names must match `SAFE_NAME_RE`. MP4 uses `ffmpeg -c:v libx264 -pix_fmt yuv420p -c:a aac`.

### `GET /media/audio/<name>` · `GET /media/videos/<name>[?download=1]`
Served by `send_from_directory` (supports range requests). `download=1` adds `Content-Disposition: attachment`.

## 4. Backend modules and functions

### `app.py`
* `create_app()` – application factory (used by tests too); sets `MAX_CONTENT_LENGTH`.
* `error_response(message, status, **extra)` – uniform JSON errors.
* Error handlers: `413` (too large), `HTTPException` (JSON for `/api/` and `/media/`),
  `Exception` (logs with `log.exception`, returns a generic message — no stack trace).
* `__main__`: starts `app.run(host, port, debug=False, threaded=True)`; `--open` opens the browser.

### `services/validators.py`
* `validate_greeting_request(data)` → cleaned dict or `ValidationError(errors)`.
  Rules: names required, ≤40 chars, letters (any script incl. Devanagari marks) / space / `.'-`
  (`is_valid_name` via `unicodedata` categories); occasion/tone/language/length must be in config;
  Custom needs `occasion_name`; message ≤300; small blocked-word list.
* `validate_script_text(text)` – non-empty, ≤1200 chars, no blocked words.
* `_clean_text` strips control characters and collapses spaces.

### `services/llm_service.py`
* Exceptions: `LLMError` → `LLMUnavailableError`, `LLMModelMissingError`, `LLMTimeoutError`,
  `LLMEmptyResponseError` (each has a user-friendly `reason`).
* `OllamaClient(base_url, model, timeout, session)` – `session` is injectable for tests.
  * `list_models()` – `GET /api/tags` (3 s timeout).
  * `has_model(names)` – compares with `model` (adds `:latest` if no tag).
  * `status()` – never raises; used by the status chip and `check_setup.py`.
  * `chat(system, user)` – `POST /api/chat` with `stream:false`, `keep_alive:"10m"`,
    `options.temperature`, `options.num_predict`, `options.top_p`. Maps
    `Timeout → LLMTimeoutError`, `ConnectionError → LLMUnavailableError`, HTTP 404 →
    `LLMModelMissingError`, empty content/invalid JSON → `LLMEmptyResponseError`.

### `services/script_generator.py`
* `SYSTEM_PROMPT`, `TONE_GUIDE`, `OCCASION_GUIDE`, `LANGUAGE_GUIDE` – prompt building blocks.
* `build_prompts(details)` → `(system_prompt, user_prompt)`.
* `clean_llm_output(text)` – removes leading "Sure/Here is…:" labels, trailing "Note:" sections,
  `(stage directions)`/`[…]`, emojis, markdown symbols, wrapping quotes; collapses whitespace.
* `enforce_length(text, max_words)` – if over 1.3 × max, keeps whole sentences that fit.
* `ensure_personalised(text, details)` – prefixes "Dear <name>," if the name is missing
  (not for Devanagari output, where the model may transliterate the name).
* `generate_script(details, client=None, allow_fallback=None)` – orchestrates; treats answers
  under 5 words as failures; returns the dict described in the API section.

### `services/template_generator.py` (NOT AI)
* `ENGLISH[occasion][tone]` (lists of templates), `HINGLISH[occasion]`, `HINDI[occasion]`.
* `default_event_name(occasion, occasion_name)` and `generate_template_greeting(details, rng)`.

### `services/tts_service.py` and `services/tts_worker.py`
* Worker CLI: `python -m services.tts_worker voices` / `speak --text-file --out --rate --voice-id`.
  Prints one JSON line; exit codes 0/2 (pyttsx3 missing)/3 (engine error).
  `describe_language()` classifies voices as `en`/`hi`/`other` from id, name and language tags;
  `is_indian_english()` detects en-IN voices; `linux_espeak_fallback()` is a Linux-only safety net
  (pyttsx3's espeak driver sometimes writes nothing for long texts) and is never used on Windows.
* `tts_library_installed()`, `_run_worker(args, timeout)` (subprocess with `CREATE_NO_WINDOW`,
  UTF-8, timeout → `TTSTimeoutError`), `list_voices(force)` (cached 120 s),
  `supported_languages(voices)`, `choose_voice(language, voices, preferred_id)`
  (Hindi → Hindi voice or `TTSVoiceMissingError`; Hinglish → Indian-English voice if present;
  English → en-US/US/en-IN/en-GB preferred), `wav_duration_seconds(path)`, `cleanup_old_audio()`
  (deletes speech files older than 24 h), `synthesize(script, language, voice_id, rate)`.
* Why a subprocess: SAPI5 is a COM component; repeatedly calling `runAndWait()` inside a
  long-running, multi-threaded web server can hang. A short-lived process per request is isolated,
  can be killed by a timeout, and frees resources automatically.

### `services/video_store.py`
* `SAFE_NAME_RE`, `WEBM_MAGIC`, `MIN_VIDEO_BYTES`, `VideoError`.
* `slugify`, `is_safe_name`, `safe_path` (regex + resolved-parent check),
  `save_uploaded_video`, `describe`, `list_videos` (newest first), `delete_video` (removes
  `.webm`, `.mp4`, `.json`), `inspect_streams` (ffprobe, optional), `convert_to_mp4` (optional).

### `check_setup.py`
`check_python` (version, RAM via `GlobalMemoryStatusEx` / `/proc/meminfo`), `check_packages`,
`check_llm(interactive)` (finds `ollama.exe` on PATH or in `%LOCALAPPDATA%\Programs\Ollama`, can
start `ollama serve`, prints download size/disk/hardware/license and asks before `ollama pull`),
`check_tts`, `check_ffmpeg`. Exit code 1 only if Python or required packages are missing.

## 5. Front-end components

### `avatar.js` — `AvatarRenderer`
* Canvas is 960×540 (the recorded resolution); CSS scales it on screen.
* Data: `AVATAR_THEMES` (per occasion: gradient, accent, particle type, headline),
  `EXPRESSIONS` (target values for `browRaise`, `browTilt`, `smile`, `eyeOpen`, `eyeSize`,
  `mouthO`), `TONE_EXPRESSION` (Friendly→happy, Formal→calm, Funny→excited, Heartfelt→warm),
  `AVATAR_LOOKS` (skin/hair/shirt palettes).
* Public: `start()`, `setLevelSource(fn)`, `setSpeaking(bool)`, `setExpression(name)`,
  `setLook(part, color)`, `wave(ms)`, `setTheme(occasion)`, `setCaption({headline,name,from,source})`.
* `update(now)`: eases face values (`dt*6`), blink state machine (140 ms close + 140 ms open,
  every 2–5 s), gaze targets, mouth target = `level^0.8` with asymmetric smoothing (0.55 opening,
  0.28 closing), arm lift easing, particle motion with wrap-around.
* `draw(now)`: background → particles → shadow → `drawAvatar` (body, collar, neck, arm, head with
  tilt: back hair, ears, face, fringe, cheeks, eyes, brows, nose, mouth) → `drawCard` (headline,
  name, sender, 5 loudness bars) → `drawDisclosure`. `fitText` shrinks long names to fit.

### `voice.js` — `VoicePlayer`
* `ensureGraph()` (once; `createMediaElementSource` may only be called once per element):
  source → analyser (fftSize 1024) → `ctx.destination`; source → `MediaStreamDestination`.
* `load(url)` resolves on `loadedmetadata` with the duration; `play/pause/stop/replay`.
* `level()` – RMS of `getFloatTimeDomainData`, mapped `(rms − 0.012) / 0.16`, clamped 0..1.
* `recordingTrack()` – the audio track used by the recorder.

### `recorder.js` — `GreetingRecorder`
* `checkSupport(canvas)` – MediaRecorder, `captureStream`, AudioContext, a WebM type.
* `pickMimeType()` – first of `video/webm;codecs=vp9,opus`, `…vp8,opus`, `video/webm`.
* `record(onProgress)` – see the sequence below. Constants `LEAD_IN_MS=900`, `TAIL_MS=1300`, `FPS=30`;
  bitrates 3 Mbps video, 128 kbps audio; `start(250)` timeslice; safety timeout = expected
  length + 15 s; `cancel()` rejects with `code:"cancelled"`. Resolves `{blob, mimeType, seconds}`
  only from `onstop` and only if the blob is ≥ 2000 bytes.

Recording sequence:
```
stop preview → resume AudioContext → get audio track → canvas.captureStream(30)
→ new MediaStream([video, audio]) → new MediaRecorder(...).start(250)
→ avatar.wave(); after 900 ms voice.play() + setSpeaking(true)
→ audio "ended" → setSpeaking(false), wave(); after 1300 ms recorder.stop()
→ onstop: Blob(chunks) → size check → resolve → preview/download → POST /api/videos
```

### `app.js`
State object (`details`, `source`, `model`, `originalScript`, `voiceForScript`, `recording`…) and
functions `loadStatus`, `updateLanguageOptions` (disables languages without a voice),
`updateOccasionField`, `readForm`, `quickValidate`, `showFieldErrors`, `generateScript`,
`showSource`, `onScriptChanged` (edit detection; warns if the voice is stale), `createVoice`,
`voiceIsCurrent`, `setRecordEnabled` (needs current voice + consent), `recordVideo`,
`showResult` (includes the WebM duration workaround `currentTime = 1e101`), `downloadName`,
`saveToGallery`, `loadGallery`, `renderGallery` (HTML-escaped labels), `buildSwatches`,
`refreshCaption`, `applyAutoExpression`, `toast`, `setBusy`, `setStep`, `api` (fetch wrapper that
turns non-OK JSON into thrown `Error`s). `window.greetingStudio` exposes objects for debugging and
the browser check.

## 6. Prompt flow
```
form → validate_greeting_request → build_prompts
   SYSTEM: role + output rules (only spoken words, no titles/emojis/stage directions, kind)
   USER:   names, occasion+guide, tone+guide, word range, language rule,
           "start with <name>, end with sign-off from <sender>", personal message
→ OllamaClient.chat(temperature 0.8, num_predict 260, top_p 0.9)
→ clean_llm_output → (<5 words? → fallback) → ensure_personalised → enforce_length
→ {script, source:"llm", model, notice}
```

## 7. Error-handling matrix
| Situation | Where detected | User sees |
|---|---|---|
| Empty name / invalid option | `app.js` + `validators.py` | red field messages |
| Ollama not running | `chat` → `LLMUnavailableError` | template + reason badge |
| Model not downloaded | HTTP 404 → `LLMModelMissingError` | template + "not downloaded" |
| Generation too slow | `LLMTimeoutError` (120 s) | template + "took too long" |
| Empty / tiny answer | `LLMEmptyResponseError` / <5 words | template + reason |
| pyttsx3 missing | `tts_library_installed` / exit 2 | "pyttsx3 is not installed…" |
| No Hindi voice | `choose_voice` | "Choose Hinglish instead…" (422) |
| Speech engine crash / hang | exit 3 / `TimeoutExpired` | friendly message; detail in terminal |
| Browser lacks MediaRecorder | `checkSupport` | "use Chrome or Edge" |
| Voice cannot play during recording | `play()` rejection | error, recording discarded |
| Empty recording | `onstop` size check | "came out empty… keep tab visible" |
| Bad upload / name | `video_store` | 400/404 JSON |
| Anything unexpected | Flask handler | generic message, details in terminal |

## 8. Tests
`pytest` (166 tests, ~1 s): `tests/test_app.py` (routes, validation, fallback, TTS errors, uploads,
download headers, path traversal, MP4 without FFmpeg, hidden stack traces),
`tests/test_llm_service.py` (fake HTTP session: success, unavailable, timeout, 404, 500, empty,
invalid JSON, status), `tests/test_script_generator.py` (prompt contents, cleaning, length,
fallbacks, every template combination, validation cases), `tests/test_tts_service.py` (voice
choice, language support, worker exit codes, timeouts, empty output, WAV duration).
`tests/conftest.py` gives each test a temporary output folder.
`tests/browser_check.py` (optional, Playwright): 18 end-to-end checks including ffprobe of the
downloaded WebM. See `TEST_REPORT.md` for actual results.

## 9. Design decisions
| Decision | Reason |
|---|---|
| Ollama + `qwen2.5:1.5b` | Free, no account, one installer on Windows, CPU-friendly 986 MB model, Apache-2.0, multilingual |
| Non-streaming LLM call | Simpler code; greetings are short |
| Template fallback, always labelled | Demo still works without the model; honesty about AI |
| pyttsx3 / SAPI5 | Offline, preinstalled voices on Windows, tiny dependency |
| TTS in a subprocess | Avoids COM hangs in the web server; enforceable timeout |
| Canvas 2D cartoon | No GPU, no models, original asset, easy to explain and customise |
| Loudness-based lip movement | Works for any language/voice; honest "approximate" claim |
| Browser recording (MediaRecorder) | No server-side video stack needed; real audio+video WebM |
| Web Audio `MediaStreamDestination` | Puts the voice into the recording as a real track |
| Files instead of a database | Fewer moving parts; data stays visible in `output/` |
| Strict file-name regex | Simple, robust protection against path traversal |
| `127.0.0.1` only | Nothing exposed to the network |
