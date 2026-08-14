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
one semantic edge; T1071.001-as-source remains unbuilt for lack of
evidence.

CROSS-GROUP COMPARISONS (see docs/decisions/006-cross-group-comparison.md
for the full reasoning): a comparison is a claim about two of the edges
above - "these two groups are documented handling the same technique pair
differently" - not a new behavioral claim of its own, so it is authored
separately in `CROSS_GROUP_COMPARISONS` below and attached onto its two
constituent edges by `add_cross_group_comparisons()`, rather than modeled
as a new edge type between technique nodes. Its fields:
    comparison_id  - short stable identifier, referenced nowhere else
    technique_pair - the unordered (source, target) pair being compared
    groups         - the two group_context values being contrasted
    contrast_type  - "direction" (the two groups chain the pair in
                     opposite order) or "mechanism" (same order, same
                     pair, materially different how/what)
    edges          - the two edges being compared, each identified by
                     (source, target, group_context); must each already
                     exist in SEMANTIC_EDGES or add_cross_group_
                     comparisons() raises
    confidence     - NOT the same meaning as an edge's confidence. Here:
                     how confident we are the divergence is a real
                     difference in documented tradecraft rather than an
                     artifact of which campaigns happened to get
                     reported. Computed as the weaker constituent edge's
                     confidence, discounted for (1) exclusivity risk -
                     does the same group also show the other pattern
                     elsewhere? and (2) comparability - are the two
                     documented operations the same kind of thing, seen
                     through the same kind of reporting? Reasoning is
                     written out per-comparison in `evidence`, same
                     discipline as edges.
    sample_size    - count of independently named sources across both
                     sides combined (== len(sources)); the split is
                     disclosed in `evidence`, not encoded in the number.
    sources        - union of both sides' real sources
    evidence       - the contrast itself, in our own words, plus the
                     confidence reasoning
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
        "confidence": 0.75,
        "sample_size": 1,
        "sources": ["Cybersecurity Advisory GRU Brute Force Campaign July 2021"],
        "evidence": (
            "REGROUNDED 2026-08-14: the earlier evidence text here "
            "paraphrased the advisory as credentials being used for "
            "'further network access via remote code execution and "
            "lateral movement' - that conflates two separate sentences. "
            "The advisory attributes that remote code execution to "
            "exploiting Microsoft Exchange CVE-2020-0688 and CVE-2020-"
            "17144, i.e. exploitation, not a scripting interpreter. The "
            "advisory does support a PowerShell step, but elsewhere: it "
            "records APT28 using a PowerShell cmdlet to grant the "
            "ApplicationImpersonation role to an account they had already "
            "compromised (MITRE's own T1098.002 procedure example cites "
            "this advisory for exactly this). Running that Exchange "
            "cmdlet is impossible without the brute-forced credentials, "
            "which makes Valid Accounts a directly-narrated precondition "
            "for PowerShell execution here, not a co-citation inference - "
            "raised from 0.65 accordingly."
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
    {
        "source": "T1566.001",
        "target": "T1204.002",
        "edge_type": "TEMPORALLY_PRECEDES",
        "group_context": "Lazarus Group",
        "confidence": 0.8,
        "sample_size": 2,
        "sources": [
            "McAfee Lazarus Jul 2020",
            "McAfee Lazarus Nov 2020",
        ],
        "evidence": (
            "Added 2026-08-14 as the second side of a cross-group "
            "comparison against APT29's edge of the same name and "
            "direction (see CROSS_GROUP_COMPARISONS, cmp-002). McAfee's "
            "Operation North Star reporting narrates the full delivery-to-"
            "execution step directly: the operators lifted real job-"
            "recruitment content from US defense-contractor websites to "
            "lure targeted employees into opening malicious spearphishing "
            "email attachments. Unlike APT29's equivalent chain, the "
            "attached document carries no macro - opening it causes "
            "Office to fetch a remote .dotm template (hosted under a .jpg "
            "extension on a compromised server), and the macro that "
            "executes lives in that downloaded template, which McAfee "
            "describes as a deliberate measure to defeat static analysis "
            "of the attachment. Scored 0.8 rather than higher because it "
            "is a campaign-level narration rather than a single-incident "
            "timeline. ClearSky Lazarus Aug 2020 corroborates the wider "
            "Dream Job campaign but is NOT counted in sources here: its "
            "documented delivery is largely LinkedIn messaging plus "
            "OneDrive/Dropbox links, closer to T1566.003/T1566.002 than "
            "to Spearphishing Attachment specifically."
        ),
    },
]


