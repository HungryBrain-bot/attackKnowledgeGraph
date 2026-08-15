# Future direction: multi-agent continuous CTI ingestion

> **DESIGN ONLY - NOT BUILT.** Nothing in this document exists in code.
> No agent roles described here have been implemented, no orchestration
> exists, `ingestion/` remains the empty placeholder it's always been
> (see docs/decisions/001-seed-scope.md). This is deferred design
> thinking, dated 2026-08-13, written down so it isn't lost or
> reconstructed from memory later - not a roadmap item, not a claim of
> progress. See `.claude/skills/scale-to-continuous-ingestion/SKILL.md`
> for the explicit trigger condition before anyone acts on this.

## Context

Today, `graph/semantic_edges.py` hand-authors every `TEMPORALLY_PRECEDES`/
`CAUSALLY_ENABLES` edge as a static Python literal in `SEMANTIC_EDGES` -
16 edges, each with a `confidence`, `sample_size`, `sources`, and
`evidence` field, sourced by a human reading real CTI reports (see
docs/decisions/002-semantic-edge-schema.md). This works at 13 techniques
and 3 groups. It does not scale to continuous ingestion of daily CTI feed
updates across a broader ATT&CK surface - that was always out of scope
for this prototype (docs/decisions/001: "the technical brief this
project is based on envisions modeling the full ATT&CK corpus with
automated CTI ingestion at scale... a multi-month/multi-person effort").

This document sketches, at design level only, what a multi-agent
orchestration approach to that continuous-ingestion problem would look
like, so the thinking exists somewhere real if it's ever picked up -
without pretending it's been derisked, prototyped, or is currently
planned work.

## Agent roles

Each role below is a proposed responsibility boundary, not a class name
or an implementation commitment. They're written as a pipeline because
that's the natural shape of "watch a feed, extract a claim, verify it,
score it, merge it" - not because a real design would necessarily be
strictly sequential.

1. **Source monitoring** - watches CTI feeds (vendor threat-intel blogs,
   government advisories, ISAC bulletins, MITRE ATT&CK's own dataset
   updates) for new or updated reporting touching groups/techniques
   already in the graph, or candidate techniques to add. Outputs a
   queue of candidate source documents, not extracted claims - this
   role never touches the graph directly.
2. **Extraction** - reads one flagged source document and proposes
   candidate semantic edges in a structure that mirrors today's
   `SEMANTIC_EDGES` schema exactly: technique pair, edge type
   (`TEMPORALLY_PRECEDES`/`CAUSALLY_ENABLES`), `group_context`, a
   quoted passage as evidence, and the source citation. Never free-form
   prose - a candidate edge that can't be expressed in the existing
   schema shape is a signal the schema itself needs revisiting, not a
   reason to loosen the extraction format.
3. **Evidence grounding** - independently verifies that the extraction
   agent's quoted passage actually appears in the source document, and
   that the source document itself is real (fetchable, not a fabricated
   citation). This is the ingestion-time analog of `query/rag.py`'s
   `_check_no_ungrounded_techniques()` guard (docs/decisions/005) -
   the same "don't trust the generating step to police itself, verify
   independently" principle, applied one stage earlier in the pipeline.
4. **Confidence scoring** - assigns `confidence` and `sample_size` per
   the literal, non-statistical definitions already fixed in
   docs/decisions/002: `sample_size` = count of independently named
   sources, counted directly, never invented; `confidence` = how
   directly the source narrates the specific ordering/causal claim,
   with the reasoning written out alongside the score, not presented
   bare. This is explicitly the highest-stakes role in the pipeline -
   see "Validation gates," below.
5. **Conflict detection** - checks each candidate edge against the
   existing trusted graph for contradiction (e.g. a new source implies
   the reverse causal direction of an edge already in the graph). This
   project already has one real, documented case of exactly this kind
   of error - the T1059.001/T1021.001 edge direction that was
   originally modeled backwards and only caught when a human re-read
   the full Volexity report (see BUILD_LOG.md's 2026-08-13 entry on the
   correction). A conflict-detection role exists specifically because
   that failure mode is real, not hypothetical, and won't get rarer at
   ingestion scale - it'll get more frequent and harder to catch by hand.

## How this maps onto `graph/` without breaking it

- **The structural graph stays exactly as it is.** `build_graph.py`'s
  STIX-sourced nodes/edges (Technique, Tactic, Group, Software,
  HAS_TACTIC, USES_TECHNIQUE) are official MITRE data, not something an
  ingestion pipeline would touch or need to reproduce. Continuous
  ingestion is scoped to semantic edges only, same boundary that already
  exists between Phase 1 and Phase 2 today.
- **Semantic edges move from hand-authored to agent-proposed +
  validated, but the additive relationship to the structural graph
  doesn't change.** Today, `add_semantic_edges()` takes the structural
  graph and layers `SEMANTIC_EDGES` onto it, raising if a referenced
  technique isn't already a seed node (docs/decisions/002). A future
  ingestion pipeline would preserve that exact contract - agent output
  still can't reference a technique that isn't already a real node from
  real STIX data.
- **A new trust boundary is needed between "proposed" and "validated"
  that doesn't exist today, because today everything in
  `SEMANTIC_EDGES` is already validated (a human wrote it).** The
  natural design is two artifacts instead of one: a `proposed_edges`
  output from the extraction/grounding/scoring roles, and a
  `validated_edges` file that `query/graph_loader.py` actually loads -
  structurally analogous to today's `data/structural_graph.json` vs.
  `data/graph_with_semantics.json` split, which already exists
  specifically so the phase boundary stays visible in git history
  (docs/decisions/002). Nothing moves from `proposed_edges` to
  `validated_edges` without passing the gate below.
- **`ingestion/`'s existing placeholder becomes the natural home** for
  the source-monitoring and extraction roles' code, once built -
  consistent with CLAUDE.md's current description of that directory as
  "reserved for a future automated CTI ingestion pipeline," not a
  relocation of anything that exists today.

## Validation gate(s) - what has to be true before an agent-proposed edge is trusted

This project's single load-bearing convention is CLAUDE.md's "no
invented data." Today that's enforced by a human directly reading CTI
reports and writing citations by hand - the gate is inherent to the
process. A multi-agent pipeline removes that inherent gate, so an
explicit one has to replace it, or the convention silently stops being
true the moment ingestion goes live. Proposed gate, all conditions
required, not optional:

1. **Evidence grounding passed independently** - the quoted evidence
   text is confirmed present in the actual source document by a role
   other than the one that extracted it (role 3, above). An extraction
   agent's self-reported citation is not sufficient on its own, the same
   way this project doesn't let `query/rag.py`'s LLM call self-certify
   its own groundedness (docs/decisions/005).
2. **At least one independently-named, real source** - `sample_size`
   computed the same literal way it is today: counted from a real
   `sources` list, never asserted as a round number.
3. **A written confidence justification, not just a score** - matching
   the existing discipline in `graph/semantic_edges.py`'s `evidence`
   field. A confidence value with no reasoning attached is rejected
   automatically, before it ever reaches a human.
4. **Conflict check clear, or explicitly resolved** - a candidate edge
   that contradicts an existing validated edge (direction, group
   attribution, or edge type) is blocked from auto-merge and routed to
   explicit review, never silently overwritten.
5. **Human review before first promotion to "validated," at minimum
   during any initial rollout.** This project has exactly one real,
   documented instance of an edge direction being wrong despite looking
   individually well-cited - caught by a human, not by any automated
   check that existed at the time. Design-level honesty: nothing above
   proves an all-agent pipeline would have caught that error either.
   Treat human review as the actual gate until there's real operating
   evidence (many cycles, audited) that the automated stages alone would
   catch what a human catches today. This mirrors CLAUDE.md's Model
   Usage convention already reserving exactly this class of judgment
   call (confidence/sample_size assignment, reconciling ambiguous
   evidence) for the highest-scrutiny tier available, not the cheapest
   one that gets the schema fields filled in.

**What breaks if this gate doesn't hold**: "no invented data" stops
being a true statement about this project, silently, at a scale where
nobody is reading every edge by hand anymore. Today, a wrong edge is one
mistake in 16, each individually human-checked, and this project's own
history shows even that low a volume produced one real error that took
a full report re-read to catch. An ingestion pipeline without a real
gate doesn't reduce that error rate - it multiplies the volume while
removing the check that catches it, which is a materially worse failure
mode than the current one, not a scaled-up version of the same risk.

## Schema design reference: v0.3.0 (`docs/future/schema_reference/`)

**Current vs. future state, explicitly**: attck-graph's actual
`graph/semantic_edges.py` currently uses a simple flat schema (`type`,
`confidence`, `sample_size`, `citation`) - deliberately, per
docs/decisions/002-semantic-edge-schema.md. The schema described in this
section and saved under `docs/future/schema_reference/` is a **target
for a later phase, not the current implementation**. Adopting it now
would violate this project's own Code Review Standards (CLAUDE.md:
"don't add complexity ahead of an observed need") - 16 hand-authored
edges don't need a JSON Schema, a controlled 12-type vocabulary, or a
staging/validated promotion pipeline; they need exactly what
`semantic_edges.py` already gives them. This reference exists purely so
the target shape is written down for whenever the `scale-to-continuous-
ingestion` skill's trigger condition is actually met, not as a claim
that any of it exists today.

