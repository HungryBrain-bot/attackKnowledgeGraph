# T1078 - Valid Accounts

## The Attack - What Actually Happens
Once an adversary has credentials - dumped, brute-forced, or phished -
they stop looking like an intruder and start looking like a user. For
APT29 in the SolarWinds intrusion, Mandiant's UNC2452 report documents
this transition happening extremely fast: Domain Administrator privileges
within 12 hours of the initial phishing payload executing. For APT28,
the 2021 NSA/CISA/FBI/NCSC joint advisory on the GRU's Kubernetes-based
brute-force campaign describes credentials obtained at scale (targeting
Microsoft 365 and other services across hundreds of organizations) being
turned into further access via "remote code execution and lateral
movement." Separately, Volexity's Nearest Neighbor Attack report shows
compromised Wi-Fi credentials being the specific precondition that let
APT28 RDP into a target network at all.

## The Present Problem
Valid Accounts is arguably the hardest ATT&CK technique to build
detection coverage for precisely because the activity is, by design,
indistinguishable from legitimate use at the log level. A static
technique catalog can't help with that - what helps is knowing what
tends to follow a suspected credential compromise for a given actor, so
monitoring can be front-loaded onto the *next* step (lateral movement,
privilege use) rather than the account activity itself.

## How This Graph Models It
- Node: `T1078` (Technique), tactics `initial-access`, `persistence`,
  `privilege-escalation`, `stealth`.
- Edges: `T1059.001 --TEMPORALLY_PRECEDES--> T1078` (APT29, confidence
  0.85) incoming; `T1078 --CAUSALLY_ENABLES--> T1021.001` (APT28,
  confidence 0.75) and `T1078 --CAUSALLY_ENABLES--> T1059.001` (APT28,
  confidence 0.65) outgoing.

## Evidence and Sources
- Mandiant UNC2452 APT29 April 2022, NSA Joint Advisory SVR SolarWinds
  April 2021 (APT29 timeline).
- Volexity Nearest Neighbor Attack Nov 2024 (APT28, RDP precondition).
- Cybersecurity Advisory GRU Brute Force Campaign July 2021 (APT28,
  credential-to-RCE/lateral-movement pattern, advisory-level not
  incident-specific - see the lower confidence score on that edge).

## What This Enables
"A compromised account was confirmed for an APT28-attributed intrusion -
what should we watch for in the next hour?" surfaces two concrete,
differently-sourced possibilities (RDP-based lateral movement, or
further PowerShell-based exploitation) instead of a generic "monitor for
lateral movement" answer.
