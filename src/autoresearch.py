"""Autoresearch Loop — autonomous HD research agent that runs overnight.

Inspired by Karpathy's autoresearch: generates hypotheses, searches literature,
scores candidates, refines — in a loop. Each cycle:

1. Review current knowledge state
2. Generate research questions
3. Search PubMed for answers
4. Analyze findings with LLM
5. Update knowledge graph
6. Score and rank drug candidates
7. Log results and iterate
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from llm import ask, ask_json
from literature_agent import search_pubmed, fetch_papers, analyze_paper
from repurposing_scanner import HD_TARGETS, KNOWN_REPURPOSING_CANDIDATES, generate_hypotheses
from trial_tracker import search_trials

console = Console()

LOG_DIR = Path.home() / "Documents" / "hd-research-agent" / "runs"


def log_cycle(run_dir: Path, cycle: int, data: dict):
    """Write cycle results to disk."""
    cycle_file = run_dir / f"cycle_{cycle:03d}.json"
    with open(cycle_file, "w") as f:
        json.dump(data, f, indent=2, default=str)
    console.print(f"  [dim]Logged to {cycle_file}[/dim]")


def generate_research_questions(knowledge_state: dict) -> list[str]:
    """Use LLM to generate the next set of research questions."""
    targets = list(HD_TARGETS.keys())
    known_drugs = [d["drug"] for d in KNOWN_REPURPOSING_CANDIDATES]

    prompt = f"""You are an autonomous HD research agent. Based on the current state of knowledge,
generate 3 specific, searchable research questions for PubMed.

Current knowledge:
- Known HD targets: {', '.join(targets)}
- Known drug candidates: {', '.join(known_drugs)}
- Cycles completed: {knowledge_state.get('cycles_completed', 0)}
- Papers analyzed so far: {knowledge_state.get('papers_analyzed', 0)}
- Hypotheses generated: {knowledge_state.get('hypotheses_count', 0)}

Previous queries (avoid repeating): {knowledge_state.get('previous_queries', [])}

Focus on:
- Underexplored targets (not just HTT)
- Novel mechanisms discovered in the last year
- Drug repurposing opportunities
- Somatic CAG expansion modifiers (MSH3, FAN1, PMS1)
- Biomarkers for tracking treatment response

Return JSON: {{"questions": ["query1", "query2", "query3"]}}"""

    result = ask_json(prompt, system="You are an autonomous HD research agent.")
    return result.get("questions", [])


def score_hypothesis(hypothesis: dict, supporting_papers: list[dict]) -> float:
    """Score a drug repurposing hypothesis based on evidence."""
    prompt = f"""Score this drug repurposing hypothesis for Huntington's disease on a 0-100 scale.

Hypothesis: {hypothesis.get('drug', '?')} targeting {hypothesis.get('hd_target', '?')}
Mechanism: {hypothesis.get('mechanism', '?')}
Rationale: {hypothesis.get('rationale', '?')}

Supporting evidence from {len(supporting_papers)} papers:
{json.dumps([p.get('analysis', {}).get('key_finding', '') for p in supporting_papers[:5]], indent=2)}

Score based on:
- Strength of mechanistic rationale (0-25)
- Quality of supporting evidence (0-25)
- Feasibility (FDA-approved drug, brain penetrant?) (0-25)
- Novelty (not already well-studied for HD) (0-25)

