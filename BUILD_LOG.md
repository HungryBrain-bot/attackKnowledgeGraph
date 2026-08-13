# Build Log

## 2026-08-13 - Scaffolding

- Initialized repo structure: graph/, ingestion/, query/, docs/,
  .claude/skills/
- Wrote two Claude Code skills:
  - `build-and-document` - ADR + CLAUDE.md + build log discipline for
    engineering decisions
  - `attack-pattern-doc` - per-technique case file discipline (problem,
    mechanics, gap, how the graph models it, sources)
- Wrote CLAUDE.md (engineering-only, no product-pitch language) and
  NOTES-private.md (gitignored, holds full platform vision separately)
- Nothing built yet. Next session: graph core - pull real structural
  data via mitreattack-python, pick the 10-15 technique / 2-3 group
  seed set, build the NetworkX MultiDiGraph.

## 2026-08-13 - Structural graph (Phase 1)

- Downloaded official MITRE ATT&CK enterprise STIX bundle from MITRE's
  GitHub (data/raw/enterprise-attack.json, ~48MB, gitignored - not
  committing raw upstream data).
- Confirmed all three target groups exist with expected ATT&CK IDs:
  APT29=G0016, APT28=G0007, Lazarus Group=G0032.
- Analyzed technique overlap across the three groups (234 unique
  techniques total) to pick a defensible 13-technique seed set - see
  docs/decisions/001-seed-scope.md.
- Verified the seed set includes the exact techniques used as worked
  examples in the technical brief (T1059.001, T1003.002, T1078),
  confirmed real for these groups against live MITRE data - not
  assumed.
- Built graph/seed_config.py (fixed seed list) and graph/build_graph.py
  (structural MultiDiGraph builder: Technique/Tactic/Group nodes,
  HAS_TACTIC/USES_TECHNIQUE edges, citation sources captured per edge
  where available).
- Ran end-to-end: 26 nodes (13 Technique, 10 Tactic, 3 Group), 54 edges
  (17 HAS_TACTIC, 37 USES_TECHNIQUE - 37 of 39 possible group-technique
  pairs exist, confirming strong real overlap).
- Next: semantic edges (Phase 2) - hand-author TEMPORALLY_PRECEDES /
  CAUSALLY_ENABLES relationships for a subset of technique pairs, each
  with a cited source, alongside the first docs/attack-patterns/ case
  files.
