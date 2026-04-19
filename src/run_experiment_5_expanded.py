"""Experiment #5: Expanded Corpus Analysis

The corpus grew from 46 to 65 papers after paper scout ran.
This experiment analyzes the 19 new papers and re-synthesizes
across the full corpus to see what new signals emerge.

Focused questions:
  - Do the new papers confirm or challenge Experiment #4 findings?
  - Any new drug candidates not seen in the somatic expansion screen?
  - New therapeutic approaches (gene therapy, nanoparticles, neuro-
    inflammation, combination therapies)?
  - Updated target rankings with larger evidence base?

Model: Gemma 4 (26B) running locally on Mac M2
"""

import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL = os.environ.get("HD_AGENT_MODEL", "gemma4:latest")

PMC_FETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def ask_llm(prompt, system="", temperature=0.2):
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
    if "```" in text:
        lines = text.split("\n")
        cleaned = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(cleaned)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        text = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', text)
        text = re.sub(r'[\x00-\x1f]', ' ', text)
        return json.loads(text)


def get_pmc_ids(pmids):
    pmc_map = {}
    for i in range(0, len(pmids), 50):
        batch = pmids[i:i+50]
        resp = requests.get(
            "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/",
            params={"ids": ",".join(batch), "format": "json"},
            timeout=15
        )
        if resp.ok:
            for rec in resp.json().get("records", []):
                if rec.get("pmcid"):
                    pmc_map[rec.get("pmid", "")] = rec["pmcid"]
        time.sleep(1)
    return pmc_map


def fetch_full_text(pmcid):
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


def analyze_paper(title, sections, abstract=""):
    full_text = ""
    for sec in sections:
        full_text += f"\n\n## {sec['section']}\n{sec['text']}"

    if len(full_text) > 50000:
        full_text = full_text[:50000] + "\n\n[... truncated at 50K chars ...]"

    prompt = f"""You are analyzing an HD research paper. Extract all therapeutically relevant information.

Title: {title}

FULL PAPER TEXT:
{full_text}

Return JSON:
{{
  "category": "gene_therapy|small_molecule|biomarker|mechanism|clinical_trial|aso|review|neuroprotection|combination_therapy|other",
  "main_finding": "2-3 sentence summary of the primary contribution",
  "therapeutic_approach": "What therapeutic strategy does this paper explore?",
  "targets": ["molecular targets or genes studied"],
  "compounds": ["drugs, compounds, or therapeutic agents mentioned"],
  "novel_insights": ["2-3 things this paper reveals that weren't widely known"],
  "drug_repurposing_signals": ["any existing drugs mentioned as potentially useful for HD"],
  "somatic_expansion_relevance": "direct|indirect|none",
  "clinical_readiness": "concept|preclinical|clinical",
  "relevance_score": 1-10,
  "confidence": "high|medium|low"
}}"""

    try:
        return ask_json(prompt,
            system="You are a senior neuroscience researcher. Be specific about mechanisms, compounds, and evidence levels.")
    except Exception as e:
        return {"error": str(e), "main_finding": f"Analysis failed: {e}"}


def analyze_abstract(title, abstract):
    prompt = f"""Analyze this HD paper abstract for therapeutic relevance.

Title: {title}
Abstract: {abstract}

Return JSON:
{{
  "category": "gene_therapy|small_molecule|biomarker|mechanism|clinical_trial|aso|review|neuroprotection|other",
  "main_finding": "1-2 sentence summary",
  "targets": ["molecular targets mentioned"],
  "compounds": ["drugs or compounds mentioned"],
  "therapeutic_approach": "What approach does this paper explore?",
  "relevance_score": 1-10,
  "confidence": "low"
}}"""

    try:
        return ask_json(prompt, system="You are an HD researcher screening papers.")
    except Exception as e:
        return {"error": str(e), "main_finding": f"Abstract analysis failed: {e}"}


