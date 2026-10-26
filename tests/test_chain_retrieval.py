"""
Deterministic unit tests for query/retrieval.py's multi-hop chain
retrieval (get_chain_context()/format_chain_context() - see
docs/decisions/008-multi-hop-chain-retrieval.md and 009-single-group-
chains.md). Pure graph traversal, no LLM call - never skips, same
discipline as test_rag_guard.py.
"""
import pytest

from query.graph_loader import load_graph
from query.retrieval import format_chain_context, get_chain_context

graph = load_graph()


def test_direct_one_hop_chain_found():
    """T1566.001 --TEMPORALLY_PRECEDES--> T1204.002 is a real, direct
    APT29 edge - the chain path should be exactly that one hop."""
    context = get_chain_context(graph, ["T1566.001", "T1204.002"], group="APT29")
    (found,) = context["links"][0]["paths"]
    assert found["hops"] == 1
    assert found["path"][0]["edge_type"] == "TEMPORALLY_PRECEDES"
    assert found["path"][0]["from_technique"] == "T1566.001"
    assert found["path"][0]["to_technique"] == "T1204.002"


def test_two_hop_chain_found():
    """T1566.001 -> T1059.001 isn't a direct APT29 edge, but is reachable
    via T1204.002 (T1566.001->T1204.002->T1059.001) - the bounded BFS
    should find that 2-hop path, not report it unreachable."""
    context = get_chain_context(graph, ["T1566.001", "T1059.001"], group="APT29")
    (found,) = context["links"][0]["paths"]
    assert found["hops"] == 2
    assert [hop["edge_type"] for hop in found["path"]] == ["TEMPORALLY_PRECEDES", "CAUSALLY_ENABLES"]
    assert found["path"][0]["to_technique"] == found["path"][1]["from_technique"] == "T1204.002"


def test_no_path_reports_none_not_a_guess():
    """T1566.001 -> T1560.001 has no connecting APT29 semantic-edge path
    in this seed set - the BFS must say so explicitly (None), never
    fabricate or silently omit a connection."""
    context = get_chain_context(graph, ["T1566.001", "T1560.001"], group="APT29")
    assert context["links"][0]["paths"] == []


def test_three_technique_chain_has_two_links():
    context = get_chain_context(graph, ["T1566.001", "T1204.002", "T1059.001"], group="APT29")
    assert [t["technique_id"] for t in context["techniques"]] == ["T1566.001", "T1204.002", "T1059.001"]
    assert len(context["links"]) == 2
    assert context["links"][0]["from"] == "T1566.001" and context["links"][0]["to"] == "T1204.002"
    assert context["links"][1]["from"] == "T1204.002" and context["links"][1]["to"] == "T1059.001"


def test_group_filter_can_make_a_real_edge_unreachable():
    """The same T1566.001->T1204.002 edge exists for Lazarus Group too,
    but filtering to a group with no such edge must not leak another
    group's path across the filter boundary."""
    apt29_unfiltered_edge_exists = get_chain_context(graph, ["T1566.001", "T1204.002"], group="Lazarus Group")
    assert apt29_unfiltered_edge_exists["links"][0]["paths"]  # Lazarus Group does have this edge

    no_such_group_edge = get_chain_context(graph, ["T1566.001", "T1021.001"], group="Lazarus Group")
    assert no_such_group_edge["links"][0]["paths"] == []


def test_requires_at_least_two_technique_ids():
    with pytest.raises(ValueError):
        get_chain_context(graph, ["T1566.001"])


def test_invalid_technique_id_raises_same_as_single_hop_path():
    with pytest.raises(ValueError):
        get_chain_context(graph, ["T1566.001", "NOT-A-REAL-ID"])


def test_format_chain_context_never_fabricates_a_path():
    """format_chain_context()'s output for an unreachable link must say
    so in plain text - nothing for the LLM to misread as a real path."""
    context = get_chain_context(graph, ["T1566.001", "T1560.001"], group="APT29")
    text = format_chain_context(context)
    assert "no single-group semantic-edge path found" in text
    assert "hop 1:" not in text.split("Path T1566.001 -> T1560.001:")[1]


def test_unfiltered_chain_never_mixes_groups():
    """Regression for the 2026-10-26 review (docs/decisions/009): with no
    group filter, T1021.001 -> T1003.002 used to come back as an APT28
    hop, then an APT29 hop, then an APT28 hop - a sequence no single
    actor ran. Every returned path must now use one group's edges only,
    and the APT28-APT29-APT28 stitch must be gone."""
    context = get_chain_context(graph, ["T1021.001", "T1003.002"])
    for found in context["links"][0]["paths"]:
        assert {hop["group_context"] for hop in found["path"]} == {found["group"]}
    text = format_chain_context(context)
    assert "[APT29] T1059.001 (PowerShell) --TEMPORALLY_PRECEDES--> T1078" not in text.split("Path T1021.001")[1]


def test_unfiltered_chain_lists_each_groups_path_separately():
    """T1566.001 -> T1204.002 exists for both APT29 and Lazarus Group;
    unfiltered, both appear as separate one-group paths."""
    context = get_chain_context(graph, ["T1566.001", "T1204.002"])
    assert sorted(found["group"] for found in context["links"][0]["paths"]) == ["APT29", "Lazarus Group"]


def test_path_spanning_incidents_is_flagged():
    """A single group's edges can still come from different operations.
    APT29's T1566.001 -> T1204.002 -> T1059.001 -> T1078 joins a
    phishing-chain edge to an edge from a separate report, so the path
    must be flagged and the facts block must say it is not one observed
    intrusion."""
    context = get_chain_context(graph, ["T1566.001", "T1078"], group="APT29")
    (found,) = context["links"][0]["paths"]
    assert len(found["incidents"]) > 1 and found["spans_incidents"]
    assert "NOT one observed intrusion sequence" in format_chain_context(context)


def test_every_hop_carries_an_incident_field():
    context = get_chain_context(graph, ["T1566.001", "T1059.001"], group="APT29")
    for found in context["links"][0]["paths"]:
        for hop in found["path"]:
            assert "incident_id" in hop
