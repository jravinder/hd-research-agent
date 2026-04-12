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

# Upstash Vector (serverless semantic search with built-in BGE embeddings)
UPSTASH_VECTOR_URL = os.environ.get("UPSTASH_VECTOR_URL", "")
UPSTASH_VECTOR_TOKEN = os.environ.get("UPSTASH_VECTOR_TOKEN", "")

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


def search_semantic(query, top_k=8):
    """Semantic search via Upstash Vector (built-in BGE embeddings, no external API needed)."""
    if not UPSTASH_VECTOR_URL or not UPSTASH_VECTOR_TOKEN:
        return []
    try:
        payload = json.dumps({"data": query, "topK": top_k, "includeMetadata": True}).encode("utf-8")
        req = urllib.request.Request(
            f"{UPSTASH_VECTOR_URL}/query-data",
            data=payload,
            headers={
                "Authorization": f"Bearer {UPSTASH_VECTOR_TOKEN}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return [
                {
                    "pmid": r.get("metadata", {}).get("pmid", ""),
                    "title": r.get("metadata", {}).get("title", ""),
                    "section": r.get("metadata", {}).get("section", ""),
                    "text": r.get("metadata", {}).get("text", ""),
                    "score": r.get("score", 0),
                }
                for r in data.get("result", [])
            ]
    except Exception:
        return []


def find_relevant_chunks(query, max_chunks=10):
    """Keyword fallback: search the full-text knowledge base for relevant chunks."""
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


def unique_sources(items):
    """Return unique source records keyed by PMID."""
    seen = set()
    sources = []
    for item in items:
        pmid = str(item.get("pmid", "")).strip()
        if not pmid or pmid in seen:
            continue
        seen.add(pmid)
        sources.append({
            "pmid": pmid,
            "title": item.get("title", "")[:120],
        })
    return sources


def extract_pmids(text):
    """Extract PubMed IDs cited like [12345678] from model output."""
    return re.findall(r"\[(\d{8})\]", text or "")


def prioritize_sources_by_citation(response_text, sources):
    """Move explicitly cited PMIDs to the front while preserving uniqueness."""
    cited_pmids = extract_pmids(response_text)
    if not cited_pmids or not sources:
        return sources

    by_pmid = {str(source.get("pmid", "")).strip(): source for source in sources}
    ordered = []
    seen = set()

    for pmid in cited_pmids:
        source = by_pmid.get(pmid)
        if source and pmid not in seen:
            ordered.append(source)
            seen.add(pmid)

    for source in sources:
        pmid = str(source.get("pmid", "")).strip()
        if pmid and pmid not in seen:
            ordered.append(source)
            seen.add(pmid)

    return ordered


def build_context(query):
    """Build RAG context from knowledge base, corpus, experiments, and trial data."""
    context_parts = []
    sources = []

    # Semantic search via Upstash Vector (primary source)
    chunks = search_semantic(query)

    # Fall back to keyword search if semantic returns nothing
    if not chunks:
        chunks = find_relevant_chunks(query)

    if chunks:
        sources.extend(unique_sources(chunks))
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
            sources.extend(unique_sources(papers))
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

    return {
        "text": "\n".join(context_parts),
        "sources": sources[:8],
        "source_count": len(sources),
    }


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
6. ALWAYS ground answers in the provided research context.
7. When making factual claims from papers, cite PubMed IDs inline using the format [12345678].
8. If the available context does not support a claim strongly, say that plainly instead of filling the gap.
9. If the question is about trials or site-level statistics, use the provided context and be explicit when the answer comes from site data rather than a paper.
10. If there are relevant papers in context, do not return an uncited research summary.
11. ALWAYS end responses with: "*This is AI-generated research analysis, not medical advice.*"

WHAT YOU CAN DO:
- Explain what a research paper found (citing the PubMed ID)
- Describe what clinical trials are recruiting and where to find them on ClinicalTrials.gov
- Explain what our AI drug repurposing hypotheses mean — as unvalidated ideas
- Describe how a drug mechanism works in general scientific terms
- Point people to HDSA, HDBuzz, HDYO, Enroll-HD for real support
- Explain the HD treatment pipeline at a high level

FORMAT:
- Prefer this structure whenever the question is research-facing:
  **Summary**
  2-4 sentences.

  **What The Evidence Here Says**
  2-5 bullet points, each grounded in the provided context.

  **Limits / Uncertainty**
  1-3 bullet points on ambiguity, missing evidence, or why this should be treated cautiously.

  **Where To Look Next**
  1-3 bullet points pointing to trials, reports, or papers in the context.
- If the user asks a very narrow factual question, you may answer more briefly, but still cite PMIDs when using papers.
- Keep answers concise and readable. Avoid long walls of text.

TONE: Warm, careful, honest. You are a librarian helping someone navigate research, not a doctor giving advice. When in doubt, redirect to professionals."""


def has_research_context(context_bundle):
    """Whether the answer had research sources available for citation."""
    return bool(context_bundle.get("sources"))


def has_inline_citations(text):
    """Whether the model included PMID-style citations in the response."""
    return bool(extract_pmids(text))


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
            context_bundle = build_context(query_for_rag)
            context = context_bundle["text"]
            sources = context_bundle["sources"]

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
            sources = prioritize_sources_by_citation(response, sources)

            response_has_inline_citations = has_inline_citations(response)
            citation_warning = None
            if has_research_context(context_bundle) and not response_has_inline_citations:
                citation_warning = "This answer used retrieved research context but did not include inline PubMed citations. Treat it as lower-confidence summary text."

            # Translate response back to user's language if needed
            response_lang = "en-IN"
            if user_lang != "en-IN":
                response = sarvam_translate(response, "en-IN", user_lang)
                response_lang = user_lang
                if citation_warning:
                    citation_warning = sarvam_translate(citation_warning, "en-IN", user_lang)

            self._respond(200, {
                "response": response,
                "papers_cited": len(sources),
                "sources": sources,
                "citation_warning": citation_warning,
                "has_inline_citations": response_has_inline_citations,
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
