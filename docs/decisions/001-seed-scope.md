# 001. Scope the prototype to 3 groups / 13 hand-picked techniques

## Status
Accepted

## Context
The technical brief this project is based on envisions modeling the full
ATT&CK corpus with automated CTI ingestion at scale. Building that is a
multi-month/multi-person effort. The goal here is a working prototype
that proves the architecture's value on a small, defensible slice of
real data, in an 11-week solo timeframe.

## Decision
Scope to 3 threat groups (APT29/G0016, APT28/G0007, Lazarus Group/G0032)
and 13 techniques, chosen to:
- Form a coherent, explainable kill chain (initial access through
  collection/exfil staging)
- Overlap across all three groups (verified: 37 of 39 possible
  group-technique pairs exist), so group-comparison queries have real
  data behind them, not a contrived example
- Include the exact techniques (T1059.001, T1003.002, T1078) used as
  worked examples in the technical brief, so the prototype can
  reproduce those examples with real data

All group/technique attributions come from the official MITRE ATT&CK
STIX dataset (`data/raw/enterprise-attack.json`, pulled from MITRE's own
GitHub repo), not synthetic or invented data.

## Alternatives considered
- **Full ATT&CK ingestion**: rejected - out of scope for a prototype,
  and would dilute focus away from the semantic-edge/query-layer work
  that's the actual differentiator.
- **Single group, more techniques**: rejected - loses the group-
  comparison use case, which is one of the three documented operational
  use cases in the technical brief.
- **Random/arbitrary technique sample**: rejected - a kill-chain-shaped
  set is more demoable and more honest about "why these 13," versus an
  arbitrary sample that would need justifying case by case.

## Consequences
- Easy to explain and defend in an interview: every inclusion has a
  reason.
- Semantic edges (Phase 2) only need to be authored for this bounded
  set - keeps that hand-authoring effort tractable.
- Explicitly NOT a claim of ATT&CK coverage - README and CLAUDE.md both
  state this is a 13-technique/3-group prototype, not a general system.
- If the project ever moves toward automated ingestion, this seed set
  becomes the first validation/regression set to check new pipeline
  output against known-good data.
