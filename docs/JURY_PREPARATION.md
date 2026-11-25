# Jury Preparation

Speak naturally — these are guides, not lines to memorise word for word.

---

## 30-second introduction
"Good morning. My project is PS 36, the AI Avatar Greeting Video Generator. You enter a name, an
occasion and a tone, and a small AI language model running **on my own laptop** writes a
personalised greeting. The computer speaks it with an offline voice, an animated cartoon avatar
says it on screen, and the browser records everything into a downloadable video. It is completely
free, works offline after setup, and keeps personal data private."

## One-minute explanation
"Greeting videos are popular, but most avatar tools are paid, cloud-based, or clone real faces
without consent. I built a free, local alternative. The front end is HTML, CSS and JavaScript; the
back end is Flask in Python. For the script, Flask builds a careful prompt and sends it to
**Ollama**, which runs the **Qwen 2.5 1.5-billion-parameter** model on the CPU. The text is cleaned
and shown in an editor, labelled as AI-generated. Then **pyttsx3** uses Windows' built-in voices to
create a WAV file. My original cartoon avatar, drawn with the Canvas API, blinks and changes
expression, and its mouth follows the loudness of the voice using the Web Audio API. Finally, the
**MediaRecorder** API records the canvas and the audio together into a WebM video you can download.
If the model is unavailable, a clearly labelled template fallback keeps the demo working."

## Two-minute explanation
Add to the one-minute version:
* "Every input changes the prompt — tone has its own description, occasion has its own guidance,
  and the language instruction switches between English, Hinglish and Hindi."
* "Small models sometimes add titles or emojis, so I post-process the output and limit its length."
* "Speech runs in a separate process because the Windows speech engine can freeze inside a web server."
* "A key detail: playing audio next to a canvas does not put sound into a recording. I route the
  audio through a Web Audio graph to get a real audio track, combine it with the canvas video track
  into one MediaStream, and record that."
* "I handled lip-sync honestly: it is loudness-based, approximate — not phoneme-level."
* "For ethics: an original cartoon, no photo upload or voice cloning, a consent checkbox, and a
  'computer-generated' label inside every video."
* "There are 166 automated tests, and an optional browser test that records a real video and
  checks that it contains both a video and an audio track."

## Five-minute technical explanation (outline)
1. **Problem & objectives** (30 s) — PS 36 requirements, free/local/ethical.
2. **Architecture** (45 s) — browser (4 JS modules) ↔ Flask (`app.py` + 6 service modules) ↔ Ollama; files in `output/`.
3. **LLM** (75 s) — why local; model size 986 MB, Q4_K_M, Apache-2.0; system vs user prompt;
   temperature 0.8; `num_predict` 260; cleaning; fallback with labels; error types.
4. **Speech** (30 s) — pyttsx3/SAPI5, subprocess worker, voice selection by language, WAV duration.
5. **Avatar** (45 s) — Canvas loop, easing, blink state machine, expressions from tone, RMS loudness → mouth.
6. **Recording** (45 s) — `captureStream(30)` + `MediaStreamDestination` → `MediaStream` → `MediaRecorder` VP9/Opus → Blob → download; success only in `onstop`.
7. **Quality, security, ethics** (30 s) — validation, safe file names, localhost only, tests, consent.
8. **Limitations & future** (30 s) — approximate lip-sync, robotic voice, small model; Piper TTS, visemes.

---

## Live demonstration script
1. **Before the jury arrives:** start Ollama; run `run_windows.bat`; generate one greeting to warm
   up the model (the first generation is the slowest); close other heavy apps; set volume.
2. "Here's the status bar — Ollama is ready with qwen2.5:1.5b, and these are the voices pyttsx3 found."
3. Fill: *Priya*, *Rahul*, *Birthday*, *Friendly*, *English*, message *"Can't wait for our Goa trip!"*.
4. Click **Generate**. "The local model is writing this now — nothing is going to the internet."
5. Point at the **AI-generated · qwen2.5:1.5b** badge. Make a small edit → "Edited by you".
6. Click **Regenerate** once to show variety (optional, if time).
7. Change tone to **Funny** → regenerate → show the difference (optional).
8. **Create voice** → **Play**. "The mouth follows the loudness of the real audio."
9. Open **Expression and colours**, change shirt colour.
10. Tick **consent** → **Record**. Explain the progress bar and the lead-in/goodbye wave.
11. Play the result; click **Download**; open the file from Downloads in Chrome/VLC.
12. Show the gallery entry ("✓ video + audio" appears if FFmpeg is installed).
13. Optional: stop Ollama (tray → Quit) and generate again → show the **Template fallback – NOT AI** label and reason.

