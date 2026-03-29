"""Knowledge Base Builder - pulls full text from PMC, chunks it, builds searchable KB.

Goes beyond abstracts. For papers available on PubMed Central (open access),
downloads the full text, splits into semantic chunks, and indexes for RAG.

The chatbot uses this for grounded, detailed answers with section-level citations.
"""

import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
KB_FILE = DATA_DIR / "knowledge_base.json"
CORPUS_FILE = DATA_DIR / "corpus.json"

PMC_ID_CONV = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
PMC_FETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def get_pmc_ids(pmids):
    """Convert PMIDs to PMCIDs (only open access papers have these)."""
    pmc_map = {}
    batch_size = 20
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i:i+batch_size]
        try:
            resp = requests.get(PMC_ID_CONV, params={
                "ids": ",".join(batch), "format": "json"
            }, timeout=15)
            if resp.ok:
                for rec in resp.json().get("records", []):
                    if rec.get("pmcid"):
                        pmc_map[rec.get("pmid", "")] = rec["pmcid"]
        except Exception as e:
            print(f"  ID conversion error: {e}")
        time.sleep(0.5)
    return pmc_map


def fetch_full_text(pmcid):
    """Fetch full text XML from PMC."""
    try:
        resp = requests.get(PMC_FETCH, params={
            "db": "pmc", "id": pmcid, "retmode": "xml"
        }, timeout=30)
        if resp.ok:
            return resp.text
    except Exception as e:
        print(f"  Fetch error for {pmcid}: {e}")
    return None


def parse_pmc_xml(xml_text):
    """Parse PMC XML into sections with text."""
    sections = []
    try:
        root = ET.fromstring(xml_text)
        body = root.find(".//body")
        if body is None:
            return sections

        for sec in body.findall(".//sec"):
            title_el = sec.find("title")
            title = title_el.text if title_el is not None and title_el.text else "Untitled"

            paragraphs = []
            for p in sec.findall(".//p"):
                text = ET.tostring(p, encoding="unicode", method="text").strip()
                if text and len(text) > 50:
                    paragraphs.append(text)

            if paragraphs:
                sections.append({
                    "section": title,
                    "text": "\n\n".join(paragraphs),
                    "char_count": sum(len(p) for p in paragraphs),
                })
    except ET.ParseError:
        pass
    return sections


def chunk_sections(sections, max_chunk=1500):
    """Split long sections into smaller chunks for RAG."""
    chunks = []
    for sec in sections:
        text = sec["text"]
        section_name = sec["section"]

        if len(text) <= max_chunk:
            chunks.append({
                "section": section_name,
                "text": text,
            })
        else:
            # Split by paragraphs
            paragraphs = text.split("\n\n")
            current_chunk = ""
            for para in paragraphs:
                if len(current_chunk) + len(para) > max_chunk and current_chunk:
                    chunks.append({
                        "section": section_name,
                        "text": current_chunk.strip(),
                    })
                    current_chunk = para
                else:
                    current_chunk += "\n\n" + para if current_chunk else para

            if current_chunk.strip():
                chunks.append({
                    "section": section_name,
                    "text": current_chunk.strip(),
                })
    return chunks


def build_kb():
    """Build the full knowledge base from corpus + PMC full texts."""
    print(f"\n{'='*50}")
    print(f"  Knowledge Base Builder")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    # Load corpus
    if not CORPUS_FILE.exists():
        print("No corpus.json found. Run paper_scout first.")
        return

    with open(CORPUS_FILE) as f:
        corpus = json.load(f)

    papers = corpus.get("papers", {})
    pmids = list(papers.keys())
    print(f"Corpus: {len(pmids)} papers")

    # Find which have full text on PMC
    print("Checking PMC for full text availability...")
    pmc_map = get_pmc_ids(pmids)
    print(f"Full text available: {len(pmc_map)}/{len(pmids)}")

    # Load existing KB or start fresh
    kb = {"papers": {}, "chunks": [], "built": None, "stats": {}}

    total_chunks = 0
    total_chars = 0

    for pmid, pmcid in pmc_map.items():
        paper_info = papers.get(pmid, {})
        title = paper_info.get("title", "")[:80]
        print(f"\n  [{pmcid}] {title}")

        # Fetch full text
        xml_text = fetch_full_text(pmcid)
        if not xml_text:
            print("    No XML returned")
            continue

        # Parse sections
        sections = parse_pmc_xml(xml_text)
        if not sections:
            print("    No sections parsed")
            continue

        # Chunk
        chunks = chunk_sections(sections)
        print(f"    {len(sections)} sections -> {len(chunks)} chunks")

        # Store
        kb["papers"][pmid] = {
            "pmid": pmid,
            "pmcid": pmcid,
            "title": paper_info.get("title", ""),
            "journal": paper_info.get("journal", ""),
            "date": paper_info.get("date", ""),
            "sections": [s["section"] for s in sections],
            "chunk_count": len(chunks),
        }

        for chunk in chunks:
            kb["chunks"].append({
                "pmid": pmid,
                "pmcid": pmcid,
                "section": chunk["section"],
                "text": chunk["text"],
                "title": paper_info.get("title", ""),
            })

        total_chunks += len(chunks)
        total_chars += sum(len(c["text"]) for c in chunks)

        time.sleep(1)  # Rate limit PMC

    # Also include abstracts for papers without full text
    print("\nAdding abstracts for papers without full text...")
    for pmid, paper in papers.items():
        if pmid not in pmc_map and paper.get("abstract"):
            kb["chunks"].append({
                "pmid": pmid,
                "pmcid": None,
                "section": "Abstract",
                "text": paper["abstract"],
                "title": paper.get("title", ""),
            })
            total_chunks += 1
            total_chars += len(paper.get("abstract", ""))

    kb["built"] = datetime.now().isoformat()
    kb["stats"] = {
        "total_papers": len(pmids),
        "full_text_papers": len(pmc_map),
        "abstract_only_papers": len(pmids) - len(pmc_map),
        "total_chunks": total_chunks,
        "total_characters": total_chars,
    }

    # Save
    with open(KB_FILE, "w") as f:
        json.dump(kb, f, indent=2, default=str)

    print(f"\n{'='*50}")
    print(f"  Knowledge Base built:")
    print(f"  Full text papers: {len(pmc_map)}")
    print(f"  Abstract-only: {len(pmids) - len(pmc_map)}")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Total characters: {total_chars:,}")
    print(f"  Saved to: {KB_FILE}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    build_kb()
