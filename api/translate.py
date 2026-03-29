"""Sarvam AI Translation — translates chatbot responses to Indian languages.

Supports all 22 Indian languages via Sarvam Translate API.
Used by the chatbot to detect language and respond in the user's language.
"""

import json
import os
import re
from http.server import BaseHTTPRequestHandler

import urllib.request

SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")
SARVAM_URL = "https://api.sarvam.ai/translate"

# Language detection patterns (simple keyword-based)
LANG_PATTERNS = {
    "hi-IN": r'[\u0900-\u097F]',  # Devanagari (Hindi, Marathi)
    "ta-IN": r'[\u0B80-\u0BFF]',  # Tamil
    "te-IN": r'[\u0C00-\u0C7F]',  # Telugu
    "bn-IN": r'[\u0980-\u09FF]',  # Bengali
    "kn-IN": r'[\u0C80-\u0CFF]',  # Kannada
    "ml-IN": r'[\u0D00-\u0D7F]',  # Malayalam
    "gu-IN": r'[\u0A80-\u0AFF]',  # Gujarati
    "pa-IN": r'[\u0A00-\u0A7F]',  # Punjabi (Gurmukhi)
    "od-IN": r'[\u0B00-\u0B7F]',  # Odia
    "ur-IN": r'[\u0600-\u06FF]',  # Urdu (Arabic script)
}

# Supported language codes
SUPPORTED_LANGS = {
    "hi-IN": "Hindi", "ta-IN": "Tamil", "te-IN": "Telugu",
    "bn-IN": "Bengali", "mr-IN": "Marathi", "kn-IN": "Kannada",
    "ml-IN": "Malayalam", "gu-IN": "Gujarati", "pa-IN": "Punjabi",
    "od-IN": "Odia", "ur-IN": "Urdu", "as-IN": "Assamese",
    "en-IN": "English",
}


def detect_language(text):
    """Detect if text contains Indian language scripts."""
    for lang_code, pattern in LANG_PATTERNS.items():
        if re.search(pattern, text):
            # Special case: Devanagari is shared by Hindi and Marathi
            # Default to Hindi
            return lang_code
    return "en-IN"


def translate(text, source_lang, target_lang):
    """Translate text using Sarvam AI API."""
    if not SARVAM_API_KEY:
        return text  # Pass through if no key

    if source_lang == target_lang:
        return text

    payload = json.dumps({
        "input": text,
        "source_language_code": source_lang,
        "target_language_code": target_lang,
        "mode": "formal",
        "model": "mayura:v2",
        "enable_preprocessing": True,
    }).encode("utf-8")

    req = urllib.request.Request(
        SARVAM_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "api-subscription-key": SARVAM_API_KEY,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("translated_text", text)
    except Exception as e:
        print(f"Sarvam translate error: {e}")
        return text


class handler(BaseHTTPRequestHandler):
    """Standalone translate endpoint for client-side use."""

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length))

            text = body.get("text", "").strip()
            target = body.get("target", "hi-IN")
            source = body.get("source", "en-IN")

            if not text:
                self._respond(400, {"error": "No text provided"})
                return

            if not SARVAM_API_KEY:
                self._respond(200, {"translated_text": text, "note": "Sarvam API key not configured"})
                return

            translated = translate(text, source, target)
            self._respond(200, {
                "translated_text": translated,
                "source_language": source,
                "target_language": target,
            })

        except Exception as e:
            self._respond(500, {"error": str(e)})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _respond(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
