# Methods + Experiment Log

*Auto-compiled on 2026-04-03*

## Experiment History

| ID | Date | Model | Papers | Successful | Characters |
|----|------|-------|--------|------------|------------|
| EXP-001 | 2026-03-27 | llama3.1:8b | 22 | 0 | 0 |
| EXP-002 | 2026-04-01 | qwen3.5:27b | 16 | 0 | 1,935,627 |
| EXP-003_GEMMA4 | 2026-04-02 | gemma4:latest | 16 | 14 | 1,935,627 |
| EXP-003 | 2026-04-02 | qwen3.5:27b | 16 | 0 | 1,935,627 |

## Reproducibility

```bash
git clone https://github.com/jravinder/hd-research-agent
pip install -r requirements.txt
python src/run_experiment.py    # EXP-001
python src/run_experiment_2.py  # EXP-002
python src/run_experiment_3.py  # EXP-003
```
