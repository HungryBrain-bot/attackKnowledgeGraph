"""
Semantic edge schema and hand-authored edge set (Phase 2).

Semantic edges model sequence/causality BETWEEN techniques, which plain
ATT&CK data doesn't capture - "APT28 uses T1078 and T1021.001" doesn't
say the stolen credentials are what got them onto the RDP pivot host.
These edges do, one cited observation at a time.

WHY GROUP-SCOPED, NOT UNIVERSAL (see docs/decisions/002-semantic-edge-
schema.md): every edge below is backed by evidence of how ONE specific
group chained these two techniques in a documented incident/campaign,
not a claim that technique A always precedes technique B for any actor.

Field meanings (kept deliberately literal so nothing here is a vibe):
    edge_type     - "TEMPORALLY_PRECEDES" (A observed before B, ordering
                    claim only) or "CAUSALLY_ENABLES" (A is a documented
                    or mechanistically direct prerequisite for B, a
                    stronger claim than mere ordering)
    group_context - which group's documented behavior this edge reflects
    incident_id   - the one operation/intrusion (or, where stated, one
                    campaign) the edge was observed in. Multi-hop chains
                    warn when they join edges from different incidents
                    (docs/decisions/009).
    confidence    - author's judgment (0-1) of how DIRECTLY the quoted
                    source narrates this specific ordering/causal claim.
                    Not a statistical figure, and not comparable across
                    authors - see each edge's "evidence" for the reason.
    sample_size   - count of independent named sources in `sources`
                    that each narrate the claim themselves. Co-citation
                    (two techniques mentioned in the same report) does
                    not count.
    sources       - named publications, as MITRE ATT&CK cites them where
                    it does
    source_url    - where the primary source can be fetched
    source_date   - the source's publication date (YYYY-MM-DD)
    quote         - a short verbatim extract (under 25 words) from that
                    source supporting the edge. Checked against the
                    fetched page on the audit date in docs/edge-audit.md.
    evidence      - our own explanation of how the quote supports the
                    edge, including anything inferred rather than stated

AUDIT (2026-10-26, docs/decisions/010-edge-reaudit.md and
docs/edge-audit.md): all 17 earlier edges were re-checked against their
primary sources. Only edges whose source could be fetched and quoted
for the specific ordering or dependency were kept. 12 were removed:
two as true by definition, ten because the source did not support the
claim as written (wrong technique, wrong group, wrong incident, or only
co-citation). The removed edges and the reason for each are listed in
docs/edge-audit.md, not kept here.
"""

import networkx as nx

