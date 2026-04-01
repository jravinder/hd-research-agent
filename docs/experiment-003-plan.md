# Experiment #3: Multi-Model Deep Paper Analysis

## The Question

Does a larger, reasoning-optimized model produce meaningfully different insights from HD research papers compared to a smaller general-purpose model? And where do they agree?

## Design

**Same 16 full-text papers from Experiment #2, run through 2 models:**

| Model | Parameters | Context | Hardware | Type |
|-------|-----------|---------|----------|------|
| Llama 3.1 8B | 8B | 64K | Jetson AGX Orin | General purpose |
| Qwen 3.5 27B | 27B | 128K | Mac M2 (or Jetson via SD card) | Reasoning-optimized |

**Same prompt, same papers, same extraction schema.** Only the model changes.

## What We're Looking For

1. **Agreement** - Where both models identify the same targets, findings, and hypotheses. High-confidence signals.
2. **Divergence** - Where only the larger model finds something. Depth vs speed tradeoff.
3. **Contradictions** - Where models disagree. Which one is right?
4. **Hallucination rate** - Does the 27B model hallucinate less (or more) than 8B?
5. **Novel connections** - Does 27B find cross-paper patterns that 8B missed?
6. **Drug repurposing quality** - Are the hypotheses more specific, better-reasoned?

## Hypothesis

The 27B reasoning-distilled model will:
- Find more specific molecular targets (not just "Huntington's disease" as a target)
- Generate drug repurposing hypotheses with stronger mechanistic rationale
- Identify more cross-paper connections (because it can hold more context)
- Produce fewer hallucinations (better calibrated confidence)

## Methodology

1. Pull same 16 PMC full-text papers used in EXP-002
2. Run each through Llama 3.1 8B (Jetson) with identical prompt
3. Run each through Qwen 3.5 27B (Mac) with identical prompt
4. Both use the same JSON extraction schema
5. Compare outputs paper-by-paper
6. Run cross-paper synthesis with each model
7. Compare synthesis results
8. Publish side-by-side comparison

## Metrics

| Metric | How We Measure |
|--------|---------------|
| Target specificity | Count gene/protein names vs generic terms |
| Hypothesis quality | Specificity of mechanism + rationale length |
| Agreement rate | % of targets/findings both models identify |
| Unique insights | Findings only one model produces |
| Hallucination check | Manual spot-check of 5 claims per model against source text |
| Runtime | Wall clock time per paper |

## Infrastructure

- Llama 3.1 8B: Ollama on Jetson AGX Orin 64GB (existing)
- Qwen 3.5 27B: Ollama on Mac M2 24GB (Q4 quant, ~17GB) or Jetson via SD card
- Same run_experiment.py framework, parameterized by model
- Results saved to data/experiment_003_results.json

## Output

1. Side-by-side comparison table (paper by paper)
2. Venn diagram of targets found by each model
3. Hypothesis quality comparison
4. Published report on the website (experiment-3.html)
5. Raw data on GitHub

## Timeline

- Models: Pulling now (both machines)
- Run Llama 3.1: ~30 min (already done in EXP-002, can reuse)
- Run Qwen 3.5: ~60-90 min (larger model, slower inference)
- Analysis + report: ~1 hour
- Publish: Same day

## Why This Matters

If the 27B model produces meaningfully better hypotheses, it justifies:
- Applying for API credits (Gemini Pro, Claude) for even larger models
- Moving to production-grade inference for the chatbot
- Building a case for startup credit applications

If both models agree on the same hypotheses, those hypotheses are higher-confidence candidates worth prioritizing.

## Experiment Card (pre-filled)

| Field | Value |
|-------|-------|
| ID | EXP-003 |
| Type | Comparative / Multi-Model |
| Status | Planned |
| Models | Llama 3.1 8B vs Qwen 3.5 27B |
| Data | 16 PMC full-text papers (same as EXP-002) |
| Hardware | Jetson AGX Orin + Mac M2 MBP |
| Cost | $0 (local inference) |
| Reproducibility | `python src/run_experiment_3.py --model llama3.1:8b` then `--model qwen3.5:27b` |
