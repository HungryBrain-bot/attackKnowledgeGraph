# CLAUDE.md

## Project

A knowledge-graph prototype over a subset of MITRE ATT&CK: 10-15
techniques across 2-3 threat groups, modeled as a NetworkX MultiDiGraph,
with hand-authored semantic edges (temporal/causal relationships between
techniques, not just "technique exists") and a small Graph RAG query
layer on top.

This is a scoped proof-of-concept, not a production platform. No live
CTI ingestion, no autonomous extraction pipeline, no multi-domain
expansion - all seed data and semantic edges are manually authored
against real, cited sources.

## Architecture

- `graph/` - graph construction: nodes (Tactic, Technique, Sub-technique,
  Group, Software) and edges (structural: HAS_TECHNIQUE, USES_TECHNIQUE;
  semantic: TEMPORALLY_PRECEDES, CAUSALLY_ENABLES, etc.)
- `ingestion/` - one-time/manual seed data loading (mitreattack-python
  for structural data, hand-authored JSON for semantic edges). NOT an
  automated pipeline in this prototype.
- `query/` - Graph RAG: traverse graph for a relevant subgraph, LLM
  formats it into a cited natural-language answer. LLM does not
  originate facts.
- `docs/attack-patterns/` - one case file per technique (problem,
  mechanics, how the graph models it, sources) - see
  `.claude/skills/attack-pattern-doc/SKILL.md`
- `docs/decisions/` - ADRs for real engineering decisions - see
  `.claude/skills/build-and-document/SKILL.md`
- `NOTES-private.md` - gitignored, personal/product-vision notes only.
  Never referenced by anything that gets committed.

## Conventions

- Every semantic edge carries confidence score + sample_size + a real
  citation, or is explicitly labeled an estimate. No invented data.
- Structural data (nodes, HAS_TECHNIQUE/USES_TECHNIQUE edges) comes from
  the official `mitreattack-python` library - real, not synthetic.
- Semantic edges (Phase 2 schema) are hand-authored for the prototype,
  not auto-extracted. This is a deliberate scope decision - see
  docs/decisions/ once written.

## Current status

Phase: Semantic edges built (Phase 2 of README's scope), on top of the
Phase 1 structural graph.

- `data/raw/enterprise-attack.json` - official MITRE ATT&CK STIX bundle,
  pulled live from MITRE's GitHub repo (not committed - regenerate with
  the curl command in graph/build_graph.py's module docstring context,
  or see BUILD_LOG.md).
- `graph/seed_config.py` - fixed seed set: 3 groups (APT29, APT28,
  Lazarus Group), 13 techniques spanning a full kill chain. See
  docs/decisions/001-seed-scope.md for why these specific groups/
  techniques.
- `graph/build_graph.py` - builds a NetworkX MultiDiGraph from real
  STIX data: Technique/Tactic/Group nodes, HAS_TACTIC/USES_TECHNIQUE
  structural edges. Verified output: 26 nodes, 54 edges.
  `data/structural_graph.json` is its serialized output (node_link
  format) - left untouched by Phase 2, see docs/decisions/002.
- `graph/semantic_edges.py` - adds 9 hand-authored, group-scoped
  TEMPORALLY_PRECEDES/CAUSALLY_ENABLES edges (4 groups of APT29, APT28,
  and Lazarus Group behavior) on top of the structural graph, each with
  a real citation, confidence score, and sample_size. Deliberately
  covers 9 of the 13 seed techniques, not all 13 - only pairs with
  citable sequencing/causal evidence were included this pass. See
  docs/decisions/002-semantic-edge-schema.md for the schema decisions
  (group-scoped, not universal; literal confidence/sample_size
  definitions) and the module's own docstring for full field docs.
  Combined output: `data/graph_with_semantics.json`, 26 nodes, 63 edges
  (37 USES_TECHNIQUE, 17 HAS_TACTIC, 5 CAUSALLY_ENABLES,
  4 TEMPORALLY_PRECEDES).
- `docs/attack-patterns/` - 9 case files, one per technique touched by a
  semantic edge this pass (T1566.001, T1204.002, T1059.001, T1078,
  T1083, T1021.001, T1560.001, T1074.002, T1071.001).
- Environment: `mitreattack-python` isn't available as a system package
  on this machine (Kali marks Python as externally managed) - use the
  project's `.venv` (gitignored, `python3 -m venv .venv && .venv/bin/pip
  install -r requirements.txt`) rather than the system `python3` to run
  anything in `graph/`.

Next: T1003.002, T1057, T1105, and T1547.001 have no semantic edges yet
(no citable sequencing evidence found this pass - see
docs/decisions/002); cross-group comparison edges (e.g. contrasting how
APT29 vs APT28 chain the same technique pair) are also unbuilt. After
that, the Graph RAG query layer.

## Do NOT

- Don't reproduce the full platform-pitch language (6-phase roadmap,
  6-gate validator, multi-agent ingestion pipeline) as if it's built or
  imminent. Document only what this prototype actually contains.
- Don't add real API keys/secrets anywhere.
- Don't invent confidence scores or campaign details without a citable
  source.
