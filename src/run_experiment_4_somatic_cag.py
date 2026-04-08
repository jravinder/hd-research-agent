"""Experiment #4: Somatic CAG Expansion Drug Screen

The hottest frontier in HD therapeutics. GWAS identified DNA repair genes
(MSH3, FAN1, PMS1, MLH1, LIG1) as the strongest modifiers of disease onset.
Multiple companies now have drugs in development against these targets.

This experiment:
  1. Discovers somatic expansion papers from PubMed (2024-2026)
  2. Pulls full text from PMC
  3. Screens each paper for drug candidates against 5 validated targets
  4. Synthesizes a ranked drug candidate list across all papers
  5. Generates novel combination hypotheses

Model: Gemma 4 (26B) running locally on Mac M2
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

OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL = os.environ.get("HD_AGENT_MODEL", "gemma4:latest")

PMC_FETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PUBMED_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# The 5 validated somatic expansion targets
SOMATIC_TARGETS = ["MSH3", "FAN1", "PMS1", "MLH1", "LIG1"]

# PubMed search queries to find somatic expansion papers
SEARCH_QUERIES = [
    "huntington disease somatic CAG expansion",
    "huntington disease MSH3 mismatch repair",
    "huntington disease FAN1 DNA repair",
    "huntington disease PMS1 splice modifier",
    "huntington disease DNA repair genetic modifier",
    "huntington disease repeat expansion therapeutics",
    "CAG repeat instability drug treatment",
    "huntington disease LIG1 ligase",
]


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
    full_system = system + "\nRespond with valid JSON only. No markdown fences, no explanation outside the JSON. Escape all special characters in strings properly."
    text = ask_llm(prompt, system=full_system, temperature=0.1)
    # Strip markdown code fences
    if "```" in text:
        lines = text.split("\n")
        cleaned = []
        in_fence = False
        for line in lines:
            if line.strip().startswith("```"):
                in_fence = not in_fence
                continue
            cleaned.append(line)
        text = "\n".join(cleaned)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fix common LLM JSON errors: unescaped backslashes, control chars
        import re
        text = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', text)
        text = re.sub(r'[\x00-\x1f]', ' ', text)
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise e


def search_pubmed(query, max_results=30):
    """Search PubMed for papers matching query."""
    resp = requests.get(PUBMED_SEARCH, params={
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json",
        "sort": "date",
        "mindate": "2024/01/01",
        "maxdate": "2026/12/31",
        "datetype": "pdat",
    }, timeout=15)
    if not resp.ok:
        return []
    data = resp.json()
    return data.get("esearchresult", {}).get("idlist", [])


def fetch_paper_metadata(pmids):
    """Fetch title/abstract/journal for a list of PMIDs."""
    if not pmids:
        return {}
    resp = requests.get(PUBMED_FETCH, params={
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }, timeout=30)
    if not resp.ok:
        return {}

    papers = {}
    root = ET.fromstring(resp.text)
    for article in root.findall(".//PubmedArticle"):
        pmid_el = article.find(".//PMID")
        if pmid_el is None:
            continue
        pmid = pmid_el.text

        title_el = article.find(".//ArticleTitle")
        title = ET.tostring(title_el, encoding="unicode", method="text").strip() if title_el is not None else ""

        abstract_parts = []
        for ab in article.findall(".//AbstractText"):
            text = ET.tostring(ab, encoding="unicode", method="text").strip()
            label = ab.get("Label", "")
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        abstract = " ".join(abstract_parts)

        journal_el = article.find(".//Journal/Title")
        journal = journal_el.text if journal_el is not None else ""

        date_el = article.find(".//PubDate")
        pub_date = ""
        if date_el is not None:
            y = date_el.findtext("Year", "")
            m = date_el.findtext("Month", "")
            pub_date = f"{y} {m}".strip()

        papers[pmid] = {
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "journal": journal,
            "date": pub_date,
        }
    return papers


def get_pmc_ids(pmids):
    """Convert PMIDs to PMCIDs."""
    pmc_map = {}
    # Process in batches of 50
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


def analyze_paper_somatic(title, sections, abstract=""):
    """Analyze a paper specifically for somatic CAG expansion drug candidates."""
    full_text = ""
    for sec in sections:
        full_text += f"\n\n## {sec['section']}\n{sec['text']}"

    # If paper is very long, include first 50K chars
    if len(full_text) > 50000:
        full_text = full_text[:50000] + "\n\n[... truncated at 50K chars ...]"

    prompt = f"""You are screening this HD research paper for drug candidates that target somatic CAG repeat expansion.

