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

Phase: Structural graph built (Phase 1 of README's scope).

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
- `data/structural_graph.json` - serialized graph output (node_link
  format).

Next: semantic edges (TEMPORALLY_PRECEDES, CAUSALLY_ENABLES, etc.),
hand-authored per docs/attack-patterns/ case files, then the Graph RAG
query layer.

## Do NOT

- Don't reproduce the full platform-pitch language (6-phase roadmap,
  6-gate validator, multi-agent ingestion pipeline) as if it's built or
  imminent. Document only what this prototype actually contains.
- Don't add real API keys/secrets anywhere.
- Don't invent confidence scores or campaign details without a citable
  source.
