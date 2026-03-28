# What Can an LLM Learn from 22 HD Research Papers Overnight?

*HD Research Hub — Experiment #1 | March 27, 2026*

## The Question

Huntington's Disease research is moving fast. In just the last 90 days, PubMed published dozens of papers spanning gene therapy, somatic expansion, biomarkers, AI/ML applications, and drug repurposing. No single researcher can read them all.

So we asked a simple question: **if we feed these papers to an open-source LLM running on a $1,000 edge device, what patterns does it find?**

This isn't a clinical study. We're not doctors. We're data scientists exploring whether AI can be a useful research assistant for the HD community — surfacing connections across papers that a human skimming abstracts might miss.

## What We Did

1. **Pulled 22 recent papers** from PubMed across five search queries: HD treatment, HD + AI/ML, somatic CAG expansion, drug repurposing, and biomarkers
2. **Sent each abstract to Llama 3.1 8B** running on an NVIDIA Jetson AGX Orin (a 64GB edge AI device) via Ollama
3. **Asked the LLM to extract**: molecular targets, compounds mentioned, key findings, and whether the paper suggests drug repurposing potential
4. **Then asked it to generate hypotheses**: given everything it learned, what FDA-approved drugs might be worth investigating for HD?

Total cost: $0 (all open-source, local inference, public data).

## What We Found

**20 out of 22 papers** were successfully analyzed (2 had abstracts too short for the model to parse).

### The Research Landscape Right Now

The LLM categorized the papers and a clear picture emerged:

| Category | Count | What it tells us |
|----------|-------|-----------------|
| Mechanism studies | 6 | Scientists are still uncovering *how* HD works at the molecular level |
| Reviews | 5 | The field is synthesizing — a sign that enough new data exists to warrant reviews |
| Biomarker research | 4 | Growing focus on *measuring* HD progression, critical for clinical trials |
| AI/ML applications | 3 | Machine learning is entering HD research, but still early |
| Gene therapy | 2 | The most promising treatment approach, but few papers this quarter |

### Targets the LLM Kept Finding

Across all papers, these molecular targets appeared most frequently:

- **HTT / mHTT** (huntingtin protein) — still the central focus, but researchers are looking at it from new angles: post-translational modifications (phosphorylation, SUMOylation, ubiquitination) that might offer druggable intervention points
- **TDP-43** — an unexpected connection. A new paper links TDP-43 proteinopathies (usually associated with ALS) to HD mechanisms. Cross-disease insights like this are exactly what pattern-matching AI is good at finding.
- **NfL (neurofilament light chain)** — emerging as the leading biomarker for tracking HD progression. Multiple papers confirmed it becomes "exponentially higher" with CAG repeat length.
- **MLH1 / PMS2** — DNA mismatch repair genes tied to somatic CAG expansion. A paper on disrupting protein-protein interactions in MLH1's C-terminal domain caught the LLM's attention — this is the frontier of HD genetics.

### An Interesting Observation

The LLM flagged that **post-translational modifications of huntingtin** (not just the protein itself) are getting significant research attention. Phosphorylation, SUMOylation, O-GlcNAcylation — these are chemical modifications that change how the protein behaves. Each one is potentially a drug target, and they're less explored than the protein itself.

## AI-Generated Hypotheses

We then asked the model: based on everything you just analyzed, suggest 5 FDA-approved drugs that might be worth investigating for HD. Here's what it returned, with our honest assessment:

### 1. Tocilizumab (Score: 80/100)
- **What it is:** An IL-6 receptor blocker, approved for rheumatoid arthritis
- **The idea:** Mutant huntingtin triggers neuroinflammation. Blocking IL-6 might reduce the inflammatory damage
- **Our take:** Interesting. IL-6 is elevated in HD models, and anti-inflammatory approaches are underexplored. But tocilizumab is an IV infusion and may not cross the blood-brain barrier well. Worth a literature deep-dive.

### 2. Riluzole (Score: 60/100)
- **What it is:** Glutamate release inhibitor, approved for ALS
- **The idea:** HD involves excitotoxicity (too much glutamate killing neurons). Riluzole reduces glutamate.
- **Our take:** Actually already tested in HD with modest results. The model didn't know this, which is a good reminder that AI hypotheses need human verification.

