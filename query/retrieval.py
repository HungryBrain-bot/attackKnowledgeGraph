"""
Graph RAG retrieval (Phase 3).

Given a technique ID (and optionally a group), traverses the combined
structural + semantic graph to build a structured set of facts. This is
the "R" in Graph RAG: pure graph traversal, no LLM involved - the LLM in
rag.py only ever sees what this module retrieves, per this project's
"LLM does not originate facts" rule (see CLAUDE.md, Architecture).

WHY SINGLE-TECHNIQUE-CENTRIC, ONE HOP (see docs/decisions/003-query-
layer-scope.md): every case file's "What This Enables" section is
already phrased as "technique X observed, group Y - what's next / what
enabled it" - that's the shape the semantic edges were actually
authored to answer. This module retrieves exactly that: one technique's
structural usage plus its directly-connected semantic edges, optionally
filtered to one group. It does not walk multiple hops or resolve
multi-entity questions - a deliberate scope cut, not an oversight.
"""
from __future__ import annotations

import networkx as nx

SEMANTIC_EDGE_TYPES = ("TEMPORALLY_PRECEDES", "CAUSALLY_ENABLES")


def get_technique_context(g: nx.MultiDiGraph, technique_id: str, group: str | None = None) -> dict:
    """Builds a structured fact set for one technique.

    Includes the technique's own attributes, which groups structurally
    use it (USES_TECHNIQUE, with citation sources), and every semantic
    edge (TEMPORALLY_PRECEDES/CAUSALLY_ENABLES) touching it - incoming
    and outgoing. If `group` is given, semantic edges are filtered to
    that group's `group_context`; structural usage is left unfiltered
    so the caller can still see which groups actually use the technique
    at all.

    Raises ValueError if `technique_id` isn't a Technique node in the
    graph.
    """
    if technique_id not in g:
        raise ValueError(f"{technique_id} is not in the graph")

    node = g.nodes[technique_id]
    if node.get("node_type") != "Technique":
        raise ValueError(f"{technique_id} is a {node.get('node_type')}, not a Technique")

    used_by = [
        {"group": source, "sources": data.get("sources", [])}
        for source, _, data in g.in_edges(technique_id, data=True)
        if data.get("edge_type") == "USES_TECHNIQUE"
    ]

    def edge_fact(other: str, data: dict, direction: str) -> dict:
        return {
            "direction": direction,
            "other_technique": other,
            "other_technique_name": g.nodes[other].get("name", other),
            "edge_type": data["edge_type"],
            "group_context": data["group_context"],
            "confidence": data["confidence"],
            "sample_size": data["sample_size"],
            "sources": data["sources"],
            "evidence": data["evidence"],
        }

    def matches_group(data: dict) -> bool:
        return group is None or data.get("group_context", "").lower() == group.lower()

    semantic_edges = [
        edge_fact(target, data, "outgoing")
        for _, target, data in g.out_edges(technique_id, data=True)
        if data.get("edge_type") in SEMANTIC_EDGE_TYPES and matches_group(data)
    ] + [
        edge_fact(source, data, "incoming")
        for source, _, data in g.in_edges(technique_id, data=True)
        if data.get("edge_type") in SEMANTIC_EDGE_TYPES and matches_group(data)
    ]

    return {
        "technique_id": technique_id,
        "name": node.get("name"),
        "tactics": node.get("tactics", []),
        "description": node.get("description", ""),
        "used_by": used_by,
        "group_filter": group,
        "semantic_edges": semantic_edges,
    }


def format_context(context: dict) -> str:
    """Renders a retrieved context dict into the plain-text facts block
    the LLM prompt is built from. Deterministic and complete - every
    field the LLM is allowed to use appears here, nothing more."""
    lines = [
        f"TECHNIQUE: {context['technique_id']} - {context['name']}",
        f"Tactics: {', '.join(context['tactics']) or 'none listed'}",
        f"Description: {context['description']}",
        "",
    ]

    if context["used_by"]:
        lines.append("Used by (structural, from official MITRE ATT&CK data):")
        for u in context["used_by"]:
            sources = ", ".join(u["sources"]) or "MITRE ATT&CK"
            lines.append(f"  - {u['group']} (sources: {sources})")
    else:
        lines.append("Used by: no group in the seed set is recorded as using this technique.")
    lines.append("")

    scope = f" (filtered to group: {context['group_filter']})" if context["group_filter"] else " (all groups)"
    lines.append(f"Semantic edges{scope}:")
    if not context["semantic_edges"]:
        lines.append(
            "  (none - no hand-authored semantic edge touches this technique"
            + (f" for {context['group_filter']}" if context["group_filter"] else "")
            + ")"
        )
    for e in context["semantic_edges"]:
        if e["direction"] == "outgoing":
            arrow = (
                f"{context['technique_id']} --{e['edge_type']}--> "
                f"{e['other_technique']} ({e['other_technique_name']})"
            )
        else:
            arrow = (
                f"{e['other_technique']} ({e['other_technique_name']}) "
                f"--{e['edge_type']}--> {context['technique_id']}"
            )
        lines.append(f"  - [{e['group_context']}] {arrow}")
        lines.append(
            f"    confidence: {e['confidence']}, sample_size: {e['sample_size']}, "
            f"sources: {', '.join(e['sources'])}"
        )
        lines.append(f"    evidence: {e['evidence']}")

    return "\n".join(lines)
