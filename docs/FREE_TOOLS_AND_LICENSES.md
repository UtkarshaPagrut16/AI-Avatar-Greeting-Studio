# Free Tools and Licenses

**"Free to download"** means you pay nothing. **"Open source"** means the source code is published
under a license that lets you study, modify and share it (with conditions). Some tools here are
free but *not* open source (e.g. the Windows speech voices). All tools listed are free of charge.

License information below was taken from each package's published metadata or official page at the
time of building (October 2026). Licenses can change in new versions — check again before any
commercial use. This is not legal advice.

## 1. Python packages (installed by `requirements.txt`)
| Package | Purpose | License | Open source? |
|---|---|---|---|
| Flask 3.x | Web framework | BSD-3-Clause | ✅ |
| Werkzeug (Flask dependency) | HTTP utilities | BSD-3-Clause | ✅ |
| Jinja2 (Flask dependency) | HTML templates | BSD-3-Clause | ✅ |
| MarkupSafe, itsdangerous, click, blinker | Flask dependencies | BSD-3-Clause / BSD / MIT | ✅ |
| requests 2.x | HTTP client for Ollama | Apache-2.0 | ✅ |
| urllib3, idna, charset-normalizer, certifi | requests dependencies | MIT / BSD-3-Clause / MIT / MPL-2.0 | ✅ |
| pyttsx3 2.9x | Offline text-to-speech wrapper | MPL-2.0 | ✅ |
| pywin32 (Windows only, via pyttsx3) | Windows COM access | PSF license | ✅ |
| comtypes (Windows only, via pyttsx3) | COM access | MIT | ✅ |
| pytest 8+/9 (+ pluggy, iniconfig, packaging, pygments) | Testing | MIT (+ MIT / MIT / Apache-2.0 or BSD-2 / BSD-2) | ✅ |
| playwright (optional, browser check only) | Browser automation | Apache-2.0 | ✅ |

## 2. Programs
| Tool | Purpose | License | Notes |
|---|---|---|---|
| Python 3 | Runtime | PSF License | Open source |
| Ollama | Local LLM runner | MIT | Open source; free, no account needed |
| Windows SAPI5 speech engine & voices (Zira, David, …) | Speech | Part of Microsoft Windows (proprietary) | Free with Windows, not open source |
| Google Chrome / Microsoft Edge | Run the app, record video | Proprietary freeware (built on open-source Chromium, BSD-style) | Free |
| FFmpeg / ffprobe (optional) | MP4 conversion, stream check | LGPL-2.1+ or GPL, depending on the build (e.g. Gyan.dev full builds are GPL-3.0) | Open source |
| VLC (optional, playback) | Play WebM/MP4 | GPL-2.0+ (core LGPL) | Open source |
| VS Code (optional) | Editor | Microsoft product license (built from MIT-licensed source "Code - OSS") | Free |

## 3. The AI model
| Item | Details |
|---|---|
| Ollama name | `qwen2.5:1.5b` |
| Original model | Qwen2.5-1.5B-Instruct, by the Qwen team, Alibaba Cloud |
| Parameters | 1.54 billion |
| Format in Ollama | GGUF, Q4_K_M 4-bit quantisation, **986 MB** download |
| Languages | 29+ (including English and Chinese; Hindi works but with lower quality in a model this small) |
| **License** | **Apache License 2.0** (per the Ollama library page: all Qwen2.5 sizes except 3B and 72B use Apache 2.0) |
| Commercial use | Apache-2.0 permits commercial use, modification and redistribution, with attribution and license notice; no warranty. |
| ⚠ Caution | Other sizes differ: **qwen2.5:3b** and **72b** use Qwen's own license with extra conditions. If you change `OLLAMA_MODEL`, check that model's license first. |

The model weights are **not** included in the ZIP; they are downloaded by Ollama from the Ollama
library when you run `ollama pull qwen2.5:1.5b`.

## 4. Assets created for this project
| Asset | Origin | License |
|---|---|---|
| Cartoon avatar (drawn in `static/js/avatar.js`) | Original, drawn in code for this project | Same as the project code |
| Logo (`static/img/logo.svg`) | Original | Same as the project code |
| Backgrounds, confetti, hearts, sparkles | Drawn in code | Same as the project code |
| Screenshots (`docs/screenshots/`) | Captured from this app during automated testing | Same as the project code |
| Fonts | System fonts only (Segoe UI on Windows); no font files bundled | — |

No third-party images, icons, fonts, sounds or videos are bundled. Emoji characters in the UI are
rendered by the operating system's emoji font.

## 5. Offline vs internet
| Component | Needs internet? |
|---|---|
| Installing Python, Ollama, VS Code | Yes, once |
| `pip install -r requirements.txt` | Yes, once (offline afterwards if packages are already installed) |
| `ollama pull qwen2.5:1.5b` | Yes, once (986 MB) |
| Generating scripts with the LLM | **No** — inference is local |
| Template fallback | No |
| Text-to-speech (SAPI5 voices) | No |
| Avatar animation, recording, download | No |
| Gallery, MP4 conversion (FFmpeg) | No |
| Optional Playwright browser check (installing Chromium) | Yes, once |

**No feature requires internet after installation**, and no personal data is sent anywhere.

## 6. Project code license
The project's own code was written for this academic project. If you publish it, add a license
of your choice (for example MIT) and keep the third-party license notices above.