Title: {title}

FULL PAPER TEXT:
{full_text}

CONTEXT: Somatic CAG expansion is the most promising therapeutic frontier in HD. The key pathway:
- MutSbeta (MSH2-MSH3) recognizes CAG repeat loops
- MutLgamma (MLH1-MLH3) nicks DNA, enabling expansion
- Pol-delta synthesizes using the loop as template, adding CAG repeats
- LIG1 seals the nick, locking in expansion
- FAN1 opposes expansion by removing loops (contraction)

The 5 validated targets: MSH3, FAN1, PMS1, MLH1, LIG1

Analyze this paper. Return JSON:
{{
  "category": "mechanism|drug_candidate|biomarker|clinical_trial|genetic_modifier|review|other",
  "main_finding": "2-3 sentence summary focused on somatic expansion relevance",
  "methodology": "Methods used (1-2 sentences)",
  "key_data": "Specific quantitative results (CAG length changes, expansion rates, IC50s, etc.)",
  "somatic_expansion_relevance": "direct|indirect|background",
  "targets_discussed": ["list all molecular targets mentioned, especially MSH3/FAN1/PMS1/MLH1/LIG1"],
  "drug_candidates": [
    {{
      "name": "compound/drug name",
      "target": "which of the 5 targets it hits",
      "mechanism": "how it reduces somatic expansion",
      "evidence_level": "in_vitro|cell_model|animal_model|clinical",
      "key_result": "specific result (e.g. 50% expansion reduction at 10uM)",
      "developer": "company or lab if mentioned"
    }}
  ],
  "expansion_measurements": {{
    "method": "how expansion was measured (if applicable)",
    "tissue": "which tissue/cell type",
    "magnitude": "expansion rate or change observed"
  }},
  "novel_insights": ["2-3 things this paper reveals about somatic expansion"],
  "combination_opportunities": ["potential drug combinations suggested by the data"],
  "limitations": "key limitations acknowledged",
  "relevance_score": 1-10,
  "confidence": "high|medium|low"
}}"""

    try:
        return ask_json(prompt,
            system="You are a senior HD researcher and medicinal chemist. "
                   "Focus on actionable drug repurposing and combination therapy opportunities. "
                   "Be specific about targets, mechanisms, and evidence levels.")
    except Exception as e:
        return {"error": str(e), "main_finding": f"Analysis failed: {e}"}


def analyze_abstract_somatic(title, abstract):
    """Fallback: analyze abstract when full text is not available."""
    prompt = f"""Screen this HD paper abstract for somatic CAG expansion drug candidates.

Title: {title}
Abstract: {abstract}

The 5 validated somatic expansion targets: MSH3, FAN1, PMS1, MLH1, LIG1

