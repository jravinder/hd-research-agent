# Gemma 4 Good Hackathon Submission — Design Spec

**Date:** 2026-05-14
**Deadline:** 2026-05-18, 23:59 UTC (4 days)
**Competition:** [The Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon) — Kaggle + Google DeepMind, $200K prize pool, health/education/climate tracks. Judged on impact, technical execution, clear use-case communication.

## Goal

Enter HD Research Hub into the **health** track by making Gemma 4 the platform's core model and showcasing its two headline capabilities the competition explicitly calls out: **multimodal understanding** and **native function calling**.

## Scope Decision

Go big: ship **both** multimodal and native function calling. Architecture follows hackathon options **B + C**:

- **B (hybrid hosted):** the live chatbot runs Gemma 4 via a hosted endpoint; the offline pipeline runs Gemma 4 on the Jetson.
- **C (notebook-centric):** a self-contained Kaggle notebook is the reproducible centerpiece judges run themselves.

There is **no Cloudflare tunnel** (that was option A, not chosen).

## Verified Technical Facts (checked 2026-05-14)

- **Gemma 4 is genuinely multimodal + agentic.** Vision on all sizes (chart comprehension, OCR, document parsing), native function calling, Apache 2.0. Sizes: E2B/E4B (edge), 31B dense, 26B-A4B MoE.
- **Jetson is ready.** `192.168.4.124:11434` is running `gemma4:latest` (8B, Q4_K_M, vision-capable) now. The local Mac has `gemma4:latest`, `gemma4:e4b`, and `nomic-embed-text`. No new model pull needed.
- **Hosted path exists.** Gemma 4 on the Gemini API / AI Studio as `gemma-4-31b-it` and `gemma-4-26b-a4b-it`, `generateContent` endpoint, API key from AI Studio.

### Wrinkles to design around

1. **Ollama tool-calling bug:** Gemma 4 tool calls break over Ollama's *OpenAI-compatible* API with *streaming*. Mitigation: stay on Ollama's native `/api/chat`, non-streaming — which `llm.py` already does. Do not migrate to the OpenAI-compat path.
2. **Gemma 4 function calling via the Gemini API** may need explicit output parsing (a tool-use protocol, not always the clean structured `functionCall` part Gemini-native returns). Use the `gemini-api-dev` skill at implementation time to get this exact.

## Competitive Landscape (checked 2026-05-14)

Reviewed the public code gallery (~20 visible notebooks). Findings that shaped this spec:

- **HD is an open lane.** No Huntington's Disease submission exists. The only neurodegenerative entry is "yourOwn" (an Alzheimer's *companion* app). Nobody is doing a research-acceleration platform — entries are overwhelmingly end-user assistants, chatbots, and image detectors.
- **The Kaggle notebook is the primary artifact, and it is a rich narrative.** The top entry (FarmWise AI, 33 votes, Bronze) is a notebook with 20 interactive demo cells, a table of contents, a "Why It Wins" section, "Technical Architecture", "Gemma 4 Usage Statement", "Competition Readiness Checklist", "System Evaluation", "Limitations", and "Gemma Trademark Attribution" — runs on Kaggle T4 x2, Apache 2.0 licensed. Other strong entries (CodecareGemma4, 11 votes) follow the same shape: Problem → Why Gemma 4 → Dataset → Prompt Design → Implementation → Demo Cases → Evaluation → Limitations → Future Work → Submission Readiness Check.
- **Multimodal image-classification demos resonate.** FarmWise's "disease detection from leaf images" is structurally identical to our "extract findings from paper figures" — confirms 2a/2b are on-target.
- **The edge/offline story is valued.** FarmWise leads with "100% Offline / On-Device Deployment." Our pipeline is genuinely edge (Jetson); the chatbot is hosted. The notebook and write-up should foreground the Jetson edge inference rather than bury it.
- **"Not clinical" is a positioning asset.** A competing entry, "DocAgent," is a clinical decision support system. Our explicit non-clinical, research-and-education stance plus the medical-redirect guardrail is a cleaner, safer story for a "for good" hackathon — lean into it in the write-up.
- **Fine-tuning with Unsloth** is a side theme (separate $10K Unsloth prize). We are not fine-tuning. That is fine and out of scope; noted only so it is a deliberate choice, not an oversight.

## Architecture & Inference Topology

| Surface | Where Gemma 4 runs | Model |
|---|---|---|
| Daily agent pipeline (paper figures, molecular structures, hypothesis extraction) | Jetson AGX Orin via Ollama | `gemma4:latest` |
| Live chatbot (agentic + image upload) | Hosted — Google AI Studio / Gemini API | `gemma-4-31b-it` (primary), `gemma-4-26b-a4b-it` (throughput fallback) |
| Kaggle notebook (reproducible centerpiece) | Kaggle GPU | `google/gemma-4` (or AI Studio key as secret) |

