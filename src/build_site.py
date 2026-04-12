"""Build Site — regenerates index.html with fresh data from data.json.

Pulls real numbers from data.json (written by data_fetcher.py) and
injects them into the landing page. Then commits and pushes to trigger
Vercel auto-deploy.
"""

import json
import os
import subprocess
import sys
from html import escape
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "data.json"
HYPOTHESES_FILE = ROOT / "data" / "hypotheses_tracker.json"
INDEX_FILE = ROOT / "index.html"


def load_data():
    """Load data.json."""
    if not DATA_FILE.exists():
        print("No data.json found — run data_fetcher.py first")
        sys.exit(1)
    with open(DATA_FILE) as f:
        return json.load(f)


def load_hypotheses():
    """Load tracked hypotheses if available."""
    if not HYPOTHESES_FILE.exists():
        return []
    with open(HYPOTHESES_FILE) as f:
        tracker = json.load(f)
    return tracker.get("hypotheses", [])


def sanitize_url(url):
    """Allow only http(s) URLs and escape for safe HTML attribute insertion."""
    candidate = (url or "").strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        return "#"
    return escape(candidate, quote=True)


def text(value):
    """Escape arbitrary text for safe HTML rendering."""
    return escape(str(value or ""))


def _extract_topics(paper):
    """Extract relevant topic tags from a paper title and abstract."""
    title_abs = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    topic_map = {
        "gene therapy": ["gene therapy", "aav", "amt-130", "viral vector", "crispr"],
        "biomarker": ["biomarker", "neurofilament", "nfl", "uch-l1", "gfap"],
        "drug repurposing": ["repurpos", "repositioning", "fda-approved"],
        "somatic expansion": ["somatic expansion", "cag repeat", "msh3", "fan1", "pms1", "mismatch repair"],
        "neuroinflammation": ["neuroinflam", "microglia", "astrocyte", "il-6", "cytokine"],
        "autophagy": ["autophagy", "mtor", "clearance", "aggregate"],
        "AI / ML": ["machine learning", "deep learning", "artificial intelligence", "neural network", "computational"],
        "clinical trial": ["clinical trial", "phase i", "phase ii", "phase iii", "randomized"],
        "protein structure": ["protein structure", "huntingtin", "polyglutamine", "cryo-em", "alphafold"],
        "TDP-43": ["tdp-43", "tdp43"],
    }
    tags = []
    for tag, keywords in topic_map.items():
        if any(kw in title_abs for kw in keywords):
            tags.append(tag)
    return tags[:3]  # max 3 tags per paper


def build_papers_html(papers):
    """Build HTML for latest papers section with topic tags."""
    if not papers:
        return ""

    tag_colors = {
        "gene therapy": "purple", "biomarker": "blue", "drug repurposing": "orange",
        "somatic expansion": "red", "neuroinflammation": "pink", "autophagy": "green",
        "AI / ML": "amber", "clinical trial": "emerald", "protein structure": "indigo",
        "TDP-43": "amber",
    }

    cards = []
    for p in papers[:6]:
        journal = text(p.get("journal", "")[:40])
        date = text(p.get("pub_date", ""))
        title = text(p.get("title", "")[:100])
        url = sanitize_url(p.get("url", "#"))
        abstract = text(p.get("abstract", "")[:200])
        topics = _extract_topics(p)

        tags_html = ""
        if topics:
            tag_spans = []
            for t in topics:
                color = tag_colors.get(t, "gray")
                tag_spans.append(f'<span class="px-2 py-0.5 bg-{color}-100 text-{color}-700 rounded text-xs font-medium">{t}</span>')
            tags_html = f'<div class="flex flex-wrap gap-1 mb-2">{"".join(tag_spans)}</div>'

        cards.append(f'''
      <div class="bg-white border border-stone-200 rounded-xl p-5 hover:shadow-md transition-shadow">
        <div class="text-xs text-amber-700 font-bold uppercase mb-2">{date} — {journal}</div>
        {tags_html}
        <h3 class="text-base font-bold text-stone-900 mb-2">{title}</h3>
        <p class="text-stone-600 text-sm line-clamp-3">{abstract}</p>
        <a href="{url}" target="_blank" rel="noopener noreferrer" class="text-amber-700 text-sm font-medium mt-2 inline-flex items-center gap-1">PubMed <span class="material-symbols-outlined text-sm">open_in_new</span></a>
      </div>''')
    return "\n".join(cards)


def build_trials_html(trials):
    """Build HTML rows for trials table."""
    if not trials:
        return ""
    rows = []
    for t in trials[:10]:
        phase = text(t.get("phase", "N/A"))
        status = t.get("status", "")
        status_color = "green" if status == "RECRUITING" else "amber" if "ACTIVE" in status else "gray"
        status_label = text(status.replace("_", " ").title())
        intervention = text(t.get("intervention", "")[:40])
        title = text(t.get("title", "")[:50])
        sponsor = text(t.get("sponsor", "")[:25])
        nct_id = text(t.get("nct_id", ""))
        url = sanitize_url(t.get("url", "#"))
        rows.append(f'''
          <tr class="hover:bg-amber-50/50 transition-colors">
            <td class="py-3 px-6 font-bold text-stone-900"><a href="{url}" target="_blank" rel="noopener noreferrer" class="hover:text-amber-700">{nct_id}</a></td>
            <td class="py-3 px-6 text-stone-800 text-sm">{title}</td>
            <td class="py-3 px-6 text-stone-800 text-sm">{sponsor}</td>
            <td class="py-3 px-6"><span class="px-2 py-1 bg-amber-100 text-amber-800 rounded-md text-xs font-medium">{phase}</span></td>
            <td class="py-3 px-6"><span class="px-2 py-1 bg-{status_color}-100 text-{status_color}-700 rounded-md text-xs font-medium">{status_label}</span></td>
            <td class="py-3 px-6 text-stone-700 text-sm">{intervention}</td>
          </tr>''')
    return "\n".join(rows)


