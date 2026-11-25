"""Tests for services/llm_service.py using a fake HTTP session (no real Ollama)."""
import pytest
import requests

from services.llm_service import (LLMEmptyResponseError, LLMError, LLMModelMissingError, LLMTimeoutError,
                                  LLMUnavailableError, OllamaClient)


class FakeResponse:
    def __init__(self, status=200, payload=None, bad_json=False):
        self.status_code, self.payload, self.bad_json = status, payload or {}, bad_json

    def json(self):
        if self.bad_json:
            raise ValueError("not json")
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(str(self.status_code))


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.sent = response, error, None

    def post(self, url, json=None, timeout=None):
        self.sent = {"url": url, "json": json, "timeout": timeout}
        if self.error:
            raise self.error
        return self.response

    def get(self, url, timeout=None):
        if self.error:
            raise self.error
        return self.response


def client_with(**kwargs):
    return OllamaClient(base_url="http://127.0.0.1:11434", model="qwen2.5:1.5b", timeout=5,
                        session=FakeSession(**kwargs))


def test_chat_success_returns_text_and_sends_correct_request():
    client = client_with(response=FakeResponse(payload={"message": {"content": "  Happy birthday, Priya!  "}}))
    assert client.chat("system", "user") == "Happy birthday, Priya!"
    sent = client.http.sent
    assert sent["url"].endswith("/api/chat")
    assert sent["json"]["model"] == "qwen2.5:1.5b"
    assert sent["json"]["stream"] is False
    assert sent["json"]["messages"][0] == {"role": "system", "content": "system"}
    assert sent["json"]["options"]["num_predict"] > 0


def test_runner_not_running_raises_unavailable():
    client = client_with(error=requests.exceptions.ConnectionError("refused"))
    with pytest.raises(LLMUnavailableError):
        client.chat("s", "u")


def test_timeout_raises_timeout_error():
    client = client_with(error=requests.exceptions.ReadTimeout("slow"))
    with pytest.raises(LLMTimeoutError):
        client.chat("s", "u")


def test_missing_model_404_raises_model_missing():
    client = client_with(response=FakeResponse(status=404, payload={"error": "model not found"}))
    with pytest.raises(LLMModelMissingError):
        client.chat("s", "u")


def test_server_error_raises_llm_error():
    client = client_with(response=FakeResponse(status=500))
    with pytest.raises(LLMError):
        client.chat("s", "u")


@pytest.mark.parametrize("payload", [{"message": {"content": ""}}, {"message": {"content": "   "}}, {}])
def test_empty_response_raises_empty_error(payload):
    client = client_with(response=FakeResponse(payload=payload))
    with pytest.raises(LLMEmptyResponseError):
        client.chat("s", "u")


def test_invalid_json_raises_empty_error():
    client = client_with(response=FakeResponse(bad_json=True))
    with pytest.raises(LLMEmptyResponseError):
        client.chat("s", "u")


def test_status_reports_model_ready():
    client = client_with(response=FakeResponse(payload={"models": [{"name": "qwen2.5:1.5b"}, {"name": "x:latest"}]}))
    assert client.status() == {"runner": True, "model_ready": True, "model": "qwen2.5:1.5b"}


def test_status_reports_model_missing():
    client = client_with(response=FakeResponse(payload={"models": [{"name": "llama3:8b"}]}))
    assert client.status()["model_ready"] is False


def test_status_when_ollama_off_never_raises():
    client = client_with(error=requests.exceptions.ConnectionError("refused"))
    assert client.status() == {"runner": False, "model_ready": False, "model": "qwen2.5:1.5b"}


def test_model_without_tag_matches_latest():
    client = OllamaClient(model="phi3", session=FakeSession())
    assert client.has_model(["phi3:latest"])