Four design reference files are saved under `docs/future/schema_reference/`,
unimplemented:
- `edge_schema_0.3.0.json` - the full JSON Schema for a semantic edge at
  this target maturity level.
- `relationship_types.json` - the controlled relationship-type
  vocabulary (below).
- `objective_taxonomy.json` - a controlled vocabulary of attacker
  operational objectives (e.g. `GOAL_CREDENTIAL_ACCESS`), mapped to
  ATT&CK tactics but capturing intent an ATT&CK tactic alone doesn't.
- `environment_taxonomy.json` - a controlled vocabulary of deployment
  environments (cloud identity, on-prem AD, hybrid, OT/ICS, etc.), so an
  edge can record *which* environment a relationship was observed in
  rather than implying it's universal.
- `edge_schema_changelog.md` - the version history and, more usefully,
  the *reasoning* behind each schema decision (0.1.0 through the
  planned 0.4.0) - the "why," not just the "what changed."

### The controlled relationship-type vocabulary

Today's graph uses exactly 2 semantic edge types, both defined informally
in `graph/semantic_edges.py`'s docstring: `TEMPORALLY_PRECEDES` and
`CAUSALLY_ENABLES`. The v0.3.0 schema formalizes a **12-type controlled
vocabulary** that this project's 2 types are a subset of - the eventual
superset they could grow into, not a replacement for them:
`TEMPORALLY_PRECEDES`, `CAUSALLY_ENABLES`, `LOGICALLY_REQUIRES` (a
harder prerequisite than `CAUSALLY_ENABLES` - "cannot execute without"
rather than "creates a capability for"), `LIKELY_FOLLOWED_BY` (weaker,
probabilistic-only successor), `DETECTED_BY`, `MITIGATED_BY`,
`ATTRIBUTED_TO`, `RELATED_TO` (an explicitly-discouraged catch-all -
"if used frequently, propose a new specific type instead"), `DELIVERS`,
`EXPLOITS`, `DROPS`, and `COMMUNICATES_WITH`. Each type in
`relationship_types.json` declares its own directionality, inverse
relationship name, and valid source/target entity types (e.g.
`DETECTED_BY` can only target a `detection` node, never a `technique`) -
so a future validation step can reject a structurally nonsensical edge
before it ever reaches a human reviewer. `DETECTED_BY` specifically -
what using it for real would add to the graph, a coverage-gap
visualization layered onto `visualize/render_graph.py`, and why it can't
be populated honestly without real, environment-specific detection rule
data - is worked out in its own design doc,
[`docs/future/detection-coverage.md`](detection-coverage.md), rather than
here; same "design only, not built" status.

