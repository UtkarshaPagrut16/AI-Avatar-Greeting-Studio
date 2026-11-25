"""
Shared test setup. Every test gets its own empty output folder, so tests never
touch your real recordings. No model download, Ollama or speech engine is needed:
those parts are replaced by small fakes ("mocks").
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402


@pytest.fixture(autouse=True)
def temp_output(tmp_path, monkeypatch):
    for name in ("AUDIO_DIR", "VIDEO_DIR", "TMP_DIR"):
        folder = tmp_path / name.lower()
        folder.mkdir()
        monkeypatch.setattr(config, name, folder)
    monkeypatch.setattr(config, "ALLOW_TEMPLATE_FALLBACK", True)
    return tmp_path


@pytest.fixture
def client():
    from app import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def details():
    return {
        "recipient": "Priya", "sender": "Rahul", "occasion": "Birthday", "occasion_name": "",
        "tone": "Friendly", "language": "en", "length": "Short", "message": "",
    }


class FakeLLM:
    """Stands in for OllamaClient. Either returns `reply` or raises `error`."""

    def __init__(self, reply="", error=None, model="qwen2.5:1.5b"):
        self.reply, self.error, self.model = reply, error, model
        self.calls = []

    def chat(self, system_prompt, user_prompt, **_):
        self.calls.append((system_prompt, user_prompt))
        if self.error:
            raise self.error
        return self.reply


@pytest.fixture
def fake_llm():
    return FakeLLM


def make_wav(path, seconds=1.0, rate=22050):
    """Write a real (silent) WAV file, like the speech engine would."""
    import wave
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(b"\x00\x00" * int(rate * seconds))


@pytest.fixture
def wav_maker():
    return make_wav
