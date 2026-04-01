"""Experiment #3: Deep Full-Text Analysis of HD Research Papers

Unlike Experiment #1 (abstracts only), this reads entire papers end-to-end.
Methods, Results, Discussion, Conclusions. Every section, every finding.

The LLM reads each full paper like a researcher would, then synthesizes
across all papers to find patterns, contradictions, and novel connections.
"""

import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
KB_FILE = DATA_DIR / "knowledge_base.json"

OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://192.168.4.124:11434")
MODEL = os.environ.get("HD_AGENT_MODEL", "llama3.1:8b")

PMC_FETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def ask_llm(prompt, system="", temperature=0.2):
    """Call Ollama."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = requests.post(
        f"{OLLAMA_BASE}/api/chat",
        json={"model": MODEL, "messages": messages, "stream": False,
              "options": {"temperature": temperature, "num_ctx": 65536}},
        timeout=1800,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def ask_json(prompt, system=""):
    full_system = system + "\nRespond with valid JSON only. No markdown fences."
    text = ask_llm(prompt, system=full_system, temperature=0.1)
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return json.loads(text.strip())


def fetch_full_text(pmcid):
    """Fetch full paper text from PMC."""
    resp = requests.get(PMC_FETCH, params={
        "db": "pmc", "id": pmcid, "retmode": "xml"
    }, timeout=30)
    if not resp.ok:
        return None

    root = ET.fromstring(resp.text)
    body = root.find(".//body")
    if body is None:
        return None

    sections = []
    for sec in body.findall(".//sec"):
        title_el = sec.find("title")
        title = title_el.text if title_el is not None and title_el.text else "Untitled"
        paragraphs = []
        for p in sec.findall(".//p"):
            text = ET.tostring(p, encoding="unicode", method="text").strip()
            if text:
                paragraphs.append(text)
        if paragraphs:
            sections.append({"section": title, "text": "\n\n".join(paragraphs)})

    return sections


def get_pmc_ids(pmids):
    """Convert PMIDs to PMCIDs."""
    pmc_map = {}
    resp = requests.get(
        "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/",
        params={"ids": ",".join(pmids), "format": "json"},
        timeout=15
    )
    if resp.ok:
        for rec in resp.json().get("records", []):
            if rec.get("pmcid"):
                pmc_map[rec.get("pmid", "")] = rec["pmcid"]
    return pmc_map


def analyze_full_paper(title, sections):
    """Send entire paper to LLM for deep analysis."""
    # Build full text from all sections
    full_text = ""
    for sec in sections:
        full_text += f"\n\n## {sec['section']}\n{sec['text']}"

    # Full paper goes in. No truncation. Llama 3.1 has 128K context.

    prompt = f"""You are reading a complete Huntington's Disease research paper. Analyze it deeply.

Title: {title}

FULL PAPER TEXT:
{full_text}

Analyze this paper thoroughly. Return JSON:
{{
  "category": "gene_therapy|small_molecule|biomarker|mechanism|ai_ml|clinical_trial|crispr|aso|review|other",
  "main_finding": "2-3 sentence summary of the paper's primary contribution",
  "methodology": "What methods did they use? (1-2 sentences)",
  "key_data": "What specific numbers, measurements, or quantitative results did they report?",
  "targets": ["molecular targets or genes studied"],
  "compounds": ["drugs, compounds, or therapeutic agents mentioned"],
  "novel_insights": ["list 2-3 things this paper reveals that weren't known before"],
  "limitations_stated": "What limitations did the authors themselves acknowledge?",
  "implications_for_treatment": "What does this mean for HD treatment development? (1-2 sentences)",
  "connections_to_other_work": ["What other research areas or diseases does this connect to?"],
  "drug_repurposing_signals": ["Any existing drugs mentioned as potentially useful for HD"],
  "relevance_score": 1-10,
  "confidence_in_analysis": "high|medium|low"
}}"""

    try:
        return ask_json(prompt, system="You are a senior HD researcher reading papers in depth. Be thorough and specific.")
    except Exception as e:
        return {"error": str(e), "main_finding": "Analysis failed"}


def synthesize_across_papers(analyses):
    """Read all paper analyses and find cross-paper patterns."""
    summaries = []
    for a in analyses:
        if a.get("analysis", {}).get("main_finding"):
            summaries.append(
                f"[{a['pmid']}] {a['title'][:60]}: {a['analysis']['main_finding']}"
            )

    all_targets = []
    all_compounds = []
    all_insights = []
    for a in analyses:
        an = a.get("analysis", {})
        all_targets.extend(an.get("targets", []))
        all_compounds.extend(an.get("compounds", []))
        all_insights.extend(an.get("novel_insights", []))

    prompt = f"""You have deeply read {len(analyses)} complete HD research papers. Now synthesize.