Return JSON:
{{
  "category": "mechanism|drug_candidate|biomarker|clinical_trial|genetic_modifier|review|other",
  "main_finding": "1-2 sentence summary focused on somatic expansion relevance",
  "somatic_expansion_relevance": "direct|indirect|background",
  "targets_discussed": ["molecular targets mentioned"],
  "drug_candidates": [
    {{
      "name": "compound name",
      "target": "target",
      "mechanism": "mechanism",
      "evidence_level": "in_vitro|cell_model|animal_model|clinical",
      "key_result": "result if stated"
    }}
  ],
  "relevance_score": 1-10,
  "confidence": "low"
}}"""

    try:
        return ask_json(prompt,
            system="You are an HD researcher screening papers for somatic expansion drug candidates.")
    except Exception as e:
        return {"error": str(e), "main_finding": f"Abstract analysis failed: {e}"}


def synthesize_drug_screen(analyses):
    """Cross-paper synthesis focused on drug candidates."""
    summaries = []
    all_drugs = []
    all_targets = []

    for a in analyses:
        an = a.get("analysis", {})
        if an.get("main_finding"):
            summaries.append(
                f"[{a['pmid']}] {a['title'][:60]}: {an['main_finding']}"
            )
        for d in an.get("drug_candidates", []):
            if isinstance(d, dict) and d.get("name"):
                d["source_pmid"] = a["pmid"]
                all_drugs.append(d)
        all_targets.extend(an.get("targets_discussed", []))

    # Aggregate drug mentions
    drug_summary = ""
    drug_names = {}
    for d in all_drugs:
        name = d.get("name", "").lower()
        if name not in drug_names:
            drug_names[name] = {"count": 0, "details": []}
        drug_names[name]["count"] += 1
        drug_names[name]["details"].append(d)

    for name, info in sorted(drug_names.items(), key=lambda x: x[1]["count"], reverse=True)[:15]:
        detail = info["details"][0]
        drug_summary += f"- {name} ({info['count']}x): target={detail.get('target','?')}, evidence={detail.get('evidence_level','?')}\n"

    prompt = f"""You have read {len(analyses)} papers on somatic CAG expansion in Huntington's Disease.

Paper summaries:
{chr(10).join(summaries[:20])}

Drug candidates found across papers:
{drug_summary}

Target frequency: {', '.join(f'{t}({c})' for t, c in sorted(((t, all_targets.count(t)) for t in set(all_targets)), key=lambda x: -x[1])[:10])}

