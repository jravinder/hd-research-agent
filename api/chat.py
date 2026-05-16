"""HD Research Hub Chatbot API — Vercel Serverless Function (Gemma 4 agentic).

Powered by Google Gemma 4 via Google AI Studio (`gemma-4-31b-it`) using
native function calling and multimodal vision. Replaces the previous
NVIDIA NIM (Nemotron) backend.

Flow per request:
  1. Detect language; translate to English for tooling if needed (Sarvam).
  2. Run the existing text-medical-advice guardrail.
  3. If an image was uploaded, classify it with Gemma 4 vision. Personal
     medical images trigger the same MEDICAL_REDIRECT as the text guardrail.
  4. Agentic loop (no image): Gemma 4 picks tools from chat_tools.TOOLS,
     we execute, feed results back, model composes the cited answer.
     With image: a single vision call with the user's question grounded in
     a quick search_papers context lookup.
  5. Translate response back if needed.

Built for Vercel Python serverless. Cold-start RAM is dominated by data/
JSON loads; everything else is stateless. No streaming.
"""

import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

# Make src/ importable from this Vercel function.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).parent))

# Force aistudio backend on the deployed serverless function.
os.environ.setdefault("HD_LLM_BACKEND", "aistudio")

from translate import detect_language, translate as sarvam_translate, SUPPORTED_LANGS  # type: ignore
from src.llm import ask, ask_vision, ask_with_tools  # type: ignore
from src.chat_tools import TOOLS, dispatch, classify_uploaded_image  # type: ignore


# -------- System prompt --------------------------------------------------- #

SYSTEM_PROMPT = """You are the HD Research Hub assistant — an AI that helps people explore Huntington's Disease RESEARCH. You are NOT a doctor, NOT a medical advisor, NOT a therapist.

OUTPUT FORMAT (mandatory — Gemma 4 reasoning models like you tend to leak inner monologue, so this rule overrides that habit):
- Wrap the user-facing answer inside <answer>...</answer> tags. EVERYTHING outside the tags is invisible to the user and will be discarded by the application.
- Inside the tags: the final composed answer only. Use markdown freely.
- Outside the tags: do whatever reasoning you need, but the user will not see it.
- If you forget the tags, your reasoning preamble will be shown to the user — which is bad. Always include <answer> and </answer>.

HARD RULES (never break these):
1. NEVER give personal medical advice. If someone asks about their personal health, symptoms, diagnosis, testing, or treatment decisions, ALWAYS redirect them to HDSA (hdsa.org, 1-800-345-HDSA), their neurologist, or a genetic counselor.
2. NEVER recommend that someone start, stop, or change any medication or treatment.
3. NEVER predict prognosis or life expectancy.
4. NEVER suggest someone should or should not get genetic testing.
5. NEVER frame AI-generated hypotheses as validated treatments. Always say they are "unvalidated computational ideas that need expert review and experimental testing."
6. ALWAYS ground answers in research returned by tools or in the provided image.
7. Cite PubMed IDs inline using [PMID] format whenever you use information from a paper.
8. If a tool returned no relevant results, say so plainly — do not invent.
9. ALWAYS end research-facing responses with: "*This is AI-generated research analysis, not medical advice.*"

YOU HAVE TOOLS. Use them. Prefer calling a tool over guessing.

- search_papers(query) — full-text research corpus (PubMed papers + figure-derived findings)
- get_clinical_trials(status?, limit?) — current HD trials from ClinicalTrials.gov
- get_target_info(gene) — ranked HD targets table (HTT, IL-6, etc.)
- get_experiment_findings(n?) — our AI-generated drug-repurposing hypotheses
- get_latest_papers(days?, limit?) — most recent papers in the corpus

Call one or more tools when the question is research-facing. Compose the answer from tool results.

FORMAT for research questions:
  **Summary** — 2–4 sentences.
  **What the evidence here says** — bullets, each with a [PMID] citation when sourced from a paper.
  **Limits / uncertainty** — bullets.
  **Where to look next** — pointers to specific trials, hypotheses, or sources.

TONE: warm, careful, honest. A librarian helping someone navigate research, not a doctor."""


