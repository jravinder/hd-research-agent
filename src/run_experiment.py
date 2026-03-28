"""Run Experiment #1: AI-Powered HD Literature Analysis + Hypothesis Generation

Reads papers_full.json, sends each to LLM for structured analysis,
generates drug repurposing hypotheses from findings, scores them,
and publishes results as a markdown report.

No medical expertise needed — this is a data science experiment.
We're asking: what patterns can an LLM find in HD research that
a human skimming abstracts might miss?
"""

import json
import time
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
OLLAMA_BASE = "http://192.168.4.124:11434"  # Jetson
MODEL = "llama3.1:8b"


def ask_llm(prompt, system="", temperature=0.2):
    """Call Ollama on Jetson."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = requests.post(
        f"{OLLAMA_BASE}/api/chat",
        json={"model": MODEL, "messages": messages, "stream": False, "options": {"temperature": temperature}},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def ask_json(prompt, system=""):
    """Call LLM and parse JSON response."""
    full_system = system + "\nRespond with valid JSON only. No markdown fences, no explanation."
    text = ask_llm(prompt, system=full_system, temperature=0.1)
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


def analyze_paper(paper):
    """Extract structured insights from a paper abstract."""
    prompt = f"""Analyze this Huntington's disease research paper:

Title: {paper['title']}
Abstract: {paper['abstract'][:800]}

Return JSON:
{{
  "category": "gene_therapy|small_molecule|biomarker|mechanism|ai_ml|clinical_trial|review|other",
  "targets": ["molecular targets or genes mentioned"],
  "compounds": ["drugs or compounds mentioned"],
  "finding": "one sentence — the key discovery or result",
  "relevance": "high|medium|low",
  "repurposing_signal": true/false,
  "novel_target": true/false
}}"""
    try:
        return ask_json(prompt, system="You are a biomedical research analyst.")
    except Exception as e:
        return {"error": str(e), "finding": "Analysis failed"}


def generate_hypotheses(findings_summary):
    """Generate drug repurposing hypotheses from paper findings."""
    prompt = f"""Based on these recent Huntington's disease research findings, generate 5 novel drug repurposing hypotheses.

Recent findings:
{findings_summary}

For each hypothesis, pick an FDA-approved drug and explain why it might work for HD.

Return JSON array:
[{{
  "drug": "name",
  "original_use": "what it's approved for",
  "hd_target": "which HD mechanism",
  "rationale": "2 sentences on why this could work",
  "confidence": "high|medium|low",
  "score": 0-100,
  "next_experiment": "what would you test first"
}}]"""
    try:
        return ask_json(prompt, system="You are a computational pharmacology expert. Be scientifically rigorous but creative.")
    except Exception as e:
        return [{"error": str(e)}]


def run():
    papers_file = DATA_DIR / "papers_full.json"
    if not papers_file.exists():
        print("No papers_full.json — run data fetcher first")
        return

    with open(papers_file) as f:
        papers = json.load(f)

    print(f"\n{'='*60}")
    print(f"  HD Research Experiment #1")
    print(f"  {len(papers)} papers | Model: {MODEL} on Jetson")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Phase 1: Analyze each paper
    print("Phase 1: Analyzing papers with LLM...\n")
    analyses = []
    for i, paper in enumerate(papers):
        print(f"  [{i+1}/{len(papers)}] {paper['title'][:60]}...")
        analysis = analyze_paper(paper)
        analyses.append({"paper": paper, "analysis": analysis})

        finding = analysis.get("finding", "?")
        targets = analysis.get("targets", [])
        print(f"    -> {finding[:80]}")
        if targets:
            print(f"    -> Targets: {', '.join(targets[:4])}")
        print()
        time.sleep(1)

    # Phase 2: Summarize findings
    print("\nPhase 2: Synthesizing findings...\n")
    findings = [a["analysis"].get("finding", "") for a in analyses if a["analysis"].get("finding")]
    high_relevance = [a for a in analyses if a["analysis"].get("relevance") == "high"]
    repurposing = [a for a in analyses if a["analysis"].get("repurposing_signal")]
    novel = [a for a in analyses if a["analysis"].get("novel_target")]

    all_targets = []
    for a in analyses:
        all_targets.extend(a["analysis"].get("targets", []))
    target_counts = {}
    for t in all_targets:
        t_lower = t.lower().strip()
        if t_lower:
            target_counts[t_lower] = target_counts.get(t_lower, 0) + 1
    top_targets = sorted(target_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    all_compounds = []
    for a in analyses:
        all_compounds.extend(a["analysis"].get("compounds", []))
    compound_counts = {}
    for c in all_compounds:
        c_lower = c.lower().strip()
        if c_lower:
            compound_counts[c_lower] = compound_counts.get(c_lower, 0) + 1
    top_compounds = sorted(compound_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    print(f"  Papers analyzed: {len(analyses)}")
    print(f"  High relevance: {len(high_relevance)}")
    print(f"  Repurposing signals: {len(repurposing)}")
    print(f"  Novel targets: {len(novel)}")
    print(f"  Top targets: {', '.join(t[0] for t in top_targets[:5])}")
    print(f"  Top compounds: {', '.join(c[0] for c in top_compounds[:5])}")

    # Phase 3: Generate hypotheses
    print("\nPhase 3: Generating drug repurposing hypotheses...\n")
    findings_text = "; ".join(findings[:15])
    hypotheses = generate_hypotheses(findings_text)

    if isinstance(hypotheses, list):
        for h in hypotheses:
            if "error" not in h:
                print(f"  [{h.get('score',0)}/100] {h.get('drug','?')} -> {h.get('hd_target','?')}")
                print(f"    {h.get('rationale','')[:100]}")
                print()

    # Phase 4: Write report
    print("\nPhase 4: Writing report...\n")
    report_file = ROOT / "data" / "experiment_001_report.md"

    report = f"""# Experiment #1: AI-Powered HD Literature Analysis

