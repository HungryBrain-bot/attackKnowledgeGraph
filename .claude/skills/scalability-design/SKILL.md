---
name: scalability-design
description: "Use this skill on an explicit request to plan how this project would scale (vertically or horizontally), or when a genuinely load-bearing change happens - the seed set grows significantly beyond 13 techniques, or a real concurrent-user scenario emerges (not a hypothetical one). Do NOT trigger automatically, as part of routine build sessions, or just because docs/future/scalability.md or api/ exist. Produces design-only analysis - grounded in this project's actual code, not generic scaling advice - written to docs/future/scalability.md, distinguishing what's already true today from what would need to be built."
---

# Scalability Design

This skill exists to keep scaling analysis honest and specific to this
project's actual architecture, not a generic "how to scale a web app"
essay. The design thinking lives in `docs/future/scalability.md` - some
of it is a real, already-true fact about the current code (the API's
statelessness), stated as such; the rest is deferred, design-only
analysis of what would need to change for real growth, same discipline
as `docs/future/multi-agent-ingestion.md` and
`docs/future/detection-coverage.md`.

## When to trigger

**Only** on one of:
- An explicit request to plan or document how this project would scale.
- A genuinely load-bearing change actually happens - the seed set
  (`graph/seed_config.py`) grows significantly beyond its current 13
  techniques/3 groups, or a real concurrent-user scenario emerges (an
  actual deployment with real traffic, not "what if this had users
  someday").

**Never** trigger this skill automatically, as part of a routine build
session, or just because `docs/future/scalability.md` or `api/` exist
and are being referenced in conversation - same discipline as
`scale-to-continuous-ingestion`'s trigger conditions, for the same
reason: this is cheap to trigger accidentally (there's always some
hypothetical scale story to tell) and the value of the doc comes from it
staying tied to real, current numbers rather than getting stale or
speculative.

## What to do when actually triggered

Ground every claim in this project's actual code and actual measured
numbers - never generic scaling advice copy-pasted from how these
problems are "usually" solved. Re-verify the numbers below against
current reality before reusing them; they were measured at a specific
point in time and this project's seed set can change.

1. **Vertical scaling - check what's actually in memory and where.**
   `query/graph_loader.py` loads the full combined graph
   (`data/graph_with_semantics.json`) into a NetworkX `MultiDiGraph` in
   one process-lifetime call - `api/main.py` does this once at import
   time (`_graph = load_graph()`), not per-request. At the time this
   skill was first applied (2026-08-15), that file was 26 nodes / 71
   edges, ~50KB on disk. Don't confuse this with the separate,
   already-flagged tradeoff in `graph/build_graph.py` (loading the full
   ~48MB raw STIX bundle into memory) - that only runs at build time,
   whenever a maintainer regenerates the committed graph JSON after
   changing `graph/seed_config.py` or `graph/semantic_edges.py`; it is
   never on the API's request-serving path and doesn't affect runtime
   scaling at all. Conflating the two is the most likely mistake here -
   verify which load path is actually being asked about before drawing
   a conclusion.
2. **Horizontal scaling - verify statelessness, don't assume it.** Read
   `api/main.py` and everything it calls
   (`query/retrieval.py`/`query/rag.py`/`query/llm_provider.py`) for any
   in-process mutable state a second replica wouldn't share: a mutation
   of the loaded graph object, an in-memory cache whose contents could
   differ between replicas, a filesystem write, anything keyed on
   which specific replica served a prior request. At the time this
   skill was first applied, there was none - see
   `docs/future/scalability.md`'s "Already true today" section for the
   actual verification and its reasoning, not just an assertion. If a
   future change introduces per-process state (an in-memory cache is
   the most likely candidate - see "What would need to change," below),
   this conclusion needs re-verifying, not assumed to still hold.
3. **"What would need to change" gets tied to a concrete trigger
   condition per item, not just proposed.** A real graph database
   (e.g. Neo4j) replacing the in-memory NetworkX graph, a real container
   orchestrator replacing `docker compose`, a caching layer for repeated
   queries, and real rate limiting each get their own "what would
   actually make this worth doing" condition - see
   `docs/future/scalability.md`'s corresponding section. Don't
   recommend infrastructure this project's real numbers don't yet
   justify.
4. **Follow `build-and-document`'s discipline** for anything that
   changes as a result: check CLAUDE.md's current state first, write an
   ADR if a real infrastructure decision actually gets made (not for
   this design doc itself, which documents analysis, not a decision),
   update CLAUDE.md and BUILD_LOG.md.

## What must NOT change

- **Don't build any of the "what would need to change" infrastructure
  speculatively** just because this skill produced a plan for it - see
  "When to trigger," above. A design doc is not an implementation
  ticket.
- **Don't restate the horizontal-scaling statelessness conclusion as
  still true without re-checking it** if `api/main.py` or the query
  layer has changed since it was last verified - it's a claim about
  specific code, not a permanent architectural property.
- **Don't let a scaling story override this project's other standing
  disciplines** - e.g. a caching layer added for real must still keep
  `rag.answer()`'s deterministic guards (`_check_no_ungrounded_
  techniques`/`_check_no_ungrounded_edges`) in the path for any answer
  actually served, cached or not; a graph database migration must still
  preserve "every semantic edge carries confidence + sample_size + a
  real citation" (CLAUDE.md's Conventions).

## Do NOT

- Don't produce a generic "how to scale a FastAPI service" writeup that
  could apply to any project - every claim in
  `docs/future/scalability.md` must be traceable to this project's
  actual code or actual measured numbers.
- Don't present a design-only recommendation as if it's already built,
  or blur the line between "already true today" (the statelessness
  finding) and "would need to be built" (a graph database, an
  orchestrator, caching, rate limiting) - the doc keeps those
  explicitly separate for a reason.
- Don't skip re-verifying the statelessness claim against current code
  before reusing it - see point 2 above.
