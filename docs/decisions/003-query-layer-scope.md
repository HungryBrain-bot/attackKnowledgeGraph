# 003. Query layer: single-technique retrieval, LLM formats only

## Status
Accepted

## Context
Phase 3 is the "small Graph RAG query layer" scoped in CLAUDE.md and the
README: traverse the graph for a relevant subgraph, have the LLM format
it into a cited natural-language answer, with the LLM never originating
facts. Two real design questions had to be settled before writing any
code: how much of the graph a single query should retrieve, and how a
free-text question gets mapped to a graph query at all without turning
this into a second LLM call (or a full NL-to-Cypher-style system, well
past this prototype's scope).

## Decision

**Retrieval is single-technique-centric, one hop, with an optional group
filter.** `query/retrieval.py` takes a technique ID and returns that
technique's own attributes, its structural `USES_TECHNIQUE` usage
(unfiltered - which groups use it at all), and every semantic edge
directly touching it, optionally filtered to one group's
`group_context`. It does not walk multiple hops or resolve
multi-technique questions in one call. This isn't an arbitrary cut: every
case file's "What This Enables" section is already phrased exactly this
way - "technique X observed, group Y, what's next / what enabled it" -
so retrieval matches the shape the semantic edges were actually authored
to answer, not a hypothetical broader one.

**Entity extraction from the question is plain regex/string matching,
not an LLM call.** ATT&CK technique IDs (`T\d{4}(\.\d{3})?`) and this
project's three seed group names are unambiguous, well-known identifiers
- there's no natural-language ambiguity to resolve, so spending an LLM
call (and its latency/cost) on extracting them would be pure overhead.
`query/ask.py` requires a technique ID to be present in the question and
errors clearly if none is found, rather than guessing.

**The LLM's only job is formatting the retrieved facts.** `query/rag.py`
sends a single Messages API call (`claude-opus-5`, matching this
project's Model Usage convention that runtime application code isn't
subject to the development-time cost tiering) with a system prompt that
forbids using anything outside the FACTS block, requires every
substantive claim to cite its source, and requires the model to say so
explicitly when the facts don't cover something - rather than filling
gaps from its own training knowledge of ATT&CK. This is Retrieval
(deterministic graph traversal) then Generation (constrained formatting)
as two genuinely separate steps, not a single opaque LLM call that
happens to see some graph data.

## Alternatives considered
- **LLM-based intent/entity extraction from the question**: rejected -
  technique IDs and group names are already unambiguous strings; an LLM
  call to extract them would add latency and a second point of failure
  for zero disambiguation benefit.
- **Multi-hop or multi-entity retrieval** (e.g. "compare APT29 and APT28
  on T1059.001", or walking two edges deep): rejected for this pass -
  not what the current semantic edges were authored to support, and
  would meaningfully grow the retrieval and prompt-construction surface
  for a "small" query layer. A natural next step, not in this pass.
- **Letting the LLM see the raw graph JSON** instead of a formatted facts
  block: rejected - the formatted block is what makes the "cite your
  sources" and "don't use outside knowledge" system-prompt rules
  enforceable and auditable; a raw JSON dump makes it harder to verify
  the model didn't quietly use something outside it.

## Consequences
- The query layer only answers questions that name a technique ID -
  "what happens after T1059.001 for APT29" works, "what should I watch
  for after a phishing email" does not (no technique ID to anchor on).
  This is an honest, documented limit of the prototype, not a bug.
- Extending to multi-hop or multi-entity queries later means extending
  `retrieval.py`'s traversal, not touching `rag.py` - the two are
  already cleanly separated by the facts-block boundary.
- Every answer is verifiable against `format_context()`'s output, which
  is printed alongside the answer in `query/ask.py` - a reviewer never
  has to trust the LLM's citations blind.
