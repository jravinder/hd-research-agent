# Gemma 4 Good Hackathon — 1-Hour Execution Plan

> **For agentic workers:** Use superpowers:executing-plans (inline) — the 1-hour budget rules out subagent overhead. Steps use `- [ ]` checkboxes.

**Goal:** Ship HD Research Hub as a Gemma 4 Good Hackathon submission — agentic chatbot with native function calling + multimodal image upload, plus a reproducible Kaggle notebook, write-up, and demo video — by Kaggle deadline 2026-05-18 23:59 UTC.

**Architecture:** Hosted Gemma 4 via Google AI Studio (`gemma-4-31b-it`) for the live chatbot; Jetson Ollama Gemma 4 for the offline pipeline; a self-contained Kaggle notebook as the reproducible centerpiece. One `src/llm.py` abstracts both backends. Spec: `docs/superpowers/specs/2026-05-14-gemma4-hackathon-design.md`.

**Tech stack:** Python (Vercel serverless), `google-genai` SDK, Ollama `/api/chat`, vanilla HTML/JS chat UI, Jupyter notebook for Kaggle, Playwright for the demo video.

**Adapted from skill defaults:** the writing-plans skill recommends full TDD with bite-sized 2-5 min tasks. The user has explicitly constrained this to ~1 hour, so this plan trades pytest TDD for pragmatic live-endpoint verification. Smoke tests where they pay off; not where they would burn the budget.

**Tier discipline:** if anything slips, cut Block 2 stretch cells, then Block 3 video to a static GIF, then 2c/3b entirely. Live agentic chatbot + Kaggle notebook + write-up are the floor.

---

## Block 0: User-blocked items (0-5 min, parallel with mine)

- [ ] **User:** create Gemini API key at https://aistudio.google.com/apikey → paste back into chat
- [ ] **User (optional):** grab kaggle.json from kaggle.com/settings → place at `~/.kaggle/kaggle.json` so I can auto-upload the notebook

## Block 1: Agentic Gemma 4 chatbot, deployed (5-30 min)

**Files to create/modify:**
- Modify: `src/llm.py` (new entry points: `ask_vision`, `ask_with_tools`, backend switch)
- Create: `src/chat_tools.py` (5 tool functions + their JSON schemas)
- Modify: `api/chat.py` (rewrite agentic, delete NIM path)
- Modify: `chat.html` (image upload button + tool-call surfacing)
- Modify: `requirements.txt` (add `google-genai`)

### Task 1.1 — Refactor `src/llm.py`

Add `ask_vision()` and `ask_with_tools()` with backend switch `HD_LLM_BACKEND=ollama|aistudio`. Keep `ask()` and `ask_json()` backwards-compatible (existing pipeline depends on them). For aistudio, use the `google-genai` SDK; for ollama, hit `/api/chat` with `images` field (vision) and `tools` field (tool calling). Model: `gemma-4-31b-it` on aistudio; `gemma4:latest` on ollama.

- [ ] Write the file with all four entry points
- [ ] Verify: `HD_LLM_BACKEND=ollama python3 -c "from src.llm import ask; print(ask('say hi in 3 words'))"`
- [ ] Verify: `HD_LLM_BACKEND=aistudio GEMINI_API_KEY=<key> python3 -c "from src.llm import ask; print(ask('say hi in 3 words'))"`

### Task 1.2 — `src/chat_tools.py` with 5 tools

Each tool: a Python function operating on the `data/*.json` snapshots already in the repo, plus a JSON schema in google-genai tool format.

- `search_papers(query: str) -> list[Chunk]` — Upstash semantic search (existing) wrapped as a tool
- `get_clinical_trials(status: str = "recruiting") -> list[Trial]` — reads `data/data.json`
- `get_target_info(gene: str) -> Target` — reads `data/target_rankings.json`
- `get_experiment_findings(n: int = 5) -> list[Finding]` — reads `data/experiment_001_results.json` + later experiment hypotheses
- `get_latest_papers(days: int = 30) -> list[Paper]` — reads `data/corpus.json`, filters by date

- [ ] Write `src/chat_tools.py` with both the dispatch table and the schema list
- [ ] Verify: `python3 -c "from src.chat_tools import TOOLS, dispatch; print([t['name'] for t in TOOLS]); print(dispatch('get_clinical_trials', {}))"`

### Task 1.3 — Rewrite `api/chat.py` agentic

Flow: user message → guardrail check (existing text patterns + new image guardrail) → `ask_with_tools()` loop (model emits tool call → we execute → feed result → up to 3 turns) → format final response with `tools_used` field surfaced to UI. Delete `NIM_API_KEY`, `NIM_URL`, `NIM_MODEL`, `call_nim`. Keep Sarvam translation + medical guardrail wrappers exactly as-is.

- [ ] Rewrite the file
- [ ] Add image upload handling: accept `image_b64` field, run image guardrail if present, pass image to `ask_vision()` via the tool loop
- [ ] Local smoke test: POST a research question, get back JSON with `response`, `sources`, `tools_used`
- [ ] Local smoke test: POST a medical-advice question, get redirect

