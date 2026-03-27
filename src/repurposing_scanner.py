"""Repurposing Scanner — identifies existing drugs that may have activity against HD targets."""

import json
import time
from dataclasses import dataclass
from typing import Optional

import requests
from rich.console import Console
from rich.table import Table

from llm import ask, ask_json

console = Console()

# Known HD-relevant targets from transcriptomic studies (BDASeq, CHDI, literature)
HD_TARGETS = {
    "HTT": "Huntingtin protein — the primary cause of HD",
    "BDNF": "Brain-derived neurotrophic factor — reduced in HD, critical for neuronal survival",
    "DARPP-32": "Dopamine signaling — early marker of HD progression",
    "PDE10A": "Phosphodiesterase 10A — reduced in HD striatum",
    "mGluR5": "Metabotropic glutamate receptor 5 — excitotoxicity in HD",
    "HDAC": "Histone deacetylases — epigenetic dysregulation in HD",
    "CB1": "Cannabinoid receptor 1 — lost early in HD",
    "CB2": "Cannabinoid receptor 2 — neuroinflammation modulator",
    "Sigma-1R": "Sigma-1 receptor — Pridopidine target, neuroprotection",
    "FAN1": "Fanconi-associated nuclease 1 — DNA repair, somatic expansion",
    "MSH3": "MutS homolog 3 — mismatch repair, drives somatic CAG expansion",
    "PMS1": "DNA mismatch repair — genetic modifier of HD onset",
    "PPARGC1A": "PGC-1alpha — mitochondrial biogenesis, impaired in HD",
    "NFkB": "NF-kB pathway — neuroinflammation in HD",
    "mTOR": "mTOR pathway — autophagy regulation, mutant HTT clearance",
    "SIRT1": "Sirtuin 1 — neuroprotection, metabolic regulation in HD",
}

# Known drugs with reported activity at HD targets (from literature)
KNOWN_REPURPOSING_CANDIDATES = [
    {"drug": "Valproic acid", "target": "HDAC", "status": "Tested in HD trials, mixed results", "mechanism": "HDAC inhibitor"},
    {"drug": "Vorinostat (SAHA)", "target": "HDAC", "status": "Preclinical HD data", "mechanism": "HDAC inhibitor"},
    {"drug": "Simvastatin", "target": "BDNF", "status": "Preclinical — increases BDNF", "mechanism": "HMG-CoA reductase inhibitor"},
    {"drug": "Pridopidine", "target": "Sigma-1R", "status": "Phase III (Prilenia)", "mechanism": "Sigma-1 receptor agonist"},
    {"drug": "Laquinimod", "target": "NFkB", "status": "Phase II completed", "mechanism": "Immunomodulator"},
    {"drug": "Metformin", "target": "mTOR/AMPK", "status": "Preclinical HD data", "mechanism": "AMPK activator, promotes autophagy"},
    {"drug": "Rapamycin", "target": "mTOR", "status": "Preclinical — clears mutant HTT", "mechanism": "mTOR inhibitor"},
    {"drug": "Resveratrol", "target": "SIRT1", "status": "Preclinical", "mechanism": "SIRT1 activator"},
    {"drug": "Cannabidiol (CBD)", "target": "CB1/CB2", "status": "Early human data", "mechanism": "Cannabinoid modulator"},
    {"drug": "Cyclosporine A", "target": "Calcineurin", "status": "Preclinical HD data", "mechanism": "Immunosuppressant"},
    {"drug": "Riluzole", "target": "Glutamate", "status": "Tested in HD, modest effect", "mechanism": "Glutamate release inhibitor"},
    {"drug": "Bevantolol (SOM3355)", "target": "Chorea", "status": "Phase II (SOM Biotech, AI-discovered)", "mechanism": "Beta-blocker repurposed via AI"},
]


