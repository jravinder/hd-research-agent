"""Wiki Compiler Agent — reads experiment results + corpus, updates wiki pages.

Closes the autoresearch loop: experiments generate data, this agent
compiles it into the wiki, wiki feeds back into next experiment's context.

Runs after every experiment or agent run.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DATA_DIR = ROOT / "data"
WIKI_DIR = ROOT / "wiki"


def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def compile_targets():
    """Compile all targets from all experiments into wiki/targets.md."""
    all_targets = {}

    # Scan all experiment results
    for f in sorted(DATA_DIR.glob("experiment_*_results.json")):
        exp = load_json(f)
        exp_id = f.stem.replace("_results", "").replace("experiment_", "EXP-")

        for analysis in exp.get("analyses", []):
            an = analysis.get("analysis", {})
            for target in an.get("targets", []):
                t = target.strip()
                if not t or len(t) < 3:
                    continue
                key = t.lower()
                if key not in all_targets:
                    all_targets[key] = {"name": t, "experiments": [], "count": 0}
                if exp_id not in all_targets[key]["experiments"]:
                    all_targets[key]["experiments"].append(exp_id)
                all_targets[key]["count"] += 1

    # Sort by frequency
    sorted_targets = sorted(all_targets.values(), key=lambda x: x["count"], reverse=True)

    # Write wiki page
    md = "# Molecular Targets\n\n"
    md += f"*Auto-compiled from {len(list(DATA_DIR.glob('experiment_*_results.json')))} experiments on {datetime.now().strftime('%Y-%m-%d')}*\n\n"
    md += "| Target | Mentions | Found In |\n"
    md += "|--------|----------|----------|\n"
    for t in sorted_targets[:30]:
        exps = ", ".join(t["experiments"])
        md += f"| {t['name']} | {t['count']} | {exps} |\n"

    (WIKI_DIR / "targets.md").write_text(md)
    print(f"  targets.md: {len(sorted_targets)} targets compiled")
    return sorted_targets


def compile_hypotheses():
    """Compile all hypotheses from experiments + tracker into wiki/hypotheses.md."""
    all_hypotheses = []

    # From experiment results
    for f in sorted(DATA_DIR.glob("experiment_*_results.json")):
        exp = load_json(f)
        exp_id = f.stem.replace("_results", "").replace("experiment_", "EXP-")

        for h in exp.get("synthesis", {}).get("new_hypotheses", []):
            if isinstance(h, dict) and h.get("hypothesis"):
                all_hypotheses.append({
                    "hypothesis": h.get("hypothesis", ""),
                    "score": h.get("score", 0),
                    "source": exp_id,
                    "drug": h.get("drug", ""),
                    "target": h.get("hd_target", h.get("target", "")),
                })

    # From tracker
    tracker = load_json(DATA_DIR / "hypotheses_tracker.json")
    for h in tracker.get("hypotheses", []):
        all_hypotheses.append({
            "hypothesis": h.get("rationale", ""),
            "score": h.get("scores", [0])[-1] if h.get("scores") else 0,
            "source": "Tracker",
            "drug": h.get("drug", ""),
            "target": h.get("target", ""),
        })

    # Dedupe by drug name
    seen = set()
    unique = []
    for h in sorted(all_hypotheses, key=lambda x: x.get("score", 0), reverse=True):
        key = h.get("drug", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(h)

    # Write
    md = "# Drug Repurposing Hypotheses\n\n"
    md += f"*Auto-compiled on {datetime.now().strftime('%Y-%m-%d')}. None reviewed by domain experts.*\n\n"
    md += "| Drug | Target | Score | Source |\n"
    md += "|------|--------|-------|--------|\n"
    for h in unique[:20]:
        md += f"| {h.get('drug','')} | {h.get('target','')} | {h.get('score',0)}/100 | {h.get('source','')} |\n"

    md += "\n## All Hypotheses Detail\n\n"
    for h in unique[:20]:
        md += f"### {h.get('drug','')} ({h.get('score',0)}/100)\n"
        md += f"- **Target:** {h.get('target','')}\n"
        md += f"- **Source:** {h.get('source','')}\n"
        md += f"- **Rationale:** {h.get('hypothesis','')}\n\n"

    (WIKI_DIR / "hypotheses.md").write_text(md)
    print(f"  hypotheses.md: {len(unique)} unique hypotheses compiled")
    return unique


def compile_methods():
    """Update methods with latest experiment stats."""
    experiments = []
    for f in sorted(DATA_DIR.glob("experiment_*_results.json")):
        exp = load_json(f)
        exp_id = f.stem.replace("_results", "").replace("experiment_", "EXP-").upper()
        model = exp.get("model", "unknown")
        papers = exp.get("papers_analyzed", len(exp.get("analyses", [])))
        chars = exp.get("total_characters_read", 0)
        timestamp = exp.get("timestamp", "")[:10]

        # Count successful analyses
        ok = sum(1 for a in exp.get("analyses", [])
                 if a.get("analysis", {}).get("main_finding")
                 and "failed" not in str(a.get("analysis", {}).get("main_finding", "")).lower())

        experiments.append({
            "id": exp_id, "model": model, "papers": papers,
            "successful": ok, "chars": chars, "date": timestamp,
        })

    md = "# Methods + Experiment Log\n\n"
    md += f"*Auto-compiled on {datetime.now().strftime('%Y-%m-%d')}*\n\n"
    md += "## Experiment History\n\n"
    md += "| ID | Date | Model | Papers | Successful | Characters |\n"
    md += "|----|------|-------|--------|------------|------------|\n"
    for e in experiments:
        md += f"| {e['id']} | {e['date']} | {e['model']} | {e['papers']} | {e['successful']} | {e['chars']:,} |\n"

    md += "\n## Reproducibility\n\n"
    md += "```bash\n"
    md += "git clone https://github.com/jravinder/hd-research-agent\n"
    md += "pip install -r requirements.txt\n"
    md += "python src/run_experiment.py    # EXP-001\n"
    md += "python src/run_experiment_2.py  # EXP-002\n"
    md += "python src/run_experiment_3.py  # EXP-003\n"
    md += "```\n"

    (WIKI_DIR / "methods.md").write_text(md)
    print(f"  methods.md: {len(experiments)} experiments logged")
    return experiments


def run():
    """Compile all wiki pages from data."""
    print(f"\n{'='*50}")
    print(f"  Wiki Compiler")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    WIKI_DIR.mkdir(exist_ok=True)

    targets = compile_targets()
    hypotheses = compile_hypotheses()
    experiments = compile_methods()

    print(f"\n  Wiki compiled: {len(targets)} targets, {len(hypotheses)} hypotheses, {len(experiments)} experiments")
    print(f"  Location: {WIKI_DIR}/")


if __name__ == "__main__":
    run()
