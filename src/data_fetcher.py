"""Data Fetcher — pulls fresh HD data from all public sources and writes data.json.

Sources:
  - PubMed (papers)
  - ClinicalTrials.gov (active trials)
  - HDBuzz RSS (community news)
  - HDSA pipeline page
  - Open Targets (drug-target associations)

Runs on schedule. Output: data/data.json consumed by the landing page.
"""

import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

import requests

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_FILE = DATA_DIR / "data.json"

PUBMED_SEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
CT_API = "https://clinicaltrials.gov/api/v2/studies"
HDBUZZ_RSS = "https://en.hdbuzz.net/feed"


def fetch_pubmed(query="huntington disease treatment OR huntington disease gene therapy", days=30, max_results=20):
    """Fetch recent HD papers from PubMed."""
    print(f"  PubMed: searching '{query}' (last {days} days)...")
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
    try:
        resp = requests.get(PUBMED_SEARCH, params=params, timeout=30)
        resp.raise_for_status()
        pmids = resp.json().get("esearchresult", {}).get("idlist", [])
        print(f"  PubMed: found {len(pmids)} papers")

        if not pmids:
            return []

        # Fetch details
        resp2 = requests.get(PUBMED_FETCH, params={
            "db": "pubmed", "id": ",".join(pmids), "retmode": "xml"
        }, timeout=60)
        resp2.raise_for_status()

        root = ET.fromstring(resp2.text)
        papers = []
        for article in root.findall(".//PubmedArticle"):
            medline = article.find(".//MedlineCitation")
            art = medline.find(".//Article")
            pmid = medline.findtext(".//PMID", "")
            title = art.findtext(".//ArticleTitle", "")
            abstract_parts = art.findall(".//Abstract/AbstractText")
            abstract = " ".join(t.text or "" for t in abstract_parts)[:500]
            journal = art.findtext(".//Journal/Title", "")

            pub_date_el = art.find(".//Journal/JournalIssue/PubDate")
            pub_date = ""
            if pub_date_el is not None:
                year = pub_date_el.findtext("Year", "")
                month = pub_date_el.findtext("Month", "")
                pub_date = f"{year} {month}".strip()

            author_list = art.findall(".//AuthorList/Author")
            authors = ", ".join(
                f"{a.findtext('LastName', '')} {a.findtext('Initials', '')}"
                for a in author_list[:3]
            )

            papers.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "journal": journal,
                "pub_date": pub_date,
                "authors": authors,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })
        return papers
    except Exception as e:
        print(f"  PubMed ERROR: {e}")
        return []


def fetch_trials(condition="Huntington Disease", max_results=30):
    """Fetch active HD clinical trials from ClinicalTrials.gov."""
    print(f"  ClinicalTrials.gov: searching '{condition}'...")
    params = {
        "query.cond": condition,
        "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING,ENROLLING_BY_INVITATION",
        "pageSize": max_results,
        "format": "json",
    }
    try:
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
            enrollment_info = design.get("enrollmentInfo", {})
            enrollment = enrollment_info.get("count", 0) if isinstance(enrollment_info, dict) else 0

            nct_id = ident.get("nctId", "")
            trials.append({
                "nct_id": nct_id,
                "title": ident.get("briefTitle", ""),
                "status": status_mod.get("overallStatus", ""),
                "phase": ", ".join(phases) if phases else "N/A",
                "sponsor": sponsor_mod.get("leadSponsor", {}).get("name", ""),
                "intervention": "; ".join(intervention_names),
                "enrollment": enrollment,
                "url": f"https://clinicaltrials.gov/study/{nct_id}",
                "start_date": status_mod.get("startDateStruct", {}).get("date", ""),
            })

        print(f"  ClinicalTrials.gov: found {len(trials)} active trials")
        return trials
    except Exception as e:
        print(f"  ClinicalTrials.gov ERROR: {e}")
        return []


def fetch_hdbuzz():
    """Fetch latest articles from HDBuzz RSS feed."""
    print("  HDBuzz: fetching RSS feed...")
    try:
        resp = requests.get(HDBUZZ_RSS, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.text)

        articles = []
        for item in root.findall(".//item")[:10]:
            articles.append({
                "title": item.findtext("title", ""),
                "link": item.findtext("link", ""),
                "pub_date": item.findtext("pubDate", ""),
                "description": (item.findtext("description", "") or "")[:300],
            })
        print(f"  HDBuzz: found {len(articles)} articles")
        return articles
    except Exception as e:
        print(f"  HDBuzz ERROR: {e}")
        return []


def fetch_open_targets():
    """Fetch HD-associated targets from Open Targets."""
    print("  Open Targets: fetching HD disease associations...")
    query = """
    query {
      disease(efoId: "MONDO_0007739") {
        name
        associatedTargets(page: {size: 20}) {
          rows {
            target { approvedSymbol approvedName }
            score
          }
        }
      }
    }
    """
    try:
        resp = requests.post(
            "https://api.platform.opentargets.org/api/v4/graphql",
            json={"query": query},
            timeout=15,
        )
        if resp.ok:
            data = resp.json().get("data", {}).get("disease", {})
            rows = data.get("associatedTargets", {}).get("rows", [])
            targets = []
            for r in rows:
                t = r.get("target", {})
                targets.append({
                    "symbol": t.get("approvedSymbol", ""),
                    "name": t.get("approvedName", ""),
                    "score": round(r.get("score", 0), 3),
                })
            print(f"  Open Targets: found {len(targets)} associated targets")
            return targets
    except Exception as e:
        print(f"  Open Targets ERROR: {e}")
    return []


def run():
    """Fetch all sources and write data.json."""
    print(f"\n{'='*50}")
    print(f"HD Data Fetcher — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    data = {
        "last_updated": datetime.now().isoformat(),
        "papers": fetch_pubmed(),
        "trials": fetch_trials(),
        "hdbuzz": fetch_hdbuzz(),
        "targets": fetch_open_targets(),
    }

    # Summary stats
    data["stats"] = {
        "papers_count": len(data["papers"]),
        "trials_count": len(data["trials"]),
        "hdbuzz_count": len(data["hdbuzz"]),
        "targets_count": len(data["targets"]),
        "total_enrollment": sum(t.get("enrollment", 0) for t in data["trials"]),
        "recruiting_count": sum(1 for t in data["trials"] if t.get("status") == "RECRUITING"),
    }

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"\n{'='*50}")
    print(f"Results saved to {DATA_FILE}")
    print(f"  Papers: {data['stats']['papers_count']}")
    print(f"  Trials: {data['stats']['trials_count']} ({data['stats']['recruiting_count']} recruiting)")
    print(f"  HDBuzz articles: {data['stats']['hdbuzz_count']}")
    print(f"  Targets: {data['stats']['targets_count']}")
    print(f"  Total patients enrolled: {data['stats']['total_enrollment']}")
    print(f"{'='*50}\n")

    return data


if __name__ == "__main__":
    run()