Synthesize a comprehensive drug screen report. Return JSON:
{{
  "top_findings": ["3 most important findings about somatic expansion therapeutics"],
  "target_rankings": [
    {{
      "target": "MSH3|FAN1|PMS1|MLH1|LIG1",
      "papers_mentioning": N,
      "druggability": "high|medium|low",
      "most_advanced_approach": "description",
      "key_challenge": "main obstacle"
    }}
  ],
  "drug_candidates_ranked": [
    {{
      "rank": 1,
      "drug": "name",
      "target": "target",
      "modality": "small_molecule|ASO|siRNA|gene_therapy|splice_modifier",
      "developer": "company/lab",
      "stage": "preclinical|phase1|phase2|phase3",
      "evidence_summary": "what the data shows",
      "expansion_reduction": "% or qualitative",
      "confidence": 0-100
    }}
  ],
  "combination_hypotheses": [
    {{
      "drugs": ["drug1", "drug2"],
      "rationale": "why this combination could be synergistic",
      "targets_hit": ["target1", "target2"],
      "score": 0-100
    }}
  ],
  "mechanistic_debates": ["key scientific debates in the field"],
  "research_gaps": ["what's missing from the current research"],
  "novel_hypotheses": [
    {{
      "hypothesis": "description",
      "based_on_papers": ["pmid1", "pmid2"],
      "novelty": "what makes this hypothesis new",
      "score": 0-100
    }}
  ]
}}"""

    try:
        return ask_json(prompt,
            system="You are a senior HD researcher and drug discovery expert. "
                   "Rank candidates by evidence strength and clinical readiness. "
                   "Be bold with combination hypotheses but honest about evidence gaps.")
    except Exception as e:
        return {"error": str(e)}


def run():
    print(f"\n{'='*60}")
    print(f"  Experiment #4: Somatic CAG Expansion Drug Screen")
    print(f"  Model: {MODEL} (local)")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Phase 0: Discover papers
    print("Phase 0: Discovering somatic expansion papers from PubMed...\n")
    all_pmids = set()

    for query in SEARCH_QUERIES:
        pmids = search_pubmed(query, max_results=30)
        print(f"  '{query}' -> {len(pmids)} papers")
        all_pmids.update(pmids)
        time.sleep(1)

    # Also include relevant papers from existing corpus
    corpus_path = ROOT / "data" / "corpus.json"
    if corpus_path.exists():
        with open(corpus_path) as f:
            corpus = json.load(f)
        corpus_pmids = list(corpus.get("papers", {}).keys())
        print(f"\n  Existing corpus: {len(corpus_pmids)} papers")
        all_pmids.update(corpus_pmids)

    all_pmids = sorted(all_pmids)
    print(f"\n  Total unique PMIDs: {len(all_pmids)}")

    # Fetch metadata for new papers
    print("\n  Fetching metadata...")
    metadata = fetch_paper_metadata(all_pmids)
    print(f"  Got metadata for {len(metadata)} papers")

    # Merge with corpus metadata
    if corpus_path.exists():
        for pmid in all_pmids:
            if pmid not in metadata and pmid in corpus.get("papers", {}):
                metadata[pmid] = corpus["papers"][pmid]

    # Filter for relevance: keep papers whose title/abstract mention somatic expansion keywords
    somatic_keywords = [
        "somatic", "expansion", "instability", "repeat",
        "msh3", "fan1", "pms1", "mlh1", "lig1",
        "mismatch repair", "dna repair", "modifier",
        "cag repeat", "trinucleotide", "mutsbeta", "mutlgamma",
    ]
    relevant = {}
    for pmid, paper in metadata.items():
        text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
        if any(kw in text for kw in somatic_keywords):
            relevant[pmid] = paper

    print(f"\n  Filtered to {len(relevant)} relevant papers (somatic expansion keywords)")

    # Phase 1: Get full text
    print("\nPhase 1: Checking PMC for full text...\n")
    pmc_map = get_pmc_ids(list(relevant.keys()))
    print(f"  Full text available: {len(pmc_map)} papers")
    abstract_only = [p for p in relevant if p not in pmc_map]
    print(f"  Abstract only: {len(abstract_only)} papers")

    # Phase 2: Analyze papers
    print(f"\nPhase 2: Analyzing papers with {MODEL}...\n")
    analyses = []
    success = 0
    errors = 0

    # Full-text papers first (higher value), cap at 30
    pmc_items = list(pmc_map.items())[:30]
    print(f"  Analyzing up to {len(pmc_items)} full-text papers + up to 10 abstracts\n")
    for pmid, pmcid in pmc_items:
        paper = relevant.get(pmid, metadata.get(pmid, {}))
        title = paper.get("title", "Unknown")[:80]
        print(f"  [{len(analyses)+1}/{len(relevant)}] {title}")
        print(f"    PMCID: {pmcid} (full text)")

        sections = fetch_full_text(pmcid)
        if not sections:
            print("    No text returned, falling back to abstract")
            abstract = paper.get("abstract", "")
            if abstract:
                analysis = analyze_abstract_somatic(title, abstract)
                analyses.append({
                    "pmid": pmid, "pmcid": pmcid, "title": paper.get("title", ""),
                    "journal": paper.get("journal", ""), "type": "abstract",
                    "sections_count": 0, "total_chars": len(abstract),
                    "analysis": analysis,
                })
            continue

        total_chars = sum(len(s["text"]) for s in sections)
        print(f"    {len(sections)} sections, {total_chars:,} chars")

        analysis = analyze_paper_somatic(title, sections, paper.get("abstract", ""))

        finding = analysis.get("main_finding", "?")
        score = analysis.get("relevance_score", "?")
        drugs_found = len(analysis.get("drug_candidates", []))
        print(f"    Finding: {str(finding)[:80]}")
        print(f"    Relevance: {score}/10 | Drug candidates: {drugs_found}")

        if "error" not in analysis:
            success += 1
        else:
            errors += 1

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

    # Then abstract-only papers
    for pmid in abstract_only[:10]:  # Cap at 10 abstract-only to keep runtime reasonable
        paper = relevant.get(pmid, metadata.get(pmid, {}))
        abstract = paper.get("abstract", "")
        if not abstract:
            continue

        title = paper.get("title", "Unknown")[:80]
        print(f"  [{len(analyses)+1}/{len(relevant)}] {title}")
        print(f"    PMID: {pmid} (abstract only)")

        analysis = analyze_abstract_somatic(title, abstract)

        finding = analysis.get("main_finding", "?")
        print(f"    Finding: {str(finding)[:80]}")

        if "error" not in analysis:
            success += 1
        else:
            errors += 1

        analyses.append({
            "pmid": pmid, "title": paper.get("title", ""),
            "journal": paper.get("journal", ""),
            "type": "abstract",
            "sections_count": 0,
            "total_chars": len(abstract),
            "analysis": analysis,
        })
        print()
        time.sleep(2)

    print(f"\n  Analyzed: {success} successful, {errors} errors out of {len(analyses)} papers")

    # Phase 3: Drug screen synthesis
    print(f"\nPhase 3: Synthesizing drug screen across {len(analyses)} papers...\n")
    synthesis = synthesize_drug_screen(analyses)

    if "top_findings" in synthesis:
        print("Top findings:")
        for f in synthesis.get("top_findings", []):
            print(f"  - {str(f)[:100]}")

    if "drug_candidates_ranked" in synthesis:
        print("\nDrug candidates ranked:")
        for d in synthesis.get("drug_candidates_ranked", [])[:5]:
            if isinstance(d, dict):
                print(f"  #{d.get('rank','?')} {d.get('drug','?')} -> {d.get('target','?')} ({d.get('stage','?')}) [{d.get('confidence',0)}/100]")

    if "novel_hypotheses" in synthesis:
        print("\nNovel hypotheses:")
        for h in synthesis.get("novel_hypotheses", []):
            if isinstance(h, dict):
                print(f"  [{h.get('score',0)}/100] {str(h.get('hypothesis',''))[:100]}")

    # Save results
    results = {
        "experiment_id": "EXP-004-SOMATIC-CAG",
        "timestamp": datetime.now().isoformat(),
        "model": MODEL,
        "type": "somatic_cag_expansion_drug_screen",
        "search_queries": SEARCH_QUERIES,
        "somatic_targets": SOMATIC_TARGETS,
        "papers_discovered": len(all_pmids),
        "papers_relevant": len(relevant),
        "papers_analyzed": len(analyses),
        "full_text_analyzed": sum(1 for a in analyses if a.get("type") == "full_text"),
        "abstract_only_analyzed": sum(1 for a in analyses if a.get("type") == "abstract"),
        "total_sections_read": sum(a.get("sections_count", 0) for a in analyses),
        "total_characters_read": sum(a.get("total_chars", 0) for a in analyses),
        "analyses": analyses,
        "synthesis": synthesis,
    }

    results_path = DATA_DIR / "experiment_004_somatic_cag_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Write report
    report = f"""# Experiment #4: Somatic CAG Expansion Drug Screen

