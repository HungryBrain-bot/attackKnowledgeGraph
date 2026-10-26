# Ownership notes

For Venu, to explain this project closed-book. If you cannot say a
line below without looking, that is the gap to close. Do not extend
the project to cover the gap.

## What it is, in one sentence

A graph of 13 ATT&CK techniques and 3 groups where each semantic edge
says "in this cited report, this group did A, then B", with the quote
that proves it.

## The 5 edges

1. **APT28, Valid Accounts -> RDP (enables).** In Volexity's Nearest
   Neighbor case (Feb 2022), APT28 used privileged credentials to RDP
   into a dual-homed host at the organization across the street.
2. **APT28, RDP -> PowerShell (enables).** On that same host, they ran
   a custom PowerShell script to list the Wi-Fi networks in range.
3. **APT28, Valid Accounts -> SAM dumping (precedes).** In the same
   case, an RDP login with an unprivileged account came before
   `reg save` of the SAM, SECURITY and SYSTEM hives. Order only, not
   cause, because the account was unprivileged.
4. **APT28, Valid Accounts -> PowerShell (enables).** In the 2019-2021
   GRU brute-force campaign, they used an Exchange PowerShell cmdlet to
   grant ApplicationImpersonation to an account they had already
   compromised. A campaign, not one intrusion; the dependency is
   inferred from what the cmdlet needs.
5. **APT29, Malicious File -> PowerShell (enables).** In the November
   2016 PowerDuke campaign, victims opened a shortcut (LNK) file that
   ran PowerShell to drop a backdoor.

Edges 1-3 are one incident, so `T1078 -> T1021.001 -> T1059.001` is the
only multi-hop chain that is a real observed sequence.

## The guard: what it catches and what it misses

Catches, deterministically, before an answer is returned:
- a technique ID that is not in the retrieved facts;
- an edge that is not in the facts, written with arrows or with
  "temporally precede(s/d)" / "causally enable(s/d)", active or
  passive voice;
- a real edge credited to a group the facts do not record it for, if
  the group is named in the same sentence;
- a confidence or sample_size that does not match the stored value.

Misses:
- the same claim in free prose ("PowerShell leads to Valid Accounts");
- a wrong group named in a different sentence, or alongside the right one;
- fabricated sources, quotes or incident details;
- other ways of stating numbers ("85% confident").

It fails closed: an honest refusal that repeats a fabricated edge
without quoting it is rejected too. An error beats a fabricated edge.

## Five questions an interviewer will ask, with honest answers

1. **"You started with 17 edges and have 5. What happened?"**
   I wrote edges from what techniques usually look like together, then
   attached a real report. A review showed several reports did not say
   what the edge claimed: one cited a 2015 report for 2016 malware,
   one called a 2022 phishing campaign SolarWinds, two were about a
   different North Korean group. I re-checked every edge against the
   source text, kept only those I could quote, and now every edge
   stores its quote and URL.

2. **"Your ADR said the guard closed the fabricated-attribute gap. Did it?"**
   No. It checked that an edge existed, not the confidence or group
   next to it, and a phrase like "not documented" after an edge made it
   skip the check. The review found four bypasses; I added them as
   tests, fixed them, and amended the ADR with a Known limitations
   section instead of editing the original claim. It is still pattern
   matching: free prose gets through.

3. **"What do the confidence numbers mean?"**
   My judgment of how directly the quote supports the edge, written
   down per edge. Not a probability, not calibrated, and with one
   source per edge there is nothing to calibrate against.

4. **"Why not let the LLM find the path between two techniques?"**
   Because it would fill gaps from training data, and that is exactly
   the failure the project exists to avoid. Paths come from BFS over
   cited edges; the LLM only rewrites them. Even so, a path was
   misleading until it was limited to one group and labelled when it
   joins different incidents.

5. **"Could a SOC use this?"**
   Not as it stands. It has no detection, telemetry or mitigation data
   and 5 edges. What transfers is the method: per-group, per-incident
   edges with a stored quote, deterministic retrieval, and an output
   check that is tested with probes and honest about what it misses.

## Where the evidence is

- docs/edge-audit.md - every original edge, kept or removed, and why
- docs/decisions/005 (2026-10-26 amendment), 009, 010 - the fixes
- tests/test_rag_guard.py, tests/test_chain_retrieval.py - the probes