def build_hdbuzz_html(articles):
    """Build HTML for HDBuzz news."""
    if not articles:
        return ""
    items = []
    for a in articles[:5]:
        link = sanitize_url(a.get("link", "#"))
        pub_date = text(a.get("pub_date", "")[:16])
        title = text(a.get("title", ""))
        items.append(f'''
      <a href="{link}" target="_blank" rel="noopener noreferrer" class="block border border-stone-200 rounded-xl p-5 hover:shadow-md hover:border-amber-300 transition-all">
        <div class="text-xs text-green-600 font-medium mb-1">{pub_date}</div>
        <h3 class="text-base font-bold text-stone-900">{title}</h3>
      </a>''')
    return "\n".join(items)


def build_hypotheses_html(hypotheses):
    """Build HTML for tracked hypotheses instead of hard-coded cards."""
    if not hypotheses:
        return ""

    status_styles = {
        "exploring": ("amber", "Exploring"),
        "promising": ("green", "Promising"),
        "known_tested": ("stone", "Known/Tested"),
        "deprioritized": ("red", "Deprioritized"),
    }

    cards = []
    ranked = sorted(
        hypotheses,
        key=lambda h: (h.get("scores", [0])[-1] if h.get("scores") else 0, h.get("dates", [""])[-1] if h.get("dates") else ""),
        reverse=True,
    )

    for h in ranked[:6]:
        score = h.get("scores", [0])[-1] if h.get("scores") else 0
        status_key = h.get("status", "exploring")
        color, status_label = status_styles.get(status_key, ("stone", text(status_key.replace("_", " ").title())))
        drug = text(h.get("drug", "Unknown"))
        target = text(h.get("target", ""))
        rationale = text(h.get("rationale", "")[:220])
        evidence_for = len(h.get("evidence_for", []))
        evidence_against = len(h.get("evidence_against", []))
        updated = ""
        if h.get("dates"):
            updated = text(str(h["dates"][-1])[:10])

        cards.append(f'''
      <div class="border border-{color}-200 bg-{color}-50/30 rounded-xl p-5 hover:shadow-md transition-shadow">
        <div class="flex items-center justify-between mb-3 gap-3">
          <span class="text-lg font-bold text-stone-900">{drug}</span>
          <span class="px-2 py-0.5 bg-{color}-100 text-{color}-700 rounded text-xs font-medium">{status_label}</span>
        </div>
        <div class="text-sm text-stone-800 font-medium mb-2">Target: {target}</div>
        <p class="text-sm text-stone-700">{rationale}</p>
        <div class="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-stone-600">
          <span>Latest score: {score}/100</span>
          <span>Support: {evidence_for}</span>
          <span>Concerns: {evidence_against}</span>
          {f"<span>Updated: {updated}</span>" if updated else ""}
        </div>
      </div>''')
    return "\n".join(cards)


def build_page(data):
    """Generate the full index.html from data."""
    stats = data.get("stats", {})
    papers = data.get("papers", [])
    trials = data.get("trials", [])
    hdbuzz = data.get("hdbuzz", [])
    targets = data.get("targets", [])
    hypotheses = load_hypotheses()
    last_updated = data.get("last_updated", "")

    try:
        updated_str = datetime.fromisoformat(last_updated).strftime("%B %d, %Y at %I:%M %p")
    except Exception:
        updated_str = last_updated

    targets_html = ""
    if targets:
        targets_html = "".join(
            f'<div class="border border-stone-200 rounded-lg p-3 hover:border-purple-300 transition-colors"><span class="font-bold text-stone-900">{text(t.get("symbol", ""))}</span><div class="text-xs text-stone-600 mt-1">{text(t.get("name", "")[:35])}</div><div class="text-xs text-purple-500 font-medium mt-1">Score: {text(t.get("score", 0))}</div></div>'
            for t in targets[:16]
        )

    html = f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>HD Research Hub — AI-Powered Huntington's Disease Research</title>
