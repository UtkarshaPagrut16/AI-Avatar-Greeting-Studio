"""Tests for the Flask routes in app.py (LLM, speech engine and FFmpeg are mocked)."""
import pytest

import app as app_module
from services import tts_service, video_store
from services.llm_service import LLMTimeoutError

FORM = {"recipient": "Priya", "sender": "Rahul", "occasion": "Birthday", "tone": "Friendly",
        "language": "en", "length": "Short", "message": "See you soon"}
WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 5000   # starts like a real WebM file


class FakeClient:
    model = "qwen2.5:1.5b"

    def __init__(self, reply=None, error=None):
        self.reply, self.error = reply, error

    def chat(self, *_args, **_kwargs):
        if self.error:
            raise self.error
        return self.reply

    def status(self):
        return {"runner": True, "model_ready": True, "model": self.model}


def use_llm(monkeypatch, **kwargs):
    import services.script_generator as sg
    monkeypatch.setattr(sg, "OllamaClient", lambda: FakeClient(**kwargs))


# ------------------------------------------------------------ startup / pages
def test_app_starts_and_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "AI Avatar Greeting Studio" in html
    for occasion in ("Birthday", "Anniversary", "Congratulations", "Thank You", "Welcome", "Festival", "Custom"):
        assert f'value="{occasion}"' in html
    assert 'id="avatarCanvas"' in html and 'id="recordBtn"' in html


def test_static_files_are_served(client):
    for path in ("/static/js/app.js", "/static/js/avatar.js", "/static/js/recorder.js",
                 "/static/js/voice.js", "/static/css/style.css", "/static/img/logo.svg"):
        assert client.get(path).status_code == 200, path


def test_status_endpoint(client, monkeypatch):
    monkeypatch.setattr(app_module, "OllamaClient", FakeClient)
    monkeypatch.setattr(tts_service, "tts_library_installed", lambda: True)
    monkeypatch.setattr(tts_service, "list_voices", lambda force=False: [
        {"id": "z", "name": "Zira English", "lang": "en", "indian_english": False}])
    data = client.get("/api/status").get_json()
    assert data["llm"]["model_ready"] is True
    assert data["tts"]["languages"] == {"en": True, "hinglish": True, "hi": False}


def test_status_when_tts_missing(client, monkeypatch):
    monkeypatch.setattr(app_module, "OllamaClient", FakeClient)
    monkeypatch.setattr(tts_service, "tts_library_installed", lambda: False)
    data = client.get("/api/status").get_json()
    assert data["tts"]["installed"] is False


# --------------------------------------------------------- script generation
def test_generate_script_with_llm(client, monkeypatch):
    use_llm(monkeypatch, reply="Happy birthday, Priya! Wishing you joy, cake and laughter today. See you soon. Love, Rahul.")
    data = client.post("/api/generate-script", json=FORM).get_json()
    assert data["ok"] and data["source"] == "llm" and "Priya" in data["script"]


def test_generate_script_fallback_is_disclosed(client, monkeypatch):
    use_llm(monkeypatch, error=LLMTimeoutError("slow"))
    data = client.post("/api/generate-script", json=FORM).get_json()
    assert data["source"] == "template"
    assert "NOT written by an AI model" in data["notice"]
    assert "took too long" in data["fallback_reason"]


def test_generate_script_fallback_disabled_returns_503(client, monkeypatch):
    import config
    monkeypatch.setattr(config, "ALLOW_TEMPLATE_FALLBACK", False)
    use_llm(monkeypatch, error=LLMTimeoutError("slow"))
    response = client.post("/api/generate-script", json=FORM)
    assert response.status_code == 503
    assert response.get_json()["ok"] is False


@pytest.mark.parametrize("body", [None, {}, {**FORM, "recipient": ""}, {**FORM, "occasion": "Nope"},
                                  {**FORM, "message": "m" * 400}])
def test_generate_script_rejects_invalid_input(client, body):
    response = client.post("/api/generate-script", json=body) if body is not None else \
        client.post("/api/generate-script", data="not json", content_type="text/plain")
    assert response.status_code == 400
    data = response.get_json()
    assert data["ok"] is False and data["fields"]


# ------------------------------------------------------------------ speech
def test_tts_success(client, monkeypatch):
    monkeypatch.setattr(tts_service, "synthesize", lambda script, language, voice_id=None: {
        "filename": "speech_0123456789ab.wav", "url": "/media/audio/speech_0123456789ab.wav",
        "duration": 3.2, "voice_name": "Zira", "voice_id": "z"})
    data = client.post("/api/tts", json={"script": "Hello Priya", "language": "en"}).get_json()
    assert data["ok"] and data["duration"] == 3.2


