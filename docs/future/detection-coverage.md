# Future direction: detection coverage edges and a coverage-gap view

> **DESIGN ONLY - NOT BUILT.** Nothing in this document exists in code. No
> `DETECTED_BY` edges have been added to `graph/semantic_edges.py`, no
> `Detection` node type exists in `graph/build_graph.py`, and
> `visualize/render_graph.py` has no coverage-gap layer. This is deferred
> design thinking, dated 2026-08-15, written down so it isn't lost or
> reconstructed from memory later - not a roadmap item, not a claim of
> progress. See "What would trigger picking this up," below, before anyone
> acts on it.

## Context

`docs/future/schema_reference/relationship_types.json` already defines a
`DETECTED_BY` relationship type as part of the unimplemented v0.3.0 edge
schema (see `docs/future/multi-agent-ingestion.md`'s "Schema design
reference" section for how that schema relates to today's actual, much
simpler `graph/semantic_edges.py`). Its definition, quoted here in full
since it's the entire technical basis for this document:

```json
"DETECTED_BY": {
  "id": "DETECTED_BY",
  "semantic_category": "detection_coverage",
  "description": "Source technique generates telemetry detected by the target detection rule or data source.",
  "directionality": "directed",
  "inverse": "DETECTS",
  "requires_temporal_context": false,
  "valid_source_types": ["technique", "subtechnique"],
  "valid_target_types": ["detection"],
  "coverage_states": ["FULL", "PARTIAL", "WEAK", "NONE", "UNKNOWN"],
  "note": "Must include coverage_state and any conditions (licensing, config, browser) as edge attributes.",
  "example": "T1059.001 DETECTED_BY Sentinel_PowerShell_Anomaly_Rule"
}
```

That field has sat in the schema reference, unused, since it was written.
This document works out what actually using it would look like, at design
level, for two reasons: (1) it's the one `relationship_types.json` entry
whose value is easy to demonstrate visually (a coverage-gap view is
immediately legible, unlike most of the other 11 relationship types), and
(2) it's the one place this project's "no invented data" convention
(CLAUDE.md's Conventions) is hardest to honor by accident, which is worth
thinking through *before* anyone is tempted to populate it, not after -
see "Why this can't be populated honestly today," below.

## What a `DETECTED_BY` edge would add to the graph

A new node type, `Detection`, representing one concrete, environment-specific
detection rule, alert, or analytic - a Sentinel analytics rule, a Splunk
correlation search, an EDR behavioral rule, a Sigma rule mapped to a real
deployed data source. Each `Detection` node would need at minimum:

- `rule_id` / `rule_name` - the actual identifier in whatever detection
  platform it lives in (e.g. `Sentinel_PowerShell_Anomaly_Rule`, matching
  `relationship_types.json`'s own example).
- `platform` - which detection platform/product it's deployed in (Sentinel,
  Splunk ES, CrowdStrike, Elastic Security, a custom Sigma rule against a
  named log source, etc.) - coverage claims are meaningless without knowing
  what's actually watching.
- `data_source` - the underlying telemetry the rule depends on (e.g.
  Windows PowerShell ScriptBlock logging, Sysmon Event ID 1), since a rule
  with no data source enabled provides zero real coverage regardless of how
  well-written it is.

One `DETECTED_BY` edge per (technique, detection rule) pair this project
has real, verified evidence for, carrying:

- `coverage_state` - one of `relationship_types.json`'s five values
  (`FULL`, `PARTIAL`, `WEAK`, `NONE`, `UNKNOWN`), same literal-not-
  statistical discipline docs/decisions/002 already established for
  `confidence`/`sample_size`: this records what was actually verified about
  the rule's coverage of the technique, not a guessed or interpolated
  score.
- `conditions` - the licensing, configuration, or environment prerequisites
  the schema's `note` field calls out (e.g. "requires the E5 add-on
  enabling ScriptBlock logging ingestion," "browser-based delivery only,
  does not cover the same technique delivered via USB").
- A citation, same as every other edge type in this project - here that
  means a pointer to the actual rule definition (a rule ID, a link to the
  internal detection-content repo, a screenshot/export of the rule logic)
  and, ideally, evidence it was actually validated (a detection engineering
  test, a red-team exercise result, a documented false-negative rate) -
  not just that the rule exists and looks relevant.

This slots into the existing structural/semantic layering the same way
`multi-agent-ingestion.md`'s "How this maps onto `graph/`" section already
describes for semantic edges generally: `Detection` nodes and `DETECTED_BY`
edges would be additive, loaded the same way `semantic_edges.py` layers
`SEMANTIC_EDGES` onto `build_graph.py`'s structural graph today, not a
change to any existing node or edge.

## The coverage-gap visualization

Layered onto `visualize/render_graph.py`'s existing graph (see that
module and the README's "Open the interactive graph visualization" link,
added in the same session as this document), the useful question a
defender actually has is: **which techniques in this graph have no
`FULL`-coverage `DETECTED_BY` edge at all?** That's the gap that matters -
a technique with only `PARTIAL`/`WEAK`/`UNKNOWN` coverage, or none, is
exactly what a defender needs surfaced, not buried in a per-edge tooltip
they'd have to check one at a time.

