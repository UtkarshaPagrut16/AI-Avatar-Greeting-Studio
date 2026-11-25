# Presentation Script (13 slides, about 10–12 minutes)

Tip: put the screenshots from `docs/screenshots/` and diagrams from `FLOWCHARTS.md` on your slides.

---

## Slide 1 — Title
**Slide points**
* PS 36 — AI Avatar Greeting Video Generator
* "AI Avatar Greeting Studio"
* Your name, roll number, guide's name, department, date

**Script:** "Good morning, respected jury members. I am presenting PS 36, the AI Avatar Greeting
Video Generator. My application, AI Avatar Greeting Studio, creates a short personalised greeting
video using a language model that runs entirely on my laptop."

---

## Slide 2 — Problem statement
**Slide points**
* Personal greetings feel generic as text
* Avatar video tools: paid, cloud-based, need GPUs
* Privacy risk: names and messages uploaded
* Ethical risk: cloning real faces/voices without consent

**Script:** "We all send birthday and thank-you messages, but plain text can feel generic. Talking
avatar services exist, but they are usually paid, run in the cloud — meaning our personal messages
go to someone else's servers — and some can clone a real person's face or voice without consent.
I wanted a free, private and responsible alternative."

---

## Slide 3 — Objectives
**Slide points**
1. LLM-generated, personalised script
2. Offline speech synthesis
3. Animated talking avatar
4. Downloadable video with audio
5. Honest labelling and consent
6. Easy setup on Windows 11, zero cost

**Script:** "My objectives follow the PS 36 guideline: generate the script with an LLM, synthesise
the voice, create an avatar video, handle timing and lip-sync limits, address consent for
likeness, and present the finished video — all free and easy to install."

---

## Slide 4 — Proposed solution
**Slide points**
* Form → local LLM script → editable preview
* Script → offline voice (.wav)
* Cartoon avatar speaks it in the browser
* Browser records animation + voice → WebM
* Template fallback, clearly labelled, if LLM unavailable

**Script:** "The user fills a short form. A local model writes the greeting, which the user can
edit or regenerate. The text becomes speech offline. My original cartoon avatar speaks it, and the
browser records the animation and the voice into a video. If the model isn't available, a template
fallback keeps the demo working, and it is clearly labelled as not AI."

---

## Slide 5 — System architecture
**Slide points:** architecture diagram (FLOWCHARTS.md §1): Browser ↔ Flask ↔ Ollama / pyttsx3 / output folder

**Script:** "On the left is the browser, with four JavaScript modules: the page logic, the avatar,
the voice player and the recorder. They talk over HTTP and JSON to a Flask server in Python. Flask
validates input, calls Ollama for the script, calls pyttsx3 for speech, and stores videos in a
local folder. Everything runs on 127.0.0.1 — this computer."

---

## Slide 6 — Technology stack
**Slide points**
| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| AI | Ollama + qwen2.5:1.5b (986 MB, Apache-2.0) |
| Speech | pyttsx3 + Windows SAPI5 voices |
| Frontend | HTML, CSS, JavaScript |
| Avatar | Canvas 2D API |
| Audio | Web Audio API |
| Video | captureStream + MediaRecorder → WebM |
| Testing | pytest (166 tests), Playwright (optional) |

**Script:** "I chose tools that are free, run offline and are simple to explain. No database, no
front-end framework and no paid service."

---

## Slide 7 — LLM-based script generation
**Slide points**
* System prompt: rules (only spoken words, no emojis/titles, respectful)
* User prompt: names, occasion & tone guidance, word range, language, personal message
* Temperature 0.8 → Regenerate gives variety
* Cleaning + length limit
* Errors → labelled template fallback

**Script:** "The key AI part is prompt engineering. I give the model a system prompt with strict
output rules and a user prompt that turns every form field into a clear instruction — for example,
'Funny: light-hearted with one gentle, clean joke.' Small models sometimes add titles or emojis, so
I clean the output and limit its length. If Ollama is off, the model is missing, or it times out,
the app uses templates and shows exactly why."

---

## Slide 8 — Speech synthesis and avatar animation
**Slide points**
* pyttsx3 → SAPI5 → .wav (separate worker process, timeout)
* Voice chosen by language; Hindi only if a Hindi voice exists
* Canvas avatar: blink, eye movement, expressions, waving, themed particles
* Mouth = voice loudness (Web Audio Analyser) → approximate lip-sync

**Script:** "Speech is created offline with pyttsx3. The avatar is drawn in code about sixty times
a second. It blinks, looks around, changes expression based on tone and waves hello and goodbye.
The mouth opens according to the loudness of the real audio. This is approximate lip-sync, not
phoneme-level, and I state that clearly."

---

## Slide 9 — Video recording and download
**Slide points**
* canvas.captureStream(30) → video track
* Web Audio MediaStreamDestination → audio track
* new MediaStream([video, audio]) → MediaRecorder (VP9 + Opus)
* Success only after `onstop` + size check → download, gallery

**Script:** "A common mistake is to play audio beside a canvas and expect it in the recording — it
won't be there. I route the voice through Web Audio to get a real audio track, combine it with the
canvas video track and record both with MediaRecorder. The app reports success only after the
recorder has stopped and the file is complete."

---

## Slide 10 — Live demonstration
**Slide points:** Priya · Rahul · Birthday · Friendly → Generate → Edit → Voice → Record → Download

**Script:** "Let me show you." *(Follow the demonstration script in JURY_PREPARATION.md.)*

---

## Slide 11 — Limitations and ethical considerations
**Slide points**
* Approximate lip-sync; robotic SAPI5 voices
* Small model can be generic; Hindi depends on installed voice
* WebM compatibility; real-time recording
* Ethics: original cartoon, no face/voice cloning, consent checkbox, on-video disclosure, local data

**Script:** "I want to be clear about limitations. On ethics: using someone's likeness needs their
consent — even locally — so I use an original cartoon, offer no photo upload, label every video as
computer-generated and keep all data on the computer."

---

## Slide 12 — Future scope
**Slide points**
* Phoneme/viseme lip-sync
* Neural offline TTS (e.g. Piper), better Hindi
* More avatars, subtitles
* Larger models with GPU; streaming text
* Automatic MP4; faster-than-real-time rendering

**Script:** "Next steps would be viseme-based lip-sync, more natural offline voices, more avatar
styles and subtitles, and automatic MP4 export."

---

## Slide 13 — Conclusion
**Slide points**
* Free, local, private greeting videos
* Genuine LLM + speech + animation + real video with audio
* Honest about AI, limitations and consent
* Thank you — questions?

**Script:** "To conclude, AI Avatar Greeting Studio shows that a small local language model and
standard browser technologies can create personalised greeting videos for free, privately and
responsibly. Thank you. I'm happy to take your questions."
