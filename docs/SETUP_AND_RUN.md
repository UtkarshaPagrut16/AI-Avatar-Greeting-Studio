# Setup and Run Guide (Windows 11)

This guide assumes **no prior Python or Flask experience**. Follow the parts in order.
Time needed: about 15–30 minutes the first time (mostly downloads).

> **Two ways to set up:** Part A uses the one-click `run_windows.bat`. Part B shows the
> exact manual commands, in case the batch file fails or you want to understand each step.

---

## What you need

| Item | Required? | Size | Notes |
|---|---|---|---|
| Windows 11 (Windows 10 22H2+ also works) | ✅ | – | No administrator rights needed |
| Python 3.11 or 3.12 (3.9+ works) | ✅ | ~30 MB | From python.org |
| Google Chrome or Microsoft Edge | ✅ | – | Edge is already on Windows 11 |
| Ollama (local LLM runner) | ✅ for AI scripts | installer ~1 GB on disk | Without it, the labelled template fallback is used |
| Model `qwen2.5:1.5b` | ✅ for AI scripts | **986 MB download**, ~1.1 GB disk | Apache 2.0 license |
| FFmpeg | ❌ optional | ~100 MB | Only for MP4 copies; WebM works without it |
| Internet | Only during setup | – | Everything runs offline afterwards |

**Hardware for the LLM:** no graphics card needed (runs on the CPU). 8 GB RAM is recommended;
the model needs roughly 2 GB of free RAM while running. On a typical laptop CPU a greeting takes
roughly 5–30 seconds (this is an estimate; the very first request after starting is slower
because the model is loaded into memory).

---

## Step 1 — Install Python

1. Go to <https://www.python.org/downloads/> and download **Python 3.12** (Windows installer, 64-bit).
2. Run the installer. On the first screen **tick "Add python.exe to PATH"**, then click **Install Now**.
3. Check it: press `Win + R`, type `cmd`, press Enter, then type:
   ```cmd
   python --version
   ```
   You should see something like `Python 3.12.x`. (If you see nothing or the Microsoft Store
   opens, see TROUBLESHOOTING.md → *Python not found*.)

## Step 2 — Install Ollama (the local LLM runner)

1. Go to <https://ollama.com/download> and download **Ollama for Windows** (`OllamaSetup.exe`).
   No account or sign-in is needed. Alternatively, in PowerShell: `winget install Ollama.Ollama`
2. Run the installer. It installs for your user only (no admin rights). Ollama then runs in the
   background (look for the llama icon near the clock). Its local address is `http://localhost:11434`.
3. Check it in a **new** CMD window:
   ```cmd
   ollama --version
   ```

You do **not** need to download the model yet — `run_windows.bat` will ask you. Models are stored
in `C:\Users\<you>\.ollama`.

## Step 3 — Extract the ZIP

1. Right-click `AI_Avatar_Greeting_Studio.zip` → **Extract All…** → choose e.g. `C:\Projects` → **Extract**.
2. You now have `C:\Projects\AI_Avatar_Greeting_Studio\AI-Avatar-Greeting-Studio\` (Windows adds the
   outer folder). The **project folder** is the one that contains `app.py` and `run_windows.bat`.

> Tip: avoid putting the project inside OneDrive-synced folders; syncing can lock files.

## Step 4 — Open the project in VS Code (optional but recommended)

1. Install VS Code from <https://code.visualstudio.com/> (free).
2. **File → Open Folder…** → select the project folder (the one with `app.py`).
3. Install the **Python** extension when VS Code suggests it.
4. Open a terminal inside VS Code: **Terminal → New Terminal**. It opens in the project folder.

**Without VS Code:** open the project folder in File Explorer, click the address bar, type `cmd`,
press Enter. A Command Prompt opens **in the correct directory**. Check with `dir` — you should
see `app.py`.

---

## Part A — One-click setup with `run_windows.bat` (recommended)

Double-click `run_windows.bat` (or type `run_windows.bat` in the CMD window from Step 4).

It does the following, printing `[ OK ]`, `[WARN]` or `[FAIL]` for each item:

1. Finds Python (tries the `py` launcher, then `python`) and checks the version is 3.9+.
2. Creates a private virtual environment in `.venv` **only if it does not exist yet**.
3. Installs the packages from `requirements.txt` (Flask, requests, pyttsx3, pytest).
4. Runs `check_setup.py --interactive`, which:
   * shows your RAM,
   * checks Ollama is installed and running (offers to start it if it is installed but stopped),
   * checks whether `qwen2.5:1.5b` is downloaded — if not, **shows the download size, disk space,
     hardware needs and license and asks `Download qwen2.5:1.5b now? [y/N]`**. Nothing is
     downloaded unless you type `y`,
   * lists your English and Hindi speech voices,
   * checks for optional FFmpeg.
5. Starts the app and opens <http://127.0.0.1:5000> in your default browser.

**Keep the black window open** while using the app — it *is* the server. Closing it stops the app.

The batch file never edits system settings, never asks for administrator rights and never
overwrites your files or configuration. Running it again is safe and fast.

---

## Part B — Manual setup (exact commands, in order)

Open CMD **in the project folder** (Step 4), then run:

```cmd
:: 1. Create a virtual environment (a private folder of Python packages for this project)
python -m venv .venv

:: 2. Activate it - your prompt will start with (.venv)
.venv\Scripts\activate

:: 3. Install the Python packages
python -m pip install --upgrade pip
pip install -r requirements.txt

:: 4. Download the LLM (986 MB, one time, needs internet)
ollama pull qwen2.5:1.5b

