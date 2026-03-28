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
INDEX_FILE = ROOT / "index.html"


def load_data():
    """Load data.json."""
    if not DATA_FILE.exists():
        print("No data.json found — run data_fetcher.py first")
        sys.exit(1)
    with open(DATA_FILE) as f:
        return json.load(f)


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
        "AI / ML": "teal", "clinical trial": "emerald", "protein structure": "indigo",
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
      <div class="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md transition-shadow">
        <div class="text-xs text-teal-600 font-bold uppercase mb-2">{date} — {journal}</div>
        {tags_html}
        <h3 class="text-base font-bold text-gray-900 mb-2">{title}</h3>
        <p class="text-gray-400 text-sm line-clamp-3">{abstract}</p>
        <a href="{url}" target="_blank" rel="noopener noreferrer" class="text-teal-600 text-sm font-medium mt-2 inline-flex items-center gap-1">PubMed <span class="material-symbols-outlined text-sm">open_in_new</span></a>
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
        status_color = "green" if status == "RECRUITING" else "teal" if "ACTIVE" in status else "gray"
        status_label = text(status.replace("_", " ").title())
        intervention = text(t.get("intervention", "")[:40])
        title = text(t.get("title", "")[:50])
        sponsor = text(t.get("sponsor", "")[:25])
        nct_id = text(t.get("nct_id", ""))
        url = sanitize_url(t.get("url", "#"))
        rows.append(f'''
          <tr class="hover:bg-teal-50/50 transition-colors">
            <td class="py-3 px-6 font-bold text-gray-900"><a href="{url}" target="_blank" rel="noopener noreferrer" class="hover:text-teal-600">{nct_id}</a></td>
            <td class="py-3 px-6 text-gray-600 text-sm">{title}</td>
            <td class="py-3 px-6 text-gray-600 text-sm">{sponsor}</td>
            <td class="py-3 px-6"><span class="px-2 py-1 bg-teal-100 text-teal-700 rounded-md text-xs font-medium">{phase}</span></td>
            <td class="py-3 px-6"><span class="px-2 py-1 bg-{status_color}-100 text-{status_color}-700 rounded-md text-xs font-medium">{status_label}</span></td>
            <td class="py-3 px-6 text-gray-500 text-sm">{intervention}</td>
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
      <a href="{link}" target="_blank" rel="noopener noreferrer" class="block border border-gray-200 rounded-xl p-5 hover:shadow-md hover:border-teal-300 transition-all">
        <div class="text-xs text-green-600 font-medium mb-1">{pub_date}</div>
        <h3 class="text-base font-bold text-gray-900">{title}</h3>
      </a>''')
    return "\n".join(items)


def build_page(data):
    """Generate the full index.html from data."""
    stats = data.get("stats", {})
    papers = data.get("papers", [])
    trials = data.get("trials", [])
    hdbuzz = data.get("hdbuzz", [])
    targets = data.get("targets", [])
    last_updated = data.get("last_updated", "")

    try:
        updated_str = datetime.fromisoformat(last_updated).strftime("%B %d, %Y at %I:%M %p")
    except Exception:
        updated_str = last_updated

    targets_html = ""
    if targets:
        targets_html = "".join(
            f'<div class="border border-gray-200 rounded-lg p-3 hover:border-purple-300 transition-colors"><span class="font-bold text-gray-900">{text(t.get("symbol", ""))}</span><div class="text-xs text-gray-400 mt-1">{text(t.get("name", "")[:35])}</div><div class="text-xs text-purple-500 font-medium mt-1">Score: {text(t.get("score", 0))}</div></div>'
            for t in targets[:16]
        )

    html = f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>HD Research Hub — AI-Powered Huntington's Disease Research</title>
