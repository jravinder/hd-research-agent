# Experiment #1: AI-Powered HD Literature Analysis

**Date:** March 27, 2026
**Model:** llama3.1:8b (Llama 3.1 8B on NVIDIA Jetson AGX Orin)
**Papers analyzed:** 22
**Method:** Autonomous LLM analysis of recent PubMed abstracts + hypothesis generation

## Summary

We fed 22 recent Huntington's disease research papers to Llama 3.1 8B running on an NVIDIA Jetson AGX Orin and asked it to extract structured insights: molecular targets, compounds, key findings, and drug repurposing signals.

This is not a clinical study. It's a data science experiment asking: **what patterns can an LLM surface from HD research that might help prioritize investigation?**

## Key Numbers

| Metric | Count |
|--------|-------|
| Papers analyzed | 22 |
| High relevance | 17 |
| Repurposing signals found | 0 |
| Novel targets identified | 7 |

## Most Mentioned Targets

| Target | Mentions |
|--------|----------|
| huntington's disease | 6 |
| neurological diseases | 1 |
| huntingtin (htt) gene | 1 |
| mutant huntingtin (mhtt) protein | 1 |
| tdp-43 | 1 |
| tau | 1 |
| α-synuclein | 1 |
| mutant huntingtin | 1 |
| huntingtin gene | 1 |
| cag repeats | 1 |

## Most Mentioned Compounds

| Compound | Mentions |
|----------|----------|
| gm-csf/sargramostim | 1 |

## Paper-by-Paper Analysis

### [41233526] Huntington disease: somatic expansion, pathobiology and therapeutics.
- **Journal:** Nature reviews. Neurology (2026 Jan)
- **Category:** ?
- **Finding:** Analysis failed
- **Targets:** 
- **Compounds:** 
- **Relevance:** ?
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41233526/)

### [41497150] AMT-130 gene therapy: a promising disease-modifying approach for Huntington's disease.
- **Journal:** Annals of medicine and surgery (2012) (2026 Jan)
- **Category:** ?
- **Finding:** Analysis failed
- **Targets:** 
- **Compounds:** 
- **Relevance:** ?
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41497150/)

### [41389437] Genetic therapies for neurological diseases.
- **Journal:** Pharmacological reviews (2026 Jan)
- **Category:** review
- **Finding:** The paper presents a comprehensive review of genetic therapies for neurological diseases, highlighting various approaches and their potential applications.
- **Targets:** Huntington's disease, neurological diseases
- **Compounds:** 
- **Relevance:** high
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41389437/)

### [41349897] Huntingtin protein in health and Huntington's disease: Molecular mechanisms, pathology and therapeutic strategies.
- **Journal:** Ageing research reviews (2026 Jan)
- **Category:** mechanism
- **Finding:** Phosphorylation, SUMOylation, O-GlcNAcylation, and ubiquitination are some of the post-translational modifications that affect the toxicity, location, and aggregation of mutant huntingtin protein.
- **Targets:** huntingtin (HTT) gene, mutant huntingtin (mHTT) protein
- **Compounds:** 
- **Relevance:** high
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41349897/)

### [40891506] TDP-43 proteinopathies and neurodegeneration: insights from Caenorhabditis elegans models.
- **Journal:** The FEBS journal (2026 Jan)
- **Category:** mechanism
- **Finding:** Deciphering the pathophysiological mechanisms underpinning TDP-43-mediated neurodegeneration is paramount for developing effective therapies and novel diagnostic tools.
- **Targets:** TDP-43
- **Compounds:** 
- **Relevance:** high
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/40891506/)

### [41479093] Nursing in Huntington's Disease and Cell and Gene Therapy.
- **Journal:** Advances in experimental medicine and biology (2026)
- **Category:** review
- **Finding:** Recent advancements in cell and gene therapy have brought new treatment options for Huntington's Disease.
- **Targets:** Huntington's Disease
- **Compounds:** 
- **Relevance:** high
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41479093/)

