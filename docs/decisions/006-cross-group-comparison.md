# 006. Cross-group comparisons are annotations on existing edges, not a new edge type

## Status
Accepted

## Context
ADR-002 scoped semantic edges to one group's documented behavior
(`group_context`) rather than a universal claim about a technique pair.
That was always going to leave an interesting question open: what happens
when two groups are independently documented handling the *same*
technique pair in a genuinely different way? BUILD_LOG's Phase 2 close-out
flagged this as unbuilt for lack of evidence. This session went looking
for real evidence, and found two genuine cases:

- **{T1059.001, T1078}, APT29 vs. APT28 - direction reversed.** APT29's
  SolarWinds/UNC2452 intrusion runs `T1059.001 -> T1078`: a spearphishing
  payload executes first, and Domain Administrator access is the outcome
  (Mandiant's quoted "less than 12 hours" timeline). APT28's GRU
  brute-force campaign runs `T1078 -> T1059.001`: credentials harvested by
  Kubernetes-distributed password spraying come first, and PowerShell
  (an Exchange `ApplicationImpersonation` cmdlet, per the joint advisory)
  is what those credentials buy. Same unordered pair, opposite direction,
  different initial-access vector, different plane (on-prem AD vs.
  M365/Exchange identity).
- **T1566.001 -> T1204.002, APT29 vs. Lazarus Group - same direction,
  different mechanism.** Both groups are documented running delivery
  straight into execution, but WHEN the malicious code exists on the
  victim host differs. APT29's weaponized attachment is self-contained -
  the macro is in the file, so execution is a purely local event. Lazarus
  (McAfee's Operation North Star reporting) sends an attachment with no
  macro at all; opening it makes Office fetch a remote `.dotm` template
  disguised as a `.jpg`, and only then does a macro exist to run -
  execution is network-dependent. This required authoring a new Lazarus
  edge for `T1566.001 -> T1204.002` (it didn't exist before this session)
  since a comparison needs both sides to already exist as real edges.

Both required real sourcing work to state precisely and to score
honestly - see `graph/semantic_edges.py`'s `CROSS_GROUP_COMPARISONS`
`evidence` fields for the full reasoning, including why each is
discounted below its stronger constituent edge's confidence. Five other
candidate pairs were investigated and rejected for lack of real
same-pair, cross-group sourcing (co-citation alone, or evidence for a
mechanistically different technique than the one being compared) -
deliberately not padded in to hit a round number.

The open design question: how does a *comparison* get represented in a
schema that, until now, only had to represent single-group behavioral
claims?

## Decision

**A cross-group comparison is authored as its own scored record in a new
`CROSS_GROUP_COMPARISONS` list, and attached as a `comparisons` list
attribute onto the two semantic edges it compares - not modeled as a new
edge type between technique nodes.** `add_cross_group_comparisons()`
looks up each comparison's two `(source, target, group_context)`
references via a new `_find_semantic_edge()` helper and appends the
rendered comparison onto each matching edge's data dict, raising if
either reference doesn't resolve to a real edge already in the graph.

A comparison also needed its own definition of `confidence`, distinct
from what that field means on a behavioral edge (see ADR-002). An edge's
confidence asks "how directly do the sources narrate this specific
group's ordering/causal claim?" A comparison's confidence asks a
different question: "how confident are we that this divergence is a
*real* difference in documented tradecraft, rather than an artifact of
which campaigns happened to get reported?" It's computed as the weaker
constituent edge's confidence, then discounted for two comparison-specific
risks: **exclusivity** (does the same group also show the other pattern
elsewhere, meaning the contrast is campaign-scoped rather than truly
group-scoped?) and **comparability** (are the two documented operations
the same kind of thing, narrated by the same kind of report, or is part
of the apparent divergence just an artifact of the reporting lens?). Both
authored comparisons score below their strongest constituent edge for
exactly this reason - see the module docstring and per-comparison
`evidence` for the full field definitions and reasoning.

## Alternatives considered

- **A new `CONTRASTS_WITH` edge type between the two technique nodes,
  carrying both group contexts.** This is the naturally-reached-for
  option and was seriously considered, but rejected on several grounds
  that compound:
  - **It would have to lie about direction for cmp-001.** The graph is a
    `MultiDiGraph`; `graph/generate_diagrams.py` renders every edge as a
    directed arrow. Comparison cmp-001's pair is unordered by
    definition - the divergence *is* that direction differs - so any
    direction chosen for the edge is arbitrary and visually asserts a
    sequence that doesn't exist. For cmp-002, where both sides genuinely
    run the same direction, a `CONTRASTS_WITH` arrow would read as a
    *third* sequencing claim layered on top of the two real ones. There's
    no direction that's honest in both cases.
  - **`group_context` is single-valued and load-bearing.**
    `query/retrieval.py`'s `matches_group()` does one case-folded string
    compare against `data["group_context"]`. A comparison inherently
    names two groups. As a new edge it would either need a forked field
    shape (breaking an invariant every current consumer relies on) or
    would be silently dropped by group filtering - meaning the one query
    most likely to want a comparison surfaced ("what happens after
    T1059.001 for APT29?") is exactly the one that would hide it.
  - **It conflates a meta-claim with a behavioral claim.** `TEMPORALLY_
    PRECEDES`/`CAUSALLY_ENABLES` assert something about what an attacker
    did. A comparison asserts something about *our own two edges*.
    Putting both in the same edge-type namespace between the same nodes
    blurs a distinction ADR-002 was explicit about maintaining.
  - **Blast radius vs. dataset size.** A new edge type has to be taught
    to `query/retrieval.py`'s `SEMANTIC_EDGE_TYPES`, `generate_diagrams
    .py`'s type/color/style maps, and every diagram - for two data
    points. CLAUDE.md's Code Review Standards are explicit about not
    adding machinery ahead of an observed need at this scale.

  Its one real merit - a comparison deserves its own `confidence`/
  `sample_size`/`sources` as a distinct claim, not just prose bolted onto
  an existing edge - is kept by the chosen design: `CROSS_GROUP_
  COMPARISONS` records are first-class and fully scored. Only the
  graph-topological expression (a peer edge between technique nodes) was
  declined.

- **Plain duplicated `compared_to` prose written directly into both
  constituent edges' `evidence` fields.** Rejected: the same comparison
  text authored twice in two separate dict literals drifts the moment
  one is edited without the other, and there's no single place to hang
  the comparison's own confidence/sample_size/sources. The `CROSS_GROUP_
  COMPARISONS` list plus a build-time attach step gets the same
  attribute-locality without the duplication - one source of truth,
  copied onto both edges programmatically, not by hand.

- **A separate module or JSON file for comparisons, outside
  `semantic_edges.py`.** Rejected for now: a comparison is meaningless
  without the two edges it references, and splitting them into another
  file adds a cross-file integrity problem (a renamed group or a
  corrected edge could silently orphan a comparison in a file nobody
  thinks to check) for no benefit at two comparisons. Worth revisiting if
  comparisons ever meaningfully outnumber edges.

- **A `Comparison` node type in the graph.** Rejected: reifying a
  two-item annotation into a new node class pollutes a node set that is
  currently exactly "things MITRE says exist" (Technique/Tactic/Group/
  Software), for something that is fundamentally metadata about two
  edges, not an entity.

## Consequences
- `add_cross_group_comparisons()` raises if a comparison names an edge
  that doesn't exist - the same fail-loud discipline as
  `add_semantic_edges()`. This is what stops a comparison from silently
  outliving a corrected or removed edge, the same failure mode ADR-002's
  Consequences section already flagged for edges themselves (and the one
  that bit this project once already - the reversed T1059.001/T1021.001
  edge, BUILD_LOG 2026-08-13).
- Node/edge counts: unchanged by the comparisons themselves (they're
  attributes, not edges). The one new Lazarus edge required to give
  cmp-002 a second side does change counts: 26 nodes, 71 edges (7
  TEMPORALLY_PRECEDES, 10 CAUSALLY_ENABLES, up from 6/9) - verified by
  actually re-running `graph/semantic_edges.py`, not just computed by
  hand.
- While verifying cmp-001, the existing APT28 `T1078 -> T1059.001` edge
  was found to be grounded in the wrong sentence of its cited advisory
  (attributing the RCE step to PowerShell when the advisory actually
  attributes it to Exchange CVE exploitation) - re-grounded on the
  advisory's real PowerShell-relevant fact (an `ApplicationImpersonation`
  cmdlet grant, which MITRE's own T1098.002 procedure example also cites
  this advisory for) and its confidence raised 0.65 -> 0.75 accordingly.
  Documented inline in that edge's `evidence` field, same pattern as the
  2026-08-13 T1059.001/T1021.001 correction.
- `query/retrieval.py` and `format_context()` do not yet surface the new
  `comparisons` attribute - the query layer still returns exactly what it
  did before this change. Surfacing it (as a separate, explicitly-
  labeled block, not inline with the arrows, and deliberately
  **not** filtered by the `group` query parameter, since a comparison
  whose other side is a different group is still relevant context) is
  future query-layer work, out of scope for this pass, and would need an
  `ai-security-assessment` run before shipping - injecting a second
  group's behavior into a group-filtered answer widens the already-logged
  open item in `docs/security-assessment.md` that the deterministic
  grounding guard checks technique IDs only, not group attribution.
- Extending this to more comparisons later means repeating the same
  sourcing discipline (real citations, honest rejection of
  unsubstantiated pairs, comparison-specific confidence reasoning), not
  just filling in the schema shape - same principle ADR-002 already
  established for edges.
