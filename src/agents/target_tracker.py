"""Target Tracker Agent — Updates protein target rankings as evidence shifts.

Reads the analysis log and recalculates target scores based on:
- How many papers mention each target
- Evidence levels (clinical > preclinical > concept)
- Recency (newer papers weighted higher)
- Drug candidate proximity to trials

Outputs updated target rankings to data/target_rankings.json
"""

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DATA_DIR = ROOT / "data"
ANALYSIS_LOG = DATA_DIR / "analysis_log.json"
RANKINGS_FILE = DATA_DIR / "target_rankings.json"

# Known HD somatic expansion targets
KNOWN_TARGETS = {
    "msh3": {"full_name": "MutS Homolog 3", "role": "drives expansion"},
    "fan1": {"full_name": "Fanconi Anemia-Associated Nuclease 1", "role": "opposes expansion"},
    "pms1": {"full_name": "Post-Meiotic Segregation 1", "role": "enables expansion"},
    "mlh1": {"full_name": "MutL Homolog 1", "role": "drives expansion"},
    "lig1": {"full_name": "DNA Ligase 1", "role": "locks in expansion"},
    "htt": {"full_name": "Huntingtin", "role": "primary disease gene"},
    "bdnf": {"full_name": "Brain-Derived Neurotrophic Factor", "role": "neuroprotection"},
    "hdac": {"full_name": "Histone Deacetylases", "role": "epigenetic regulation"},
    "mtor": {"full_name": "mTOR pathway", "role": "autophagy regulation"},
    "nlrp3": {"full_name": "NLRP3 Inflammasome", "role": "neuroinflammation"},
}

EVIDENCE_WEIGHTS = {
    "clinical": 5,
    "preclinical": 3,
    "concept": 1,
}


def run():
    print(f"\n{'='*50}")
    print(f"  Target Tracker Agent")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    if not ANALYSIS_LOG.exists():
        print("  No analysis log found. Run paper_analyzer first.")
        return

    with open(ANALYSIS_LOG) as f:
        log = json.load(f)

    analyzed = log.get("analyzed", {})
    print(f"  Papers in analysis log: {len(analyzed)}")

    # Count target mentions and evidence
    target_data = defaultdict(lambda: {
        "mentions": 0,
        "papers": [],
        "compounds": [],
        "evidence_levels": [],
        "score": 0,
    })

    for pmid, entry in analyzed.items():
        analysis = entry.get("analysis", {})
        if "error" in analysis:
            continue

        targets = analysis.get("targets", [])
        compounds = analysis.get("compounds", [])
        readiness = analysis.get("clinical_readiness", "concept")
        relevance = analysis.get("relevance_score", 5)

        for target in targets:
            key = str(target).lower().strip()
            if not key or len(key) < 2:
                continue
            target_data[key]["mentions"] += 1
            target_data[key]["papers"].append(pmid)
            target_data[key]["evidence_levels"].append(readiness)

            # Add compounds associated with this target
            for c in compounds:
                if str(c) not in target_data[key]["compounds"]:
                    target_data[key]["compounds"].append(str(c))

    # Calculate scores
    for key, data in target_data.items():
        mention_score = min(data["mentions"] * 2, 20)  # Cap at 20
        evidence_score = sum(EVIDENCE_WEIGHTS.get(e, 1) for e in data["evidence_levels"])
        compound_score = min(len(data["compounds"]) * 3, 15)  # Cap at 15

        data["score"] = mention_score + evidence_score + compound_score

    # Sort by score
    ranked = sorted(target_data.items(), key=lambda x: x[1]["score"], reverse=True)

    # Build output
    rankings = {
        "generated": datetime.now().isoformat(),
        "papers_analyzed": len(analyzed),
        "targets": [],
    }

    print(f"\n  Target Rankings:")
    for key, data in ranked[:20]:
        info = KNOWN_TARGETS.get(key, {})
        entry = {
            "symbol": key.upper(),
            "full_name": info.get("full_name", ""),
            "role": info.get("role", ""),
            "mentions": data["mentions"],
            "score": data["score"],
            "top_compounds": data["compounds"][:5],
            "evidence_levels": list(set(data["evidence_levels"])),
            "paper_count": len(set(data["papers"])),
        }
        rankings["targets"].append(entry)
        print(f"    {key.upper():8s}  score:{data['score']:3d}  mentions:{data['mentions']:2d}  compounds:{len(data['compounds'])}")

    with open(RANKINGS_FILE, "w") as f:
        json.dump(rankings, f, indent=2, default=str)

    print(f"\n  Rankings saved to {RANKINGS_FILE}")
    print(f"  Total targets tracked: {len(rankings['targets'])}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    run()