**Date:** {datetime.now().strftime('%B %d, %Y')}
**Model:** {MODEL} (Llama 3.1 8B on NVIDIA Jetson AGX Orin)
**Papers analyzed:** {len(analyses)}
**Method:** Autonomous LLM analysis of recent PubMed abstracts + hypothesis generation

## Summary

We fed {len(papers)} recent Huntington's disease research papers to Llama 3.1 8B running on an NVIDIA Jetson AGX Orin and asked it to extract structured insights: molecular targets, compounds, key findings, and drug repurposing signals.

This is not a clinical study. It's a data science experiment asking: **what patterns can an LLM surface from HD research that might help prioritize investigation?**

## Key Numbers

| Metric | Count |
|--------|-------|
| Papers analyzed | {len(analyses)} |
| High relevance | {len(high_relevance)} |
| Repurposing signals found | {len(repurposing)} |
| Novel targets identified | {len(novel)} |

## Most Mentioned Targets

| Target | Mentions |
|--------|----------|
"""
    for target, count in top_targets:
        report += f"| {target} | {count} |\n"

    report += f"""
## Most Mentioned Compounds

| Compound | Mentions |
|----------|----------|
"""
    for compound, count in top_compounds:
        report += f"| {compound} | {count} |\n"

    report += """
## Paper-by-Paper Analysis

"""
    for a in analyses:
        p = a["paper"]
        an = a["analysis"]
        report += f"### [{p['pmid']}] {p['title']}\n"
        report += f"- **Journal:** {p['journal']} ({p['date']})\n"
        report += f"- **Category:** {an.get('category', '?')}\n"
        report += f"- **Finding:** {an.get('finding', '?')}\n"
        report += f"- **Targets:** {', '.join(an.get('targets', []))}\n"
        report += f"- **Compounds:** {', '.join(an.get('compounds', []))}\n"
        report += f"- **Relevance:** {an.get('relevance', '?')}\n"
        report += f"- **Repurposing signal:** {'Yes' if an.get('repurposing_signal') else 'No'}\n"
        report += f"- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/)\n\n"

    report += "## AI-Generated Drug Repurposing Hypotheses\n\n"
    report += "*These are exploratory ideas generated by an AI model, not clinical recommendations.*\n\n"

    if isinstance(hypotheses, list):
        for h in hypotheses:
            if "error" not in h:
                report += f"### {h.get('drug', '?')} -> {h.get('hd_target', '?')}\n"
                report += f"- **Original use:** {h.get('original_use', '?')}\n"
                report += f"- **Rationale:** {h.get('rationale', '?')}\n"
                report += f"- **Confidence:** {h.get('confidence', '?')}\n"
                report += f"- **Score:** {h.get('score', 0)}/100\n"
                report += f"- **Suggested next experiment:** {h.get('next_experiment', '?')}\n\n"

    report += f"""---

## Methodology

1. **Data collection:** PubMed E-utilities API, 5 search queries covering HD treatment, AI/ML, somatic expansion, drug repurposing, and biomarkers (last 90 days)
2. **Analysis:** Each paper abstract sent to Llama 3.1 8B with structured extraction prompt
3. **Hypothesis generation:** Findings summarized and fed to LLM for drug repurposing ideation
4. **Infrastructure:** NVIDIA Jetson AGX Orin 64GB, Ollama {MODEL}
5. **Code:** [github.com/jravinder/hd-research-agent](https://github.com/jravinder/hd-research-agent)

## Disclaimer

This is an open-source research experiment by a curious data scientist, not a medical study. AI-generated hypotheses have not been clinically validated. Always consult qualified healthcare professionals. Published to contribute ideas to the HD research community.

## License

MIT — use freely, build on it, improve it.
"""

    with open(report_file, "w") as f:
        f.write(report)
    print(f"Report saved to {report_file}")

    # Save raw results
    results_file = DATA_DIR / "experiment_001_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "model": MODEL,
            "papers_count": len(papers),
            "analyses": analyses,
            "hypotheses": hypotheses,
            "top_targets": top_targets,
            "top_compounds": top_compounds,
            "stats": {
                "high_relevance": len(high_relevance),
                "repurposing_signals": len(repurposing),
                "novel_targets": len(novel),
            }
        }, f, indent=2, default=str)
    print(f"Raw results saved to {results_file}")

    print(f"\n{'='*60}")
    print(f"  Experiment #1 complete!")
    print(f"  Report: data/experiment_001_report.md")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run()
