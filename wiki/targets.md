# Molecular Targets

Compiled from EXP-001 (abstracts), EXP-002 (full text), and Paper Scout (46 papers).

## High-Confidence Targets (found in multiple experiments)

### HTT / mHTT (Huntingtin protein)
- The root cause. CAG repeat expansion produces toxic mutant huntingtin.
- Every experiment identifies this. All therapies ultimately aim to reduce mHTT.
- Sources: EXP-001 (6 mentions), EXP-002 (4 papers), corpus (all papers)

### cGAS-STING Pathway
- Mediates mitochondrial DNA release causing neuroinflammation.
- Found in 3 papers in EXP-002 full-text analysis. Not visible from abstracts alone.
- Cross-disease target (HD, AD, PD).
- Hypothesis: cGAS inhibition scored 90/100 in EXP-002.

### LIG1 (DNA Ligase 1)
- K845N variant suppresses somatic CAG expansion in mice.
- Found only in EXP-002 (full text). Invisible from abstracts.
- Novel. Connects DNA repair to HD progression.
- Hypothesis: LIG1 as therapeutic target scored 80/100 in EXP-002.

### NfL (Neurofilament Light Chain)
- Leading biomarker for tracking HD progression.
- Multiple papers confirmed it becomes exponentially higher with CAG repeat length.
- Not a drug target (biomarker, not causal). EXP-001 correctly flagged this distinction.

### MSH3 / FAN1 / PMS1
- Somatic expansion modifier genes. Hottest frontier in HD genetics.
- Control how fast CAG repeats grow in brain cells.
- Nobody has published an AI drug screen against these. Our planned EXP-004.

## Targets Found in Single Experiments

### TDP-43
- EXP-001 found a cross-disease connection between TDP-43 (usually ALS) and HD.
- Lithium hypothesis (GSK-3B inhibition) scored 55/100.

### DNJC7
- EXP-002: potent modifier of polyQ protein aggregation. 2 papers.

### IL-6 Pathway
- EXP-001: Tocilizumab hypothesis for neuroinflammation scored 80/100.
- No new PubMed evidence found in hypothesis refiner run.

## What Abstracts Miss vs Full Text

| Target | Found in Abstracts (EXP-001) | Found in Full Text (EXP-002) |
|--------|------------------------------|------------------------------|
| HTT/mHTT | Yes | Yes |
| cGAS-STING | No | Yes (3 papers) |
| LIG1 K845N | No | Yes |
| TDP-43 connection | Yes (1 paper) | Yes |
| NfL biomarker | Yes | Yes |
| DNJC7 | No | Yes (2 papers) |
| Copper homeostasis | No | Contradictory (debated) |

Full-text analysis found 3 targets invisible from abstracts alone.
