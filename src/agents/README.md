# HD Research Agents

Autonomous agents that run on schedule, building up the research corpus over time.

| Agent | What it does | Schedule |
|-------|-------------|----------|
| `paper_scout.py` | Scans PubMed for new HD papers, analyzes with LLM, appends to corpus | Every 6 hours |
| `hypothesis_refiner.py` | Takes existing hypotheses, searches for supporting/contradicting evidence, re-scores | Daily |
| `trial_watcher.py` | Monitors ClinicalTrials.gov for status changes, alerts on new recruiting trials | Daily |
| `digest_writer.py` | Compiles weekly findings into a publishable digest on the website | Weekly (Sunday) |