### Code structure

`src/llm.py` becomes the single Gemma 4 module with three entry points:

- `ask(prompt, system, ...)` — text generation
- `ask_vision(prompt, images, system, ...)` — image + text
- `ask_with_tools(prompt, tools, system, ...)` — native function calling, abstracting over Ollama tool-calling (Jetson) and AI Studio function-calling (hosted)

An environment switch `HD_LLM_BACKEND=ollama|aistudio` selects the backend so the *same* code runs in the pipeline (Jetson), the chatbot API (hosted), and the Kaggle notebook. The pipeline sets `ollama`; `api/chat.py` sets `aistudio`.

### Deleted

The NVIDIA NIM code path in `api/chat.py` (`NIM_API_KEY`, `NIM_URL`, `NIM_MODEL`, `call_nim`).

### Honesty note

CLAUDE.md currently claims "zero cloud AI dependencies." That was never true (the deployed chatbot used NVIDIA NIM, a cloud API) and will not be true after this (AI Studio is cloud). CLAUDE.md, README, and the write-up must state what is actually true: **edge inference for the research pipeline, hosted Gemma 4 for the interactive product.**

## Feature 1: Multimodal (Gemma 4 vision)

Three surfaces, all routed through `ask_vision()`.

### 2a. Paper figure reading — pipeline *(feeds the moat)*

`paper_analyzer.py` already pulls full text from PMC open-access papers. Add: download each paper's figure images (PMC OA service), and for each figure ask Gemma 4 to *"describe what this shows and extract quantitative findings — numbers, p-values, effect sizes, sample sizes."* The extracted finding becomes a new knowledge-base chunk tagged `section: figure-N`. Result: the chatbot can cite findings that exist only in a chart, never in the abstract.

### 2b. Chatbot image upload *(demo star)*

`chat.html` gets an image upload button. User submits a figure/chart/diagram → `api/chat.py` → `ask_vision()` on the hosted endpoint → grounded, cited answer.

**New guardrail required:** a vision check that catches personal medical images (MRI, brain scans, genetic reports) and fires the existing `MEDICAL_REDIRECT`. The current `MEDICAL_ADVICE_PATTERNS` guardrail is text-only; image upload opens a clinical-input door the project's rules forbid.

### 2c. Molecular structure reading — repurposing scanner *(honest stretch)*

For each candidate drug, fetch its 2D structure PNG from PubChem and ask Gemma 4 to note functional groups + blood-brain-barrier-relevant properties, appended to each hypothesis. **Lowest priority** — Gemma 4 reading chemical structures reliably is unproven. In 4 days this should be a clean "we tried this, here is what worked and didn't" write-up note rather than a half-broken feature.

**Priority within multimodal:** 2b is must-ship (Tier 1), 2a is strong and high-priority (Tier 2), 2c is cut-first (Tier 3). See Priority Tiers below.

## Feature 2: Native function calling (Gemma 4 tools)

### 3a. Agentic chatbot *(core — the headline demo)*

Today `api/chat.py` does *fixed* RAG: it always runs the same `build_context()` then one LLM call. Make it **agentic** — Gemma 4 gets real tools and decides which to call:

- `search_papers(query)` — semantic search over KB full-text chunks (including figure-derived chunks from 2a)
- `get_clinical_trials(status?)` — live HD trial data
- `get_target_info(gene)` — target rankings / Open Targets data
- `get_experiment_findings(n?)` — AI-generated hypotheses + findings
- `get_latest_papers(days?)` — recent corpus papers

Flow: user message → Gemma 4 with tool schemas → model emits tool call(s) → we execute → feed results back → model composes the cited answer. The response **surfaces which tools were called** — transparency, matching CLAUDE.md's chain-of-thought philosophy. The medical guardrail and Sarvam translation wrap around this unchanged.

### 3b. Pipeline function calling *(stretch)*

The daily agents (`paper_analyzer`, `hypothesis_refiner`, `target_tracker`) currently call `ask_json()`, which hand-parses JSON from a markdown fence — fragile. Swap to `ask_with_tools()` for structured extraction through the native schema. More robust, but invisible in a demo video — so it is stretch.

## Deliverable: Kaggle Notebook

A single self-contained notebook `gemma4_hd_research.ipynb` judges run top-to-bottom on Kaggle's GPU (target: T4 x2, under ~10 min). This is the **primary judged artifact** — the competitive landscape shows the notebook is where entries win or lose, so it is structured as a rich narrative, not a bare script. It satisfies "public code + reproducibility" *and* proves the two headline features work without the Jetson or the live site.

**Structure** (mirrors the shape of the top-voted entries):