def search_opentargets(target: str) -> list[dict]:
    """Query Open Targets for drugs associated with a target (simplified)."""
    # Open Targets GraphQL API
    query = """
    query searchTarget($q: String!) {
      search(queryString: $q, entityNames: ["target"], page: {size: 5}) {
        hits {
          id
          name
          description
        }
      }
    }
    """
    try:
        resp = requests.post(
            "https://api.platform.opentargets.org/api/v4/graphql",
            json={"query": query, "variables": {"q": target}},
            timeout=15,
        )
        if resp.ok:
            return resp.json().get("data", {}).get("search", {}).get("hits", [])
    except Exception:
        pass
    return []


def generate_hypotheses(papers_summary: str = "") -> list[dict]:
    """Use LLM to generate novel drug repurposing hypotheses for HD."""
    targets_str = "\n".join(f"- {name}: {desc}" for name, desc in HD_TARGETS.items())
    known_str = "\n".join(f"- {d['drug']} → {d['target']} ({d['status']})" for d in KNOWN_REPURPOSING_CANDIDATES)

    prompt = f"""You are a computational pharmacology expert specializing in Huntington's disease.

Known HD molecular targets:
{targets_str}

Known repurposing candidates already under investigation:
{known_str}

{f"Recent paper findings: {papers_summary}" if papers_summary else ""}

Generate 5 NEW drug repurposing hypotheses for Huntington's disease. For each:
- Choose an FDA-approved drug NOT in the known candidates list
- Identify which HD target(s) it could act on
- Explain the mechanistic rationale
- Rate confidence (high/medium/low)
- Cite any supporting evidence if known

Return JSON array:
[
  {{
    "drug": "drug name",
    "original_indication": "what it's approved for",
    "hd_target": "which HD target",
    "mechanism": "how it could help in HD",
    "confidence": "high|medium|low",
    "rationale": "2-3 sentence scientific rationale",
    "next_step": "what experiment would test this"
  }}
]"""

    return ask_json(prompt, system="You are a drug repurposing AI for neurodegenerative diseases. Be scientifically rigorous.")


def run(papers_summary: str = ""):
    """Display known candidates and generate new hypotheses."""
    console.print(f"\n[bold blue]HD Drug Repurposing Scanner[/bold blue]\n")

    # Show known candidates
    table = Table(title="Known Repurposing Candidates")
    table.add_column("Drug", style="cyan")
    table.add_column("Target", style="green")
    table.add_column("Mechanism", style="white")
    table.add_column("Status", style="yellow")

    for d in KNOWN_REPURPOSING_CANDIDATES:
        table.add_row(d["drug"], d["target"], d["mechanism"], d["status"])
    console.print(table)

    # Generate new hypotheses
    console.print(f"\n[bold]Generating novel repurposing hypotheses with LLM...[/bold]\n")
    try:
        hypotheses = generate_hypotheses(papers_summary)
        if isinstance(hypotheses, list):
            table2 = Table(title="AI-Generated Repurposing Hypotheses")
            table2.add_column("Drug", style="cyan")
            table2.add_column("Original Use", style="dim")
            table2.add_column("HD Target", style="green")
            table2.add_column("Confidence", style="yellow")
            table2.add_column("Rationale", style="white", max_width=50)

            for h in hypotheses:
                conf = h.get("confidence", "?")
                color = "green" if conf == "high" else "yellow" if conf == "medium" else "red"
                table2.add_row(
                    h.get("drug", "?"),
                    h.get("original_indication", "?")[:30],
                    h.get("hd_target", "?"),
                    f"[{color}]{conf}[/{color}]",
                    h.get("rationale", "")[:50],
                )
            console.print(table2)

            for h in hypotheses:
                console.print(f"\n  [cyan]{h.get('drug', '?')}[/cyan] → {h.get('hd_target', '?')}")
                console.print(f"  [white]{h.get('rationale', '')}[/white]")
                console.print(f"  [dim]Next step: {h.get('next_step', 'N/A')}[/dim]")

            return hypotheses
    except Exception as e:
        console.print(f"[red]LLM analysis failed: {e}[/red]")
        console.print("[dim]Make sure Ollama is running (ollama serve) with a model pulled.[/dim]")
        return []


if __name__ == "__main__":
    run()
