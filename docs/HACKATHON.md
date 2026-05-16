# HD Research Hub — Gemma 4 Good Hackathon Submission

**Track:** Health & Sciences ($10,000). *"Bridge the gap between humans and data. Build tools that accelerate discovery or democratize knowledge."*

**Disease:** Huntington's Disease — the only Huntington's entry in the competition.

## The question

Can AI compound the slow loop of Huntington's Disease research — paper by paper, day after day — instead of replacing it? And in the same place where researchers compound, can a person who just got an HD diagnosis (or who lives with someone who did) safely understand what the science actually says?

## Four pillars

The Health & Sciences track asks two things: *bridge humans and data*, and *democratize knowledge*. HD Research Hub does both, on the same KB, at the same URL, for four kinds of people:

### 1. Understand the disease and navigate it

Anyone — patient, caregiver, newly-diagnosed family member, curious clinician — can land on [hd-research-agent.vercel.app/chat.html](https://hd-research-agent.vercel.app/chat.html) and ask plain-language questions ("what is somatic CAG expansion?", "what trials are open?", "what's the state of HTT lowering?"). Every answer is grounded in real PubMed papers and cites the PMID inline. Available in **22 Indian languages** via Sarvam AI plus English.

When the question crosses into personal medical territory — "should I take X?", "should I get tested?", an uploaded brain scan — Gemma 4 catches it (text patterns + a vision classifier on uploads) and redirects to **HDSA, HDBuzz, HDYO, and the user's neurologist or genetic counselor**. We're a research tool, not a clinic, and the guardrail is hard.

### 2. Run the data and the papers yourself

Everything is open and reproducible. The Kaggle notebook `notebooks/gemma4_hd_research.ipynb` runs the *same* `src/llm.py` the live site uses, top-to-bottom on a fresh Kaggle GPU. It pulls real PMC HD papers, reads their figures with Gemma 4 vision, runs the same agentic chatbot, and prints the evaluation. Anyone with a Kaggle account and curiosity can re-execute the entire pipeline in under 10 minutes.

The chatbot itself lets researchers ask questions against the **actual Methods, Results, and Discussion sections** of full-text papers — not journalist summaries, not abstracts. Upload a paper figure and Gemma 4 reads it (axes, effect sizes, p-values where legible). Apache 2.0, MIT-style permissive.

### 3. Generate new hypotheses

The `src/repurposing_scanner.py` agent walks 16 HD targets, asks Gemma 4 to nominate drug-repurposing candidates with rationales, scores them, and publishes the result to `data/experiment_*_results.json`. The autoresearch loop in `src/autoresearch.py` runs the same loop overnight on the Jetson — Karpathy-style, 100 runs better than 1 perfect plan. Five experiments have shipped so far (Experiments #1-#5), each with its own report on the live site, each flagged honestly with what worked and what didn't.

The chatbot exposes those hypotheses via `get_experiment_findings`. Anyone can ask "what's the top drug-repurposing hypothesis and which target?" and Gemma 4 picks the tool, fetches the answer, and disclaims it as an unvalidated computational idea.

### 4. Scout new data automatically

Every 24 hours, GitHub Actions runs `src/data_fetcher.py` (PubMed E-utilities, ClinicalTrials.gov REST v2, HDBuzz RSS, Open Targets GraphQL — all free public APIs) and writes fresh papers, trials, news, and target rankings into `data/`. The Jetson-side `src/agents/paper_scout.py` ingests new full-text from PubMed Central into the knowledge base. The KB grows daily. The chatbot improves daily. Nobody has to remember to refresh.

## How Gemma 4 powers each pillar

| Pillar | Gemma 4 capability used |
|---|---|
| Understand & navigate | Native function calling (5 tools) + Sarvam translation + text/image medical guardrail |
| Run the data | The shared `src/llm.py` running on Kaggle GPU; multimodal figure reading; agentic loop with the same tools |
| Generate hypotheses | Edge inference on Jetson AGX Orin (Ollama `gemma4:latest`) for the daily repurposing scanner + experiments |
| Scout new data | Edge inference on Jetson for full-text paper analysis and hypothesis refinement on each ingestion |

### The five tools the agentic chatbot picks from

- `search_papers(query)` — semantic + keyword search over the full-text knowledge base
- `get_clinical_trials(status?)` — live HD trials from ClinicalTrials.gov
- `get_target_info(gene)` — ranked HD targets table
- `get_experiment_findings(n?)` — AI-generated drug-repurposing hypotheses
- `get_latest_papers(days?)` — recently ingested corpus papers

User question → Gemma 4 emits a tool call → we execute → results feed back → up to three turns → Gemma 4 composes the cited answer. The UI surfaces which tools Gemma called for transparency.

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
       | Daily agents:       |        |  Gemma 4 via Google   |
       | paper_scout         |        |  AI Studio / Gemini   |
       | paper_analyzer      |        |  gemma-4-31b-it       |
       | repurposing_scanner |        +-----------+-----------+
       | hypothesis_refiner  |                    |
       | target_tracker      |                    |
       +---------+-----------+                    |
                 v                                v
       +---------------------------------------------------+
       |   Knowledge Base  (data/*.json + Upstash Vector)  |
       |   Full-text chunks, hypotheses, targets, trials   |
       +-----------------------------+---------------------+
                                     |
                                     v
                       +--------------------------+
                       |   User browser           |
                       |   chat.html + dashboard  |
                       |   22 Indian languages    |
                       +--------------------------+

  Reproducible: notebooks/gemma4_hd_research.ipynb
                runs the same src/llm.py on Kaggle GPU
```

One `src/llm.py` switched by `HD_LLM_BACKEND` (`ollama` for the edge pipeline, `aistudio` for the serverless chatbot). The Kaggle notebook imports the same module.

## The moat: chat with the actual research

Most HD resources show titles, abstracts, or journalist summaries. We pull full-text papers from PubMed Central, chunk them by section, and let Gemma 4 + the five tools answer against the actual Methods, Results, and Discussion text. Every pipeline run adds chunks. Every experiment adds hypotheses. The chatbot gets sharper as the corpus grows.

## What worked

- The agentic loop reliably picks the right tool: trial questions go to `get_clinical_trials`, target lookups to `get_target_info`, research questions to `search_papers`. Gemma 4 chains tools when needed.
- Multimodal vision works on both backends with the same `ask_vision()` call site — Ollama on Jetson, AI Studio for the live site.
- The medical-advice guardrail catches text patterns *and* uploaded personal medical images. Gemma 4 is the classifier for the image side.
- The daily pipeline already runs in production via GitHub Actions and has been refreshing the knowledge base every 24 hours for weeks.
- The Sarvam AI translation wrapper survived the rewrite unchanged — Gemma 4 sees English, the user gets their language back.
- The Kaggle notebook executes top-to-bottom on a fresh GPU session in under 10 minutes against the attached `google/gemma-4` model.

## What did not ship (and why)

Cut from scope, in order:

- **Molecular structure reading for the repurposing scanner (spec 2c).** Gemma 4 reading 2D chemical structures reliably is unproven in the time available. Better to write this up honestly than ship a half-broken feature.
- **Pipeline function calling (spec 3b).** The daily agents still use `ask_json()` for structured extraction. Native function calling would be more robust but it is invisible in a demo, so the chatbot won.
- **Cloudflare-tunnel "edge-only chatbot" (spec option A).** Vercel cannot reach a LAN IP, and we wanted the live site to actually run Gemma 4 in production for judges, not behind a fragile tunnel. The pipeline is genuinely edge; the live chatbot is honestly hosted.

## Not clinical, on purpose

HD Research Hub is a research-and-education tool with a hard medical-redirect guardrail. We are data scientists, not doctors. Every output disclaims. The system prompt refuses to give personal medical advice, recommend medications, predict prognosis, or interpret personal medical imagery. It redirects to HDSA, HDBuzz, HDYO, and the user's own neurologist or genetic counselor.

Other entries in the competition aim at clinical decision support. We deliberately stay one step back from the clinic. For a "for good" hackathon, the safer story is the truer one — and "democratize knowledge" means safely.

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
- Design spec: `docs/superpowers/specs/2026-05-14-gemma4-hackathon-design.md`
- Execution plan: `docs/superpowers/plans/2026-05-15-gemma4-hackathon.md`

---

*Gemma is a trademark of Google LLC. This project is AI-generated research analysis, not medical advice.*