# -------- Guardrails (text + image) --------------------------------------- #

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
    "- **HDSA Helpline:** hdsa.org or 1-800-345-HDSA — social workers and HD specialists\n"
    "- **HDBuzz:** en.hdbuzz.net — scientists explain HD research in plain language\n"
    "- **HDYO:** hdyo.org — for young people and young families\n"
    "- **Your neurologist or genetic counselor** — for anything about your personal health, testing, or treatment\n\n"
    "I'm here if you want to explore the research landscape — like what trials are recruiting or what scientists are working on. "
    "For anything about *your* health, please talk to a professional.\n\n"
    "*This is AI-generated research analysis, not medical advice.*"
)

IMAGE_MEDICAL_REDIRECT = (
    "That looks like a personal medical image (a scan, photo, or test result). "
    "I'm a research tool — I'm not qualified or licensed to interpret personal medical imagery, "
    "and doing so could be harmful.\n\n"
    "**Please share it with the right professional instead:**\n\n"
    "- **Your neurologist or radiologist** — they can read scans in the context of your full history\n"
    "- **A genetic counselor** — for genetic test results\n"
    "- **HDSA Helpline:** hdsa.org or 1-800-345-HDSA — can connect you with HD specialists\n\n"
    "If you have a *research figure* from a paper (chart, plot, table, diagram), I'd be happy to help interpret it. "
    "Just no scans, photos of people, or personal test results, please.\n\n"
    "*This is AI-generated research analysis, not medical advice.*"
)


# -------- Helpers --------------------------------------------------------- #

def extract_pmids(text: str) -> list[str]:
    return re.findall(r"\[(\d{4,9})\]", text or "")


_REASONING_PATTERNS = [
    r"^\s*\*\s+",          # bullet reasoning lines
    r"^\s*-\s+(I |Let |Step |First |Then |Now )",  # bullet "I will..." lines
    r"^(The user is|I need to|I should|Let me|I'll|First,|Step \d|Looking at|Looking closer|Searching|Note:|Wait,|Self-Correction|Final answer:)",
]
_REASONING_RE = [re.compile(p, re.IGNORECASE) for p in _REASONING_PATTERNS]


