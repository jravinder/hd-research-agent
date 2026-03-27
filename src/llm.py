"""LLM interface for HD Research Agent. Uses Ollama API directly (no litellm dependency)."""

import json
import os
from typing import Optional

import requests


OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("HD_AGENT_MODEL", "llama3.1:8b")


def ask(prompt: str, system: str = "", model: str = DEFAULT_MODEL, temperature: float = 0.3) -> str:
    """Send a prompt to Ollama and return the response text."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = requests.post(
        f"{OLLAMA_BASE}/api/chat",
        json={
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def ask_json(prompt: str, system: str = "", model: str = DEFAULT_MODEL) -> dict:
    """Send a prompt and parse the response as JSON."""
    system_with_json = system + "\nYou MUST respond with valid JSON only. No markdown, no explanation."
    text = ask(prompt, system=system_with_json, model=model, temperature=0.1)
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    return json.loads(text)
