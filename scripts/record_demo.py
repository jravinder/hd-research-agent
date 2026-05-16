"""Record a silent screen capture of the HD Research Hub chatbot demo for the
Gemma 4 Good Hackathon submission.

Walks through:
  1. Load chat.html
  2. Ask "How many HD trials are currently recruiting?" → see tools_used badge + cited answer
  3. Ask "What's the top drug-repurposing hypothesis from our experiments?"
  4. Upload a research figure → see vision answer
  5. Upload a "medical image" (a stock MRI) → see guardrail redirect

Saves to media/demo.webm. Convert to mp4 with ffmpeg if needed:
    ffmpeg -i media/demo.webm -c:v libx264 -crf 23 -preset fast media/demo.mp4

Usage:
    python3 scripts/record_demo.py [URL]
    URL defaults to https://hd-research-agent.vercel.app/chat.html
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


REPO = Path(__file__).resolve().parent.parent
MEDIA = REPO / "media"
MEDIA.mkdir(exist_ok=True)


def find_demo_image() -> Path | None:
    """Pick a research-figure image to upload. Prefer a real one in the repo."""
    candidates = [
        REPO / "media" / "demo_figure.png",
        REPO / "media" / "sample_figure.png",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def find_medical_image() -> Path | None:
    candidates = [
        REPO / "media" / "demo_medical.png",
        REPO / "media" / "sample_mri.png",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "https://hd-research-agent.vercel.app/chat.html"
    figure = find_demo_image()
    medical = find_medical_image()
    print(f"recording: {url}")
    print(f"  research figure: {figure or 'none — multimodal scene will be skipped'}")
    print(f"  medical image:   {medical or 'none — guardrail scene will be skipped'}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=str(MEDIA),
            record_video_size={"width": 1280, "height": 800},
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2500)

        # Scene 1: function-calling agentic question
        page.fill("#chat-input", "How many HD trials are currently recruiting? Cite sources.")
        page.click("#send-btn")
        page.wait_for_selector("#typing", state="detached", timeout=180000)
        page.wait_for_timeout(2500)

        # Scene 2: experiment hypotheses
        page.fill("#chat-input",
                  "What's the top drug-repurposing hypothesis from our experiments, and which HD target does it act on?")
        page.click("#send-btn")
        page.wait_for_selector("#typing", state="detached", timeout=180000)
        page.wait_for_timeout(2500)

        # Scene 3: multimodal figure upload
        if figure:
            page.set_input_files("#chat-image", str(figure))
            page.wait_for_timeout(800)
            page.fill("#chat-input", "What does this figure show? Extract any quantitative findings.")
            page.click("#send-btn")
            page.wait_for_selector("#typing", state="detached", timeout=180000)
            page.wait_for_timeout(2500)

        # Scene 4a: guardrail on a personal medical image (if provided)
        if medical:
            page.set_input_files("#chat-image", str(medical))
            page.wait_for_timeout(800)
            page.fill("#chat-input", "Can you read this and tell me if it's bad?")
            page.click("#send-btn")
            page.wait_for_selector("#typing", state="detached", timeout=180000)
            page.wait_for_timeout(2500)

        # Scene 4b: text medical-advice guardrail — always show this so the
        # video makes the safety stance visible.
        page.fill("#chat-input",
                  "Should I take tominersen for my Huntington's? What dose would you recommend?")
        page.click("#send-btn")
        page.wait_for_selector("#typing", state="detached", timeout=30000)
        page.wait_for_timeout(3000)

        # Final beat for visual breathing room
        page.wait_for_timeout(1500)
        context.close()
        browser.close()

    # Find the recorded webm (Playwright names it with a hash)
    webms = sorted(MEDIA.glob("*.webm"), key=lambda p: p.stat().st_mtime, reverse=True)
    if webms:
        target = MEDIA / "demo.webm"
        webms[0].rename(target)
        print(f"saved: {target}")
    else:
        print("WARNING: no video file produced")


if __name__ == "__main__":
    main()
