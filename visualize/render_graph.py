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
  semantic edges (TEMPORALLY_PRECEDES, CAUSALLY_ENABLES) and from each
  other (USES_TECHNIQUE darker/heavier - the actual "who does what" fact -
  HAS_TACTIC lighter/thinner - every technique has exactly one, so it
  carries less information and should recede): semantic edges are colored
  per group_context, dashed for TEMPORALLY_PRECEDES vs solid for
  CAUSALLY_ENABLES (matching generate_diagrams.py's Mermaid convention),
  with `confidence` driving line width. Semantic edge opacity is a fixed,
  legible constant rather than confidence-driven - the dataviz skill's
  palette validator flagged low-opacity edge colors as failing contrast
  against the canvas at the low end of the confidence range, so width
  alone now carries that signal and opacity stays readable regardless of
  confidence (see BUILD_LOG.md's beautification-pass entry).
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

# Neutral tokens, chosen with the dataviz skill's `validate_palette.js`
# (light mode, run against this exact CANVAS_BG surface - see BUILD_LOG.md).
# Technique's color intentionally fails the validator's categorical
# chroma-floor check ("reads gray") - that's deliberate, not an oversight:
# Technique nodes shouldn't visually read as belonging to any one hue
# category the way the 3 GROUP_COLORS do, and shape (dot) already
# distinguishes them from Tactic (box) and Group (star). GROUP_COLORS
# itself is untouched - it's graph/generate_diagrams.py's existing,
# already-shared palette, and changing it here would break the "a group
# means the same color everywhere in the repo" property this module was
# built to preserve.
CANVAS_BG = "#fcfcfb"
HEADER_BG = "#f9f9f7"
HEADER_BORDER = "#d8d6cc"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
TOOLTIP_BORDER = "#d8d6cc"

NODE_TYPE_BASE_STYLE = {
    "Technique": {"shape": "dot", "color": "#4C5A70"},
    "Tactic": {"shape": "box", "color": "#B8760F"},
    # Group nodes get their color from GROUP_COLORS instead - see _style_node.
}

# USES_TECHNIQUE is the actual "who does what" structural fact and stays
# darker/heavier; HAS_TACTIC is a one-per-technique categorization edge
# that carries little information on its own, so it recedes lighter/
# thinner rather than competing visually with it or with semantic edges.
HAS_TACTIC_COLOR = "#c9c7bd"
HAS_TACTIC_OPACITY = 0.55
USES_TECHNIQUE_COLOR = "#726f66"
USES_TECHNIQUE_OPACITY = 0.8
SEMANTIC_EDGE_OPACITY = 0.85

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
    docs/security-assessment.md's 2026-08-15 web-security finding).
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


def _darken_hex(hex_color: str, factor: float = 0.72) -> str:
    """Darkens a hex color for a node's border, so filled shapes have a
    visible edge against CANVAS_BG instead of blending into their own fill."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    r, g, b = (max(0, int(c * factor)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def _style_node(g: nx.MultiDiGraph, node_id: str, data: dict) -> dict:
    node_type = data["node_type"]
    degree = g.degree(node_id)
    base = NODE_TYPE_BASE_STYLE.get(node_type, {"shape": "dot", "color": "#888888"})
    fill = GROUP_COLORS.get(data["name"], "#888888") if node_type == "Group" else base["color"]
    style = {
        "shape": "star" if node_type == "Group" else base["shape"],
        "color": {
            "background": fill,
            "border": _darken_hex(fill),
            "highlight": {"background": fill, "border": _darken_hex(fill, 0.5)},
        },
        "size": _node_size(degree),
        "label": data.get("attack_id") or data["name"],
        "title": _node_tooltip(node_type, data, degree),
        "node_type": node_type,
    }
    if node_type == "Group":
        style["group_name"] = data["name"]
    return style


def _semantic_edge_style(edge_type: str, data: dict) -> dict:
    confidence = data["confidence"]
    color = GROUP_COLORS.get(data["group_context"], "#888888")
    return {
        "color": {"color": color, "opacity": SEMANTIC_EDGE_OPACITY},
        "width": MIN_SEMANTIC_WIDTH + confidence * (MAX_SEMANTIC_WIDTH - MIN_SEMANTIC_WIDTH),
        "dashes": edge_type == "TEMPORALLY_PRECEDES",
        "base_opacity": SEMANTIC_EDGE_OPACITY,
    }


def _structural_edge_style(edge_type: str) -> dict:
    if edge_type == "USES_TECHNIQUE":
        color, width, opacity = USES_TECHNIQUE_COLOR, 1.5, USES_TECHNIQUE_OPACITY
    else:  # HAS_TACTIC
        color, width, opacity = HAS_TACTIC_COLOR, 1, HAS_TACTIC_OPACITY
    return {
        "color": {"color": color, "opacity": opacity},
        "width": width,
        "dashes": False,
        "base_opacity": opacity,
    }


def _parallel_edge_counts(g: nx.MultiDiGraph) -> Counter:
    return Counter((s, t) for s, t in g.edges(keys=False))


def build_network(g: nx.MultiDiGraph) -> Network:
    net = Network(
        height="800px",
        width="100%",
        directed=True,
        cdn_resources="in_line",
        bgcolor=CANVAS_BG,
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
            else _structural_edge_style(edge_type)
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


ALL_GROUPS_BTN_COLOR = "#3a3a37"


def _dot_swatch(color: str) -> str:
    return (
        f'<span class="legend-swatch" style="width:10px; height:10px; '
        f'border-radius:50%; background:{color};"></span>'
    )


def _box_swatch(color: str) -> str:
    return f'<span class="legend-swatch" style="width:10px; height:10px; background:{color};"></span>'


def _star_swatch(color: str) -> str:
    return f'<span class="legend-swatch" style="color:{color}; font-size:14px;">&#9733;</span>'


def _line_swatch(color: str, dashed: bool = False) -> str:
    border = "dashed" if dashed else "solid"
    return (
        f'<span class="legend-swatch" style="width:22px; height:0; '
        f'border-top:3px {border} {color}; background:none;"></span>'
    )


CONTROLS_TEMPLATE = """
<div id="graph-controls">
  <div class="controls-row">
    <span class="controls-label">Filter by group:</span>
    <button type="button" class="group-filter-btn active" data-group=""
      style="--btn-color: {all_groups_color};" onclick="applyGroupFilter('')">All groups</button>
    {group_buttons}
  </div>
  <div class="legend-row">
    <span><strong>Nodes:</strong></span>
    <span>{technique_swatch} Technique</span>
    <span>{tactic_swatch} Tactic</span>
    <span>{group_swatch} Group (colored by group)</span>
    <span><strong>Edges:</strong></span>
    <span>{uses_swatch} USES_TECHNIQUE</span>
    <span>{tactic_edge_swatch} HAS_TACTIC</span>
    <span>{causally_swatch} CAUSALLY_ENABLES (colored by group)</span>
    <span>{temporally_swatch} TEMPORALLY_PRECEDES (colored by group)</span>
    <span>width = confidence &middot; hover any edge for its citation, confidence, and sample_size</span>
  </div>
</div>
<style>
  #graph-controls {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: {header_bg};
    border-bottom: 2px solid {header_border};
    padding: 14px 20px;
  }}
  #graph-controls .controls-row {{
    display: flex; align-items: center; gap: 8px; margin-bottom: 10px; flex-wrap: wrap;
  }}
  #graph-controls .controls-label {{
    font-weight: 600; color: {text_primary}; font-size: 0.9em; margin-right: 4px;
  }}
  #graph-controls .legend-row {{
    font-size: 0.82em; color: {text_secondary}; line-height: 1.8;
    display: flex; flex-wrap: wrap; gap: 4px 18px; align-items: center;
  }}
  .legend-swatch {{ display: inline-block; vertical-align: middle; margin-right: 5px; }}
  .group-filter-btn {{
    padding: 5px 14px; border-radius: 16px; border: 1.5px solid #c3c2b7;
    background: #ffffff; color: {text_primary}; font-size: 0.85em; cursor: pointer;
    transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
  }}
  .group-filter-btn:hover {{ border-color: var(--btn-color, #888888); }}
  .group-filter-btn.active {{
    background: var(--btn-color, #3a3a37); border-color: var(--btn-color, #3a3a37);
    color: #ffffff; font-weight: 600;
  }}
  div.vis-tooltip {{
    background: #ffffff !important;
    border: 1px solid {tooltip_border} !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 16px rgba(11,11,11,0.16) !important;
    padding: 10px 12px !important;
    max-width: 360px !important;
    white-space: normal !important;
    overflow-wrap: break-word !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    font-size: 13px !important;
    line-height: 1.45 !important;
    color: {text_primary} !important;
  }}
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
        f'style="--btn-color: {GROUP_COLORS.get(name, "#3a3a37")};" '
        f'onclick="applyGroupFilter(\'{html.escape(name)}\')">{html.escape(name)}</button>'
        for name in group_names
    )
    # A generic mid-tone stand-in for the swatches below - semantic edges are
    # colored per group_context at render time, not one fixed color, so the
    # legend shows the encoding (dashed vs. solid, and "colored by group" in
    # the label) rather than picking one specific group's hex to represent it.
    generic_group_color = "#8a8a86"
    controls = CONTROLS_TEMPLATE.format(
        group_buttons=buttons,
        all_groups_color=ALL_GROUPS_BTN_COLOR,
        header_bg=HEADER_BG,
        header_border=HEADER_BORDER,
        text_primary=TEXT_PRIMARY,
        text_secondary=TEXT_SECONDARY,
        tooltip_border=TOOLTIP_BORDER,
        technique_swatch=_dot_swatch(NODE_TYPE_BASE_STYLE["Technique"]["color"]),
        tactic_swatch=_box_swatch(NODE_TYPE_BASE_STYLE["Tactic"]["color"]),
        group_swatch=_star_swatch(generic_group_color),
        uses_swatch=_line_swatch(USES_TECHNIQUE_COLOR),
        tactic_edge_swatch=_line_swatch(HAS_TACTIC_COLOR),
        causally_swatch=_line_swatch(generic_group_color),
        temporally_swatch=_line_swatch(generic_group_color, dashed=True),
    )
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
