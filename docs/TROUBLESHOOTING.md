# Troubleshooting

First step for almost any problem: run the setup checker in the project folder
```cmd
.venv\Scripts\python.exe check_setup.py
```
and read the `[FAIL]` / `[WARN]` lines. Also look at the **black terminal window** — the full
error is printed there (the browser shows only a short message).

---

## Python and dependency installation
| Problem | Fix |
|---|---|
| `'python' is not recognized` or the Microsoft Store opens | Reinstall Python from python.org and tick **Add python.exe to PATH**. Or use the launcher: `py -3 --version`. Turn off the Store alias: Settings → Apps → Advanced app settings → App execution aliases → switch off `python.exe` / `python3.exe`. |
| Python older than 3.9 | Install Python 3.12. |
| `pip install` fails with network/SSL errors | Check internet; try again; on college Wi-Fi with a proxy, try a mobile hotspot. |
| `pywin32` / `comtypes` errors on install | `pip install --upgrade pip` then `pip install -r requirements.txt` again. |
| `ModuleNotFoundError: No module named 'flask'` | You are not using the project's environment. Use `.venv\Scripts\python.exe app.py` or activate `.venv` first. |

## Virtual environments
| Problem | Fix |
|---|---|
| `.venv\Scripts\activate` — "running scripts is disabled" (PowerShell) | Use CMD instead, or run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or skip activation and call `.venv\Scripts\python.exe` directly. |
| venv creation fails | Make sure the folder is not read-only or inside a synced/locked location; move the project to `C:\Projects`. |
| Broken environment | Close the app, delete the `.venv` folder, run `run_windows.bat` again (it rebuilds it). |
| Moved the project folder and the venv stopped working | Delete `.venv` and run `run_windows.bat` again (venvs are tied to their path). |

## Flask startup
| Problem | Fix |
|---|---|
| `Address already in use` / port 5000 busy | Another copy is running — close it. Or `set GREETING_PORT=5050` and open `http://127.0.0.1:5050`. |
| Browser shows "This site can't be reached" | The terminal window was closed or crashed. Start the app again and keep the window open. |
| Page loads without styles | Hard refresh: `Ctrl + F5`. |
| Windows Firewall prompt | The app only listens on 127.0.0.1; you may click Cancel — it still works locally. |

## Installing and starting Ollama
| Problem | Fix |
|---|---|
| `'ollama' is not recognized` | Install from <https://ollama.com/download>, then open a **new** terminal. The checker also looks in `%LOCALAPPDATA%\Programs\Ollama`. |
| Status chip: "Ollama not running" | Start **Ollama** from the Start menu (llama icon appears near the clock), or run `ollama serve` in a separate window. |
| Port 11434 in use | Another Ollama is already running — that's fine. If another program uses it, close it. |

## Downloading and loading the model
| Problem | Fix |
|---|---|
| Chip says model not downloaded | `ollama pull qwen2.5:1.5b` (986 MB). Check with `ollama list`. |
| Download stops/fails | Re-run the same command — it resumes. Ensure ~2 GB free disk. |
| Not enough disk on C: | Set a user environment variable `OLLAMA_MODELS` to a folder on another drive, quit and restart Ollama, then pull again. |
| Want a different model | `set OLLAMA_MODEL=qwen2.5:0.5b` before starting the app, and `ollama pull qwen2.5:0.5b`. Check its license first. |

## Insufficient RAM, slow inference, model errors
| Problem | Fix |
|---|---|
| First generation very slow | Normal: the model is loading into RAM. Later requests are faster (kept loaded for 10 minutes). Do a warm-up generation before demos. |
| Always slow / template fallback with "took too long" | Close browsers tabs and heavy apps; plug in the charger (power-saving slows the CPU); increase `set LLM_TIMEOUT_SECONDS=240`; or use `qwen2.5:0.5b`. |
| "model requires more system memory" in Ollama | Free RAM (close apps) or use the 0.5B model. |
| Output is odd, too long or in the wrong language | Click Regenerate, or edit the script. Small models are imperfect. You can lower `LLM_TEMPERATURE` (e.g. 0.6) for more predictable text. |
| Hindi output weak | 1.5B models are weaker in Hindi; prefer Hinglish or English, and edit the text. |

## Offline operation
* After setup, turn off Wi-Fi and test: generation, voice, recording should all work.
* `pip install` needs internet only when packages are missing; `run_windows.bat` continues
  offline if they are already installed.
* If the fallback appears offline, Ollama is not running — offline is not the cause.

## TTS and voice problems
| Problem | Fix |
|---|---|
| "pyttsx3 is not installed" | `.venv\Scripts\python.exe -m pip install pyttsx3` |
| "speech engine reported an error" | Run `.venv\Scripts\python.exe -m services.tts_worker voices` to see the real error. Reinstall: `pip install --force-reinstall pyttsx3 pywin32 comtypes`. Restart the PC once after installing pywin32. |
| Speech took too long | Very long scripts or a busy PC; shorten the script; set `TTS_TIMEOUT_SECONDS=180`. |
| Hindi disabled ("no voice installed") | Install a Hindi voice (Settings → Time & language → Speech / Language → Hindi → speech). Many new voices are OneCore-only and invisible to pyttsx3; if Hindi still isn't listed, use **Hinglish**. |
| Wrong voice or speed | Change `TTS_RATE` (e.g. `set TTS_RATE=150`). Voice choice rules are in `choose_voice()` in `services/tts_service.py`. |
| Names pronounced oddly | Edit the script spelling phonetically (e.g. "Pree-ya") — it only affects speech. |

## Browser audio playback
| Problem | Fix |
|---|---|
| No sound | Check system volume and the browser tab isn't muted (right-click tab → Unmute site). Use Chrome or Edge. |
| "Could not play audio" | Click on the page once, then Play again (browsers block audio before a user click). |
| Avatar mouth doesn't move | Make sure audio is actually playing; refresh the page (`Ctrl + F5`) and create the voice again. |

## Recording, download and video playback
| Problem | Fix |
|---|---|
| Record button disabled | Create the voice for the **current** script and tick the consent box. |
| "This browser does not support MediaRecorder" | Use the latest Chrome or Edge. |
| Video stutters or "recording came out empty" | Keep the tab visible and in front during recording; close other heavy apps. |
| Downloaded video has no sound | Confirm sound in the preview first; if the preview has sound, the file does too — try playing it in Chrome or VLC. With FFmpeg installed, the gallery shows "✓ video + audio". |
| WebM won't open | Drag the file into Chrome/Edge, or install VLC (free). For phones/WhatsApp, install FFmpeg and use **Make MP4**. |
| Video length shows 0:00 or seeks badly in some players | A known property of MediaRecorder WebM files (no duration in the header). Use Chrome/VLC, or make an MP4 copy. |
| Gallery save failed | The download still works. Check disk space and the terminal message. |
| "FFmpeg is not installed" | Optional: `winget install Gyan.FFmpeg`, then restart the terminal and the app. |

## Still stuck?
1. Run `python -m pytest` — if tests fail, the installation is incomplete.
2. Delete `.venv`, run `run_windows.bat` again.
3. Note the exact error text from the terminal and search it, or ask your guide.
