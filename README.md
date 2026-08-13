# attck-graph

A knowledge-graph prototype over a scoped subset of MITRE ATT&CK, modeling
not just *which* techniques a threat group uses, but the relationships
between them - what tends to precede what, what enables what, and where
detection coverage gaps exist.

## Why

MITRE ATT&CK catalogs techniques as a taxonomy. It doesn't model sequence,
timing, prerequisites, or confidence - so knowing "APT29 uses T1059.001
and T1003" doesn't tell a defender what to expect next, how urgently, or
whether existing detections actually cover the path an attacker takes.
This project explores modeling that as a graph: structural ATT&CK data as
a base layer, hand-authored semantic edges (temporal/causal relationships,
cited against real sources) on top, and a small retrieval layer so the
graph can answer questions like "given this observed technique, what's
likely next and do we have coverage."

## Scope (honest version)

This is a prototype covering **10-15 techniques across 2-3 threat groups**,
not a production system:
- Structural graph (nodes, HAS_TECHNIQUE/USES_TECHNIQUE edges): real data
  via the official `mitreattack-python` library.
- Semantic edges (temporal/causal relationships): hand-authored against
  cited public CTI sources - not an automated extraction pipeline.
- Query layer: graph traversal + LLM-formatted answer, grounded in the
  retrieved subgraph only.

See `docs/attack-patterns/` for the per-technique writeups (what the
attack is, the gap in existing tooling, how it's modeled here, sources)
and `docs/decisions/` for engineering decision records.

## Status

Early build - see `BUILD_LOG.md` for session-by-session progress.

## Setup

```bash
pip install -r requirements.txt

# fetch the official MITRE ATT&CK STIX bundle (gitignored, ~48MB, not committed)
mkdir -p data/raw && curl -o data/raw/enterprise-attack.json \
  https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json

python -m graph.build_graph      # structural graph -> data/structural_graph.json
python -m graph.semantic_edges   # + semantic edges -> data/graph_with_semantics.json
```
