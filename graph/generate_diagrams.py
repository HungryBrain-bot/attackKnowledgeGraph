"""
Data-driven Mermaid diagram generator (see .claude/skills/
generate-diagrams/SKILL.md for the full trigger/idempotency contract -
this docstring covers implementation, that skill covers when/why).

Reads data/graph_with_semantics.json (via query.graph_loader, the same
loader the query layer uses - not rebuilt from the raw STIX bundle) and
writes two kinds of diagram, both inside `<!-- BEGIN GENERATED -->` /
`<!-- END GENERATED -->` markers so hand-authored content around them is
never touched:

    python -m graph.generate_diagrams

- One Mermaid flowchart per seed technique (its direct incoming/
  outgoing semantic edges) into that technique's
  docs/attack-patterns/<ID>-*.md file, under a `## Flow` section.
- One master kill-chain diagram (all seed techniques, all semantic
  edges, colored by group_context) into README.md.

Every traversal is sorted by a stable key before being emitted - never
relies on graph/dict iteration order - so two runs against unchanged
data produce byte-identical output. This is verified by actually
running the script twice and diffing, not just asserted; see
BUILD_LOG.md for the result of that check.
"""
from __future__ import annotations

import re
from pathlib import Path

import networkx as nx

from query.graph_loader import load_graph

REPO_ROOT = Path(__file__).parent.parent
ATTACK_PATTERNS_DIR = REPO_ROOT / "docs" / "attack-patterns"
README_PATH = REPO_ROOT / "README.md"

SEMANTIC_EDGE_TYPES = ("TEMPORALLY_PRECEDES", "CAUSALLY_ENABLES")

BEGIN_MARKER = (
    "<!-- BEGIN GENERATED: graph/generate_diagrams.py "
    "(do not hand-edit; rerun the script) -->"
)
END_MARKER = "<!-- END GENERATED -->"

# A real, widely-used qualitative palette (seaborn's "deep" categorical
# colors) - just needs to be distinct per group, not anything fancier.
GROUP_COLORS = {
    "APT29": "#4C72B0",
    "APT28": "#C44E52",
    "Lazarus Group": "#55A868",
}


def _sanitize_node_id(technique_id: str) -> str:
    """Mermaid node IDs can't contain '.' - technique IDs can."""
    return "T_" + re.sub(r"[^0-9A-Za-z]", "_", technique_id)


def _node_label(g: nx.MultiDiGraph, technique_id: str) -> str:
    name = g.nodes[technique_id].get("name", technique_id)
    return f'{_sanitize_node_id(technique_id)}["{technique_id}<br/>{name}"]'


def _semantic_edges_touching(g: nx.MultiDiGraph, technique_id: str) -> list[dict]:
    """All semantic edges with `technique_id` as source or target,
    sorted by a stable key for deterministic output."""
    edges = []
    for source, target, data in g.out_edges(technique_id, data=True):
        if data.get("edge_type") in SEMANTIC_EDGE_TYPES:
            edges.append({"source": source, "target": target, **data})
    for source, target, data in g.in_edges(technique_id, data=True):
        if data.get("edge_type") in SEMANTIC_EDGE_TYPES:
            edges.append({"source": source, "target": target, **data})
    edges.sort(key=lambda e: (e["source"], e["target"], e["edge_type"], e["group_context"]))
    return edges


def _all_semantic_edges(g: nx.MultiDiGraph) -> list[dict]:
    edges = []
    for source, target, data in g.edges(data=True):
        if data.get("edge_type") in SEMANTIC_EDGE_TYPES:
            edges.append({"source": source, "target": target, **data})
    edges.sort(key=lambda e: (e["source"], e["target"], e["edge_type"], e["group_context"]))
    return edges


def technique_flow_diagram(g: nx.MultiDiGraph, technique_id: str) -> str:
    """Mermaid flowchart of one technique's direct semantic edges."""
    edges = _semantic_edges_touching(g, technique_id)

    involved = {technique_id}
    for e in edges:
        involved.add(e["source"])
        involved.add(e["target"])
    ordered_nodes = [technique_id] + sorted(involved - {technique_id})

    lines = ["```mermaid", "flowchart LR"]
    for tid in ordered_nodes:
        lines.append(f"    {_node_label(g, tid)}")
    if not edges:
        lines.append(f"    %% no semantic edges touch {technique_id} yet")
    for e in edges:
        s = _sanitize_node_id(e["source"])
        t = _sanitize_node_id(e["target"])
        label = f"{e['edge_type']}<br/>{e['group_context']}, {e['confidence']}"
        arrow = "-.->" if e["edge_type"] == "TEMPORALLY_PRECEDES" else "-->"
        lines.append(f'    {s} {arrow}|"{label}"| {t}')
    lines.append("```")
    return "\n".join(lines)


