# HD Research Agent

An AI-powered research agent for Huntington's Disease drug discovery. Uses LLMs to analyze published research, identify drug repurposing candidates, and run autonomous experiment loops on publicly available HD datasets.

## Why This Exists

- **41,000 people** are currently dying from HD in the US alone, 200,000+ at risk
- **AMT-130** (the first treatment to slow HD by 75%) is blocked by the FDA demanding more data
- **AI can help**: drug repurposing, synthetic control arms, and autonomous research loops are all underexplored in HD
- Nobody is running autoresearch-style agent loops on HD yet — this repo changes that

## What It Does

1. **Literature Agent** — Pulls recent HD papers from PubMed/arXiv, extracts key findings, builds a knowledge graph of targets, compounds, and mechanisms
2. **Repurposing Scanner** — Cross-references known drugs against HD-relevant gene targets identified in transcriptomic studies (BDASeq, CHDI data)
3. **Trial Analyzer** — Parses ClinicalTrials.gov for HD pipeline status, tracks which compounds are advancing or failing
4. **Autoresearch Loop** — Runs overnight: generates hypotheses, searches literature, scores candidates, refines — Karpathy-style

## Stack

- Python 3.10+
- Ollama (local LLM inference — works on Jetson AGX Orin or Mac)
- LiteLLM for model routing
- PubMed E-utilities API (free, no key needed)
- ClinicalTrials.gov API (free)

## Quick Start

```bash
pip install -r requirements.txt

# Run the literature agent (pulls recent HD papers)
python src/literature_agent.py

# Run the repurposing scanner
python src/repurposing_scanner.py

# Run the full autoresearch loop (runs overnight)
python src/autoresearch.py --hours=8
```

## Architecture

```
src/
├── literature_agent.py    # PubMed/arXiv paper fetcher + LLM summarizer
├── repurposing_scanner.py # Drug-target cross-reference engine
├── trial_tracker.py       # ClinicalTrials.gov HD pipeline monitor
├── autoresearch.py        # Autonomous research loop orchestrator
├── knowledge_graph.py     # In-memory graph of targets, compounds, mechanisms
└── llm.py                 # LLM interface (Ollama/LiteLLM)
```

## Data Sources

- [PubMed](https://pubmed.ncbi.nlm.nih.gov/) — HD research literature (E-utilities API)
- [ClinicalTrials.gov](https://clinicaltrials.gov/) — Active HD trials
- [HDSA Pipeline](https://hdsa.org/hd-research/therapies-in-pipeline/) — Therapy tracker
- [Enroll-HD](https://www.enroll-hd.org/) — Longitudinal patient data (requires access request)

## License

MIT