def test_tts_missing_dependency(client, monkeypatch):
    monkeypatch.setattr(tts_service, "tts_library_installed", lambda: False)
    response = client.post("/api/tts", json={"script": "Hello Priya", "language": "en"})
    assert response.status_code == 500
    assert "pyttsx3" in response.get_json()["error"]


def test_tts_engine_failure_has_friendly_message(client, monkeypatch):
    def broken(*_a, **_k):
        raise tts_service.TTSFailedError("COM error 0x8004 internal detail")
    monkeypatch.setattr(tts_service, "synthesize", broken)
    data = client.post("/api/tts", json={"script": "Hello", "language": "en"}).get_json()
    assert data["error"] == tts_service.TTSFailedError.user_message
    assert "0x8004" not in data["error"]


def test_tts_missing_voice_is_422(client, monkeypatch):
    def no_voice(*_a, **_k):
        raise tts_service.TTSVoiceMissingError("No Hindi voice is installed.")
    monkeypatch.setattr(tts_service, "synthesize", no_voice)
    response = client.post("/api/tts", json={"script": "नमस्ते", "language": "hi"})
    assert response.status_code == 422 and "Hindi" in response.get_json()["error"]


@pytest.mark.parametrize("body", [{"script": "", "language": "en"}, {"script": "Hi", "language": "xx"}])
def test_tts_rejects_bad_input(client, body):
    assert client.post("/api/tts", json=body).status_code == 400


def test_audio_route_blocks_bad_names(client):
    assert client.get("/media/audio/..%2Fconfig.py").status_code == 404
    assert client.get("/media/audio/secret.txt").status_code == 404


# ------------------------------------------------------------------ videos
def upload(client, data=WEBM, label="Birthday for Priya"):
    from io import BytesIO
    return client.post("/api/videos", data={"video": (BytesIO(data), "greeting.webm"), "label": label},
                       content_type="multipart/form-data")


def test_upload_list_download_delete(client, monkeypatch):
    monkeypatch.setattr(video_store, "inspect_streams", lambda path: {"video": True, "audio": True})
    response = upload(client)
    assert response.status_code == 201
    video = response.get_json()["video"]
    assert video_store.is_safe_name(video["name"])
    assert video["streams"] == {"video": True, "audio": True}

    listed = client.get("/api/videos").get_json()["videos"]
    assert [v["name"] for v in listed] == [video["name"]]
    assert listed[0]["label"] == "Birthday for Priya"

    download = client.get(video["url"] + "?download=1")
    assert download.status_code == 200
    assert "attachment" in download.headers["Content-Disposition"]
    assert download.data == WEBM

    assert client.delete(f"/api/videos/{video['name']}").get_json()["ok"]
    assert client.get("/api/videos").get_json()["videos"] == []


@pytest.mark.parametrize("data", [b"", b"\x1a\x45\xdf\xa3", b"MZ" + b"\x00" * 5000])
def test_upload_rejects_empty_or_non_webm(client, data):
    response = upload(client, data=data)
    assert response.status_code == 400
    assert response.get_json()["ok"] is False


def test_upload_without_file(client):
    response = client.post("/api/videos", data={}, content_type="multipart/form-data")
    assert response.status_code == 400


def test_video_routes_block_path_traversal(client):
    assert client.get("/media/videos/..%2F..%2Fapp.py").status_code == 404
    assert client.delete("/api/videos/../../app.py").status_code in (404, 405)
    assert client.delete("/api/videos/greeting_x.webm").status_code == 404


def test_mp4_without_ffmpeg_gives_clear_error(client, monkeypatch):
    monkeypatch.setattr(video_store, "inspect_streams", lambda path: None)
    monkeypatch.setattr(video_store, "ffmpeg_path", lambda: None)
    name = upload(client).get_json()["video"]["name"]
    response = client.post(f"/api/videos/{name}/mp4")
    assert response.status_code == 400
    assert "FFmpeg is not installed" in response.get_json()["error"]


def test_unknown_api_route_returns_json_404(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404 and response.get_json()["ok"] is False


def test_unexpected_error_hides_stack_trace(client, monkeypatch):
    def crash(*_a, **_k):
        raise RuntimeError("secret internal detail")
    monkeypatch.setattr(video_store, "list_videos", crash)
    response = client.get("/api/videos")
    assert response.status_code == 500
    body = response.get_data(as_text=True)
    assert "secret internal detail" not in body and "Traceback" not in body
