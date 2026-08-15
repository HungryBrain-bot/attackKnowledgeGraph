"""
Interactive pyvis visualization of data/graph_with_semantics.json.

    python -m visualize.render_graph

Writes docs/graph_visualization.html: a single HTML file (vis-network
inlined via cdn_resources="in_line", no external JS/CSS fetch needed to draw
the graph itself) that:

- Colors/shapes nodes by node_type (Technique = dot, Tactic = box, Group =
  star colored per the same GROUP_COLORS palette graph/generate_diagrams.py
  uses for its Mermaid diagrams, so a group means the same color everywhere
  in the repo), sized by degree (in + out, counting parallel edges).
- Adds a client-side group filter (one button per SEED_GROUPS group) that
  dims every node/edge NOT directly connected to the selected group, without
  removing anything - the "what's shared across groups" view stays visible,
  just de-emphasized.
- Styles structural edges (USES_TECHNIQUE, HAS_TACTIC) distinctly from
  semantic edges (TEMPORALLY_PRECEDES, CAUSALLY_ENABLES): semantic edges are
  colored per group_context, dashed for TEMPORALLY_PRECEDES vs solid for
  CAUSALLY_ENABLES (matching generate_diagrams.py's Mermaid convention), and
  their line width/opacity scales with `confidence`.
- Gives every semantic edge a hover tooltip with its real confidence,
  sample_size, sources, and evidence text, and every USES_TECHNIQUE edge a
  tooltip with its sources - the "every claim is sourced" property this
  project holds to in prose should be visible in the graph itself.

Regenerate whenever data/graph_with_semantics.json changes (same trigger
condition as .claude/skills/generate-diagrams). Same idempotency guarantee
as that skill: every traversal below is sorted by a stable key and no
timestamps/random IDs are emitted, so two runs against unchanged input data
produce byte-identical output.
"""
from __future__ import annotations

import html
from collections import Counter
from pathlib import Path

import networkx as nx
from pyvis.network import Network

from graph.generate_diagrams import GROUP_COLORS
from query.graph_loader import load_graph

REPO_ROOT = Path(__file__).parent.parent
OUTPUT_PATH = REPO_ROOT / "docs" / "graph_visualization.html"

STRUCTURAL_EDGE_TYPES = ("USES_TECHNIQUE", "HAS_TACTIC")
SEMANTIC_EDGE_TYPES = ("TEMPORALLY_PRECEDES", "CAUSALLY_ENABLES")

NODE_TYPE_BASE_STYLE = {
    "Technique": {"shape": "dot", "color": "#6C7A89"},
    "Tactic": {"shape": "box", "color": "#D9A441"},
    # Group nodes get their color from GROUP_COLORS instead - see _style_node.
}

STRUCTURAL_EDGE_COLOR = "#B5B5B5"
DIMMED_OPACITY = 0.08
MIN_NODE_SIZE = 12
NODE_SIZE_PER_DEGREE = 2.5
MAX_NODE_SIZE = 45
MIN_SEMANTIC_WIDTH = 1.5
MAX_SEMANTIC_WIDTH = 7.0


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "..."


def _tooltip(lines: list[str]) -> str:
    """Joins lines with a real newline, not `<br>`.

    vis-network's Popup renders a string `title` via `element.innerText =
    title` (confirmed by reading the inlined vis-network 9.1.2 source in a
    generated output file - not assumed from memory of vis-network's docs,
    which is what produced this bug the first time). `innerText`'s setter
    is a plain-text assignment: it never parses its input as HTML, so a
    literal `<br>` shows up on screen as the four characters `<br>` instead
    of a line break, and `\\n` is what actually renders as one. It also
    means this string must NOT be HTML-escaped - `innerText` doesn't decode
    entities either, so an `html.escape()`'d `&` would render on screen as
    the literal text `&amp;` instead of `&`. Because the renderer is
    `innerText` rather than `innerHTML`, this content is inert even if it
    contained real markup - do not "fix" that by escaping it again; escape
    only if this ever moves to an `innerHTML`-based tooltip instead (see
    docs/security-assessment.md's 2026-08-16 finding).
    """
    return "\n".join(lines)


def _node_size(degree: int) -> float:
    return min(MAX_NODE_SIZE, MIN_NODE_SIZE + degree * NODE_SIZE_PER_DEGREE)


