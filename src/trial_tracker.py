"""Trial Tracker — monitors Huntington's disease clinical trials from ClinicalTrials.gov."""

import json
from dataclasses import dataclass
from typing import Optional

import requests
from rich.console import Console
from rich.table import Table

console = Console()

CT_API = "https://clinicaltrials.gov/api/v2/studies"


@dataclass
class Trial:
    nct_id: str
    title: str
    status: str
    phase: str
    sponsor: str
    intervention: str
    start_date: str
    completion_date: str
    enrollment: int


def search_trials(condition: str = "Huntington Disease", status: str = "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION", max_results: int = 50) -> list[Trial]:
    """Search ClinicalTrials.gov for HD trials."""
    params = {
        "query.cond": condition,
        "filter.overallStatus": status,
        "pageSize": max_results,
        "format": "json",
    }

    resp = requests.get(CT_API, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    trials = []
    for study in data.get("studies", []):
        proto = study.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        status_mod = proto.get("statusModule", {})
        design = proto.get("designModule", {})
        sponsor_mod = proto.get("sponsorCollaboratorsModule", {})
        arms = proto.get("armsInterventionsModule", {})

        interventions = arms.get("interventions", [])
        intervention_names = [i.get("name", "") for i in interventions[:3]]

        phases = design.get("phases", [])
        phase_str = ", ".join(phases) if phases else "N/A"

        enrollment_info = design.get("enrollmentInfo", {})
        enrollment = enrollment_info.get("count", 0) if isinstance(enrollment_info, dict) else 0

        trials.append(Trial(
            nct_id=ident.get("nctId", ""),
            title=ident.get("briefTitle", ""),
            status=status_mod.get("overallStatus", ""),
            phase=phase_str,
            sponsor=sponsor_mod.get("leadSponsor", {}).get("name", ""),
            intervention="; ".join(intervention_names),
            start_date=status_mod.get("startDateStruct", {}).get("date", ""),
            completion_date=status_mod.get("completionDateStruct", {}).get("date", ""),
            enrollment=enrollment,
        ))

    return trials


def run():
    """Fetch and display active HD clinical trials."""
    console.print(f"\n[bold blue]HD Trial Tracker[/bold blue]")
    console.print("[dim]Fetching active Huntington's disease trials from ClinicalTrials.gov...[/dim]\n")

    trials = search_trials()
    console.print(f"Found {len(trials)} active trials\n")

    if not trials:
        console.print("[yellow]No active trials found.[/yellow]")
        return []

    # Group by phase
    by_phase = {}
    for t in trials:
        by_phase.setdefault(t.phase, []).append(t)

    for phase in sorted(by_phase.keys()):
        table = Table(title=f"Phase: {phase}")
        table.add_column("NCT ID", style="cyan", width=15)
        table.add_column("Title", style="white", max_width=50)
        table.add_column("Sponsor", style="green", max_width=25)
        table.add_column("Intervention", style="yellow", max_width=30)
        table.add_column("Status", style="magenta", width=12)
        table.add_column("N", style="white", width=6)

        for t in by_phase[phase]:
            table.add_row(
                t.nct_id,
                t.title[:50],
                t.sponsor[:25],
                t.intervention[:30],
                t.status,
                str(t.enrollment),
            )
        console.print(table)
        console.print()

    # Summary stats
    gene_therapy = [t for t in trials if any(kw in t.intervention.lower() for kw in ["gene", "aav", "amt-130"])]
    small_mol = [t for t in trials if any(kw in t.intervention.lower() for kw in ["oral", "tablet", "capsule", "mg"])]
    aso = [t for t in trials if any(kw in t.intervention.lower() for kw in ["antisense", "aso", "oligonucleotide"])]

    console.print(f"[bold]Pipeline Summary:[/bold]")
    console.print(f"  Gene therapies: {len(gene_therapy)}")
    console.print(f"  Small molecules: {len(small_mol)}")
    console.print(f"  Antisense oligos: {len(aso)}")
    console.print(f"  Total patients enrolled: {sum(t.enrollment for t in trials)}")

    return trials


if __name__ == "__main__":
    run()
