# HD Research Hub

An open experiment in applying AI to real-world drug discovery — built for data scientists, AI/ML engineers, researchers, and curious builders.

We're exploring how autonomous agents, LLMs, and public datasets can contribute to Huntington's Disease research. This is an experimentation playground, not a medical product.

**Live site:** [hd-research-agent.vercel.app](https://hd-research-agent.vercel.app)

> **Note:** This project is for research and educational purposes. For medical information about HD, please visit [HDSA](https://hdsa.org), [HDBuzz](https://en.hdbuzz.net), or consult your healthcare provider. Our AI-generated hypotheses are unvalidated starting points, not clinical findings.

## The Art of the Possible

Applying agentic AI to hard problems — HD is one of the hardest, and the tools are finally here:

- **75% disease slowing** demonstrated in AMT-130 gene therapy trial — the first treatment to meaningfully modify HD progression
- **7+ therapies** in active clinical trials, with 21 studies recruiting right now
- **AI is opening new doors** — Novartis used generative AI to design 15 million candidate compounds; SOM Biotech's AI platform discovered a drug repurposing candidate now in Phase II
- **Digital twins** (Unlearn) could transform how clinical trials are run, making them faster and more accessible

This project asks: what else can AI contribute?

## What It Does

1. **Literature Agent** — Pulls recent HD papers from PubMed, uses LLMs to extract targets, compounds, key findings, and drug repurposing opportunities
2. **Drug Repurposing Scanner** — Cross-references 16 known HD targets against FDA-approved drugs. Generates and scores novel hypotheses
3. **Trial Tracker** — Live data from ClinicalTrials.gov — which trials are recruiting, who's sponsoring, what's advancing
4. **Autoresearch Loop** — Karpathy-style overnight agent: generates hypotheses, searches literature, scores candidates, refines autonomously
5. **Live Dashboard** — Auto-updated daily from PubMed, ClinicalTrials.gov, HDBuzz, and Open Targets

## Quick Start

```bash
pip install -r requirements.txt

# Pull fresh data from all sources and rebuild the site
python src/build_site.py --no-deploy --refresh-data

# Run the literature agent (pulls and analyzes PubMed papers)
python src/literature_agent.py

# Run the repurposing scanner (AI-generated drug hypotheses)
python src/repurposing_scanner.py

# Run the full autoresearch loop overnight
python src/autoresearch.py --hours=8
```

## Architecture

```
src/
├── data_fetcher.py       # Pulls from PubMed, ClinicalTrials.gov, HDBuzz, Open Targets
├── build_site.py         # Generates index.html from live data, auto-deploys
├── literature_agent.py   # PubMed paper fetcher + LLM analyzer
├── repurposing_scanner.py# Drug-target cross-reference + AI hypothesis generator
├── trial_tracker.py      # ClinicalTrials.gov HD pipeline monitor
├── autoresearch.py       # Autonomous overnight research loop
└── llm.py                # Ollama API interface (no third-party AI dependencies)
```

## Stack

- Python 3.10+
- Ollama (local LLM inference — works on Jetson AGX Orin or Mac)
- PubMed E-utilities API (free)
- ClinicalTrials.gov API (free)
- HDBuzz RSS (free)
- Open Targets GraphQL (free)
- Vercel (auto-deploy on push)
- GitHub Actions (daily data refresh)

## Data Sources

All data is from publicly available, authoritative sources:

- [PubMed](https://pubmed.ncbi.nlm.nih.gov/) — Research literature
- [ClinicalTrials.gov](https://clinicaltrials.gov/) — Active HD trials
- [HDBuzz](https://en.hdbuzz.net/) — HD news in plain language
- [Open Targets](https://platform.opentargets.org/) — Drug-target associations
- [HDSA](https://hdsa.org/hd-research/therapies-in-pipeline/) — Therapy pipeline

## Resources

If you or someone you know is affected by HD:

- [HDSA](https://hdsa.org) — Support groups, Centers of Excellence, advocacy
- [HDBuzz](https://en.hdbuzz.net) — Research news explained in plain language
- [HDYO](https://www.hdyo.org) — Resources for young people
- [Enroll-HD](https://www.enroll-hd.org) — Join the world's largest HD study
- [HD Reach](https://hdreach.org) — Rehab and exercise resources

## Contributing

All welcome — data scientists, ML engineers, bioinformaticians, HD researchers, families, and anyone who wants to help. Open an issue or submit a PR.

## License

MIT