### [41585268] Viral and non-viral cellular therapies for neurodegeneration.
- **Journal:** Frontiers in medicine (2025)
- **Category:** review
- **Finding:** Current and developing therapeutic strategies for neurodegenerative diseases include viral vector-based gene delivery, antisense oligonucleotide methods, stem cell transplantation, and genome editing technologies.
- **Targets:** tau, α-synuclein, mutant huntingtin
- **Compounds:** 
- **Relevance:** high
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41585268/)

### [41338440] Machine learning and deep learning in clinical practice: Advancing neurodegenerative disease diagnosis with multimodal markers.
- **Journal:** Brain research bulletin (2026 Jan)
- **Category:** ai_ml
- **Finding:** Recent advances in artificial intelligence, particularly machine learning (ML), have provided new opportunities for precision diagnosis and treatment in neurology.
- **Targets:** 
- **Compounds:** 
- **Relevance:** high
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41338440/)

### [41553597] Decoding Non-Neuronal Mechanisms and Therapeutic Targets in Huntington's Disease Through Integrative Transcriptomics and Machine Learning.
- **Journal:** Journal of molecular neuroscience : MN (2026 Jan)
- **Category:** gene_therapy|ai_ml
- **Finding:** An integrated computational approach combining machine learning with transcriptomic analysis identified novel therapeutic targets in Huntington's disease.
- **Targets:** huntingtin gene, CAG repeats
- **Compounds:** 
- **Relevance:** high
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41553597/)

### [41674784] CRISPR-Cas technologies in neurodegenerative disorders: mechanistic insights, therapeutic potential, and translational challenges.
- **Journal:** Frontiers in neurology (2025)
- **Category:** review
- **Finding:** CRISPR-Cas genome-editing technologies have emerged as powerful tools for precise DNA and RNA modulation, offering promising therapeutic strategies for neurodegenerative disorders.
- **Targets:** Huntington's disease, Alzheimer's disease, Parkinson's disease, amyotrophic lateral sclerosis
- **Compounds:** 
- **Relevance:** high
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41674784/)

### [41276980] Computational Approaches to Neurological Disorder Diagnosis: An In-Depth Review of Current Methods and Future Prospects.
- **Journal:** Current medical imaging (2026)
- **Category:** review
- **Finding:** The review highlights the current computational approaches employed for the diagnosis of Huntington's disease and other neurological disorders.
- **Targets:** Huntington's disease
- **Compounds:** 
- **Relevance:** medium
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41276980/)

### [41313957] Protective predictors of cardiovascular disease: an explainable AI approach.
- **Journal:** Public health (2026 Jan)
- **Category:** other
- **Finding:** An interpretable machine learning model (XGBoost) was developed to identify protective factors against cardiovascular disease.
- **Targets:** 
- **Compounds:** 
- **Relevance:** low
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41313957/)

### [41505360] Multimodal MRI integrating anti-motion multi-parametric mappings for investigating subcortical nuclei microstructural alterations in Huntington's disease.
- **Journal:** Journal of Huntington's disease (2026 Jan)
- **Category:** clinical_trial
- **Finding:** Multimodal MRI integrating anti-motion multi-parametric mappings can detect subcortical nuclei microstructural alterations in Huntington's disease.
- **Targets:** Huntington's disease
- **Compounds:** 
- **Relevance:** high
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41505360/)

### [41480639] Disruption of protein-protein interaction hotspots in the C-terminal domain of MLH1 confers mismatch repair deficiency.
- **Journal:** NAR cancer (2025 Dec)
- **Category:** mechanism
- **Finding:** Disruption of protein-protein interaction hotspots in the C-terminal domain of MLH1 confers mismatch repair deficiency.
- **Targets:** MLH1, PMS2
- **Compounds:** 
- **Relevance:** high
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41480639/)