### 3. Lithium (Score: 55/100)
- **What it is:** Mood stabilizer, one of the oldest psychiatric drugs
- **The idea:** May reduce TDP-43 phosphorylation and aggregation — relevant given the newly discovered TDP-43/HD connection
- **Our take:** The TDP-43 angle is genuinely novel. Lithium's effect on autophagy and GSK-3β is well-documented. This connection through the new TDP-43 paper is the kind of cross-paper insight that's hard for humans to make quickly.

### 4. Bisoprolol (Score: 50/100)
- **What it is:** Beta-blocker for heart conditions
- **The idea:** May reduce stress-associated NfL elevation
- **Our take:** Weak. NfL is a *biomarker*, not a cause. Reducing the biomarker doesn't treat the disease. This is a good example of the model confusing correlation with causation.

### 5. Tetracycline (Score: 40/100)
- **What it is:** Antibiotic
- **The idea:** Might disrupt protein-protein interactions in MLH1
- **Our take:** Creative but speculative. The model connected the MLH1 PPI paper with tetracycline's known protein-binding properties, but the leap is too big without structural data.

## What Worked, What Didn't

**What worked:**
- The LLM correctly categorized 20/22 papers by research type
- It extracted meaningful targets and identified cross-paper patterns (TDP-43 connection, post-translational modifications)
- The Tocilizumab and Lithium hypotheses are interesting starting points that warrant expert review and literature validation
- Running on Jetson means this can repeat nightly at zero cost

**What didn't:**
- 2 papers failed to parse (abstracts too short or structured unusually)
- The model didn't know which drugs have already been tested in HD (Riluzole)
- One hypothesis confused a biomarker with a causal target (Bisoprolol/NfL)
- Repurposing signals from individual papers were zero — the model found signals only when synthesizing across papers

**Lesson:** LLMs are good at pattern-matching across papers but bad at knowing what's already been tried. The best use is generating starting-point ideas for human researchers to evaluate — not making clinical decisions.

## Important Limitations

- **No expert review.** These hypotheses have not been reviewed by HD researchers, pharmacologists, or clinicians. They are LLM outputs, not peer-reviewed findings.
- **No experimental validation.** None of these ideas have been tested in a lab, animal model, or clinical setting by us.
- **Abstracts only.** The AI read paper abstracts, not full texts. Important details, caveats, and negative results in full papers were invisible to the model.
- **Model knowledge gaps.** The LLM doesn't know the full history of HD clinical trials. It suggested Riluzole without knowing it was already tested.
- **Scoring is relative, not absolute.** A "score" of 80/100 means the model rated its own rationale highly — it does not mean the hypothesis has an 80% chance of working.
- **Single model, single run.** Results from one LLM in one session. Different models or different prompts could produce different hypotheses.

If you are a researcher and see something interesting here, please evaluate it independently using primary literature and your domain expertise. We welcome feedback — open an issue on [GitHub](https://github.com/jravinder/hd-research-agent/issues).

## How to Reproduce This

Everything is open source:

```bash
git clone https://github.com/jravinder/hd-research-agent
cd hd-research-agent
pip install -r requirements.txt
python src/run_experiment.py
```

Requires: Python 3.10+, Ollama with any model (we used llama3.1:8b on Jetson, but it works on any Mac too).

## What's Next

- **Experiment #2:** Focus specifically on somatic CAG expansion papers (MSH3, FAN1, PMS1) — the hottest frontier in HD genetics
- **Experiment #3:** Run the same papers through multiple models and compare outputs — do they agree?
- **Monthly digest:** Automate this into a monthly published analysis on the website

## About This Project

HD Research Hub is an open-source project by a curious data scientist exploring how AI can help accelerate Huntington's Disease research. We're not doctors, not a pharma company, not competing with the excellent work of HDSA, HDBuzz, and the HD research community. We're building tools and publishing what we learn, openly, in case it's useful.

All data from [PubMed](https://pubmed.ncbi.nlm.nih.gov). All code on [GitHub](https://github.com/jravinder/hd-research-agent). All hypotheses are AI-generated and unvalidated — always consult qualified researchers and healthcare professionals.

*— HD Research Hub Team*
