"""Tests for services/tts_service.py. The speech engine itself is mocked."""
import subprocess
import types

import pytest

from services import tts_service
from services.tts_worker import describe_language, is_indian_english

VOICES = [
    {"id": "zira", "name": "Microsoft Zira Desktop - English (United States)", "lang": "en", "indian_english": False},
    {"id": "heera", "name": "Microsoft Heera Desktop - English (India)", "lang": "en", "indian_english": True},
]
HINDI = {"id": "kalpana", "name": "Microsoft Kalpana - Hindi (India)", "lang": "hi", "indian_english": False}


@pytest.fixture(autouse=True)
def reset_cache():
    tts_service._voice_cache.update(time=0.0, voices=None)


def test_describe_language_for_windows_voice_names():
    assert describe_language("TTS_MS_EN-US_ZIRA_11.0", "Microsoft Zira Desktop - English (United States)", []) == "en"
    assert describe_language("TTS_MS_HI-IN_KALPANA", "Microsoft Kalpana Desktop - Hindi (India)", []) == "hi"
    assert describe_language("x", "Deutsch", [b"de"]) == "other"
    assert is_indian_english("TTS_MS_EN-IN_HEERA", "Microsoft Heera - English (India)")


def test_choose_voice_rules():
    assert tts_service.choose_voice("en", VOICES)["id"] == "zira"
    assert tts_service.choose_voice("hinglish", VOICES)["id"] == "heera"   # Indian English preferred
    assert tts_service.choose_voice("hi", VOICES + [HINDI])["id"] == "kalpana"
    assert tts_service.choose_voice("en", VOICES, preferred_id="heera")["id"] == "heera"


def test_hindi_without_hindi_voice_is_a_clear_error():
    with pytest.raises(tts_service.TTSVoiceMissingError) as info:
        tts_service.choose_voice("hi", VOICES)
    assert "Hinglish" in str(info.value)


def test_no_voices_at_all():
    with pytest.raises(tts_service.TTSVoiceMissingError):
        tts_service.choose_voice("en", [])


def test_supported_languages():
    assert tts_service.supported_languages(VOICES) == {"en": True, "hinglish": True, "hi": False}
    assert tts_service.supported_languages(VOICES + [HINDI])["hi"] is True


def test_missing_pyttsx3(monkeypatch):
    monkeypatch.setattr(tts_service, "tts_library_installed", lambda: False)
    with pytest.raises(tts_service.TTSUnavailableError):
        tts_service.synthesize("Hello", "en")
    with pytest.raises(tts_service.TTSUnavailableError):
        tts_service.list_voices()


def test_synthesize_success(monkeypatch, wav_maker):
    monkeypatch.setattr(tts_service, "tts_library_installed", lambda: True)
    monkeypatch.setattr(tts_service, "list_voices", lambda force=False: VOICES)

    def fake_worker(args, timeout):
        out = args[args.index("--out") + 1]
        wav_maker(out, seconds=2.0)
        assert args[args.index("--voice-id") + 1] == "zira"
        return {"ok": True}

    monkeypatch.setattr(tts_service, "_run_worker", fake_worker)
    result = tts_service.synthesize("Happy birthday Priya", "en")
    assert result["url"].startswith("/media/audio/speech_") and result["url"].endswith(".wav")
    assert result["duration"] == 2.0
    assert result["voice_name"].startswith("Microsoft Zira")


def test_synthesize_empty_file_is_an_error(monkeypatch):
    monkeypatch.setattr(tts_service, "tts_library_installed", lambda: True)
    monkeypatch.setattr(tts_service, "list_voices", lambda force=False: VOICES)
    monkeypatch.setattr(tts_service, "_run_worker", lambda args, timeout: {"ok": True})  # writes nothing
    with pytest.raises(tts_service.TTSFailedError):
        tts_service.synthesize("Hello", "en")


def _fake_completed(code, stdout="", stderr=""):
    return types.SimpleNamespace(returncode=code, stdout=stdout, stderr=stderr)


def test_worker_reports_missing_library(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _fake_completed(2, '{"ok": false, "error": "pyttsx3 is not installed"}'))
    with pytest.raises(tts_service.TTSUnavailableError):
        tts_service._run_worker(["voices"], timeout=5)


def test_worker_engine_failure(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _fake_completed(3, '{"ok": false, "error": "COMError"}'))
    with pytest.raises(tts_service.TTSFailedError) as info:
        tts_service._run_worker(["voices"], timeout=5)
    assert "COMError" in info.value.detail


def test_worker_timeout(monkeypatch):
    def slow(*a, **k):
        raise subprocess.TimeoutExpired(cmd="tts", timeout=5)
    monkeypatch.setattr(subprocess, "run", slow)
    with pytest.raises(tts_service.TTSTimeoutError):
        tts_service._run_worker(["voices"], timeout=5)


def test_wav_duration(tmp_path, wav_maker):
    path = tmp_path / "a.wav"
    wav_maker(path, seconds=1.5)
    assert tts_service.wav_duration_seconds(path) == 1.5
    (tmp_path / "bad.wav").write_bytes(b"nope")
    assert tts_service.wav_duration_seconds(tmp_path / "bad.wav") is None
