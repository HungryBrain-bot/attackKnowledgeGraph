# T1105 - Ingress Tool Transfer

## The Attack - What Actually Happens
For APT29's UNC3524 activity (merged in as "Eye Spy on Your Email"),
ingress tool transfer is the opening move, not a follow-on: the actor's
first documented step was deploying the QUIETEXIT backdoor onto network
appliances - SAN arrays, load balancers, wireless access points -
specifically chosen because they don't run traditional endpoint
security. Everything else in that intrusion (SOCKS-tunneled lateral
movement, offline SAM/LSA credential extraction, mailbox access) flows
from having that backdoor in place first. For APT28, Trend Micro's Pawn
Storm reporting and the 2021 GRU brute-force joint advisory both
document tool transfer as something PowerShell execution feeds into -
a first-stage script or foothold pulling down further tooling.

## The Present Problem
"A file was downloaded/transferred onto this host" covers everything
from a legitimate software update to the delivery of a second-stage
implant, so the raw event is nearly meaningless without knowing what
usually follows it for a given actor. APT29's UNC3524 pattern shows tool
transfer being the *first* attributable step onto unmonitored network
appliances specifically - a very different triage priority than APT28's
pattern, where it shows up mid-chain, fed by an earlier PowerShell
foothold.

## How This Graph Models It
- Node: `T1105` (Technique), tactic `command-and-control`.
- Edges: `T1105 --CAUSALLY_ENABLES--> T1003.002` (APT29, confidence 0.8,
  sample_size 1, out) and `T1105 --CAUSALLY_ENABLES--> T1547.001`
  (APT29, confidence 0.65, sample_size 1, out); `T1059.001
  --CAUSALLY_ENABLES--> T1105` (APT28, confidence 0.65, sample_size 2,
  in).

## Evidence and Sources
- Mandiant, "UNC3524: Eye Spy on Your Email" (APT29): explicit
  backdoor-deployment-then-credential-dumping sequence.
- Mandiant "No Easy Breach" (APT29, DerbyCon 2016): co-cites T1105 and
  T1547.001; full presentation content not independently retrievable, so
  the tool-transfer-then-persist ordering is inferred rather than
  quoted.
- TrendMicro Pawn Storm Dec 2020, Cybersecurity Advisory GRU Brute Force
  Campaign July 2021 (APT28): both co-cite T1059.001 and T1105; ordering
  inferred from the general shape of a PowerShell-first-stage-then-
  tool-download pattern.

## What This Enables
"Unmonitored network appliance shows an unexpected binary transfer,
APT29 suspected - what should be assumed already compromised, and what's
next?" resolves to: treat this as a likely opening move (per the UNC3524
pattern), and expect offline credential extraction via `reg save` to
follow, not the other way around.
