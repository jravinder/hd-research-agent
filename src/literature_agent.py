"""Literature Agent — fetches and analyzes recent Huntington's disease papers from PubMed."""

import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional

import requests
from rich.console import Console
from rich.table import Table

from llm import ask, ask_json

console = Console()

PUBMED_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _xml_text(element) -> str:
    """Flatten XML element text, preserving nested tag content."""
    if element is None:
        return ""
    return "".join(element.itertext()).strip()


@dataclass
class Paper:
    pmid: str
    title: str
    abstract: str
    authors: str
    journal: str
    pub_date: str
    keywords: list[str]


def search_pubmed(query: str = "huntington disease", days: int = 30, max_results: int = 20) -> list[str]:
    """Search PubMed and return PMIDs."""
    min_date = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
    max_date = datetime.now().strftime("%Y/%m/%d")

    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "sort": "relevance",
        "datetype": "pdat",
        "mindate": min_date,
        "maxdate": max_date,
        "retmode": "json",
    }
    resp = requests.get(PUBMED_SEARCH, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("esearchresult", {}).get("idlist", [])


def fetch_papers(pmids: list[str]) -> list[Paper]:
    """Fetch paper details from PubMed."""
    if not pmids:
        return []

    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
    }
    resp = requests.get(PUBMED_FETCH, params=params, timeout=60)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    papers = []

    for article in root.findall(".//PubmedArticle"):
        medline = article.find(".//MedlineCitation")
        art = medline.find(".//Article")

        pmid = medline.findtext(".//PMID", "")
        title = _xml_text(art.find(".//ArticleTitle"))
        abstract_parts = art.findall(".//Abstract/AbstractText")
        abstract = " ".join(_xml_text(t) for t in abstract_parts).strip()

        author_list = art.findall(".//AuthorList/Author")
        authors = ", ".join(
            f"{a.findtext('LastName', '')} {a.findtext('Initials', '')}"
            for a in author_list[:5]
        )
        if len(author_list) > 5:
            authors += f" et al. ({len(author_list)} authors)"

        journal = art.findtext(".//Journal/Title", "")

        pub_date_el = art.find(".//Journal/JournalIssue/PubDate")
        if pub_date_el is not None:
            year = pub_date_el.findtext("Year", "")
            month = pub_date_el.findtext("Month", "")
            pub_date = f"{year} {month}".strip()
        else:
            pub_date = ""

        kw_list = medline.findall(".//KeywordList/Keyword")
        keywords = [_xml_text(kw) for kw in kw_list if _xml_text(kw)]

        papers.append(Paper(
            pmid=pmid, title=title, abstract=abstract,
            authors=authors, journal=journal, pub_date=pub_date,
            keywords=keywords,
        ))

    return papers


def analyze_paper(paper: Paper) -> dict:
    """Use LLM to extract structured insights from a paper."""
    prompt = f"""Analyze this Huntington's disease research paper and extract structured information.

Title: {paper.title}
Abstract: {paper.abstract}
Keywords: {', '.join(paper.keywords)}

Return JSON with:
{{
  "category": "gene_therapy|small_molecule|biomarker|mechanism|clinical_trial|review|other",
  "targets": ["list of molecular targets or genes mentioned"],
  "compounds": ["list of drugs or compounds mentioned"],
  "key_finding": "one sentence summary of the main finding",
  "relevance_to_treatment": "high|medium|low",
  "novel_mechanism": true/false,
  "drug_repurposing_potential": true/false
}}"""

    try:
        return ask_json(prompt, system="You are a neuroscience research analyst specializing in Huntington's disease.")
    except Exception as e:
        return {"error": str(e), "key_finding": "Analysis failed"}


def run(query: str = "huntington disease treatment", days: int = 30, max_results: int = 15, analyze: bool = True):
    """Main entry point: search, fetch, and optionally analyze papers."""
    console.print(f"\n[bold blue]HD Literature Agent[/bold blue]")
    console.print(f"Query: {query} | Last {days} days | Max {max_results} papers\n")

    # Search
    console.print("[dim]Searching PubMed...[/dim]")
    pmids = search_pubmed(query, days=days, max_results=max_results)
    console.print(f"Found {len(pmids)} papers")

    if not pmids:
        console.print("[yellow]No papers found. Try broadening the query or date range.[/yellow]")
        return []

    # Fetch
    console.print("[dim]Fetching paper details...[/dim]")
    papers = fetch_papers(pmids)
    console.print(f"Fetched {len(papers)} papers\n")

    # Display
    table = Table(title="Recent HD Papers")
    table.add_column("PMID", style="cyan", width=10)
    table.add_column("Title", style="white", max_width=60)
    table.add_column("Journal", style="green", max_width=25)
    table.add_column("Date", style="yellow", width=10)

    for p in papers:
        table.add_row(p.pmid, p.title[:60], p.journal[:25], p.pub_date)

    console.print(table)

    # Analyze with LLM
    if analyze and papers:
        console.print(f"\n[bold]Analyzing {len(papers)} papers with LLM...[/bold]\n")
        results = []
        for i, paper in enumerate(papers):
            console.print(f"  [{i+1}/{len(papers)}] {paper.title[:50]}...")
            analysis = analyze_paper(paper)
            results.append({"paper": asdict(paper), "analysis": analysis})

            finding = analysis.get("key_finding", "N/A")
            targets = analysis.get("targets", [])
            compounds = analysis.get("compounds", [])
            relevance = analysis.get("relevance_to_treatment", "?")

            console.print(f"    Finding: [white]{finding}[/white]")
            if targets:
                console.print(f"    Targets: [cyan]{', '.join(targets[:5])}[/cyan]")
            if compounds:
                console.print(f"    Compounds: [green]{', '.join(compounds[:5])}[/green]")
            console.print(f"    Relevance: [{'green' if relevance == 'high' else 'yellow'}]{relevance}[/]")
            console.print()

            time.sleep(0.5)  # Rate limit LLM calls

        # Summary
        high_relevance = [r for r in results if r["analysis"].get("relevance_to_treatment") == "high"]
        repurposing = [r for r in results if r["analysis"].get("drug_repurposing_potential")]
        novel = [r for r in results if r["analysis"].get("novel_mechanism")]

        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Total papers analyzed: {len(results)}")
        console.print(f"  High relevance to treatment: {len(high_relevance)}")
        console.print(f"  Drug repurposing potential: {len(repurposing)}")
        console.print(f"  Novel mechanisms: {len(novel)}")

        if repurposing:
            console.print(f"\n[bold green]Drug Repurposing Candidates:[/bold green]")
            for r in repurposing:
                compounds = r["analysis"].get("compounds", [])
                if compounds:
                    console.print(f"  - {', '.join(compounds)} (PMID: {r['paper']['pmid']})")

        return results

    return [{"paper": asdict(p)} for p in papers]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="HD Literature Agent")
    parser.add_argument("--query", default="huntington disease treatment", help="PubMed search query")
    parser.add_argument("--days", type=int, default=30, help="Look back N days")
    parser.add_argument("--max", type=int, default=15, help="Max papers to fetch")
    parser.add_argument("--no-analyze", action="store_true", help="Skip LLM analysis")
    args = parser.parse_args()

    run(query=args.query, days=args.days, max_results=args.max, analyze=not args.no_analyze)