### Demonstration checklist
- [ ] Laptop charged / plugged in; volume up; notifications off
- [ ] Ollama running (llama icon) and `ollama list` shows `qwen2.5:1.5b`
- [ ] App running; page open in Chrome/Edge at `http://127.0.0.1:5000`
- [ ] One warm-up generation done
- [ ] Status chips green
- [ ] A **backup video** already in the gallery and a copy in Downloads
- [ ] Screenshots in `docs/screenshots` ready
- [ ] Browser zoom so the jury can read the text (Ctrl + / Ctrl −)

### Backup plan
| If this fails… | Do this |
|---|---|
| Model slow or not responding | Explain timeouts; show the **template fallback** (clearly labelled) and continue the demo; show a previously generated AI script/video |
| Ollama will not start | Same as above; show `check_setup.py` output explaining the problem |
| No sound from speakers | Show the voice duration and the moving mouth; play the downloaded video on a phone/headphones |
| Voice creation fails | Show the error message (friendly handling is a feature); play a gallery video made earlier |
| Recording fails | Play the backup video from the gallery; explain the recorder steps with `FLOWCHARTS.md` |
| Browser problem | Use the other browser (Edge ↔ Chrome) |
| Everything fails | Use the screenshots and backup video; walk through the code |

Say it calmly: *"This is exactly why I built error handling and a fallback — let me show you."*

---

## Likely jury questions and answers

### Problem, objectives, innovation
1. **What problem does your project solve?** — Creating personalised greeting videos for free,
   privately and ethically, without paid cloud avatar services or face cloning.
2. **What are your objectives?** — LLM-generated personalised script, offline speech, animated
   avatar, downloadable video with audio, honest labelling, easy Windows setup.
3. **What is innovative here?** — Everything runs locally on a normal laptop with free tools; the
   AI and the multimedia pipeline are combined in the browser; and honesty is built in — AI vs
   template labels and a disclosure inside the video.
4. **Who would use it?** — Students, families, teachers, HR teams, small businesses sending
   thank-you or welcome videos.
5. **How is it different from just sending a text?** — It is personalised by an AI, spoken and
   animated, making it more engaging, while still taking under a minute to create.

### Architecture, Flask, Python, JavaScript
6. **Explain your architecture.** — Browser front end (HTML/CSS/JS) talks over HTTP/JSON to a Flask
   back end; Flask talks to Ollama for the LLM and to pyttsx3 for speech; videos are recorded in
   the browser and saved to a local folder.
7. **Why Flask?** — Lightweight, easy to learn and explain, perfect for a few API routes.
8. **What is a route?** — A URL mapped to a Python function, e.g. `POST /api/tts` → `api_tts()`.
9. **Why is the video recorded in the browser and not in Python?** — The browser already has the
   canvas and the audio and can encode WebM natively; Python would need heavy video libraries.
10. **What does `create_app()` do?** — It is an application factory that builds and configures the
    Flask app; tests use it to create a fresh app.
11. **How do the front end and back end communicate?** — `fetch()` calls with JSON bodies; the
    server replies with JSON like `{"ok": true, "script": "..."}`.
12. **Why no database?** — We only store a few files; a folder is simpler and transparent.
13. **Why no React or other framework?** — Not needed for one page; plain JS is lighter, works
    offline, and is easier to explain.

### LLM, model, prompt engineering
14. **What is an LLM?** — A neural network trained on large text data to predict the next token;
    instruction-tuned versions follow instructions.
15. **Which model do you use and why?** — `qwen2.5:1.5b` — 1.54 B parameters, 986 MB download,
    runs on CPU, multilingual, Apache-2.0 licensed: a good balance of quality, size and speed.
16. **What is Ollama?** — A free local runner that downloads models and serves them through an HTTP
    API on port 11434.
17. **Why a local LLM instead of a paid API?** — Zero cost, no API keys, works offline, and
    personal data never leaves the computer — matching the project requirements.
18. **How is the model installed and loaded?** — `ollama pull qwen2.5:1.5b` downloads it once (our
    setup script asks first). Ollama loads it into RAM on the first request and keeps it for 10
    minutes (`keep_alive`).