Return JSON: {{"score": N, "breakdown": {{"mechanism": N, "evidence": N, "feasibility": N, "novelty": N}}, "reasoning": "brief explanation"}}"""

    try:
        result = ask_json(prompt, system="You are a drug development expert.")
        return result.get("score", 0)
    except Exception:
        return 0


def run_cycle(cycle: int, knowledge_state: dict, run_dir: Path) -> dict:
    """Run one research cycle."""
    console.print(Panel(f"[bold]Cycle {cycle}[/bold] | {datetime.now().strftime('%H:%M:%S')}", style="blue"))

    cycle_data = {"cycle": cycle, "timestamp": datetime.now().isoformat()}

    # Step 1: Generate research questions
    console.print("  [cyan]Generating research questions...[/cyan]")
    questions = generate_research_questions(knowledge_state)
    cycle_data["questions"] = questions
    for q in questions:
        console.print(f"    ? {q}")

    # Step 2: Search and analyze papers for each question
    all_papers = []
    all_analyses = []
    for q in questions:
        console.print(f"\n  [yellow]Searching: {q}[/yellow]")
        pmids = search_pubmed(q, days=90, max_results=5)
        if pmids:
            papers = fetch_papers(pmids)
            console.print(f"    Found {len(papers)} papers")
            for paper in papers[:3]:  # Analyze top 3 per question
                analysis = analyze_paper(paper)
                all_analyses.append({"paper": {"pmid": paper.pmid, "title": paper.title}, "analysis": analysis})
                finding = analysis.get("key_finding", "N/A")
                console.print(f"    [{paper.pmid}] {finding[:80]}")
                time.sleep(1)  # Rate limit
            all_papers.extend(papers)
        else:
            console.print("    No papers found")

        knowledge_state.setdefault("previous_queries", []).append(q)

    cycle_data["papers_found"] = len(all_papers)
    cycle_data["analyses"] = all_analyses
    knowledge_state["papers_analyzed"] = knowledge_state.get("papers_analyzed", 0) + len(all_analyses)

    # Step 3: Generate new hypotheses informed by findings
    console.print(f"\n  [green]Generating hypotheses from findings...[/green]")
    findings_summary = "; ".join(
        a["analysis"].get("key_finding", "")
        for a in all_analyses if a["analysis"].get("key_finding")
    )[:2000]

    try:
        hypotheses = generate_hypotheses(findings_summary)
        cycle_data["hypotheses"] = hypotheses
        knowledge_state["hypotheses_count"] = knowledge_state.get("hypotheses_count", 0) + len(hypotheses)

        # Score each hypothesis
        for h in hypotheses:
            score = score_hypothesis(h, all_analyses)
            h["score"] = score
            console.print(f"    {h.get('drug', '?')} → {h.get('hd_target', '?')}: [bold]{score}/100[/bold]")

        # Track best hypotheses across cycles
        best = knowledge_state.setdefault("best_hypotheses", [])
        for h in hypotheses:
            if h.get("score", 0) >= 60:
                best.append(h)
        # Keep top 20
        knowledge_state["best_hypotheses"] = sorted(best, key=lambda x: x.get("score", 0), reverse=True)[:20]

    except Exception as e:
        console.print(f"  [red]Hypothesis generation failed: {e}[/red]")
        cycle_data["hypotheses"] = []

    # Log
    knowledge_state["cycles_completed"] = cycle
    cycle_data["knowledge_state_snapshot"] = {
        "papers_analyzed": knowledge_state["papers_analyzed"],
        "hypotheses_count": knowledge_state.get("hypotheses_count", 0),
        "best_hypothesis_count": len(knowledge_state.get("best_hypotheses", [])),
    }
    log_cycle(run_dir, cycle, cycle_data)

    return knowledge_state


def run(hours: float = 8, cycle_delay_minutes: int = 5):
    """Run the autoresearch loop."""
    console.print(Panel(
        f"[bold blue]HD Autoresearch Agent[/bold blue]\n"
        f"Duration: {hours}h | Cycle delay: {cycle_delay_minutes}min\n"
        f"Model: {os.environ.get('HD_AGENT_MODEL', 'ollama/llama3.1:8b')}",
        title="Starting",
    ))

    # Setup logging
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = LOG_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"Logging to: {run_dir}\n")

    # Initialize knowledge state
    knowledge_state = {
        "cycles_completed": 0,
        "papers_analyzed": 0,
        "hypotheses_count": 0,
        "best_hypotheses": [],
        "previous_queries": [],
    }

    start_time = time.time()
    end_time = start_time + (hours * 3600)
    cycle = 0

    while time.time() < end_time:
        cycle += 1
        try:
            knowledge_state = run_cycle(cycle, knowledge_state, run_dir)
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user.[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Cycle {cycle} failed: {e}[/red]")

        elapsed = (time.time() - start_time) / 3600
        remaining = hours - elapsed
        console.print(f"\n[dim]Elapsed: {elapsed:.1f}h | Remaining: {remaining:.1f}h | Next cycle in {cycle_delay_minutes}min[/dim]\n")

        if time.time() < end_time:
            time.sleep(cycle_delay_minutes * 60)

    # Final summary
    console.print(Panel("[bold green]Autoresearch Complete[/bold green]", title="Done"))
    console.print(f"Cycles: {knowledge_state['cycles_completed']}")
    console.print(f"Papers analyzed: {knowledge_state['papers_analyzed']}")
    console.print(f"Hypotheses generated: {knowledge_state['hypotheses_count']}")

    best = knowledge_state.get("best_hypotheses", [])
    if best:
        console.print(f"\n[bold]Top {min(5, len(best))} Hypotheses:[/bold]")
        for h in best[:5]:
            console.print(f"  [{h.get('score', 0)}/100] {h.get('drug', '?')} → {h.get('hd_target', '?')}")
            console.print(f"    {h.get('rationale', '')[:100]}")

    # Save final state
    with open(run_dir / "final_state.json", "w") as f:
        json.dump(knowledge_state, f, indent=2, default=str)
    console.print(f"\nFinal state saved to {run_dir / 'final_state.json'}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HD Autoresearch Agent")
    parser.add_argument("--hours", type=float, default=8, help="Hours to run")
    parser.add_argument("--delay", type=int, default=5, help="Minutes between cycles")
    args = parser.parse_args()

    run(hours=args.hours, cycle_delay_minutes=args.delay)
