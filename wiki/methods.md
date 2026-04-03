# Methods

How we run experiments and what we've learned about doing it well.

## Experiment Pipeline

1. Pull papers from PubMed (E-utilities API, free)
2. Fetch full text from PubMed Central (open access only)
3. Feed entire paper to LLM (no chunking for experiments)
4. Extract: targets, compounds, findings, repurposing signals (JSON schema)
5. Cross-paper synthesis: patterns, contradictions, gaps
6. Generate hypotheses, score, publish

## What Works

- **Full text beats abstracts.** EXP-002 found 3 targets invisible from abstracts (cGAS, LIG1, DNJC7).
- **Structured JSON extraction** forces the model to be specific. Free-form summaries are vague.
- **Publishing failures** builds credibility. Riluzole was wrong. We said so.
- **Git as memory.** Every commit is a checkpoint. results.tsv equivalent is our data/*.json files.
- **Pre-commit guardrails** catch real issues before they ship.

## What Doesn't Work

- **27B models on M2 Mac** timeout on full papers. Need GPU (Jetson) or API credits.
- **Reddit keeps timing out** in last30days. Blind spot on patient community.
- **Upstash dimension mismatch** cost us 3 index recreations. Match embedding model to index dim from the start.
- **Google Translate CSS** hides itself. Need selective .skiptranslate overrides.

## Model Comparison (so far)

| Model | Size | Context | Hardware | Full Paper Speed | Quality |
|-------|------|---------|----------|-----------------|---------|
| Llama 3.1 8B | 8B | 64K | Jetson | ~2 min/paper | Good for extraction, misses some nuance |
| Qwen 3.5 27B | 27B | 128K | Mac M2 | Timeout (>30 min) | Could not complete |
| Gemma 4 | 26B | 256K | Mac M2 | Testing | TBD |

## Reproducibility

Every experiment can be reproduced:
```
git clone https://github.com/jravinder/hd-research-agent
pip install -r requirements.txt
python src/run_experiment.py          # EXP-001
python src/run_experiment_2.py        # EXP-002
python src/run_experiment_3.py        # EXP-003
```

Requires: Python 3.10+, Ollama with a model pulled.