Paper summaries:
{chr(10).join(summaries[:15])}

All targets mentioned: {', '.join(set(t.lower() for t in all_targets if t))[:500]}
All compounds mentioned: {', '.join(set(c.lower() for c in all_compounds if c))[:500]}

Based on reading these FULL papers (not just abstracts), answer:

1. What are the 3 most important findings across all papers?
2. What contradictions or debates exist between papers?
3. What targets appear in multiple papers and seem most promising?
4. What drug repurposing opportunities emerge from the full-text data?
5. What gaps in the research do you see (things no paper addressed)?
6. Generate 3 new hypotheses that combine insights from multiple papers.

Return JSON:
{{
  "top_findings": ["finding 1", "finding 2", "finding 3"],
  "contradictions": ["contradiction or debate 1"],
  "promising_targets": [{{"target": "name", "papers_mentioning": N, "why_promising": "reason"}}],
  "repurposing_opportunities": [{{"drug": "name", "rationale": "why", "confidence": "high|medium|low"}}],
  "research_gaps": ["gap 1", "gap 2"],
  "new_hypotheses": [{{"hypothesis": "description", "based_on_papers": ["pmid1"], "score": 0-100}}]
}}"""

    try:
        return ask_json(prompt, system="You are a senior HD researcher synthesizing findings from deep paper reads.")
    except Exception as e:
        return {"error": str(e)}


def run():
    print(f"\n{'='*60}")
    print(f"  Experiment #3: Deep Full-Text Paper Analysis")
    print(f"  Model: {MODEL} on Jetson")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Load corpus to get PMIDs
    with open(ROOT / "data" / "corpus.json") as f:
        corpus = json.load(f)

    pmids = list(corpus.get("papers", {}).keys())
    print(f"Corpus: {len(pmids)} papers")

    # Find which have full text on PMC
    print("Checking PMC for full text...")
    pmc_map = get_pmc_ids(pmids)
    print(f"Full text available: {len(pmc_map)} papers\n")

    # Phase 1: Read and analyze each full paper
    print("Phase 1: Reading full papers...\n")
    analyses = []
    for pmid, pmcid in pmc_map.items():
        paper_info = corpus["papers"].get(pmid, {})
        title = paper_info.get("title", "")[:80]
        print(f"  [{pmcid}] {title}")

        # Fetch full text
        sections = fetch_full_text(pmcid)
        if not sections:
            print("    No text returned, skipping")
            continue

        total_chars = sum(len(s["text"]) for s in sections)
        print(f"    {len(sections)} sections, {total_chars:,} characters")

        # Deep analysis
        print(f"    Analyzing with {MODEL}...")
        analysis = analyze_full_paper(title, sections)

        finding = analysis.get("main_finding", "?")
        score = analysis.get("relevance_score", "?")
        print(f"    Finding: {finding[:80]}")
        print(f"    Relevance: {score}/10")

        analyses.append({
            "pmid": pmid,
            "pmcid": pmcid,
            "title": paper_info.get("title", ""),
            "journal": paper_info.get("journal", ""),
            "sections_count": len(sections),
            "total_chars": total_chars,
            "analysis": analysis,
        })
        print()
        time.sleep(2)

    # Phase 2: Cross-paper synthesis
    print(f"\nPhase 2: Synthesizing across {len(analyses)} papers...\n")
    synthesis = synthesize_across_papers(analyses)

    if "top_findings" in synthesis:
        print("Top findings:")
        for f in synthesis.get("top_findings", []):
            print(f"  - {f[:100]}")

    if "new_hypotheses" in synthesis:
        print("\nNew hypotheses:")
        for h in synthesis.get("new_hypotheses", []):
            print(f"  [{h.get('score',0)}/100] {h.get('hypothesis','')[:100]}")

    # Save results
    results = {
        "experiment_id": "EXP-003",
        "timestamp": datetime.now().isoformat(),
        "model": MODEL,
        "type": "multi_model_comparison_qwen35",
        "papers_analyzed": len(analyses),
        "total_sections_read": sum(a["sections_count"] for a in analyses),
        "total_characters_read": sum(a["total_chars"] for a in analyses),
        "analyses": analyses,
        "synthesis": synthesis,
    }

    with open(DATA_DIR / "experiment_003_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Write report
    report = f"""# Experiment #3: Deep Full-Text Analysis of HD Research Papers

