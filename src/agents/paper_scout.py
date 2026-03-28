"""Paper Scout Agent — continuously discovers and analyzes new HD papers.

Runs every 6 hours. Maintains a growing corpus in data/corpus.json.
Only analyzes papers it hasn't seen before. Builds up knowledge over time.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from literature_agent import search_pubmed, fetch_papers
from llm import ask_json

ROOT = Path(__file__).parent.parent.parent
CORPUS_FILE = ROOT / "data" / "corpus.json"

# Diverse queries to cast a wide net
QUERIES = [
    "huntington disease treatment",
    "huntington disease gene therapy",
    "huntington somatic expansion CAG",
    "huntington drug repurposing",
    "huntington biomarker neurofilament",
    "huntington CRISPR",
    "huntington antisense oligonucleotide",
    "huntington neuroinflammation",
    "huntington autophagy mTOR",
    "huntington digital twin clinical trial",
    "huntingtin protein structure drug target",
    "MSH3 FAN1 PMS1 repeat expansion",
]


def load_corpus():
    if CORPUS_FILE.exists():
        with open(CORPUS_FILE) as f:
            return json.load(f)
    return {"papers": {}, "last_run": None, "total_runs": 0}


def save_corpus(corpus):
    CORPUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CORPUS_FILE, "w") as f:
        json.dump(corpus, f, indent=2, default=str)


def analyze_paper_safe(paper):
    """Analyze with LLM, return None on failure."""
    prompt = f"""Analyze this Huntington's disease research paper:

Title: {paper.title}
Abstract: {paper.abstract[:800]}

Return JSON:
{{
  "category": "gene_therapy|small_molecule|biomarker|mechanism|ai_ml|clinical_trial|crispr|aso|review|other",
  "targets": ["molecular targets or genes"],
  "compounds": ["drugs or compounds"],
  "finding": "one sentence key discovery",
  "relevance": "high|medium|low",
  "repurposing_potential": true/false,
  "novel_insight": "what is new or surprising here, or null"
}}"""
    try:
        return ask_json(prompt, system="You are a biomedical research analyst specializing in Huntington's disease.")
    except Exception as e:
        return None


def run():
    corpus = load_corpus()
    seen_pmids = set(corpus["papers"].keys())
    new_count = 0
    analyzed_count = 0

    print(f"\n{'='*50}")
    print(f"Paper Scout Agent — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Corpus size: {len(seen_pmids)} papers")
    print(f"{'='*50}\n")

    for query in QUERIES:
        print(f"  Searching: {query}")
        try:
            pmids = search_pubmed(query, days=60, max_results=10)
            new_pmids = [p for p in pmids if p not in seen_pmids]

            if not new_pmids:
                print(f"    No new papers")
                continue

            print(f"    {len(new_pmids)} new papers found")
            papers = fetch_papers(new_pmids)
            time.sleep(1)  # Rate limit PubMed

            for paper in papers:
                if paper.pmid in seen_pmids:
                    continue

                print(f"    Analyzing [{paper.pmid}] {paper.title[:50]}...")
                analysis = analyze_paper_safe(paper)

                corpus["papers"][paper.pmid] = {
                    "pmid": paper.pmid,
                    "title": paper.title,
                    "abstract": paper.abstract[:500],
                    "journal": paper.journal,
                    "date": paper.pub_date,
                    "authors": paper.authors,
                    "query": query,
                    "discovered": datetime.now().isoformat(),
                    "analysis": analysis,
                }
                seen_pmids.add(paper.pmid)
                new_count += 1
                if analysis:
                    analyzed_count += 1
                    finding = analysis.get("finding", "")
                    print(f"      -> {finding[:80]}")

                time.sleep(2)  # Rate limit LLM

        except Exception as e:
            print(f"    Error: {e}")
            continue

        time.sleep(1)

    corpus["last_run"] = datetime.now().isoformat()
    corpus["total_runs"] = corpus.get("total_runs", 0) + 1
    save_corpus(corpus)

    print(f"\n{'='*50}")
    print(f"  New papers: {new_count}")
    print(f"  Analyzed: {analyzed_count}")
    print(f"  Total corpus: {len(corpus['papers'])}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    run()