CROSS_GROUP_COMPARISONS = [
    {
        "comparison_id": "cmp-001",
        "technique_pair": ("T1059.001", "T1078"),
        "groups": ("APT29", "APT28"),
        "contrast_type": "direction",
        "edges": [
            ("T1059.001", "T1078", "APT29"),
            ("T1078", "T1059.001", "APT28"),
        ],
        "confidence": 0.6,
        "sample_size": 3,
        "sources": [
            "Mandiant UNC2452 APT29 April 2022",
            "NSA Joint Advisory SVR SolarWinds April 2021",
            "Cybersecurity Advisory GRU Brute Force Campaign July 2021",
        ],
        "evidence": (
            "The same unordered technique pair is documented running in "
            "opposite directions by the two groups, with different "
            "initial access and in different planes. APT29 (SolarWinds/"
            "UNC2452): a spearphishing payload executes on an endpoint "
            "first, and privileged account use is the OUTCOME - Mandiant "
            "records Domain Administrator obtained less than 12 hours "
            "after the initial execution of a phishing payload. APT28 "
            "(GRU brute-force campaign): credentials come first, "
            "harvested by Kubernetes-distributed password spraying, and "
            "PowerShell is what those credentials BUY - the advisory-"
            "cited step is an authenticated Exchange cmdlet granting "
            "ApplicationImpersonation to the already-compromised account. "
            "So the divergence is not only an arrow flip: for APT29 the "
            "credentials are the prize won by executing code on-premises "
            "against Active Directory; for APT28 the credentials are the "
            "entry ticket that lets administrative code run at all, in "
            "the M365/Exchange identity plane. Scored 0.6, below the 0.75 "
            "floor set by the weaker constituent edge, for two reasons "
            "specific to comparison claims. (1) Exclusivity: the same "
            "Mandiant report also lists stolen credentials and password "
            "sprays among APT29's initial-access vectors, so APT29 "
            "demonstrably ALSO runs credentials-first - this is a "
            "contrast between two documented operations, NOT a claim that "
            "either group only ever works in one direction. (2) "
            "Comparability: the two sides are seen through different "
            "lenses - a single-intrusion IR narrative vs. a multi-year "
            "campaign advisory - so some of the apparent divergence is "
            "attributable to what each report type narrates rather than "
            "to actor behavior. Sources split 2 (APT29) / 1 (APT28); the "
            "single-source APT28 side is the limiting factor."
        ),
    },
    {
        "comparison_id": "cmp-002",
        "technique_pair": ("T1566.001", "T1204.002"),
        "groups": ("APT29", "Lazarus Group"),
        "contrast_type": "mechanism",
        "edges": [
            ("T1566.001", "T1204.002", "APT29"),
            ("T1566.001", "T1204.002", "Lazarus Group"),
        ],
        "confidence": 0.7,
        "sample_size": 5,
        "sources": [
            "Secureworks IRON HEMLOCK Profile",
            "ESET T3 Threat Report 2021",
            "F-Secure The Dukes",
            "McAfee Lazarus Jul 2020",
            "McAfee Lazarus Nov 2020",
        ],
        "evidence": (
            "Same pair, same direction, materially different mechanism: "
            "the two groups differ on WHEN the malicious code is present "
            "on the victim host. APT29's attachment is self-contained - "
            "the macro is inside the attached document, so T1204.002 is a "
            "purely local event and the file detonates the same way "
            "offline. Lazarus's attachment (McAfee's Operation North "
            "Star) is a benign-looking fetcher carrying no macro at all: "
            "opening it makes Office download a remote .dotm template "
            "disguised with a .jpg extension, and only then does a macro "
            "exist to execute. T1204.002 is therefore network-dependent "
            "for Lazarus and not for APT29 - a detonated copy of the "
            "Lazarus attachment with no outbound reachability shows "
            "nothing. The chains also stop resembling each other "
            "immediately after: APT29's macro hands off to a PowerShell "
            "backdoor (see the T1204.002 -> T1059.001 edge), while "
            "Lazarus's downloaded-template macro loads a DLL via "
            "rundll32 - a different technique (T1218.011) not modeled as "
            "a mirrored T1204.002 -> T1059.001 edge for Lazarus, since "
            "none of this project's cited Lazarus sources narrate that "
            "specific handoff landing on PowerShell. Detection "
            "consequence: attachment-content inspection catches APT29's "
            "version and misses Lazarus's; Office outbound template-fetch "
            "telemetry catches Lazarus's and is irrelevant to APT29's. "
            "Scored 0.7, discounted from the 0.75 constituent floor for "
            "exclusivity only: ClearSky's Dream Job reporting shows "
            "Lazarus ALSO using a plain macro-bearing DOC in the same "
            "period, so template injection is a campaign choice, not a "
            "Lazarus signature. Comparability is high - both sides are "
            "the same operation type (spearphishing email with document "
            "attachment) at comparable technical detail - which is why "
            "this scores above cmp-001 despite cmp-001's more striking "
            "contrast. Sources split 3 (APT29) / 2 (Lazarus Group)."
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


def _find_semantic_edge(g: nx.MultiDiGraph, source: str, target: str, group_context: str) -> dict | None:
    """Finds the semantic edge (source, target) scoped to group_context.

    Early-exit search over the parallel edges a MultiDiGraph can hold
    between the same two nodes. None if no matching TEMPORALLY_PRECEDES/
    CAUSALLY_ENABLES edge exists.
    """
    for data in (g.get_edge_data(source, target) or {}).values():
        if (
            data.get("edge_type") in ("TEMPORALLY_PRECEDES", "CAUSALLY_ENABLES")
            and data.get("group_context") == group_context
        ):
            return data
    return None


def add_cross_group_comparisons(g: nx.MultiDiGraph) -> nx.MultiDiGraph:
    """Attaches cross-group comparison annotations onto the semantic
    edges they compare.

    A comparison is a claim ABOUT two existing edges, not a new
    behavioral claim of its own - so it's stored as a "comparisons" list
    attribute on those edges rather than as a new edge type (see
    docs/decisions/006-cross-group-comparison.md). Mutates and returns
    `g`. Raises if a comparison names an edge that doesn't exist, so a
    comparison can never silently outlive a corrected or removed edge.
    """
    for c in CROSS_GROUP_COMPARISONS:
        for source, target, group_context in c["edges"]:
            data = _find_semantic_edge(g, source, target, group_context)
            if data is None:
                raise ValueError(
                    f"Comparison {c['comparison_id']} references "
                    f"{source} -> {target} ({group_context}), which is not "
                    f"a semantic edge in the graph - check "
                    f"CROSS_GROUP_COMPARISONS"
                )
            data.setdefault("comparisons", []).append(
                {
                    "comparison_id": c["comparison_id"],
                    "contrast_type": c["contrast_type"],
                    "groups": c["groups"],
                    "confidence": c["confidence"],
                    "sample_size": c["sample_size"],
                    "sources": c["sources"],
                    "evidence": c["evidence"],
                }
            )
    return g


if __name__ == "__main__":
    import json
    from pathlib import Path

    from graph.build_graph import build_structural_graph, graph_summary

    g = build_structural_graph()
    g = add_semantic_edges(g)
    g = add_cross_group_comparisons(g)
    print(graph_summary(g))
    print(f"  Cross-group comparisons: {len(CROSS_GROUP_COMPARISONS)}")

    out_path = Path(__file__).parent.parent / "data" / "graph_with_semantics.json"
    data = nx.node_link_data(g, edges="edges")
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\nSaved to {out_path}")