### [41699789] Huntington's Disease: An Overview of Biomarkers in Prognostic, Diagnostic, and Therapeutic Management.
- **Journal:** Rejuvenation research (2026 Feb)
- **Category:** review
- **Finding:** Recent research has identified neurofilament light chain and mHTT as robust indicators of Huntington's disease progression.
- **Targets:** HTT gene, mHTT protein
- **Compounds:** 
- **Relevance:** high
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41699789/)

### [41000014] Cerebrospinal Fluid Proenkephalin Predicts Striatal Atrophy Decades before Clinical Motor Diagnosis in Huntington's Disease.
- **Journal:** Movement disorders : official journal of the Movement Disorder Society (2026 Jan)
- **Category:** biomarker
- **Finding:** Cerebrospinal fluid Proenkephalin concentration predicts striatal atrophy decades before clinical motor diagnosis in Huntington's disease.
- **Targets:** Proenkephalin (PENK)
- **Compounds:** 
- **Relevance:** high
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41000014/)

### [41492395] Neural and biomarker correlates of the Parkinson's Disease-Cognitive Rating Scale in Huntington's disease.
- **Journal:** Neuroimage. Reports (2026 Mar)
- **Category:** biomarker
- **Finding:** This study investigates the neuroanatomical and fluid biomarker correlates of performance on the Parkinson's Disease-Cognitive Rating Scale in Huntington's disease.
- **Targets:** neurofilament light chain (NfL)
- **Compounds:** 
- **Relevance:** high
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41492395/)

### [41421353] Blood measure of neuronal death is exponentially higher with age, especially in females, and halted in Alzheimer's disease by GM-CSF treatment.
- **Journal:** Cell reports. Medicine (2026 Jan)
- **Category:** biomarker
- **Finding:** Plasma concentrations of UCH-L1 and NfL become exponentially higher with age, especially in females.
- **Targets:** UCH-L1, NfL, GFAP
- **Compounds:** GM-CSF/sargramostim
- **Relevance:** high
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41421353/)

### [41527739] Insights into phosphoproteomic studies and prospects of phosphoproteins as biomarkers for brain disorders.
- **Journal:** Journal of Alzheimer's disease : JAD (2026 Mar)
- **Category:** biomarker
- **Finding:** Phosphoproteomic studies and phosphoprotein biomarkers show promise for predicting, diagnosing, prognosticating, and monitoring brain disorders.
- **Targets:** microtubule-associated protein tau, neurofilament heavy polypeptide
- **Compounds:** 
- **Relevance:** high
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41527739/)

### [41828602] A Two-Track Model of Huntington's Disease Pathology: Striatal Atrophy Mediates Maladaptive Immune Dysregulation.
- **Journal:** International journal of molecular sciences (2026 Mar)
- **Category:** biomarker
- **Finding:** A distinct 'Two-Track' model of Huntington's disease pathology was revealed, with axonal damage protein neurofilament light chain (NEFL) showing a strong inverse correlation with putamen volume.
- **Targets:** neurofilament light chain (NEFL)
- **Compounds:** 
- **Relevance:** high
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41828602/)

### [41762390] Multiple System Atrophy Combined Outcome Assessment (MuSyCA): process, format, and validation plan.
- **Journal:** Clinical autonomic research : official journal of the Clinical Autonomic Research Society (2026 Feb)
- **Category:** clinical_trial
- **Finding:** A new outcome assessment tool, MuSyCA, was developed to track disease progression in Multiple System Atrophy trials.
- **Targets:** Multiple System Atrophy
- **Compounds:** 
- **Relevance:** high
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41762390/)