**Date:** {datetime.now().strftime('%B %d, %Y')}
**Model:** {MODEL} on NVIDIA Jetson AGX Orin
**Papers read (full text):** {len(analyses)}
**Total sections analyzed:** {results['total_sections_read']}
**Total characters read:** {results['total_characters_read']:,}

## Difference from Experiment #1

Experiment #1 read **abstracts only** (200 words each). This experiment reads **entire papers** end-to-end: Introduction, Methods, Results, Discussion, Conclusions. Every section, every finding, every data point the authors reported.

## Top Findings

"""
    for i, f in enumerate(synthesis.get("top_findings", []), 1):
        report += f"{i}. {f}\n"

    report += "\n## Cross-Paper Contradictions\n\n"
    for c in synthesis.get("contradictions", []):
        report += f"- {c}\n"

    report += "\n## Promising Targets\n\n"
    for t in synthesis.get("promising_targets", []):
        if isinstance(t, dict):
            report += f"- **{t.get('target','')}** ({t.get('papers_mentioning',0)} papers): {t.get('why_promising','')}\n"

    report += "\n## New Hypotheses (from full-text analysis)\n\n"
    for h in synthesis.get("new_hypotheses", []):
        if isinstance(h, dict):
            report += f"- [{h.get('score',0)}/100] {h.get('hypothesis','')}\n"

    report += "\n## Research Gaps Identified\n\n"
    for g in synthesis.get("research_gaps", []):
        report += f"- {g}\n"

    report += f"""
## Methodology

- Full text retrieved from PubMed Central (open access papers only)
- Each paper analyzed by {MODEL} with 8K context window
- Cross-paper synthesis generated from all individual analyses
- All code: [github.com/jravinder/hd-research-agent](https://github.com/jravinder/hd-research-agent)

## Limitations

- Only open-access papers analyzed (papers behind paywalls are excluded)
- 8K context window means very long papers are truncated (first ~6000 chars per paper)
- Single model, single run
- Not reviewed by HD domain experts

This is AI-generated research analysis, not medical advice.
"""

    with open(DATA_DIR / "experiment_003_report.md", "w") as f:
        f.write(report)

    print(f"\n{'='*60}")
    print(f"  Experiment #3 complete!")
    print(f"  Papers read: {len(analyses)}")
    print(f"  Sections analyzed: {results['total_sections_read']}")
    print(f"  Characters read: {results['total_characters_read']:,}")
    print(f"  Report: data/experiment_003_report.md")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run()
