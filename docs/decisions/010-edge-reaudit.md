# 010. Edges must carry a fetchable source URL and a verbatim quote; 12 of 17 removed

## Status
Accepted (2026-10-26)

## Context
ADR 002 required every semantic edge to have "a real citation", and
CLAUDE.md's Conventions said "no invented data". Both were followed in
letter: every edge named a real report. A senior-security-engineer
review (2026-10-26) found the citations did not always support the
edge:

- one evidence string credited F-Secure's 2015 "The Dukes" report with
  malware (PowerDuke, POSHSPY) first reported in 2016 and 2017;
- the APT29 `T1059.001 -> T1078` edge, presented as the strongest,
  cited a 2022 phishing campaign while calling it SolarWinds/SUNBURST,
  and counted an unrelated SolarWinds advisory as a second source;
- several edges were true by definition or rested only on two
  techniques appearing in the same report.

The schema had nowhere to put the one thing that makes a citation
checkable: the sentence in the source that supports the edge.

## Decision
1. **Every edge stores `source_url`, `source_date`, a verbatim `quote`
   under 25 words, and `incident_id`** (ADR 009). The quote must
   narrate the specific order or dependency for that group; it is
   printed in the facts block next to the edge, so a reader can check
   it without leaving the answer.
2. **An edge that cannot be quoted from a source fetchable today is
   removed**, not kept with a lower confidence. Removed edges are
   listed with the reason in `docs/edge-audit.md`, so nothing is
   dropped silently, and they live in git history if a source turns up.
3. **Edges true by definition are removed.** `T1566.001 ->
   T1204.002` (an attachment is opened after it is delivered) is the
   case here, for both groups that had it.
4. `sample_size` counts only sources that narrate the claim
   themselves; co-citation does not count.

Applying this left 5 of 17 edges: three APT28 edges from Volexity's
Nearest Neighbor report, one APT28 edge from the 2021 GRU brute-force
advisory, and one APT29 edge re-sourced to Volexity's PowerDuke report.

## Alternatives considered
- **Keep unverified edges, marked `UNVERIFIED`, with low confidence**:
  rejected. The query layer would still retrieve them and an LLM would
  still narrate them; a label in the data does not survive into a
  fluent answer. The audit table keeps the record instead.
- **Re-source each removed edge from memory of other reports**:
  rejected. That is how the original errors happened. One edge was
  re-sourced (PowerDuke), and only because the replacement report was
  fetched and quoted.
- **Add the edges the audit surfaced** (APT29 `T1204.002 -> T1078`
  from the Trello report; the Andariel sequence from CISA AA24-207A):
  rejected for this pass, which is consolidation only. Listed in
  `docs/edge-audit.md` for a deliberate decision.

## Consequences
- The graph now has 5 semantic edges (4 CAUSALLY_ENABLES, 1
  TEMPORALLY_PRECEDES); combined graph 26 nodes, 59 edges. Lazarus
  Group has no semantic edges; most seed techniques have none.
- The README's "ATT&CK Navigator vs. this project" table relied on
  removed edges and is removed (step 4 of the same review).
- Each case file in `docs/attack-patterns/` gets a dated audit note
  listing its kept and removed edges. Their prose is the pre-audit
  record and was not rewritten line by line.
- `tests/test_query_layer_against_evtx.py` no longer asserts that every
  technique with telemetry has a semantic edge.
- Multi-hop chain tests moved to a synthetic fixture graph for the
  path-search behavior the real 5-edge graph is too small to exercise.
- The quotes were extracted through a summarising fetch tool and have
  not been compared character by character with the source pages;
  `docs/edge-audit.md` says so.
