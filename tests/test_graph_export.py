"""Export format version: the committed graph JSON and the loader agree.

Tests only the `schema_version` stamp. It does not check that the
fields on each node or edge match that version - a field change without
a version bump would still pass here.
"""
import json

import pytest

from graph.semantic_edges import SCHEMA_VERSION
from query import graph_loader


@pytest.mark.parametrize(
    "name", ["graph_with_semantics.json", "structural_graph.json"]
)
def test_committed_json_carries_current_schema_version(name):
    path = graph_loader.GRAPH_PATH.parent / name
    data = json.loads(path.read_text())
    assert data["graph"]["schema_version"] == SCHEMA_VERSION


def test_loader_accepts_current_version():
    g = graph_loader.load_graph()
    assert g.graph["schema_version"] == SCHEMA_VERSION


@pytest.mark.parametrize("graph_attrs", [{}, {"schema_version": SCHEMA_VERSION + 1}])
def test_loader_rejects_missing_or_other_version(tmp_path, monkeypatch, graph_attrs):
    data = json.loads(graph_loader.GRAPH_PATH.read_text())
    data["graph"] = graph_attrs
    stale = tmp_path / "graph_with_semantics.json"
    stale.write_text(json.dumps(data))
    monkeypatch.setattr(graph_loader, "GRAPH_PATH", stale)
    with pytest.raises(ValueError, match="schema_version"):
        graph_loader.load_graph()
