# 007. REST API wrapper (FastAPI) and containerization

## Status
Accepted

## Context
Phase 3 built a real Graph RAG query layer, but the only entry point was
`query/ask.py`, a CLI - useful for developing and testing the pipeline,
but not something another service, a frontend, or a reviewer without a
local Python environment could hit directly. This phase wraps the
existing query layer behind HTTP and packages it as a container, without
touching any of the query layer's own logic - `api/main.py` is a new
caller of `query/retrieval.py`, `query/rag.py`, and
`query/llm_provider.py`, exactly like `query/ask.py` already is, not a
second implementation of any of it.

Two real decisions had to be made: which web framework, and how the
container gets the graph data it needs to answer queries without baking
in the 48MB raw STIX bundle or any secret.

## Decision

**FastAPI, not Flask.** Three concrete reasons, not a default preference:
1. **Pydantic request/response models come for free.** `QueryRequest`/
   `QueryResponse` in `api/main.py` double as both the input-validation
   layer (a malformed body is a structured `422`, not a hand-rolled
   `if`-chain) and the API's self-documenting schema - Flask would need
   an added library (e.g. `marshmallow` or `pydantic` bolted on
   separately) to get the same thing.
2. **Auto-generated OpenAPI docs at `/docs`** give anyone exploring this
   API - including a reviewer who hasn't read this repo - a working,
   interactive reference with zero extra code, which directly serves the
   task's own ask for a `/techniques` endpoint "useful for anyone
   exploring the API without prior knowledge of `seed_config.py`."
3. **Async-native (via Starlette/ASGI) without forcing async code.** This
   project's route handlers are synchronous (the query layer is pure
   Python/NetworkX plus a blocking SDK call, none of it async) and
   FastAPI runs sync `def` handlers in a thread pool automatically - so
   this isn't "chose FastAPI for async" in a project with no async need,
   it's "chose FastAPI for its validation/docs ergonomics, and it
   happens not to force an async rewrite to get them."

Flask remains a perfectly fine choice in general; it just would have
meant writing by hand what FastAPI provides directly, for a project this
size with no other constraint pointing at Flask specifically (e.g. an
existing Flask-based deployment target, which doesn't exist here).

**The container never fetches the STIX bundle, and never builds the
graph at image-build time.** This isn't a build-vs-mount tradeoff in the
usual sense, because there's a third option this project already has:
`data/graph_with_semantics.json` (the combined structural + semantic
graph `query/graph_loader.py` reads) is a **committed, tracked file in
this repo** - only `data/raw/enterprise-attack.json` (the 48MB upstream
STIX bundle) and `data/test_logs/` are gitignored. The API's entire
runtime data dependency is that one already-committed JSON file, so the
`Dockerfile` just `COPY`s the repository in like any other source file -
no `curl`, no `graph.build_graph`/`graph.semantic_edges` invocation, no
volume mount required for the image to serve real answers immediately
after `docker build`. Rebuilding the graph from the raw STIX bundle
remains a maintainer-only, README-documented step (unchanged from Phase
1) for whoever updates `graph/seed_config.py` or `graph/semantic_edges.py`
and needs to regenerate the committed JSON - not something the API
container needs to do or wait on.

`data/raw/` and `.env` are excluded from the build context via
`.dockerignore` (not just left out of `COPY` instructions) so a stray
`COPY . .` can never accidentally pull in the 48MB raw bundle or a
secret - defense in depth, not reliance on remembering the right `COPY`
paths.

**Single-stage Dockerfile, not multi-stage.** Multi-stage buys a smaller
final image when the build stage needs tooling (a C compiler, dev
headers) the runtime stage doesn't - none of this project's dependencies
(`fastapi`, `uvicorn`, `networkx`, `anthropic`, `openai`,
`mitreattack-python`, `pyvis`, `python-dotenv`) require compilation on
the `python:3.13-slim` base; all resolve to pure-Python or manylinux
wheels. A multi-stage split here would add Dockerfile complexity to
solve a problem (bloated final image from leftover build tooling) that
doesn't exist for this dependency set - the same "don't add complexity
ahead of an observed need" standard CLAUDE.md's Code Review Standards
already apply to the rest of this codebase.

**`docker-compose.yml`** wraps the single service with a port mapping and
an `env_file: .env` reference, so `docker compose up` is a real
one-command path from a fresh clone to a running API - matching the
existing README Quick Start's spirit (a copy-pasteable sequence that
actually works) for anyone who'd rather not set up a Python venv at all.

## Security

Per the `red-team-assessment` skill's trigger conditions (a new
user-facing input path), the LLM and code lenses were run against
`api/main.py` specifically before this was called done - see
docs/security-assessment.md's 2026-08-15 "`api/main.py` FastAPI wrapper"
entry for the full results. Summary: HTTP exposure doesn't weaken the
injection resistance already verified for the CLI, because `/query`
calls the exact same guarded `rag.answer()` function with no new code in
between; the new HTTP-specific surface (request size, malformed JSON,
content-type) is handled by `MaxBodySizeMiddleware` and FastAPI/Pydantic's
own request parsing, and a catch-all exception handler was added and
live-verified so an unexpected failure returns a generic `500` rather
than a stack trace. One honestly-documented residual gap: the request-size
middleware checks `Content-Length` only, not a `Transfer-Encoding:
chunked` body with no declared length - noted in the assessment entry as
a known gap for a real deployment (reverse-proxy body-size limiting)
rather than solved preemptively in this prototype's own middleware.

## Alternatives considered
- **Flask**: rejected per the FastAPI reasoning above - not wrong, just
  more code to get the same validation/docs behavior this project gets
  for free with FastAPI.
- **Fetching/building the graph at Docker build time** (`RUN curl ... &&
  python -m graph.build_graph && python -m graph.semantic_edges`):
  rejected - it would download the 48MB STIX bundle on every image
  build for data that's already sitting in the repo as a committed,
  version-controlled artifact; pure waste with no benefit, and it would
  make the image build depend on an external network call that has
  nothing to do with what the API actually serves.
- **Requiring a mounted volume for the graph JSON at container run
  time**: rejected for the same reason - the file is already committed
  and small (well under the image's own source size), so there's no
  "large/frequently-changing data" justification for keeping it out of
  the image the way there is for the raw STIX bundle.
- **Multi-stage Dockerfile**: rejected per the reasoning above - no
  compiled dependency in this project's `requirements.txt` needs
  build-stage tooling that the runtime stage doesn't also need, so a
  multi-stage split wouldn't meaningfully shrink the final image, only
  add structure for its own sake.

## Consequences
- `docker build` produces a working image with zero external network
  access required during the build (no STIX fetch) - a fresh clone with
  Docker and nothing else can go from `git clone` to a running API with
  `docker compose up`.
- If a future maintainer updates `graph/seed_config.py` or
  `graph/semantic_edges.py`, they must still re-run
  `python -m graph.build_graph && python -m graph.semantic_edges` and
  commit the regenerated `data/graph_with_semantics.json` (and
  `data/structural_graph.json`) before rebuilding the image - the image
  build itself will not pick up a graph change without that commit,
  since it only ever copies whatever is already checked in. This matches
  how `docs/graph_visualization.html` and the Mermaid diagrams already
  work in this repo (regenerate-then-commit, not regenerate-on-build).
- `api/main.py` loads the graph once at import time (module-level
  `_graph = load_graph()`), so a missing or corrupt
  `data/graph_with_semantics.json` fails the container at startup with a
  clear error, rather than surfacing as a mysterious first-request 500.
