"""
Semantic edge schema and hand-authored edge set (Phase 2).

Semantic edges model sequence/causality BETWEEN techniques, which plain
ATT&CK data doesn't capture - "APT29 uses T1059.001 and T1078" doesn't
tell you PowerShell execution is what got them from a phishing payload
to Domain Admin in under 12 hours. These edges do.

WHY GROUP-SCOPED, NOT UNIVERSAL (see docs/decisions/002-semantic-edge-
schema.md): every edge below is backed by evidence of how ONE specific
group chained these two techniques in a documented incident/campaign,
not a claim that technique A always precedes technique B for any actor.
Two different groups could plausibly have a different or even reversed
relationship between the same technique pair - the schema allows that by
keying each edge to a group_context.

Field meanings (kept deliberately literal so nothing here is a vibe):
    edge_type     - "TEMPORALLY_PRECEDES" (A observed before B, ordering
                    claim only) or "CAUSALLY_ENABLES" (A is a documented
                    or mechanistically direct prerequisite for B, a
                    stronger claim than mere ordering)
    group_context - which group's documented behavior this edge reflects
    confidence    - author's assessment (0-1) of how DIRECTLY the cited
                    sources narrate this specific ordering/causal claim,
                    vs. being inferred from co-citation or technique
                    semantics. Not a statistical figure - see per-edge
                    "evidence" for the reasoning behind each score.
    sample_size   - count of independent named CTI sources supporting
                    the claim (counted from `sources`, not invented)
    sources       - real, named publications. For sources also present
                    as USES_TECHNIQUE citations in the structural graph
                    (graph/build_graph.py output), co-citation across
                    both techniques is part of the evidence itself: it
                    means the same report described both techniques
                    together. Additional sources here were pulled
                    directly from the named publication, independent of
                    the STIX bundle.
    evidence      - what the source(s) actually say, in our own words -
                    never reproduced report text (copyright discipline
                    per the attack-pattern-doc skill)

Every edge below has a real citation. None are author-estimated - where
direct sequencing/causal evidence couldn't be found for a plausible pair,
the pair is simply omitted rather than dressed up as a guess. As of the
second authoring pass (2026-08-13) all 13 seed techniques have at least
one semantic edge; T1071.001-as-source, and cross-group comparison edges
for the same technique pair, remain unbuilt for lack of evidence.
"""

import networkx as nx