**Date:** {datetime.now().strftime('%B %d, %Y')}
**Model:** {MODEL} (local, Apple M2)
**Papers discovered:** {len(all_pmids)}
**Papers relevant (filtered):** {len(relevant)}
**Papers analyzed:** {len(analyses)} ({results['full_text_analyzed']} full text, {results['abstract_only_analyzed']} abstract)
**Total characters read:** {results['total_characters_read']:,}
**Targets screened:** {', '.join(SOMATIC_TARGETS)}

## Why Somatic Expansion?

GWAS studies identified DNA repair genes as the strongest modifiers of HD onset.
Natural genetic variants in these genes delay onset by 6-8 years. The somatic
expansion pathway (MutSbeta -> MutLgamma -> Pol-delta -> LIG1, opposed by FAN1)
is now the most active frontier in HD drug development, with multiple companies
(LoQus23, Harness, Skyhawk, Rgenta) developing drugs against these targets.

## Top Findings

"""
    for i, f in enumerate(synthesis.get("top_findings", []), 1):
        report += f"{i}. {f}\n"

    report += "\n## Target Rankings\n\n"
    report += "| Target | Papers | Druggability | Most Advanced Approach | Key Challenge |\n"
    report += "|--------|--------|-------------|----------------------|---------------|\n"
    for t in synthesis.get("target_rankings", []):
        if isinstance(t, dict):
            report += f"| {t.get('target','')} | {t.get('papers_mentioning',0)} | {t.get('druggability','')} | {t.get('most_advanced_approach','')} | {t.get('key_challenge','')} |\n"

    report += "\n## Drug Candidates Ranked\n\n"
    for d in synthesis.get("drug_candidates_ranked", []):
        if isinstance(d, dict):
            report += f"### #{d.get('rank','?')}. {d.get('drug','')} ({d.get('confidence',0)}/100)\n"
            report += f"- **Target:** {d.get('target','')}\n"
            report += f"- **Modality:** {d.get('modality','')}\n"
            report += f"- **Developer:** {d.get('developer','')}\n"
            report += f"- **Stage:** {d.get('stage','')}\n"
            report += f"- **Evidence:** {d.get('evidence_summary','')}\n"
            report += f"- **Expansion reduction:** {d.get('expansion_reduction','')}\n\n"

    report += "## Combination Hypotheses\n\n"
    for c in synthesis.get("combination_hypotheses", []):
        if isinstance(c, dict):
            drugs = " + ".join(c.get("drugs", []))
            report += f"- **{drugs}** [{c.get('score',0)}/100]: {c.get('rationale','')}\n"

    report += "\n## Novel Hypotheses\n\n"
    for h in synthesis.get("novel_hypotheses", []):
        if isinstance(h, dict):
            report += f"- [{h.get('score',0)}/100] {h.get('hypothesis','')}\n"
            report += f"  *Novelty: {h.get('novelty','')}*\n\n"

    report += "\n## Research Gaps\n\n"
    for g in synthesis.get("research_gaps", []):
        report += f"- {g}\n"

    report += f"""
