"""
Structural graph builder (Phase 1).

Builds the base NetworkX MultiDiGraph from REAL MITRE ATT&CK STIX data
(data/raw/enterprise-attack.json, official MITRE source) - no synthetic
or invented structural data. Scoped to the seed groups/techniques in
seed_config.py (see docs/decisions/001-seed-scope.md for why this is a
deliberately small, hand-picked set rather than the full ATT&CK corpus).

Node types: Group, Technique, Tactic
Structural edge types (from ATT&CK itself):
    USES_TECHNIQUE   - Group -> Technique
    HAS_TACTIC       - Technique -> Tactic  (a technique can map to >1 tactic)

Semantic edges (TEMPORALLY_PRECEDES, CAUSALLY_ENABLES, etc.) are NOT
built here - those are hand-authored in graph/semantic_edges.py against
cited sources, per the project's Phase 2 scope decision.
"""
import json
from collections import Counter
from pathlib import Path

import networkx as nx
from mitreattack.stix20 import MitreAttackData

from graph.seed_config import SEED_GROUPS, SEED_TECHNIQUES

STIX_PATH = Path(__file__).parent.parent / "data" / "raw" / "enterprise-attack.json"


def get_mitre_attack_id(obj: dict) -> str | None:
    """Extracts a STIX object's official ATT&CK ID (e.g. T1059.001, G0016)
    from its external_references, early-exiting on the first match."""
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack":
            return ref.get("external_id")
    return None


def extract_sources(technique_usage: dict) -> list[str]:
    """Extracts citation source names for a group's use of a technique from
    the relationship object(s) STIX attaches the citation to, deduped via a
    single set comprehension."""
    sources = {
        ref.get("source_name")
        for rel in technique_usage.get("relationships", [])
        for ref in rel.get("external_references", [])
        if ref.get("source_name") not in (None, "mitre-attack")
    }
    return sorted(sources) or ["MITRE ATT&CK"]


def build_structural_graph() -> nx.MultiDiGraph:
    # Loads the full ~48MB enterprise STIX bundle into memory on every run
    # rather than filtering/indexing it first - accepted tradeoff at this
    # prototype's scale (13 seed techniques); revisit if the seed set ever
    # grows significantly.
    attack_data = MitreAttackData(str(STIX_PATH))
    g = nx.MultiDiGraph()

    # --- Technique + Tactic nodes ---
    technique_objs = {}
    for tid in SEED_TECHNIQUES:
        obj = attack_data.get_object_by_attack_id(tid, "attack-pattern")
        if obj is None:
            raise ValueError(f"Technique {tid} not found in ATT&CK dataset")
        technique_objs[tid] = obj

        tactics = [p["phase_name"] for p in obj.get("kill_chain_phases", [])]
        g.add_node(
            tid,
            node_type="Technique",
            name=obj["name"],
            attack_id=tid,
            tactics=tactics,
            description=obj.get("description", "")[:500],  # trim for graph size
        )
        for tactic in tactics:
            tactic_node_id = f"tactic--{tactic}"
            if tactic_node_id not in g:
                g.add_node(tactic_node_id, node_type="Tactic", name=tactic)
            g.add_edge(tid, tactic_node_id, edge_type="HAS_TACTIC")

    # --- Group nodes + USES_TECHNIQUE edges ---
    for gname, gid in SEED_GROUPS.items():
        group_obj = attack_data.get_object_by_stix_id(gid)
        g.add_node(
            gname,
            node_type="Group",
            name=gname,
            attack_id=get_mitre_attack_id(group_obj),
            aliases=group_obj.get("aliases", []),
        )

        used = attack_data.get_techniques_used_by_group(gid)
        for t in used:
            t_attack_id = get_mitre_attack_id(t["object"])
            if t_attack_id in SEED_TECHNIQUES:
                g.add_edge(
                    gname,
                    t_attack_id,
                    edge_type="USES_TECHNIQUE",
                    sources=extract_sources(t),
                )

    return g


def graph_summary(g: nx.MultiDiGraph) -> str:
    node_counts = Counter(data["node_type"] for _, data in g.nodes(data=True))
    edge_counts = Counter(data["edge_type"] for _, _, data in g.edges(data=True))
    lines = ["Graph summary:", f"  Nodes: {g.number_of_nodes()} total"]
    for k, v in node_counts.items():
        lines.append(f"    {k}: {v}")
    lines.append(f"  Edges: {g.number_of_edges()} total")
    for k, v in edge_counts.items():
        lines.append(f"    {k}: {v}")
    return "\n".join(lines)


if __name__ == "__main__":
    g = build_structural_graph()
    print(graph_summary(g))

    out_path = Path(__file__).parent.parent / "data" / "structural_graph.json"
    data = nx.node_link_data(g, edges="edges")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\nSaved to {out_path}")
