---
name: scale-to-continuous-ingestion
description: "Use this skill ONLY on an explicit, real decision to actually pursue multi-agent continuous CTI ingestion - e.g. the project owner explicitly says \"let's build the ingestion pipeline now,\" or there's genuine external interest from someone evaluating this project beyond a portfolio/interview context. Do NOT trigger automatically, as part of routine build sessions, or just because docs/future/multi-agent-ingestion.md or docs/future/schema_reference/ exist."
---

# Scale to Continuous Ingestion

This skill exists to gate a specific, deliberately deferred piece of
work: replacing `graph/semantic_edges.py`'s hand-authored edges with a
multi-agent continuous CTI ingestion pipeline. The design thinking for
that is written down in `docs/future/multi-agent-ingestion.md` - marked
design-only, unbuilt, dated. This skill is the trigger discipline that
keeps it that way until there's a real reason not to.

## When to trigger

**Only** on one of:
- The project owner explicitly decides to build the ingestion pipeline
  now - not "this would be cool eventually," an actual decision to
  start.
- Real external interest from someone evaluating this project beyond a
  portfolio/interview context - e.g. a team that wants to actually run
  this against a live CTI feed, not a hypothetical.

**Never** trigger this skill:
- Automatically, on any schedule or file change.
- As part of a routine build-and-document session, even one that touches
  `graph/semantic_edges.py` or `ingestion/`.
- Just because `docs/future/multi-agent-ingestion.md` or
  `docs/future/schema_reference/` exist and someone is reading or
  referencing them in conversation.

If in doubt whether a request rises to this bar, ask rather than assume -
this is exactly the kind of scope expansion (empty placeholder directory
to real multi-agent system) that's cheap to trigger accidentally and
expensive to walk back once code exists.

## What to do when actually triggered

1. **Read `docs/future/multi-agent-ingestion.md` first, then
   `docs/future/schema_reference/` (starting with
   `edge_schema_changelog.md` for the reasoning, not just
   `edge_schema_0.3.0.json` for the shape).** Treat both as a first draft
   to revise, not a finished spec to implement literally. They were
   written at a point in time - re-check their assumptions against
   whatever's actually true when this is picked up: are the proposed
   agent roles still the right shape, has the CTI-source landscape
   changed, has the provider landscape changed (new models, new
   grounding/verification tooling that didn't exist when the design was
   written), does the validation-gate design still hold up, does the
   v0.3.0 relationship-type/objective/environment vocabulary still cover
   what real CTI sources actually describe or does it need revising
   before anything's built against it. The orchestration doc's own "why
   deferred" and "validation gate" sections, and the schema reference's
   own "Current vs. future state" framing, are the parts most likely to
   need real scrutiny before anything gets built from them - don't skip
   past them to the agent-role list or the schema fields.
2. **Treat this as new engineering work, not a resume of paused work.**
   Follow the `build-and-document` skill's full discipline from the
   start: check CLAUDE.md's current state first, write ADRs for real
   decisions as they're made (the design doc's proposals are a starting
   point for those decisions, not a substitute for making them for
   real), update CLAUDE.md and BUILD_LOG.md as you go.
3. **Design and build the validation gate before or alongside the first
   agent role that proposes an edge - never after.** The design doc's
   own conclusion is that an ungated pipeline is a materially worse
   failure mode than today's hand-authored process, not a scaled-up
   version of the same risk. Standing up extraction before grounding/
   scoring/conflict-detection/review exists, "temporarily," is exactly
   how that failure mode gets shipped by accident.

## What must NOT change

The ingestion pipeline is additive engineering on top of this project's
existing standards - not a license to relax them because the volume of
edges is about to grow. Specifically, none of the following bend for
ingestion-scale convenience:

- **No invented data** (CLAUDE.md's Conventions) - every edge, agent-
  proposed or human-authored, carries a real citation or is explicitly
  labeled an estimate. An agent unable to find a real source for a
  plausible-sounding edge does not get to lower that bar; it produces no
  edge.
- **`confidence` and `sample_size` keep their literal definitions**
  (docs/decisions/002) - `sample_size` counted directly from named
  sources, `confidence` scored with written reasoning attached, never a
  bare number either role or a human finds convenient.
- **The `build-and-document` skill's discipline** - ADRs for real
  decisions, CLAUDE.md kept current (not append-only, overwritten to
  reflect actual state), BUILD_LOG.md's append-only session log.
- **The `attack-pattern-doc` skill's discipline** - any newly-ingested
  technique still gets a real case file, sourced the same way, not
  generated boilerplate.
- **The `ai-security-assessment` skill's discipline** - if ingestion
  introduces any new input path where external or agent-generated text
  reaches an LLM prompt (e.g. an extraction agent's output feeding a
  scoring agent's prompt), that's a new trigger condition for that
  skill, not an exemption from it. Multi-agent pipelines have more
  prompt-injection surface than a single query call, not less.

## Do NOT

- Don't build any part of this pipeline speculatively, "since we're
  already touching `ingestion/`" - see "When to trigger," above.
- Don't implement `docs/future/multi-agent-ingestion.md`'s agent roles
  literally without re-validating them first - it was written without
  the benefit of whatever's true at the time this is actually picked up.
- Don't let a growing edge volume become a reason to loosen citation,
  confidence, or sample_size discipline "just for the ingested ones" -
  see "What must NOT change," above. A two-tier trust system (rigorous
  for hand-authored edges, looser for ingested ones) is worse than
  either extreme, because it's not visible at query time which tier an
  edge came from unless that's explicitly modeled and surfaced too.
