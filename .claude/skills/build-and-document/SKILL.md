---
name: build-and-document
description: "Use this skill whenever building, modifying, or making an architectural decision on this project - adding graph nodes/edges, writing ingestion code, changing the schema, adding a query capability, or fixing a design flaw. Ensures every real engineering decision gets captured as we go, not reconstructed later from memory."
---

# Build and Document

This project is a portfolio/interview artifact as much as it is working
code. The documentation trail IS part of the deliverable - it's what lets
a technical interviewer (or future you) understand *why* the system looks
the way it does, not just what it does.

## Every build session does four things, in this order

### 1. Before writing code - check CLAUDE.md
Read the current `CLAUDE.md` to know what phase we're in and what
conventions are already established. Don't re-derive context that's
already written down.

### 2. While building - narrate real decisions inline
When a genuine design choice gets made (not a trivial implementation
detail, an actual "we could have done X, we did Y because Z"), say so
in the response before writing the code, not just as a code comment.

### 3. After a logical unit of work is done - write an ADR
Create `docs/decisions/NNN-short-title.md` (zero-padded, incrementing)
whenever a real decision point was crossed. Trivial choices don't need
one; "why hand-seeded edges over an extraction pipeline for the
prototype" does. Format:

```markdown
# NNN. Short title

## Status
Accepted

## Context
What problem/tension made a decision necessary.

## Decision
What we chose.

## Alternatives considered
What else was on the table, and why not.

## Consequences
What this makes easier, harder, or explicitly out of scope now.
```

### 4. Update CLAUDE.md and BUILD_LOG.md
- `CLAUDE.md` reflects **current state** - overwrite stale sections,
  don't just append. It should always be readable top-to-bottom as an
  accurate snapshot of the project right now.
- `BUILD_LOG.md` is **append-only** - one entry per session, dated,
  short: what got built, what's mocked vs real, what's next.
- After changing `graph/semantic_edges.py` or `graph/seed_config.py`,
  see the generate-diagrams skill - the data-driven Mermaid diagrams
  need regenerating so they don't silently drift from the graph.
- After changing `query/ask.py`'s entity extraction, `query/rag.py`'s
  prompt construction/system prompt, or `query/llm_provider.py` (new
  provider added), see the ai-security-assessment skill - those are
  exactly the surfaces its adversarial test cases exist to re-check.

## Commit conventions

One commit per logical unit, not per file. Commit message explains the
*why*, following the same shape as the ADR:

```
graph: add semantic edge schema v0.1 (hand-seeded, no extraction pipeline)

Implements the confidence/evidence/context structure from the technical
brief, scoped down: edges are manually authored against real CTI sources
rather than auto-extracted. See docs/decisions/003-hand-seeded-edges.md
```

## Do NOT

- Don't write documentation that describes unbuilt future phases as if
  they exist. Every doc reflects only what's actually built.
- Don't let CLAUDE.md or the README reproduce the full pitch-deck vision
  language - describe what THIS prototype does, not the eventual product.
  Anything closer to business/product vision belongs only in
  NOTES-private.md, which is gitignored and never committed.
