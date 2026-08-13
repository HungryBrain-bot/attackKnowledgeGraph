---
name: generate-diagrams
description: "Use this skill whenever graph/semantic_edges.py's SEMANTIC_EDGES changes (edges added, edited, or removed), graph/seed_config.py's SEED_TECHNIQUES changes, or on an explicit request to update diagrams/flows. Regenerates every data-driven Mermaid diagram in the repo from data/graph_with_semantics.json so they never silently drift from the graph they claim to depict."
---

# Generate Diagrams

This project has two categories of Mermaid diagram, and mixing them up
is the one mistake this skill exists to prevent.

## Trigger conditions

Run `graph/generate_diagrams.py` whenever:
- `graph/semantic_edges.py`'s `SEMANTIC_EDGES` list changes (an edge is
  added, edited, or removed) - the per-technique flow diagrams and the
  master kill-chain diagram both depict this data directly.
- `graph/seed_config.py`'s `SEED_TECHNIQUES` changes - the master
  diagram's node set comes from here.
- Someone explicitly asks to "update the diagrams" or "regenerate the
  flows."

It is **not** triggered by changes to hand-authored prose (case file
sections other than `## Flow`, ADRs, README prose) - those diagrams are
a different category, see below.

## What it does

```bash
python -m graph.generate_diagrams
```

Precondition: `data/graph_with_semantics.json` must already exist and
be current - this script reads that file (via `query.graph_loader`,
the same loader the query layer uses), it does not rebuild the graph
itself. If `SEMANTIC_EDGES` or `SEED_TECHNIQUES` just changed, run
`python -m graph.semantic_edges` first to regenerate that file, *then*
run the diagram generator.

It writes two kinds of output, both inside clearly delimited
auto-generated blocks (see below):
- One Mermaid flowchart per seed technique, showing that technique's
  direct incoming/outgoing semantic edges (`TEMPORALLY_PRECEDES`/
  `CAUSALLY_ENABLES`, labeled with `group_context` and `confidence`) -
  written into that technique's `docs/attack-patterns/<ID>-*.md` file
  under a `## Flow` section.
- One master kill-chain diagram covering all 13 seed techniques and
  every semantic edge, edges colored by which APT group they apply to
  and styled solid/dashed by edge type - written into README.md.

## The idempotency guarantee

Running the script twice in a row with no change to
`data/graph_with_semantics.json` produces **byte-identical** output.
This is load-bearing, not a nice-to-have: without it, every regeneration
would show as a diff in review even when nothing actually changed,
training reviewers to stop looking at diagram diffs closely - exactly
when a real, wrong change would slip through. It holds because the
generator sorts every graph traversal (nodes, edges, edge attributes)
by a stable key before emitting anything - never relies on dict/graph
iteration order. Verified by actually running it twice and diffing the
output, not just asserted - see BUILD_LOG.md's entry for this skill for
the result.

## Auto-generated vs. hand-authored - the distinction that matters

**Auto-generated (never hand-edit - rerun the script instead):**
- The `## Flow` section in every `docs/attack-patterns/<ID>-*.md` file.
- The kill-chain diagram section in `README.md`.

Both are wrapped in HTML comment markers -
`<!-- BEGIN GENERATED: graph/generate_diagrams.py (do not hand-edit;
rerun the script) -->` ... `<!-- END GENERATED -->` - so the boundary is
unambiguous in the file itself, not just documented here. The generator
replaces everything between those markers on every run and leaves
everything outside them untouched. If a diagram inside a `GENERATED`
block looks wrong, the fix is a `SEMANTIC_EDGES`/`SEED_TECHNIQUES`
correction followed by regenerating - never a hand-edit inside the
markers, which the next regeneration would silently overwrite anyway.

**Hand-authored (update manually when the architecture actually
changes, never touched by the script):**
- The system architecture diagram in `README.md` and `CLAUDE.md`
  (STIX bundle through the query CLI).
- The query-flow sequence diagram in
  `docs/decisions/003-query-layer-scope.md`.
- The provider-abstraction diagram in
  `docs/decisions/004-llm-provider-abstraction.md`.

These carry no `GENERATED` markers and `graph/generate_diagrams.py`
never reads or writes them. They depict *structure* (module boundaries,
call flow, interfaces) that doesn't come from graph data and won't
change just because an edge's confidence score was corrected - they
change when the architecture itself changes, which is a hand-edit like
any other doc update, following the build-and-document skill.

## Do NOT

- Don't hand-edit inside a `<!-- BEGIN GENERATED -->` ... `<!-- END
  GENERATED -->` block. The next regeneration overwrites it silently.
- Don't point `graph/generate_diagrams.py` at the hand-authored
  diagrams listed above, even if it would be technically easy to
  template them - they don't come from graph data, so generating them
  would mean the script inventing structure it doesn't actually know.
- Don't skip the idempotency check after changing the generator itself.
  If two consecutive runs ever produce different output with unchanged
  input data, that's a bug in the generator (probably an unsorted
  traversal), not acceptable diagram "jitter."
