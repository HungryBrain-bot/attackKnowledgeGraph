---
name: generate-diagrams
description: "Use this skill whenever [PLACEHOLDER: your source-of-truth data - e.g. a config file, a schema, a database of records] changes, or on an explicit request to update diagrams/flows. Regenerates every data-driven diagram in the repo from that source of truth so they never silently drift from what they claim to depict."
---

# Generate Diagrams

Any project with more than a handful of diagrams eventually has two
categories of diagram - ones that depict live, changing data, and ones
that depict structure that rarely changes. Mixing them up (hand-editing
a data-driven diagram, or trying to auto-generate a structural one) is
the one mistake this template exists to prevent.

## Trigger conditions

Run `[PLACEHOLDER: your generator script]` whenever:
- `[PLACEHOLDER: your source-of-truth data file/table]` changes - any
  diagram that depicts this data directly needs regenerating.
- Someone explicitly asks to "update the diagrams" or "regenerate the
  flows."

It is **not** triggered by changes to hand-authored prose or to the
hand-authored diagrams below - those are a different category.

## What it does

```bash
python [PLACEHOLDER: your generator invocation]
```

Precondition: [PLACEHOLDER: whatever the generator reads must already
be current - state the precondition explicitly, e.g. "run your build
step first if the source-of-truth data itself needs regenerating before
the diagram generator reads it."]

It writes output inside clearly delimited auto-generated blocks (see
below) - [PLACEHOLDER: list what it writes and where, e.g. "one diagram
per entity's case file" and/or "one master diagram in the README."]

## The idempotency guarantee

Running the generator twice in a row with no change to the underlying
data must produce **byte-identical** output. This is load-bearing, not a
nice-to-have: without it, every regeneration shows as a diff in review
even when nothing actually changed, training reviewers to stop looking
at diagram diffs closely - exactly when a real, wrong change would slip
through. Achieve it by sorting every traversal (nodes, edges,
attributes, whatever your generator iterates) by a stable key before
emitting anything - never rely on dict/set/graph iteration order, which
is not guaranteed stable across runs or Python versions for all
collection types. **Verify this by actually running the generator twice
and diffing the output - don't just assert it holds.**

## Auto-generated vs. hand-authored - the distinction that matters

**Auto-generated (never hand-edit - rerun the script instead):**
- [PLACEHOLDER: list the specific generated diagrams/sections]

Wrap these in explicit markers - e.g.
`<!-- BEGIN GENERATED: [script] (do not hand-edit; rerun the script) -->`
... `<!-- END GENERATED -->` - so the boundary is unambiguous in the file
itself, not just documented here. The generator replaces everything
between the markers on every run and leaves everything outside them
untouched. If a generated diagram looks wrong, the fix is a correction
to the underlying source-of-truth data followed by regenerating - never
a hand-edit inside the markers, which the next regeneration would
silently overwrite.

**Hand-authored (update manually when the architecture actually
changes, never touched by the script):**
- [PLACEHOLDER: list your hand-authored architecture/sequence/class
  diagrams - things that depict module boundaries, call flow, or
  interfaces, which don't come from your data source and won't change
  just because a data value was corrected]

These carry no `GENERATED` markers and the generator never reads or
writes them. They change when the architecture itself changes - a
hand-edit like any other doc update (see the `build-and-document`
template).

## Do NOT

- Don't hand-edit inside a `GENERATED` block. The next regeneration
  overwrites it silently.
- Don't point the generator at the hand-authored diagrams, even if it
  would be technically easy to template them - they don't come from your
  data source, so generating them would mean the script inventing
  structure it doesn't actually know.
- Don't skip the idempotency check after changing the generator itself.
  If two consecutive runs ever produce different output with unchanged
  input data, that's a bug in the generator (probably an unsorted
  traversal), not acceptable "jitter."
