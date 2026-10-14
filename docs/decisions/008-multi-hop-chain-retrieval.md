# 008. Multi-hop chain retrieval, still no LLM in the loop

## Status
Accepted

## Context
ADR 003 scoped retrieval to single-technique, one hop, and explicitly
listed multi-hop/multi-entity retrieval as "a natural next step, not in
this pass." That next step arrived: a question can legitimately name a
chain of technique IDs in sequence (e.g. "what happens going from
T1566.001 to T1204.002 to T1059.001 for APT29?"), and the one-hop
retriever has no way to answer it - it only ever looks at edges directly
touching a single technique.

The real design question wasn't *whether* to support this (the project's
own "LLM does not originate facts" rule and ADR 003's Consequences
section both already anticipated it: "extending to multi-hop queries
later means extending `retrieval.py`'s traversal, not touching `rag.py`"
- the boundary was built for this). It was *how* to walk multiple hops
without reintroducing the thing single-hop retrieval was designed to
avoid: an LLM guessing at connections instead of a deterministic
traversal proving them.

## Decision

**Multi-hop chains are resolved by bounded breadth-first search over
the semantic-edge graph only - still pure Python, still zero LLM calls.**
`query/retrieval.py` gains `get_chain_context()`: given an ordered list
of 2+ technique IDs, it builds each technique's own one-hop context
(reusing `get_technique_context()` - no duplicated validation or fact-
extraction logic) and, for each consecutive pair, searches for the
shortest connecting path over `TEMPORALLY_PRECEDES`/`CAUSALLY_ENABLES`
edges only, optionally filtered to one group, same as single-hop
retrieval's group filter.

**BFS, not DFS, and bounded, not unbounded.** BFS guarantees the first
path found is the shortest one - important for a user-facing chain
query, where the most direct documented path is more informative than
an incidental long one. The search is capped at `MAX_CHAIN_HOPS = 4`:
the semantic-edge graph is still only 17 hand-authored edges, so an
unbounded search adds no real capability today, only a (currently
theoretical) infinite-loop/runaway-traversal risk if the graph ever grew
a cycle. This is the same "don't solve a problem that hasn't occurred"
discipline as CLAUDE.md's Code Review Standards - revisit the bound if
the semantic-edge set grows enough that 4 hops starts clipping real,
intended chains.

**No path found is reported explicitly, never silently filled in.**
`format_chain_context()` prints `(no semantic-edge path found within N
hops ...)` for an unreachable link - the same grounding discipline as
`format_context()`'s "(none - no hand-authored semantic edge touches
this technique)" line for a single technique. This matters more here
than in the single-hop case: an LLM asked "what connects X to Y" is more
tempted to reach for its own ATT&CK training knowledge to bridge a gap
than it is to invent a single fact from nothing, so making "no path"
unambiguous in the facts block is the control against that.

**Entity extraction still isn't an LLM call.** `query/ask.py`'s
`extract_technique_ids()` returns every technique ID in the question, in
the order mentioned, deduplicated - same regex as before
(`T\d{4}(\.\d{3})?`), just not stopping at the first match. 2+ IDs route
to the new chain path; exactly 1 keeps using the unchanged single-hop
path (`extract_technique_id()` is kept as a back-compat wrapper -
`api/main.py` still only exercises the single-hop path; extending the
API to the chain path is a separate, unbuilt follow-on, not done here).

## Alternatives considered
- **Let the LLM infer the connecting path from two separately-retrieved
  one-hop contexts**: rejected - this is exactly the hallucination risk
  the project's "LLM does not originate facts" rule exists to close off.
  An LLM asked to bridge two retrieved fact blocks has no way to
  distinguish "I found this in the data" from "this seems plausible
  given my training knowledge of ATT&CK."
- **Unbounded path search**: rejected per the Code Review Standards
  discipline above - no real data in this prototype needs more than a
  few hops, so the extra complexity (and the unbounded-search risk) buys
  nothing today.
- **DFS or all-paths enumeration**: rejected - BFS's shortest-path-first
  property is the right default for "what connects X to Y," and
  enumerating every path would mean more output to verify for little
  added insight at this graph's size.

## Consequences
- `query/retrieval.py` now exports `get_chain_context()` and
  `format_chain_context()` alongside the unchanged `get_technique_context()`/
  `format_context()` - the single-hop path's behavior, output format,
  and existing callers (`api/main.py`, `tests/test_adversarial_queries.py`,
  `tests/test_query_layer_against_evtx.py`) are untouched.
- `query/ask.py` now accepts chain questions
  (`python -m query.ask "T1566.001 then T1204.002 for APT29"`) and routes
  them to the new path automatically based on how many technique IDs it
  finds - no new CLI flag needed.
- `tests/test_chain_retrieval.py` pins the new behavior deterministically
  (direct hop, multi-hop, no-path, group-filtered unreachability, the
  `ValueError` cases) - no LLM call, never skips.
- `api/main.py`'s `/query` endpoint does not yet expose the chain path -
  it still only extracts and resolves the first technique ID in a
  question (via the back-compat `extract_technique_id()`). This is an
  honest, unbuilt follow-on, not an oversight: see README's Roadmap.
- ADR 003's single-hop design remains correct for the common case (one
  technique, "what's next/what enabled it") - this ADR extends it rather
  than replacing it.
