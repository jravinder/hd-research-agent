# HD Research Hub

> **Gemma 4 Good Hackathon submission** — agentic Huntington's Disease research assistant powered by **Google Gemma 4** (native function calling + multimodal vision). The only HD entry in the field. [Live demo](https://hd-research-agent.vercel.app/chat.html) · [Technical write-up](docs/HACKATHON.md) · [Notebook](notebooks/gemma4_hd_research.ipynb)

An open research infrastructure project for Huntington's Disease: part literature tracker, part trial monitor, part AI-assisted hypothesis workspace.

We're exploring whether autonomous agents, LLMs, and public datasets can make early-stage HD research exploration more legible, reviewable, and useful. This is research infrastructure, not a medical product.

**Live site:** [hd-research-agent.vercel.app](https://hd-research-agent.vercel.app)
**Chatbot:** [hd-research-agent.vercel.app/chat.html](https://hd-research-agent.vercel.app/chat.html) — chat with the actual research, upload paper figures, ask Gemma 4.

> **Note:** This project is for research and educational purposes. For medical information about HD, please visit [HDSA](https://hdsa.org), [HDBuzz](https://en.hdbuzz.net), or consult your healthcare provider. AI-generated hypotheses here are triage artifacts, not medical advice or validated findings.

## Why This Is Worth Building

The value is not that an LLM can solve Huntington's Disease. The value is narrower and more defensible:

- **Faster literature triage** — new HD papers, trials, and news get consolidated into one inspectable workflow
- **Structured hypothesis generation** — candidate ideas are linked back to targets, papers, and rationale instead of living as vague prompts
- **Open experimentation** — methods, failures, and reports are published so others can critique or extend the process
- **Lower cost of participation** — engineers and researchers can build on public datasets without recreating the whole stack

This project asks a practical question: can agent workflows help humans review more signal with less wasted time?

## What It Does

1. **Literature Agent** — Pulls recent HD papers from PubMed, uses LLMs to extract targets, compounds, key findings, and drug repurposing opportunities
2. **Drug Repurposing Scanner** — Cross-references 16 known HD targets against FDA-approved drugs. Generates and scores novel hypotheses
3. **Trial Tracker** — Live data from ClinicalTrials.gov — which trials are recruiting, who's sponsoring, what's advancing
4. **Autoresearch Loop** — overnight loop that generates questions, searches literature, scores candidates, and logs each cycle
5. **Live Dashboard** — static site regenerated from PubMed, ClinicalTrials.gov, HDBuzz, and Open Targets data

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
├── llm.py                # Gemma 4 across two backends (Ollama edge + AI Studio hosted)
└── chat_tools.py         # 5 tools + schemas for the agentic chatbot
```

## Stack

- Python 3.10+
- **Google Gemma 4** across two backends, one codebase
  - Edge: **Ollama** on Jetson AGX Orin (`gemma4:latest`, 8B Q4_K_M) for the daily research pipeline
  - Hosted: **Google AI Studio / Gemini API** (`gemma-4-31b-it`) for the live serverless chatbot
  - Selected at runtime via `HD_LLM_BACKEND=ollama|aistudio`
- PubMed E-utilities API (free)
- ClinicalTrials.gov API (free)
- HDBuzz RSS (free)
- Open Targets GraphQL (free)
- Upstash Vector (embeddings for `search_papers`)
- Sarvam AI (22 Indian languages)
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
