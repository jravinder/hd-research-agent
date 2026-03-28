"""Social Watcher Agent — monitors X, Reddit, HN, YouTube for HD research chatter.

Uses the last30days skill's research engine to scan social platforms
for Huntington's disease discussions. Runs daily, saves findings to
data/social_feed.json, and flags anything significant.

Watches for:
- New trial results or FDA decisions
- Drug repurposing discussions
- Patient community sentiment
- AI + HD research mentions
- Breakthrough announcements
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SKILL_ROOT = Path.home() / ".claude" / "skills" / "last30days"
FEED_FILE = ROOT / "data" / "social_feed.json"

# Topics to monitor — each gets a separate scan
WATCHLIST = [
    {
        "id": "hd_treatment",
        "query": "huntingtons disease treatment",
        "why": "Core treatment news — trials, approvals, setbacks",
    },
    {
        "id": "amt130",
        "query": "AMT-130 uniQure huntingtons",
        "why": "The most advanced HD therapy — track FDA progress",
    },
    {
        "id": "hd_ai",
        "query": "huntingtons disease AI drug discovery",
        "why": "AI + HD intersection — our unique angle",
    },
    {
        "id": "hd_gene_therapy",
        "query": "huntingtons gene therapy CRISPR",
        "why": "Gene therapy approaches beyond AMT-130",
    },
    {
        "id": "hd_community",
        "query": "huntingtons disease family support",
        "why": "Patient community — what people are feeling and needing",
    },
]


def load_feed():
    if FEED_FILE.exists():
        with open(FEED_FILE) as f:
            return json.load(f)
    return {"scans": [], "last_run": None, "total_runs": 0, "alerts": []}


def save_feed(feed):
    FEED_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(FEED_FILE, "w") as f:
        json.dump(feed, f, indent=2, default=str)


def run_last30days(query, days=7):
    """Run the last30days research script and capture output."""
    script = SKILL_ROOT / "scripts" / "last30days.py"
    if not script.exists():
        print(f"  last30days skill not found at {script}")
        return None

    cmd = [
        sys.executable, str(script),
        query,
        "--emit=compact",
        "--no-native-web",
        f"--days={days}",
        "--quick",
        f"--save-dir={ROOT / 'data' / 'social_raw'}",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(SKILL_ROOT),
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        print(f"  Timed out searching: {query}")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None


def parse_results(output):
    """Extract key stats from last30days output."""
    if not output:
        return {"x_posts": 0, "reddit_threads": 0, "youtube_videos": 0, "hn_stories": 0}

    stats = {
        "x_posts": 0,
        "reddit_threads": 0,
        "youtube_videos": 0,
        "hn_stories": 0,
        "highlights": [],
    }

    for line in output.split("\n"):
        if "X:" in line and "posts" in line:
            try:
                stats["x_posts"] = int(line.split("X:")[1].split("posts")[0].strip())
            except (ValueError, IndexError):
                pass
        if "Reddit:" in line and "threads" in line:
            try:
                stats["reddit_threads"] = int(line.split("Reddit:")[1].split("threads")[0].strip())
            except (ValueError, IndexError):
                pass
        if "YouTube:" in line and "videos" in line:
            try:
                stats["youtube_videos"] = int(line.split("YouTube:")[1].split("videos")[0].strip())
            except (ValueError, IndexError):
                pass
        if "HN:" in line and "stories" in line:
            try:
                stats["hn_stories"] = int(line.split("HN:")[1].split("stories")[0].strip())
            except (ValueError, IndexError):
                pass

        # Capture high-engagement posts
        if "likes" in line.lower() and ("score:" in line.lower() or "**X" in line):
            stats["highlights"].append(line.strip()[:200])

    return stats


def check_alerts(scan_results):
    """Flag significant findings that need attention."""
    alerts = []

    for scan in scan_results:
        stats = scan.get("stats", {})
        query = scan.get("query", "")

        # High volume = something is happening
        total = stats.get("x_posts", 0) + stats.get("reddit_threads", 0)
        if total > 20:
            alerts.append({
                "type": "high_volume",
                "query": query,
                "total": total,
                "message": f"High social volume for '{query}': {total} posts/threads in 7 days",
                "time": datetime.now().isoformat(),
            })

        # Check for breakthrough keywords in highlights
        breakthrough_words = ["approved", "breakthrough", "fda", "phase 3", "phase iii", "cure", "remission", "halted", "withdrawn"]
        for highlight in stats.get("highlights", []):
            if any(word in highlight.lower() for word in breakthrough_words):
                alerts.append({
                    "type": "breakthrough",
                    "query": query,
                    "highlight": highlight[:200],
                    "message": f"Possible breakthrough mention in '{query}'",
                    "time": datetime.now().isoformat(),
                })

    return alerts


def run():
    feed = load_feed()

    print(f"\n{'='*50}")
    print(f"Social Watcher Agent — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Watching {len(WATCHLIST)} topics across X, Reddit, YouTube, HN")
    print(f"{'='*50}\n")

    scan_results = []

    for topic in WATCHLIST:
        print(f"  Scanning: {topic['query']}")
        print(f"    Why: {topic['why']}")

        output = run_last30days(topic["query"], days=7)
        stats = parse_results(output)

        result = {
            "id": topic["id"],
            "query": topic["query"],
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
        }
        scan_results.append(result)

        total = stats["x_posts"] + stats["reddit_threads"] + stats["youtube_videos"] + stats["hn_stories"]
        print(f"    Found: {stats['x_posts']} X, {stats['reddit_threads']} Reddit, {stats['youtube_videos']} YT, {stats['hn_stories']} HN = {total} total")

        if stats["highlights"]:
            print(f"    Top: {stats['highlights'][0][:80]}")
        print()

        time.sleep(5)  # Don't spam APIs

    # Check for alerts
    alerts = check_alerts(scan_results)
    if alerts:
        print(f"\n  ALERTS ({len(alerts)}):")
        for a in alerts:
            print(f"    [{a['type']}] {a['message']}")

    # Save
    feed["scans"].append({
        "timestamp": datetime.now().isoformat(),
        "results": scan_results,
        "alerts": alerts,
    })

    # Keep last 30 days of scans
    feed["scans"] = feed["scans"][-30:]
    feed["last_run"] = datetime.now().isoformat()
    feed["total_runs"] = feed.get("total_runs", 0) + 1
    feed["alerts"].extend(alerts)
    feed["alerts"] = feed["alerts"][-50:]  # Keep last 50 alerts

    save_feed(feed)

    print(f"\n{'='*50}")
    print(f"  Scan complete. {len(scan_results)} topics, {len(alerts)} alerts")
    print(f"  Feed saved to {FEED_FILE}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    run()
