# Future direction: scaling this project vertically and horizontally

> **MOSTLY DESIGN ONLY - ONE SECTION IS AN ALREADY-TRUE FACT.** The
> "Already true today" section below is a real, verified property of the
> current code (`api/main.py` as of this writing) - not a future
> aspiration. Everything after it ("Vertical scaling," "What would need
> to change for real scale") is deferred design thinking, dated
> 2026-08-15, written by the `scalability-design` skill
> (`.claude/skills/scalability-design/SKILL.md`) - nothing there is
> built, and none of it should be inferred as planned or imminent. See
> "What would trigger picking this up," at the end, before anyone acts
> on any of it.

## Context

Phase 4 (docs/decisions/007-api-and-containerization.md) put a FastAPI
service and a Docker image in front of the existing Graph RAG query
layer. That naturally raises the interview-style question this document
answers directly: does this scale, and how? The honest answer splits
into two very different kinds of claim - one that's already true about
the code as it exists right now, and a much larger set of things that
would only become true with real infrastructure work this prototype
hasn't done and doesn't need yet.

## Already true today: the service is horizontally scalable as-is

**Verified by reading the actual code, not assumed.** `api/main.py`
loads the combined graph once at process start
(`_graph = load_graph()`, module-level) and every subsequent request
only *reads* it - `query/retrieval.py`'s `get_technique_context()` calls
`g.nodes`, `g.in_edges(...)`, `g.out_edges(...)`, all read-only NetworkX
operations; nothing in the request path calls `g.add_edge`,
`g.remove_node`, or any other mutating method. `format_context()` is a
pure function over the dict that call returns. `query/rag.py`'s
`answer()` and its two deterministic guards
(`_check_no_ungrounded_techniques`, `_check_no_ungrounded_edges`)
operate only on the response text and the facts string passed to them -
no shared state written or read across requests. A grep across
`api/`/`query/` for any cache, global mutable dict, or other in-process
state beyond the one read-only `_graph` object turned up nothing.

**What this means concretely**: N replicas of the exact same container
image, each independently loading its own in-memory copy of the same
committed `data/graph_with_semantics.json`, can sit behind a load
balancer with zero coordination between them. There's no session
affinity requirement (no per-client state exists to route around), no
shared-cache-invalidation problem (there's no cache at all - see
"Caching," below, for why that's a *future* addition, not a gap in this
claim), and no risk of one replica serving stale data another has since
mutated (nothing ever mutates the graph after it's loaded). The only
thing every replica needs is the same environment - the LLM provider
credentials from `.env` (via `docker-compose.yml`'s `env_file:` today,
a shared secrets mechanism in any real orchestrator tomorrow) - which is
ordinary configuration, not a statefulness problem.

This is the actual, correct, already-true scaling story for this
project: **a stateless, read-only service where horizontal scaling is
trivial by construction**, not something that needs to be built. That's
a stronger claim than any infrastructure work below, and it's true right
now with `docker compose up --scale api=N` (a real orchestrator would
replace `docker compose` for that at real scale - see "Container
orchestration," below - but the *reason* it would work is this
statelessness property, which doesn't change).

One caveat worth being explicit about, not a contradiction of the claim
above: nothing about *rate limiting or per-client fairness* exists
today (see docs/security-assessment.md / the `red-team-assessment`
skill's LLM lens, which already documents OWASP LLM10 - Unbounded
Consumption - as out of scope for "a single-user, non-production
prototype with no exposed service"). Running N replicas doesn't require
building that, but the moment this is a real, publicly reachable,
multi-replica service, that already-documented "out of scope for now"
item becomes genuinely in scope - see "Rate limiting," below.

## Vertical scaling

**Current numbers** (measured 2026-08-15, re-verify before reusing):
`data/graph_with_semantics.json` is 26 nodes / 71 edges, ~50KB on disk.
Loading it into a NetworkX `MultiDiGraph` and holding it in memory for a
process's lifetime is not a meaningfully measurable cost at this size -
milliseconds to parse, negligible resident memory next to a Python
interpreter's own baseline footprint.

**Don't conflate two different "full load into memory" costs in this
codebase - they have different owners and different scaling stories:**
1. `query/graph_loader.py` (loaded by `api/main.py` at process start,
   and by `query/ask.py` on every CLI invocation) - the ~50KB combined
   graph JSON. This is the one relevant to the *running service's*
   vertical scaling.
2. `graph/build_graph.py` (loaded only when a maintainer regenerates the
   committed graph JSON) - the ~48MB raw STIX bundle, already flagged
   in that file's own comment as "accepted tradeoff at this prototype's
   scale (13 seed techniques); revisit if the seed set ever grows
   significantly." This is a **build-time-only** cost - it never runs
   on the API's request path (confirmed: `docker/Dockerfile` never
   invokes `graph.build_graph`, and `api/main.py` never imports it) - so
   it has no bearing on the running service's vertical scaling at all,
   even though it sounds like the same category of tradeoff. Revisiting
   it (e.g. filtering the STIX bundle instead of loading it whole)
   would speed up graph *rebuilds* for maintainers, not API responses.

**Given that, here is the actual vertical-scaling lever priority for the
*running service*, ordered by what would matter first if load grew -
deliberately not leading with a graph-representation change, since the
numbers above don't support one being the bottleneck:**

1. **Request concurrency (CPU/threads), not graph size, first.**
   `api/main.py`'s route handlers are synchronous `def`s; FastAPI runs
   them in a bounded thread pool (via Starlette/AnyIO) rather than on
   the event loop directly. The dominant cost per request is the LLM
   provider network call (hundreds of milliseconds to seconds), not the
   in-process graph traversal (sub-millisecond at this graph's size).
   The first practical lever under real load is simply more CPU/threads
   per container (or an explicit `--workers` count for uvicorn) - a
   classic "give the process more resources" vertical scale, unrelated
   to the graph at all.
2. **Caching repeated queries, second.** Retrieval
   (`get_technique_context`/`format_context`) is a pure, deterministic
   function of `(technique_id, group)` against a read-only graph - the
   same inputs always produce the same facts block. Caching
   `(technique_id, group, provider, question) -> response` would cut
   both latency and LLM API cost for repeated questions (a realistic
   pattern for a demo or interview walkthrough, and the actual most
   effective single vertical lever here) without needing anything else
   on this list. See "Caching," below, for why this is listed as
   *future* rather than done.
3. **Graph representation (lazy loading, or a real graph database),
   last, and only if the numbers actually change.** At 26 nodes / 71
   edges, replacing the in-memory NetworkX graph with anything else
   would be solving a problem that doesn't exist - exactly the kind of
   premature complexity CLAUDE.md's Code Review Standards already warn
   against elsewhere in this project. This becomes worth revisiting only
   if the committed graph JSON's own size or the query patterns against
   it change substantially - see "Graph database," below, for the actual
   trigger condition.

## What would need to change for real scale

Each item here is deferred, design-only, and paired with the concrete
condition that would make it worth doing - not proposed as a roadmap.

### Graph database (e.g. Neo4j) instead of in-memory NetworkX
**Trigger condition**: either (a) the committed graph JSON grows from
tens of KB to a size where per-process full-load stops being trivial
(plausibly high tens/low hundreds of MB - full in-memory Python graph
structures cost several times their JSON size once parsed into objects,
so this is a generous but not unbounded threshold, not something 13, or
even a few hundred, hand-authored techniques would approach), or (b) a
real query pattern needs multi-hop traversal - `docs/decisions/003`'s
single-technique/one-hop retrieval is a deliberate scope cut for this
prototype, not a technical ceiling, but a real multi-hop/multi-entity
query need (e.g. "compare APT29 and APT28 across their full kill
chains") would be the kind of graph query a dedicated graph database's
query planner and indexing genuinely outperform repeated
Python-level NetworkX traversal on. `docs/future/multi-agent-ingestion.md`'s
continuous-ingestion scenario, if ever picked up, is the most likely
real path to condition (a) - a hand-authored edge set grows slowly by
construction; an ingestion pipeline doesn't.

### Container orchestrator (e.g. Kubernetes) instead of `docker compose`
**Trigger condition**: more than one instance is *genuinely* needed for
real traffic - not "could theoretically run more than one," which is
already true today per "Already true today," above, but an actual need
for autoscaling driven by real load, rolling deploys with real uptime
requirements, or multi-host placement. `docker compose`'s
`--scale api=N` already demonstrates the horizontal story on a single
host; an orchestrator earns its complexity only once "single host,
manually scaled" stops being sufficient for a real deployment target -
this prototype has none.

### Caching for repeated queries
**Trigger condition**: genuinely lower bar than the other two - this is
the cheapest, most clearly justified addition on this list, and worth
picking up as soon as repeated-question latency/cost is actually
observed to matter (a real demo/interview session hitting the same
question twice is enough justification, unlike the other items here
which need real production-scale load to justify). Deliberately still
listed as future rather than done: an LRU (or Redis, once genuinely
multi-process/shared) cache keyed on `(technique_id, group, provider,
question)` needs a decision about cache invalidation when
`data/graph_with_semantics.json` changes (a new image deploy naturally
invalidates an in-process cache; a shared external cache would need
that made explicit) - a real design decision, not a one-line addition,
so it's recorded here rather than added silently.

### Rate limiting / per-client quotas
**Trigger condition**: this service becomes genuinely, publicly
reachable with real (not just theoretical) multi-client traffic - at
which point `docs/security-assessment.md`'s existing "OWASP LLM10 -
Unbounded Consumption... worth a real look only if this ever becomes a
publicly reachable service" caveat stops being a documented
out-of-scope item and becomes something the `red-team-assessment`
skill's LLM lens needs to actually cover. Horizontal scaling itself
doesn't require this (see "Already true today," above, and its
caveat) - real external traffic does.

## What would trigger picking this up

Same discipline as `docs/future/multi-agent-ingestion.md` and
`docs/future/detection-coverage.md`: nothing above gets built as a
matter of course. Each subsection's own "Trigger condition" is the bar
for that specific piece; picking up this document as a whole (re-running
the `scalability-design` skill to refresh it) happens only per that
skill's own trigger conditions - an explicit request to plan scaling, or
one of the load-bearing changes actually happening (the seed set growing
significantly beyond 13 techniques, or a real concurrent-user scenario).
Revisit the numbers in "Vertical scaling" and the statelessness
verification in "Already true today" against whatever's actually true
at that point rather than assuming they still hold - this document is a
snapshot, not a standing guarantee.
