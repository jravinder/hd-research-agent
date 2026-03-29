"""HD Research Hub Chatbot API — Vercel Serverless Function.

RAG chatbot grounded in our research corpus. Uses NVIDIA NIM
(Nemotron) for inference. Every answer cites papers from PubMed.
Supports Indian languages via Sarvam AI translation.
"""

import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

# Import Sarvam translate
sys.path.insert(0, str(Path(__file__).parent))
from translate import detect_language, translate as sarvam_translate, SUPPORTED_LANGS
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

# Load knowledge base (full text chunks)
KB = {}
KB_PATH = Path(__file__).parent.parent / "data" / "knowledge_base.json"
if KB_PATH.exists():
    with open(KB_PATH) as f:
        KB = json.load(f)

# Load trial data
DATA_PATH = Path(__file__).parent.parent / "data" / "data.json"
SITE_DATA = {}
if DATA_PATH.exists():
    with open(DATA_PATH) as f:
        SITE_DATA = json.load(f)


def find_relevant_chunks(query, max_chunks=10):
    """Search the full-text knowledge base for relevant chunks."""
    query_terms = set(re.findall(r'\w+', query.lower()))
    # Remove common stop words
    stop = {'the','a','an','is','are','was','were','in','on','at','to','for','of','and','or','with','that','this','what','how','why','can','do','does'}
    query_terms -= stop

    scored = []
    for chunk in KB.get("chunks", []):
        text = chunk.get("text", "").lower()
        title = chunk.get("title", "").lower()
        combined = f"{title} {text}"

        score = sum(1 for term in query_terms if term in combined)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:max_chunks]]


def find_relevant_papers(query, max_papers=8):
    """Search corpus for relevant papers (fallback if KB is empty)."""
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
    """Build RAG context from knowledge base, corpus, experiments, and trial data."""
    context_parts = []

    # Full-text knowledge base chunks (primary source)
    chunks = find_relevant_chunks(query)
    if chunks:
        context_parts.append("RELEVANT RESEARCH (from full-text papers):")
        for c in chunks:
            pmid = c.get("pmid", "")
            section = c.get("section", "")
            title = c.get("title", "")[:60]
            text = c.get("text", "")[:800]
            context_parts.append(f"- [{pmid}] {title} | Section: {section}\n  {text}")

    # Fall back to corpus abstracts if KB is empty
    if not chunks:
        papers = find_relevant_papers(query)
        if papers:
            context_parts.append("RELEVANT RESEARCH PAPERS (abstracts):")
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


# Medical advice patterns to intercept before hitting the LLM
MEDICAL_ADVICE_PATTERNS = [
    "should i take", "should i stop taking", "should i start",
    "can i take", "is it safe to take", "what dose", "what dosage",
    "my doctor", "my neurologist", "my symptoms",
    "i have huntington", "i was diagnosed", "i tested positive",
    "should i get tested", "should i get genetic",
    "am i at risk", "will i get", "will my child",
    "what treatment should", "what drug should", "what medicine",
    "how long do i have", "life expectancy",
    "cure for huntington", "is there a cure",
    "prescribe", "prescription", "medication for me",
    "side effects for me", "my side effects",
]

MEDICAL_REDIRECT = (
    "I understand this is deeply personal, and I want to make sure you get the right support. "
    "I'm an AI research tool — I can explain what's happening in HD research, but I'm not qualified to give medical advice about your personal situation.\n\n"
    "**Please reach out to these experts who can help:**\n\n"
    "- **HDSA Helpline:** hdsa.org or 1-800-345-HDSA — they have social workers and can connect you with HD specialists\n"
    "- **HDBuzz:** en.hdbuzz.net — scientists explain HD research in plain language\n"
    "- **HDYO:** hdyo.org — if you're a young person or young family\n"
    "- **Your neurologist or genetic counselor** — for anything about your personal health, testing, or treatment\n\n"
    "I'm here if you want to explore the research landscape — like what trials are recruiting or what scientists are working on. "
    "But for anything about *your* health, please talk to a professional.\n\n"
    "*This is AI-generated research analysis, not medical advice.*"
)

SYSTEM_PROMPT = """You are the HD Research Hub assistant — an AI that helps people explore Huntington's Disease RESEARCH. You are NOT a doctor, NOT a medical advisor, NOT a therapist.

HARD RULES (never break these):
1. NEVER give personal medical advice. Never say "you should take X" or "X might help you." If someone asks about their personal health, symptoms, diagnosis, testing, or treatment decisions, ALWAYS redirect them to HDSA (hdsa.org, 1-800-345-HDSA), their neurologist, or a genetic counselor.
2. NEVER recommend that someone start, stop, or change any medication or treatment.
3. NEVER predict someone's prognosis or life expectancy.
4. NEVER suggest someone should or should not get genetic testing — that is a deeply personal decision for a genetic counselor.
5. NEVER frame AI-generated hypotheses as validated treatments. Always say they are "unvalidated computational ideas that need expert review and experimental testing."
6. ALWAYS ground answers in the provided research context. Cite PubMed IDs.
7. ALWAYS end responses with: "*This is AI-generated research analysis, not medical advice.*"

WHAT YOU CAN DO:
- Explain what a research paper found (citing the PubMed ID)
- Describe what clinical trials are recruiting and where to find them on ClinicalTrials.gov
- Explain what our AI drug repurposing hypotheses mean — as unvalidated ideas
- Describe how a drug mechanism works in general scientific terms
- Point people to HDSA, HDBuzz, HDYO, Enroll-HD for real support
- Explain the HD treatment pipeline at a high level

TONE: Warm, careful, honest. You are a librarian helping someone navigate research, not a doctor giving advice. When in doubt, redirect to professionals."""


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

            # Detect language — translate to English if needed
            user_lang = detect_language(user_message)
            query_for_rag = user_message
            if user_lang != "en-IN":
                query_for_rag = sarvam_translate(user_message, user_lang, "en-IN")

            # Guardrail: intercept medical advice requests (check English version)
            msg_lower = query_for_rag.lower()
            if any(pattern in msg_lower for pattern in MEDICAL_ADVICE_PATTERNS):
                redirect = MEDICAL_REDIRECT
                if user_lang != "en-IN":
                    redirect = sarvam_translate(MEDICAL_REDIRECT, "en-IN", user_lang)
                self._respond(200, {
                    "response": redirect,
                    "papers_cited": 0,
                    "corpus_size": len(CORPUS.get("papers", {})),
                    "guardrail": "medical_advice_redirect",
                    "language": user_lang,
                })
                return

            # Build RAG context
            context = build_context(query_for_rag)

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Research context:\n{context}\n\nUser question: {query_for_rag}"},
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

            # Translate response back to user's language if needed
            response_lang = "en-IN"
            if user_lang != "en-IN":
                response = sarvam_translate(response, "en-IN", user_lang)
                response_lang = user_lang

            self._respond(200, {
                "response": response,
                "papers_cited": len(find_relevant_papers(query_for_rag)),
                "corpus_size": len(CORPUS.get("papers", {})),
                "language": response_lang,
                "language_name": SUPPORTED_LANGS.get(response_lang, "English"),
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