def synthesize(analyses, prev_results=None):
    summaries = []
    all_targets = []
    all_compounds = []
    all_approaches = set()

    for a in analyses:
        an = a.get("analysis", {})
        if an.get("main_finding") and "failed" not in str(an.get("main_finding", "")).lower():
            summaries.append(f"[{a['pmid']}] {a['title'][:60]}: {str(an['main_finding'])[:100]}")
        all_targets.extend(str(t) for t in an.get("targets", []) if t)
        all_compounds.extend(str(c) for c in an.get("compounds", []) if c)
        if an.get("therapeutic_approach"):
            all_approaches.add(str(an["therapeutic_approach"])[:80])

    # Include Experiment #4 context if available
    prev_context = ""
    if prev_results:
        prev_s = prev_results.get("synthesis", {})
        prev_drugs = prev_s.get("drug_candidates_ranked", [])
        if prev_drugs:
            prev_context = "\nPrevious experiment (EXP-004) top drug candidates:\n"
            for d in prev_drugs[:5]:
                if isinstance(d, dict):
                    prev_context += f"  - {d.get('drug','?')} -> {d.get('target','?')} ({d.get('confidence',0)}/100)\n"

    prompt = f"""You have read {len(analyses)} HD research papers. Synthesize findings.

Paper summaries:
{chr(10).join(summaries[:25])}

All targets mentioned: {', '.join(set(t.lower() for t in all_targets if t))[:500]}
All compounds mentioned: {', '.join(set(c.lower() for c in all_compounds if c))[:500]}
Therapeutic approaches seen: {', '.join(all_approaches)[:500]}
{prev_context}

Synthesize. Return JSON:
{{
  "top_findings": ["3 most important findings across all papers"],
  "new_therapeutic_approaches": [{{"approach": "name", "papers": N, "readiness": "concept|preclinical|clinical", "description": "what it is"}}],
  "updated_target_rankings": [{{"target": "name", "mentions": N, "new_evidence": "what's new", "confidence_change": "up|down|stable"}}],
  "new_drug_candidates": [{{"drug": "name", "target": "target", "mechanism": "how", "evidence": "level", "source_papers": N}}],
  "confirms_from_exp4": ["findings that confirm Experiment #4 results"],
  "challenges_from_exp4": ["findings that challenge or nuance Experiment #4 results"],
  "emerging_themes": ["new research themes not seen in previous experiments"],
  "research_gaps": ["what's still missing"],
  "novel_hypotheses": [{{"hypothesis": "description", "score": 0-100, "basis": "what papers support this"}}]
}}"""

    try:
        return ask_json(prompt,
            system="You are a senior HD researcher synthesizing the latest evidence. Compare against previous findings where relevant.")
    except Exception as e:
        return {"error": str(e)}


