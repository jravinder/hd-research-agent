# Drug Repurposing Hypotheses

All AI-generated. None reviewed by domain experts. None experimentally validated. Starting points for researchers to evaluate.

## Active Hypotheses

| Drug | Target | Score | Source | Status | Evidence Trend |
|------|--------|-------|--------|--------|----------------|
| cGAS inhibitor (class) | cGAS-STING / neuroinflammation | 90/100 | EXP-002 | Exploring | New (1 check) |
| Tocilizumab | IL-6 / neuroinflammation | 80/100 | EXP-001 | Exploring | Stable (1 check) |
| LIG1 K845N modulator | DNA repair / somatic expansion | 80/100 | EXP-002 | Exploring | New (1 check) |
| Metformin | mTOR / AMPK / autophagy | 72/100 | EXP-001 | Exploring | Stable (1 check) |
| CRISPR mito delivery | Mitochondrial biogenesis | 70/100 | EXP-002 | Exploring | New (1 check) |
| Rapamycin | mTOR | 68/100 | EXP-001 | Exploring | Stable (1 check) |
| Riluzole | Glutamate excitotoxicity | 60/100 | EXP-001 | Already tested | Known (modest results in trials) |
| Lithium | TDP-43 / GSK-3B | 55/100 | EXP-001 | Exploring | Stable (1 check) |

## How Scoring Works

- LLM generates a hypothesis, then self-rates its confidence 0-100
- Score reflects the model's assessment of mechanistic rationale, not clinical probability
- 80+ = interesting starting point worth literature deep-dive
- 60-79 = plausible but needs more evidence
- <60 = speculative or already known

## What Changed Between Experiments

**EXP-001 (abstracts):** Generated broad hypotheses. Tocilizumab and Metformin. Also suggested Riluzole without knowing it was already tested.

**EXP-002 (full text):** Generated more specific hypotheses. cGAS pathway and LIG1 variant only visible from reading Methods and Discussion sections. Higher specificity, fewer hallucinations.

## Refiner History

Run #1 (2026-03-29): Searched PubMed for each hypothesis + HD. No new papers found for any. Scores unchanged. These combinations are underexplored.
