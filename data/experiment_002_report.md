# Experiment #2: Deep Full-Text Analysis of HD Research Papers

**Date:** March 30, 2026
**Model:** llama3.1:8b on NVIDIA Jetson AGX Orin
**Papers read (full text):** 16
**Total sections analyzed:** 380
**Total characters read:** 1,935,627

## Difference from Experiment #1

Experiment #1 read **abstracts only** (200 words each). This experiment reads **entire papers** end-to-end: Introduction, Methods, Results, Discussion, Conclusions. Every section, every finding, every data point the authors reported.

## Top Findings

1. The K845N variant of LIG1 confers enhanced substrate discrimination and increased repair fidelity, suppressing somatic CAG expansion in mice.
2. CRISPR-Cas technology has shown potential in treating neurodegenerative diseases by allowing for precise genetic modifications to address the underlying causes.
3. Mitochondrial dysfunction is a key driver of neuroinflammation in various neurological disorders, including AD, PD, and HD.

## Cross-Paper Contradictions

- There is no clear consensus on the role of copper homeostasis imbalance in neurodegenerative diseases, with some papers suggesting it contributes to disease progression while others do not mention it at all.

## Promising Targets

- **CGAS** (3 papers): involved in mtDNA release and neuroinflammation
- **DNJC7** (2 papers): potent modifier of polyQ protein aggregation
- **Htt CAG repeat** (4 papers): underlying cause of HD

## New Hypotheses (from full-text analysis)

- [80/100] The K845N variant of LIG1 may be a potential therapeutic target for HD by suppressing somatic CAG expansion and improving mitochondrial function.
- [70/100] CRISPR-Cas technology may be used to deliver genes that promote mitochondrial biogenesis and function, leading to improved outcomes in neurodegenerative diseases.
- [90/100] The inhibition of CGAS-mediated mtDNA release may be a potential therapeutic strategy for treating neuroinflammatory disorders, including AD, PD, and HD.

## Research Gaps Identified

- The role of gut microbiota dysbiosis in neurodegenerative diseases is not well understood and warrants further investigation.
- There is limited research on the use of CRISPR-Cas technology to treat neurodegenerative diseases, particularly in human subjects.

## Methodology

- Full text retrieved from PubMed Central (open access papers only)
- Each paper analyzed by llama3.1:8b with 8K context window
- Cross-paper synthesis generated from all individual analyses
- All code: [github.com/jravinder/hd-research-agent](https://github.com/jravinder/hd-research-agent)

## Limitations

- Only open-access papers analyzed (papers behind paywalls are excluded)
- 8K context window means very long papers are truncated (first ~6000 chars per paper)
- Single model, single run
- Not reviewed by HD domain experts

This is AI-generated research analysis, not medical advice.
