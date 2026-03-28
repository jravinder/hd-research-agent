# HD Research Agents

Autonomous agents that run on schedule, building up the research corpus over time.

| Agent | What it does | Schedule |
|-------|-------------|----------|
| `paper_scout.py` | Scans PubMed for new HD papers, analyzes with LLM, appends to corpus | Every 6 hours |
| `hypothesis_refiner.py` | Takes existing hypotheses, searches for supporting/contradicting evidence, re-scores | Daily |
| `social_watcher.py` | Monitors X, Reddit, YouTube, HN for HD chatter using last30days skill | Daily |
| `digest_writer.py` | Compiles weekly findings into a publishable digest on the website | Weekly (Sunday) |
| `run_all.py` | Orchestrates all agents, rebuilds site, publishes | On demand or cron |
