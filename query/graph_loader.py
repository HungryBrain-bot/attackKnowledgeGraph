"""
Graph RAG loader (Phase 3).

Loads the pre-built combined graph (data/graph_with_semantics.json,
produced by graph/semantic_edges.py) rather than rebuilding it from the
raw STIX bundle on every query - querying doesn't need
mitreattack-python or the 48MB raw file, only the already-serialized
graph artifact this project already commits to keep the phases visible
in the repo (see docs/decisions/002-semantic-edge-schema.md).
"""
import json
from pathlib import Path

import networkx as nx

GRAPH_PATH = Path(__file__).parent.parent / "data" / "graph_with_semantics.json"


def load_graph() -> nx.MultiDiGraph:
    if not GRAPH_PATH.exists():
        raise FileNotFoundError(
            f"{GRAPH_PATH} not found - run `python -m graph.semantic_edges` "
            "first to build it."
        )
    with open(GRAPH_PATH) as f:
        data = json.load(f)
    return nx.node_link_graph(data, edges="edges")
