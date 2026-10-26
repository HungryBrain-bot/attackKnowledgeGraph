# 009. Multi-hop chains use one group's edges per path, and say when they span incidents

## Status
Accepted (2026-10-26). Amends ADR 008's path search; ADR 008's BFS,
hop bound, and "report no path explicitly" decisions are unchanged.

## Context
ADR 008's `_find_semantic_path()` applied the group filter only when
the caller gave one. With no group in the question it searched every
group's edges at once, so the shortest path could switch actors
mid-chain. A senior-security-engineer review (2026-10-26) confirmed it:
with no group filter, `T1021.001 -> T1003.002` came back as

```
hop 1: [APT28] T1021.001 --CAUSALLY_ENABLES--> T1059.001
hop 2: [APT29] T1059.001 --TEMPORALLY_PRECEDES--> T1078
hop 3: [APT28] T1078 --CAUSALLY_ENABLES--> T1003.002
```

No intrusion ran that sequence. Every edge is group-scoped (ADR 002)
precisely so this kind of composite would not be presented as fact.

The review also found a quieter version of the same problem with a
group filter on: one group's edges come from several different
operations (APT29's phishing-chain edges are from Dukes-era reporting,
its discovery edges from SolarWinds, its credential-dumping edge from
UNC3524). A filtered path can therefore show an order no single
APT29 operation was documented to follow.

## Decision
1. **A path never mixes groups.** `_find_semantic_path()` now requires
   a group. `get_chain_context()` runs it once per group when the
   question names none, and returns each group's path side by side
   under `links[i]["paths"]`. Paths from different groups are never
   joined, and `format_chain_context()` says so in the facts block.
2. **Every edge carries `incident_id`**, the one operation it was
   observed in, or `None` when its sources describe different
   operations. Each path lists the incidents its hops come from, and
   `spans_incidents` is True when there is more than one or any is
   unknown. The facts block then prints a WARNING line that the path
   is not one observed intrusion sequence.
3. Link shape changes from `{"path", "hops"}` to
   `{"paths": [{"group", "path", "hops", "incidents", "spans_incidents"}]}`.
   No external consumer reads it: `api/main.py` returns only the
   rendered facts text, not the context dict.

## Alternatives considered
- **Label every hop with its group but still return the mixed path**:
  rejected. Hop labels were already there (`[APT28]`, `[APT29]`) and the
  path was still presented as one sequence; an LLM summarising it
  would naturally narrate it as one chain.
- **Refuse multi-hop queries without a group**: rejected. Per-group
  paths answer the unfiltered question honestly, and the
  `T1566.001 -> T1204.002` pair really is documented for two groups.
- **Refuse paths that span incidents**: rejected for now. With 17
  edges almost every multi-hop path spans incidents, so this would
  turn the feature off in practice. A warning keeps the path visible
  and makes its status explicit; revisit if the edge set grows enough
  that single-incident paths become common.

## Consequences
- Unfiltered `T1021.001 -> T1003.002` now correctly reports no path:
  APT28's own edges do not connect them.
- `tests/test_chain_retrieval.py` pins: no path mixes groups (the exact
  review case), unfiltered queries list each group's path separately,
  and a path across incidents is flagged in data and in the facts text.
- The incident labels are only as good as the edge audit behind them
  (ADR 010 and `docs/edge-audit.md`).
- The grounding guard (ADR 005) parses the new
  `incident: ...` field without change, since it only reads
  `confidence` and `sample_size` from the attribute line.