def run():
    print(f"\n{'='*60}")
    print(f"  Experiment #5: Expanded Corpus Analysis")
    print(f"  Model: {MODEL} (local)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Load corpus
    with open(ROOT / "data" / "corpus.json") as f:
        corpus = json.load(f)

    # Load previous experiment results for comparison
    prev_path = DATA_DIR / "experiment_004_somatic_cag_results.json"
    prev_results = None
    if prev_path.exists():
        with open(prev_path) as f:
            prev_results = json.load(f)
        prev_pmids = set(a["pmid"] for a in prev_results.get("analyses", []))
        print(f"  Previous experiment: {len(prev_pmids)} papers analyzed")
    else:
        prev_pmids = set()

    all_pmids = list(corpus.get("papers", {}).keys())
    new_pmids = [p for p in all_pmids if p not in prev_pmids]
    print(f"  Total corpus: {len(all_pmids)} papers")
    print(f"  New since Experiment #4: {len(new_pmids)} papers")

    # Get PMC IDs for new papers
    print("\nPhase 1: Checking PMC for full text...\n")
    pmc_map = get_pmc_ids(new_pmids)
    abstract_only = [p for p in new_pmids if p not in pmc_map]
    print(f"  Full text available: {len(pmc_map)} papers")
    print(f"  Abstract only: {len(abstract_only)} papers")

    # Analyze new papers
    print(f"\nPhase 2: Analyzing {len(new_pmids)} new papers with {MODEL}...\n")
    analyses = []
    success = 0

    for pmid, pmcid in list(pmc_map.items())[:20]:
        paper = corpus["papers"].get(pmid, {})
        title = paper.get("title", "Unknown")[:80]
        print(f"  [{len(analyses)+1}/{len(new_pmids)}] {title}")
        print(f"    PMCID: {pmcid} (full text)")

        sections = fetch_full_text(pmcid)
        if not sections:
            print("    No text returned, trying abstract")
            abstract = paper.get("abstract", "")
            if abstract:
                analysis = analyze_abstract(title, abstract)
                analyses.append({
                    "pmid": pmid, "title": paper.get("title", ""),
                    "journal": paper.get("journal", ""), "type": "abstract",
                    "sections_count": 0, "total_chars": len(abstract),
                    "analysis": analysis,
                })
                if "error" not in analysis:
                    success += 1
            continue

        total_chars = sum(len(s["text"]) for s in sections)
        print(f"    {len(sections)} sections, {total_chars:,} chars")

        analysis = analyze_paper(title, sections, paper.get("abstract", ""))

        finding = analysis.get("main_finding", "?")
        score = analysis.get("relevance_score", "?")
        print(f"    Finding: {str(finding)[:80]}")
        print(f"    Relevance: {score}/10")

        if "error" not in analysis:
            success += 1

        analyses.append({
            "pmid": pmid, "pmcid": pmcid,
            "title": paper.get("title", ""),
            "journal": paper.get("journal", ""),
            "type": "full_text",
            "sections_count": len(sections),
            "total_chars": total_chars,
            "analysis": analysis,
        })
        print()
        time.sleep(2)

    # Abstract-only papers
    for pmid in abstract_only[:10]:
        paper = corpus["papers"].get(pmid, {})
        abstract = paper.get("abstract", "")
        if not abstract:
            continue

        title = paper.get("title", "Unknown")[:80]
        print(f"  [{len(analyses)+1}/{len(new_pmids)}] {title}")
        print(f"    PMID: {pmid} (abstract only)")

        analysis = analyze_abstract(title, abstract)
        finding = analysis.get("main_finding", "?")
        print(f"    Finding: {str(finding)[:80]}")

        if "error" not in analysis:
            success += 1

        analyses.append({
            "pmid": pmid, "title": paper.get("title", ""),
            "journal": paper.get("journal", ""),
            "type": "abstract",
            "sections_count": 0, "total_chars": len(abstract),
            "analysis": analysis,
        })
        print()
        time.sleep(2)

    print(f"\n  Analyzed: {success} successful out of {len(analyses)} papers")

    # Synthesis
    print(f"\nPhase 3: Synthesizing across {len(analyses)} new papers...\n")
    synthesis = synthesize(analyses, prev_results)

    if "top_findings" in synthesis:
        print("Top findings:")
        for f_item in synthesis.get("top_findings", []):
            print(f"  - {str(f_item)[:100]}")

    if "new_drug_candidates" in synthesis:
        print("\nNew drug candidates:")
        for d in synthesis.get("new_drug_candidates", [])[:5]:
            if isinstance(d, dict):
                print(f"  {d.get('drug','?')} -> {d.get('target','?')} ({d.get('evidence','?')})")

    if "novel_hypotheses" in synthesis:
        print("\nNovel hypotheses:")
        for h in synthesis.get("novel_hypotheses", []):
            if isinstance(h, dict):
                print(f"  [{h.get('score',0)}/100] {str(h.get('hypothesis',''))[:100]}")

    # Save
    results = {
        "experiment_id": "EXP-005-EXPANDED",
        "timestamp": datetime.now().isoformat(),
        "model": MODEL,
        "type": "expanded_corpus_analysis",
        "corpus_size": len(all_pmids),
        "new_papers_analyzed": len(analyses),
        "full_text_analyzed": sum(1 for a in analyses if a.get("type") == "full_text"),
        "abstract_only_analyzed": sum(1 for a in analyses if a.get("type") == "abstract"),
        "total_sections_read": sum(a.get("sections_count", 0) for a in analyses),
        "total_characters_read": sum(a.get("total_chars", 0) for a in analyses),
        "analyses": analyses,
        "synthesis": synthesis,
    }

    results_path = DATA_DIR / "experiment_005_expanded_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n{'='*60}")
    print(f"  Experiment #5 complete!")
    print(f"  New papers analyzed: {len(analyses)}")
    print(f"  Characters read: {results['total_characters_read']:,}")
    print(f"  Results: {results_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run()
