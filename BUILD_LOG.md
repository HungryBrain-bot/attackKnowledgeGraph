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

## 2026-08-13 - Semantic edges (Phase 2)

- Environment fix: `mitreattack-python` was not actually installed
  (Kali's system Python is externally managed, `pip install` refuses
  system-wide installs). Created a project `.venv` (already gitignored)
  and installed `requirements.txt` into it - `data/raw/enterprise-attack.json`
  was still present on disk from the Phase 1 session, so no re-download
  needed.
- Researched real, citable evidence for technique-pair sequencing/
  causality before writing any edges - pulled citations already
  verified real via the Phase 1 structural graph (MITRE STIX
  relationship objects), plus two directly-fetched primary reports:
  Volexity's "The Nearest Neighbor Attack" (Nov 2024, APT28 Wi-Fi
  pivot) and CISA AA24-207A (Aug 2024, Lazarus Group). Also confirmed
  Mandiant's UNC2452/APT29 writeup states Domain Admin was reached
  under 12 hours after the initial phishing payload executed - directly
  usable for a high-confidence PowerShell -> Valid Accounts edge.
- Designed the semantic edge schema as group-scoped (a `group_context`
  per edge, not a universal technique-to-technique claim) with
  `confidence` and `sample_size` given literal definitions rather than
  left vague - see docs/decisions/002-semantic-edge-schema.md.
- Built `graph/semantic_edges.py`: 9 edges (4 TEMPORALLY_PRECEDES, 5
  CAUSALLY_ENABLES) across APT29 (4 edges, SolarWinds/SUNBURST
  intrusion), APT28 (3 edges, Nearest Neighbor attack + GRU brute-force
  advisory), and Lazarus Group (2 edges, AA24-207A) - touching 9 of the
  13 seed techniques. Deliberately left T1003.002, T1057, T1105, and
  T1547.001 without edges this pass rather than force weakly-evidenced
  claims.
- Ran end-to-end: combined graph (structural + semantic) is 26 nodes,
  63 edges. `data/structural_graph.json` (Phase 1) untouched; new output
  saved to `data/graph_with_semantics.json`.
- Wrote 9 docs/attack-patterns/ case files, one per touched technique,
  following the attack-pattern-doc skill's five-section format.
- Next: extend semantic edge coverage to the remaining 4 techniques and
  consider cross-group comparison edges once evidence is found: then the
  Graph RAG query layer (traversal + LLM-formatted, cited answers).

## 2026-08-13 - Semantic edge coverage completed (remaining 4 techniques)

- Researched and added 7 new semantic edges covering the 4 techniques
  left out of the first pass (T1003.002, T1057, T1105, T1547.001) - all
  13 seed techniques now have at least one semantic edge.
- Found real sourcing without inventing anything: extended the existing
  APT29/SolarWinds discovery chain (T1078 -> T1057 -> T1083, using
  sources already verified real via the structural graph's MITRE
  citations); fetched Mandiant's UNC3524/"Eye Spy on Your Email" report
  directly, which explicitly narrates ingress tool transfer (QUIETEXIT
  backdoor) enabling SAM/LSA credential dumping via `reg save`; used
  Trend Micro's Pawn Storm Dec 2020 report (co-cited across
  T1059.001/T1105/T1547.001 for APT28) for two lower-confidence
  (0.65) edges, honestly scored lower because the exact mechanism
  couldn't be independently confirmed beyond co-citation.
- **Found and fixed a real error while sourcing the new work**: fetching
  the full Volexity "Nearest Neighbor Attack" report (needed to source
  a new T1078 -> T1003.002 edge) showed the previously-committed
  APT28 T1059.001 -> T1021.001 edge had the causality backwards. The
  actual documented sequence is RDP-into-a-pivot-host first, then the
  PowerShell Wi-Fi enumeration script runs from that foothold - not
  PowerShell enabling RDP as originally modeled. Reversed the edge to
  T1021.001 -> T1059.001, corrected the T1078 -> T1021.001 edge's
  evidence text (the RDP hop is into the intermediate organization's
  pivot host, not directly into the ultimate target), and updated both
  affected case files (T1021.001, T1059.001) with an explicit
  correction note rather than silently overwriting them. This was
  already pushed to origin/main before the error was caught - the fix
  is a new commit, not a rewrite of history.
- Added a new edge (`T1078 -> T1003.002`, APT28, confidence 0.85) for
  the second, distinct use of Valid Accounts in the Nearest Neighbor
  incident (Wi-Fi credentials into the target, separate from the
  earlier RDP credentials into the pivot host) - documented as two
  edges from the same T1078 node rather than inventing per-instance
  nodes, with the simplification called out explicitly in
  T1003.002's case file.
- Wrote 4 new docs/attack-patterns/ case files (T1003.002, T1057,
  T1105, T1547.001) and updated 3 existing ones (T1078, T1021.001,
  T1059.001, T1083) whose edges changed.
- Ran end-to-end: 26 nodes, 70 edges (37 USES_TECHNIQUE, 17 HAS_TACTIC,
  10 CAUSALLY_ENABLES, 6 TEMPORALLY_PRECEDES).
- Next: cross-group comparison edges; consider deeper sourcing for the
  0.65-confidence tier if time allows; then the Graph RAG query layer.