Concretely, once real `DETECTED_BY` data exists, this would extend the
existing visualization with:

- A distinct visual treatment for `Technique` nodes with no `FULL`-coverage
  edge - e.g. a red/hollow border on top of the existing type-based styling
  (`visualize/render_graph.py`'s `_style_node`), so a coverage gap is
  visible in the same view as the group filter, not a separate artifact.
- `Detection` nodes rendered as a fourth node shape (alongside the existing
  Technique/Tactic/Group dot/box/star), with `DETECTED_BY` edges styled
  distinctly from both today's structural and semantic edge categories -
  the same "structural vs. semantic vs. this" visual grammar the existing
  legend already establishes, extended by one row.
- A toggle (alongside the existing per-group filter buttons) that isolates
  the gap view: dim everything except techniques below `FULL` coverage and
  their existing (if any) `PARTIAL`/`WEAK`/`NONE` detection edges - reusing
  the same dim-not-remove interaction `applyGroupFilter()` already
  implements, not a new interaction pattern.
- Detection-edge tooltips carrying `coverage_state`, `conditions`, and the
  citation, matching the existing tooltip discipline for semantic edges
  (`_edge_tooltip` in `visualize/render_graph.py`) - a coverage claim
  without its sourcing visible on hover would break the one property this
  whole visualization exists to make visible.

None of this is a redesign of the existing visualization - it's the same
node/edge styling and dim-not-remove filtering pattern, extended to one
more node type and one more edge type, once there's real data to drive it.

## Why this can't be populated honestly today

Public ATT&CK/CTI data - everything this project's structural graph and
semantic edges are built from - describes what adversaries do. It does not
describe what any particular defender's toolset actually catches, because
that depends entirely on which products are deployed, how they're
licensed and configured, which data sources are actually ingested, and
whether anyone has verified the rule fires the way its description claims.
There is no public source to cite for "T1059.001 is FULL-covered" the way
`graph/semantic_edges.py`'s edges cite Secureworks or Mandiant reporting -
that fact only exists inside a real, specific, deployed environment.

This means `DETECTED_BY` data cannot be seeded the way the 13 seed
techniques or the 17 hand-authored semantic edges were - by a human reading
real, public, citable reports. It can only be populated by someone with
direct access to a real detection stack, verifying each rule against each
technique for real, the same rigor this project already applies everywhere
else (see CLAUDE.md's Conventions: "Every semantic edge carries confidence
score + sample_size + a real citation, or is explicitly labeled an
estimate. No invented data.") - that convention doesn't get an exception
for detection coverage; if anything this is the category where a plausible
-looking but fabricated coverage claim would be most actively misleading,
since it directly implies "you are protected here" to whoever reads it.

**No synthetic or example coverage data - percentages, rule names,
coverage states, anything - should ever be added to this graph or this
visualization to make the demo look more complete than it is.** An empty
or absent coverage layer honestly represents "not yet populated." A
fabricated one would misrepresent "verified secure" for techniques nobody
has actually checked, which is a materially worse failure mode than simply
not having the feature yet - the same reasoning
`docs/future/multi-agent-ingestion.md`'s "An illustrative example was
deliberately not included" section already applied when a populated
example edge for the v0.3.0 schema turned out to cite a Mandiant report
that doesn't exist and was excluded rather than "fixed" with different
invented numbers.

## What would trigger picking this up

Access to real, environment-specific detection rule data for an actual
deployed detection stack - not a hypothetical one, not a public dataset
standing in for one. Until that exists, this stays a design document: the
schema field it's based on (`relationship_types.json`'s `DETECTED_BY`)
continues to sit unused exactly as it does today, `graph/build_graph.py`
gets no `Detection` node type, and `visualize/render_graph.py` gets no
coverage-gap layer. Same gating discipline as
`.claude/skills/scale-to-continuous-ingestion/SKILL.md` applies here even
though this document doesn't need a dedicated skill file of its own: a
real, explicit reason to build, not routine build-session momentum.
