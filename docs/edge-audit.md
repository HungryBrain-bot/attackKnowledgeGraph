# Edge audit, 2026-10-26

Every semantic edge that existed before this date (17) was re-checked
against its primary source. The rule: an edge stays only if a source
that can actually be fetched today narrates that specific order or
dependency, for that group, and a short verbatim quote from it can be
stored with the edge. Co-citation (both techniques named in the same
report) is not enough. Nothing was filled in from memory.

Result: **5 kept, 12 removed.** The decision record is
[ADR 010](decisions/010-edge-reaudit.md); this file is the evidence.

## How the check was done, and its limits

- Each source was fetched on 2026-10-26 with a web-fetch tool that
  returns the page through a summarising model. Quotes were requested
  verbatim and cross-checked across two or more fetches where the
  claim was load-bearing (the Nearest Neighbor ordering, the Trello
  "12 hours" sentence). They have **not** been compared character by
  character against the original page by a person. Spot-check them
  before quoting them in an interview.
- Sources that could not be fetched (the F-Secure "The Dukes" PDF is
  blocked by robots.txt; Mandiant's "No Easy Breach" slides; the
  Secureworks, ESET and ClearSky reports) count as unverified, not as
  supporting evidence.
- Publication dates are the dates shown on the fetched pages, except
  CISA AA24-207A (2024-07-25), taken from the FBI release URL in search
  results rather than the PDF itself.
- `incident_id` names one intrusion where the source describes one,
  and a campaign where it does not (the GRU edge). It is our label,
  not the vendor's.

## Table