<meta name="description" content="Open-source AI research dashboard exploring how data science and machine learning can accelerate Huntington's Disease drug discovery."/>
<!-- Google Analytics -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-N8BMJ7ZG5V"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','G-N8BMJ7ZG5V');</script>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<link href="shared.css" rel="stylesheet"/>
<style>
  .text-shadow-hero {{ text-shadow: 0 2px 8px rgba(0,0,0,0.3); }}
  .stat-card {{ transition: transform 0.2s, box-shadow 0.2s; }}
  .stat-card:hover {{ transform: translateY(-2px); box-shadow: 0 8px 30px rgba(0,0,0,0.06); }}
  @media (max-width: 768px) {{
    .mobile-menu {{ display: none; }}
    .mobile-menu.active {{ display: flex; flex-direction: column; position: absolute; top: 64px; left: 0; right: 0; background: #fdf9e9; padding: 16px; border-bottom: 1px solid #d8c3ad; box-shadow: 0 4px 12px rgba(0,0,0,0.08); z-index: 100; }}
  }}
</style>
</head>
<body class="bg-[#fdf9e9] text-[#1c1c13] antialiased" style="font-size:18px;">

<!-- Nav -->
<nav class="bg-[#fdf9e9]/80 backdrop-blur-xl sticky top-0 z-50 shadow-sm">
  <div class="flex justify-between items-center max-w-7xl mx-auto px-6 h-20">
    <div class="flex items-center gap-4 md:gap-8">
      <span class="text-2xl font-bold tracking-tighter text-amber-700">HD Research Hub</span>
      <button onclick="document.getElementById('mobile-nav').classList.toggle('active')" class="md:hidden p-2">
        <span class="material-symbols-outlined">menu</span>
      </button>
      <div id="mobile-nav" class="mobile-menu hidden md:flex items-center gap-8 text-sm font-medium">
        <a href="#pillars" class="text-stone-800 hover:text-amber-700 transition-colors">Start Here</a>
        <a href="#trials" class="text-stone-800 hover:text-amber-700 transition-colors">Trials</a>
        <a href="#ideas" class="text-stone-800 hover:text-amber-700 transition-colors">Ideas</a>
        <a href="#resources" class="text-stone-800 hover:text-amber-700 transition-colors">Resources</a>
        <a href="research.html" class="text-stone-800 hover:text-amber-700 transition-colors">Our Work</a>
        <a href="about.html" class="text-stone-800 hover:text-amber-700 transition-colors">About</a>
      </div>
    </div>
    <div class="flex items-center gap-4">
      <div id="google_translate_element"></div>
      <a href="chat.html" class="bg-amber-500 text-white px-5 py-2 rounded-lg font-semibold text-sm hover:shadow-[0_0_15px_rgba(245,158,11,0.4)] transition-all active:scale-95">Ask HD Research</a>
    </div>
  </div>
</nav>

<!-- Hero — Sunrise Hope (Stitch design) -->
<section class="relative rounded-xl overflow-hidden min-h-[500px] flex items-center justify-center text-center p-8 md:p-12 mx-4 md:mx-6 mt-6">
  <div class="absolute inset-0 z-0">
    <img class="w-full h-full object-cover" alt="Mountain peaks at sunrise" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDEYiOi0pH5LZMmy4KRxZQNonDjeLvrSzXozMeypp9TCRTCXrUapIE0udef6db-3imY_EdeTF7JDrBTgTMbqliVA1JlD1QGTK9AdmAPgkqb6VIa9zkLXJd8NQ9FX4RuNPApn9hWcN7GYMU0tacM2S0zNnRob-j1wxkEQmhqRjj6oJv3e32mpsppjqqzgMJqjxFOnZauLMK_YQMJiJhz7kVvkAROwL-_qVnTzT5i1tPWLpdsN2Hyp9bdMfak2U5fLU1Hf1rJE2o880s"/>
    <div class="absolute inset-0 bg-gradient-to-br from-amber-500/30 via-amber-900/20 to-rose-500/20 mix-blend-multiply"></div>
    <div class="absolute inset-0 bg-black/15"></div>
  </div>
  <div class="relative z-10 space-y-6 max-w-3xl">
    <h1 class="text-5xl md:text-7xl font-extrabold tracking-tighter text-white text-shadow-hero leading-tight">
      Learn HD. Explore the Evidence. Chat With the Data.
    </h1>
    <p class="text-lg md:text-xl text-white/90 font-medium max-w-2xl mx-auto leading-relaxed">
      A public HD research workspace with three jobs: help people learn the field, keep an always-updating view of papers and trials, and answer questions from a grounded research corpus.
    </p>
    <div class="flex flex-wrap justify-center gap-4">
      <a href="chat.html" class="bg-amber-500 text-white px-8 py-4 rounded-lg font-bold text-lg hover:shadow-[0_0_20px_rgba(245,158,11,0.5)] transition-all">Ask HD Research</a>
      <a href="learn.html" class="bg-white/10 backdrop-blur-md text-white border border-white/30 px-8 py-4 rounded-lg font-bold text-lg hover:bg-white/20 transition-all">Start Learning</a>
    </div>
  </div>
</section>

<!-- Stats -->
<section class="py-12 px-4 md:px-6">
  <div class="max-w-5xl mx-auto">
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
      <div class="stat-card bg-white rounded-xl p-5 shadow-sm border border-amber-100">
        <div class="text-2xl md:text-3xl font-extrabold text-amber-600">{stats.get('papers_count', 0)}</div>
        <div class="text-xs text-stone-700 font-medium mt-1">Recent Papers</div>
      </div>
      <div class="stat-card bg-white rounded-xl p-5 shadow-sm border border-green-100">
        <div class="text-2xl md:text-3xl font-extrabold text-green-600">{stats.get('trials_count', 0)}</div>
        <div class="text-xs text-stone-700 font-medium mt-1">Active Trials</div>
      </div>
      <div class="stat-card bg-white rounded-xl p-5 shadow-sm border border-orange-100">
        <div class="text-2xl md:text-3xl font-extrabold text-orange-500">{stats.get('recruiting_count', 0)}</div>
        <div class="text-xs text-stone-700 font-medium mt-1">Recruiting Now</div>
      </div>
      <div class="stat-card bg-white rounded-xl p-5 shadow-sm border border-purple-100">
        <div class="text-2xl md:text-3xl font-extrabold text-purple-600">{stats.get('targets_count', 0) or '16+'}</div>
        <div class="text-xs text-stone-700 font-medium mt-1">Known Targets</div>
      </div>
    </div>
    <p class="text-xs text-stone-600 text-center mt-4">Updated {updated_str} — auto-refreshed daily from PubMed, ClinicalTrials.gov, HDBuzz, Open Targets</p>
  </div>
</section>

<!-- Core product pillars -->
<section id="pillars" class="py-16 px-4 md:px-8">
  <div class="max-w-5xl mx-auto">
    <div class="text-center mb-12">
      <div class="text-sm font-bold text-amber-700 uppercase tracking-wider mb-2">Start Here</div>
      <h2 class="text-2xl md:text-3xl font-bold text-stone-900">Three Useful Ways In</h2>
      <p class="text-stone-700 mt-2 max-w-2xl mx-auto">This project is most useful when it helps people do one of three things well: get oriented, ask better questions, and stay current without manually monitoring every source.</p>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
      <div class="bg-gradient-to-br from-amber-50 to-amber-100/50 border border-amber-200 rounded-2xl p-6">
        <div class="w-11 h-11 bg-amber-500 rounded-xl flex items-center justify-center mb-4">
          <span class="material-symbols-outlined text-white">school</span>
        </div>
        <h3 class="text-lg font-bold text-stone-900 mb-2">Learn the Basics</h3>
        <p class="text-stone-700 text-sm">The site should help a newcomer move from “what is HD?” to targets, biomarkers, trials, and current debates without needing to decode raw papers first.</p>
        <a href="learn.html" class="text-amber-700 text-sm font-medium mt-3 inline-flex items-center gap-1">Open learning path <span class="material-symbols-outlined text-sm">arrow_forward</span></a>
      </div>
      <div class="bg-gradient-to-br from-orange-50 to-orange-100/50 border border-orange-200 rounded-2xl p-6">
        <div class="w-11 h-11 bg-orange-500 rounded-xl flex items-center justify-center mb-4">
          <span class="material-symbols-outlined text-white">chat</span>
        </div>
        <h3 class="text-lg font-bold text-stone-900 mb-2">Chat With Grounded Data</h3>
        <p class="text-stone-700 text-sm">A useful chat tool answers plain-English questions against the HD corpus, experiment reports, and trial data, then points back to sources instead of bluffing confidence.</p>
        <a href="chat.html" class="text-orange-600 text-sm font-medium mt-3 inline-flex items-center gap-1">Ask the corpus <span class="material-symbols-outlined text-sm">arrow_forward</span></a>
      </div>
      <div class="bg-gradient-to-br from-green-50 to-green-100/50 border border-green-200 rounded-2xl p-6">
        <div class="w-11 h-11 bg-green-500 rounded-xl flex items-center justify-center mb-4">
          <span class="material-symbols-outlined text-white">sync</span>
        </div>
        <h3 class="text-lg font-bold text-stone-900 mb-2">Automated Research Gatherer</h3>
        <p class="text-stone-700 text-sm">The engine behind the site is the daily gatherer: papers, trials, feeds, and tracked hypotheses collected into one inspectable workspace so someone does not have to monitor everything manually.</p>
        <a href="research.html" class="text-green-700 text-sm font-medium mt-3 inline-flex items-center gap-1">See the workflow <span class="material-symbols-outlined text-sm">arrow_forward</span></a>
      </div>
    </div>
  </div>
</section>

<!-- Guided value section -->
<section class="py-12 px-4 md:px-8">
  <div class="max-w-5xl mx-auto">
    <div class="bg-gradient-to-br from-white to-amber-50 border border-amber-200 rounded-3xl p-6 md:p-8">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div class="bg-[#fdf9e9] rounded-2xl border border-stone-200 p-5">
          <div class="text-xs font-bold uppercase tracking-wider text-amber-700 mb-2">For Learners</div>
          <h3 class="text-lg font-bold text-stone-900 mb-2">Start With the Field Map</h3>
          <p class="text-sm text-stone-700">Use the learning path to build the basics first, then read experiment pages once the vocabulary makes sense.</p>
        </div>
        <div class="bg-[#fdf9e9] rounded-2xl border border-stone-200 p-5">
          <div class="text-xs font-bold uppercase tracking-wider text-orange-600 mb-2">For Questions</div>
          <h3 class="text-lg font-bold text-stone-900 mb-2">Use Chat as a Research Interface</h3>
          <p class="text-sm text-stone-700">Ask about a mechanism, treatment, or trial, then use the linked sources and reports to verify the answer.</p>
        </div>
        <div class="bg-[#fdf9e9] rounded-2xl border border-stone-200 p-5">
          <div class="text-xs font-bold uppercase tracking-wider text-green-700 mb-2">For Staying Current</div>
          <h3 class="text-lg font-bold text-stone-900 mb-2">Let the Gatherer Do the Watching</h3>
          <p class="text-sm text-stone-700">The automation layer refreshes the raw inputs so the dashboard and chat have something current to stand on.</p>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- HD News — combining HDBuzz + recent breakthroughs -->
<section id="news" class="py-16 px-4 md:px-8 bg-[#f8f4e4]">
  <div class="max-w-5xl mx-auto">
    <div class="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-2">
      <div>
        <div class="text-sm font-bold text-orange-600 uppercase tracking-wider mb-1">What's Happening Now</div>
        <h2 class="text-2xl md:text-3xl font-bold text-stone-900">HD News + Breakthroughs</h2>
      </div>
      <a href="https://en.hdbuzz.net" target="_blank" class="text-amber-700 text-sm font-medium flex items-center gap-1">More on HDBuzz <span class="material-symbols-outlined text-sm">open_in_new</span></a>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
{build_hdbuzz_html(hdbuzz)}
    </div>
  </div>
</section>

<!-- Latest Papers -->
<section id="papers" class="py-16 px-4 md:px-8">
  <div class="max-w-5xl mx-auto">
    <div class="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-2">
      <div>
        <div class="text-sm font-bold text-amber-700 uppercase tracking-wider mb-1">Fresh from PubMed</div>
        <h2 class="text-2xl md:text-3xl font-bold text-stone-900">Latest Research Papers</h2>
      </div>
      <a href="https://pubmed.ncbi.nlm.nih.gov/?term=huntington+disease+treatment" target="_blank" class="text-amber-700 text-sm font-medium flex items-center gap-1">All HD papers <span class="material-symbols-outlined text-sm">open_in_new</span></a>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
{build_papers_html(papers)}
    </div>
  </div>
</section>

<!-- Active Trials -->
<section id="trials" class="py-16 px-4 md:px-8 bg-[#f8f4e4]">
  <div class="max-w-5xl mx-auto">
    <div class="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-2">
      <div>
        <div class="text-sm font-bold text-green-600 uppercase tracking-wider mb-1">Reasons for Optimism</div>
        <h2 class="text-2xl md:text-3xl font-bold text-stone-900">Active Clinical Trials</h2>
        <p class="text-stone-700 text-sm mt-1">{stats.get('trials_count', 0)} trials, {stats.get('total_enrollment', 0):,} patients enrolled, {stats.get('recruiting_count', 0)} recruiting now</p>
      </div>
      <a href="https://clinicaltrials.gov/search?cond=Huntington+Disease&aggFilters=status:rec act" target="_blank" class="text-amber-700 text-sm font-medium flex items-center gap-1">ClinicalTrials.gov <span class="material-symbols-outlined text-sm">open_in_new</span></a>
    </div>
    <div class="bg-white border border-stone-200 rounded-xl overflow-x-auto">
      <table class="w-full text-left min-w-[700px]">
        <thead>
          <tr class="bg-[#f8f4e4] border-b border-stone-200">
            <th class="py-3 px-4 md:px-6 text-xs font-bold uppercase tracking-wider text-stone-700">NCT ID</th>
            <th class="py-3 px-4 md:px-6 text-xs font-bold uppercase tracking-wider text-stone-700">Title</th>
            <th class="py-3 px-4 md:px-6 text-xs font-bold uppercase tracking-wider text-stone-700">Sponsor</th>
            <th class="py-3 px-4 md:px-6 text-xs font-bold uppercase tracking-wider text-stone-700">Phase</th>
            <th class="py-3 px-4 md:px-6 text-xs font-bold uppercase tracking-wider text-stone-700">Status</th>
            <th class="py-3 px-4 md:px-6 text-xs font-bold uppercase tracking-wider text-stone-700">Intervention</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
{build_trials_html(trials)}
        </tbody>
      </table>
    </div>
  </div>
</section>

<!-- Research Ideas — our published hypotheses -->
<section id="ideas" class="py-16 px-4 md:px-8">
  <div class="max-w-5xl mx-auto">
    <div class="text-center mb-10">
      <div class="text-sm font-bold text-orange-600 uppercase tracking-wider mb-2">Open Research</div>
      <h2 class="text-2xl md:text-3xl font-bold text-stone-900">Published Research Ideas</h2>
      <p class="text-stone-700 mt-2 max-w-xl mx-auto">AI-assisted repurposing ideas with explicit uncertainty. These are starting points for review, not recommendations or validated findings.</p>
      <a href="experiment-1.html" class="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600 transition-colors">Read Experiment #1: Full Analysis <span class="material-symbols-outlined text-sm">arrow_forward</span></a>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
{build_hypotheses_html(hypotheses)}
    </div>
    <div class="mt-8 bg-orange-50 border border-orange-200 rounded-xl p-5 text-center">
      <p class="text-sm text-stone-800"><strong>Important:</strong> These hypotheses are triage artifacts, not evidence of efficacy. They have not been clinically validated, experimentally confirmed, or expert-reviewed unless explicitly stated.</p>
      <p class="text-sm text-stone-700 mt-2">These cards are generated from <code>data/hypotheses_tracker.json</code>, not hand-picked homepage copy. Are you an HD researcher? We'd love your feedback. <a href="https://github.com/jravinder/hd-research-agent/discussions" target="_blank" class="text-amber-700 underline font-medium">Review and discuss on GitHub</a></p>
    </div>
  </div>
</section>

<!-- No Tech Background? Start Here -->
<section class="py-12 px-4 md:px-8">
  <div class="max-w-5xl mx-auto">
    <div class="bg-gradient-to-br from-green-50 to-amber-50 border border-green-200 rounded-2xl p-6 md:p-8">
      <div class="flex flex-col md:flex-row gap-6 items-start">
        <div class="w-12 h-12 bg-green-500 rounded-xl flex items-center justify-center flex-shrink-0">
          <span class="material-symbols-outlined text-white text-2xl">waving_hand</span>
        </div>
        <div class="flex-1">
          <h2 class="text-xl font-bold text-stone-900 mb-2">Who This Is For</h2>
          <p class="text-stone-800 text-sm leading-relaxed mb-4">This is best viewed as <strong>open research infrastructure</strong>: a place where data scientists, AI engineers, bioinformaticians, and researchers can test whether agent workflows actually help with literature review, hypothesis triage, and research communication.</p>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div class="bg-white rounded-xl p-4 border border-stone-200">
              <div class="font-bold text-stone-900 text-sm mb-1">Data Scientists + AI/ML Engineers</div>
              <p class="text-xs text-stone-700 mb-2">Run our autonomous research agents. Fork the repo. Try different models. Add experiments. This is open-source infrastructure you can build on.</p>
            </div>
            <div class="bg-white rounded-xl p-4 border border-stone-200">
              <div class="font-bold text-stone-900 text-sm mb-1">Researchers + Domain Experts</div>
              <p class="text-xs text-stone-700 mb-2">Review our AI-generated hypotheses. Spot what's promising and what's wrong. Your expertise is what turns computational ideas into real science. <a href="https://github.com/jravinder/hd-research-agent/discussions" target="_blank" class="text-amber-700 underline">Join the discussion</a>.</p>
            </div>
            <div class="bg-white rounded-xl p-4 border border-stone-200">
              <div class="font-bold text-stone-900 text-sm mb-1">Students + Curious Builders</div>
              <p class="text-xs text-stone-700 mb-2">Want to learn how AI applies to drug discovery? Read our <a href="experiment-1.html" class="text-amber-700 underline">experiment reports</a> — we show every step, what worked, and what didn't. No PhD required to follow along.</p>
            </div>
          </div>
          <div class="bg-orange-50 border border-orange-200 rounded-lg p-3 mt-2">
            <p class="text-xs text-stone-800"><strong>For patients and families:</strong> This is not a medical resource. For support, guidance, and verified medical information, please go to <a href="https://hdsa.org" target="_blank" class="text-amber-700 underline font-medium">HDSA</a>, <a href="https://en.hdbuzz.net" target="_blank" class="text-amber-700 underline font-medium">HDBuzz</a>, or <a href="https://www.hdyo.org" target="_blank" class="text-amber-700 underline font-medium">HDYO</a>. They have doctors and scientists reviewing every word. We don't.</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- Resources — for people just learning or impacted -->
<section id="resources" class="py-16 px-4 md:px-8 bg-amber-50/30">
  <div class="max-w-5xl mx-auto">
    <div class="text-center mb-10">
      <div class="text-sm font-bold text-amber-700 uppercase tracking-wider mb-2">Trusted Organizations</div>
      <h2 class="text-2xl md:text-3xl font-bold text-stone-900">Resources for Patients, Families + Researchers</h2>
      <p class="text-stone-700 mt-2">These organizations are the real experts. We link to them because they do essential work.</p>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <a href="https://hdsa.org" target="_blank" class="bg-white border border-stone-200 rounded-xl p-6 hover:shadow-md hover:border-amber-300 transition-all group">
        <div class="text-lg font-bold text-stone-900 mb-1 group-hover:text-amber-700">HDSA</div>
        <div class="text-xs text-amber-700 font-medium mb-2">Support + Advocacy</div>
        <p class="text-sm text-stone-700">Huntington's Disease Society of America. Find local support groups, social workers, Centers of Excellence. The primary advocacy organization in the US.</p>
      </a>
      <a href="https://en.hdbuzz.net" target="_blank" class="bg-white border border-stone-200 rounded-xl p-6 hover:shadow-md hover:border-amber-300 transition-all group">
        <div class="text-lg font-bold text-stone-900 mb-1 group-hover:text-amber-700">HDBuzz</div>
        <div class="text-xs text-orange-600 font-medium mb-2">Research News in Plain Language</div>
        <p class="text-sm text-stone-700">Scientists explain HD research in words everyone can understand. The best place to follow new developments without needing a PhD.</p>
      </a>
      <a href="https://www.hdyo.org" target="_blank" class="bg-white border border-stone-200 rounded-xl p-6 hover:shadow-md hover:border-amber-300 transition-all group">
        <div class="text-lg font-bold text-stone-900 mb-1 group-hover:text-amber-700">HDYO</div>
        <div class="text-xs text-green-600 font-medium mb-2">Young People</div>
        <p class="text-sm text-stone-700">Huntington's Disease Youth Organization. Resources specifically for young people affected by HD — teens, young adults, and young families.</p>
      </a>
      <a href="https://www.enroll-hd.org" target="_blank" class="bg-white border border-stone-200 rounded-xl p-6 hover:shadow-md hover:border-amber-300 transition-all group">
        <div class="text-lg font-bold text-stone-900 mb-1 group-hover:text-amber-700">Enroll-HD</div>
        <div class="text-xs text-purple-600 font-medium mb-2">Join Research</div>
        <p class="text-sm text-stone-700">The world's largest observational study for HD families. Your data helps researchers understand HD and design better clinical trials.</p>
      </a>
      <a href="https://www.euro-hd.net" target="_blank" class="bg-white border border-stone-200 rounded-xl p-6 hover:shadow-md hover:border-amber-300 transition-all group">
        <div class="text-lg font-bold text-stone-900 mb-1 group-hover:text-amber-700">European HD Network</div>
        <div class="text-xs text-blue-600 font-medium mb-2">International Research</div>
        <p class="text-sm text-stone-700">EHDN coordinates HD research across Europe. Clinical trials, registries, and working groups advancing the science globally.</p>
      </a>
      <a href="https://hdreach.org" target="_blank" class="bg-white border border-stone-200 rounded-xl p-6 hover:shadow-md hover:border-amber-300 transition-all group">
        <div class="text-lg font-bold text-stone-900 mb-1 group-hover:text-amber-700">HD Reach</div>
        <div class="text-xs text-red-600 font-medium mb-2">Rehab + Exercise</div>
        <p class="text-sm text-stone-700">Evidence-based rehabilitation exercises designed for people with HD. Physical therapy, speech therapy, and occupational therapy resources.</p>
      </a>
    </div>
  </div>
</section>

<!-- Get Involved -->
<section id="involved" class="py-16 px-4 md:px-8">
  <div class="max-w-5xl mx-auto">
    <div class="text-center mb-10">
      <div class="text-sm font-bold text-green-600 uppercase tracking-wider mb-2">Make a Difference</div>
      <h2 class="text-2xl md:text-3xl font-bold text-stone-900">Ways to Get Involved</h2>
      <p class="text-stone-700 mt-2">Whether you're a patient, family member, researcher, developer, or just someone who cares.</p>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
      <div class="border border-green-200 bg-green-50/30 rounded-2xl p-6">
        <div class="flex items-center gap-3 mb-3">
          <div class="w-10 h-10 bg-green-500 rounded-xl flex items-center justify-center">
            <span class="material-symbols-outlined text-white text-xl">volunteer_activism</span>
          </div>
          <h3 class="text-lg font-bold text-stone-900">Join a Clinical Trial</h3>
        </div>
        <p class="text-sm text-stone-700 mb-3">{stats.get('recruiting_count', 0)} HD trials are actively recruiting right now. Your participation directly accelerates the path to treatment.</p>
        <a href="https://clinicaltrials.gov/search?cond=Huntington+Disease&aggFilters=status:rec" target="_blank" class="text-green-600 text-sm font-medium inline-flex items-center gap-1">Find recruiting trials <span class="material-symbols-outlined text-sm">open_in_new</span></a>
      </div>
      <div class="border border-amber-200 bg-amber-50/30 rounded-2xl p-6">
        <div class="flex items-center gap-3 mb-3">
          <div class="w-10 h-10 bg-amber-500 rounded-xl flex items-center justify-center">
            <span class="material-symbols-outlined text-white text-xl">code</span>
          </div>
          <h3 class="text-lg font-bold text-stone-900">Contribute to Open Source</h3>
        </div>
        <p class="text-sm text-stone-700 mb-3">Our research agent, literature scanner, and drug repurposing tools are all open source. Data scientists, ML engineers, and bioinformaticians welcome.</p>
        <a href="https://github.com/jravinder/hd-research-agent" target="_blank" class="text-amber-700 text-sm font-medium inline-flex items-center gap-1">View on GitHub <span class="material-symbols-outlined text-sm">open_in_new</span></a>
      </div>
      <div class="border border-orange-200 bg-orange-50/30 rounded-2xl p-6">
        <div class="flex items-center gap-3 mb-3">
          <div class="w-10 h-10 bg-orange-500 rounded-xl flex items-center justify-center">
            <span class="material-symbols-outlined text-white text-xl">record_voice_over</span>
          </div>
          <h3 class="text-lg font-bold text-stone-900">Share Your Story</h3>
        </div>
        <p class="text-sm text-stone-700 mb-3">Patient and family stories drive awareness and funding. Share your experience with HDSA or on social media to help others feel less alone.</p>
        <a href="https://hdsa.org/get-involved/" target="_blank" class="text-orange-600 text-sm font-medium inline-flex items-center gap-1">HDSA Get Involved <span class="material-symbols-outlined text-sm">open_in_new</span></a>
      </div>
      <div class="border border-purple-200 bg-purple-50/30 rounded-2xl p-6">
        <div class="flex items-center gap-3 mb-3">
          <div class="w-10 h-10 bg-purple-500 rounded-xl flex items-center justify-center">
            <span class="material-symbols-outlined text-white text-xl">favorite</span>
          </div>
          <h3 class="text-lg font-bold text-stone-900">Donate</h3>
        </div>
        <p class="text-sm text-stone-700 mb-3">Research funding saves lives. HDSA and CHDI Foundation fund the science that makes breakthroughs like AMT-130 possible.</p>
        <a href="https://hdsa.org/donate/" target="_blank" class="text-purple-600 text-sm font-medium inline-flex items-center gap-1">Donate to HDSA <span class="material-symbols-outlined text-sm">open_in_new</span></a>
      </div>
      <div class="border border-amber-200 bg-amber-50/30 rounded-2xl p-6">
        <div class="flex items-center gap-3 mb-3">
          <div class="w-10 h-10 bg-amber-500 rounded-xl flex items-center justify-center">
            <span class="material-symbols-outlined text-white text-xl">forum</span>
          </div>
          <h3 class="text-lg font-bold text-stone-900">Share Feedback or Ideas</h3>
        </div>
        <p class="text-sm text-stone-700 mb-3">Are you an HD researcher? See something interesting in our hypotheses? Spot an error? We want to hear from you — every correction makes this better.</p>
        <a href="https://github.com/jravinder/hd-research-agent/discussions" target="_blank" class="text-amber-700 text-sm font-medium inline-flex items-center gap-1">Join the Discussion <span class="material-symbols-outlined text-sm">open_in_new</span></a>
      </div>
    </div>
  </div>
</section>

<!-- Footer -->
<footer class="bg-stone-900 text-white py-12 px-4 md:px-8">
  <div class="max-w-5xl mx-auto">
    <div class="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
      <div>
        <p class="font-bold text-sm uppercase tracking-wider text-stone-600 mb-3">Explore</p>
        <div class="flex flex-col gap-2 text-sm">
          <a href="experiment-1.html" class="text-amber-400 hover:underline">Experiment #1</a>
          <a href="chat.html" class="text-amber-400 hover:underline">Ask HD Research</a>
          <a href="journey.html" class="text-amber-400 hover:underline">Our Journey</a>
          <a href="guide.html" class="text-amber-400 hover:underline">How to Use This</a>
        </div>
      </div>
      <div>
        <p class="font-bold text-sm uppercase tracking-wider text-stone-600 mb-3">About</p>
        <div class="flex flex-col gap-2 text-sm">
          <a href="about.html" class="text-amber-400 hover:underline">Why We Built This</a>
          <a href="https://github.com/jravinder/hd-research-agent" target="_blank" class="text-amber-400 hover:underline">GitHub (MIT License)</a>
          <a href="https://github.com/jravinder/hd-research-agent/issues" target="_blank" class="text-amber-400 hover:underline">Give Feedback</a>
        </div>
      </div>
      <div>
        <p class="font-bold text-sm uppercase tracking-wider text-stone-600 mb-3">Data Sources</p>
        <div class="flex flex-col gap-2 text-sm">
          <a href="https://pubmed.ncbi.nlm.nih.gov" target="_blank" class="text-amber-400 hover:underline">PubMed</a>
          <a href="https://clinicaltrials.gov" target="_blank" class="text-amber-400 hover:underline">ClinicalTrials.gov</a>
          <a href="https://en.hdbuzz.net" target="_blank" class="text-amber-400 hover:underline">HDBuzz</a>
          <a href="https://platform.opentargets.org" target="_blank" class="text-amber-400 hover:underline">Open Targets</a>
        </div>
      </div>
      <div>
        <p class="font-bold text-sm uppercase tracking-wider text-stone-600 mb-3">Legal</p>
        <div class="flex flex-col gap-2 text-sm">
          <a href="privacy.html" class="text-amber-400 hover:underline">Privacy Policy</a>
          <a href="terms.html" class="text-amber-400 hover:underline">Terms of Use</a>
        </div>
      </div>
    </div>
    <div class="border-t border-gray-800 pt-6 text-center">
      <p class="text-stone-700 text-xs leading-relaxed">This is a research and educational tool, not a medical product. Nothing on this site constitutes medical advice. Always consult qualified healthcare professionals. All data is sourced from publicly available databases and is refreshed daily. AI-generated hypotheses are exploratory and have not been clinically validated.</p>
    </div>
  </div>
</footer>

<!-- Translate: clean dropdown, no popups -->
<script>
function googleTranslateElementInit() {{
  new google.translate.TranslateElement({{
    pageLanguage: 'en',
    includedLanguages: 'en,hi,ta,te,bn,mr,kn,ml,gu,pa,ur,es,fr,de,ja,zh-CN,pt,ar,ko,it,ru',
    layout: google.translate.TranslateElement.InlineLayout.HORIZONTAL,
    autoDisplay: false,
    multilanguagePage: false
  }}, 'google_translate_element');
}}
</script>
<script src="https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit"></script>
<style>
  /* Hide Google Translate banner/popup cruft */
  .goog-te-banner-frame {{ display: none !important; }}
  body {{ top: 0 !important; }}
  .goog-te-gadget {{ font-size: 0 !important; }}
  .goog-te-gadget .goog-te-combo {{ font-size: 13px !important; padding: 4px 8px; border: 1px solid #e5e7eb; border-radius: 8px; background: white; color: #374151; outline: none; cursor: pointer; }}
  .goog-te-gadget > span {{ display: none !important; }}
  .goog-te-gadget img {{ display: none !important; }}
  #google_translate_element {{ line-height: 0; }}
  body > .skiptranslate {{ display: none !important; }}
  body {{ top: 0 !important; position: static !important; }}
</style>
</body></html>'''

    with open(INDEX_FILE, "w") as f:
        f.write(html)
    print(f"Generated {INDEX_FILE}")


def deploy():
    """Git commit and push to trigger Vercel auto-deploy."""
    import subprocess
    os.chdir(ROOT)
    subprocess.run(["git", "add", "data/data.json", "index.html"], check=True)

    # Check if there are changes
    result = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if result.returncode == 0:
        print("No changes to deploy.")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    subprocess.run(["git", "commit", "-m", f"Auto-update: fresh data from all sources ({now})"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("Deployed to Vercel via git push.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build HD Research Hub site from live data")
    parser.add_argument("--no-deploy", action="store_true", help="Skip git push")
    parser.add_argument("--refresh-data", action="store_true", help="Fetch fresh data before building the site")
    args = parser.parse_args()

    if args.refresh_data:
        from data_fetcher import run as fetch_data
        data = fetch_data()
    else:
        data = load_data()
    build_page(data)

    if not args.no_deploy:
        deploy()