1. **Title + the problem** — HD research is slow; what an AI research-acceleration platform changes. Lead with the question.
2. **Why Gemma 4** — multimodal + native function calling are exactly what this needs; edge-deployable.
3. **Setup** — install pinned deps, load Gemma 4 (Kaggle `google/gemma-4` model or AI Studio key as secret).
4. **Multimodal demo** — pull 2–3 real HD papers from PMC with figures, run `ask_vision()` live, show Gemma 4 extracting quantitative findings from a survival curve / western blot.
5. **Function calling demo** — define the 5 chatbot tools against the shipped `data/` JSON files, ask 2–3 HD research questions, show Gemma 4 selecting and calling tools and composing a cited answer.
6. **The compounding-KB point** — show a figure-derived chunk entering the knowledge base and then being retrieved by the chatbot. This is the moat.
7. **Edge story** — show the same `src/llm.py` running against the Jetson; foreground that the research pipeline runs on a desktop edge device.
8. **Evaluation** — a small honest evaluation of figure-extraction and tool-selection quality on a handful of cases.
9. **Limitations & future work** — what Gemma 4 nailed, what it missed (especially molecular structures if 2c made the cut); not clinical; open-access papers only.
10. **Gemma 4 usage statement + trademark attribution + Apache 2.0 license** — competition housekeeping the strong entries all include.

The notebook imports the *same* `src/llm.py` the live site uses — not a reimplementation — so it proves the actual production code. Ships with pinned deps and the `data/` snapshot committed so it runs identically months later.

## Submission Packaging

Hackathon requires: working demo + public code repo + technical write-up + short video.

| Deliverable | Owner | What |
|---|---|---|
| Working demo | Claude (code) | Live site: agentic chatbot + image upload, running Gemma 4 |
| Public repo | exists | Cleaned up, honest CLAUDE.md/README, pinned deps |
| Kaggle notebook | Claude | The reproducible centerpiece (above) |
| Technical write-up | Claude (draft) | How Gemma 4 is used, what worked, what didn't |
| Short video | **User** | Claude writes the demo script + shot list; user records and narrates |
| AI Studio API key | **User** | User creates it; Claude wires it in |

### Positioning (for the write-up and notebook narrative)

- **Open lane:** the only HD entry, and the only research-acceleration platform in a field of end-user assistants. Say so plainly.
- **Not clinical, on purpose:** a research-and-education tool with a hard medical-redirect guardrail — contrast with clinical-decision-support entries. This is a safety strength for a "for good" hackathon.
- **The moat:** chat with the actual full-text research corpus — now including findings Gemma 4 read out of figures — not journalist summaries. Every agent run compounds the knowledge base.
- **Edge:** the research pipeline runs on a Jetson AGX Orin on a desk. Foreground it; do not bury it.

## 4-Day Sequence

Today May 14 → deadline May 18 23:59 UTC.

- **Day 1** — Unify `src/llm.py` (`ask` / `ask_vision` / `ask_with_tools` + backend switch). Verification gate: confirm Ollama `gemma4` accepts images via `/api/chat`; confirm AI Studio key works with `gemma-4-31b-it` + function calling. *(User: create the AI Studio key.)*
- **Day 2** — Core: rewrite `api/chat.py` agentic with 5 tools, delete NIM (3a). Chatbot image upload + vision guardrail + `chat.html` UI (2b). Pipeline figure reading in `paper_analyzer.py` (2a).
- **Day 3** — Kaggle notebook. Stretch if time: 3b then 2c. Run pipeline once to populate figure-derived KB chunks, deploy.
- **Day 4** — Technical write-up, CLAUDE.md/README honesty pass, demo script for the video, final deploy verification, user submits on Kaggle.

## Priority Tiers

If time runs short, cut from the bottom:

1. **Must ship:** unified `llm.py`, agentic chatbot (3a), image upload + guardrail (2b), Kaggle notebook, write-up, video
2. **Strong:** pipeline figure reading (2a)
3. **Cut first, in this order:** molecular structures (2c) → pipeline function calling (3b)

## Out of Scope

- Cloudflare tunnel / making the LAN Jetson publicly reachable (option A, not chosen)
- Audio multimodal (Gemma 4 supports it; not relevant to HD research surfaces here)
- Any new data source or new experiment
- Unrelated refactoring of the existing site or pipeline beyond the `llm.py` unification

## Success Criteria

- Live deployed chatbot answers an HD research question by calling at least one Gemma 4 tool and citing a source, with the tool call surfaced to the user.
- Live deployed chatbot accepts an uploaded research figure and answers a grounded question about it; uploading a personal medical image triggers the redirect guardrail.
- The daily pipeline produces at least one figure-derived knowledge-base chunk from a real PMC paper.
- The Kaggle notebook runs top-to-bottom on a fresh Kaggle session and demonstrates both multimodal and function calling.
- CLAUDE.md, README, and the write-up accurately describe the inference topology (no false "zero cloud" claim).
- Submission (demo URL + repo + write-up + video) filed on Kaggle before 2026-05-18 23:59 UTC.
