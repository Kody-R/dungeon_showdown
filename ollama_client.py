from __future__ import annotations
import json
from typing import Any

import requests


class OllamaClient:
    def __init__(self, model: str, base_url: str = "http://localhost:11434", timeout: int = 45, enabled: bool = True):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.enabled = enabled
        self.last_error = ""

    def generate(self, prompt: str, temperature: float = 0.8, max_tokens: int = 500, fallback: str = "") -> str:
        if not self.enabled:
            self.last_error = "Ollama disabled in settings."
            return fallback
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        try:
            response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            text = str(data.get("response", "")).strip()
            if not text:
                self.last_error = "Ollama returned an empty response."
                return fallback
            self.last_error = ""
            return text
        except (requests.RequestException, json.JSONDecodeError, ValueError) as exc:
            self.last_error = str(exc)
            return fallback

    def list_models(self) -> list[str]:
        if not self.enabled:
            self.last_error = "Ollama disabled in settings."
            return []
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=min(self.timeout, 8))
            response.raise_for_status()
            data = response.json()
            models = []
            for item in data.get("models", []):
                name = item.get("name")
                if name:
                    models.append(str(name))
            self.last_error = ""
            return sorted(models)
        except (requests.RequestException, json.JSONDecodeError, ValueError) as exc:
            self.last_error = str(exc)
            return []