SEMANTIC_EDGES = [
    {
        "source": "T1078",
        "target": "T1021.001",
        "edge_type": "CAUSALLY_ENABLES",
        "group_context": "APT28",
        "incident_id": "nearest-neighbor-2022",
        "confidence": 0.85,
        "sample_size": 1,
        "sources": ["Volexity Nearest Neighbor Attack Nov 2024"],
        "source_url": "https://www.volexity.com/blog/2024/11/22/the-nearest-neighbor-attack-how-a-russian-apt-weaponized-nearby-wi-fi-networks-for-covert-access/",
        "source_date": "2024-11-22",
        "quote": (
            "after an attacker used privileged credentials to connect to it "
            "via RDP from another system within Organization B’s network"
        ),
        "evidence": (
            "Volexity's incident response (activity from February 2022, "
            "attributed to GruesomeLarch/APT28): the dual-homed system at "
            "Organization B, used as the Wi-Fi pivot into Organization A, "
            "was reached over RDP using privileged credentials. The quote "
            "states the dependency directly - the credentials are how the "
            "RDP session was opened."
        ),
    },
    {
        "source": "T1021.001",
        "target": "T1059.001",
        "edge_type": "CAUSALLY_ENABLES",
        "group_context": "APT28",
        "incident_id": "nearest-neighbor-2022",
        "confidence": 0.8,
        "sample_size": 1,
        "sources": ["Volexity Nearest Neighbor Attack Nov 2024"],
        "source_url": "https://www.volexity.com/blog/2024/11/22/the-nearest-neighbor-attack-how-a-russian-apt-weaponized-nearby-wi-fi-networks-for-covert-access/",
        "source_date": "2024-11-22",
        "quote": "used a custom PowerShell script to examine the available networks within range",
        "evidence": (
            "Same incident and same host: after reaching the Organization B "
            "system over RDP, APT28 ran a custom PowerShell script on it to "
            "list Wi-Fi networks in range. The report narrates RDP first, "
            "then the script, but gives no timestamps; 'enables' rests on "
            "the script running on the host the RDP session reached. "
            "Scored below the edge above for that reason."
        ),
    },
    {
        "source": "T1078",
        "target": "T1003.002",
        "edge_type": "TEMPORALLY_PRECEDES",
        "group_context": "APT28",
        "incident_id": "nearest-neighbor-2022",
        "confidence": 0.75,
        "sample_size": 1,
        "sources": ["Volexity Nearest Neighbor Attack Nov 2024"],
        "source_url": "https://www.volexity.com/blog/2024/11/22/the-nearest-neighbor-attack-how-a-russian-apt-weaponized-nearby-wi-fi-networks-for-covert-access/",
        "source_date": "2024-11-22",
        "quote": (
            "A login with an unprivileged user account on the server occurred "
            "over RDP. ... reg save hklm\\sam C:\\ProgramData\\sam.save"
        ),
        "evidence": (
            "CORRECTED 2026-10-26: the earlier text said Volexity "
            "'explicitly states' the hive dumping happened only after "
            "Wi-Fi access to Organization A; the report does not say that. "
            "What it does narrate, in order, for the first detected "
            "activity on 4 February 2022: an RDP login with a valid "
            "(unprivileged) account on the server, then `reg save` of the "
            "SAM, SECURITY and SYSTEM hives. Retyped from CAUSALLY_ENABLES "
            "to TEMPORALLY_PRECEDES: the account was unprivileged, so the "
            "report supports the order, not that the login enabled the "
            "dump. Confidence lowered from 0.85 to 0.75 accordingly."
        ),
    },
    {
        "source": "T1078",
        "target": "T1059.001",
        "edge_type": "CAUSALLY_ENABLES",
        "group_context": "APT28",
        "incident_id": "gru-brute-force-campaign-2019-2021",
        "confidence": 0.7,
        "sample_size": 1,
        "sources": ["Cybersecurity Advisory GRU Brute Force Campaign July 2021"],
        "source_url": "https://media.defense.gov/2021/Jul/01/2002753896/-1/-1/1/CSA_GRU_GLOBAL_BRUTE_FORCE_CAMPAIGN_UOO158036-21.PDF",
        "source_date": "2021-07-01",
        "quote": (
            "The actors used a Powershell® cmdlet (New-ManagementRoleAssignment) "
            "to grant the 'ApplicationImpersonation' role"
        ),
        "evidence": (
            "NSA/CISA/FBI/NCSC advisory on GTsSS (APT28) password spraying, "
            "mid-2019 to early 2021. The advisory says the actors used "
            "legitimate credentials to keep access, and records an "
            "authenticated Exchange PowerShell cmdlet run against an "
            "already-compromised account. The dependency (the cmdlet needs "
            "those credentials) is inferred from what the cmdlet requires; "
            "the advisory does not narrate it as a sequence. incident_id "
            "names a multi-year campaign, not one intrusion - lowered from "
            "0.75 to 0.7 for that reason."
        ),
    },
    {
        "source": "T1204.002",
        "target": "T1059.001",
        "edge_type": "CAUSALLY_ENABLES",
        "group_context": "APT29",
        "incident_id": "powerduke-2016-11",
        "confidence": 0.8,
        "sample_size": 1,
        "sources": ["Volexity PowerDuke November 2016"],
        "source_url": "https://www.volexity.com/blog/2016/11/09/powerduke-post-election-spear-phishing-campaigns-targeting-think-tanks-and-ngos/",
        "source_date": "2016-11-09",
        "quote": (
            "This shortcut file contains PowerShell commands that conduct "
            "anti-VM checks, drop a backdoor, and launch a clean decoy document."
        ),
        "evidence": (
            "RE-SOURCED 2026-10-26: the earlier evidence credited F-Secure's "
            "2015 'The Dukes' report with POSHSPY/PowerDuke macros launching "
            "PowerShell, but PowerDuke was first reported by Volexity in "
            "November 2016, after that report, and Volexity's own report "
            "does not describe the Word macros launching PowerShell. What "
            "it does describe, for waves 1 and 5 of the post-election "
            "campaign attributed to The Dukes (APT29), is a malicious "
            "shortcut (LNK) file the victim opens, which runs PowerShell. "
            "Opening a malicious file is T1204.002, so the edge stands, on "
            "a different mechanism (LNK, not macro) and a different source. "
            "The previous three sources (Secureworks, ESET, F-Secure) are "
            "no longer counted: none was fetched and quoted for this claim."
        ),
    },
]


def add_semantic_edges(g: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Adds hand-authored semantic edges to an existing structural graph.

    Mutates and returns `g`. Raises if a source/target technique isn't
    already a node - semantic edges are only ever authored on top of
    seed techniques already verified real by build_graph.py.
    """
    for e in SEMANTIC_EDGES:
        for tid in (e["source"], e["target"]):
            if tid not in g:
                raise ValueError(
                    f"Semantic edge references {tid}, not in the structural "
                    f"graph - check graph/seed_config.py"
                )
        g.add_edge(
            e["source"],
            e["target"],
            edge_type=e["edge_type"],
            group_context=e["group_context"],
            confidence=e["confidence"],
            sample_size=e["sample_size"],
            sources=e["sources"],
            evidence=e["evidence"],
            incident_id=e["incident_id"],
            source_url=e["source_url"],
            source_date=e["source_date"],
            quote=e["quote"],
        )
    return g


if __name__ == "__main__":
    import json
    from pathlib import Path

    from graph.build_graph import build_structural_graph, graph_summary

    g = build_structural_graph()
    g = add_semantic_edges(g)
    print(graph_summary(g))

    out_path = Path(__file__).parent.parent / "data" / "graph_with_semantics.json"
    data = nx.node_link_data(g, edges="edges")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\nSaved to {out_path}")
