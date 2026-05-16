"""LLM interface for HD Research Agent — Gemma 4 across two backends.

Backends:
  - `ollama`   : Ollama on Jetson AGX Orin or localhost. Used by the offline
                 agent pipeline. Vision + native tool calling on `gemma4:latest`.
  - `aistudio` : Google AI Studio / Gemini API. Used by the live serverless
                 chatbot (`api/chat.py`) because Vercel can't reach the LAN
                 Jetson. Model: `gemma-4-31b-it`.

Backend is selected by env `HD_LLM_BACKEND` (default `ollama`). The same four
public entry points work on both:

  - ask(prompt, system=...) -> str
  - ask_json(prompt, system=...) -> dict          (backwards compat for pipeline)
  - ask_vision(prompt, images, system=...) -> str (multimodal)
  - ask_with_tools(prompt, tools, system=...) -> (text, tool_calls)
                                                  where tool_calls is a list of
                                                  {"name": str, "args": dict}

The pipeline imports the first two; api/chat.py uses all four. The Kaggle
notebook can import the whole module via `from src.llm import *`.

No litellm. No streaming. We hit Ollama's native /api/chat (avoiding the known
Gemma 4 tool-calling bug on Ollama's OpenAI-compatible streaming path).
"""

from __future__ import annotations

import base64
import json
import os
import re
from typing import Any

import requests


# -------- Configuration ---------------------------------------------------- #

BACKEND = os.environ.get("HD_LLM_BACKEND", "ollama").lower()

# Ollama
OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("HD_AGENT_MODEL", "gemma4:latest")

# AI Studio (Gemini API serving Gemma 4)
AISTUDIO_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
AISTUDIO_MODEL = os.environ.get("HD_AISTUDIO_MODEL", "gemma-4-31b-it")
AISTUDIO_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Back-compat alias for callers that imported the old constant
DEFAULT_MODEL = OLLAMA_MODEL


# -------- Helpers ---------------------------------------------------------- #

def _image_to_b64(image: Any) -> str:
    """Accept bytes, a base64 string, or a filesystem path; return base64 string."""
    if isinstance(image, bytes):
        return base64.b64encode(image).decode("ascii")
    if isinstance(image, str):
        if os.path.exists(image):
            with open(image, "rb") as f:
                return base64.b64encode(f.read()).decode("ascii")
        # Assume already a base64 string (strip data: URL prefix if present)
        if image.startswith("data:"):
            return image.split(",", 1)[1]
        return image
    raise TypeError(f"unsupported image type: {type(image)}")


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


# -------- Ollama backend --------------------------------------------------- #

def _ollama_chat(messages: list[dict], temperature: float = 0.3,
                 tools: list[dict] | None = None, model: str | None = None) -> dict:
    """POST to Ollama /api/chat. Non-streaming. Returns the response JSON."""
    payload: dict[str, Any] = {
        "model": model or OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if tools:
        payload["tools"] = tools
    resp = requests.post(f"{OLLAMA_BASE}/api/chat", json=payload, timeout=180)
    resp.raise_for_status()
    return resp.json()


def _ollama_ask(prompt: str, system: str = "", temperature: float = 0.3,
                model: str | None = None) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    data = _ollama_chat(messages, temperature=temperature, model=model)
    return data["message"]["content"].strip()


def _ollama_vision(prompt: str, images: list[Any], system: str = "",
                   temperature: float = 0.3, model: str | None = None) -> str:
    """Ollama vision via /api/chat. The user message carries `images` (base64)."""
    b64_images = [_image_to_b64(im) for im in images]
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt, "images": b64_images})
    data = _ollama_chat(messages, temperature=temperature, model=model)
    return data["message"]["content"].strip()


def _ollama_tools(prompt: str, tools: list[dict], system: str = "",
                  temperature: float = 0.3, model: str | None = None
                  ) -> tuple[str, list[dict]]:
    """Ollama native tool calling. Returns (text, tool_calls)."""
    # Ollama tool format: [{"type": "function", "function": {name, description, parameters}}]
    ollama_tools = [{"type": "function", "function": t} for t in tools]
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    data = _ollama_chat(messages, temperature=temperature,
                        tools=ollama_tools, model=model)
    msg = data.get("message", {})
    text = (msg.get("content") or "").strip()
    raw_calls = msg.get("tool_calls", []) or []
    calls = []
    for c in raw_calls:
        fn = c.get("function", {})
        args = fn.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        calls.append({"name": fn.get("name", ""), "args": args})
    return text, calls


# -------- AI Studio backend ------------------------------------------------ #

def _aistudio_generate(contents: list[dict], system: str = "",
                       temperature: float = 0.3, tools: list[dict] | None = None,
                       model: str | None = None) -> dict:
    """POST to Gemini API generateContent. Returns the raw response JSON."""
    if not AISTUDIO_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")
    url = f"{AISTUDIO_BASE}/models/{model or AISTUDIO_MODEL}:generateContent?key={AISTUDIO_KEY}"
    payload: dict[str, Any] = {
        "contents": contents,
        "generationConfig": {"temperature": temperature},
    }
    if system:
        # Gemma models on AI Studio do not all support systemInstruction;
        # prepend system text to the first user message instead.
        if contents and contents[0].get("role") == "user":
            first_parts = contents[0]["parts"]
            first_parts.insert(0, {"text": f"[System]\n{system}\n\n[User]\n"})
    if tools:
        payload["tools"] = [{"functionDeclarations": tools}]
    resp = requests.post(url, json=payload, timeout=180,
                         headers={"Content-Type": "application/json"})
    resp.raise_for_status()
    return resp.json()


