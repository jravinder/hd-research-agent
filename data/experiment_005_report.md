# Experiment #5: Expanded Corpus Analysis

**Date:** April 19, 2026
**Model:** gemma4:latest (local, Apple M2)
**Corpus Size:** 65 papers (Expanded from 46)
**Papers analyzed:** 25 (16 full text, 9 abstract)
**Total characters read:** 1,913,844
**Total sections read:** 381

## Overview

This experiment analyzed the expanded corpus after the Paper Scout agent discovered 19 new papers. The goal was to re-synthesize findings across a larger evidence base and see if new therapeutic signals emerged beyond the somatic expansion focus of Experiment #4.

## Key Findings

- **"Two-Track" Pathology Model:** HD is increasingly seen as a confluence of two distinct processes: Track 1 (primary genetic/structural damage to HTT) and Track 2 (secondary metabolic and immune failure).
- **Copper Homeostasis:** A strong signal emerged linking copper dysregulation to mitochondrial failure and "cuproptosis" (copper-dependent cell death), suggesting new therapeutic avenues.
- **Advanced RNA Modalities:** Strong reinforcement for mRNA-splicing modulators (SKY-0515, PTC518) and next-gen delivery systems (LNPs) as the leading edge of clinical development.
- **Gut-Brain Axis:** Emerging evidence for postbiotics and psychobiotics as potential non-traditional interventions for HD.

## Updated Target Rankings

| Target | Mentions | Evidence Trend | Confidence |
|--------|----------|----------------|------------|
| Mutant Huntingtin (mHTT) | 15 | Shift toward splicing/isoform modulation | Stable |
| Mitochondrial Dysfunction | 12 | Linked to copper/oxidative stress cascade | Up |
| Inflammatory Effectors (NLRP3) | 8 | Specific focus on inflammasome blockade | Up |
| Lipid Metabolism (ApoE) | 4 | Critical for neural homeostasis | Up |
| Axonal Integrity (NfL) | 3 | Validated as robust trial readout | Stable |

## New Drug Candidates Identified

| Candidate | Target | Mechanism | Evidence |
|-----------|--------|-----------|----------|
| **SKY-0515** | HTT/PMS1 | mRNA-splicing modulator | Phase II/III |
| **AMT-130** | HTT | AAV5-miHTT gene therapy | Phase I/II |
| **MCC950** | NLRP3 | Inflammasome inhibitor | Preclinical |
| **Copper Chelators** | Copper | Restoring copper balance | Preclinical |
| **Disulfiram** | FDX1 | Inhibits cuproptosis | Preclinical |

## Novel Hypotheses

1.  **Copper-Inflammasome Cascade (Score: 95/100):** Copper dysregulation initiates mitochondrial failure, which subsequently triggers the NLRP3 inflammasome, leading to chronic neuroinflammation and accelerating mHTT toxicity.
2.  **Microbiome-Mitochondrial Synergy (Score: 85/100):** Gut microbiome imbalance contributes to systemic inflammation, which exacerbates primary mHTT-induced mitochondrial stress in the CNS.

## Methodology

- Corpus expanded via Paper Scout (PubMed search).
- 25 papers analyzed using gemma4:latest with specific prompts for structured extraction.
- Cross-paper synthesis focused on reconciling new data with previous experiment findings.
- Results logged to `experiment_005_expanded_results.json`.

## Limitations

- Synthesis is model-driven and requires human expert review.
- Focus on open-access full-text papers may bias results toward certain journals/institutions.
- "Two-Track" model is a conceptual framework derived by the AI, not yet a standard clinical term.

This is AI-generated research analysis, not medical advice.
For HD support, visit [hdsa.org](https://hdsa.org).
