# Experiment #4: Somatic CAG Expansion Drug Screen

**Date:** April 07, 2026
**Model:** gemma4:latest (local, Apple M2)
**Papers discovered:** 123
**Papers relevant (filtered):** 92
**Papers analyzed:** 75 (55 full text, 20 abstract)
**Total characters read:** 4,976,515
**Targets screened:** MSH3, FAN1, PMS1, MLH1, LIG1

## Why Somatic Expansion?

GWAS studies identified DNA repair genes as the strongest modifiers of HD onset.
Natural genetic variants in these genes delay onset by 6-8 years. The somatic
expansion pathway (MutSbeta -> MutLgamma -> Pol-delta -> LIG1, opposed by FAN1)
is now the most active frontier in HD drug development, with multiple companies
(LoQus23, Harness, Skyhawk, Rgenta) developing drugs against these targets.

## Top Findings


## Target Rankings

| Target | Papers | Druggability | Most Advanced Approach | Key Challenge |
|--------|--------|-------------|----------------------|---------------|

## Drug Candidates Ranked

## Combination Hypotheses


## Novel Hypotheses


## Research Gaps


## Methodology

- PubMed searched with 8 targeted queries (2024-2026)
- Full text from PMC where available, abstracts as fallback
- Each paper screened by gemma4:latest with somatic expansion-specific prompts
- Cross-paper synthesis ranks drug candidates by evidence and clinical readiness
- All code: github.com/jravinder/hd-research-agent

## Limitations

- Only open-access papers analyzed (paywalled papers excluded)
- Single model, single run (different temperature/prompt could change results)
- Not reviewed by HD domain experts or medicinal chemists
- Drug candidate rankings reflect AI assessment, not clinical validation
- Abstract-only papers contribute lower-confidence results

This is AI-generated research analysis, not medical advice.
For HD support, visit hdsa.org.
