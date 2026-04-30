"""Paper Analyzer Agent — Gemma reads new papers and extracts structured data.

Runs after Paper Scout finds new papers. For each unanalyzed paper:
1. Fetches full text from PMC (or uses abstract)
2. Sends to Gemma for structured analysis
3. Saves results to knowledge base
4. Updates corpus with analysis

This is the core intelligence loop: new papers come in, Gemma reads them,
structured knowledge comes out.
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

ROOT = Path(__file__).parent.parent.parent
DATA_DIR = ROOT / "data"
CORPUS_FILE = DATA_DIR / "corpus.json"
KB_FILE = DATA_DIR / "knowledge_base.json"
ANALYSIS_LOG = DATA_DIR / "analysis_log.json"

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
        try:
            resp = requests.get(
                "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/",
                params={"ids": ",".join(batch), "format": "json"},
                timeout=15
            )
            if resp.ok:
                for rec in resp.json().get("records", []):
                    if rec.get("pmcid"):
                        pmc_map[rec.get("pmid", "")] = rec["pmcid"]
        except Exception:
            pass
        time.sleep(1)
    return pmc_map


def fetch_full_text(pmcid):
    try:
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
    except Exception:
        return None


def analyze_paper(title, text, is_abstract=False):
    """Send paper to Gemma for structured analysis."""
    if len(text) > 50000:
        text = text[:50000] + "\n\n[... truncated at 50K chars ...]"

    source_type = "abstract" if is_abstract else "full paper"

    prompt = f"""You are analyzing an HD research {source_type}. Extract all therapeutically relevant information.

Title: {title}

TEXT:
{text}

Return JSON:
{{
  "category": "gene_therapy|small_molecule|biomarker|mechanism|clinical_trial|aso|review|neuroprotection|combination_therapy|other",
  "main_finding": "2-3 sentence summary",
  "therapeutic_approach": "What therapeutic strategy does this explore?",
  "targets": ["molecular targets or genes"],
  "compounds": ["drugs or compounds mentioned"],
  "novel_insights": ["2-3 new things this reveals"],
  "drug_repurposing_signals": ["existing drugs potentially useful for HD"],
  "somatic_expansion_relevance": "direct|indirect|none",
  "clinical_readiness": "concept|preclinical|clinical",
  "relevance_score": 1-10,
  "confidence": "high|medium|low"
}}"""

    try:
        return ask_json(prompt,
            system="You are a senior neuroscience researcher. Be specific about mechanisms and evidence levels.")
    except Exception as e:
        return {"error": str(e), "main_finding": f"Analysis failed: {e}"}


def load_analysis_log():
    if ANALYSIS_LOG.exists():
        with open(ANALYSIS_LOG) as f:
            return json.load(f)
    return {"analyzed": {}, "last_run": None}


def save_analysis_log(log):
    with open(ANALYSIS_LOG, "w") as f:
        json.dump(log, f, indent=2, default=str)


def run():
    print(f"\n{'='*50}")
    print(f"  Paper Analyzer Agent")
    print(f"  Model: {MODEL}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    # Load corpus and analysis log
    if not CORPUS_FILE.exists():
        print("  No corpus.json found. Run paper_scout first.")
        return

    with open(CORPUS_FILE) as f:
        corpus = json.load(f)

    log = load_analysis_log()
    analyzed_pmids = set(log.get("analyzed", {}).keys())

    # Find unanalyzed papers
    all_pmids = list(corpus.get("papers", {}).keys())
    new_pmids = [p for p in all_pmids if p not in analyzed_pmids]

    print(f"  Corpus: {len(all_pmids)} papers")
    print(f"  Already analyzed: {len(analyzed_pmids)}")
    print(f"  New to analyze: {len(new_pmids)}")

    if not new_pmids:
        print("  Nothing new to analyze.")
        log["last_run"] = datetime.now().isoformat()
        save_analysis_log(log)
        return

    # Get PMC IDs for full text
    print("\n  Checking PMC for full text...")
    pmc_map = get_pmc_ids(new_pmids)
    print(f"  Full text available: {len(pmc_map)}")

    # Analyze papers (cap at 10 per run to keep runtime reasonable)
    max_per_run = 10
    to_analyze = new_pmids[:max_per_run]
    success = 0
    new_analyses = []

    print(f"\n  Analyzing up to {len(to_analyze)} papers...\n")

    for i, pmid in enumerate(to_analyze):
        paper = corpus["papers"].get(pmid, {})
        title = paper.get("title", "Unknown")[:80]
        print(f"  [{i+1}/{len(to_analyze)}] {title}")

        pmcid = pmc_map.get(pmid)
        analysis = None

        if pmcid:
            sections = fetch_full_text(pmcid)
            if sections:
                full_text = "\n\n".join(f"## {s['section']}\n{s['text']}" for s in sections)
                total_chars = len(full_text)
                print(f"    Full text: {total_chars:,} chars")
                analysis = analyze_paper(title, full_text, is_abstract=False)
            else:
                print("    No full text returned")

        if analysis is None:
            abstract = paper.get("abstract", "")
            if abstract:
                print(f"    Using abstract: {len(abstract)} chars")
                analysis = analyze_paper(title, abstract, is_abstract=True)

        if analysis and "error" not in analysis:
            finding = str(analysis.get("main_finding", ""))[:80]
            score = analysis.get("relevance_score", "?")
            print(f"    Finding: {finding}")
            print(f"    Relevance: {score}/10")
            success += 1
        else:
            print(f"    Analysis failed")

        # Save to log
        log["analyzed"][pmid] = {
            "timestamp": datetime.now().isoformat(),
            "pmcid": pmcid,
            "analysis": analysis or {"error": "No text available"},
        }

        if analysis:
            new_analyses.append({
                "pmid": pmid,
                "title": paper.get("title", ""),
                "analysis": analysis,
            })

        print()
        time.sleep(2)

    # Save log
    log["last_run"] = datetime.now().isoformat()
    log["total_analyzed"] = len(log["analyzed"])
    save_analysis_log(log)

    print(f"\n{'='*50}")
    print(f"  Paper Analyzer complete")
    print(f"  Analyzed: {success}/{len(to_analyze)} successful")
    print(f"  Total in log: {len(log['analyzed'])}")
    print(f"  Remaining: {len(new_pmids) - len(to_analyze)}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    run()
