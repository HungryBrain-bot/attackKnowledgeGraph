"""
Graph RAG retrieval (Phase 3 + Phase 5 multi-hop extension).

Given one technique ID, or an ordered chain of technique IDs, traverses
the combined structural + semantic graph to build a structured set of
facts. This is the "R" in Graph RAG: pure graph traversal, no LLM
involved - the LLM in rag.py only ever sees what this module retrieves,
per this project's "LLM does not originate facts" rule (see CLAUDE.md,
Architecture).

WHY SINGLE-TECHNIQUE-CENTRIC, ONE HOP, BY DEFAULT (see docs/decisions/
003-query-layer-scope.md): every case file's "What This Enables" section
is already phrased as "technique X observed, group Y - what's next /
what enabled it" - that's the shape the semantic edges were actually
authored to answer. `get_technique_context()` retrieves exactly that.

MULTI-HOP CHAIN RETRIEVAL (see docs/decisions/008-multi-hop-chain-
retrieval.md): when a question names 2+ technique IDs in sequence,
`get_chain_context()` walks the semantic-edge graph between each
consecutive pair with a bounded BFS - still pure Python graph traversal,
no LLM, same grounding guarantee as the single-hop path. This replaces
the "rejected for this pass" multi-hop line in ADR 003 now that there's
a real need for it; see ADR 008 for why BFS/bounded-depth rather than an
unbounded search or an LLM-driven walk. Since 2026-10-26 a path never
mixes groups and is labelled with the incidents its hops come from (see
ADR 009).
"""
from __future__ import annotations

from collections import deque

import networkx as nx

SEMANTIC_EDGE_TYPES = ("TEMPORALLY_PRECEDES", "CAUSALLY_ENABLES")

# Bounded rather than unbounded: the semantic-edge graph is small (5
# audited edges since 2026-10-26) and a chain query only makes sense between
# techniques already roughly kill-chain-adjacent, so 4 hops is generous
# for anything this prototype's data actually supports. Revisit this if
# the semantic-edge set grows enough that 4 hops stops reaching
# genuinely connected techniques.
MAX_CHAIN_HOPS = 4


def _matches_group(data: dict, group: str | None) -> bool:
    return group is None or data.get("group_context", "").lower() == group.lower()


def _edge_core_fields(data: dict) -> dict:
    """Shared field extraction for edge facts - confidence/sample_size/
    sources/evidence/group_context/edge_type - used by both the one-hop
    `_edge_fact()` and the multi-hop `_hop_fact()` builders below."""
    return {
        "edge_type": data["edge_type"],
        "group_context": data["group_context"],
        "confidence": data["confidence"],
        "sample_size": data["sample_size"],
        "sources": data["sources"],
        "evidence": data["evidence"],
        "incident_id": data.get("incident_id"),
        "quote": data.get("quote"),
        "source_url": data.get("source_url"),
    }


def _edge_fact(g: nx.MultiDiGraph, other: str, data: dict, direction: str) -> dict:
    return {
        "direction": direction,
        "other_technique": other,
        "other_technique_name": g.nodes[other].get("name", other),
        **_edge_core_fields(data),
    }