| # | Edge | Group | Status | Source | Quote (verbatim, under 25 words) | Incident ID | Note |
|---|---|---|---|---|---|---|---|
| 1 | `T1078 -> T1021.001` | APT28 | **VERIFIED** | [Volexity, 2024-11-22](https://www.volexity.com/blog/2024/11/22/the-nearest-neighbor-attack-how-a-russian-apt-weaponized-nearby-wi-fi-networks-for-covert-access/) | "after an attacker used privileged credentials to connect to it via RDP from another system within Organization B’s network" | nearest-neighbor-2022 | Kept. Quote states the dependency directly. |
| 2 | `T1021.001 -> T1059.001` | APT28 | **VERIFIED** | [Volexity, 2024-11-22](https://www.volexity.com/blog/2024/11/22/the-nearest-neighbor-attack-how-a-russian-apt-weaponized-nearby-wi-fi-networks-for-covert-access/) | "used a custom PowerShell script to examine the available networks within range" | nearest-neighbor-2022 | Kept. Order is narrated (RDP onto the host, then the script on it); no timestamps. |
| 3 | `T1078 -> T1003.002` | APT28 | **VERIFIED (corrected)** | [Volexity, 2024-11-22](https://www.volexity.com/blog/2024/11/22/the-nearest-neighbor-attack-how-a-russian-apt-weaponized-nearby-wi-fi-networks-for-covert-access/) | "A login with an unprivileged user account on the server occurred over RDP. ... reg save hklm\sam C:\ProgramData\sam.save" | nearest-neighbor-2022 | Kept, retyped CAUSALLY_ENABLES to TEMPORALLY_PRECEDES, 0.85 to 0.75. Old evidence claimed Volexity 'explicitly states' dumping came only after Wi-Fi access; it does not. |
| 4 | `T1078 -> T1059.001` | APT28 | **VERIFIED (dependency inferred)** | [NSA/CISA/FBI/NCSC, 2021-07-01](https://media.defense.gov/2021/Jul/01/2002753896/-1/-1/1/CSA_GRU_GLOBAL_BRUTE_FORCE_CAMPAIGN_UOO158036-21.PDF) | "The actors used a Powershell® cmdlet (New-ManagementRoleAssignment) to grant the 'ApplicationImpersonation' role" | gru-brute-force-campaign-2019-2021 | Kept. Quote shows the PowerShell step; that it needs the stolen credentials is inferred from the cmdlet. Campaign, not one intrusion. 0.75 to 0.7. |
| 5 | `T1204.002 -> T1059.001` | APT29 | **VERIFIED (re-sourced)** | [Volexity PowerDuke, 2016-11-09](https://www.volexity.com/blog/2016/11/09/powerduke-post-election-spear-phishing-campaigns-targeting-think-tanks-and-ngos/) | "This shortcut file contains PowerShell commands that conduct anti-VM checks, drop a backdoor, and launch a clean decoy document." | powerduke-2016-11 | Kept on a new source and mechanism (LNK, not macro). Old evidence credited F-Secure's 2015 report with PowerDuke/POSHSPY, first reported in 2016 and 2017. |
| 6 | `T1566.001 -> T1204.002` | APT29 | **REMOVED (true by definition)** | Secureworks / ESET / F-Secure (not fetched) | - | - | A malicious attachment is opened after it is delivered. The edge's own evidence said the order 'follows directly from what each technique IS'. Adds no information. |
| 7 | `T1566.001 -> T1204.002` | Lazarus Group | **REMOVED (true by definition)** | McAfee Operation North Star 2020 (not fetched) | - | - | Same as above. The template-injection detail was the useful part and lived in the removed cross-group comparison, not the edge. |
| 8 | `T1059.001 -> T1078` | APT29 | **REMOVED (unverified as stated)** | [Mandiant, 2022-04-28](https://cloud.google.com/blog/topics/threat-intelligence/tracking-apt29-phishing-campaigns/) | "In multiple cases, APT29 was able to gain Domain Admin in less than 12 hours from the initial phishing payload's execution." | apt29-trello-phishing-2022 | Source is the 2022 'Trello From the Other Side' phishing report, not SolarWinds/SUNBURST, and the payload chain is ISO/LNK/DLL (BEATDROP), not PowerShell. The NSA SolarWinds advisory was unrelated and should not have counted as a second source. The quote would support T1204.002 to T1078, a different edge, so not added. |
| 9 | `T1560.001 -> T1074.002` | APT29 | **REMOVED (unverified)** | [Volexity Dark Halo, 2020-12-14](https://www.volexity.com/blog/2020/12/14/dark-halo-leverages-solarwinds-compromise-to-breach-organizations/) | "The attacker created password-protected archives on the victims’ OWA server so that they could be exfiltrated via a simple HTTP request." | - | Archive and staging are one step here; no source narrates archive-then-stage. Old evidence admitted co-citation only. |
| 10 | `T1078 -> T1057` | APT29 | **REMOVED (unverified)** | UK NCSC / Mandiant / NSA (co-citation) | - | - | Old evidence admitted ordering 'follows the pipeline's natural shape rather than an explicit quoted sequence'. Dark Halo lists Get-Process only in an appendix. |
| 11 | `T1057 -> T1083` | APT29 | **REMOVED (unverified)** | Volexity / NCSC / NSA / Mandiant (co-citation) | - | - | Old evidence admitted the order was inferred. No narration found. |
| 12 | `T1059.001 -> T1547.001` | APT28 | **REMOVED (unverified)** | [Trend Micro, 2020-12-17](https://www.trendmicro.com/en_us/research/20/l/pawn-storm-lack-of-sophistication-as-a-strategy.html) | "The first thing this malware does is it copies itself to the startup directory for persistence." | - | Persistence is done by the malware itself, not by PowerShell; the report's only PowerShell use Base64-encodes a file. |
| 13 | `T1059.001 -> T1105` | APT28 | **REMOVED (unverified)** | [Trend Micro](https://www.trendmicro.com/en_us/research/20/l/pawn-storm-lack-of-sophistication-as-a-strategy.html); [GRU advisory](https://media.defense.gov/2021/Jul/01/2002753896/-1/-1/1/CSA_GRU_GLOBAL_BRUTE_FORCE_CAMPAIGN_UOO158036-21.PDF) | "The actors used certutil.exe, a known "Living Off the Land" technique, to transfer a file into a target environment." | - | Tool transfer in the advisory is certutil, not PowerShell; Pawn Storm's PowerShell does not download anything. The two sources were different operations. |
| 14 | `T1105 -> T1003.002` | APT29 | **REMOVED (unverified)** | [Mandiant UNC3524, 2022-05-02](https://cloud.google.com/blog/topics/threat-intelligence/unc3524-eye-spy-email/) | "We also observed the threat actor using the built-in reg save command to save registry hives and extract LSA secrets offline." | unc3524-2022 | Report says LSA secrets (T1003.004), not SAM, and lateral movement via WMIEXEC, not the QUIETEXIT tunnel the old evidence described. |
| 15 | `T1105 -> T1547.001` | APT29 | **REMOVED (unverified)** | Mandiant 'No Easy Breach' DerbyCon 2016 (not retrievable) | - | - | Old evidence said the presentation could not be retrieved; still not retrieved. |
| 16 | `T1083 -> T1560.001` | Lazarus Group | **REMOVED (wrong group)** | [CISA AA24-207A, 2024-07-25](https://cisa.gov/sites/default/files/2024-07/aa24-207a-dprk-cyber-group-conducts-global-espionage-campaign.pdf) | "The actors identify data for theft by enumerating files and folders across many directories and servers" | - | The advisory is about Andariel (MITRE G0138), a separate ATT&CK group from Lazarus Group (G0032); the text does not mention Lazarus. The three other Lazarus sources were co-citation only. |
| 17 | `T1560.001 -> T1071.001` | Lazarus Group | **REMOVED (wrong group, wrong technique)** | [CISA AA24-207A, 2024-07-25](https://cisa.gov/sites/default/files/2024-07/aa24-207a-dprk-cyber-group-conducts-global-espionage-campaign.pdf) | "The actors typically exfiltrate data to web services such as cloud storage or servers not associated with their primary C2." | - | Andariel, not Lazarus Group. Exfiltration to cloud storage is T1567, not T1071.001 (C2 over web protocols). |

## What the removals say about how the edges were first written

The pattern behind most removals is the same: the original evidence
text named a real report and a plausible sequence, but the sequence
came from what the techniques usually look like together, and the
report was attached afterwards. Three edges admitted this in their own
evidence text ("follows the pipeline's natural shape", "inferred from
co-citation"). Four misread the source (wrong technique, wrong
mechanism, or a detail the report does not contain). Two credited the
wrong group or the wrong campaign. The fix is the rule at the top of
this file, enforced by the `quote` and `source_url` fields every edge
now carries.

## Open for Venu

- **APT29 `T1204.002 -> T1078`.** The Trello quote in row 8 supports
  "executing the phishing payload preceded Domain Admin, in under 12
  hours" - a real, quotable edge, but a new one, so it was not added
  in a consolidation pass. Decide deliberately whether to add it.
- **Andariel.** Rows 16 and 17 are real behavior with a good quote,
  attributed to the wrong group. Andariel is not a seed group, so
  re-homing them would widen scope.
- **Lazarus Group now has no semantic edges.** The structural
  `USES_TECHNIQUE` data for it is unchanged.
