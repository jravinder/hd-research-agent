"""Upstash Vector - serverless vector search for production (Vercel-compatible).

Alternative to local Redis Stack. Works from Vercel serverless functions.
Uses Upstash Vector with nomic-embed-text embeddings via Ollama.

Setup:
  1. Create index at console.upstash.com/vector (768 dim, cosine)
  2. Set UPSTASH_VECTOR_URL and UPSTASH_VECTOR_TOKEN env vars
  3. Run: python vector_upstash.py --build
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).parent.parent
KB_FILE = ROOT / "data" / "knowledge_base.json"

OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")

UPSTASH_URL = os.environ.get("UPSTASH_VECTOR_URL", "")
UPSTASH_TOKEN = os.environ.get("UPSTASH_VECTOR_TOKEN", "")


def get_embedding(text, model=EMBED_MODEL):
    """Get embedding from Ollama."""
    resp = requests.post(
        f"{OLLAMA_BASE}/api/embed",
        json={"model": model, "input": text},
        timeout=30,
    )
    resp.raise_for_status()
    embeddings = resp.json().get("embeddings", [])
    return embeddings[0] if embeddings else None


def get_upstash_client():
    """Get Upstash Vector client."""
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        print("Set UPSTASH_VECTOR_URL and UPSTASH_VECTOR_TOKEN env vars")
        sys.exit(1)

    from upstash_vector import Index
    return Index(url=UPSTASH_URL, token=UPSTASH_TOKEN)


def build():
    """Embed all KB chunks and upsert to Upstash Vector."""
    print(f"\n{'='*50}")
    print(f"  Upstash Vector Builder")
    print(f"  Embedding: {EMBED_MODEL}")
    print(f"{'='*50}\n")

    if not KB_FILE.exists():
        print("No knowledge_base.json. Run knowledge_base.py first.")
        return

    with open(KB_FILE) as f:
        kb = json.load(f)

    chunks = kb.get("chunks", [])
    print(f"  Chunks: {len(chunks)}")

    index = get_upstash_client()

    batch_size = 50
    total = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        vectors = []

        for j, chunk in enumerate(batch):
            idx = i + j
            text = chunk.get("text", "")
            title = chunk.get("title", "")
            embed_text = f"{title}. {chunk.get('section', '')}. {text[:500]}"

            try:
                embedding = get_embedding(embed_text)
                if embedding:
                    vectors.append({
                        "id": str(idx),
                        "vector": embedding,
                        "metadata": {
                            "pmid": chunk.get("pmid", ""),
                            "title": title[:200],
                            "section": chunk.get("section", ""),
                            "text": text[:1500],
                        },
                    })
            except Exception as e:
                print(f"  Embed error on {idx}: {e}")

            time.sleep(0.03)

        if vectors:
            try:
                index.upsert(vectors=vectors)
                total += len(vectors)
                print(f"  Upserted {total}/{len(chunks)}")
            except Exception as e:
                print(f"  Upsert error: {e}")

    print(f"\n  Done. {total} vectors in Upstash.")


def search(query, top_k=5):
    """Semantic search via Upstash Vector."""
    embedding = get_embedding(query)
    if not embedding:
        return []

    index = get_upstash_client()
    results = index.query(vector=embedding, top_k=top_k, include_metadata=True)

    return [
        {
            "pmid": r.metadata.get("pmid", "") if r.metadata else "",
            "title": r.metadata.get("title", "") if r.metadata else "",
            "section": r.metadata.get("section", "") if r.metadata else "",
            "text": r.metadata.get("text", "") if r.metadata else "",
            "score": r.score,
        }
        for r in results
    ]


def search_rest(query_embedding, top_k=5):
    """Search via REST API (for Vercel serverless, no upstash-vector needed)."""
    resp = requests.post(
        f"{UPSTASH_URL}/query",
        headers={
            "Authorization": f"Bearer {UPSTASH_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "vector": query_embedding,
            "topK": top_k,
            "includeMetadata": True,
        },
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json().get("result", [])

    return [
        {
            "pmid": r.get("metadata", {}).get("pmid", ""),
            "title": r.get("metadata", {}).get("title", ""),
            "section": r.get("metadata", {}).get("section", ""),
            "text": r.get("metadata", {}).get("text", ""),
            "score": r.get("score", 0),
        }
        for r in results
    ]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--search", type=str)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    if args.build:
        build()
    elif args.search:
        results = search(args.search, top_k=args.top_k)
        for r in results:
            print(f"\n[{r['pmid']}] {r['title'][:60]}")
            print(f"  Section: {r['section']}")
            print(f"  Score: {r['score']:.4f}")
            print(f"  {r['text'][:150]}...")
