"""
llm_service.py - Talks to the local LLM runner (Ollama).

Ollama runs on this computer and listens on http://127.0.0.1:11434.
We send it a JSON request over HTTP and it answers with the text that the
model (qwen2.5:1.5b by default) generated. Nothing leaves the computer.

Ollama API endpoints used:
    GET  /api/tags   -> list of models that are downloaded locally
    POST /api/chat   -> send system + user messages, receive the reply
"""
import requests

import config


class LLMError(Exception):
    """Base class for every LLM problem. `reason` is a short user-friendly text."""

    reason = "The local LLM could not generate a greeting."


class LLMUnavailableError(LLMError):
    reason = "Ollama is not running on this computer (could not connect to it)."


class LLMModelMissingError(LLMError):
    reason = "The language model is not downloaded yet."


class LLMTimeoutError(LLMError):
    reason = "The local LLM took too long to answer."


class LLMEmptyResponseError(LLMError):
    reason = "The local LLM returned an empty answer."


class OllamaClient:
    """Very small client for the Ollama HTTP API."""

    def __init__(self, base_url=None, model=None, timeout=None, session=None):
        self.base_url = (base_url or config.OLLAMA_URL).rstrip("/")
        self.model = model or config.OLLAMA_MODEL
        self.timeout = timeout or config.LLM_TIMEOUT_SECONDS
        self.http = session or requests  # tests can pass a fake session

    # ------------------------------------------------------------------ status
    def list_models(self):
        """Return names of downloaded models. Raises LLMUnavailableError if Ollama is off."""
        try:
            response = self.http.get(f"{self.base_url}/api/tags", timeout=3)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as exc:
            raise LLMUnavailableError(str(exc)) from exc
        except ValueError as exc:  # response was not JSON
            raise LLMUnavailableError("Unexpected reply from Ollama.") from exc
        return [m.get("name", "") for m in data.get("models", [])]

    def has_model(self, names=None):
        """True if our model (e.g. 'qwen2.5:1.5b') is in the downloaded list."""
        names = names if names is not None else self.list_models()
        wanted = self.model if ":" in self.model else self.model + ":latest"
        return wanted in names

    def status(self):
        """Small dictionary for the UI status bar. Never raises."""
        try:
            names = self.list_models()
        except LLMError:
            return {"runner": False, "model_ready": False, "model": self.model}
        return {"runner": True, "model_ready": self.has_model(names), "model": self.model}

    # -------------------------------------------------------------- generation
    def chat(self, system_prompt, user_prompt, temperature=None, max_tokens=None):
        """Send one conversation to the model and return its reply text."""
        payload = {
            "model": self.model,
            "stream": False,              # wait for the full answer
            "keep_alive": "10m",          # keep the model in RAM for 10 minutes
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "temperature": config.LLM_TEMPERATURE if temperature is None else temperature,
                "num_predict": max_tokens or config.LLM_MAX_TOKENS,
                "top_p": 0.9,
            },
        }
        try:
            response = self.http.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
        except requests.exceptions.Timeout as exc:
            raise LLMTimeoutError(str(exc)) from exc
        except requests.exceptions.ConnectionError as exc:
            raise LLMUnavailableError(str(exc)) from exc
        except requests.exceptions.RequestException as exc:
            raise LLMError(str(exc)) from exc

        if response.status_code == 404:
            # Ollama answers 404 when the requested model is not downloaded.
            raise LLMModelMissingError(f"Model '{self.model}' not found. Run: ollama pull {self.model}")
        if response.status_code >= 400:
            raise LLMError(f"Ollama returned HTTP {response.status_code}.")

        try:
            data = response.json()
        except ValueError as exc:
            raise LLMEmptyResponseError("Reply was not valid JSON.") from exc

        text = (data.get("message") or {}).get("content", "")
        if not text or not text.strip():
            raise LLMEmptyResponseError("Model reply was empty.")
        return text.strip()
