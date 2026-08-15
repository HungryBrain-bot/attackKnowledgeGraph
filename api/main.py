"""
FastAPI wrapper around the Graph RAG query layer (Phase 4).

A new entry point on top of the same core functions query/ask.py's CLI
already calls - query/retrieval.py's get_technique_context()/
format_context(), query/llm_provider.py's has_credentials()/
get_provider(), and query/rag.py's answer() - not a reimplementation of
any of it. Entity extraction (technique ID / group name from free text)
is imported directly from query/ask.py rather than duplicated, so the
API and CLI are governed by the exact same "what counts as a valid
question" logic. See docs/decisions/007-api-and-containerization.md for
why FastAPI, and the Docker packaging decisions.

    uvicorn api.main:app --reload

This is a new user-facing input path (see docs/security-assessment.md's
dated entry for this addition) - the LLM-injection surface itself is
unchanged from the CLI (same untrusted-question / trusted-facts
separation from docs/decisions/005), but HTTP exposure adds its own
concerns handled here: a request-size ceiling (`MaxBodySizeMiddleware`)
and a catch-all exception handler so an unexpected failure returns a
clean, generic 500 instead of a stack trace.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from graph.seed_config import SEED_TECHNIQUES
from query.ask import extract_group, extract_technique_id
from query.graph_loader import load_graph
from query.llm_provider import PROVIDERS, get_provider, has_credentials
from query.rag import answer
from query.retrieval import format_context, get_technique_context

# Generous for a free-text question, small enough to reject an
# oversized-body attempt before it reaches JSON parsing or the LLM
# prompt. Checked against the Content-Length header in
# MaxBodySizeMiddleware below - see docs/security-assessment.md for the
# documented residual gap (a chunked request with no Content-Length
# header isn't caught by a header check alone).
MAX_BODY_BYTES = 10_000

app = FastAPI(
    title="attck-graph query API",
    description="Graph RAG over a scoped MITRE ATT&CK subset - see CLAUDE.md.",
)

# Loaded once at process startup, not per-request - a long-lived server
# process re-parsing data/graph_with_semantics.json on every request
# would be pure overhead, and a missing/corrupt graph file should fail
# the process at startup (a loud, immediate error) rather than surface
# as a mysterious 500 on the first request.
_graph = load_graph()


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Rejects a request whose declared Content-Length exceeds
    MAX_BODY_BYTES with a clean 413, before it reaches route handling or
    JSON parsing."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None and int(content_length) > MAX_BODY_BYTES:
            return JSONResponse({"detail": "Request body too large"}, status_code=413)
        return await call_next(request)


app.add_middleware(MaxBodySizeMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all so an unexpected failure (e.g. an LLM SDK raising a type
    this module didn't anticipate) returns a clean, generic 500 instead
    of a raw traceback - FastAPI's default `debug=False` already
    suppresses traceback detail in the response, this is a second,
    explicit backstop so that stays true regardless of how the app is
    launched."""
    return JSONResponse({"detail": "Internal server error"}, status_code=500)


class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="A question mentioning an ATT&CK technique ID, e.g. 'what happens after T1059.001 for APT29?'",
    )
    provider: str | None = Field(
        None,
        description="Override LLM_PROVIDER for this request, e.g. 'openai' or 'claude'. Omit to use the configured default.",
    )


class QueryResponse(BaseModel):
    technique_id: str
    group: str | None
    facts: str
    answer: str | None
    note: str | None = None


@app.get("/health")
def health() -> dict:
    """Confirms the graph actually loaded (not just that the process is
    up) by reporting its real node/edge counts."""
    return {
        "status": "ok",
        "graph_nodes": _graph.number_of_nodes(),
        "graph_edges": _graph.number_of_edges(),
    }


@app.get("/techniques")
def techniques() -> dict:
    """The 13 seed technique IDs, for anyone exploring the API without
    prior knowledge of graph/seed_config.py."""
    return {"techniques": SEED_TECHNIQUES}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    technique_id = extract_technique_id(req.question)
    if technique_id is None:
        raise HTTPException(
            status_code=400,
            detail="Couldn't find a technique ID (e.g. T1059.001) in the question - this prototype's query layer requires one.",
        )
    group = extract_group(req.question)

    try:
        context = get_technique_context(_graph, technique_id, group=group)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    facts = format_context(context)

    if req.provider is not None and req.provider not in PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown provider {req.provider!r} - choices: {sorted(PROVIDERS)}",
        )

    if not has_credentials(req.provider):
        return QueryResponse(
            technique_id=technique_id,
            group=group,
            facts=facts,
            answer=None,
            note="No LLM provider credentials configured for this provider - showing retrieved facts only.",
        )

    try:
        answer_text = answer(req.question, facts, provider=get_provider(req.provider))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM provider call failed: {e}")

    return QueryResponse(technique_id=technique_id, group=group, facts=facts, answer=answer_text)