def _node_tooltip(node_type: str, data: dict, degree: int) -> str:
    if node_type == "Technique":
        return _tooltip(
            [
                f"{data['attack_id']} - {data['name']}",
                f"Tactics: {', '.join(sorted(data.get('tactics', [])))}",
                f"Connections: {degree}",
                "",
                _truncate(data.get("description", ""), 400),
            ]
        )
    if node_type == "Tactic":
        return _tooltip([f"Tactic: {data['name']}", f"Connections: {degree}"])
    aliases = sorted(data.get("aliases", []))
    shown = ", ".join(aliases[:5]) + ("..." if len(aliases) > 5 else "")
    return _tooltip(
        [
            f"{data['name']} ({data['attack_id']})",
            f"Aliases: {shown}",
            f"Connections: {degree}",
        ]
    )


def _edge_tooltip(edge_type: str, source: str, target: str, data: dict) -> str:
    if edge_type == "HAS_TACTIC":
        return _tooltip(
            [f"{source} HAS_TACTIC {target}", "structural - official MITRE ATT&CK data"]
        )
    if edge_type == "USES_TECHNIQUE":
        return _tooltip(
            [
                f"{source} USES_TECHNIQUE {target}",
                "structural - official MITRE ATT&CK data",
                f"Sources: {', '.join(data.get('sources', []))}",
            ]
        )
    return _tooltip(
        [
            f"[{data['group_context']}] {source} --{edge_type}--> {target}",
            f"Confidence: {data['confidence']} | Sample size: {data['sample_size']}",
            f"Sources: {', '.join(data.get('sources', []))}",
            "",
            _truncate(data.get("evidence", ""), 600),
        ]
    )


def _style_node(g: nx.MultiDiGraph, node_id: str, data: dict) -> dict:
    node_type = data["node_type"]
    degree = g.degree(node_id)
    style = dict(NODE_TYPE_BASE_STYLE.get(node_type, {"shape": "dot", "color": "#888888"}))
    style["size"] = _node_size(degree)
    style["label"] = data.get("attack_id") or data["name"]
    style["title"] = _node_tooltip(node_type, data, degree)
    style["node_type"] = node_type
    if node_type == "Group":
        style["shape"] = "star"
        style["color"] = GROUP_COLORS.get(data["name"], "#888888")
        style["group_name"] = data["name"]
    return style


def _semantic_edge_style(edge_type: str, data: dict) -> dict:
    confidence = data["confidence"]
    color = GROUP_COLORS.get(data["group_context"], "#888888")
    return {
        "color": {"color": color, "opacity": confidence},
        "width": MIN_SEMANTIC_WIDTH + confidence * (MAX_SEMANTIC_WIDTH - MIN_SEMANTIC_WIDTH),
        "dashes": edge_type == "TEMPORALLY_PRECEDES",
        "base_opacity": confidence,
    }


def _structural_edge_style() -> dict:
    return {
        "color": {"color": STRUCTURAL_EDGE_COLOR, "opacity": 0.5},
        "width": 1,
        "dashes": False,
        "base_opacity": 0.5,
    }


def _parallel_edge_counts(g: nx.MultiDiGraph) -> Counter:
    return Counter((s, t) for s, t in g.edges(keys=False))


def build_network(g: nx.MultiDiGraph) -> Network:
    net = Network(
        height="800px",
        width="100%",
        directed=True,
        cdn_resources="in_line",
        bgcolor="#ffffff",
    )
    net.set_options(
        """
        {
          "layout": {"randomSeed": 42},
          "interaction": {"hover": true, "tooltipDelay": 120, "navigationButtons": true},
          "physics": {
            "solver": "barnesHut",
            "barnesHut": {"gravitationalConstant": -12000, "springLength": 140},
            "stabilization": {"iterations": 300}
          }
        }
        """
    )

    for node_id in sorted(g.nodes()):
        data = g.nodes[node_id]
        net.add_node(node_id, **_style_node(g, node_id, data))

    parallel_counts = _parallel_edge_counts(g)
    edges = sorted(
        g.edges(keys=True, data=True), key=lambda e: (e[0], e[1], e[3]["edge_type"], e[2])
    )
    for source, target, key, data in edges:
        edge_type = data["edge_type"]
        style = (
            _semantic_edge_style(edge_type, data)
            if edge_type in SEMANTIC_EDGE_TYPES
            else _structural_edge_style()
        )
        style["title"] = _edge_tooltip(edge_type, source, target, data)
        style["edge_type"] = edge_type
        if edge_type in SEMANTIC_EDGE_TYPES:
            style["group_context"] = data["group_context"]
        style["id"] = f"{edge_type}|{source}|{target}|{key}"
        if parallel_counts[(source, target)] > 1:
            style["smooth"] = {
                "enabled": True,
                "type": "curvedCW",
                "roundness": min(0.1 + 0.2 * key, 0.7),
            }
        net.add_edge(source, target, **style)

    return net


