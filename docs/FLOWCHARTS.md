# Flowcharts (Mermaid)

These diagrams render on GitHub, in VS Code (with a Mermaid extension) or at <https://mermaid.live>
(paste the code — rendering happens in your browser).

## 1. Application architecture
```mermaid
flowchart LR
    subgraph Browser["Browser (Chrome / Edge)"]
        UI["index.html + style.css"]
        APPJS["app.js<br/>form, editor, gallery"]
        AV["avatar.js<br/>AvatarRenderer (Canvas)"]
        VO["voice.js<br/>VoicePlayer (Web Audio)"]
        REC["recorder.js<br/>GreetingRecorder (MediaRecorder)"]
    end
    subgraph Server["Flask server - app.py (127.0.0.1:5000)"]
        VAL["validators.py"]
        SG["script_generator.py"]
        LLM["llm_service.py"]
        TPL["template_generator.py<br/>(NOT AI)"]
        TTS["tts_service.py"]
        WRK["tts_worker.py<br/>(separate process)"]
        VS["video_store.py"]
    end
    OLL["Ollama 127.0.0.1:11434<br/>qwen2.5:1.5b"]
    SAPI["pyttsx3 + Windows SAPI5 voices"]
    FS[("output/ folder<br/>audio, videos")]

    UI --- APPJS
    APPJS -- "fetch JSON" --> Server
    APPJS --> AV
    APPJS --> VO
    APPJS --> REC
    VO -- "loudness" --> AV
    SG --> VAL
    SG --> LLM -- "HTTP /api/chat" --> OLL
    SG -- "on LLM error" --> TPL
    TTS --> WRK --> SAPI
    TTS --> FS
    VS --> FS
```

## 2. LLM-based greeting generation
```mermaid
sequenceDiagram
    actor User
    participant JS as app.js
    participant F as Flask (app.py)
    participant V as validators.py
    participant SG as script_generator.py
    participant O as Ollama + qwen2.5:1.5b
    User->>JS: Fill form, click Generate
    JS->>JS: quickValidate()
    JS->>F: POST /api/generate-script (JSON)
    F->>V: validate_greeting_request()
    V-->>F: cleaned details
    F->>SG: generate_script(details)
    SG->>SG: build_prompts() - system + user prompt
    SG->>O: POST /api/chat (temperature 0.8, num_predict 260)
    O-->>SG: {"message": {"content": "..."}}
    SG->>SG: clean_llm_output, ensure_personalised, enforce_length
    SG-->>F: {script, source: "llm", model, notice}
    F-->>JS: 200 JSON
    JS->>User: Script in editor + "AI-generated" badge
```

## 3. LLM failure and template fallback
```mermaid
flowchart TD
    A["generate_script(details)"] --> B["OllamaClient.chat()"]
    B -->|"connection refused"| E1["LLMUnavailableError"]
    B -->|"HTTP 404"| E2["LLMModelMissingError"]
    B -->|"over 120 s"| E3["LLMTimeoutError"]
    B -->|"empty / invalid JSON"| E4["LLMEmptyResponseError"]
    B -->|"text received"| C["clean_llm_output()"]
    C --> D{"5 or more words?"}
    D -->|"no"| E5["LLMError: too short"]
    D -->|"yes"| OK["source = llm<br/>purple AI badge"]
    E1 & E2 & E3 & E4 & E5 --> F{"ALLOW_TEMPLATE_FALLBACK?"}
    F -->|"yes"| T["generate_template_greeting()<br/>source = template<br/>amber NOT AI badge + reason"]
    F -->|"no"| X["HTTP 503 error message"]
```

## 4. Text-to-speech
```mermaid
flowchart TD
    A["Click Create voice"] --> B["POST /api/tts {script, language}"]
    B --> C["validate_script_text()"]
    C -->|"invalid"| R1["400 message"]
    C --> D{"pyttsx3 installed?"}
    D -->|"no"| R2["500: install pyttsx3"]
    D -->|"yes"| E["list_voices() (cached)"]
    E --> F["choose_voice(language)"]
    F -->|"no Hindi voice"| R3["422: use Hinglish"]
    F --> G["write script to output/tmp"]
    G --> H["subprocess: python -m services.tts_worker speak"]
    H -->|"timeout"| R4["500: took too long"]
    H -->|"exit code 3"| R5["500: engine error"]
    H --> I{"WAV larger than 44 bytes?"}
    I -->|"no"| R6["500: file empty"]
    I -->|"yes"| J["read duration with wave module"]
    J --> K["JSON {url, duration, voice_name}"]
    K --> L["VoicePlayer.load(url)"]
```

## 5. Avatar animation and recording
```mermaid
flowchart TD
    subgraph Loop["Every frame (requestAnimationFrame)"]
        U1["ease face toward expression"] --> U2["blink timer, eye movement"]
        U2 --> U3["mouth target = voice.level() ^ 0.8"]
        U3 --> U4["arm wave, particles"]
        U4 --> U5["draw background, avatar, card, disclosure"]
    end
    R0["Click Record (consent ticked)"] --> R1["checkSupport()"]
    R1 -->|"unsupported"| RE["error message"]
    R1 --> R2["voice.recordingTrack() - audio track"]
    R2 --> R3["canvas.captureStream(30) - video track"]
    R3 --> R4["new MediaStream([video, audio])"]
    R4 --> R5["MediaRecorder(vp9,opus).start(250)"]
    R5 --> R6["avatar.wave(); wait 900 ms"]
    R6 --> R7["voice.play(); setSpeaking(true)"]
    R7 --> R8["audio 'ended' then wave; wait 1300 ms"]
    R8 --> R9["recorder.stop()"]
    R9 --> R10["onstop: Blob from chunks"]
    R10 --> R11{"Blob at least 2000 bytes?"}
    R11 -->|"no"| RE2["error: empty recording"]
    R11 -->|"yes"| R12["success: preview + download"]
```

## 6. Video download and gallery
```mermaid
flowchart LR
    A["WebM Blob"] --> B["URL.createObjectURL()"]
    B --> C["video preview"]
    B --> D["a download = greeting_priya_birthday_DATE.webm"]
    D --> E["Downloads folder"]
    A --> F["POST /api/videos (multipart)"]
    F --> G{"size and WebM signature OK?"}
    G -->|"no"| H["400 error, download still works"]
    G -->|"yes"| I["save output/videos + .json label"]
    I --> J["optional ffprobe: video + audio?"]
    J --> K["Gallery: play, WebM, Make MP4 (FFmpeg), Delete"]
```

## 7. Error handling (overview)
```mermaid
flowchart TD
    REQ["Request from browser"] --> V{"Valid input?"}
    V -->|"no"| E400["400 + field messages"]
    V -->|"yes"| S["Service call"]
    S -->|"LLM error"| FB["Labelled template fallback"]
    S -->|"TTS error"| ETTS["Friendly TTS message; details in terminal"]
    S -->|"Video error"| EV["400/404 with reason"]
    S -->|"Unexpected exception"| E500["Generic 500 message; log.exception in terminal; no stack trace"]
    S -->|"OK"| OKR["200 JSON {ok: true}"]
    subgraph Browser
        BR1["api() wrapper turns errors into toasts"]
        BR2["Recorder: support check, play errors, timeout guard, cancel, empty-file check"]
    end
    E400 & ETTS & EV & E500 --> BR1
```
