"""Build Site — regenerates index.html with fresh data from data.json.

Pulls real numbers from data.json (written by data_fetcher.py) and
injects them into the landing page. Then commits and pushes to trigger
Vercel auto-deploy.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

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


def build_papers_html(papers):
    """Build HTML for latest papers section."""
    if not papers:
        return ""
    cards = []
    for p in papers[:6]:
        journal = p.get("journal", "")[:40]
        date = p.get("pub_date", "")
        title = p.get("title", "")[:100]
        url = p.get("url", "#")
        abstract = p.get("abstract", "")[:200]
        cards.append(f'''
      <div class="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md transition-shadow">
        <div class="text-xs text-teal-600 font-bold uppercase mb-2">{date} — {journal}</div>
        <h3 class="text-base font-bold text-gray-900 mb-2">{title}</h3>
        <p class="text-gray-400 text-sm line-clamp-3">{abstract}</p>
        <a href="{url}" target="_blank" class="text-teal-600 text-sm font-medium mt-2 inline-flex items-center gap-1">PubMed <span class="material-symbols-outlined text-sm">open_in_new</span></a>
      </div>''')
    return "\n".join(cards)


def build_trials_html(trials):
    """Build HTML rows for trials table."""
    if not trials:
        return ""
    rows = []
    for t in trials[:10]:
        phase = t.get("phase", "N/A")
        status = t.get("status", "")
        status_color = "green" if status == "RECRUITING" else "teal" if "ACTIVE" in status else "gray"
        status_label = status.replace("_", " ").title()
        intervention = t.get("intervention", "")[:40]
        rows.append(f'''
          <tr class="hover:bg-teal-50/50 transition-colors">
            <td class="py-3 px-6 font-bold text-gray-900"><a href="{t.get('url','#')}" target="_blank" class="hover:text-teal-600">{t.get('nct_id','')}</a></td>
            <td class="py-3 px-6 text-gray-600 text-sm">{t.get('title','')[:50]}</td>
            <td class="py-3 px-6 text-gray-600 text-sm">{t.get('sponsor','')[:25]}</td>
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
        items.append(f'''
      <a href="{a.get('link','#')}" target="_blank" class="block border border-gray-200 rounded-xl p-5 hover:shadow-md hover:border-teal-300 transition-all">
        <div class="text-xs text-green-600 font-medium mb-1">{a.get('pub_date','')[:16]}</div>
        <h3 class="text-base font-bold text-gray-900">{a.get('title','')}</h3>
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

    html = f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>HD Research Hub</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
<style>body {{ font-family: 'Inter', sans-serif; }} .stat-card {{ transition: transform 0.2s; }} .stat-card:hover {{ transform: translateY(-2px); }}</style>
</head>
<body class="bg-white text-gray-900 antialiased">

<!-- Nav -->
<nav class="flex justify-between items-center px-8 h-16 border-b border-gray-100 sticky top-0 bg-white/95 backdrop-blur z-50">
  <div class="flex items-center gap-8">
    <span class="text-xl font-bold text-gray-900">HD Research Hub</span>
    <div class="hidden md:flex items-center gap-6 text-sm font-medium">
      <a href="#papers" class="text-teal-600 hover:text-teal-700">Papers</a>
      <a href="#trials" class="text-gray-500 hover:text-gray-900">Trials</a>
      <a href="#news" class="text-gray-500 hover:text-gray-900">HDBuzz</a>
      <a href="#targets" class="text-gray-500 hover:text-gray-900">Targets</a>
    </div>
  </div>
  <div class="flex items-center gap-3 text-xs text-gray-400">
    Updated {updated_str}
    <a href="https://github.com/jravinder/hd-research-agent" target="_blank" class="ml-3 px-3 py-1.5 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">GitHub</a>
  </div>
</nav>

<!-- Hero -->
<section class="pt-16 pb-16 px-8">
  <div class="max-w-5xl mx-auto text-center">
    <div class="inline-block px-3 py-1 bg-teal-50 text-teal-600 rounded-full text-sm font-medium mb-6">The Art of the Possible</div>
    <h1 class="text-5xl font-extrabold tracking-tight text-gray-900 mb-4">HD Research Hub</h1>
    <p class="text-lg text-gray-500 max-w-2xl mx-auto mb-10">A personal research dashboard pulling live data from PubMed, ClinicalTrials.gov, HDBuzz, and Open Targets. Exploring how AI can help accelerate Huntington's Disease research.</p>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto mb-10">
      <div class="stat-card bg-teal-50 border border-teal-100 rounded-xl p-4">
        <div class="text-2xl font-bold text-teal-600">{stats.get('papers_count', 0)}</div>
        <div class="text-xs text-teal-500 font-medium mt-1">Recent Papers</div>
      </div>
      <div class="stat-card bg-green-50 border border-green-100 rounded-xl p-4">
        <div class="text-2xl font-bold text-green-600">{stats.get('trials_count', 0)}</div>
        <div class="text-xs text-green-500 font-medium mt-1">Active Trials</div>
      </div>
      <div class="stat-card bg-orange-50 border border-orange-100 rounded-xl p-4">
        <div class="text-2xl font-bold text-orange-600">{stats.get('recruiting_count', 0)}</div>
        <div class="text-xs text-orange-500 font-medium mt-1">Recruiting Now</div>
      </div>
      <div class="stat-card bg-purple-50 border border-purple-100 rounded-xl p-4">
        <div class="text-2xl font-bold text-purple-600">{stats.get('targets_count', 0)}</div>
        <div class="text-xs text-purple-500 font-medium mt-1">Known Targets</div>
      </div>
    </div>
  </div>
</section>

<!-- Latest Papers -->
<section id="papers" class="py-16 px-8 bg-gray-50">
  <div class="max-w-5xl mx-auto">
    <div class="flex items-end justify-between mb-8">
      <div>
        <div class="text-sm font-bold text-teal-600 uppercase tracking-wider mb-1">From PubMed</div>
        <h2 class="text-2xl font-bold text-gray-900">Latest Research Papers</h2>
      </div>
      <a href="https://pubmed.ncbi.nlm.nih.gov/?term=huntington+disease+treatment" target="_blank" class="text-teal-600 text-sm font-medium flex items-center gap-1">View all on PubMed <span class="material-symbols-outlined text-sm">open_in_new</span></a>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
{build_papers_html(papers)}
    </div>
  </div>
</section>

<!-- Active Trials -->
<section id="trials" class="py-16 px-8">
  <div class="max-w-5xl mx-auto">
    <div class="flex items-end justify-between mb-8">
      <div>
        <div class="text-sm font-bold text-green-600 uppercase tracking-wider mb-1">Reasons for Optimism</div>
        <h2 class="text-2xl font-bold text-gray-900">Active Clinical Trials ({stats.get('trials_count', 0)} total, {stats.get('total_enrollment', 0)} patients)</h2>
      </div>
      <a href="https://clinicaltrials.gov/search?cond=Huntington+Disease&aggFilters=status:rec act" target="_blank" class="text-teal-600 text-sm font-medium flex items-center gap-1">ClinicalTrials.gov <span class="material-symbols-outlined text-sm">open_in_new</span></a>
    </div>
    <div class="bg-white border border-gray-200 rounded-xl overflow-x-auto">
      <table class="w-full text-left">
        <thead>
          <tr class="bg-gray-50 border-b border-gray-200">
            <th class="py-3 px-6 text-xs font-bold uppercase tracking-wider text-gray-500">NCT ID</th>
            <th class="py-3 px-6 text-xs font-bold uppercase tracking-wider text-gray-500">Title</th>
            <th class="py-3 px-6 text-xs font-bold uppercase tracking-wider text-gray-500">Sponsor</th>
            <th class="py-3 px-6 text-xs font-bold uppercase tracking-wider text-gray-500">Phase</th>
            <th class="py-3 px-6 text-xs font-bold uppercase tracking-wider text-gray-500">Status</th>
            <th class="py-3 px-6 text-xs font-bold uppercase tracking-wider text-gray-500">Intervention</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
{build_trials_html(trials)}
        </tbody>
      </table>
    </div>
  </div>
</section>

<!-- HDBuzz News -->
<section id="news" class="py-16 px-8 bg-gray-50">
  <div class="max-w-5xl mx-auto">
    <div class="flex items-end justify-between mb-8">
      <div>
        <div class="text-sm font-bold text-orange-600 uppercase tracking-wider mb-1">Community News</div>
        <h2 class="text-2xl font-bold text-gray-900">Latest from HDBuzz</h2>
      </div>
      <a href="https://en.hdbuzz.net" target="_blank" class="text-teal-600 text-sm font-medium flex items-center gap-1">Visit HDBuzz <span class="material-symbols-outlined text-sm">open_in_new</span></a>
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
{build_hdbuzz_html(hdbuzz)}
    </div>
  </div>
</section>

<!-- Targets -->
<section id="targets" class="py-16 px-8">
  <div class="max-w-5xl mx-auto">
    <div class="mb-8">
      <div class="text-sm font-bold text-purple-600 uppercase tracking-wider mb-1">From Open Targets</div>
      <h2 class="text-2xl font-bold text-gray-900">Top Associated Gene Targets</h2>
      <p class="text-gray-500 text-sm mt-1">Every target is a potential avenue for treatment. Data from <a href="https://platform.opentargets.org/disease/MONDO_0007739/associations" target="_blank" class="text-teal-600 underline">Open Targets</a>.</p>
    </div>
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
      {"".join(f'<div class="border border-gray-200 rounded-lg p-3 hover:border-purple-300 transition-colors"><span class="font-bold text-gray-900">{t.get("symbol","")}</span><div class="text-xs text-gray-400 mt-1">{t.get("name","")[:35]}</div><div class="text-xs text-purple-500 font-medium mt-1">Score: {t.get("score",0)}</div></div>' for t in targets[:16])}
    </div>
  </div>
</section>

<!-- Footer -->
<footer class="bg-gray-50 border-t border-gray-200 py-10 px-8">
  <div class="max-w-5xl mx-auto text-center">
    <p class="text-gray-900 font-bold mb-2">HD Research Hub</p>
    <p class="text-gray-400 text-sm mb-4">A personal research project exploring the art of the possible. Data refreshed automatically from public sources.</p>
    <div class="flex justify-center gap-6 text-sm mb-4">
      <a href="https://github.com/jravinder/hd-research-agent" target="_blank" class="text-teal-600 hover:underline">GitHub</a>
      <a href="https://hdsa.org" target="_blank" class="text-teal-600 hover:underline">HDSA</a>
      <a href="https://en.hdbuzz.net" target="_blank" class="text-teal-600 hover:underline">HDBuzz</a>
      <a href="https://clinicaltrials.gov" target="_blank" class="text-teal-600 hover:underline">ClinicalTrials.gov</a>
      <a href="https://pubmed.ncbi.nlm.nih.gov" target="_blank" class="text-teal-600 hover:underline">PubMed</a>
      <a href="https://platform.opentargets.org" target="_blank" class="text-teal-600 hover:underline">Open Targets</a>
    </div>
    <p class="text-gray-300 text-xs">Research tool for personal understanding, not medical advice. All data from public databases.</p>
  </div>
</footer>
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
    args = parser.parse_args()

    from data_fetcher import run as fetch_data
    data = fetch_data()
    build_page(data)

    if not args.no_deploy:
        deploy()