def kill_chain_diagram(g: nx.MultiDiGraph, technique_ids: list[str]) -> str:
    """Master Mermaid flowchart: every seed technique, every semantic
    edge, colored by group_context, dashed for TEMPORALLY_PRECEDES vs
    solid for CAUSALLY_ENABLES."""
    edges = _all_semantic_edges(g)

    lines = ["```mermaid", "flowchart LR"]
    for tid in sorted(technique_ids):
        lines.append(f"    {_node_label(g, tid)}")

    link_colors = []
    for e in edges:
        s = _sanitize_node_id(e["source"])
        t = _sanitize_node_id(e["target"])
        label = f"{e['group_context']}"
        arrow = "-.->" if e["edge_type"] == "TEMPORALLY_PRECEDES" else "-->"
        lines.append(f'    {s} {arrow}|"{label}"| {t}')
        link_colors.append(GROUP_COLORS.get(e["group_context"], "#888888"))

    for i, color in enumerate(link_colors):
        lines.append(f"    linkStyle {i} stroke:{color},stroke-width:2px")

    legend = ", ".join(f"{group} = `{color}`" for group, color in sorted(GROUP_COLORS.items()))
    lines.append("```")
    lines.append("")
    lines.append(
        f"*Edge color by group: {legend}. Dashed = TEMPORALLY_PRECEDES, "
        "solid = CAUSALLY_ENABLES.*"
    )
    return "\n".join(lines)


def _upsert_generated_section(text: str, heading: str, body: str) -> str:
    """Replaces the GENERATED block inside a `## <heading>` section, or
    inserts a new one if absent. The boundary that matters is the marker
    comments, not the heading text: once markers exist, only the content
    between them is ever touched. On first insertion (no markers yet),
    the block is placed at the *end* of the heading's section - after
    any hand-written prose already there, before the next `## ` heading
    or EOF - so a hand-authored intro paragraph under the heading stays
    above the diagram, not stranded below it."""
    block = f"{BEGIN_MARKER}\n{body}\n{END_MARKER}"

    marker_pattern = re.compile(re.escape(BEGIN_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL)
    if marker_pattern.search(text):
        return marker_pattern.sub(block, text, count=1)

    section_pattern = re.compile(
        rf"(^## {re.escape(heading)}\s*\n)(.*?)(?=\n## |\Z)",
        re.DOTALL | re.MULTILINE,
    )
    m = section_pattern.search(text)
    if m:
        existing_body = m.group(2).rstrip("\n")
        new_section = (
            f"{m.group(1)}{existing_body}\n\n{block}\n"
            if existing_body
            else f"{m.group(1)}\n{block}\n"
        )
        return text[: m.start()] + new_section + text[m.end() :]

    # No heading at all yet - append a brand new section at the end.
    if not text.endswith("\n"):
        text += "\n"
    if not text.endswith("\n\n"):
        text += "\n"
    return text + f"## {heading}\n\n{block}\n"


def write_technique_flow_diagrams(g: nx.MultiDiGraph, technique_ids: list[str]) -> None:
    for tid in sorted(technique_ids):
        matches = sorted(ATTACK_PATTERNS_DIR.glob(f"{tid}-*.md"))
        if not matches:
            raise FileNotFoundError(
                f"No docs/attack-patterns/ case file found for {tid} - "
                "generate_diagrams.py only writes into existing case files, "
                "it doesn't create them."
            )
        case_file = matches[0]
        diagram = technique_flow_diagram(g, tid)
        text = case_file.read_text()
        text = _upsert_generated_section(text, "Flow", diagram)
        case_file.write_text(text)


def write_kill_chain_diagram(g: nx.MultiDiGraph, technique_ids: list[str]) -> None:
    diagram = kill_chain_diagram(g, technique_ids)
    text = README_PATH.read_text()
    text = _upsert_generated_section(text, "Technique Relationship Graph", diagram)
    README_PATH.write_text(text)


def main() -> None:
    g = load_graph()
    technique_ids = sorted(
        n for n, data in g.nodes(data=True) if data.get("node_type") == "Technique"
    )
    write_technique_flow_diagrams(g, technique_ids)
    write_kill_chain_diagram(g, technique_ids)
    print(
        f"Regenerated {len(technique_ids)} per-technique flow diagrams "
        "and the README kill-chain diagram."
    )


if __name__ == "__main__":
    main()