### Confidence: computed by a deterministic function, never by an LLM directly

The schema's single most important principle, and the one most worth
preserving explicitly if this project ever does scale: **`confidence.score`
is the output of a deterministic function of qualitative inputs -
`f(source_count, corroboration, source_tier, recency, sample_size)` -
never a number an LLM is simply asked to produce.** Same inputs, same
score, every time; auditable and reproducible in a way an LLM's
self-reported confidence estimate never is. This isn't a new idea for
this project - it's a
formalization of what `graph/semantic_edges.py` already does informally
today: `sample_size` is counted directly from a real `sources` list,
`confidence` is scored by a human against docs/decisions/002's literal
definition, and the reasoning is written out in the `evidence` field
rather than presented as a bare number (see docs/decisions/002's
"`confidence` and `sample_size` are defined literally, not
statistically"). The v0.3.0 schema's contribution is making that
principle a structural requirement (`confidence_reasoning` is a
required, controlled-vocabulary object, not a free-text afterthought)
rather than a documented-but-informal convention a human happens to
follow.

### `observed_in`: group IDs only, never names

`observed_in[].group_id` stores only the ATT&CK group ID pattern
(`G[0-9]{4}`) - never a group name. `edge_schema_changelog.md`'s 0.3.0
entry explains why this was a breaking change from 0.2.0: "ATT&CK group
aliases change; IDs do not. Storing names causes staleness." Names are
resolved at query time from the graph instead. This is a real
improvement worth adopting if/when this project scales past today's 3
fixed, unchanging seed groups (`graph/seed_config.py`'s `SEED_GROUPS`
list) - at 3 groups the staleness risk this design solves for doesn't
practically exist yet, which is exactly why `semantic_edges.py` doesn't
need it today either.

### The staging → validated → live-graph promotion gate

The schema's `inference.validation_status` field (`approved` / `pending`
/ `rejected` / `requires_review`) and `relationship_types.json`'s
`ingestion_rules` block ("`pending_edges_stored_in`: `staging_graph`",
"`approved_edges_promoted_to`: `live_graph`") together define an explicit
promotion gate: an edge exists in a staging graph the moment it's
proposed, and only moves to the live, query-serving graph after
`validation_status` reaches `approved`. This is the eventual, formalized
replacement for today's approach - "hand-author directly into
`SEMANTIC_EDGES`, no separate staging state, because a human already
validated it by writing it" - and is the same staging/validated split
already sketched more generally in this document's "How this maps onto
`graph/`" section above; the schema just gives it concrete field-level
shape (`minimum_confidence_score: 0.4`, `ml_inferred_requires_review:
true`, `llm_assisted_requires_review: true`).