## Methodology

- PubMed searched with {len(SEARCH_QUERIES)} targeted queries (2024-2026)
- Full text from PMC where available, abstracts as fallback
- Each paper screened by {MODEL} with somatic expansion-specific prompts
- Cross-paper synthesis ranks drug candidates by evidence and clinical readiness
- All code: github.com/jravinder/hd-research-agent

## Limitations

- Only open-access papers analyzed (paywalled papers excluded)
- Single model, single run (different temperature/prompt could change results)
- Not reviewed by HD domain experts or medicinal chemists
- Drug candidate rankings reflect AI assessment, not clinical validation
- Abstract-only papers contribute lower-confidence results

This is AI-generated research analysis, not medical advice.
For HD support, visit hdsa.org.
"""

    report_path = DATA_DIR / "experiment_004_somatic_cag_report.md"
    with open(report_path, "w") as f:
        f.write(report)

    print(f"\n{'='*60}")
    print(f"  Experiment #4 complete!")
    print(f"  Papers discovered: {len(all_pmids)}")
    print(f"  Papers analyzed: {len(analyses)} ({results['full_text_analyzed']} full text)")
    print(f"  Characters read: {results['total_characters_read']:,}")
    print(f"  Results: {results_path}")
    print(f"  Report: {report_path}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    run()
