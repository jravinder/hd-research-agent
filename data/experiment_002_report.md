# Experiment #2: Deep Full-Text Analysis of HD Research Papers

**Date:** April 01, 2026
**Model:** qwen3.5:27b on NVIDIA Jetson AGX Orin
**Papers read (full text):** 16
**Total sections analyzed:** 380
**Total characters read:** 1,935,627

## Difference from Experiment #1

Experiment #1 read **abstracts only** (200 words each). This experiment reads **entire papers** end-to-end: Introduction, Methods, Results, Discussion, Conclusions. Every section, every finding, every data point the authors reported.

## Top Findings


## Cross-Paper Contradictions


## Promising Targets


## New Hypotheses (from full-text analysis)


## Research Gaps Identified


## Methodology

- Full text retrieved from PubMed Central (open access papers only)
- Each paper analyzed by qwen3.5:27b with 8K context window
- Cross-paper synthesis generated from all individual analyses
- All code: [github.com/jravinder/hd-research-agent](https://github.com/jravinder/hd-research-agent)

## Limitations

- Only open-access papers analyzed (papers behind paywalls are excluded)
- 8K context window means very long papers are truncated (first ~6000 chars per paper)
- Single model, single run
- Not reviewed by HD domain experts

This is AI-generated research analysis, not medical advice.