### An illustrative example was deliberately not included

A populated example edge instance was considered for this section and
explicitly excluded. The example this schema shipped with cited a
Mandiant report - "Cloud Threat Activity Report," report ID
`MANDIANT-2023-017` - that does not exist; checked directly (web search
for both the exact report title and the report ID turned up nothing
matching, only Mandiant's real, differently-named M-Trends 2023 report).
Whether that citation was a hallucination or a placeholder never meant
to be taken as real, it's fabricated evidence, and this project doesn't
carry fabricated evidence anywhere in the repo, including inside an
"unbuilt, for reference" document - the "no invented data" convention
doesn't have a design-only exception. Neither the source fixture file
nor any of its specific numbers (`sample_size: 14`, `confidence: 0.82`,
its observation counts, or its dwell-time statistics) are reproduced
here or anywhere else in this repo. The schema's structure is fully
documented above in prose, and the real field definitions are in
`docs/future/schema_reference/edge_schema_0.3.0.json` itself - a
populated illustrative instance isn't necessary to understand the shape,
and one built from invented placeholder data would risk being
mistaken for real evidence later, the exact failure mode this section
exists to avoid repeating.

## Why this is deliberately deferred now

Same reasoning as `ingestion/` being an intentionally empty placeholder
today (docs/decisions/001): this project's goal is a working prototype
that proves the graph-modeling architecture's value on a small,
defensible, fully human-verified slice of real data, in a bounded
timeframe - not the full-scale ingestion system the original technical
brief envisions. Building real multi-agent orchestration, plus a
validation gate rigorous enough to actually preserve "no invented data"
at scale, is itself a multi-month/multi-person effort, orthogonal to
proving the semantic-edge/query-layer architecture works at all.
Building it prematurely would dilute focus away from that proof, and -
more specifically - risks baking an unproven trust boundary into a
project whose entire credibility currently rests on a trust boundary
(human citation-checking) that's simple enough to audit by inspection.

## What would trigger picking this up

Not routine build sessions, and not this document existing. Per
`.claude/skills/scale-to-continuous-ingestion/SKILL.md`: a real,
explicit decision to pursue it - genuine interest from someone
evaluating this project beyond a portfolio/interview context (e.g. a
team that wants to actually run this against a live CTI feed), or the
project owner explicitly deciding to build the ingestion pipeline now.
Until then, this stays a design document, not a plan.