19. **What hardware is needed?** — No GPU. 8 GB RAM recommended; about 1.1 GB disk for the model.
20. **What is quantisation?** — Storing weights with fewer bits (4-bit here), shrinking the model
    so it fits in RAM with a small quality loss.
21. **How do you build the prompt?** — A system prompt with rules (only spoken words, no emojis or
    titles, kind) and a user prompt listing names, occasion guidance, tone guidance, word range,
    language rule and the personal message.
22. **What is temperature?** — Randomness of word choice; 0.8 gives variety so Regenerate gives new
    wording.
23. **How do you stop very long or irrelevant output?** — `num_predict` caps tokens; the prompt
    sets a word range; `enforce_length` trims to whole sentences; `clean_llm_output` removes labels,
    notes, emojis and stage directions.
24. **How do the inputs affect the output?** — Each field becomes a line in the prompt; tests check
    the prompt changes when tone, language, occasion or length change.
25. **What if the model writes something inappropriate?** — The system prompt demands respectful,
    all-ages content; inputs pass a blocked-word check; and the user reviews and edits the script
    before anything is spoken. It is not a perfect filter, and I say so.
26. **Does the AI learn from users?** — No. The model is used only for inference; no training or
    data collection.
27. **Did you train the model?** — No, I use a pre-trained, instruction-tuned model; my work is the
    integration, prompt engineering, output handling and the whole application around it.

### LLM vs template
28. **How do you know which text came from the AI?** — The server returns `source: "llm"` or
    `"template"`; the UI shows a purple AI badge or an amber "Template fallback – NOT AI" badge
    with the reason, and the video itself says which one.
29. **When is the fallback used?** — Only if the LLM fails: Ollama not running, model missing,
    timeout (120 s), empty or too-short answer, or a server error.
30. **Is the template generator AI?** — No. It fills hand-written sentences with the names — ordinary
    programming. I never present it as AI.
31. **Why keep a fallback at all?** — So the rest of the system (voice, avatar, video) can still be
    demonstrated if the hardware cannot run the model.

### Text-to-speech
32. **How is speech generated?** — pyttsx3 drives the Windows SAPI5 speech engine and saves a WAV file.
33. **Is the TTS AI?** — In this project it uses classic (non-neural) SAPI5 desktop voices, so I
    don't claim it as AI.
34. **Why a separate process for TTS?** — SAPI5 is a COM component that can hang inside a
    long-running web server; a separate process is isolated and can be stopped by a timeout.
35. **Which languages are supported?** — English and Hinglish with any English voice; Hindi
    (Devanagari) only if a Hindi voice visible to SAPI5 is installed — the app detects this and
    disables Hindi otherwise.
36. **Why does it sound robotic?** — SAPI5 desktop voices are older synthesis technology; neural TTS
    like Piper would sound better and is a future improvement.

### Avatar, lip-sync, Canvas
37. **How is the avatar made?** — Drawn entirely in code with the Canvas 2D API — ellipses and
    Bézier curves — and redrawn about 60 times per second.
38. **How does the mouth move?** — The Web Audio Analyser measures the voice's loudness (RMS) every
    frame; louder means the mouth opens wider, with smoothing.
39. **Is that real lip-sync?** — It is approximate, amplitude-based synchronisation. Real lip-sync
    maps phonemes to mouth shapes (visemes); I state this limitation clearly.
40. **How would you implement phoneme-level lip-sync?** — Get phoneme timings (from the TTS engine's
    events or a forced aligner), map each phoneme to a viseme, and draw that mouth shape at that time.
41. **How is timing handled?** — The avatar follows real audio events (`play`, `pause`, `ended`) and
    the real audio's loudness, so it stays in sync with the actual playback; the recorder adds a
    0.9 s intro and 1.3 s outro around the measured audio duration.
42. **How do expressions work?** — Each expression is a set of target values (eyebrow height/tilt,
    smile, eye openness); the face eases toward them. "Auto" picks one from the tone.
43. **How does blinking work?** — A small timer: every 2–5 seconds the eyes close and open over ~280 ms.
44. **Why not a photorealistic avatar?** — It would need GPU deep-learning models, and realistic
    faces raise consent and deepfake concerns. A cartoon is honest, light and original.

