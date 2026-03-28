"""Hypothesis Refiner Agent — takes existing hypotheses, finds evidence, re-scores.

Runs daily. For each hypothesis in the corpus:
1. Searches PubMed for supporting/contradicting evidence
2. Re-scores based on new evidence
3. Tracks score trajectory over time (is confidence growing or shrinking?)
4. Flags hypotheses that consistently score high across multiple runs
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from literature_agent import search_pubmed, fetch_papers
from llm import ask_json

ROOT = Path(__file__).parent.parent.parent
HYPOTHESES_FILE = ROOT / "data" / "hypotheses_tracker.json"
CORPUS_FILE = ROOT / "data" / "corpus.json"


def load_hypotheses():
    if HYPOTHESES_FILE.exists():
        with open(HYPOTHESES_FILE) as f:
            return json.load(f)
    # Seed with our initial hypotheses from experiment 1
    return {
        "hypotheses": [
            {
                "id": "h001",
                "drug": "Tocilizumab",
                "target": "IL-6 / neuroinflammation",
                "rationale": "IL-6 receptor blockade may reduce inflammation from mutant huntingtin aggregation",
                "scores": [80],
                "dates": [datetime.now().isoformat()],
                "status": "exploring",
                "evidence_for": [],
                "evidence_against": [],
            },
            {
                "id": "h002",
                "drug": "Lithium",
                "target": "TDP-43 / GSK-3β",
                "rationale": "May reduce TDP-43 phosphorylation and aggregation via GSK-3β inhibition, relevant to newly discovered HD-TDP-43 connection",
                "scores": [55],
                "dates": [datetime.now().isoformat()],
                "status": "exploring",
                "evidence_for": [],
                "evidence_against": [],
            },
            {
                "id": "h003",
                "drug": "Metformin",
                "target": "mTOR / AMPK / autophagy",
                "rationale": "Promotes autophagy which may help clear mutant HTT aggregates",
                "scores": [72],
                "dates": [datetime.now().isoformat()],
                "status": "exploring",
                "evidence_for": [],
                "evidence_against": [],
            },
            {
                "id": "h004",
                "drug": "Rapamycin",
                "target": "mTOR",
                "rationale": "mTOR inhibitor demonstrated clearance of mutant HTT in preclinical models",
                "scores": [68],
                "dates": [datetime.now().isoformat()],
                "status": "exploring",
                "evidence_for": [],
                "evidence_against": [],
            },
            {
                "id": "h005",
                "drug": "Riluzole",
                "target": "Glutamate excitotoxicity",
                "rationale": "Glutamate release inhibitor, may reduce excitotoxicity in HD",
                "scores": [60],
                "dates": [datetime.now().isoformat()],
                "status": "known_tested",
                "evidence_for": [],
                "evidence_against": ["Already tested in HD clinical trials with modest results"],
            },
        ],
        "last_run": None,
        "total_refinements": 0,
    }


def refine_hypothesis(hypothesis):
    """Search for new evidence and re-score a hypothesis."""
    drug = hypothesis["drug"]
    target = hypothesis["target"]

    # Search for evidence
    query = f"{drug} huntington disease {target}"
    print(f"    Searching PubMed: {query}")

    pmids = search_pubmed(query, days=90, max_results=5)
    if not pmids:
        print(f"    No new papers found")
        return hypothesis

    papers = fetch_papers(pmids[:3])
    time.sleep(1)

    evidence_texts = []
    for p in papers:
        evidence_texts.append(f"[{p.pmid}] {p.title}: {p.abstract[:200]}")

    # Ask LLM to re-evaluate
    prompt = f"""Re-evaluate this drug repurposing hypothesis for Huntington's disease based on new evidence.

Hypothesis: {drug} targeting {target}
Original rationale: {hypothesis['rationale']}
Previous score: {hypothesis['scores'][-1]}/100

New evidence from PubMed:
{chr(10).join(evidence_texts)}

Return JSON:
{{
  "new_score": 0-100,
  "evidence_for": ["supporting findings"],
  "evidence_against": ["contradicting findings or concerns"],
  "assessment": "one paragraph: is this hypothesis getting stronger or weaker?",
  "still_novel": true/false
}}"""

    try:
        result = ask_json(prompt, system="You are a pharmacology expert evaluating drug repurposing hypotheses for HD.")

        hypothesis["scores"].append(result.get("new_score", hypothesis["scores"][-1]))
        hypothesis["dates"].append(datetime.now().isoformat())

        for e in result.get("evidence_for", []):
            if e not in hypothesis["evidence_for"]:
                hypothesis["evidence_for"].append(e)
        for e in result.get("evidence_against", []):
            if e not in hypothesis["evidence_against"]:
                hypothesis["evidence_against"].append(e)

        # Update status based on trajectory
        scores = hypothesis["scores"]
        if len(scores) >= 3 and all(s >= 70 for s in scores[-3:]):
            hypothesis["status"] = "promising"
        elif len(scores) >= 3 and all(s < 40 for s in scores[-3:]):
            hypothesis["status"] = "unlikely"

        assessment = result.get("assessment", "")
        print(f"    Score: {scores[-2]} -> {scores[-1]}")
        print(f"    {assessment[:100]}")

    except Exception as e:
        print(f"    LLM evaluation failed: {e}")

    return hypothesis


def run():
    data = load_hypotheses()

    print(f"\n{'='*50}")
    print(f"Hypothesis Refiner — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Hypotheses to refine: {len(data['hypotheses'])}")
    print(f"{'='*50}\n")

    for h in data["hypotheses"]:
        print(f"  [{h['id']}] {h['drug']} -> {h['target']} (current: {h['scores'][-1]})")
        refine_hypothesis(h)
        time.sleep(2)
        print()

    data["last_run"] = datetime.now().isoformat()
    data["total_refinements"] = data.get("total_refinements", 0) + 1

    with open(HYPOTHESES_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

    # Summary
    promising = [h for h in data["hypotheses"] if h["status"] == "promising"]
    print(f"\n{'='*50}")
    print(f"  Refinement #{data['total_refinements']} complete")
    print(f"  Promising hypotheses: {len(promising)}")
    for h in data["hypotheses"]:
        trend = "↑" if len(h["scores"]) > 1 and h["scores"][-1] > h["scores"][-2] else "↓" if len(h["scores"]) > 1 and h["scores"][-1] < h["scores"][-2] else "→"
        print(f"    {trend} {h['drug']}: {' → '.join(str(s) for s in h['scores'])}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    run()
