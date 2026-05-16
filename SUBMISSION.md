# HD Research Hub — Gemma 4 Good Hackathon Submission

Single page with every artifact a judge (or the user filing the Kaggle form) needs.

## TL;DR

Agentic Huntington's Disease research assistant powered by Google Gemma 4 — native function calling over a full-text PubMed knowledge base, multimodal vision for paper figures, and a daily edge-inference pipeline on a Jetson AGX Orin. The only HD entry in the competition.

## Artifacts

| Artifact | Link |
|---|---|
| Live demo (dashboard) | https://hd-research-agent.vercel.app |
| Live chatbot (Gemma 4 agentic + image upload) | https://hd-research-agent.vercel.app/chat.html |
| GitHub repo | https://github.com/jravinder/hd-research-agent |
| Kaggle notebook (reproducible) | `notebooks/gemma4_hd_research.ipynb` — to be uploaded to Kaggle |
| Technical write-up | [`docs/HACKATHON.md`](docs/HACKATHON.md) |
| Video walkthrough | [`media/demo.mp4`](media/demo.mp4) — silent screen capture of the live agentic chatbot demonstrating function calling, multimodal figure upload, and the medical-advice guardrail |
| Design spec | [`docs/superpowers/specs/2026-05-14-gemma4-hackathon-design.md`](docs/superpowers/specs/2026-05-14-gemma4-hackathon-design.md) |
| Execution plan | [`docs/superpowers/plans/2026-05-15-gemma4-hackathon.md`](docs/superpowers/plans/2026-05-15-gemma4-hackathon.md) |

## How Gemma 4 is used (one-line each)

1. **Native function calling** in the live chatbot — 5 tools over the HD research KB, tool calls surfaced to the UI.
2. **Multimodal vision** — users upload paper figures and Gemma 4 reads the chart; a vision guardrail catches personal medical images.
3. **Edge inference** — same `src/llm.py` runs on a Jetson AGX Orin via Ollama for the daily pipeline. Backend switched by `HD_LLM_BACKEND`.

## What you do next (3 short bullets)

1. **Paste your `GEMINI_API_KEY`** into Vercel (`vercel env add GEMINI_API_KEY production`) so the live chatbot can reach Gemma 4 via AI Studio.
2. **Upload the notebook to Kaggle** — open `notebooks/gemma4_hd_research.ipynb`, push to a new Kaggle notebook attached to the Gemma 4 Good Hackathon competition, Apache 2.0 license.
3. **Hit Submit** on the Kaggle competition page with the live demo URL, the notebook URL, the GitHub repo URL, and the video link.

---

*Gemma is a trademark of Google LLC. This project is AI-generated research analysis, not medical advice.*