### Recording, MediaRecorder, WebM
45. **How is the video created?** — `canvas.captureStream(30)` gives a video track, the Web Audio
    `MediaStreamDestination` gives an audio track, both go into one `MediaStream`, and
    `MediaRecorder` encodes it to WebM.
46. **Why does the audio get into the video?** — Because I record a real audio *track* from the Web
    Audio graph — not just an audio element playing beside the canvas.
47. **What is WebM?** — An open video container; here with VP9 video and Opus audio.
48. **How do you know the recording succeeded?** — Success is shown only in the recorder's `onstop`
    event after the file is assembled and checked to be non-empty; optional ffprobe confirms both
    tracks.
49. **Why WebM and not MP4?** — Chrome/Edge's MediaRecorder produces WebM. With FFmpeg installed,
    the gallery can create an MP4 copy.
50. **Why must the tab stay visible during recording?** — Browsers slow down animation in hidden
    tabs, which would make the recorded video stutter.
51. **Can the recording be faster than real time?** — Not with MediaRecorder; WebCodecs-based
    rendering could do that in future.

### Privacy, consent, security, ethics
52. **Where does user data go?** — Only to the local Flask server and local Ollama. Nothing is sent
    to the internet.
53. **Does local processing mean consent isn't needed?** — No. Using a real person's likeness or
    voice always needs their permission, wherever it is processed. That's why I use an original
    cartoon and do not allow photo upload or voice cloning.
54. **How do you disclose AI usage?** — Badges in the app, a consent checkbox, and a
    "computer-generated avatar" note plus the script source inside every video.
55. **What security measures did you add?** — Server-side validation, strict file-name whitelist
    (prevents path traversal), WebM signature check, 100 MB upload limit, no stack traces to users,
    server bound to localhost only.
56. **Could this be misused for deepfakes?** — The design avoids it: no real faces or voices, and
    visible disclosure. Any extension to real likeness would require explicit consent and labelling.

### Offline, cost, hardware
57. **Does it work offline?** — Yes, after installing packages and downloading the model, script,
    speech, animation and recording all work offline.
58. **What does it cost?** — Nothing. All tools are free; no subscriptions or API keys.
59. **What if the laptop is too slow?** — Generation may take longer; after 120 s it falls back to
    the labelled template. A smaller model (`qwen2.5:0.5b`) can be configured.
60. **How big is everything?** — Model 986 MB; Python packages a few tens of MB; Ollama itself
    needs a few GB of disk.

### Testing, limitations, future scope
61. **How did you test it?** — 166 automated pytest tests with mocks for Ollama and TTS (success,
    unavailable, timeout, empty, missing voice, bad uploads, path traversal), plus an optional
    Playwright browser test that records a real video and verifies its tracks with ffprobe.
62. **What are the limitations?** — Approximate lip-sync, robotic voices, small-model quality,
    Hindi depends on installed voices, WebM compatibility, real-time recording.
63. **Future scope?** — Viseme lip-sync, neural offline TTS, more avatars, subtitles, bigger
    models on better hardware, MP4 by default, local-network sharing.

### Follow-up questions (with reasoning)
* *"Why 1.5B and not 7B?"* → 7B needs ~4.7 GB download and much more RAM; too slow on typical
  student laptops without a GPU. Greetings are short, so 1.5B is enough.
* *"Why not streaming output?"* → Greetings are short; non-streaming keeps the code simple. Streaming
  would improve perceived speed and is a possible enhancement.
* *"What happens if two people use it at once?"* → It is designed as a single-user local app; Flask
  runs threaded, and Ollama queues requests.
* *"How do you handle a hung speech engine?"* → The worker process has a timeout; on expiry it is
  killed and the user sees a friendly error.
* *"Is pyttsx3 really offline?"* → Yes, SAPI5 voices are installed on Windows; no network calls.

---

## Answering honestly when something is incomplete or fails
* "That part is approximate — the mouth follows loudness, not individual sounds. Phoneme-level
  lip-sync is in my future scope."
* "The model can't run on this machine right now, so the app is using the template fallback, and
  as you can see it clearly says it's **not** AI-generated. Here's a video I generated earlier with
  the model."
* "Hindi speech needs a Hindi voice installed in Windows; this laptop doesn't have one, so I use
  Hinglish."
* "I haven't tested that scenario; based on the design I expect…, and here's how I would verify it."

Never claim a feature works if you haven't shown or tested it.