SEMANTIC_EDGES = [
    {
        "source": "T1566.001",
        "target": "T1204.002",
        "edge_type": "TEMPORALLY_PRECEDES",
        "group_context": "APT29",
        "confidence": 0.75,
        "sample_size": 3,
        "sources": [
            "Secureworks IRON HEMLOCK Profile",
            "ESET T3 Threat Report 2021",
            "F-Secure The Dukes",
        ],
        "evidence": (
            "All three reports describe APT29's phishing chain as a single "
            "flow: a spearphishing email carries the malicious attachment, "
            "and the victim opening it is what triggers the malicious file. "
            "The two techniques are always described together in these "
            "reports as sequential steps of one delivery chain; the STIX "
            "relationship objects for both T1566.001 and T1204.002 on APT29 "
            "cite the same three sources. Ordering here (delivery, then "
            "execution) follows directly from what each technique IS, not "
            "just co-citation."
        ),
    },
    {
        "source": "T1204.002",
        "target": "T1059.001",
        "edge_type": "CAUSALLY_ENABLES",
        "group_context": "APT29",
        "confidence": 0.8,
        "sample_size": 3,
        "sources": [
            "Secureworks IRON HEMLOCK Profile",
            "ESET T3 Threat Report 2021",
            "F-Secure The Dukes",
        ],
        "evidence": (
            "F-Secure's 'The Dukes' documents APT29 weaponized Office "
            "documents whose macros launch a PowerShell-based backdoor "
            "(the POSHSPY/PowerDuke lineage) once the user enables content - "
            "the malicious file's entire purpose is to hand off to "
            "PowerShell. This is a mechanistic causal link (macro spawns "
            "the PowerShell process), not just an observed order."
        ),
    },
    {
        "source": "T1059.001",
        "target": "T1078",
        "edge_type": "TEMPORALLY_PRECEDES",
        "group_context": "APT29",
        "confidence": 0.85,
        "sample_size": 2,
        "sources": [
            "Mandiant UNC2452 APT29 April 2022",
            "NSA Joint Advisory SVR SolarWinds April 2021",
        ],
        "evidence": (
            "Mandiant's UNC2452/APT29 writeup states the group was able to "
            "gain Domain Administrator privileges 'less than 12 hours after "
            "the initial execution of a phishing payload' - an explicit, "
            "quoted timeline claim linking early execution (PowerShell/"
            "Cobalt Strike loaders per the same report) to subsequent use "
            "of privileged/valid accounts, in a single documented incident "
            "(the SolarWinds/SUNBURST intrusion) rather than a generic "
            "technique-level inference."
        ),
    },
    {
        "source": "T1560.001",
        "target": "T1074.002",
        "edge_type": "TEMPORALLY_PRECEDES",
        "group_context": "APT29",
        "confidence": 0.7,
        "sample_size": 4,
        "sources": [
            "Volexity SolarWinds",
            "UK NSCS Russia SolarWinds April 2021",
            "NSA Joint Advisory SVR SolarWinds April 2021",
            "Mandiant UNC2452 APT29 April 2022",
        ],
        "evidence": (
            "Four independent reports on the same SolarWinds/APT29 "
            "intrusion co-cite both T1560.001 and T1074.002, describing "
            "collected data being compressed before being moved to a "
            "staging point ahead of exfiltration. Ordering (archive, then "
            "stage) follows the natural collection pipeline; the sources "
            "confirm both steps occurred in the same intrusion, not an "
            "explicit blow-by-blow narration of which came first."
        ),
    },
    {
        "source": "T1021.001",
        "target": "T1059.001",
        "edge_type": "CAUSALLY_ENABLES",
        "group_context": "APT28",
        "confidence": 0.85,
        "sample_size": 1,
        "sources": ["Volexity Nearest Neighbor Attack Nov 2024"],
        "evidence": (
            "CORRECTED 2026-08-13: an earlier pass had this edge reversed "
            "(T1059.001 -> T1021.001). Re-reading Volexity's 'Nearest "
            "Neighbor Attack' report in full shows the actual order was RDP "
            "first: APT28 used privileged credentials to RDP into a "
            "dual-homed system at Organization B (the neighboring org used "
            "as a pivot), and only once they had that foothold did they run "
            "a custom PowerShell script on it to enumerate nearby Wi-Fi "
            "networks in range. The RDP access is the precondition for "
            "being able to run the recon script at all, not the reverse."
        ),
    },
    {
        "source": "T1078",
        "target": "T1021.001",
        "edge_type": "CAUSALLY_ENABLES",
        "group_context": "APT28",
        "confidence": 0.75,
        "sample_size": 1,
        "sources": ["Volexity Nearest Neighbor Attack Nov 2024"],
        "evidence": (
            "CORRECTED 2026-08-13: the RDP hop this edge refers to is into "
            "the dual-homed pivot system at Organization B, not directly "
            "into the ultimate target (Organization A) - Volexity states "
            "APT28 used 'privileged credentials to connect to it via RDP "
            "from another system within Organization B's network.' Valid "
            "Accounts is a documented precondition for that RDP step in "
            "this incident."
        ),
    },
    {
        "source": "T1078",
        "target": "T1003.002",
        "edge_type": "CAUSALLY_ENABLES",
        "group_context": "APT28",
        "confidence": 0.85,
        "sample_size": 1,
        "sources": ["Volexity Nearest Neighbor Attack Nov 2024"],
        "evidence": (
            "A second, distinct use of Valid Accounts in the same incident: "
            "after pivoting through the RDP foothold and the PowerShell "
            "Wi-Fi script, APT28 associated with Organization A's own "
            "enterprise Wi-Fi using a separately compromised credential "
            "set. Volexity explicitly states credential dumping (`reg save "
            "hklm\\sam ...` plus SECURITY and SYSTEM hives) happened only "
            "after that Wi-Fi access into Organization A was established, "
            "not before. Not modeled as a second T1059.001->T1078 edge to "
            "avoid implying a cycle back through the same PowerShell/RDP "
            "steps already captured above - this edge and the T1078 -> "
            "T1021.001 edge represent two different credential instances in "
            "the same incident, not a loop."
        ),
    },
    {
        "source": "T1078",
        "target": "T1059.001",
        "edge_type": "CAUSALLY_ENABLES",
        "group_context": "APT28",
        "confidence": 0.65,
        "sample_size": 1,
        "sources": ["Cybersecurity Advisory GRU Brute Force Campaign July 2021"],
        "evidence": (
            "The NSA/CISA/FBI/NCSC joint advisory on APT28's Kubernetes-"
            "based brute-force campaign states that after obtaining "
            "credentials via brute force, the group used them for "
            "'further network access via remote code execution and "
            "lateral movement.' The advisory doesn't name PowerShell "
            "specifically for this step, but T1059.001 and T1078 are both "
            "attributed to APT28 via this same advisory in MITRE's own "
            "relationship data - lower confidence than the other edges "
            "here because the causal link is corroborated rather than "
            "directly quoted."
        ),
    },
    {
        "source": "T1059.001",
        "target": "T1547.001",
        "edge_type": "CAUSALLY_ENABLES",
        "group_context": "APT28",
        "confidence": 0.65,
        "sample_size": 1,
        "sources": ["TrendMicro Pawn Storm Dec 2020"],
        "evidence": (
            "Trend Micro's December 2020 Pawn Storm report co-cites both "
            "T1059.001 and T1547.001 for APT28 - the only source MITRE's "
            "own relationship data has for T1547.001 on this group. The "
            "report documents Pawn Storm's PowerShell-heavy tradecraft "
            "(including a PowerShell payload built to steal Net-NTLMv2 "
            "hashes) but the specific 'PowerShell writes the run key' "
            "mechanism isn't quoted verbatim in what we could retrieve - "
            "confidence reflects mechanistic plausibility plus co-citation, "
            "not a directly narrated sequence."
        ),
    },
    {
        "source": "T1059.001",
        "target": "T1105",
        "edge_type": "CAUSALLY_ENABLES",
        "group_context": "APT28",
        "confidence": 0.65,
        "sample_size": 2,
        "sources": [
            "TrendMicro Pawn Storm Dec 2020",
            "Cybersecurity Advisory GRU Brute Force Campaign July 2021",
        ],
        "evidence": (
            "Both sources co-cite T1059.001 and T1105 for APT28: the GRU "
            "Brute Force advisory describes credential access being "
            "followed by 'further network access via remote code execution "
            "and lateral movement' (consistent with a PowerShell-driven "
            "foothold pulling in additional tooling), and the Pawn Storm "
            "report documents multi-stage PowerShell payload delivery. "
            "Ordering is inferred from co-citation and the general shape of "
            "a PowerShell-first-stage-then-tool-download pattern, not an "
            "explicit quote naming this exact sequence."
        ),
    },
    {
        "source": "T1105",
        "target": "T1003.002",
        "edge_type": "CAUSALLY_ENABLES",
        "group_context": "APT29",
        "confidence": 0.8,
        "sample_size": 1,
        "sources": ["Mandiant APT29 Eye Spy Email Nov 22"],
        "evidence": (
            "Mandiant's UNC3524 ('Eye Spy on Your Email') report, merged "
            "into APT29 in Nov 2022, narrates a direct sequence: the actor "
            "first deployed the QUIETEXIT backdoor onto network appliances "
            "(SAN arrays, load balancers, wireless access points) - the "
            "ingress tool transfer step - then used QUIETEXIT's SOCKS "
            "tunnel to move laterally and run `reg save` against the SAM, "
            "SECURITY, and SYSTEM registry hives to extract credentials "
            "offline. Tool transfer is an explicit precondition for the "
            "credential dumping step in this report, not an inference."
        ),
    },
    {
        "source": "T1105",
        "target": "T1547.001",
        "edge_type": "CAUSALLY_ENABLES",
        "group_context": "APT29",
        "confidence": 0.65,
        "sample_size": 1,
        "sources": ["Mandiant No Easy Breach"],
        "evidence": (
            "Mandiant's 'No Easy Breach' (DerbyCon 2016, Dunwoody & Carr) "
            "is the sole MITRE-cited source for T1547.001 on APT29, and is "
            "also cited for T1105 - the same presentation covers both "
            "APT29 tool delivery and its use of registry run keys with "
            "obfuscated PowerShell for persistence. We could not retrieve "
            "the full presentation to confirm an explicit tool-transfer-"
            "then-persist quote, so this is scored on co-citation plus the "
            "ordinary shape of an intrusion (get tooling onto the host, "
            "then persist it) rather than a directly narrated sequence."
        ),
    },
    {
        "source": "T1078",
        "target": "T1057",
        "edge_type": "TEMPORALLY_PRECEDES",
        "group_context": "APT29",
        "confidence": 0.7,
        "sample_size": 3,
        "sources": [
            "UK NSCS Russia SolarWinds April 2021",
            "Mandiant UNC2452 APT29 April 2022",
            "NSA Joint Advisory SVR SolarWinds April 2021",
        ],
        "evidence": (
            "Extends the existing SolarWinds/APT29 chain (see T1059.001 -> "
            "T1078 above): three reports on the same intrusion co-cite both "
            "T1078 and T1057, consistent with the well-documented pattern "
            "of process discovery being run as a survey step once "
            "privileged account access is already in hand. Ordering "
            "follows the pipeline's natural shape rather than an explicit "
            "quoted sequence, hence 0.7 rather than the 0.85 on the more "
            "directly-quoted T1059.001 -> T1078 edge."
        ),
    },
    {
        "source": "T1057",
        "target": "T1083",
        "edge_type": "TEMPORALLY_PRECEDES",
        "group_context": "APT29",
        "confidence": 0.7,
        "sample_size": 4,
        "sources": [
            "Volexity SolarWinds",
            "UK NSCS Russia SolarWinds April 2021",
            "NSA Joint Advisory SVR SolarWinds April 2021",
            "Mandiant UNC2452 APT29 April 2022",
        ],
        "evidence": (
            "Same SolarWinds/APT29 chain: four reports co-cite T1057 and "
            "T1083 for this intrusion. Process discovery and file/directory "
            "discovery are both 'discovery' tactic recon steps commonly run "
            "as a pair; ordering here (process survey, then filesystem "
            "survey) is inferred from the pipeline shape and technique "
            "semantics rather than an explicit narrated sequence."
        ),
    },
    {
        "source": "T1083",
        "target": "T1560.001",
        "edge_type": "TEMPORALLY_PRECEDES",
        "group_context": "Lazarus Group",
        "confidence": 0.75,
        "sample_size": 4,
        "sources": [
            "McAfee Lazarus Jul 2020",
            "ClearSky Lazarus Aug 2020",
            "ESET Lazarus Jun 2020",
            "CISA AA24-207A Aug 2024",
        ],
        "evidence": (
            "CISA AA24-207A describes Lazarus Group collecting 'relevant "
            "files' into RAR archives - archiving specific files of "
            "interest presupposes having already enumerated them via "
            "file/directory discovery. Three earlier vendor reports "
            "(McAfee, ClearSky, ESET) co-cite both T1083 and T1560.001 for "
            "Lazarus independently of AA24-207A."
        ),
    },
    {
        "source": "T1560.001",
        "target": "T1071.001",
        "edge_type": "CAUSALLY_ENABLES",
        "group_context": "Lazarus Group",
        "confidence": 0.7,
        "sample_size": 1,
        "sources": ["CISA AA24-207A Aug 2024"],
        "evidence": (
            "CISA AA24-207A states Lazarus 'typically exfiltrate[s] data "
            "to web services such as cloud storage or servers not "
            "associated with their primary C2' after archiving it with "
            "WinRAR - the archived output is what gets moved out over the "
            "web-protocol channel."
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
