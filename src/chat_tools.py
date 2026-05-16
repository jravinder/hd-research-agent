"""Tools available to the agentic Gemma 4 chatbot.

Each tool has:
  - A Python implementation that reads from the shipped data/*.json files.
  - A function declaration in the shared shape consumed by `llm.ask_with_tools`:
        {"name", "description", "parameters": {type: object, properties, required}}

The same module is importable from:
  - api/chat.py    (Vercel serverless chatbot)
  - notebooks/*    (the Kaggle notebook)
  - src/agents/*   (future: agents that need on-demand data lookups)

Keep this module pure-Python with zero external state — the only inputs are the
JSON files in data/. That's what makes it portable to Kaggle and serverless.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


# Repo root is the parent of src/ — work whether imported from src/, api/, notebooks/.
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


# -------- Data loaders (cached on first read) ----------------------------- #

_CACHE: dict[str, Any] = {}


def _load(name: str) -> Any:
    if name not in _CACHE:
        path = DATA_DIR / name
        if path.exists():
            with open(path) as f:
                _CACHE[name] = json.load(f)
        else:
            _CACHE[name] = {}
    return _CACHE[name]


# -------- Tool: search_papers --------------------------------------------- #

UPSTASH_URL = os.environ.get("UPSTASH_VECTOR_URL", "")
UPSTASH_TOKEN = os.environ.get("UPSTASH_VECTOR_TOKEN", "")

_STOP = {"the","a","an","is","are","was","were","in","on","at","to","for","of",
         "and","or","with","that","this","what","how","why","can","do","does"}


def _upstash_search(query: str, top_k: int = 8) -> list[dict]:
    if not (UPSTASH_URL and UPSTASH_TOKEN):
        return []
    try:
        payload = json.dumps({"data": query, "topK": top_k, "includeMetadata": True}).encode()
        req = urllib.request.Request(
            f"{UPSTASH_URL}/query-data", data=payload,
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}",
                     "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return [{
                "pmid": r.get("metadata", {}).get("pmid", ""),
                "title": r.get("metadata", {}).get("title", ""),
                "section": r.get("metadata", {}).get("section", ""),
                "text": (r.get("metadata", {}).get("text", "") or "")[:600],
                "score": r.get("score", 0),
            } for r in data.get("result", [])]
    except Exception:
        return []


def _keyword_search(query: str, top_k: int = 8) -> list[dict]:
    """Fallback search over data/corpus.json papers."""
    corpus = _load("corpus.json")
    terms = set(re.findall(r"\w+", query.lower())) - _STOP
    scored: list[tuple[int, dict]] = []
    for pmid, paper in (corpus.get("papers") or {}).items():
        analysis = paper.get("analysis", {}) or {}
        blob = (
            (paper.get("title", "") or "")
            + " " + (paper.get("abstract", "") or "")
            + " " + (analysis.get("finding", "") or "")
            + " " + " ".join(analysis.get("targets", []) or [])
            + " " + " ".join(analysis.get("compounds", []) or [])
        ).lower()
        score = sum(1 for t in terms if t in blob)
        if score:
            scored.append((score, {
                "pmid": pmid,
                "title": paper.get("title", "")[:160],
                "section": "abstract",
                "text": (paper.get("abstract", "") or "")[:600],
                "score": score,
            }))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


def search_papers(query: str, top_k: int = 8) -> dict:
    """Semantic-first, keyword-fallback search over the HD research corpus."""
    results = _upstash_search(query, top_k=top_k) or _keyword_search(query, top_k=top_k)
    return {"query": query, "results": results, "count": len(results)}


# -------- Tool: get_clinical_trials --------------------------------------- #

def get_clinical_trials(status: str = "", limit: int = 8) -> dict:
    """Return HD trials from data/data.json. Filter by status if provided
    (one of: recruiting, active, completed). Case-insensitive."""
    data = _load("data.json")
    trials = data.get("trials") or []
    s = (status or "").strip().lower()
    # Map fuzzy user inputs to ClinicalTrials.gov status tokens.
    STATUS_GROUPS = {
        "recruiting":  {"recruiting"},
        "active":      {"active_not_recruiting", "enrolling_by_invitation"},
        "completed":   {"completed"},
        "open":        {"recruiting", "enrolling_by_invitation"},
    }
    if s:
        targets = STATUS_GROUPS.get(s, {s})
        trials = [t for t in trials
                  if (t.get("status", "") or "").lower() in targets]
    out = [{
        "nct_id": t.get("nct_id", ""),
        "title": t.get("title", ""),
        "status": t.get("status", ""),
        "phase": t.get("phase", ""),
        "sponsor": t.get("sponsor", ""),
        "intervention": t.get("intervention", ""),
        "enrollment": t.get("enrollment", ""),
    } for t in trials[:limit]]
    stats = data.get("stats", {}) or {}
    return {"status_filter": status, "count": len(out), "trials": out,
            "summary_stats": stats}


# -------- Tool: get_target_info ------------------------------------------- #

def get_target_info(gene: str) -> dict:
    """Look up an HD target (gene/protein symbol) in the ranked targets table."""
    rankings = _load("target_rankings.json")
    targets = rankings.get("targets") or []
    g = (gene or "").strip().lower()
    hits = [t for t in targets if g and g in (t.get("symbol", "") or "").lower()]
    if not hits:
        # Broader match against full_name and role
        hits = [t for t in targets
                if g and (g in (t.get("full_name", "") or "").lower()
                          or g in (t.get("role", "") or "").lower())]
    return {"query": gene, "matches": hits[:5],
            "total_targets_ranked": len(targets)}


# -------- Tool: get_experiment_findings ----------------------------------- #

def get_experiment_findings(n: int = 5) -> dict:
    """Return the top AI-generated drug-repurposing hypotheses from our experiments."""
    exp = _load("experiment_001_results.json")
    hypotheses = exp.get("hypotheses") or []
    out = []
    for h in hypotheses[:n]:
        if isinstance(h, dict):
            out.append({
                "drug": h.get("drug", ""),
                "hd_target": h.get("hd_target", ""),
                "score": h.get("score", ""),
                "rationale": h.get("rationale", ""),
            })
    # Also pull live-tracked hypotheses if present
    tracker = _load("hypotheses_tracker.json")
    tracked = (tracker.get("hypotheses") or [])[:n]
    return {"top_experiment_hypotheses": out,
            "tracked_hypotheses": tracked,
            "disclaimer": "AI-generated, unvalidated. Not medical advice."}


# -------- Tool: get_latest_papers ----------------------------------------- #

def get_latest_papers(days: int = 30, limit: int = 8) -> dict:
    """Return the most recent papers in data/corpus.json. `days` is a soft hint;
    if publication dates are missing, the call falls back to the most recent N
    by corpus order."""
    corpus = _load("corpus.json")
    papers = corpus.get("papers") or {}
    items = list(papers.items())
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
    dated = []
    undated = []
    for pmid, p in items:
        d = p.get("pub_date") or p.get("date") or ""
        ts = None
        if d:
            try:
                ts = datetime.fromisoformat(d.replace("Z", "+00:00"))
            except Exception:
                ts = None
        if ts and ts >= cutoff:
            dated.append((ts, pmid, p))
        elif not ts:
            undated.append((pmid, p))
    dated.sort(key=lambda x: x[0], reverse=True)
    selected = dated[:limit]
    if len(selected) < limit:
        # backfill from undated (corpus is roughly chronological)
        for pmid, p in undated[: (limit - len(selected))]:
            selected.append((None, pmid, p))
    out = [{
        "pmid": pmid,
        "title": p.get("title", "")[:200],
        "abstract_snippet": (p.get("abstract", "") or "")[:300],
    } for _, pmid, p in selected]
    return {"days": days, "count": len(out), "papers": out}


# -------- Tool registry --------------------------------------------------- #

# JSON-schema-style declarations used by both Ollama and AI Studio.
TOOLS: list[dict] = [
    {
        "name": "search_papers",
        "description": (
            "Semantic search over the HD Research Hub's full-text knowledge base "
            "(PubMed papers, including figure-derived findings). Returns matching "
            "chunks with PMID, title, section, and a short text excerpt. Use this "
            "for any research-content question."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Free-text research query."},
                "top_k": {"type": "integer", "description": "Max results (default 8)."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_clinical_trials",
        "description": (
            "Return current Huntington's Disease clinical trials from "
            "ClinicalTrials.gov as cached on the site. Filter by status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": ("Optional status filter: 'recruiting', "
                                    "'active', 'completed'. Empty = all."),
                },
                "limit": {"type": "integer",
                          "description": "Max trials to return (default 8)."},
            },
            "required": [],
        },
    },
    {
        "name": "get_target_info",
        "description": (
            "Look up an HD target (gene/protein symbol such as HTT, IL-6, mHTT) "
            "in the project's ranked-target table. Returns score, mentions, "
            "associated compounds."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "gene": {"type": "string",
                         "description": "Gene/protein symbol or partial name."},
            },
            "required": ["gene"],
        },
    },
    {
        "name": "get_experiment_findings",
        "description": (
            "Return the top AI-generated drug-repurposing hypotheses from the "
            "site's experiments. UNVALIDATED computational ideas — not medical "
            "advice."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "n": {"type": "integer", "description": "Number to return (default 5)."},
            },
            "required": [],
        },
    },
    {
        "name": "get_latest_papers",
        "description": (
            "Return the most recently ingested HD research papers from the "
            "corpus. Use for 'what's new' or recency-sensitive questions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer",
                         "description": "Look-back window in days (default 30)."},
                "limit": {"type": "integer",
                          "description": "Max papers (default 8)."},
            },
            "required": [],
        },
    },
]


_DISPATCH = {
    "search_papers": search_papers,
    "get_clinical_trials": get_clinical_trials,
    "get_target_info": get_target_info,
    "get_experiment_findings": get_experiment_findings,
    "get_latest_papers": get_latest_papers,
}


def dispatch(name: str, args: dict | None) -> dict:
    """Execute a tool call by name. Unknown tool → returns an error dict."""
    fn = _DISPATCH.get(name)
    if fn is None:
        return {"error": f"unknown tool: {name}"}
    try:
        return fn(**(args or {}))
    except TypeError as e:
        # Tolerate extra/wrong kwargs — the model sometimes invents them.
        try:
            kwargs = {k: v for k, v in (args or {}).items()
                      if k in fn.__code__.co_varnames}
            return fn(**kwargs)
        except Exception as e2:
            return {"error": f"{name} failed: {e2}"}
    except Exception as e:
        return {"error": f"{name} failed: {e}"}


# -------- Vision guardrail (used by api/chat.py for image uploads) -------- #

GUARDRAIL_PROMPT = (
    "You are a strict gatekeeper. Look at the image and classify it as exactly one of:\n"
    "  PERSONAL_MEDICAL — a personal medical image: MRI, CT, X-ray, ultrasound, "
    "EEG/EKG trace, genetic test report, dermatology photo, photograph of a person.\n"
    "  RESEARCH_FIGURE — a chart, plot, graph, table, schematic, molecular structure, "
    "western blot, micrograph, or other scientific figure from a paper.\n"
    "  OTHER — anything else.\n"
    "Reply with one token only: PERSONAL_MEDICAL, RESEARCH_FIGURE, or OTHER."
)


def classify_uploaded_image(image: Any) -> str:
    """Return one of PERSONAL_MEDICAL / RESEARCH_FIGURE / OTHER. Best-effort —
    falls back to OTHER if the vision call fails."""
    try:
        from src.llm import ask_vision  # local import to avoid cycles
    except ImportError:
        from llm import ask_vision  # type: ignore
    try:
        raw = ask_vision(GUARDRAIL_PROMPT, [image], temperature=0.0)
    except Exception:
        return "OTHER"
    raw = (raw or "").strip().upper()
    for label in ("PERSONAL_MEDICAL", "RESEARCH_FIGURE", "OTHER"):
        if label in raw:
            return label
    return "OTHER"
