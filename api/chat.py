"""HD Research Hub Chatbot API — Vercel Serverless Function.

RAG chatbot grounded in our research corpus. Uses NVIDIA NIM
(Nemotron) for inference. Every answer cites papers from PubMed.
"""

import json
import os
import re
from http.server import BaseHTTPRequestHandler
from pathlib import Path

import urllib.request
import urllib.parse

NIM_API_KEY = os.environ.get("NVIDIA_NIM_API_KEY", "")
NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NIM_MODEL = "nvidia/llama-3.1-nemotron-nano-8b-v1"

# Load corpus at cold start
CORPUS = {}
CORPUS_PATH = Path(__file__).parent.parent / "data" / "corpus.json"
if CORPUS_PATH.exists():
    with open(CORPUS_PATH) as f:
        CORPUS = json.load(f)

# Load experiment results
EXPERIMENT_PATH = Path(__file__).parent.parent / "data" / "experiment_001_results.json"
EXPERIMENT = {}
if EXPERIMENT_PATH.exists():
    with open(EXPERIMENT_PATH) as f:
        EXPERIMENT = json.load(f)

# Load trial data
DATA_PATH = Path(__file__).parent.parent / "data" / "data.json"
SITE_DATA = {}
if DATA_PATH.exists():
    with open(DATA_PATH) as f:
        SITE_DATA = json.load(f)


def find_relevant_papers(query, max_papers=8):
    """Simple keyword search over the corpus."""
    query_terms = set(re.findall(r'\w+', query.lower()))
    scored = []

    for pmid, paper in CORPUS.get("papers", {}).items():
        text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
        analysis = paper.get("analysis", {})
        if analysis:
            text += f" {analysis.get('finding', '')} {' '.join(analysis.get('targets', []))} {' '.join(analysis.get('compounds', []))}"

        score = sum(1 for term in query_terms if term in text)
        if score > 0:
            scored.append((score, paper))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:max_papers]]


def build_context(query):
    """Build RAG context from corpus, experiments, and trial data."""
    papers = find_relevant_papers(query)

    context_parts = []

    # Relevant papers
    if papers:
        context_parts.append("RELEVANT RESEARCH PAPERS:")
        for p in papers:
            analysis = p.get("analysis", {})
            entry = f"- [{p.get('pmid','')}] {p.get('title','')}"
            if analysis:
                entry += f"\n  Finding: {analysis.get('finding', '')}"
                targets = analysis.get("targets", [])
                compounds = analysis.get("compounds", [])
                if targets:
                    entry += f"\n  Targets: {', '.join(targets)}"
                if compounds:
                    entry += f"\n  Compounds: {', '.join(compounds)}"
            context_parts.append(entry)

    # Hypotheses from experiment
    hypotheses = EXPERIMENT.get("hypotheses", [])
    if hypotheses:
        context_parts.append("\nOUR AI-GENERATED DRUG REPURPOSING HYPOTHESES:")
        for h in hypotheses:
            if isinstance(h, dict) and "drug" in h:
                context_parts.append(
                    f"- {h['drug']} → {h.get('hd_target', '?')} (score: {h.get('score', '?')}/100): {h.get('rationale', '')}"
                )

    # Trial stats
    stats = SITE_DATA.get("stats", {})
    if stats:
        context_parts.append(f"\nCURRENT HD TRIAL STATS: {stats.get('trials_count', 0)} active trials, {stats.get('recruiting_count', 0)} recruiting, {stats.get('total_enrollment', 0)} patients enrolled")

    return "\n".join(context_parts)


def call_nim(messages):
    """Call NVIDIA NIM API."""
    payload = json.dumps({
        "model": NIM_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1024,
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        NIM_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {NIM_API_KEY}",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]


SYSTEM_PROMPT = """You are the HD Research Hub assistant — an AI research companion for Huntington's Disease.

ROLE: Help visitors understand HD research using data from our corpus of analyzed PubMed papers, clinical trials, and AI-generated drug repurposing hypotheses.

RULES:
1. ALWAYS ground your answers in the provided context (papers, trials, hypotheses). Cite PubMed IDs when referencing papers.
2. NEVER give medical advice. If someone asks about their personal health, direct them to HDSA (hdsa.org) or their healthcare provider.
3. Be educational and hopeful — focus on progress and opportunities, not doom.
4. When you don't know something or it's not in the context, say so honestly.
5. Keep answers concise — 2-3 paragraphs max unless the user asks for detail.
6. For drug questions, clarify that our hypotheses are AI-generated and unvalidated.
7. End EVERY response with: "This is AI-generated research analysis, not medical advice."

TONE: Curious data scientist explaining findings to a smart friend. Accessible. No jargon without explanation."""


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length))
            user_message = body.get("message", "").strip()

            if not user_message:
                self._respond(400, {"error": "No message provided"})
                return

            if not NIM_API_KEY:
                self._respond(500, {"error": "NIM API key not configured"})
                return

            # Build RAG context
            context = build_context(user_message)

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Research context:\n{context}\n\nUser question: {user_message}"},
            ]

            # Handle conversation history
            history = body.get("history", [])
            if history:
                # Insert history between system and current message
                full_messages = [messages[0]]
                for h in history[-6:]:  # Last 3 exchanges
                    full_messages.append(h)
                full_messages.append(messages[1])
                messages = full_messages

            response = call_nim(messages)

            self._respond(200, {
                "response": response,
                "papers_cited": len(find_relevant_papers(user_message)),
                "corpus_size": len(CORPUS.get("papers", {})),
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
