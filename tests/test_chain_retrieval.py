"""
Deterministic unit tests for query/retrieval.py's multi-hop chain
retrieval (get_chain_context()/format_chain_context() - see
docs/decisions/008-multi-hop-chain-retrieval.md and 009-single-group-
chains.md). Pure graph traversal, no LLM call - never skips, same
discipline as test_rag_guard.py.

Two kinds of test: against the real audited graph (5 edges since the
2026-10-26 audit, docs/edge-audit.md), and against a small synthetic
graph for path-search behavior the real data is now too small to
exercise (two groups on one pair, a cross-group stitch, a path across
incidents). The synthetic edges are test fixtures, never graph data.
"""
import networkx as nx
import pytest

from query.graph_loader import load_graph
from query.retrieval import format_chain_context, get_chain_context

graph = load_graph()


def test_direct_one_hop_chain_found():
    """T1078 --CAUSALLY_ENABLES--> T1021.001 is a real, direct APT28
    edge - the chain path should be exactly that one hop."""
    context = get_chain_context(graph, ["T1078", "T1021.001"], group="APT28")
    (found,) = context["links"][0]["paths"]
    assert found["hops"] == 1
    assert found["path"][0]["edge_type"] == "CAUSALLY_ENABLES"
    assert found["path"][0]["from_technique"] == "T1078"
    assert found["path"][0]["to_technique"] == "T1021.001"


def test_bfs_returns_the_shortest_path():
    """APT28 reaches T1059.001 from T1078 both directly (GRU campaign)
    and via T1021.001 (Nearest Neighbor). BFS must return the 1-hop
    direct edge."""
    context = get_chain_context(graph, ["T1078", "T1059.001"], group="APT28")
    (found,) = context["links"][0]["paths"]
    assert found["hops"] == 1
    assert found["incidents"] == ["gru-brute-force-campaign-2019-2021"]


def test_no_path_reports_empty_not_a_guess():
    """T1204.002 -> T1003.002 has no connecting APT29 path - the BFS
    must say so explicitly (no paths), never fabricate a connection."""
    context = get_chain_context(graph, ["T1204.002", "T1003.002"], group="APT29")
    assert context["links"][0]["paths"] == []


def test_three_technique_chain_from_one_incident_is_not_flagged():
    """T1078 -> T1021.001 -> T1059.001 for APT28: two links, both from
    the Nearest Neighbor incident, so no cross-incident warning."""
    context = get_chain_context(graph, ["T1078", "T1021.001", "T1059.001"], group="APT28")
    assert [t["technique_id"] for t in context["techniques"]] == ["T1078", "T1021.001", "T1059.001"]
    assert len(context["links"]) == 2
    for link in context["links"]:
        (found,) = link["paths"]
        assert found["incidents"] == ["nearest-neighbor-2022"]
        assert not found["spans_incidents"]


def test_group_filter_can_make_a_real_edge_unreachable():
    """T1078 -> T1021.001 is an APT28 edge; filtering to APT29 must not
    leak APT28's path across the filter boundary."""
    assert get_chain_context(graph, ["T1078", "T1021.001"], group="APT28")["links"][0]["paths"]
    assert get_chain_context(graph, ["T1078", "T1021.001"], group="APT29")["links"][0]["paths"] == []


def test_requires_at_least_two_technique_ids():
    with pytest.raises(ValueError):
        get_chain_context(graph, ["T1566.001"])


def test_invalid_technique_id_raises_same_as_single_hop_path():
    with pytest.raises(ValueError):
        get_chain_context(graph, ["T1566.001", "NOT-A-REAL-ID"])


def test_format_chain_context_never_fabricates_a_path():
    """format_chain_context()'s output for an unreachable link must say
    so in plain text - nothing for the LLM to misread as a real path."""
    context = get_chain_context(graph, ["T1204.002", "T1003.002"], group="APT29")
    text = format_chain_context(context)
    assert "no single-group semantic-edge path found" in text
    assert "hop 1:" not in text.split("Path T1204.002 -> T1003.002:")[1]


def test_review_case_no_longer_returns_a_mixed_path():
    """The 2026-10-26 review's exact case: unfiltered T1021.001 ->
    T1003.002 used to return APT28, APT29, APT28 hops. Every returned
    path must use one group's edges only."""
    context = get_chain_context(graph, ["T1021.001", "T1003.002"])
    for found in context["links"][0]["paths"]:
        assert {hop["group_context"] for hop in found["path"]} == {found["group"]}


def test_every_hop_carries_incident_quote_and_url():
    context = get_chain_context(graph, ["T1078", "T1021.001", "T1059.001"], group="APT28")
    for link in context["links"]:
        for found in link["paths"]:
            for hop in found["path"]:
                assert hop["incident_id"] and hop["quote"] and hop["source_url"].startswith("https://")


# --- synthetic graph: path-search behavior (docs/decisions/009) ------------


def _synthetic_graph() -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    for tid in ("A", "B", "C", "D"):
        g.add_node(tid, node_type="Technique", name=tid, tactics=[], description="")

    def edge(src, tgt, group, incident):
        g.add_edge(
            src, tgt, edge_type="TEMPORALLY_PRECEDES", group_context=group, confidence=0.5,
            sample_size=1, sources=["fixture"], evidence="fixture", incident_id=incident,
            quote="fixture", source_url="https://example.invalid",
        )

    edge("A", "B", "G1", "i1")
    edge("B", "C", "G2", "i2")  # the only B -> C edge belongs to another group
    edge("C", "D", "G1", "i1")
    edge("A", "B", "G2", "i2")  # same pair documented for both groups
    edge("B", "D", "G2", "i3")  # G2 path A -> B -> D crosses incidents i2, i3
    return g


def test_unfiltered_search_never_stitches_groups():
    """G1 has A->B and C->D but no B->C; only G2 has B->C. An unfiltered
    A -> C search must not combine G1's A->B with G2's B->C - it should
    find G2's own A->B->C and nothing for G1."""
    context = get_chain_context(_synthetic_graph(), ["A", "C"])
    (found,) = context["links"][0]["paths"]
    assert found["group"] == "G2"
    assert {hop["group_context"] for hop in found["path"]} == {"G2"}


def test_unfiltered_search_lists_each_groups_path_separately():
    context = get_chain_context(_synthetic_graph(), ["A", "B"])
    assert sorted(found["group"] for found in context["links"][0]["paths"]) == ["G1", "G2"]


def test_path_spanning_incidents_is_flagged():
    context = get_chain_context(_synthetic_graph(), ["A", "D"], group="G2")
    (found,) = context["links"][0]["paths"]
    assert found["incidents"] == ["i2", "i3"] and found["spans_incidents"]
    assert "NOT one observed intrusion sequence" in format_chain_context(context)
