# HD Research Hub: Build Log

## Session 1: March 27-31, 2026

### What We Built (from zero)

**83 commits. 13 web pages. 20 Python scripts. 8 data files. 1 session.**

### Timeline

**Day 1 (March 27)**
- Researched HD landscape using /last30days (GTC, autoresearch, HD, TeamPCP)
- Set up X/Twitter auth for last30days skill
- Security audit: patched 32 CVEs across Mac, Jetson, DO droplet. Removed litellm (TeamPCP supply chain attack)
- Built entire HD Research Hub repo from scratch
- Experiment #1: 22 abstracts analyzed by Llama 3.1 8B on Jetson. 5 drug hypotheses generated
- Paper Scout: 46 papers discovered and analyzed
- Hypothesis Refiner: first run, 5 hypotheses scored
- Published to Vercel, set up GitHub Actions daily refresh
- Created CLAUDE.md with project vision

**Day 2 (March 28-29)**
- Redesigned site with Google Stitch "Sunrise Hope" design system
- Built RAG chatbot (NVIDIA NIM + Sarvam AI for 22 Indian languages)
- Medical guardrails: pre-commit hook, input filter (30+ patterns), system prompt rules
- Built knowledge base: 1,571 full-text chunks from 20 papers via PubMed Central
- Set up Upstash Vector (serverless semantic search, BGE embeddings)
- Added Redis Stack locally for development vector search
- Created 9 web pages: experiment reports, about, journey, guide, how-it-works, research tracker, chat
- Added Google Analytics (G-N8BMJ7ZG5V)
- Protected main branch, set up PR workflow, git pre-push hook

**Day 3 (March 30-31)**
- Experiment #2: 16 full papers read end-to-end (1.9M characters, 380 sections)
- Top hypothesis: cGAS mtDNA release inhibition (90/100)
- Built learning path page (genomics courses, HD concepts)
- Built landscape page (competition, challenges, opportunities)
- Drafted startup credit applications (NVIDIA Inception, Google, Anthropic, Microsoft)
- Updated hackathon-playbook with HD Research Hub as project #6
- Pulled Qwen 3.5 27B for Experiment #3 (multi-model comparison)

**Day 4 (April 1)**
- Experiment #3 running: Qwen 3.5 27B on same 16 papers (comparing to Llama 3.1 8B)
- Set up Jetson SD card (238GB) for Ollama model storage

### Infrastructure Built

| Component | Stack | Status |
|-----------|-------|--------|
| Website | Vercel + static HTML + Tailwind | Live |
| Chatbot | NVIDIA NIM + Sarvam AI + Upstash Vector | Live |
| Knowledge Base | 1,571 chunks from 46 papers (20 full text) | Built |
| Vector Search | Upstash Vector (BGE-base-en-v1.5, 768 dim) | Live |
| Local Vector DB | Redis Stack (HNSW, nomic-embed-text) | Built |
| LLM (experiments) | Ollama (Llama 3.1 8B on Jetson, Qwen 3.5 27B on Mac) | Running |
| LLM (chatbot) | NVIDIA NIM (Nemotron) via Vercel serverless | Live |
| Translation | Sarvam AI (22 Indian languages) | Live |
| Data Pipeline | GitHub Actions daily (PubMed, ClinicalTrials.gov, HDBuzz, Open Targets) | Active |
| Design System | Google Stitch "Sunrise Hope" (amber/gold palette) | Applied |
| Analytics | GA4 (G-N8BMJ7ZG5V) | Live |
| Guardrails | Pre-commit hook (medical disclaimers), chatbot input filter | Active |
| Branch Protection | GitHub (PRs required), git pre-push hook (blocks main) | Active |

### Experiments

| ID | Name | Model | Data | Key Result |
|----|------|-------|------|------------|
| EXP-001 | Abstract Analysis | Llama 3.1 8B | 22 abstracts | Tocilizumab 80/100, TDP-43 connection |
| EXP-002 | Full-Text Deep Analysis | Llama 3.1 8B | 16 papers, 1.9M chars | cGAS mtDNA 90/100, LIG1 K845N 80/100 |
| EXP-003 | Multi-Model Comparison | Qwen 3.5 27B | Same 16 papers | Running |

### Agents Built

| Agent | Purpose | Runs |
|-------|---------|------|
| Paper Scout | Discover + analyze new HD papers | 1 (46 papers) |
| Hypothesis Refiner | Re-score drug candidates against new evidence | 1 (scores stable) |
| Social Watcher | Monitor X, Reddit, YouTube, HN for HD chatter | 0 |
| Digest Writer | Weekly research summary | 0 |

### Web Pages (13 total)

| Page | URL |
|------|-----|
| Dashboard | / |
| Ask HD Research (chatbot) | /chat.html |
| Experiment #1 | /experiment-1.html |
| Experiment #2 | /experiment-2.html |
| Research Tracker | /research.html |
| How It Works | /how-it-works.html |
| Learning Path | /learn.html |
| HD + AI Landscape | /landscape.html |
| About | /about.html |
| Journey | /journey.html |
| Guide | /guide.html |
| Privacy Policy | /privacy.html |
| Terms of Use | /terms.html |

### Key Decisions Made

1. **No litellm** after TeamPCP supply chain attack. Direct Ollama API calls only.
2. **Full-text knowledge base** as differentiator. Chat with actual papers, not summaries.
3. **Upstash Vector with built-in embeddings** for serverless semantic search (no Ollama needed in production).
4. **Medical guardrails baked in** at code level, not just UI disclaimers.
5. **PRs to main only**. Branch protection + pre-push hook + pre-commit guardrails.
6. **Sunrise Hope design** via Google Stitch. Warm, hopeful, readable.
7. **Honest about limitations**. Every experiment publishes what worked AND what didn't.
8. **Indian language support** via Sarvam AI (not just Google Translate).
9. **Edge-first inference**. Jetson for experiments, NIM for production chatbot.
10. **Open source everything**. MIT license. Public repo. Published data.

### Credits Applied For (planned)

| Program | Credits | Status |
|---------|---------|--------|
| NVIDIA Inception | Free + $100K AWS + BioNeMo | Planned |
| Google for Startups | Up to $350K GCP | Planned |
| Anthropic Startup | $25K-$100K Claude API | Planned |
| Microsoft for Startups | $150K Azure (via Inception) | Planned |

### Lessons Learned This Session

- 27B models on M2 Mac are too slow for full-paper analysis (timeout at 10 min/paper). Need GPU or API credits.
- Upstash Vector dimension must match embedding model exactly. Recreated index 3 times.
- Google Translate `.skiptranslate` CSS hides the dropdown. Need selective override.
- macOS occasionally locks directories (iCloud sync + extended attributes). Restart terminal fixes it.
- Pre-push hook works great for enforcing PR workflow. Caught direct push attempts immediately.
- The guardrail pre-commit hook caught missing medical disclaimers multiple times. Worth the setup cost.
- Full-text paper analysis produces meaningfully different results than abstract-only. LIG1 K845N and cGAS findings were invisible from abstracts.
