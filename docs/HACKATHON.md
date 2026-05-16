# HD Research Hub — Gemma 4 Good Hackathon Submission

## The question

Can AI compound the slow loop of Huntington's Disease research, paper by paper, day after day, instead of replacing it? This is the only Huntington's Disease entry in the competition.

## What we built

A live agentic chatbot at [hd-research-agent.vercel.app](https://hd-research-agent.vercel.app) powered by **Gemma 4** with native function calling over a Huntington's Disease research knowledge base, plus multimodal image upload that interprets paper figures. Behind the site sits a daily edge-inference pipeline running on a Jetson AGX Orin that ingests new PubMed papers, extracts findings, and scores drug-repurposing hypotheses. One `src/llm.py` module talks to both backends.

Try it:

- **Live demo:** [hd-research-agent.vercel.app](https://hd-research-agent.vercel.app)
- **Chatbot:** [hd-research-agent.vercel.app/chat.html](https://hd-research-agent.vercel.app/chat.html)
- **Repo:** [github.com/jravinder/hd-research-agent](https://github.com/jravinder/hd-research-agent)
- **Notebook:** `notebooks/gemma4_hd_research.ipynb`

## How Gemma 4 is used

### 1. Native function calling (the chatbot)

`api/chat.py` is now agentic. Gemma 4 sees five tools and decides which to call:

- `search_papers(query)` — semantic + keyword search over the full-text knowledge base
- `get_clinical_trials(status?)` — live HD trials from ClinicalTrials.gov
- `get_target_info(gene)` — ranked HD targets from Open Targets
- `get_experiment_findings(n?)` — AI-generated drug-repurposing hypotheses from our experiments
- `get_latest_papers(days?)` — recently ingested corpus papers

User message → Gemma 4 emits a tool call → we execute → results feed back in → up to three turns → Gemma 4 composes a cited answer. The UI surfaces which tools Gemma called for that answer, matching the project's chain-of-thought transparency philosophy. This replaces a fixed-RAG pipeline that previously called NVIDIA NIM.

### 2. Multimodal vision (chatbot image upload)

`chat.html` accepts a research figure. The serverless function calls `ask_vision()` on `gemma-4-31b-it`, grounds the answer in a quick `search_papers` lookup, and returns a figure interpretation: what is plotted, the apparent finding, and any quantitative values Gemma 4 can read off (effect sizes, p-values, sample sizes).

A **vision guardrail** runs first. Every uploaded image is classified by Gemma 4 as `PERSONAL_MEDICAL`, `RESEARCH_FIGURE`, or `OTHER`. Personal medical images (MRI, CT, X-ray, photographs of people, genetic test reports) trigger a redirect to HDSA and a neurologist. The previous guardrail was text-only; image upload opened a clinical-input door the project's rules forbid, so Gemma 4 is now the gatekeeper for both surfaces.

### 3. Edge inference (the research pipeline)

The same `src/llm.py` module runs on a Jetson AGX Orin via Ollama, with `gemma4:latest` (8B, Q4_K_M, vision-capable). The daily pipeline ingests new PubMed papers, extracts findings, refines hypotheses, and writes back to the knowledge base. One codebase, two backends via the `HD_LLM_BACKEND` env switch: `ollama` on the Jetson, `aistudio` on Vercel.

## Architecture

```
              +-------------------+        +-----------------------+
              |   Jetson AGX Orin |        |  Vercel Serverless    |
              |  Ollama gemma4    |        |  api/chat.py          |
              |  HD_LLM_BACKEND=  |        |  HD_LLM_BACKEND=      |
              |  ollama           |        |  aistudio             |
              +---------+---------+        +-----------+-----------+
                        |                              |
                        v                              v
              +---------------------+        +-----------------------+
              | Daily agent pipeline|        |  Gemma 4 via Google   |
              | paper_analyzer.py   |        |  AI Studio Gemini API |
              | hypothesis_refiner  |        |  gemma-4-31b-it       |
              | target_tracker      |        +-----------+-----------+
              +---------+-----------+                    |
                        |                                |
                        v                                v
              +-----------------------------------------------+
              |   Knowledge Base  (data/*.json + Upstash)     |
              |   PubMed full-text chunks, hypotheses,        |
              |   target rankings, trial data                 |
              +-----------------------------+-----------------+
                                            |
                                            v
                                  +-------------------+
                                  |   User browser    |
                                  |   chat.html       |
                                  +-------------------+

  Reproducible side-channel:  notebooks/gemma4_hd_research.ipynb
                              runs the same src/llm.py on Kaggle GPU
```

## The moat — chat with the actual research

Most HD resources show titles, abstracts, or journalist summaries. We pull full-text papers from PubMed Central, chunk them by section, and let Gemma 4 plus the tools answer against the actual Methods, Results, and Discussion text. The chatbot cites specific paper sections, not just titles.

This compounds. Every daily pipeline run adds more full-text chunks, more figure-derived findings, more hypotheses. The chatbot gets sharper as the corpus grows. Nobody else is doing this for Huntington's Disease.

## What worked

- The agentic loop reliably picks the right tool in local smoke tests: clinical-trial questions route to `get_clinical_trials`, target lookups to `get_target_info`, research questions to `search_papers`, and Gemma 4 chains them when needed.
- Multimodal vision works against Ollama `gemma4:latest` on Jetson and against `gemma-4-31b-it` on AI Studio. Same `ask_vision()` call site.
- The medical-advice guardrail now catches both text patterns and uploaded personal medical images. Gemma 4 is the classifier for the image side.
- The daily pipeline already runs in production via GitHub Actions, refreshing the knowledge base every 24 hours.
- The Sarvam AI translation wrapper for 22 Indian languages survived the rewrite unchanged — Gemma 4 sees English, the user gets their language back.
- Vercel serverless cold-starts on the new code are dominated by JSON loads, not model spin-up, because Gemma 4 lives behind AI Studio.

## What didn't / wasn't shipped

Cut from scope, in order:

- **Molecular structure reading for the repurposing scanner (spec 2c).** Gemma 4 reading 2D chemical structures reliably is unproven in the time available. Better to write this up honestly than ship a half-broken feature.
- **Pipeline function calling (spec 3b).** The daily agents still call `ask_json()` for structured extraction. Native function calling would be more robust, but it is invisible in a demo. We prioritized the chatbot, where users actually see it.
- **Cloudflare-tunnel "edge-only chatbot" (spec option A).** Vercel cannot reach a LAN IP, and we wanted the live site to run Gemma 4 in production for judges, not behind a fragile tunnel. The pipeline is genuinely edge; the live chatbot is honestly hosted.

## Not clinical, on purpose

HD Research Hub is a research-and-education tool with a hard medical-redirect guardrail. We are data scientists, not doctors. Every output disclaims. The system prompt refuses to give personal medical advice, recommend medications, predict prognosis, or interpret personal medical imagery. It redirects to HDSA, HDBuzz, HDYO, and the user's own neurologist.

Other entries in the competition aim at clinical decision support. We deliberately stay one step back from the clinic. For a "for good" hackathon, the safer story is the truer one.

## Reproducibility

`notebooks/gemma4_hd_research.ipynb` runs the exact same `src/llm.py` top-to-bottom on a fresh Kaggle GPU session. It demonstrates both multimodal figure reading and native function calling against the shipped `data/` snapshot. Apache 2.0 licensed.

## Stack

- **Vercel** — serverless Python for the live chatbot
- **Google AI Studio / Gemini API** — `gemma-4-31b-it` for hosted inference
- **Ollama on Jetson AGX Orin** — `gemma4:latest` (8B Q4_K_M) for edge inference
- **Upstash Vector** — embeddings for `search_papers`
- **Sarvam AI** — 22 Indian languages
- **GitHub Actions** — daily pipeline at 08:00 UTC
- **PubMed, ClinicalTrials.gov, HDBuzz, Open Targets** — all free public APIs

## Links

- Live demo: [hd-research-agent.vercel.app](https://hd-research-agent.vercel.app)
- Chatbot: [hd-research-agent.vercel.app/chat.html](https://hd-research-agent.vercel.app/chat.html)
- GitHub: [github.com/jravinder/hd-research-agent](https://github.com/jravinder/hd-research-agent)
- Notebook: `notebooks/gemma4_hd_research.ipynb`
- Video: `media/demo.mp4`
- Spec: `docs/superpowers/specs/2026-05-14-gemma4-hackathon-design.md`
- Plan: `docs/superpowers/plans/2026-05-15-gemma4-hackathon.md`

---

*Gemma is a trademark of Google LLC. This project is AI-generated research analysis, not medical advice.*
