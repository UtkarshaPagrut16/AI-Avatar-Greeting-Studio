# Project Overview — PS 36: AI Avatar Greeting Video Generator

## 1. Introduction
**AI Avatar Greeting Studio** is a web application that creates a short, personalised greeting
video. The user types a few details — who the greeting is for, who it is from, the occasion, the
tone, the language and an optional personal message. A small **Large Language Model (LLM)** running
on the user's own computer writes the greeting. The computer then **speaks** it with an offline
voice, an original **cartoon avatar** "says" it on screen, and the browser **records** the avatar
and the voice together into a video file that can be downloaded and shared.

Everything runs locally on a normal Windows 11 laptop, using only free tools.

## 2. Problem statement
People often want to send a personal greeting — a birthday wish, a thank-you, a welcome — that
feels more special than a text message. Existing "talking avatar" services are usually:
* **paid** (subscriptions or credits),
* **cloud-based** (names and messages are uploaded to someone else's servers),
* **ethically risky** (they can clone a real person's face or voice without consent),
* or require **powerful GPUs** to run deep-learning video models.

The task (PS 36) is to *frame the task, generate the script with an LLM, synthesise voice and
avatar video, handle timing and lip-sync limitations, discuss consent for likeness, and present the
completed video* — using approaches suitable for a student project.

## 3. Objectives
1. Generate a **personalised greeting script with a genuine LLM** that uses every input field.
2. Keep the LLM **free and local** (no API keys, no cloud) and run it **without a GPU**.
3. Convert the script into **real speech audio** offline.
4. Show an **animated talking avatar** that blinks, changes expression and moves its mouth with the voice.
5. Produce a **downloadable video file containing both animation and audio**.
6. Be **honest**: label AI vs template text, disclose the avatar is computer-generated, state limitations.
7. Make installation **easy on Windows 11** and keep the architecture **simple to explain**.

## 4. Proposed solution
A small **Flask** (Python) web server provides four services: script generation, speech, a video
gallery and a status check. The browser page (HTML/CSS/JavaScript) provides the form, the editor,
the Canvas avatar and the recorder.

* **Script:** Flask builds a careful prompt and sends it to **Ollama**, which runs the
  **`qwen2.5:1.5b`** model locally. If Ollama is unavailable, a clearly labelled **template
  fallback** keeps the demo working.
* **Voice:** **pyttsx3** uses the voices built into Windows (SAPI5) to save a `.wav` file.
* **Avatar:** an original cartoon drawn with the **Canvas 2D API**, animated ~60 times per second.
* **Lip movement:** the **Web Audio API** measures the loudness of the voice while it plays; louder
  = mouth more open (approximate lip-sync).
* **Video:** `canvas.captureStream()` gives a video track, the Web Audio graph gives an audio track;
  they are combined and recorded with **MediaRecorder** into a **WebM** file.

## 5. Features and scope
**In scope (implemented):**
* Form with recipient, sender, 7 occasions (with festival/custom names), 4 tones, 3 languages
  (English, Hinglish, Hindi), 2 lengths, optional message.
* Local LLM generation, editing, regeneration, word count and speech-length estimate.
* Clear source badge: "AI-generated · qwen2.5:1.5b" or "Template fallback – NOT AI".
* Offline speech with automatic voice selection; language availability detected from installed voices.
* Play / pause / stop / replay; speaking indicator.
* Avatar: idle bob and breathing, blinking, eye movement, 5 expressions (auto from tone), waving
  hand, colour customisation, occasion-themed background and particles (confetti, hearts, lights…),
  greeting card with names, on-video "computer-generated" disclosure.
* Recording with progress, cancel, error messages; preview player; download button.
* Local gallery with download, delete, optional MP4 conversion and optional ffprobe track check.
* Consent checkbox before recording; ethics panel.
* Setup checker, one-click Windows launcher, 166 automated tests, optional browser test.

**Out of scope (deliberately):** photo upload / face cloning, voice cloning, photorealistic or
3D avatars, phoneme-level lip-sync, user accounts, databases, cloud hosting.

## 6. Real-world applications
* Personalised birthday/anniversary/festival wishes for friends and family.
* Teachers or class representatives welcoming new students; HR welcoming new employees.
* Thank-you videos for event volunteers, guest speakers or customers of a small business.
* Accessible greetings for people who prefer listening to reading.
* A teaching example of combining an LLM with classic multimedia programming, privately.

## 7. System architecture
```
┌──────────────────────────── Browser (Chrome / Edge) ────────────────────────────┐
│ index.html + style.css                                                          │
│ app.js ── form, editor, buttons, gallery, calls the API with fetch()            │
│ avatar.js ── AvatarRenderer: draws the cartoon on <canvas> 60x per second       │
│ voice.js ── VoicePlayer: <audio> + Web Audio (loudness + recordable track)      │
│ recorder.js ── GreetingRecorder: captureStream + MediaRecorder → WebM Blob      │
└───────────────▲──────────────────────────────┬──────────────────────────────────┘
                │ JSON / files over HTTP        │ (127.0.0.1:5000, this computer)
┌───────────────┴──────────────────────────────▼──────────────────────────────────┐
│ Flask server: app.py                                                            │
│  ├─ validators.py          check & clean input                                  │
│  ├─ script_generator.py ── llm_service.py ──HTTP──► Ollama (127.0.0.1:11434)    │
│  │                     └── template_generator.py (fallback, NOT AI)  qwen2.5:1.5b│
│  ├─ tts_service.py ── runs tts_worker.py ── pyttsx3 ── Windows SAPI5 voices      │
│  └─ video_store.py ── output/videos (+ optional FFmpeg / ffprobe)               │
└─────────────────────────────────────────────────────────────────────────────────┘
```
Diagrams in Mermaid format: see `FLOWCHARTS.md`.

## 8. Complete workflow (input → downloaded video)
1. User fills the form and clicks **Generate**.
2. `app.js` sends the form as JSON to `POST /api/generate-script`.
3. Flask validates it (`validate_greeting_request`).
4. `build_prompts` turns it into a *system prompt* and a *user prompt*.
5. `OllamaClient.chat` sends them to Ollama; the model writes the greeting.
6. `clean_llm_output`, `ensure_personalised` and `enforce_length` tidy the answer.
7. The script and its source (`llm`/`template`) return to the browser and appear in the editor.
8. User edits (optional) and clicks **Create voice** → `POST /api/tts`.
9. `tts_service.synthesize` picks a voice and runs `tts_worker.py`, which saves a `.wav`.
10. The browser loads the `.wav` into `VoicePlayer`. **Play** previews; the mouth follows loudness.
11. User ticks consent and clicks **Record** → `GreetingRecorder.record()`.
12. The recorder combines the canvas video track and the voice audio track, starts MediaRecorder,
    the avatar waves, the voice plays, then a goodbye wave, then recording stops.
13. Chunks become a `Blob` (WebM). It is shown in a `<video>` player and offered for download.
14. A copy is uploaded to `POST /api/videos` and appears in the gallery.

## 9. Frontend and backend responsibilities
| Frontend (browser) | Backend (Flask, Python) |
|---|---|
| Show the form, editor, avatar, gallery | Validate all input again (never trust the browser) |
| Quick checks for empty fields | Build prompts, call the LLM, clean the output |
| Play audio, measure loudness | Fall back to templates and label them |
| Draw and animate the avatar | Create speech `.wav` files with pyttsx3 |
| **Record the video** (canvas + audio) | Store, list, delete, convert videos |
| Download the finished video | Report status of Ollama, model, voices, FFmpeg |

Video is recorded in the **browser** because the browser already has the canvas and the audio and
can encode WebM efficiently — Python would need heavy video libraries to do the same.

## 10. How Flask works in this project
Flask is a small Python web framework. In `app.py`, `create_app()` creates the app and registers
**routes** with decorators such as `@app.post("/api/tts")`. When the browser requests that URL,
Flask calls the matching function and returns its result (HTML or JSON). `render_template`
fills `templates/index.html` with the occasion, tone and language lists from `config.py`.
`send_from_directory` safely serves audio and video files. Error handlers turn every error into a
simple JSON message without exposing stack traces. The server listens only on `127.0.0.1`, so
other computers cannot access it.

## 11. How HTML, CSS and JavaScript are used
* **HTML** (`templates/index.html`): the structure — cards, form fields, canvas, buttons, gallery.
* **CSS** (`static/css/style.css`): the lavender/purple look, rounded cards, shadows, hover
  effects, loading spinner, toasts, responsive two-column layout.
* **JavaScript**: `app.js` handles events and calls the API with `fetch`; `avatar.js` draws;
  `voice.js` handles audio; `recorder.js` records. No frameworks or CDNs are used, so the page
  works offline.

## 12. How the LLM generates the personalised script
An LLM predicts text one *token* (word piece) at a time based on the instructions it is given. We
give `qwen2.5:1.5b` two messages:
* **System prompt** (role and rules): write only the spoken words, one short paragraph, no titles,
  emojis or stage directions, keep it kind and suitable for all ages.
* **User prompt** (the task): recipient, sender, occasion with guidance, tone with guidance, target
  word range, language instruction, "start by addressing Priya by name, end with a sign-off from
  Rahul", and the personal message to weave in.

Temperature 0.8 gives natural variety, so **Regenerate** produces new wording. `num_predict` limits
the answer to about 260 tokens.

## 13. How the local LLM runner and model work
**Ollama** is a free program that downloads models and runs them locally, exposing a small HTTP
API at `http://127.0.0.1:11434`. The model **`qwen2.5:1.5b`** has about 1.54 billion parameters,
stored in **4-bit quantised** form (Q4_K_M), which shrinks it to 986 MB so it fits in RAM and runs
on a CPU. On the first request Ollama loads the model into memory (slower); we ask it to keep the
model loaded for 10 minutes (`keep_alive`) so later requests are faster. `GET /api/tags` tells us
which models are downloaded; `POST /api/chat` generates text.

## 14. How prompts are constructed and inputs are passed to the model
`build_prompts(details)` in `services/script_generator.py` looks up:
* `OCCASION_GUIDE["Birthday"]` → "wish them a happy birthday and a great year ahead",
* `TONE_GUIDE["Funny"]` → "light-hearted with one gentle, clean joke; never insulting",
* `LANGUAGE_GUIDE["hinglish"]` → "Hindi words written ONLY in English letters…",
* `config.LENGTHS["Short"]` → 40–65 words,

and writes them line by line into the user prompt, together with the names and message. Because
every field changes the prompt text, every field changes the output (the tests check this).
`OllamaClient.chat` sends `{"model", "messages":[system, user], "options":{temperature, num_predict}}`
as JSON.

## 15. How the fallback generator works and how it differs from the LLM
`services/template_generator.py` contains **hand-written sentences** for each occasion and tone
(English), and per occasion for Hinglish and Hindi. It replaces `{r}`, `{s}` and `{e}` with the
recipient, sender and event name, and appends the personal message word for word.

| | LLM | Template fallback |
|---|---|---|
| Creates new sentences | ✅ yes, different each time | ❌ only picks prewritten sentences |
| Understands the personal message | ✅ weaves its meaning in | ❌ appends it verbatim |
| Needs Ollama + model | ✅ | ❌ |
| Is it AI? | ✅ yes | ❌ **no** — ordinary programming |
| Label in the app | "🤖 AI-generated · qwen2.5:1.5b" | "📄 Template fallback – NOT AI" + reason |

The fallback runs **only** when the LLM fails (not running, model missing, timeout, empty/too-short
answer, server error).

## 16. How local text-to-speech works
pyttsx3 is a Python library that controls the operating system's speech engine — on Windows,
**SAPI5** with voices like Microsoft Zira/David. It is a classic (non-neural) synthesiser: it
converts text to phonemes using pronunciation rules and dictionaries, then produces audio.
`tts_service.synthesize` writes the script to a temporary text file and starts
`python -m services.tts_worker speak …` as a **separate process** (more reliable than running the
COM-based engine inside the web server, and it can be given a timeout). The worker calls
`engine.save_to_file(text, path)` and `engine.runAndWait()`, producing a `.wav`. The service checks
the file is non-empty and reads its duration with Python's `wave` module.

## 17. How the avatar is animated
`AvatarRenderer` (in `avatar.js`) runs a loop with `requestAnimationFrame`. Each frame it:
* eases face values (eyebrow height/tilt, smile, eye openness, eye size) toward the current
  **expression** so changes are smooth,
* runs a **blink** every 2–5 s (close and open over ~280 ms) and small random **eye movements**,
* applies an idle **head bob**, slight **tilt** and **breathing** of the shoulders,
* raises and swings the **arm** when waving (start and end of the video),
* moves the **particles** (confetti, hearts, bubbles, festival lights, sparkles),
* sets **mouth openness** from the voice loudness,
* draws everything with shapes: ellipses, Bézier curves and rounded rectangles.

## 18. How Canvas recording works
`canvas.captureStream(30)` turns the canvas into a live **video track**: whenever the canvas is
redrawn, a new video frame is produced (up to 30 per second requested). Because the avatar redraws
continuously, the stream contains the full animation.

## 19. How audio and video streams are combined
Simply playing an `<audio>` element next to the canvas does **not** put sound into a recording.
`VoicePlayer.ensureGraph()` builds a Web Audio graph:
`<audio> → MediaElementSource → (Analyser → speakers)` and `→ MediaStreamDestination`.
The `MediaStreamDestination` provides a real **audio track**. `GreetingRecorder.record()` creates
`new MediaStream([videoTrack, audioTrack])` — one stream with both tracks.

## 20. How WebM is generated and downloaded
`new MediaRecorder(stream, {mimeType: "video/webm;codecs=vp9,opus"})` encodes the stream (VP9
video, Opus audio; it falls back to VP8 or plain WebM if needed). Every 250 ms it delivers a chunk
of data. When the voice ends and the goodbye wave finishes, `recorder.stop()` is called; the
`onstop` event joins the chunks into a `Blob`, checks it is not empty, and only then reports
success. `URL.createObjectURL(blob)` makes a temporary link used both by the `<video>` preview and
the `<a download>` button.

## 21. Error handling
* **Input:** validated in the browser and again on the server; field-level messages are shown.
* **LLM:** separate error types for not running, model missing, timeout, empty answer → fallback
  with the reason displayed.
* **Speech:** missing pyttsx3, missing voice for the language, engine error, timeout, empty file —
  each with a friendly message.
* **Recording:** browser support check before starting, audio playback errors, recorder errors,
  empty result, a safety timer, and a Cancel button.
* **Server:** unexpected errors are logged in the terminal; the user sees a short message, never a
  stack trace. Upload size is limited to 100 MB; file names are strictly checked.

## 22. Security, privacy and consent
* **Local only:** Flask listens on `127.0.0.1`; Ollama runs locally; nothing is sent to the internet
  during normal use.
* **Minimal data:** only names and a short message; no accounts, no database; files stay in
  `output/` and can be deleted from the gallery.
* **Safe files:** only server-generated file names are accepted (blocks `../` path tricks);
  uploads must start with the WebM signature.
* **Content:** a short blocked-word list and polite-output instructions; output length is limited.
* **Consent for likeness:** the avatar is an **original cartoon**; the app intentionally offers no
  photo upload or voice cloning, because using a real person's face or voice requires that person's
  informed permission — and processing locally does **not** remove that requirement.
* **Disclosure:** every video carries "Animated, computer-generated avatar – not a real person" and
  whether the script came from the AI or the template. A consent checkbox must be ticked before
  recording.

## 23. Limitations
* Lip-sync is approximate (loudness-based, not phoneme-based).
* SAPI5 voices sound robotic compared to neural voices; Hindi needs a Hindi SAPI5 voice.
* A 1.5B model can occasionally produce generic, slightly odd or (in Hindi) less fluent text.
* CPU-only generation can take tens of seconds on slow laptops; the first request is slowest.
* WebM is not supported by some older players/phones (MP4 conversion needs FFmpeg).
* MediaRecorder WebM files have no duration in their header; some players show the length late.
* Recording happens in real time and needs the tab to stay visible.
* Blocked-word filtering is basic.

## 24. Future enhancements
* Phoneme-level lip-sync (e.g. visemes from a phoneme aligner) and more mouth shapes.
* Neural offline TTS (e.g. Piper) for more natural voices and better Hindi.
* More avatar styles and backgrounds; subtitles burned into the video.
* Larger/multilingual models when hardware allows; streaming output to show text as it is written.
* Faster-than-real-time rendering with WebCodecs; automatic MP4 export.
* Sharing via QR code on the local network.

## 25. Important files and functions
| File | Key items |
|---|---|
| `app.py` | `create_app`, routes `/api/generate-script`, `/api/tts`, `/api/videos`, `/api/status` |
| `services/script_generator.py` | `build_prompts`, `clean_llm_output`, `enforce_length`, `generate_script` |
| `services/llm_service.py` | `OllamaClient.chat`, `OllamaClient.status`, LLM error classes |
| `services/template_generator.py` | `generate_template_greeting` (NOT AI) |
| `services/tts_service.py` | `synthesize`, `choose_voice`, `list_voices` |
| `services/video_store.py` | `save_uploaded_video`, `list_videos`, `convert_to_mp4` |
| `static/js/avatar.js` | `AvatarRenderer` (`update`, `draw`, `drawMouth`, `setExpression`) |
| `static/js/voice.js` | `VoicePlayer` (`ensureGraph`, `level`, `recordingTrack`) |
| `static/js/recorder.js` | `GreetingRecorder.record`, `checkSupport`, `pickMimeType` |
| `static/js/app.js` | `generateScript`, `createVoice`, `recordVideo`, `saveToGallery` |

## 26. Complete example — a birthday greeting for Priya
1. **Input:** Recipient `Priya`, Sender `Rahul`, Occasion `Birthday`, Tone `Friendly`,
   Language `English`, Length `Short`, Message `Can't wait for our Goa trip!`.
2. **Prompt (user part, abbreviated):**
   ```
   Recipient name: Priya
   Sender name: Rahul
   Occasion: Birthday - wish them a happy birthday and a great year ahead.
   Tone: Friendly - warm, casual and cheerful, like talking to a good friend.
   Length: between 40 and 65 words.
   Write in simple, natural English.
   Start by addressing Priya by name. End with a short sign-off from Rahul.
   Include the meaning of this personal message ... "Can't wait for our Goa trip!"
   Now write the greeting script.
   ```
3. **LLM answer** (example of the *kind* of text the model writes; actual wording varies):
   *"Happy birthday, Priya! I hope your day is full of laughter, cake and your favourite people.
   I'm already counting down to our Goa trip — beaches, sunsets and lots of fun await us! Have an
   amazing year ahead. With love, Rahul."*
4. **Cleaning:** labels like "Here is your greeting:", quotes, emojis and `(smiles)` would be removed.
5. **Display:** badge "🤖 AI-generated · qwen2.5:1.5b"; Rahul adds "See you soon!" → "✏️ Edited by you".
6. **Voice:** Create voice → `speech_3f9a….wav`, Microsoft Zira, ~18 s.
7. **Preview:** Play — Birthday theme (lavender-pink, confetti), card "Happy Birthday / Priya /
   with love from Rahul", Friendly → *happy* expression, mouth follows the voice.
8. **Record:** tick consent → Record. 0.9 s wave → speech → 1.3 s goodbye wave → stop. ~20 s video.
9. **Result:** `greeting_priya_birthday_20261019-1730.webm` (VP9 + Opus, 960×540) is previewed,
   downloaded, and saved to the gallery as "Birthday for Priya".

> In automated testing in the build environment (see `TEST_REPORT.md`) this exact flow produced an
> 18–19 s WebM with a VP9 video track and an Opus audio track; ffmpeg measured real speech audio
> (mean volume about −22 dB) in the file.

### Which parts are AI and which are not?
| Component | AI? |
|---|---|
| Greeting text from `qwen2.5:1.5b` | ✅ **Generative AI (LLM)** |
| Template fallback | ❌ conventional programming |
| pyttsx3 / SAPI5 speech | ❌ classic rule-based speech synthesis (not a neural network in this project) |
| Avatar drawing, expressions, blinking | ❌ conventional programming (Canvas) |
| Mouth movement | ❌ signal processing (loudness measurement) |
| Recording, gallery, validation | ❌ conventional programming |