### [41517524] Emerging Oculomic Signatures: Linking Thickness of Entire Retinal Layers with Plasma Biomarkers in Preclinical Alzheimer's Disease.
- **Journal:** Journal of clinical medicine (2025 Dec)
- **Category:** biomarker
- **Finding:** The study explores the link between retinal layer thickness and plasma biomarkers in preclinical Alzheimer's Disease, but does not directly relate to Huntington's disease.
- **Targets:** Huntington's disease
- **Compounds:** 
- **Relevance:** low
- **Repurposing signal:** No
- [PubMed Link](https://pubmed.ncbi.nlm.nih.gov/41517524/)

## AI-Generated Drug Repurposing Hypotheses

*These are exploratory ideas generated by an AI model, not clinical recommendations.*

### Riluzole -> mutant huntingtin protein aggregation
- **Original use:** Amyotrophic Lateral Sclerosis (ALS)
- **Rationale:** Riluzole's mechanism of inhibiting glutamate release may also reduce the excitotoxicity associated with mutant huntingtin protein aggregation. Its neuroprotective effects in ALS suggest it could have a similar impact on HD.
- **Confidence:** medium
- **Score:** 60/100
- **Suggested next experiment:** Assess Riluzole's effect on mutant huntingtin protein aggregation in vitro

### Tetracycline -> protein-protein interactions (PPIs) in the C-terminal domain of MLH1
- **Original use:** Bacterial infections
- **Rationale:** Tetracycline's ability to bind and inhibit PPIs may also disrupt the protein-protein interactions that contribute to mismatch repair deficiency in HD. Its use as an antibiotic suggests it could have a similar impact on PPIs in HD.
- **Confidence:** low
- **Score:** 40/100
- **Suggested next experiment:** Investigate Tetracycline's effect on PPIs in the C-terminal domain of MLH1

### Bisoprolol -> neurofilament light chain (NfL) as a biomarker for HD progression
- **Original use:** Hypertension and Angina
- **Rationale:** Bisoprolol's beta-blockade activity may also reduce the stress and inflammation associated with NfL elevation in HD. Its use as an antihypertensive suggests it could have a similar impact on reducing NfL levels.
- **Confidence:** medium
- **Score:** 50/100
- **Suggested next experiment:** Assess Bisoprolol's effect on NfL levels in patients with HD

### Tocilizumab -> inflammation and immune response associated with mutant huntingtin protein aggregation
- **Original use:** Rheumatoid Arthritis and Juvenile Idiopathic Arthritis
- **Rationale:** Tocilizumab's IL-6 receptor blockade may also reduce the inflammation and immune response associated with mutant huntingtin protein aggregation in HD. Its use as an anti-inflammatory suggests it could have a similar impact on reducing inflammation in HD.
- **Confidence:** high
- **Score:** 80/100
- **Suggested next experiment:** Investigate Tocilizumab's effect on inflammation and immune response in patients with HD

### Lithium -> TDP-43-mediated neurodegeneration
- **Original use:** Bipolar Disorder
- **Rationale:** Lithium's ability to modulate protein kinase B (PKB) activity may also reduce the phosphorylation and aggregation of TDP-43 in HD. Its use as a mood stabilizer suggests it could have a similar impact on reducing TDP-43-mediated neurodegeneration.
- **Confidence:** medium
- **Score:** 55/100
- **Suggested next experiment:** Assess Lithium's effect on TDP-43 phosphorylation and aggregation

---

## Methodology

1. **Data collection:** PubMed E-utilities API, 5 search queries covering HD treatment, AI/ML, somatic expansion, drug repurposing, and biomarkers (last 90 days)
2. **Analysis:** Each paper abstract sent to Llama 3.1 8B with structured extraction prompt
3. **Hypothesis generation:** Findings summarized and fed to LLM for drug repurposing ideation
4. **Infrastructure:** NVIDIA Jetson AGX Orin 64GB, Ollama llama3.1:8b
5. **Code:** [github.com/jravinder/hd-research-agent](https://github.com/jravinder/hd-research-agent)

## Disclaimer

This is an open-source research experiment by a curious data scientist, not a medical study. AI-generated hypotheses have not been clinically validated. Always consult qualified healthcare professionals. Published to contribute ideas to the HD research community.

## License

MIT — use freely, build on it, improve it.