<meta name="description" content="Open-source AI research dashboard exploring how data science and machine learning can accelerate Huntington's Disease drug discovery."/>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<style>
  body {{ font-family: 'Inter', sans-serif; }}
  .stat-card {{ transition: transform 0.2s; }}
  .stat-card:hover {{ transform: translateY(-2px); }}
  .glass {{ background: rgba(255,255,255,0.7); backdrop-filter: blur(12px); }}
  @media (max-width: 768px) {{
    .mobile-menu {{ display: none; }}
    .mobile-menu.active {{ display: flex; flex-direction: column; position: absolute; top: 64px; left: 0; right: 0; background: white; padding: 16px; border-bottom: 1px solid #f3f4f6; box-shadow: 0 4px 6px rgba(0,0,0,0.05); z-index: 100; }}
  }}
</style>
</head>
<body class="bg-white text-gray-900 antialiased">

<!-- Nav — mobile hamburger + language selector -->
<nav class="flex justify-between items-center px-4 md:px-8 h-16 border-b border-gray-100 sticky top-0 glass z-50">
  <div class="flex items-center gap-4 md:gap-8">
    <span class="text-lg md:text-xl font-bold text-gray-900">HD Research Hub</span>
    <button onclick="document.getElementById('mobile-nav').classList.toggle('active')" class="md:hidden p-2">
      <span class="material-symbols-outlined">menu</span>
    </button>
    <div id="mobile-nav" class="mobile-menu hidden md:flex items-center gap-6 text-sm font-medium">
      <a href="#papers" class="text-gray-500 hover:text-gray-900 py-2">Research</a>
      <a href="#trials" class="text-gray-500 hover:text-gray-900 py-2">Trials</a>
      <a href="#ideas" class="text-gray-500 hover:text-gray-900 py-2">Ideas</a>
      <a href="#resources" class="text-gray-500 hover:text-gray-900 py-2">Resources</a>
      <a href="about.html" class="text-gray-500 hover:text-gray-900 py-2">About</a>
      <a href="chat.html" class="text-teal-600 font-semibold hover:text-teal-700 py-2 flex items-center gap-1"><span class="material-symbols-outlined text-sm">chat</span> Ask HD Research</a>
    </div>
  </div>
  <div class="flex items-center gap-2">
    <!-- Google Translate -->
    <div id="google_translate_element" class="scale-90"></div>
    <a href="https://github.com/jravinder/hd-research-agent" target="_blank" class="hidden md:flex px-3 py-1.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 items-center gap-1">
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
      GitHub
    </a>
  </div>
</nav>

<!-- Hero -->
<section class="pt-12 md:pt-20 pb-16 px-4 md:px-8 bg-gradient-to-b from-teal-50/50 to-white">
  <div class="max-w-5xl mx-auto text-center">
    <div class="inline-block px-4 py-1.5 bg-teal-100 text-teal-700 rounded-full text-sm font-semibold mb-6">The Art of the Possible</div>
    <h1 class="text-4xl md:text-6xl font-extrabold tracking-tight text-gray-900 mb-4">HD Research Hub</h1>
    <p class="text-lg md:text-xl text-gray-500 max-w-2xl mx-auto mb-4 leading-relaxed">
      What if AI could help us find treatments faster?
    </p>
    <p class="text-base text-gray-400 max-w-xl mx-auto mb-10">
      This is an open-source research dashboard exploring how data science, machine learning, and autonomous agents can accelerate Huntington's Disease drug discovery. Real data. Published ideas. Open to all.
    </p>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4 max-w-3xl mx-auto mb-10">
      <div class="stat-card bg-teal-50 border border-teal-200 rounded-xl p-4">
        <div class="text-2xl md:text-3xl font-bold text-teal-600">{stats.get('papers_count', 0)}</div>
        <div class="text-xs text-teal-500 font-medium mt-1">Recent Papers</div>
      </div>
      <div class="stat-card bg-green-50 border border-green-200 rounded-xl p-4">
        <div class="text-2xl md:text-3xl font-bold text-green-600">{stats.get('trials_count', 0)}</div>
        <div class="text-xs text-green-500 font-medium mt-1">Active Trials</div>
      </div>
      <div class="stat-card bg-orange-50 border border-orange-200 rounded-xl p-4">
        <div class="text-2xl md:text-3xl font-bold text-orange-500">{stats.get('recruiting_count', 0)}</div>
        <div class="text-xs text-orange-500 font-medium mt-1">Recruiting Now</div>
      </div>
      <div class="stat-card bg-purple-50 border border-purple-200 rounded-xl p-4">
        <div class="text-2xl md:text-3xl font-bold text-purple-600">{stats.get('targets_count', 0) or '16+'}</div>
        <div class="text-xs text-purple-500 font-medium mt-1">Known Targets</div>
      </div>
    </div>
    <p class="text-xs text-gray-300">Updated {updated_str} — auto-refreshed daily from PubMed, ClinicalTrials.gov, HDBuzz, Open Targets</p>
  </div>
</section>

<!-- AI + HD: What makes this site unique -->
<section id="ai-lens" class="py-16 px-4 md:px-8">
  <div class="max-w-5xl mx-auto">
    <div class="text-center mb-12">
      <div class="text-sm font-bold text-teal-600 uppercase tracking-wider mb-2">What Makes This Different</div>
      <h2 class="text-2xl md:text-3xl font-bold text-gray-900">An AI + Data Science Lens on HD</h2>
      <p class="text-gray-500 mt-2 max-w-xl mx-auto">We're not duplicating what HDSA and HDBuzz do brilliantly. We're asking: what can AI uniquely contribute?</p>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
      <div class="bg-gradient-to-br from-teal-50 to-teal-100/50 border border-teal-200 rounded-2xl p-6">
        <div class="w-11 h-11 bg-teal-500 rounded-xl flex items-center justify-center mb-4">
          <span class="material-symbols-outlined text-white">auto_awesome</span>
        </div>
        <h3 class="text-lg font-bold text-gray-900 mb-2">Autonomous Research Agent</h3>
        <p class="text-gray-500 text-sm">Our AI agent runs overnight — generating hypotheses, searching PubMed, scoring drug candidates, refining. Hundreds of experiments while you sleep.</p>
        <a href="https://github.com/jravinder/hd-research-agent" target="_blank" class="text-teal-600 text-sm font-medium mt-3 inline-flex items-center gap-1">See the code <span class="material-symbols-outlined text-sm">open_in_new</span></a>
      </div>
      <div class="bg-gradient-to-br from-orange-50 to-orange-100/50 border border-orange-200 rounded-2xl p-6">
        <div class="w-11 h-11 bg-orange-500 rounded-xl flex items-center justify-center mb-4">
          <span class="material-symbols-outlined text-white">biotech</span>
        </div>
        <h3 class="text-lg font-bold text-gray-900 mb-2">Drug Repurposing via AI</h3>
        <p class="text-gray-500 text-sm">Cross-referencing 16 HD targets against thousands of FDA-approved drugs. If a treatment already exists for something else, maybe it can help HD too — and skip years of safety testing.</p>
        <a href="#ideas" class="text-orange-600 text-sm font-medium mt-3 inline-flex items-center gap-1">See candidates below <span class="material-symbols-outlined text-sm">arrow_downward</span></a>
      </div>
      <div class="bg-gradient-to-br from-green-50 to-green-100/50 border border-green-200 rounded-2xl p-6">
        <div class="w-11 h-11 bg-green-500 rounded-xl flex items-center justify-center mb-4">
          <span class="material-symbols-outlined text-white">diversity_3</span>
        </div>
        <h3 class="text-lg font-bold text-gray-900 mb-2">Digital Twins for Trials</h3>
        <p class="text-gray-500 text-sm">AI-simulated patient controls could accelerate clinical trials by reducing the need for traditional placebo arms. Companies like Unlearn are pioneering this for HD.</p>
      </div>
    </div>
  </div>
</section>

<!-- HD News — combining HDBuzz + recent breakthroughs -->
<section id="news" class="py-16 px-4 md:px-8 bg-gray-50">
  <div class="max-w-5xl mx-auto">
    <div class="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-2">
      <div>
        <div class="text-sm font-bold text-orange-600 uppercase tracking-wider mb-1">What's Happening Now</div>
        <h2 class="text-2xl md:text-3xl font-bold text-gray-900">HD News + Breakthroughs</h2>
      </div>
      <a href="https://en.hdbuzz.net" target="_blank" class="text-teal-600 text-sm font-medium flex items-center gap-1">More on HDBuzz <span class="material-symbols-outlined text-sm">open_in_new</span></a>
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
        <div class="text-sm font-bold text-teal-600 uppercase tracking-wider mb-1">Fresh from PubMed</div>
        <h2 class="text-2xl md:text-3xl font-bold text-gray-900">Latest Research Papers</h2>
      </div>
      <a href="https://pubmed.ncbi.nlm.nih.gov/?term=huntington+disease+treatment" target="_blank" class="text-teal-600 text-sm font-medium flex items-center gap-1">All HD papers <span class="material-symbols-outlined text-sm">open_in_new</span></a>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
{build_papers_html(papers)}
    </div>
  </div>
</section>

<!-- Active Trials -->
<section id="trials" class="py-16 px-4 md:px-8 bg-gray-50">
  <div class="max-w-5xl mx-auto">
    <div class="flex flex-col md:flex-row md:items-end justify-between mb-8 gap-2">
      <div>
        <div class="text-sm font-bold text-green-600 uppercase tracking-wider mb-1">Reasons for Optimism</div>
        <h2 class="text-2xl md:text-3xl font-bold text-gray-900">Active Clinical Trials</h2>
        <p class="text-gray-500 text-sm mt-1">{stats.get('trials_count', 0)} trials, {stats.get('total_enrollment', 0):,} patients enrolled, {stats.get('recruiting_count', 0)} recruiting now</p>
      </div>
      <a href="https://clinicaltrials.gov/search?cond=Huntington+Disease&aggFilters=status:rec act" target="_blank" class="text-teal-600 text-sm font-medium flex items-center gap-1">ClinicalTrials.gov <span class="material-symbols-outlined text-sm">open_in_new</span></a>
    </div>
    <div class="bg-white border border-gray-200 rounded-xl overflow-x-auto">
      <table class="w-full text-left min-w-[700px]">
        <thead>
          <tr class="bg-gray-50 border-b border-gray-200">
            <th class="py-3 px-4 md:px-6 text-xs font-bold uppercase tracking-wider text-gray-500">NCT ID</th>
            <th class="py-3 px-4 md:px-6 text-xs font-bold uppercase tracking-wider text-gray-500">Title</th>
            <th class="py-3 px-4 md:px-6 text-xs font-bold uppercase tracking-wider text-gray-500">Sponsor</th>
            <th class="py-3 px-4 md:px-6 text-xs font-bold uppercase tracking-wider text-gray-500">Phase</th>
            <th class="py-3 px-4 md:px-6 text-xs font-bold uppercase tracking-wider text-gray-500">Status</th>
            <th class="py-3 px-4 md:px-6 text-xs font-bold uppercase tracking-wider text-gray-500">Intervention</th>
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
      <h2 class="text-2xl md:text-3xl font-bold text-gray-900">Published Research Ideas</h2>
      <p class="text-gray-500 mt-2 max-w-xl mx-auto">AI-generated drug repurposing hypotheses from our autonomous research agent. These are ideas worth exploring — not medical claims. All open for the community to build on.</p>
      <a href="experiment-1.html" class="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-teal-500 text-white rounded-lg text-sm font-medium hover:bg-teal-600 transition-colors">Read Experiment #1: Full Analysis <span class="material-symbols-outlined text-sm">arrow_forward</span></a>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div class="border border-teal-200 bg-teal-50/30 rounded-xl p-5 hover:shadow-md transition-shadow">
        <div class="flex items-center justify-between mb-3">
          <span class="text-lg font-bold text-gray-900">Metformin</span>
          <span class="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">Preclinical data</span>
        </div>
        <div class="text-sm text-teal-600 font-medium mb-2">Target: mTOR / AMPK</div>
        <p class="text-sm text-gray-500">Promotes autophagy — the cell's self-cleaning mechanism. May help clear mutant HTT protein aggregates. Already FDA-approved for diabetes with well-known safety profile.</p>
        <div class="mt-3 text-xs text-gray-400">Hypothesis score: 72/100</div>
      </div>
      <div class="border border-teal-200 bg-teal-50/30 rounded-xl p-5 hover:shadow-md transition-shadow">
        <div class="flex items-center justify-between mb-3">
          <span class="text-lg font-bold text-gray-900">Rapamycin</span>
          <span class="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">Preclinical data</span>
        </div>
        <div class="text-sm text-teal-600 font-medium mb-2">Target: mTOR</div>
        <p class="text-sm text-gray-500">mTOR inhibitor — has demonstrated clearance of mutant HTT in preclinical HD models. Strong mechanistic rationale for inducing autophagy of toxic protein aggregates.</p>
        <div class="mt-3 text-xs text-gray-400">Hypothesis score: 68/100</div>
      </div>
      <div class="border border-orange-200 bg-orange-50/30 rounded-xl p-5 hover:shadow-md transition-shadow">
        <div class="flex items-center justify-between mb-3">
          <span class="text-lg font-bold text-gray-900">Bevantolol (SOM3355)</span>
          <span class="px-2 py-0.5 bg-teal-100 text-teal-700 rounded text-xs font-medium">Phase II</span>
        </div>
        <div class="text-sm text-orange-600 font-medium mb-2">Target: Chorea</div>
        <p class="text-sm text-gray-500">AI-discovered by SOM Biotech using their SOMAIPRO platform. Beta-blocker repurposed for HD chorea. Proof that AI drug repurposing works in practice.</p>
        <div class="mt-3 text-xs text-gray-400">Already in clinical trials</div>
      </div>
      <div class="border border-green-200 bg-green-50/30 rounded-xl p-5 hover:shadow-md transition-shadow">
        <div class="flex items-center justify-between mb-3">
          <span class="text-lg font-bold text-gray-900">CBD</span>
          <span class="px-2 py-0.5 bg-teal-100 text-teal-700 rounded text-xs font-medium">Early human data</span>
        </div>
        <div class="text-sm text-green-600 font-medium mb-2">Target: CB1 / CB2 receptors</div>
        <p class="text-sm text-gray-500">Cannabinoid receptors are lost early in HD. Early human trial data suggests potential for slowing progression. CB2 modulation may also address neuroinflammation.</p>
        <div class="mt-3 text-xs text-gray-400">Hypothesis score: 61/100</div>
      </div>
      <div class="border border-purple-200 bg-purple-50/30 rounded-xl p-5 hover:shadow-md transition-shadow">
        <div class="flex items-center justify-between mb-3">
          <span class="text-lg font-bold text-gray-900">Vorinostat (SAHA)</span>
          <span class="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">Preclinical</span>
        </div>
        <div class="text-sm text-purple-600 font-medium mb-2">Target: HDAC</div>
        <p class="text-sm text-gray-500">HDAC inhibitor addressing epigenetic dysregulation in HD. Already FDA-approved for lymphoma. May restore gene expression patterns disrupted by mutant HTT.</p>
        <div class="mt-3 text-xs text-gray-400">Hypothesis score: 64/100</div>
      </div>
      <div class="border border-gray-200 bg-gray-50/30 rounded-xl p-5 hover:shadow-md transition-shadow">
        <div class="flex items-center justify-between mb-3">
          <span class="text-lg font-bold text-gray-900">Simvastatin</span>
          <span class="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">Preclinical</span>
        </div>
        <div class="text-sm text-gray-600 font-medium mb-2">Target: BDNF</div>
        <p class="text-sm text-gray-500">Common statin that increases brain-derived neurotrophic factor (BDNF) — critically reduced in HD. BDNF supports the survival of neurons most vulnerable in HD.</p>
        <div class="mt-3 text-xs text-gray-400">Hypothesis score: 58/100</div>
      </div>
    </div>
    <div class="mt-8 bg-orange-50 border border-orange-200 rounded-xl p-5 text-center">
      <p class="text-sm text-gray-600"><strong>Important:</strong> These hypotheses are AI-generated starting points — not validated findings. They have not been reviewed by HD domain experts or tested experimentally. We publish them openly for the community to evaluate.</p>
      <p class="text-sm text-gray-500 mt-2">Are you an HD researcher? We'd love your feedback. <a href="https://github.com/jravinder/hd-research-agent/discussions" target="_blank" class="text-teal-600 underline font-medium">Review and discuss on GitHub</a></p>
    </div>
  </div>
</section>

<!-- No Tech Background? Start Here -->
<section class="py-12 px-4 md:px-8">
  <div class="max-w-5xl mx-auto">
    <div class="bg-gradient-to-br from-green-50 to-teal-50 border border-green-200 rounded-2xl p-6 md:p-8">
      <div class="flex flex-col md:flex-row gap-6 items-start">
        <div class="w-12 h-12 bg-green-500 rounded-xl flex items-center justify-center flex-shrink-0">
          <span class="material-symbols-outlined text-white text-2xl">waving_hand</span>
        </div>
        <div class="flex-1">
          <h2 class="text-xl font-bold text-gray-900 mb-2">New to AI or HD Research? You Belong Here.</h2>
          <p class="text-gray-600 text-sm leading-relaxed mb-4">You don't need to know anything about AI, machine learning, or coding to use this site. We built it for everyone — patients, families, students, caregivers, and anyone who's curious. Here's how to start:</p>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div class="bg-white rounded-xl p-4 border border-gray-200">
              <div class="font-bold text-gray-900 text-sm mb-1">Just want to understand HD?</div>
              <p class="text-xs text-gray-500 mb-2">Start with <a href="https://en.hdbuzz.net" target="_blank" class="text-teal-600 underline">HDBuzz</a> — scientists explain HD research in plain language. Then come back here to see what's in the treatment pipeline.</p>
            </div>
            <div class="bg-white rounded-xl p-4 border border-gray-200">
              <div class="font-bold text-gray-900 text-sm mb-1">Have a question?</div>
              <p class="text-xs text-gray-500 mb-2">Ask our <a href="chat.html" class="text-teal-600 underline">AI research assistant</a>. Type in plain English — no jargon needed. It will answer using real research papers and cite its sources.</p>
            </div>
            <div class="bg-white rounded-xl p-4 border border-gray-200">
              <div class="font-bold text-gray-900 text-sm mb-1">Want to help but not technical?</div>
              <p class="text-xs text-gray-500 mb-2">Share this site with someone who might benefit. <a href="https://www.enroll-hd.org" target="_blank" class="text-teal-600 underline">Join Enroll-HD</a>. <a href="https://hdsa.org/get-involved/" target="_blank" class="text-teal-600 underline">Volunteer with HDSA</a>. Your story and data matter more than code.</p>
            </div>
          </div>
          <p class="text-xs text-gray-400">This site uses AI to read research papers and suggest ideas for scientists to explore. We explain how everything works in our <a href="guide.html" class="text-teal-600 underline">beginner's guide</a>. No expertise required.</p>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- Resources — for people just learning or impacted -->
<section id="resources" class="py-16 px-4 md:px-8 bg-teal-50/30">
  <div class="max-w-5xl mx-auto">
    <div class="text-center mb-10">
      <div class="text-sm font-bold text-teal-600 uppercase tracking-wider mb-2">Trusted Organizations</div>
      <h2 class="text-2xl md:text-3xl font-bold text-gray-900">Resources for Patients, Families + Researchers</h2>
      <p class="text-gray-500 mt-2">These organizations are the real experts. We link to them because they do essential work.</p>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <a href="https://hdsa.org" target="_blank" class="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-md hover:border-teal-300 transition-all group">
        <div class="text-lg font-bold text-gray-900 mb-1 group-hover:text-teal-600">HDSA</div>
        <div class="text-xs text-teal-600 font-medium mb-2">Support + Advocacy</div>
        <p class="text-sm text-gray-500">Huntington's Disease Society of America. Find local support groups, social workers, Centers of Excellence. The primary advocacy organization in the US.</p>
      </a>
      <a href="https://en.hdbuzz.net" target="_blank" class="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-md hover:border-teal-300 transition-all group">
        <div class="text-lg font-bold text-gray-900 mb-1 group-hover:text-teal-600">HDBuzz</div>
        <div class="text-xs text-orange-600 font-medium mb-2">Research News in Plain Language</div>
        <p class="text-sm text-gray-500">Scientists explain HD research in words everyone can understand. The best place to follow new developments without needing a PhD.</p>
      </a>
      <a href="https://www.hdyo.org" target="_blank" class="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-md hover:border-teal-300 transition-all group">
        <div class="text-lg font-bold text-gray-900 mb-1 group-hover:text-teal-600">HDYO</div>
        <div class="text-xs text-green-600 font-medium mb-2">Young People</div>
        <p class="text-sm text-gray-500">Huntington's Disease Youth Organization. Resources specifically for young people affected by HD — teens, young adults, and young families.</p>
      </a>
      <a href="https://www.enroll-hd.org" target="_blank" class="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-md hover:border-teal-300 transition-all group">
        <div class="text-lg font-bold text-gray-900 mb-1 group-hover:text-teal-600">Enroll-HD</div>
        <div class="text-xs text-purple-600 font-medium mb-2">Join Research</div>
        <p class="text-sm text-gray-500">The world's largest observational study for HD families. Your data helps researchers understand HD and design better clinical trials.</p>
      </a>
      <a href="https://www.euro-hd.net" target="_blank" class="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-md hover:border-teal-300 transition-all group">
        <div class="text-lg font-bold text-gray-900 mb-1 group-hover:text-teal-600">European HD Network</div>
        <div class="text-xs text-blue-600 font-medium mb-2">International Research</div>
        <p class="text-sm text-gray-500">EHDN coordinates HD research across Europe. Clinical trials, registries, and working groups advancing the science globally.</p>
      </a>
      <a href="https://hdreach.org" target="_blank" class="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-md hover:border-teal-300 transition-all group">
        <div class="text-lg font-bold text-gray-900 mb-1 group-hover:text-teal-600">HD Reach</div>
        <div class="text-xs text-red-600 font-medium mb-2">Rehab + Exercise</div>
        <p class="text-sm text-gray-500">Evidence-based rehabilitation exercises designed for people with HD. Physical therapy, speech therapy, and occupational therapy resources.</p>
      </a>
    </div>
  </div>
</section>

<!-- Get Involved -->
<section id="involved" class="py-16 px-4 md:px-8">
  <div class="max-w-5xl mx-auto">
    <div class="text-center mb-10">
      <div class="text-sm font-bold text-green-600 uppercase tracking-wider mb-2">Make a Difference</div>
      <h2 class="text-2xl md:text-3xl font-bold text-gray-900">Ways to Get Involved</h2>
      <p class="text-gray-500 mt-2">Whether you're a patient, family member, researcher, developer, or just someone who cares.</p>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
      <div class="border border-green-200 bg-green-50/30 rounded-2xl p-6">
        <div class="flex items-center gap-3 mb-3">
          <div class="w-10 h-10 bg-green-500 rounded-xl flex items-center justify-center">
            <span class="material-symbols-outlined text-white text-xl">volunteer_activism</span>
          </div>
          <h3 class="text-lg font-bold text-gray-900">Join a Clinical Trial</h3>
        </div>
        <p class="text-sm text-gray-500 mb-3">{stats.get('recruiting_count', 0)} HD trials are actively recruiting right now. Your participation directly accelerates the path to treatment.</p>
        <a href="https://clinicaltrials.gov/search?cond=Huntington+Disease&aggFilters=status:rec" target="_blank" class="text-green-600 text-sm font-medium inline-flex items-center gap-1">Find recruiting trials <span class="material-symbols-outlined text-sm">open_in_new</span></a>
      </div>
      <div class="border border-teal-200 bg-teal-50/30 rounded-2xl p-6">
        <div class="flex items-center gap-3 mb-3">
          <div class="w-10 h-10 bg-teal-500 rounded-xl flex items-center justify-center">
            <span class="material-symbols-outlined text-white text-xl">code</span>
          </div>
          <h3 class="text-lg font-bold text-gray-900">Contribute to Open Source</h3>
        </div>
        <p class="text-sm text-gray-500 mb-3">Our research agent, literature scanner, and drug repurposing tools are all open source. Data scientists, ML engineers, and bioinformaticians welcome.</p>
        <a href="https://github.com/jravinder/hd-research-agent" target="_blank" class="text-teal-600 text-sm font-medium inline-flex items-center gap-1">View on GitHub <span class="material-symbols-outlined text-sm">open_in_new</span></a>
      </div>
      <div class="border border-orange-200 bg-orange-50/30 rounded-2xl p-6">
        <div class="flex items-center gap-3 mb-3">
          <div class="w-10 h-10 bg-orange-500 rounded-xl flex items-center justify-center">
            <span class="material-symbols-outlined text-white text-xl">record_voice_over</span>
          </div>
          <h3 class="text-lg font-bold text-gray-900">Share Your Story</h3>
        </div>
        <p class="text-sm text-gray-500 mb-3">Patient and family stories drive awareness and funding. Share your experience with HDSA or on social media to help others feel less alone.</p>
        <a href="https://hdsa.org/get-involved/" target="_blank" class="text-orange-600 text-sm font-medium inline-flex items-center gap-1">HDSA Get Involved <span class="material-symbols-outlined text-sm">open_in_new</span></a>
      </div>
      <div class="border border-purple-200 bg-purple-50/30 rounded-2xl p-6">
        <div class="flex items-center gap-3 mb-3">
          <div class="w-10 h-10 bg-purple-500 rounded-xl flex items-center justify-center">
            <span class="material-symbols-outlined text-white text-xl">favorite</span>
          </div>
          <h3 class="text-lg font-bold text-gray-900">Donate</h3>
        </div>
        <p class="text-sm text-gray-500 mb-3">Research funding saves lives. HDSA and CHDI Foundation fund the science that makes breakthroughs like AMT-130 possible.</p>
        <a href="https://hdsa.org/donate/" target="_blank" class="text-purple-600 text-sm font-medium inline-flex items-center gap-1">Donate to HDSA <span class="material-symbols-outlined text-sm">open_in_new</span></a>
      </div>
      <div class="border border-teal-200 bg-teal-50/30 rounded-2xl p-6">
        <div class="flex items-center gap-3 mb-3">
          <div class="w-10 h-10 bg-teal-500 rounded-xl flex items-center justify-center">
            <span class="material-symbols-outlined text-white text-xl">forum</span>
          </div>
          <h3 class="text-lg font-bold text-gray-900">Share Feedback or Ideas</h3>
        </div>
        <p class="text-sm text-gray-500 mb-3">Are you an HD researcher? See something interesting in our hypotheses? Spot an error? We want to hear from you — every correction makes this better.</p>
        <a href="https://github.com/jravinder/hd-research-agent/discussions" target="_blank" class="text-teal-600 text-sm font-medium inline-flex items-center gap-1">Join the Discussion <span class="material-symbols-outlined text-sm">open_in_new</span></a>
      </div>
    </div>
  </div>
</section>

<!-- Footer -->
<footer class="bg-gray-900 text-white py-12 px-4 md:px-8">
  <div class="max-w-5xl mx-auto">
    <div class="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
      <div>
        <p class="font-bold text-sm uppercase tracking-wider text-gray-400 mb-3">Explore</p>
        <div class="flex flex-col gap-2 text-sm">
          <a href="experiment-1.html" class="text-teal-400 hover:underline">Experiment #1</a>
          <a href="chat.html" class="text-teal-400 hover:underline">Ask HD Research</a>
          <a href="journey.html" class="text-teal-400 hover:underline">Our Journey</a>
          <a href="guide.html" class="text-teal-400 hover:underline">How to Use This</a>
        </div>
      </div>
      <div>
        <p class="font-bold text-sm uppercase tracking-wider text-gray-400 mb-3">About</p>
        <div class="flex flex-col gap-2 text-sm">
          <a href="about.html" class="text-teal-400 hover:underline">Why We Built This</a>
          <a href="https://github.com/jravinder/hd-research-agent" target="_blank" class="text-teal-400 hover:underline">GitHub (MIT License)</a>
          <a href="https://github.com/jravinder/hd-research-agent/issues" target="_blank" class="text-teal-400 hover:underline">Give Feedback</a>
        </div>
      </div>
      <div>
        <p class="font-bold text-sm uppercase tracking-wider text-gray-400 mb-3">Data Sources</p>
        <div class="flex flex-col gap-2 text-sm">
          <a href="https://pubmed.ncbi.nlm.nih.gov" target="_blank" class="text-teal-400 hover:underline">PubMed</a>
          <a href="https://clinicaltrials.gov" target="_blank" class="text-teal-400 hover:underline">ClinicalTrials.gov</a>
          <a href="https://en.hdbuzz.net" target="_blank" class="text-teal-400 hover:underline">HDBuzz</a>
          <a href="https://platform.opentargets.org" target="_blank" class="text-teal-400 hover:underline">Open Targets</a>
        </div>
      </div>
      <div>
        <p class="font-bold text-sm uppercase tracking-wider text-gray-400 mb-3">Legal</p>
        <div class="flex flex-col gap-2 text-sm">
          <a href="privacy.html" class="text-teal-400 hover:underline">Privacy Policy</a>
          <a href="terms.html" class="text-teal-400 hover:underline">Terms of Use</a>
        </div>
      </div>
    </div>
    <div class="border-t border-gray-800 pt-6 text-center">
      <p class="text-gray-500 text-xs leading-relaxed">This is a research and educational tool, not a medical product. Nothing on this site constitutes medical advice. Always consult qualified healthcare professionals. All data is sourced from publicly available databases and is refreshed daily. AI-generated hypotheses are exploratory and have not been clinically validated.</p>
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
  .skiptranslate {{ display: none !important; }}
  body {{ top: 0 !important; }}
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