def _aistudio_text_from_response(data: dict) -> str:
    """Extract concatenated text from candidates[0].content.parts[*].text."""
    cands = data.get("candidates") or []
    if not cands:
        return ""
    parts = cands[0].get("content", {}).get("parts", []) or []
    return "".join(p.get("text", "") for p in parts if "text" in p).strip()


def _aistudio_calls_from_response(data: dict) -> list[dict]:
    """Extract function calls from candidates[0].content.parts[*].functionCall."""
    cands = data.get("candidates") or []
    if not cands:
        return []
    parts = cands[0].get("content", {}).get("parts", []) or []
    calls = []
    for p in parts:
        fc = p.get("functionCall")
        if fc:
            calls.append({"name": fc.get("name", ""), "args": fc.get("args", {}) or {}})
    # Fallback: some Gemma deployments emit a textual tool-use protocol like
    # ```tool_code\n<name>(<args>)\n``` — parse if no structured call.
    if not calls:
        text = _aistudio_text_from_response(data)
        for m in re.finditer(r"```tool_code\s*\n([\w_]+)\((.*?)\)\s*\n```", text, re.DOTALL):
            name = m.group(1)
            args_src = m.group(2).strip()
            args: dict = {}
            for kv in re.finditer(r"(\w+)\s*=\s*(\"[^\"]*\"|\d+|true|false|null)", args_src):
                k = kv.group(1)
                v: Any = kv.group(2)
                if v.startswith('"'):
                    v = v[1:-1]
                elif v in ("true", "false"):
                    v = (v == "true")
                elif v == "null":
                    v = None
                else:
                    try:
                        v = int(v)
                    except ValueError:
                        pass
                args[k] = v
            calls.append({"name": name, "args": args})
    return calls


def _aistudio_ask(prompt: str, system: str = "", temperature: float = 0.3,
                  model: str | None = None) -> str:
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    data = _aistudio_generate(contents, system=system, temperature=temperature, model=model)
    return _aistudio_text_from_response(data)


def _aistudio_vision(prompt: str, images: list[Any], system: str = "",
                     temperature: float = 0.3, model: str | None = None) -> str:
    parts: list[dict] = [{"text": prompt}]
    for im in images:
        b64 = _image_to_b64(im)
        parts.append({"inlineData": {"mimeType": "image/png", "data": b64}})
    contents = [{"role": "user", "parts": parts}]
    data = _aistudio_generate(contents, system=system, temperature=temperature, model=model)
    return _aistudio_text_from_response(data)


def _aistudio_tools(prompt: str, tools: list[dict], system: str = "",
                    temperature: float = 0.3, model: str | None = None
                    ) -> tuple[str, list[dict]]:
    contents = [{"role": "user", "parts": [{"text": prompt}]}]
    data = _aistudio_generate(contents, system=system, temperature=temperature,
                              tools=tools, model=model)
    text = _aistudio_text_from_response(data)
    calls = _aistudio_calls_from_response(data)
    return text, calls


# -------- Public entry points (backend-agnostic) -------------------------- #

def ask(prompt: str, system: str = "", model: str | None = None,
        temperature: float = 0.3) -> str:
    """Text → text. Backend selected by HD_LLM_BACKEND."""
    if BACKEND == "aistudio":
        return _aistudio_ask(prompt, system=system, temperature=temperature, model=model)
    return _ollama_ask(prompt, system=system, temperature=temperature, model=model)


def ask_json(prompt: str, system: str = "", model: str | None = None) -> dict:
    """Text → parsed JSON. Kept for backwards compatibility with the pipeline."""
    sys_with_json = (system or "") + "\nYou MUST respond with valid JSON only. No markdown, no explanation."
    text = ask(prompt, system=sys_with_json, model=model, temperature=0.1)
    return json.loads(_strip_code_fence(text))


def ask_vision(prompt: str, images: list[Any], system: str = "",
               model: str | None = None, temperature: float = 0.3) -> str:
    """(Text + images) → text. images can be bytes, base64 strings, or file paths."""
    if BACKEND == "aistudio":
        return _aistudio_vision(prompt, images, system=system,
                                temperature=temperature, model=model)
    return _ollama_vision(prompt, images, system=system,
                          temperature=temperature, model=model)


def ask_with_tools(prompt: str, tools: list[dict], system: str = "",
                   model: str | None = None, temperature: float = 0.3
                   ) -> tuple[str, list[dict]]:
    """(Text + tool schemas) → (text, tool_calls).

    `tools` is a list of function declarations in the shared shape:
        {"name": "search_papers",
         "description": "...",
         "parameters": {"type": "object", "properties": {...}, "required": [...]}}

    Returns final text and a list of tool calls the model wants run:
        [{"name": "search_papers", "args": {"query": "ASO huntingtin"}}, ...]
    The caller is responsible for executing the tools and (optionally) feeding
    the results back via a follow-up `ask()` call to compose the final answer.
    """
    if BACKEND == "aistudio":
        return _aistudio_tools(prompt, tools, system=system,
                               temperature=temperature, model=model)
    return _ollama_tools(prompt, tools, system=system,
                         temperature=temperature, model=model)
