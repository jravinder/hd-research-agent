"""Run All Agents — orchestrates the full agent pipeline.

Usage:
  python run_all.py              # Run all agents
  python run_all.py --scout      # Paper scout only
  python run_all.py --refine     # Hypothesis refiner only
  python run_all.py --digest     # Digest writer only
  python run_all.py --publish    # Commit + push after running

Designed to run from cron/launchd on Mac or Jetson.
Ollama must be available (local or Jetson).
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


def run_agent(name, script):
    print(f"\n{'='*50}")
    print(f"  Running: {name}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(script.parent),
        capture_output=False,
        timeout=600,  # 10 min max per agent
    )
    return result.returncode == 0


def publish():
    """Commit and push all changes."""
    import os
    os.chdir(ROOT)
    subprocess.run(["git", "add", "data/", "index.html"], check=False)
    result = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if result.returncode != 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(["git", "commit", "-m", f"Agent run: {now} — new papers, refined hypotheses"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("\nPublished to GitHub → Vercel auto-deploy triggered.")
    else:
        print("\nNo changes to publish.")


def main():
    parser = argparse.ArgumentParser(description="HD Research Agent Runner")
    parser.add_argument("--scout", action="store_true", help="Run paper scout only")
    parser.add_argument("--refine", action="store_true", help="Run hypothesis refiner only")
    parser.add_argument("--digest", action="store_true", help="Run digest writer only")
    parser.add_argument("--publish", action="store_true", help="Git commit + push after running")
    args = parser.parse_args()

    agents_dir = Path(__file__).parent
    run_all = not (args.scout or args.refine or args.digest)

    results = {}

    if run_all or args.scout:
        results["Paper Scout"] = run_agent("Paper Scout", agents_dir / "paper_scout.py")

    if run_all or args.refine:
        results["Hypothesis Refiner"] = run_agent("Hypothesis Refiner", agents_dir / "hypothesis_refiner.py")

    if run_all or args.digest:
        results["Digest Writer"] = run_agent("Digest Writer", agents_dir / "digest_writer.py")

    # Also rebuild the site with fresh data
    if run_all:
        print("\nRebuilding site...")
        subprocess.run([sys.executable, str(ROOT / "src" / "build_site.py"), "--no-deploy"], check=False)

    # Summary
    print(f"\n{'='*50}")
    print(f"  Agent Run Summary — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    for name, ok in results.items():
        status = "OK" if ok else "FAILED"
        print(f"    {name}: {status}")
    print(f"{'='*50}\n")

    if args.publish or run_all:
        publish()


if __name__ == "__main__":
    main()
