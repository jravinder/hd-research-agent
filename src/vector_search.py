"""Vector Search - embeds knowledge base chunks and indexes in Redis for semantic RAG.

Uses nomic-embed-text via Ollama for embeddings (768 dimensions).
Stores in Redis Stack with RediSearch HNSW index for sub-100ms search.

Flow:
  1. Load knowledge_base.json chunks
  2. Embed each chunk via Ollama
  3. Store in Redis with vector index
  4. Search: embed query → find nearest neighbors → return chunks
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

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
INDEX_NAME = "hd_research"
PREFIX = "chunk:"
VECTOR_DIM = 768  # nomic-embed-text dimension


def get_embedding(text, model=EMBED_MODEL):
    """Get embedding vector from Ollama."""
    resp = requests.post(
        f"{OLLAMA_BASE}/api/embed",
        json={"model": model, "input": text},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    # Ollama returns {"embeddings": [[...]]}
    embeddings = data.get("embeddings", [])
    if embeddings:
        return embeddings[0]
    return None


def connect_redis():
    """Connect to Redis."""
    try:
        import redis
        r = redis.from_url(REDIS_URL, decode_responses=False)
        r.ping()
        return r
    except ImportError:
        print("redis-py not installed. Run: pip install redis")
        sys.exit(1)
    except Exception as e:
        print(f"Redis connection failed: {e}")
        print("Make sure Redis Stack is running: redis-stack-server")
        sys.exit(1)


def create_index(r):
    """Create RediSearch vector index."""
    from redis.commands.search.field import VectorField, TextField, TagField
    from redis.commands.search.index_definition import IndexDefinition, IndexType

    try:
        r.ft(INDEX_NAME).info()
        print(f"  Index '{INDEX_NAME}' already exists")
        return
    except Exception:
        pass

    schema = (
        TextField("title"),
        TextField("section"),
        TextField("text"),
        TagField("pmid"),
        VectorField(
            "embedding",
            "HNSW",
            {
                "TYPE": "FLOAT32",
                "DIM": VECTOR_DIM,
                "DISTANCE_METRIC": "COSINE",
                "M": 16,
                "EF_CONSTRUCTION": 200,
            },
        ),
    )

    definition = IndexDefinition(prefix=[PREFIX], index_type=IndexType.HASH)
    r.ft(INDEX_NAME).create_index(schema, definition=definition)
    print(f"  Created index '{INDEX_NAME}'")


def index_chunks(r, chunks):
    """Embed and store all chunks in Redis."""
    import numpy as np

    total = len(chunks)
    indexed = 0
    failed = 0

    for i, chunk in enumerate(chunks):
        key = f"{PREFIX}{i}"
        text = chunk.get("text", "")
        title = chunk.get("title", "")

        # Create embedding text (title + section + content for better matching)
        embed_text = f"{title}. {chunk.get('section', '')}. {text[:500]}"

        try:
            embedding = get_embedding(embed_text)
            if embedding is None:
                failed += 1
                continue

            vec = np.array(embedding, dtype=np.float32).tobytes()

            r.hset(key, mapping={
                "title": title,
                "section": chunk.get("section", ""),
                "text": text,
                "pmid": chunk.get("pmid", ""),
                "embedding": vec,
            })
            indexed += 1

            if (i + 1) % 50 == 0:
                print(f"  Indexed {i+1}/{total} chunks...")

        except Exception as e:
            failed += 1
            if failed <= 3:
                print(f"  Error on chunk {i}: {e}")

        time.sleep(0.05)  # Rate limit Ollama

    return indexed, failed


def search(query, top_k=5):
    """Semantic search over the knowledge base."""
    import numpy as np
    from redis.commands.search.query import Query

    r = connect_redis()
    embedding = get_embedding(query)
    if embedding is None:
        return []

    vec = np.array(embedding, dtype=np.float32).tobytes()

    q = (
        Query(f"*=>[KNN {top_k} @embedding $vec AS score]")
        .sort_by("score")
        .return_fields("title", "section", "text", "pmid", "score")
        .paging(0, top_k)
        .dialect(2)
    )

    results = r.ft(INDEX_NAME).search(q, query_params={"vec": vec})

    chunks = []
    for doc in results.docs:
        chunks.append({
            "pmid": doc.pmid.decode() if isinstance(doc.pmid, bytes) else doc.pmid,
            "title": doc.title.decode() if isinstance(doc.title, bytes) else doc.title,
            "section": doc.section.decode() if isinstance(doc.section, bytes) else doc.section,
            "text": doc.text.decode() if isinstance(doc.text, bytes) else doc.text,
            "score": float(doc.score),
        })

    return chunks


def build():
    """Build the vector index from knowledge base."""
    print(f"\n{'='*50}")
    print(f"  Vector Search Builder")
    print(f"  Model: {EMBED_MODEL}")
    print(f"  Redis: {REDIS_URL}")
    print(f"{'='*50}\n")

    # Load KB
    if not KB_FILE.exists():
        print("No knowledge_base.json. Run knowledge_base.py first.")
        return

    with open(KB_FILE) as f:
        kb = json.load(f)

    chunks = kb.get("chunks", [])
    print(f"  Chunks to index: {len(chunks)}")

    # Connect to Redis
    r = connect_redis()
    print("  Redis connected")

    # Create index
    create_index(r)

    # Index chunks
    print(f"\n  Embedding and indexing {len(chunks)} chunks...")
    start = time.time()
    indexed, failed = index_chunks(r, chunks)
    elapsed = time.time() - start

    print(f"\n{'='*50}")
    print(f"  Indexed: {indexed}")
    print(f"  Failed: {failed}")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Speed: {indexed/elapsed:.1f} chunks/sec")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="Build the vector index")
    parser.add_argument("--search", type=str, help="Search query")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results")
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
    else:
        parser.print_help()
