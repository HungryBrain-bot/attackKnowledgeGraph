# 002. Semantic edges are group-scoped, evidence-gated, and additive

## Status
Accepted

## Context
Phase 1 gives a structural graph (which groups use which techniques) but
answers none of the questions that actually matter to a defender: given
technique A is observed, what tends to come next, and is that a loose
temporal pattern or a hard prerequisite? That's the gap this project is
built to explore, via two new edge types - `TEMPORALLY_PRECEDES` (A
observed before B) and `CAUSALLY_ENABLES` (A is a documented or
mechanistic prerequisite for B).

Three design questions had to be answered before writing any edges:

1. Is a semantic edge a claim about the technique pair in general, or
   about one group's documented behavior?
2. What do `confidence` and `sample_size` actually mean, precisely
   enough that they can't be quietly invented?
3. How many of the 13 seed techniques get edges in this pass?

## Decision

**Edges are group-scoped, not universal.** Every edge carries a
`group_context` field. The evidence available is behavioral - "APT28 ran
a PowerShell recon script that let them identify the target's Wi-Fi,
then RDP'd in" - not a general law that PowerShell execution always
precedes RDP for any actor. A different group could plausibly reverse or
break that relationship; the schema doesn't foreclose that.

**`confidence` and `sample_size` are defined literally, not
statistically:**
- `sample_size` = count of independently named CTI sources supporting
  the claim, counted directly from the `sources` list - never a made-up
  number.
- `confidence` (0-1) = how *directly* those sources narrate the specific
  ordering/causal claim, vs. being inferred from co-citation or from
  what the techniques mechanically are. A quoted timeline claim from a
  single-incident report (e.g. Mandiant's "Domain Admin within 12
  hours") scores higher than an inference drawn from two techniques
  being co-cited across several reports about the same campaign.
  Reasoning for each score is written out per-edge in `evidence` - the
  score is never presented without its justification alongside it.

**Coverage is deliberately partial.** This pass authors 9 edges
touching 9 of the 13 seed techniques (`graph/semantic_edges.py`), scoped
to pairs where real, specific sequencing or causal evidence was found -
not all 13 techniques, not every plausible-sounding pair. T1003.002,
T1057, T1105, and T1547.001 have no outgoing/incoming semantic edges
yet, because the sourcing search for this session didn't turn up a
citable, specific sequencing claim for them (as opposed to just "the
group uses this technique too," which the structural graph already
captures). CLAUDE.md's conventions allow an edge to be explicitly
labeled an estimate when no source exists - this batch doesn't use that
allowance at all; every edge here has a real citation.

**Semantic edges are additive, not a rebuild.** `graph/semantic_edges.py`
takes the structural graph from `build_graph.py` and adds edges onto it
via `add_semantic_edges()`, raising if a referenced technique isn't
already a seed node. Output is a separate file,
`data/graph_with_semantics.json` - `data/structural_graph.json` (Phase 1
output) is left untouched so the phase boundary stays visible in the
repo.

## Alternatives considered
- **Universal (non-group-scoped) edges**: rejected - would overstate
  what the evidence supports. The whole reason these edges are
  interesting is that they're grounded in what a specific group actually
  did, not a claim about technique physics.
- **Fill in all 13 techniques this pass, using estimates where no source
  exists**: rejected for this session - the user asked for edges "each
  with a real cited source." Padding out coverage with labeled estimates
  is allowed by CLAUDE.md in general, but conflated with 9 real ones in
  the same batch, it would blur which edges are load-bearing.
- **Mutate `structural_graph.json` in place**: rejected - would make it
  impossible to tell, later, which nodes/edges came from raw ATT&CK data
  vs. hand authorship without diffing against git history.

## Consequences
- Every number in `graph/semantic_edges.py` traces to something a human
  can check: a named report, a quoted claim, or an explicit "this is
  inferred, here's why the inference is reasonable" note in `evidence`.
- The graph now has two edge classes with genuinely different evidentiary
  weight (structural = official STIX data; semantic = hand-authored,
  variable confidence) - the query layer, once built, will need to
  surface that distinction rather than flattening it.
- Extending coverage later (T1003.002, T1057, T1105, T1547.001, or any
  cross-group comparison edges) means repeating this same sourcing
  discipline, not just filling in the schema shape.
