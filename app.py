"""
app.py - The Flask web server for AI Avatar Greeting Studio (PS 36).

Run it with:   python app.py      then open   http://127.0.0.1:5000

Pages and API routes
--------------------
GET    /                          main page (templates/index.html)
GET    /api/status                is Ollama running? is the model ready? which voices?
POST   /api/generate-script       form details -> greeting script (LLM or template)
POST   /api/tts                   script -> speech .wav file
GET    /api/videos                list saved greeting videos (gallery)
POST   /api/videos                upload a WebM recorded in the browser
DELETE /api/videos/<name>         delete a saved video
POST   /api/videos/<name>/mp4     optional MP4 copy (needs FFmpeg)
GET    /media/audio/<name>        serve a generated speech file
GET    /media/videos/<name>       serve / download a saved video
"""
import logging
import re

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.exceptions import HTTPException

import config
from services import tts_service, video_store
from services.llm_service import LLMError, OllamaClient
from services.script_generator import generate_script
from services.validators import ValidationError, validate_greeting_request, validate_script_text

AUDIO_NAME_RE = re.compile(r"^speech_[a-f0-9]{12}\.wav$")
log = logging.getLogger("greeting_studio")


def error_response(message, status=400, **extra):
    """Every API error has the same simple JSON shape: {ok: false, error: "..."}."""
    return jsonify({"ok": False, "error": message, **extra}), status


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024
    app.config["JSON_AS_ASCII"] = False

    # ------------------------------------------------------------------ pages
    @app.get("/")
    def index():
        return render_template(
            "index.html",
            occasions=config.OCCASIONS,
            tones=config.TONES,
            languages=config.LANGUAGES,
            lengths=list(config.LENGTHS),
            model_name=config.OLLAMA_MODEL,
        )

    # ----------------------------------------------------------------- status
    @app.get("/api/status")
    def status():
        llm = OllamaClient().status()
        tts = {"installed": tts_service.tts_library_installed(), "voices": [], "languages": {}}
        if tts["installed"]:
            try:
                voices = tts_service.list_voices()
                tts["voices"] = [{"id": v["id"], "name": v["name"], "lang": v["lang"]} for v in voices
                                 if v["lang"] in ("en", "hi")]
                tts["languages"] = tts_service.supported_languages(voices)
            except tts_service.TTSError as exc:
                tts["error"] = exc.user_message
        return jsonify({
            "ok": True,
            "llm": llm,
            "fallback_enabled": config.ALLOW_TEMPLATE_FALLBACK,
            "tts": tts,
            "ffmpeg": video_store.ffmpeg_path() is not None,
        })

    # -------------------------------------------------------- script (LLM)
    @app.post("/api/generate-script")
    def api_generate_script():
        try:
            details = validate_greeting_request(request.get_json(silent=True))
        except ValidationError as exc:
            return error_response("Please fix the highlighted fields.", 400, fields=exc.errors)
        try:
            result = generate_script(details)
        except LLMError as exc:  # only reached when fallback is switched off
            return error_response(f"{exc.reason} Template fallback is disabled.", 503)
        return jsonify({"ok": True, **result})

    # ------------------------------------------------------------ speech
    @app.post("/api/tts")
    def api_tts():
        data = request.get_json(silent=True) or {}
        language = str(data.get("language") or "en")
        if language not in config.LANGUAGES:
            return error_response("Unsupported language.", 400)
        try:
            script = validate_script_text(data.get("script"))
            result = tts_service.synthesize(script, language, voice_id=data.get("voice_id") or None)
        except ValidationError as exc:
            return error_response(next(iter(exc.errors.values())), 400)
        except tts_service.TTSVoiceMissingError as exc:
            return error_response(exc.detail or exc.user_message, 422)
        except tts_service.TTSError as exc:
            log.warning("TTS failed: %s", exc.detail)
            return error_response(exc.user_message, 500)
        return jsonify({"ok": True, **result})

    # ------------------------------------------------------------ videos
    @app.get("/api/videos")
    def api_list_videos():
        return jsonify({"ok": True, "videos": video_store.list_videos(),
                        "ffmpeg": video_store.ffmpeg_path() is not None})

    @app.post("/api/videos")
    def api_upload_video():
        try:
            info = video_store.save_uploaded_video(request.files.get("video"),
                                                   request.form.get("label", ""))
        except video_store.VideoError as exc:
            return error_response(str(exc), 400)
        return jsonify({"ok": True, "video": info}), 201

    @app.delete("/api/videos/<name>")
    def api_delete_video(name):
        try:
            video_store.delete_video(name)
        except video_store.VideoError as exc:
            return error_response(str(exc), 404)
        return jsonify({"ok": True})

    @app.post("/api/videos/<name>/mp4")
    def api_convert_mp4(name):
        try:
            url = video_store.convert_to_mp4(name)
        except video_store.VideoError as exc:
            return error_response(str(exc), 400)
        return jsonify({"ok": True, "mp4_url": url})

    # ------------------------------------------------------------- media
    @app.get("/media/audio/<name>")
    def media_audio(name):
        if not AUDIO_NAME_RE.match(name):
            return error_response("Not found.", 404)
        return send_from_directory(config.AUDIO_DIR, name, mimetype="audio/wav")

    @app.get("/media/videos/<name>")
    def media_video(name):
        if not video_store.is_safe_name(name):
            return error_response("Not found.", 404)
        download = request.args.get("download") == "1"
        return send_from_directory(config.VIDEO_DIR, name, as_attachment=download)

    # ------------------------------------------------------- error pages
    @app.errorhandler(413)
    def too_large(_error):
        return error_response(f"File is too large (limit {config.MAX_UPLOAD_MB} MB).", 413)

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith(("/api/", "/media/")):
            return error_response(error.description or error.name, error.code)
        return error

    @app.errorhandler(Exception)
    def unexpected_error(error):
        # Full details go to the terminal for the developer; the user only
        # sees a friendly message (no stack traces in the browser).
        log.exception("Unexpected error: %s", error)
        return error_response("Something went wrong on the server. Check the terminal window for details.", 500)

    return app


app = create_app()

if __name__ == "__main__":
    import sys
    import threading
    import webbrowser

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    url = f"http://{config.HOST}:{config.PORT}"
    if "--open" in sys.argv:  # run_windows.bat opens the browser automatically
        threading.Timer(2.0, lambda: webbrowser.open(url)).start()
    print("\n  AI Avatar Greeting Studio is starting...")
    print(f"  Open this address in Chrome or Edge:  {url}")
    print("  Keep this window open while you use the app. Press CTRL+C to stop.\n")
    app.run(host=config.HOST, port=config.PORT, debug=False, threaded=True)
