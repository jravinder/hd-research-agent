# Issue Backlog

Local issue list created because GitHub issue creation is currently blocked by an invalid `gh` auth token on this machine.

## 1. Split publishable artifacts from local-only research state

- Problem: `data/` mixes site inputs, durable agent outputs, and large machine-local artifacts.
- Impact: noisy git status, accidental commits, unclear deploy surface.
- Suggested scope:
  - define which generated files are intended for version control
  - move local-only artifacts behind `.gitignore` or into a separate cache directory
  - document the policy in the README

## 2. Add a real environment/setup guide

- Problem: the README under-specifies required services and optional components.
- Impact: a fresh machine cannot reliably run the repo without reading source files.
- Suggested scope:
  - document Ollama, Redis Stack, Upstash Vector, and the `last30days` skill dependency
  - add “minimum setup” versus “full research stack”
  - include expected generated files and commands

## 3. Add regression checks around builders and automation

- Problem: the repo has no tests for the site builder, knowledge-base builder, or publish path.
- Impact: workflow regressions land silently.
- Suggested scope:
  - add unit tests for HTML escaping/sanitization helpers
  - add tests for PMC section parsing and chunking
  - add a small smoke test for `run_all.py` publish gating

## 4. Fix PMC full-text parsing duplication

- Problem: nested PMC sections currently duplicate subsection paragraphs into parent sections.
- Impact: duplicated KB chunks and biased retrieval.
- Suggested scope:
  - parse only direct child paragraphs per section
  - preserve subsection boundaries without double-counting text

