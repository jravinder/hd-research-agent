"""Local preview server for the HD Research Hub chatbot.

Serves the static site (chat.html, shared.*, etc.) AND wraps the Vercel
serverless `api/chat.py` handler so the local site behaves like production —
but talks to the local-or-Jetson Ollama Gemma 4 instead of AI Studio.

Usage:
    HD_LLM_BACKEND=ollama python3 scripts/local_server.py 8780

Then open http://localhost:8780/chat.html
"""

from __future__ import annotations

import importlib
import io
import mimetypes
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
os.chdir(REPO)
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "api"))

# Force a backend that doesn't need GEMINI_API_KEY for the local preview.
os.environ.setdefault("HD_LLM_BACKEND", "ollama")

# Import the Vercel handler. It's a BaseHTTPRequestHandler subclass.
chat_module = importlib.import_module("api.chat")
ChatHandler = chat_module.handler


class CombinedHandler(BaseHTTPRequestHandler):
    """Dispatch /api/chat to api/chat.handler; serve other paths as static files."""

    def do_OPTIONS(self):
        if self.path.startswith("/api/chat"):
            return self._proxy_to_chat("OPTIONS")
        self.send_response(204)
        self.end_headers()

    def do_POST(self):
        if self.path.startswith("/api/chat"):
            return self._proxy_to_chat("POST")
        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/chat"):
            self.send_response(405)
            self.end_headers()
            return
        # Map / to /chat.html for convenience.
        path = self.path.split("?")[0]
        if path in ("/", ""):
            path = "/chat.html"
        local = (REPO / path.lstrip("/")).resolve()
        if not str(local).startswith(str(REPO)):
            self.send_response(403); self.end_headers(); return
        if not local.is_file():
            self.send_response(404); self.end_headers()
            self.wfile.write(b"not found")
            return
        ctype, _ = mimetypes.guess_type(local.name)
        ctype = ctype or "application/octet-stream"
        data = local.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _proxy_to_chat(self, method: str):
        """Invoke the api/chat.handler over an in-process stream."""
        handler = _DelegatingChatHandler(self.rfile, self.wfile, self.headers,
                                         self.path, self.command,
                                         self.client_address)
        if method == "POST":
            handler.do_POST()
        else:
            handler.do_OPTIONS()


class _DelegatingChatHandler(ChatHandler):
    """Re-use the chat.py handler's do_POST/do_OPTIONS by spoofing the
    BaseHTTPRequestHandler initializer. We bypass __init__ because we already
    have a live connection from CombinedHandler."""

    def __init__(self, rfile, wfile, headers, path, command, client_address):
        # Intentionally skip BaseHTTPRequestHandler.__init__
        self.rfile = rfile
        self.wfile = wfile
        self.headers = headers
        self.path = path
        self.command = command
        self.request_version = "HTTP/1.1"
        self.requestline = f"{command} {path} HTTP/1.1"
        self.client_address = client_address

    def log_request(self, code="-", size="-"):  # quiet
        pass

    def log_message(self, fmt, *args):  # quiet
        pass


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8780
    server = HTTPServer(("127.0.0.1", port), CombinedHandler)
    print(f"serving HD Research Hub preview on http://localhost:{port}/chat.html")
    print(f"backend: HD_LLM_BACKEND={os.environ.get('HD_LLM_BACKEND')}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