### Task 1.4 — Image guardrail (`src/chat_tools.py::is_personal_medical_image`)

A Gemma 4 vision call that classifies an uploaded image as `personal_medical | research_figure | other`. If `personal_medical`, fire `MEDICAL_REDIRECT`.

- [ ] Add the function
- [ ] Smoke: feed a known research-figure image → not flagged; feed a brain MRI screenshot from the web → flagged

### Task 1.5 — `chat.html` UI

- Add a file-input button next to the message input (camera/image icon)
- On submit with image: base64-encode, send as `image_b64`
- Render `tools_used` as a small "Tools used: search_papers, get_clinical_trials" badge above the answer

- [ ] Edit the file
- [ ] Eyeball locally with `python3 -m http.server 8710` and visit `localhost:8710/chat.html`

### Task 1.6 — Deps + env

- [ ] `requirements.txt`: add `google-genai>=0.3.0`
- [ ] `vercel env add GEMINI_API_KEY production` (pipe in the user's key)
- [ ] Commit, push branch `hackathon/gemma4-good`, open PR, merge to main
- [ ] Vercel auto-deploys; verify with `curl -sI https://hd-research-agent.vercel.app/` then a real chat POST to the live API

## Block 2: Kaggle notebook (30-45 min)

**Files:** `notebooks/gemma4_hd_research.ipynb`

Self-contained narrative notebook mirroring the winning shape from the competitive landscape: TOC, Why Gemma 4, Setup, Multimodal demo, Function calling demo, Edge story, Evaluation, Limitations, Attribution.

Inference inside the notebook uses Kaggle's `google/gemma-4` model directly (no API key in Kaggle env), but `src/llm.py` is imported so the same code that runs the live site is what runs in the notebook.

- [ ] Cell 1 (markdown) — Title, the question, the open lane (no HD entries in field)
- [ ] Cell 2 (markdown) — Why Gemma 4: multimodal + native function calling + edge-deployable + Apache 2.0
- [ ] Cell 3 (code) — `pip install -r requirements.txt`, clone repo for `data/` + `src/llm.py`, configure backend
- [ ] Cell 4 (code) — Multimodal demo: pull 2 real PMC HD-paper figures, run `ask_vision()`, show extracted quantitative findings
- [ ] Cell 5 (code) — Function calling demo: define the 5 tools, ask 3 HD research questions, show tool selection + cited answer
- [ ] Cell 6 (markdown) — The compounding-KB point with a worked example
- [ ] Cell 7 (code) — Edge story: same `src/llm.py` running against a remote Ollama-compatible endpoint (or simulated locally), note the Jetson production reality
- [ ] Cell 8 (code) — Small honest evaluation: 5-case figure-extraction sanity table + 5-case tool-selection table
- [ ] Cell 9 (markdown) — Limitations (open-access only, 2c not shipped, etc.), Gemma 4 usage statement, trademark attribution, Apache 2.0 license note
- [ ] Verify it runs top-to-bottom locally with `jupyter nbconvert --to notebook --execute notebooks/gemma4_hd_research.ipynb`

## Block 3: Write-up + demo video + submission packaging (45-58 min)

### Task 3.1 — Technical write-up (`docs/HACKATHON.md`)

Sections: problem, what we built, how Gemma 4 is used (multimodal + function calling + edge), the compounding KB moat, what worked / what didn't, links to repo + notebook + live demo + video.

- [ ] Write the file

### Task 3.2 — Honesty pass on `CLAUDE.md` + `README.md`

Remove the "zero cloud AI dependencies" line; replace with the truthful "edge inference for the research pipeline, hosted Gemma 4 for the interactive product."

- [ ] Edit both files

### Task 3.3 — Demo video (Playwright screen capture)

A silent screen recording of: load `chat.html` → ask a research question → see tool-calls badge + cited answer → upload a research figure → see vision answer → upload a "medical image" → see guardrail redirect. ~60s. Save as `media/demo.mp4`.

- [ ] Write a Playwright script that records the walkthrough
- [ ] Save the video; if user wants narration they can re-record over it

### Task 3.4 — Submission package (`SUBMISSION.md`)

A single file with: repo link, live demo URL, notebook link (once user uploads), video link, write-up link.

- [ ] Write the file

## Block 4: Push & verify (58-60 min)

- [ ] Final commit on branch, push, merge to main
- [ ] Verify `https://hd-research-agent.vercel.app/chat.html` still works with the agentic + image upload changes
- [ ] Tell user the 3 things they need to click: upload notebook to Kaggle competition, link the video, hit Submit
- [ ] (Optional) Telegram notification when finished if user has opted into notifications

## Cut order if time slips

1. Block 3.3 video → static GIF or skip (user records)
2. Block 2 evaluation cell (8) → trim
3. Block 1.4 image guardrail vision call → keep text-only redirect for now, flag in write-up
4. Block 1 stretch: surfacing tool-calls in UI (badge) — okay to ship without if needed