def _group_names(g: nx.MultiDiGraph) -> list[str]:
    return sorted(data["name"] for _, data in g.nodes(data=True) if data["node_type"] == "Group")


CONTROLS_TEMPLATE = """
<div id="graph-controls" style="font-family: sans-serif; padding: 12px 16px; border-bottom: 1px solid #ddd;">
  <div style="margin-bottom: 8px;">
    <strong>Filter by group:</strong>
    <button type="button" class="group-filter-btn active" data-group="" onclick="applyGroupFilter('')">All groups</button>
    {group_buttons}
  </div>
  <div style="font-size: 0.85em; color: #444; line-height: 1.6;">
    <strong>Legend:</strong>
    &nbsp;&#9679; Technique &nbsp; &#9632; Tactic &nbsp; &#9733; Group (colored by group) &nbsp;|&nbsp;
    gray edge = structural (USES_TECHNIQUE / HAS_TACTIC) &nbsp;|&nbsp;
    colored solid edge = CAUSALLY_ENABLES &nbsp; colored dashed edge = TEMPORALLY_PRECEDES
    &nbsp;(color = group_context, width/opacity = confidence) &nbsp;|&nbsp;
    hover any edge for its citation, confidence, and sample_size.
  </div>
</div>
<style>
  .group-filter-btn {{
    margin-right: 6px; padding: 4px 10px; border: 1px solid #999; border-radius: 4px;
    background: #f5f5f5; cursor: pointer; font-size: 0.9em;
  }}
  .group-filter-btn.active {{ background: #333; color: #fff; border-color: #333; }}
</style>
"""

FILTER_SCRIPT_TEMPLATE = """
<script type="text/javascript">
  function nodeIsRelevant(nodeId, group) {{
    var n = allNodes[nodeId];
    if (n.node_type === 'Group') return n.group_name === group;
    for (var key in allEdges) {{
      var e = allEdges[key];
      if (e.from !== nodeId && e.to !== nodeId) continue;
      if (edgeIsRelevant(e, group)) return true;
    }}
    return false;
  }}

  function edgeIsRelevant(e, group) {{
    if (e.edge_type === 'USES_TECHNIQUE') return e.from === group;
    if (e.edge_type === 'TEMPORALLY_PRECEDES' || e.edge_type === 'CAUSALLY_ENABLES') {{
      return e.group_context === group;
    }}
    return false;
  }}

  function applyGroupFilter(group) {{
    var nodeUpdates = [];
    var edgeUpdates = [];
    for (var id in allNodes) {{
      var relevant = !group || nodeIsRelevant(id, group);
      nodeUpdates.push({{id: id, opacity: relevant ? 1.0 : {dimmed}}});
    }}
    for (var key in allEdges) {{
      var e = allEdges[key];
      var relevant = !group || edgeIsRelevant(e, group);
      var opacity = relevant ? (e.base_opacity !== undefined ? e.base_opacity : 1.0) : {dimmed};
      edgeUpdates.push({{id: e.id, color: {{opacity: opacity}}}});
    }}
    nodes.update(nodeUpdates);
    edges.update(edgeUpdates);
    document.querySelectorAll('.group-filter-btn').forEach(function (b) {{
      b.classList.toggle('active', b.dataset.group === group);
    }});
  }}

  network.once('stabilizationIterationsDone', function () {{
    network.setOptions({{physics: false}});
  }});
</script>
"""


def _inject_controls(html_text: str, group_names: list[str]) -> str:
    buttons = "\n    ".join(
        f'<button type="button" class="group-filter-btn" data-group="{html.escape(name)}" '
        f'onclick="applyGroupFilter(\'{html.escape(name)}\')">{html.escape(name)}</button>'
        for name in group_names
    )
    controls = CONTROLS_TEMPLATE.format(group_buttons=buttons)
    html_text = html_text.replace("<body>", "<body>\n" + controls, 1)

    script = FILTER_SCRIPT_TEMPLATE.format(dimmed=DIMMED_OPACITY)
    html_text = html_text.replace("</body>", script + "\n</body>", 1)
    return html_text


def render(g: nx.MultiDiGraph) -> str:
    net = build_network(g)
    html_text = net.generate_html(notebook=False)
    return _inject_controls(html_text, _group_names(g))


def main() -> None:
    g = load_graph()
    html_text = render(g)
    OUTPUT_PATH.write_text(html_text)
    print(f"Wrote {OUTPUT_PATH} ({len(g.nodes())} nodes, {len(g.edges())} edges).")


if __name__ == "__main__":
    main()