def strip_reasoning(text: str) -> str:
    """Strip Gemma 4's inner-monologue preamble. Three strategies, in order:

    1. If the response contains <answer>...</answer> tags, return that content.
    2. If it contains a '***' or '---' horizontal-rule divider, take what follows.
    3. Otherwise, drop leading lines that look like reasoning (bullets, 'I should…').
    """
    if not text:
        return text
    s = text.strip()

    # 1. Tag-wrapped answer
    m = re.search(r"<answer>\s*(.*?)\s*</answer>", s, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # 2. Horizontal-rule divider — take the last segment
    parts = re.split(r"\n\s*(?:\*\*\*|---)\s*\n", s)
    if len(parts) > 1:
        s = parts[-1].strip()

    # 3. Strip leading reasoning lines until we hit something that looks like answer
    lines = s.splitlines()
    while lines and any(p.match(lines[0]) for p in _REASONING_RE):
        lines.pop(0)
    # Also drop blank prefix
    while lines and not lines[0].strip():
        lines.pop(0)
    cleaned = "\n".join(lines).strip()
    return cleaned or s


def _format_tool_result_for_model(name: str, args: dict, result: dict) -> str:
    """Compact, model-readable summary of a tool result, capped in size."""
    snippet = json.dumps(result, separators=(",", ":"))
    if len(snippet) > 6000:
        snippet = snippet[:6000] + " …(truncated)"
    return f"TOOL: {name}({json.dumps(args)})\nRESULT: {snippet}"


def _collect_sources(tool_results: list[dict]) -> list[dict]:
    """Pull (pmid, title) pairs out of tool results for the citations footer."""
    seen: dict[str, dict] = {}
    for tr in tool_results:
        result = tr.get("result") or {}
        for x in (result.get("results") or []):
            pmid = str(x.get("pmid", "") or "").strip()
            if pmid and pmid not in seen:
                seen[pmid] = {"pmid": pmid, "title": (x.get("title", "") or "")[:160]}
        for p in (result.get("papers") or []):
            pmid = str(p.get("pmid", "") or "").strip()
            if pmid and pmid not in seen:
                seen[pmid] = {"pmid": pmid, "title": (p.get("title", "") or "")[:160]}
    return list(seen.values())[:8]


def _prioritize_cited(response_text: str, sources: list[dict]) -> list[dict]:
    cited = extract_pmids(response_text)
    if not cited or not sources:
        return sources
    by_pmid = {s["pmid"]: s for s in sources}
    out: list[dict] = []
    seen = set()
    for pmid in cited:
        s = by_pmid.get(pmid)
        if s and pmid not in seen:
            out.append(s); seen.add(pmid)
    for s in sources:
        if s["pmid"] not in seen:
            out.append(s); seen.add(s["pmid"])
    return out


# -------- Agentic loop ---------------------------------------------------- #

MAX_TOOL_TURNS = 3


def run_agentic(user_question: str) -> dict:
    """Run the Gemma 4 agentic loop. Returns dict with response, tools_used,
    sources."""
    tools_used: list[str] = []
    tool_results: list[dict] = []

    prompt = user_question
    text, calls = ask_with_tools(prompt, TOOLS, system=SYSTEM_PROMPT, temperature=0.3)

    turns = 0
    while calls and turns < MAX_TOOL_TURNS:
        turns += 1
        # Execute every requested call, collect results
        round_results = []
        for c in calls:
            name = c.get("name", "")
            args = c.get("args") or {}
            res = dispatch(name, args)
            tools_used.append(name)
            round_results.append({"name": name, "args": args, "result": res})
            tool_results.append({"name": name, "args": args, "result": res})

        # Compose a follow-up turn with all tool results
        tool_block = "\n\n".join(
            _format_tool_result_for_model(r["name"], r["args"], r["result"])
            for r in round_results
        )
        follow_up = (
            f"You previously asked to call tools to answer the user's question:\n"
            f"  USER QUESTION: {user_question}\n\n"
            f"Here are the tool results:\n\n{tool_block}\n\n"
            f"If you need to call more tools, do so. Otherwise, write the final "
            f"answer for the user, citing [PMID] when you use a paper."
        )
        text, calls = ask_with_tools(follow_up, TOOLS, system=SYSTEM_PROMPT, temperature=0.3)

    # If the model produced no text but had tool results, compose one from results.
    if not text and tool_results:
        compose = (
            f"USER QUESTION: {user_question}\n\nTool results:\n"
            + "\n\n".join(_format_tool_result_for_model(r["name"], r["args"], r["result"])
                          for r in tool_results)
            + "\n\nWrite the final answer now, citing [PMID] where applicable."
        )
        text = ask(compose, system=SYSTEM_PROMPT, temperature=0.3)

    text = strip_reasoning(text)
    sources = _prioritize_cited(text, _collect_sources(tool_results))
    return {
        "response": text or "I wasn't able to compose an answer. Try rephrasing.",
        "tools_used": tools_used,
        "sources": sources,
    }


def run_vision(user_question: str, image_b64: str) -> dict:
    """Single vision call — used when the user uploads a research figure.
    We also fetch a small text context via search_papers to ground the answer."""
    # Quick context lookup so the figure interpretation is grounded.
    ctx = dispatch("search_papers", {"query": user_question, "top_k": 5}) or {}
    chunks = ctx.get("results") or []
    ctx_text = "\n".join(
        f"- [{c.get('pmid','')}] {c.get('title','')[:100]} | {c.get('section','')}\n"
        f"  {c.get('text','')[:400]}"
        for c in chunks[:5]
    )

    prompt = (
        f"USER QUESTION (about an uploaded research figure): {user_question}\n\n"
        f"Relevant research context (cite [PMID] when used):\n{ctx_text or '(no relevant chunks)'}\n\n"
        f"Interpret the figure: what is plotted, what the finding is, any "
        f"numeric values (effect size, p-values, sample sizes) you can read off it. "
        f"Be honest if you cannot read a value cleanly."
    )
    text = ask_vision(prompt, [image_b64], system=SYSTEM_PROMPT, temperature=0.3)
    text = strip_reasoning(text)

    sources: list[dict] = []
    seen = set()
    for c in chunks[:8]:
        pmid = str(c.get("pmid", "") or "").strip()
        if pmid and pmid not in seen:
            seen.add(pmid)
            sources.append({"pmid": pmid, "title": (c.get("title", "") or "")[:160]})
    sources = _prioritize_cited(text, sources)
    return {
        "response": text or "I wasn't able to interpret the image. Try a different figure.",
        "tools_used": ["ask_vision", "search_papers"],
        "sources": sources,
    }


# -------- HTTP handler ---------------------------------------------------- #

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(content_length))
            user_message = (body.get("message") or "").strip()
            image_b64 = (body.get("image_b64") or "").strip()

            if not user_message and not image_b64:
                self._respond(400, {"error": "No message or image provided"})
                return

            # Default question if user only sent an image.
            if not user_message and image_b64:
                user_message = "What does this figure show? Extract any quantitative findings."

            # Language detection / translation
            user_lang = detect_language(user_message)
            query_for_model = user_message
            if user_lang != "en-IN":
                query_for_model = sarvam_translate(user_message, user_lang, "en-IN")

            # Text guardrail
            msg_lower = query_for_model.lower()
            if any(p in msg_lower for p in MEDICAL_ADVICE_PATTERNS):
                redirect = MEDICAL_REDIRECT
                if user_lang != "en-IN":
                    redirect = sarvam_translate(MEDICAL_REDIRECT, "en-IN", user_lang)
                self._respond(200, {
                    "response": redirect,
                    "papers_cited": 0,
                    "sources": [],
                    "tools_used": ["guardrail:text_medical_advice"],
                    "guardrail": "medical_advice_redirect",
                    "language": user_lang,
                    "language_name": SUPPORTED_LANGS.get(user_lang, "English"),
                })
                return

            # Image guardrail
            if image_b64:
                label = classify_uploaded_image(image_b64)
                if label == "PERSONAL_MEDICAL":
                    redirect = IMAGE_MEDICAL_REDIRECT
                    if user_lang != "en-IN":
                        redirect = sarvam_translate(IMAGE_MEDICAL_REDIRECT, "en-IN", user_lang)
                    self._respond(200, {
                        "response": redirect,
                        "papers_cited": 0,
                        "sources": [],
                        "tools_used": ["guardrail:image_personal_medical"],
                        "guardrail": "image_medical_redirect",
                        "language": user_lang,
                        "language_name": SUPPORTED_LANGS.get(user_lang, "English"),
                    })
                    return

            # Route: image present → vision call, else → agentic tool loop
            if image_b64:
                bundle = run_vision(query_for_model, image_b64)
            else:
                bundle = run_agentic(query_for_model)

            response_text = bundle["response"]
            response_lang = "en-IN"
            if user_lang != "en-IN":
                response_text = sarvam_translate(response_text, "en-IN", user_lang)
                response_lang = user_lang

            self._respond(200, {
                "response": response_text,
                "papers_cited": len(bundle["sources"]),
                "sources": bundle["sources"],
                "tools_used": bundle["tools_used"],
                "has_inline_citations": bool(extract_pmids(bundle["response"])),
                "language": response_lang,
                "language_name": SUPPORTED_LANGS.get(response_lang, "English"),
                "model": "gemma-4-31b-it",
            })

        except Exception as e:  # last-resort error envelope
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