def _hop_fact(g: nx.MultiDiGraph, source: str, target: str, data: dict) -> dict:
    return {
        "from_technique": source,
        "from_technique_name": g.nodes[source].get("name", source),
        "to_technique": target,
        "to_technique_name": g.nodes[target].get("name", target),
        **_edge_core_fields(data),
    }


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

    semantic_edges = [
        _edge_fact(g, target, data, "outgoing")
        for _, target, data in g.out_edges(technique_id, data=True)
        if data.get("edge_type") in SEMANTIC_EDGE_TYPES and _matches_group(data, group)
    ] + [
        _edge_fact(g, source, data, "incoming")
        for source, _, data in g.in_edges(technique_id, data=True)
        if data.get("edge_type") in SEMANTIC_EDGE_TYPES and _matches_group(data, group)
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


def _find_semantic_path(
    g: nx.MultiDiGraph,
    source: str,
    target: str,
    group: str,
    max_hops: int,
) -> list[dict] | None:
    """Bounded, early-exit BFS from `source` to `target` over directed
    semantic edges only (TEMPORALLY_PRECEDES/CAUSALLY_ENABLES) of ONE
    group, up to `max_hops` hops deep.

    `group` is required: a path is only ever built from one group's
    edges (docs/decisions/009). Before 2026-10-26 an unfiltered search
    walked every group's edges at once and could return an APT28 hop,
    then an APT29 hop, then an APT28 hop - a sequence no actor ran.

    BFS (not DFS) so the first path found is guaranteed shortest. Returns
    the ordered list of hop-facts connecting source to target, or None
    if no such path exists within max_hops.
    """
    if source == target:
        return []

    queue: deque[tuple[str, list[dict]]] = deque([(source, [])])
    visited = {source}

    while queue:
        node, path = queue.popleft()
        if len(path) >= max_hops:
            continue
        for _, next_node, data in g.out_edges(node, data=True):
            if data.get("edge_type") not in SEMANTIC_EDGE_TYPES or not _matches_group(data, group):
                continue
            if next_node in visited:
                continue
            new_path = path + [_hop_fact(g, node, next_node, data)]
            if next_node == target:
                return new_path
            visited.add(next_node)
            queue.append((next_node, new_path))

    return None


def semantic_edge_groups(g: nx.MultiDiGraph) -> list[str]:
    """Every group_context that has at least one semantic edge, sorted."""
    return sorted(
        {data["group_context"] for _, _, data in g.edges(data=True) if data.get("edge_type") in SEMANTIC_EDGE_TYPES}
    )


def _path_incidents(path: list[dict]) -> list[str]:
    """Distinct incident IDs a path's hops come from, in hop order.
    A hop with no incident_id counts as "unknown", which is itself a
    reason not to read the path as one observed sequence."""
    incidents: list[str] = []
    for hop in path:
        incident = hop.get("incident_id") or "unknown"
        if incident not in incidents:
            incidents.append(incident)
    return incidents


def get_chain_context(
    g: nx.MultiDiGraph,
    technique_ids: list[str],
    group: str | None = None,
    max_hops: int = MAX_CHAIN_HOPS,
) -> dict:
    """Multi-hop counterpart to `get_technique_context()`: builds a
    structured fact set for an ordered chain of 2+ techniques.

    Each technique in the chain gets its own one-hop context (reusing
    `get_technique_context()`, so validation and per-technique facts
    stay in one place). For each consecutive pair in `technique_ids`,
    does a bounded BFS over semantic edges to find the shortest
    connecting path, up to `max_hops` hops - still pure graph traversal,
    no LLM, same grounding guarantee as the single-hop path.

    Paths never mix groups (docs/decisions/009): with a `group` filter,
    each link gets at most that group's path; without one, each link
    gets one single-group path per group that has one, side by side and
    never stitched together. Every path also lists the incidents its
    hops come from, and `spans_incidents` is True when there is more
    than one (or an unknown one) - a single group's edges can still come
    from different operations, so such a path is not one observed
    intrusion.

    Raises ValueError if fewer than 2 technique IDs are given, or if any
    of them isn't a Technique node in the graph (via
    `get_technique_context()`).
    """
    if len(technique_ids) < 2:
        raise ValueError("get_chain_context needs at least 2 technique IDs - use get_technique_context for one")

    techniques = [get_technique_context(g, tid, group=group) for tid in technique_ids]
    groups = [group] if group is not None else semantic_edge_groups(g)

    links = []
    for source, target in zip(technique_ids, technique_ids[1:]):
        paths = []
        for candidate_group in groups:
            path = _find_semantic_path(g, source, target, candidate_group, max_hops)
            if path is None:
                continue
            incidents = _path_incidents(path)
            paths.append(
                {
                    "group": path[0]["group_context"] if path else candidate_group,
                    "path": path,
                    "hops": len(path),
                    "incidents": incidents,
                    "spans_incidents": len(incidents) > 1 or "unknown" in incidents,
                }
            )
        links.append({"from": source, "to": target, "paths": paths})

    return {
        "technique_ids": technique_ids,
        "group_filter": group,
        "max_hops": max_hops,
        "techniques": techniques,
        "links": links,
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
            f"incident: {e['incident_id'] or 'unknown'}, sources: {', '.join(e['sources'])}"
        )
        lines.append(f"    quote: \"{e['quote']}\" ({e['source_url']})")
        lines.append(f"    evidence: {e['evidence']}")

    return "\n".join(lines)


def format_chain_context(context: dict) -> str:
    """Renders a `get_chain_context()` dict into the plain-text facts
    block the LLM prompt is built from - same contract as
    `format_context()`: every field the LLM is allowed to use appears
    here, nothing more, including an explicit "no path found" line when
    a link's BFS came up empty (the LLM must not fill that gap from its
    own knowledge of ATT&CK)."""
    scope = f" (filtered to group: {context['group_filter']})" if context["group_filter"] else " (all groups)"
    lines = [
        f"CHAIN: {' -> '.join(context['technique_ids'])}",
        f"Max hops searched per link: {context['max_hops']}{scope}",
        "",
    ]

    for tech_context in context["techniques"]:
        lines.append(format_context(tech_context))
        lines.append("")

    lines.append(
        "Paths below are per group: each one uses a single group's edges, "
        "and hops from different groups are never combined into one sequence."
    )
    lines.append("")

    for link in context["links"]:
        lines.append(f"Path {link['from']} -> {link['to']}:")
        if link["from"] == link["to"]:
            lines.append("  (same technique - no hops needed)")
        elif not link["paths"]:
            lines.append(
                f"  (no single-group semantic-edge path found within {context['max_hops']} hops"
                + (f" for {context['group_filter']}" if context["group_filter"] else "")
                + ")"
            )
        for p in link["paths"]:
            if not p["path"]:
                continue
            lines.append(f"  [{p['group']}] {p['hops']}-hop path, incidents: {', '.join(p['incidents'])}")
            if p["spans_incidents"]:
                lines.append(
                    "  WARNING: this path joins edges from different (or unidentified) "
                    "incidents - it is NOT one observed intrusion sequence."
                )
            for hop_num, hop in enumerate(p["path"], start=1):
                lines.append(
                    f"  hop {hop_num}: [{hop['group_context']}] "
                    f"{hop['from_technique']} ({hop['from_technique_name']}) "
                    f"--{hop['edge_type']}--> "
                    f"{hop['to_technique']} ({hop['to_technique_name']})"
                )
                lines.append(
                    f"    confidence: {hop['confidence']}, sample_size: {hop['sample_size']}, "
                    f"incident: {hop['incident_id'] or 'unknown'}, sources: {', '.join(hop['sources'])}"
                )
                lines.append(f"    quote: \"{hop['quote']}\" ({hop['source_url']})")
                lines.append(f"    evidence: {hop['evidence']}")
        lines.append("")

    return "\n".join(lines)