:: 5. (Optional) quick test of the model in the terminal; type /bye to exit
ollama run qwen2.5:1.5b "Write a one-line birthday wish for Priya."

:: 6. Check everything
python check_setup.py

:: 7. Start the app
python app.py
```

Then open **<http://127.0.0.1:5000>** in Chrome or Edge.

> **PowerShell users:** if `.venv\Scripts\activate` shows "running scripts is disabled", either use
> CMD instead, or run `.venv\Scripts\python.exe app.py` directly (no activation needed), or run
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

**What is a virtual environment?** It is a folder (`.venv`) that holds this project's own copy of
Python packages, so they do not clash with other projects. "Activating" just tells the terminal to
use that folder's Python.

### Text-to-speech prerequisites
pyttsx3 uses the speech voices built into Windows (SAPI5), usually **Microsoft David** and
**Microsoft Zira** (English). Nothing extra is needed for English or Hinglish. `pip` installs
`pywin32` and `comtypes` automatically on Windows.

Optional extra voices: **Settings → Time & language → Speech → Manage voices → Add voices**.
Note that many newer Windows voices are "OneCore" voices that pyttsx3 (SAPI5) **cannot see**.
`check_setup.py` and the app's status chip show exactly which voices pyttsx3 found. If no Hindi
voice is listed, the **Hindi (Devanagari)** option is disabled and **Hinglish** is recommended.

### Optional: FFmpeg for MP4
```powershell
winget install Gyan.FFmpeg
```
Close and reopen the terminal afterwards. A **Make MP4** button then appears in the gallery.

---

## Using the app

### 1. Generate and edit a greeting
1. Type **Recipient** (e.g. `Priya`) and **Sender** (e.g. `Rahul`).
2. Choose **Occasion**. For *Festival* you can type the name (e.g. `Diwali`); for *Custom* you
   must describe it (e.g. `Farewell`).
3. Choose a **Tone**, **Language** and **Length**; optionally add a **Personal message**.
4. Click **✨ Generate greeting script**. With the LLM ready, the badge says
   **🤖 AI-generated · qwen2.5:1.5b**. If Ollama is not available, the badge says
   **📄 Template fallback – NOT AI** with the reason.
5. Edit the text freely. **✏️ Edited by you** appears. Click **↻ Regenerate** for a new version
   (the LLM gives different wording each time).

### 2. Generate and play speech
1. Click **🔊 Create voice**. A `.wav` file is created offline; the voice name and length appear.
2. Use **▶ Play**, **⏸ Pause**, **⏹ Stop**, **↺ Replay**. The avatar's mouth moves with the voice.
3. If you edit the script afterwards, the app warns you to create the voice again, so the speech
   always matches the text.

### 3. Animate and record the avatar
1. Optional: open **🎨 Expression and colours** to change expression, skin, hair or shirt colour.
2. Tick the **consent** box.
3. Click **● Record greeting video**. The avatar waves, speaks the greeting, waves goodbye.
   A progress bar shows the status. **Keep the tab visible** while recording (browsers slow down
   hidden tabs).
4. "✅ Recording finished successfully." appears only after the file is complete.

### 4. Download and play the video
* Click **⬇ Download video (.webm)**. The file goes to your *Downloads* folder, named like
  `greeting_priya_birthday_20261019-1730.webm`.
* Play it in **Chrome/Edge** (drag the file into a tab), **VLC**, or the Windows 11 Media Player.
* A copy is also kept in the **Saved greetings** gallery (`output\videos`). With FFmpeg installed,
  **Make MP4** creates an MP4 copy for phones/WhatsApp.

### Stopping and restarting
* **Stop:** click the black window and press `Ctrl + C` (or just close it).
* **Restart:** double-click `run_windows.bat` again, or in CMD:
  `.venv\Scripts\python.exe app.py`.
* Ollama keeps running in the background; that is normal. To quit it, right-click the llama icon
  near the clock → **Quit Ollama**.

---

## Running the automated tests
```cmd
run_tests.bat
```
or manually:
```cmd
.venv\Scripts\activate
python -m pytest -v
```
The 166 tests use fake ("mock") versions of Ollama and the speech engine, so they do **not**
need the model or speakers and finish in about a second.

Optional real-browser check (records a real video and inspects it; needs ~150 MB extra):
```cmd
pip install playwright
python -m playwright install chromium
:: start the app in another window first, then:
python tests\browser_check.py --headed
```

---

## Using the template fallback (when the LLM cannot run)
If Ollama is not installed, not running, the model is missing, the computer is too slow (timeout
after 120 s), or the model returns an empty answer, the app automatically uses **fixed templates**.
It always shows:
* the amber badge **📄 Template fallback – NOT AI**,
* the reason (e.g. "Ollama is not running on this computer"),
* the note "Script: template (not AI)" inside the video itself.

Template text is **never** presented as AI-generated. Everything else (voice, avatar, video) works
the same. To turn the fallback off (so errors are shown instead), set
`ALLOW_TEMPLATE_FALLBACK=0` before starting (`set ALLOW_TEMPLATE_FALLBACK=0` in CMD).

## Changing settings without editing code
Set environment variables in CMD before `python app.py`, for example:
```cmd
set OLLAMA_MODEL=qwen2.5:0.5b
set LLM_TIMEOUT_SECONDS=180
set GREETING_PORT=5050
python app.py
```
All settings and defaults are listed in `config.py`.

## If something goes wrong
See **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** — it covers Python, virtual environments,
Flask, Ollama, model download, RAM, voices, browser audio, recording and playback.
